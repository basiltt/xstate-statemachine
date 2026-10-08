# src/xstate_statemachine/contrib/drf/fields.py
"""`StatechartSerializerField` and `event_serializer`."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from rest_framework import serializers

from ..django._events import available_events

__all__ = ["StatechartSerializerField", "event_serializer", "state_body"]


def state_body(
    instance: Any,
    *,
    user: Any = None,
    context_serializer: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """The FastAPI ``GET /{id}`` body shape for a model instance::

        {"state", "state_ids", "available_events", "machine_version"
         [, "context"]}

    ``state`` is the XState value; ``available_events`` are the events
    *user* may send now (`permitted_events`) or, without a user, the ones
    `can()` allows. Context only through *context_serializer* (X0.1).
    """
    interp = instance.machine
    if user is not None:
        from ..django.permissions import permitted_events

        events = permitted_events(user, instance)
    else:
        events = available_events(interp)
    body: Dict[str, Any] = {
        "state": interp.value,
        "state_ids": sorted(interp.current_state_ids),
        "available_events": events,
        "machine_version": interp.machine.version or None,
    }
    if context_serializer is not None:
        body["context"] = context_serializer(interp.context)
    return body


def _state_schema(cls: Any) -> Any:
    """📝 #283 battle: without this drf-spectacular typed the field as
    ``string``; it is the state-body object (FastAPI ``StateModel``)."""
    try:
        from drf_spectacular.utils import extend_schema_field
    except ImportError:  # pragma: no cover - [drf] without spectacular
        return cls
    return extend_schema_field(
        {
            "type": "object",
            "readOnly": True,
            "required": [
                "state",
                "state_ids",
                "available_events",
                "machine_version",
            ],
            "properties": {
                "state": {},
                "state_ids": {"type": "array", "items": {"type": "string"}},
                "available_events": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "machine_version": {"type": "string", "nullable": True},
                "context": {},
            },
        }
    )(cls)


@_state_schema
class StatechartSerializerField(serializers.Field):
    """Read-only: the statechart of the instance as the FastAPI state body.

    Args:
        context_serializer: ``(context) -> JSON``; without it the context
            is NOT included (X0.1).
        per_user: Report ``available_events`` as ``request.user`` sees
            them (default ``True`` when the serializer has a request).
    """

    def __init__(
        self,
        *,
        context_serializer: Optional[Callable[[Any], Any]] = None,
        per_user: bool = True,
        **kw: Any,
    ) -> None:
        kw["read_only"] = True
        kw.setdefault("source", "*")
        super().__init__(**kw)
        self.context_serializer = context_serializer
        self.per_user = per_user

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        request = self.context.get("request") if self.context else None
        user = getattr(request, "user", None) if self.per_user else None
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None
        return state_body(
            instance, user=user, context_serializer=self.context_serializer
        )


def event_serializer(
    event: str, fields: Optional[Dict[str, Any]] = None, *, model: Any = None
) -> Any:
    """A ``Serializer`` class for *event*'s payload: from plain DRF
    *fields*, or from a pydantic *model* (A9) validated in ``validate``."""
    attrs: Dict[str, Any] = dict(fields or {})
    if model is not None:

        def validate(self: Any, data: Any) -> Any:
            try:
                raw = dict(self.initial_data)
                raw.pop("type", None)
                return model.model_validate(raw).model_dump(mode="json")
            except Exception as exc:  # noqa: BLE001 - pydantic error
                raise serializers.ValidationError(
                    {"payload": [type(exc).__name__]}
                ) from None

        attrs["validate"] = validate
    return type(
        f"{event.title().replace('_', '')}Serializer",
        (serializers.Serializer,),
        attrs,
    )
