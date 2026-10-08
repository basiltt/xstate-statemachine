# src/xstate_statemachine/contrib/channels/consumer.py
# -----------------------------------------------------------------------------
# 📡 StatechartConsumer (see the package docstring for the protocol)
# -----------------------------------------------------------------------------
#    server → client   {"kind": "snapshot", ...state body}
#                      {"kind": "transition", "event", ...receipt body}
#                      {"kind": "receipt", ...receipt body}   (to the sender)
#                      {"kind": "error", "status", "title", "error"}
#                      {"kind": "ping"}
#    client → server   {"type": "EVENT", "payload": {...}}
#                      {"type": "xsm.ping"}  → {"kind": "pong"}
# -----------------------------------------------------------------------------
"""`StatechartConsumer`."""

from __future__ import annotations

import asyncio
import inspect
import logging
import weakref
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from ...receipts import receipt_to_status
from ..django._events import declared_events
from ..django._problems import problem_for_exception, receipt_fields
from ..django.mixin import reserved_keys
from ..django.permissions import has_event_permission, permitted_events
from .broadcast import (
    ensure_broadcaster,
    group_name_for,
    register_group_namer,
)
from ...context_keys import (
    public_context as _public_context,
)  # 🔑 #265: no `_xsm_*` keys in API bodies

__all__ = ["StatechartConsumer", "WS_POLICY_VIOLATION", "live_consumers"]

WS_POLICY_VIOLATION = 1008
logger = logging.getLogger(__name__)
_LIVE: "weakref.WeakSet[StatechartConsumer]" = weakref.WeakSet()


def _concrete_model(user: Any) -> Any:
    """The user's model class, through a `SimpleLazyObject` proxy."""
    cls = type(user)
    if hasattr(cls, "_default_manager"):
        return cls
    from django.utils.functional import LazyObject, empty

    if isinstance(user, LazyObject):
        if user._wrapped is empty:
            user._setup()
        return type(user._wrapped)
    from django.contrib.auth import get_user_model

    return get_user_model()


def live_consumers() -> int:
    """Connected consumers in this process (the leak test reads it)."""
    return len(_LIVE)


