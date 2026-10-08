# src/xstate_statemachine/contrib/channels/broadcast.py
# -----------------------------------------------------------------------------
# 📡 Transitions committed ANYWHERE reach the row's WebSocket subscribers
# -----------------------------------------------------------------------------
# 🏛️ #283 battle: `StatechartConsumer` only pushed transitions that came
#    through a socket -- an approval made in the admin or through the REST
#    API never reached the dashboard watching that expense. A dashboard
#    that only updates when the change came through its own socket is not
#    a dashboard. The fix is a `post_transition(on_commit=True)` receiver:
#    it fires once the row's transaction has COMMITTED (never for a rolled
#    back send) and `group_send`s to the row's group, from any thread.
#
# 📝 Connected on first use (`ensure_broadcaster()`, idempotent via
#    `dispatch_uid`) -- the consumer calls it at import, and a project
#    without a consumer never pays for it.
# -----------------------------------------------------------------------------
"""Broadcast committed transitions to Channels groups."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..django.signals import post_transition

__all__ = [
    "ensure_broadcaster",
    "group_name_for",
    "group_names_for",
    "register_group_namer",
    "transition_message",
]

logger = logging.getLogger(__name__)
_UID = "xsm.channels.broadcast"


def group_name_for(instance: Any) -> str:
    """``xsm.<app>.<model>.<pk>`` -- one group per row."""
    opts = instance._meta
    return f"xsm.{opts.app_label}.{opts.model_name}.{instance.pk}"


# 🔥 #283 battle B: a consumer subclass that overrides `group_name` joined
#    a group the broadcaster never addressed -- its subscribers silently
#    got no pushes. Consumers register their `group_name` per model; the
#    broadcaster sends to every distinct group they name for the row.
_NAMERS: Dict[Any, List[Callable[[Any], str]]] = {}


def register_group_namer(model: Any, namer: Callable[[Any], str]) -> None:
    """Make the broadcaster also address ``namer(instance)`` for *model*."""
    namers = _NAMERS.setdefault(model, [])
    if namer not in namers:
        namers.append(namer)


def group_names_for(instance: Any) -> List[str]:
    """Every group a committed transition on *instance* is sent to."""
    names = [group_name_for(instance)]
    for model, namers in list(_NAMERS.items()):
        if isinstance(instance, model):
            for namer in namers:
                name = namer(instance)
                if name not in names:
                    names.append(name)
    return names


def transition_message(instance: Any, event: Any) -> dict:
    vcol = f"{instance.statechart_field_obj().name}_version"
    return {
        "type": "xsm.transition",
        "event": str(getattr(event, "type", event)),
        "version": getattr(instance, vcol, None),
    }


def _on_commit(sender: Any, instance: Any, event: Any, receipt: Any, **kw):
    if not getattr(receipt, "changed", False):
        return
    layer = get_channel_layer()
    if layer is None:  # pragma: no cover - no CHANNEL_LAYERS configured
        return
    message = transition_message(instance, event)
    for group in group_names_for(instance):
        _push(layer, group, message, event)


def _push(layer: Any, group: str, message: dict, event: Any) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    try:
        if loop is not None:
            # 🔥 #283 battle B: committed on an event-loop thread (e.g.
            #    `DJANGO_ALLOW_ASYNC_UNSAFE`, or a receiver run from async
            #    code): `async_to_sync` raises there. Schedule the push.
            task = loop.create_task(layer.group_send(group, message))
            _PENDING.add(task)
            task.add_done_callback(_done)
            return
        async_to_sync(layer.group_send)(group, message)
    except Exception:  # noqa: BLE001 -- a push must never break a commit
        logger.warning(
            "channels: could not broadcast %s on %s",
            getattr(event, "type", event),
            group,
            exc_info=True,
        )


_PENDING: "set[asyncio.Task]" = set()  # type: ignore[type-arg]


def _done(task: "asyncio.Task") -> None:  # type: ignore[type-arg]
    _PENDING.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.warning(
            "channels: could not broadcast", exc_info=task.exception()
        )


def ensure_broadcaster() -> None:
    """Connect the committed-transition broadcaster (idempotent)."""
    post_transition.connect(
        _on_commit, weak=False, dispatch_uid=_UID, on_commit=True
    )
