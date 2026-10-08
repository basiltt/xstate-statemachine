# src/xstate_statemachine/contrib/drf/viewsets.py
# -----------------------------------------------------------------------------
# 🧭 StatechartViewSetMixin -- generated @actions per declared event
# -----------------------------------------------------------------------------
#    POST {pk}/<event-slug>/   one per declared event (SUBMIT → submit/,
#                              LEGAL_OK → legal-ok/), payload = body
#    POST {pk}/send/           {"type": "EVENT", ...payload}
#    GET  {pk}/events/         {"available": [...], "declared": [...]}
#    GET  {pk}/history/        TransitionLog rows (view's pagination_class
#                              + filter backends; separate permission)
#    GET  {pk}/stream/         SSE: state now, then on every change
#
#    Status of a send is the CORE receipt table (#305): 200 changed / no-op,
#    202 deferred, 409 guard-denied or stopped, 422 idempotency mismatch;
#    403 when `has_event_permission` (permission guards) refuses the user;
#    422 for an invalid payload or an unknown event on ``send/``.
#
# 🔐 X0.1: building a concrete viewset WITHOUT an explicit
#    ``permission_classes`` raises `ImproperlyConfigured` (write
#    ``[AllowAny]`` if you mean it). X0.2: ``Idempotency-Key`` is scoped to
#    ``request.user.pk``. X0.7: problems carry the exception class only.
# -----------------------------------------------------------------------------
"""`StatechartViewSetMixin`."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Type

from django.core.exceptions import ImproperlyConfigured
from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from ...receipts import receipt_to_status
from ..django._events import declared_events, value_from_ids
from ..django._problems import (
    IDEMPOTENCY_HEADER,
    PROBLEM_MEDIA_TYPE,
    problem_body,
    problem_for_exception,
    receipt_fields,
)
from ..django.mixin import reserved_keys
from ..django.permissions import has_event_permission, permitted_events
from .fields import state_body
from .permissions import StatechartHistoryPermission

__all__ = ["StatechartViewSetMixin", "event_slug", "problem_response"]

RESERVED = ("send", "events", "history", "stream")
#: The audit row's `reason`, sent as a HEADER (payload keys are data).
REASON_HEADER = "X-XSM-Reason"
MAX_REASON_CHARS = 2000


def event_slug(event: str) -> str:
    """``LEGAL_OK`` → ``legal-ok`` (the URL path of its action)."""
    slug = re.sub(r"[^a-z0-9]+", "-", event.lower()).strip("-")
    if not slug:
        raise ImproperlyConfigured(f"event {event!r} has no URL-safe slug")
    return slug


def problem_response(status: int, title: str, **ext: Any) -> Response:
    """An RFC 9457 ``application/problem+json`` response."""
    resp = Response(problem_body(status, title, **ext), status=status)
    resp.content_type = PROBLEM_MEDIA_TYPE
    return resp


# -----------------------------------------------------------------------------
# 📐 Response serializers (for the schema; the views build dicts)
# -----------------------------------------------------------------------------
class StateSerializer(serializers.Serializer):
    state = serializers.JSONField()
    state_ids = serializers.ListField(child=serializers.CharField())
    available_events = serializers.ListField(child=serializers.CharField())
    machine_version = serializers.CharField(allow_null=True)
    context = serializers.JSONField(required=False)


class ReceiptSerializer(StateSerializer):
    changed = serializers.BooleanField()
    denied = serializers.BooleanField()
    deferred = serializers.BooleanField()
    duplicate = serializers.BooleanField()
    error = serializers.CharField(allow_null=True)


class ProblemSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    status = serializers.IntegerField()
    detail = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class EventsSerializer(serializers.Serializer):
    available = serializers.ListField(child=serializers.CharField())
    declared = serializers.ListField(child=serializers.CharField())


class SendSerializer(serializers.Serializer):
    type = serializers.CharField()


class HistorySerializer(serializers.Serializer):
    seq = serializers.IntegerField()
    event = serializers.CharField()
    disposition = serializers.CharField()
    from_states = serializers.ListField(child=serializers.CharField())
    to_states = serializers.ListField(child=serializers.CharField())
    actions = serializers.ListField(child=serializers.CharField())
    actor = serializers.IntegerField(source="actor_id", allow_null=True)
    reason = serializers.CharField(allow_blank=True)
    created = serializers.DateTimeField()


def _schema(**kw: Any) -> Callable[[Any], Any]:
    """`drf_spectacular.utils.extend_schema` when installed, else a no-op."""
    try:
        from drf_spectacular.utils import extend_schema
    except ImportError:  # pragma: no cover - [drf] without spectacular
        return lambda fn: fn
    return extend_schema(**kw)


def _send_responses() -> Dict[int, Any]:
    # 📝 #283 battle: 401 (an Idempotency-Key from nobody) and 503 (store /
    #    inbox outage, #306) are real answers of every send route.
    return {
        200: ReceiptSerializer,
        202: ReceiptSerializer,
        401: ProblemSerializer,
        403: ProblemSerializer,
        409: ReceiptSerializer,
        422: ProblemSerializer,
        503: ProblemSerializer,
    }


def _send_parameters() -> List[Any]:
    """The two request headers every send route reads (schema only)."""
    try:
        from drf_spectacular.utils import OpenApiParameter
    except ImportError:  # pragma: no cover - [drf] without spectacular
        return []
    return [
        OpenApiParameter(
            IDEMPOTENCY_HEADER,
            str,
            OpenApiParameter.HEADER,
            description=(
                "Retry key, scoped to the authenticated user: a replay "
                "answers the original receipt (duplicate=true); the same "
                "key with a different event or payload is 422."
            ),
        ),
        OpenApiParameter(
            REASON_HEADER,
            str,
            OpenApiParameter.HEADER,
            description=(
                "Audit reason recorded on the transition log row "
                f"(max {MAX_REASON_CHARS} chars)."
            ),
        ),
    ]


# -----------------------------------------------------------------------------
# 🧭 Mixin
# -----------------------------------------------------------------------------
class StatechartViewSetMixin:
    """Mix into a ``GenericViewSet`` over a `StatechartModelMixin` model::

        class OrderViewSet(StatechartViewSetMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
            queryset = Order.objects.all()
            serializer_class = OrderSerializer
            permission_classes = [IsAuthenticated]

    Attributes:
        xsm_event_serializers: ``{EVENT: SerializerClass}`` validating that
            event's payload (422 on failure; `event_serializer` builds one
            from fields or a pydantic model).
        xsm_context_serializer: ``(context) -> JSON`` to include context in
            response bodies (X0.1: off by default). A receipt stores state
            ids, not context: an ``Idempotency-Key`` replay renders the
            ORIGINAL ``state`` / ``state_ids`` but the row's CURRENT
            context.
        Idempotency-Key with ``xsm_inbox = None`` is ignored (no dedup).
        xsm_inbox: An `InboxStore` for ``Idempotency-Key``; default a
            `DjangoInbox` (joins the send's transaction); ``None`` = off.
        xsm_history_permission_classes: Checked for ``history/`` (default
            `StatechartHistoryPermission`: the model's ``view`` perm).
        xsm_history_filter_backends: Filter backends for ``history/``;
            ``None`` (default) = the view's ``filter_backends``.
        xsm_lock: Lock mode for sends (default: the model's).
        xsm_stream_poll_s / xsm_stream_max_s / xsm_heartbeat_s: SSE.
    """

    xsm_event_serializers: Dict[str, Any] = {}
    xsm_context_serializer: Optional[Callable[[Any], Any]] = None
    xsm_inbox: Any = "default"
    xsm_history_permission_classes: Any = (StatechartHistoryPermission,)
    xsm_history_filter_backends: Any = None
    xsm_lock: Optional[str] = None
    xsm_stream_poll_s: float = 0.5
    xsm_stream_max_s: float = 300.0
    xsm_heartbeat_s: float = 15.0
    #: Re-check permissions every N polls of `stream/` (M4).
    xsm_stream_recheck_every: int = 10

    #: The event being handled (read by `StatechartEventPermission`).
    xsm_event: Optional[str] = None

    # -- class construction --------------------------------------------------------
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        model = cls._xsm_model()
        if model is None:
            return  # an abstract intermediate base
        cls._xsm_check_permissions()
        events = declared_events(model.statechart_class_machine())
        slugs: Dict[str, str] = {}
        for event in events:
            slug = event_slug(event)
            if slug in RESERVED or slug in slugs:
                raise ImproperlyConfigured(
                    f"{cls.__name__}: event {event!r} maps to URL "
                    f"{slug!r}, which is reserved or taken by "
                    f"{slugs.get(slug, slug)!r}"
                )
            slugs[slug] = event
            attr = "xsm_event_" + slug.replace("-", "_")
            if attr not in cls.__dict__:
                setattr(cls, attr, _event_action(event, slug, cls))

    @classmethod
    def _xsm_model(cls) -> Any:
        explicit = getattr(cls, "statechart_model", None)
        if explicit is not None:
            return explicit
        qs = cls.__dict__.get("queryset")
        if qs is None:
            for base in cls.__mro__[1:]:
                if (
                    "queryset" in base.__dict__
                    and base.__dict__["queryset"] is not None
                ):
                    qs = base.__dict__["queryset"]
                    break
        return getattr(qs, "model", None)

    @classmethod
    def _xsm_check_permissions(cls) -> None:
        for klass in cls.__mro__:
            mod = getattr(klass, "__module__", "") or ""
            if klass is StatechartViewSetMixin or mod.startswith(
                "rest_framework"
            ):
                continue
            if "permission_classes" in klass.__dict__:
                return
        raise ImproperlyConfigured(
            f"{cls.__name__} must set permission_classes explicitly -- the "
            f"statechart API is closed by default (X0.1). Use "
            f"[IsAuthenticated], a custom policy, or [AllowAny] if you "
            f"really mean it."
        )

    # -- helpers ----------------------------------------------------------------------
    def _xsm_object(self, event: Optional[str]) -> Any:
        self.xsm_event = event
        return self.get_object()  # type: ignore[attr-defined]

    def _xsm_principal(self, request: Any) -> Optional[str]:
        """``user:<pk>`` for an authenticated user, else ``None``.

        🔐 Battle #303 review H1: this used to return the constant
        ``"anonymous"``, which pooled every unauthenticated caller into
        one idempotency scope. ``None`` means "nobody" and the send
        route answers 401 to an ``Idempotency-Key`` from nobody.
        """
        user = request.user
        pk = getattr(user, "pk", None)
        return f"user:{pk}" if pk is not None else None

    def _xsm_inbox(self, obj: Any = None) -> Any:
        inbox = self.xsm_inbox
        if inbox == "default":
            from django.db import router

            from ..django.inbox import DjangoInbox

            # 🔐 M3: the claim/mark must join the send's transaction, so
            #    it goes to the database the ROW is written to.
            model = type(obj) if obj is not None else self._xsm_model()
            using = getattr(getattr(obj, "_state", None), "db", None)
            return DjangoInbox(using=using or router.db_for_write(model))
        return inbox

    def _xsm_state(self, request: Any, obj: Any) -> Dict[str, Any]:
        return state_body(
            obj,
            user=request.user,
            context_serializer=self.xsm_context_serializer,
        )

    def _xsm_payload(self, event: str, data: Any) -> Any:
        if not isinstance(data, dict):
            if hasattr(data, "dict"):
                data = data.dict()
            else:
                return problem_response(
                    422, "Request body must be a JSON object"
                )
        payload = {k: v for k, v in data.items() if k != "type"}
        # 🔐 H1/H2: framework options and server-assigned identity fields
        #    are never client data.
        bad = reserved_keys(payload)
        if bad:
            return problem_response(
                422,
                "Reserved key in request body",
                error="ReservedKeyError",
                keys=bad,
            )
        ser_cls = self.xsm_event_serializers.get(event)
        if ser_cls is None:
            return payload
        ser = ser_cls(data=payload)
        if not ser.is_valid():
            return problem_response(
                422,
                "Invalid event payload",
                error="ValidationError",
                errors=ser.errors,
            )
        return dict(ser.validated_data)

    # -- the send path ----------------------------------------------------------------
    def xsm_send(self, request: Any, event: str, data: Any) -> Response:
        """Authorise, validate, send; map the receipt to a response."""
        obj = self._xsm_object(event)
        if not has_event_permission(
            request.user, obj, event, require_enabled=False
        ):
            return problem_response(403, "Forbidden", error="PermissionDenied")
        payload = self._xsm_payload(event, data)
        if isinstance(payload, Response):
            return payload
        plugins: List[Any] = []
        idem = request.headers.get(IDEMPOTENCY_HEADER)
        inbox = self._xsm_inbox(obj)
        if idem and inbox is not None:
            from ...persistence.idempotency import IdempotencyPlugin

            who = self._xsm_principal(request)
            if who is None:
                # 🔐 An idempotency key from nobody cannot be scoped to
                #    anyone; refusing beats pooling (X0.1 / X0.2).
                return problem_response(
                    401,
                    "Unauthenticated",
                    error="UnauthenticatedError",
                )
            payload["idempotency_key"] = idem
            plugins.append(IdempotencyPlugin(inbox, principal=lambda e: who))
        # 📝 #283 battle: the admin's confirm form records WHY; an API
        #    client could not -- `reason` is a reserved payload key (422).
        #    A header is not payload: it is the audit row's `reason`.
        reason = request.headers.get(REASON_HEADER) or None
        if reason is not None and len(reason) > MAX_REASON_CHARS:
            return problem_response(
                422,
                "Reason too long",
                error="ReasonTooLongError",
                limit=MAX_REASON_CHARS,
            )
        try:
            receipt = obj.send(
                event,
                actor=request.user,
                reason=reason,
                lock=self.xsm_lock,
                plugins=plugins,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
            status, body = problem_for_exception(exc)
            resp = Response(body, status=status)
            resp.content_type = PROBLEM_MEDIA_TYPE
            return resp
        status = receipt_to_status(receipt)
        if (
            receipt.error is not None
            and status in (409, 422)
            and receipt.duplicate
        ):
            _, body = problem_for_exception(receipt.error)
            resp = Response(body, status=status)
            resp.content_type = PROBLEM_MEDIA_TYPE
            return resp
        body = self._xsm_state(request, obj)
        # 📝 #283 battle: `state` / `state_ids` describe the RECEIPT's step
        #    (the FastAPI router's contract), not the row -- so a replayed
        #    Idempotency-Key answers with exactly the original body even
        #    after another role moved the row on. `GET /{id}/` is the
        #    row's current state. Both fields come from the same ids.
        body["state_ids"] = sorted(receipt.state_ids)
        body["state"] = value_from_ids(
            type(obj).statechart_class_machine(), receipt.state_ids
        )
        body.update(receipt_fields(receipt))
        return Response(body, status=status)

    # -- generic routes ---------------------------------------------------------------
    @_schema(
        request=SendSerializer,
        responses=_send_responses(),
        parameters=_send_parameters(),
    )
    @action(
        detail=True, methods=["post"], url_path="send", url_name="xsm-send"
    )
    def xsm_send_any(
        self, request: Any, *args: Any, **kwargs: Any
    ) -> Response:
        data = request.data
        etype = data.get("type") if isinstance(data, dict) else None
        if not isinstance(etype, str) or not etype:
            return problem_response(422, 'Body must carry a string "type"')
        model = type(self)._xsm_model()
        if etype not in declared_events(model.statechart_class_machine()):
            return problem_response(
                422, "Unknown event", error="UnknownEventError"
            )
        return self.xsm_send(request, etype, data)

    @_schema(responses={200: EventsSerializer})
    @action(
        detail=True, methods=["get"], url_path="events", url_name="xsm-events"
    )
    def xsm_events(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        obj = self._xsm_object(None)
        return Response(
            {
                "available": permitted_events(request.user, obj),
                "declared": declared_events(obj.statechart_machine_node()),
            }
        )

    @_schema(responses={200: HistorySerializer(many=True)})
    @action(
        detail=True,
        methods=["get"],
        url_path="history",
        url_name="xsm-history",
    )
    def xsm_history(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        obj = self._xsm_object(None)
        for perm_cls in self.xsm_history_permission_classes:
            perm = perm_cls()
            if not perm.has_permission(
                request, self
            ) or not perm.has_object_permission(request, self, obj):
                return problem_response(
                    403, "Forbidden", error="PermissionDenied"
                )
        qs = obj.history
        backends = self.xsm_history_filter_backends
        if backends is None:
            backends = getattr(self, "filter_backends", ())
        for backend in list(backends):
            qs = backend().filter_queryset(request, qs, self)
        page = self.paginate_queryset(qs)  # type: ignore[attr-defined]
        if page is not None:
            data = HistorySerializer(page, many=True).data
            return self.get_paginated_response(data)  # type: ignore[attr-defined]
        return Response(HistorySerializer(qs, many=True).data)

    @_schema(responses={(200, "text/event-stream"): str})
    @action(
        detail=True, methods=["get"], url_path="stream", url_name="xsm-stream"
    )
    def xsm_stream(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """Server-Sent Events: the state now, then after every committed
        change (polls the row's version). ⚠️ Holds a worker for the life
        of the stream: run it on ASGI / a threaded server."""
        obj = self._xsm_object(None)
        resp = StreamingHttpResponse(
            self._xsm_sse(request, obj), content_type="text/event-stream"
        )
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp

    def _xsm_stream_allowed(self, request: Any, obj: Any) -> bool:
        """Fresh user row + the view's permission classes on *obj*."""
        user = request.user
        try:
            fresh = type(user)._default_manager.get(pk=user.pk)
        except Exception:  # noqa: BLE001 - deleted user
            return False
        if not getattr(fresh, "is_active", True):
            return False
        request.user = fresh
        try:
            self.check_permissions(request)  # type: ignore[attr-defined]
            self.check_object_permissions(request, obj)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - PermissionDenied / NotAuth
            return False
        return True

    def _xsm_sse(self, request: Any, obj: Any) -> Iterator[str]:
        name = obj.statechart_field_obj().name
        vcol = f"{name}_version"
        mgr = type(obj)._base_manager
        seen = -1
        polls = 0
        start = last_beat = time.monotonic()
        while time.monotonic() - start < self.xsm_stream_max_s:
            polls += 1
            if polls % max(
                1, self.xsm_stream_recheck_every
            ) == 0 and not self._xsm_stream_allowed(request, obj):
                # 🔐 M4: access revoked mid-stream -> stop.
                yield 'event: error\ndata: {"status":403}\n\n'
                return
            version = (
                mgr.filter(pk=obj.pk).values_list(vcol, flat=True).first()
            )
            if version is None:
                return
            if version != seen:
                seen = version
                obj.refresh_from_db()
                body = self._xsm_state(request, obj)
                body["version"] = version
                yield f"id: {version}\nevent: state\ndata: {json.dumps(body, separators=(',', ':'), default=str)}\n\n"
                last_beat = time.monotonic()
            elif time.monotonic() - last_beat >= self.xsm_heartbeat_s:
                last_beat = time.monotonic()
                yield ": heartbeat\n\n"
            time.sleep(self.xsm_stream_poll_s)


def _event_action(event: str, slug: str, cls: Type[Any]) -> Any:
    ser = cls.xsm_event_serializers.get(event)

    def handler(
        self: Any, request: Any, *args: Any, **kwargs: Any
    ) -> Response:
        return self.xsm_send(request, event, request.data)

    handler.__name__ = "xsm_event_" + slug.replace("-", "_")
    handler.__doc__ = f"Send ``{event}`` to this object."
    handler = action(
        detail=True,
        methods=["post"],
        url_path=slug,
        url_name=f"xsm-{slug}",
    )(handler)
    return _schema(
        request=ser,
        responses=_send_responses(),
        parameters=_send_parameters(),
        operation_id=f"{cls.__name__.lower()}_{slug.replace('-', '_')}",
        description=f"Send the `{event}` event.",
    )(handler)