class StatechartConsumer(AsyncJsonWebsocketConsumer):
    """Subclass and set `model` (or override `get_instance`)::

        class OrderConsumer(StatechartConsumer):
            model = Order

        websocket_urlpatterns = [
            path("ws/orders/<int:pk>/", OrderConsumer.as_asgi()),
        ]
        # asgi.py: AuthMiddlewareStack(URLRouter(websocket_urlpatterns))

    Attributes:
        model: The `StatechartModelMixin` model.
        lookup_kwarg: URL kwarg carrying the primary key (``"pk"``).
        heartbeat_s: Ping interval; ``0`` disables it.
        context_serializer: ``(context) -> JSON``; context is NOT sent
            without it (X0.1).
    """

    model: Any = None
    lookup_kwarg = "pk"
    heartbeat_s: float = 15.0
    context_serializer: Any = None

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        # 📡 an overridden `group_name` is still addressed by the
        #    broadcaster (#283 battle B).
        namer = getattr(cls, "group_name")
        if cls.model is None or namer is group_name_for:
            return
        if not isinstance(
            inspect.getattr_static(cls, "group_name"), staticmethod
        ):
            raise TypeError(
                f"{cls.__name__}.group_name must be a @staticmethod "
                "(the broadcaster calls it without a consumer)"
            )
        register_group_namer(cls.model, namer)

    # -- hooks -------------------------------------------------------------------
    def get_instance(self) -> Any:
        """The row for this connection (sync; runs in a worker thread)."""
        if self.model is None:
            raise TypeError(f"{type(self).__name__}.model is not set")
        pk = self.scope["url_route"]["kwargs"][self.lookup_kwarg]
        return self.model._default_manager.filter(pk=pk).first()

    def authorize(self, user: Any, instance: Any) -> bool:
        """May *user* watch *instance*? Default: the model's ``view``
        permission (object-level when the backend supports it)."""
        opts = instance._meta
        perm = f"{opts.app_label}.view_{opts.model_name}"
        return bool(user.has_perm(perm) or user.has_perm(perm, instance))

    #: ``xsm.<app>.<model>.<pk>`` (shared with the broadcaster). An
    #: override (a staticmethod) is registered with the broadcaster.
    group_name = staticmethod(group_name_for)

    # -- lifecycle ---------------------------------------------------------------
    async def connect(self) -> None:
        self.instance: Any = None
        self.group: Optional[str] = None
        self._beat: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        user = self.scope.get("user")
        if user is None:
            logger.warning(
                "%s: no 'user' in the scope -- wrap the router in "
                "AuthMiddlewareStack; closing with 1008",
                type(self).__name__,
            )
        if user is None or not getattr(user, "is_authenticated", False):
            # 🔐 No AuthMiddlewareStack, or an anonymous user.
            await self.close(code=WS_POLICY_VIOLATION)
            return
        instance = await database_sync_to_async(self.get_instance)()
        if instance is None or not await database_sync_to_async(
            self.authorize
        )(user, instance):
            await self.close(code=WS_POLICY_VIOLATION)
            return
        self.instance = instance
        self.group = self.group_name(instance)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        _LIVE.add(self)
        body = await database_sync_to_async(self._state)(user)
        await self.send_json({"kind": "snapshot", **body})
        if self.heartbeat_s > 0:
            self._beat = asyncio.ensure_future(self._heartbeat())

    async def disconnect(self, code: Any) -> None:
        if self._beat is not None:
            self._beat.cancel()
            try:
                await self._beat
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._beat = None
        if self.group is not None:
            await self.channel_layer.group_discard(
                self.group, self.channel_name
            )
            self.group = None
        _LIVE.discard(self)
        self.instance = None

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_s)
            # 🔐 M2: a revoked / deactivated user is dropped within one
            #    heartbeat even when the row is quiet.
            if not await database_sync_to_async(self._still_allowed)():
                await self.close(code=WS_POLICY_VIOLATION)
                return
            await self.send_json({"kind": "ping"})

    def _still_allowed(self) -> bool:
        """Re-run the connect-time checks against a FRESH user row."""
        user = self.scope.get("user")
        inst = self.instance
        if user is None or inst is None:
            return False
        try:
            if getattr(user, "pk", None) is not None:
                # 🔥 #283 battle: under `AuthMiddlewareStack` the scope
                #    user is a `SimpleLazyObject`; `type(user)` is the
                #    proxy class (no `_default_manager`), so this raised
                #    and EVERY push closed the socket with 1008 -- every
                #    dashboard subscriber was kicked on the first
                #    transition. The communicator tests set a concrete
                #    user and never saw it. Resolve the real model class.
                model = _concrete_model(user)
                user = model._default_manager.get(pk=user.pk)
                self.scope["user"] = user
        except Exception:  # noqa: BLE001 - deleted user
            return False
        if not getattr(user, "is_authenticated", False) or not getattr(
            user, "is_active", True
        ):
            return False
        return bool(self.authorize(user, inst))

    # -- inbound -----------------------------------------------------------------
    async def receive(
        self,
        text_data: Optional[str] = None,
        bytes_data: Optional[bytes] = None,
        **kwargs: Any,
    ) -> None:
        # 🔥 #283 battle B: a malformed JSON frame (or any binary frame)
        #    raised inside Channels' `receive` -- the consumer task died,
        #    the socket dropped with 1011 and `disconnect` never ran, so
        #    the connection stayed in its group and in `live_consumers()`.
        #    Answer with an error frame; the socket stays open.
        if self.instance is None:
            return
        if text_data is None:
            await self._error(422, "Binary frames are not supported")
            return
        try:
            content = await self.decode_json(text_data)
        except ValueError:
            await self._error(422, "Malformed JSON")
            return
        await self.receive_json(content, **kwargs)

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        if self.instance is None:
            return
        if not isinstance(content, dict) or not isinstance(
            content.get("type"), str
        ):
            await self._error(422, 'Message must carry a string "type"')
            return
        etype = content["type"]
        if etype == "xsm.ping":
            await self.send_json({"kind": "pong"})
            return
        payload = content.get("payload") or {}
        if not isinstance(payload, dict):
            await self._error(422, "payload must be an object")
            return
        bad = reserved_keys(payload)
        if bad:
            # 🔐 H1/H2: never client data.
            await self.send_json(
                {
                    "kind": "error",
                    **_problem(
                        422, "Reserved key in payload", "ReservedKeyError"
                    ),
                    "keys": bad,
                }
            )
            return
        result = await database_sync_to_async(self._send)(etype, payload)
        if "problem" in result:
            await self.send_json({"kind": "error", **result["problem"]})
            return
        await self.send_json({"kind": "receipt", **result["body"]})
        # 📡 #283 battle: the push to the group is the broadcaster's job --
        #    a `post_transition(on_commit=True)` receiver that fires for a
        #    transition committed ANYWHERE (admin, REST API, a command, this
        #    socket). Pushing here too delivered socket-made transitions
        #    twice.

    def _send(self, etype: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._still_allowed():
            return {"problem": _problem(403, "Forbidden", "PermissionDenied")}
        user = self.scope["user"]
        inst = self.instance
        inst.refresh_from_db()
        if etype not in declared_events(inst.statechart_machine_node()):
            return {
                "problem": _problem(422, "Unknown event", "UnknownEventError")
            }
        if not has_event_permission(user, inst, etype, require_enabled=False):
            return {"problem": _problem(403, "Forbidden", "PermissionDenied")}
        try:
            receipt = inst.send(etype, actor=user, payload=payload)
        except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
            status, body = problem_for_exception(exc)
            return {"problem": {**body, "status": status}}
        body = self._state(user)
        body["state_ids"] = sorted(receipt.state_ids)
        body.update(receipt_fields(receipt))
        body["status"] = receipt_to_status(receipt)
        vcol = f"{inst.statechart_field_obj().name}_version"
        return {
            "body": body,
            "changed": bool(receipt.changed),
            "version": getattr(inst, vcol),
        }

    def _state(self, user: Any) -> Dict[str, Any]:
        inst = self.instance
        interp = inst.machine
        body: Dict[str, Any] = {
            "state": interp.value,
            "state_ids": sorted(interp.current_state_ids),
            "available_events": permitted_events(user, inst),
            "machine_version": interp.machine.version or None,
        }
        if self.context_serializer is not None:
            body["context"] = self.context_serializer(
                _public_context(interp.context)
            )
        return body

    # -- group messages ------------------------------------------------------------
    async def xsm_transition(self, message: Dict[str, Any]) -> None:
        """A committed transition on this row (from any connection)."""
        if self.instance is None:
            return

        def fresh() -> Optional[Dict[str, Any]]:
            # 🔐 M2: re-authorise before every push.
            if not self._still_allowed():
                return None
            self.instance.refresh_from_db()
            return self._state(self.scope["user"])

        body = await database_sync_to_async(fresh)()
        if body is None:
            await self.close(code=WS_POLICY_VIOLATION)
            return
        await self.send_json(
            {
                "kind": "transition",
                "event": message.get("event"),
                "version": message.get("version"),
                **body,
            }
        )

    async def _error(self, status: int, title: str) -> None:
        await self.send_json(
            {"kind": "error", **_problem(status, title, None)}
        )


def _problem(status: int, title: str, error: Optional[str]) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
    }
    if error:
        body["error"] = error
    return body


# 📡 committed transitions from anywhere reach the groups (idempotent)
ensure_broadcaster()
