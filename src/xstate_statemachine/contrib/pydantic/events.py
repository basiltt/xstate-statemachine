# src/xstate_statemachine/contrib/pydantic/events.py
"""Typed events: `EventModel` + `events_union()` (#266)."""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Type,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, ValidationError

from ._scrub import scrub

__all__ = ["EventModel", "events_union", "event_type_of", "models_of"]


class EventModel(BaseModel):
    """Base for a typed event: ``type: Literal["PAY"]`` plus payload fields.

    An instance IS an event -- it implements the `__xstate_event__`
    adapter protocol (#305), so ``interp.send(Pay(amount=10))`` works on
    every send path of both engines: the ``type`` field is the event type
    and every other field (dumped in Python mode, so `Decimal` stays a
    `Decimal`) is the payload.

    ::

        class Pay(EventModel):
            type: Literal["PAY"] = "PAY"
            amount: Decimal
            method: Literal["card", "bank"] = "card"
    """

    model_config = ConfigDict(extra="forbid")

    type: str

    def __xstate_event__(self) -> Dict[str, Any]:
        data = self.model_dump(mode="python")
        return data  # includes "type" -- exactly the dict form send() takes

    @classmethod
    def event_type(cls) -> str:
        """The literal ``type`` this model declares (or its default)."""
        t = event_type_of(cls)
        if t is None:
            raise TypeError(
                f"{cls.__name__}.type must be a Literal[...] with one value "
                f"(or have a default) so it can be registered as a schema"
            )
        return t


def event_type_of(model: Type[BaseModel]) -> Optional[str]:
    """The single literal ``type`` value of *model*, else its default."""
    field = model.model_fields.get("type")
    if field is None:
        return None
    ann = field.annotation
    if get_origin(ann) is not None:
        args = get_args(ann)
        # Literal["PAY"] -> ("PAY",); Optional[Literal[...]] etc. are not
        # a single type and fall through to the default.
        if len(args) == 1 and isinstance(args[0], str):
            return args[0]
    default = field.default
    return default if isinstance(default, str) else None


def _validator_for(
    model: Type[EventModel], event_type: str
) -> Callable[[Any], None]:
    def _validate(payload: Any) -> None:
        data = dict(payload or {})
        data.setdefault("type", event_type)
        # 📝 `idempotency_key` is transport metadata the inbox (#261) reads
        #    (the HTTP `Idempotency-Key` header lands here), not a field of
        #    the event -- an `extra="forbid"` model must not reject it.
        data.pop("idempotency_key", None)
        # A pydantic ValidationError propagates as-is: the engine wraps it
        # in `InvalidEventPayloadError` (#51) with the structured
        # `.errors()` reachable through `.cause`.
        # 🔥 #266 battle (X0.5): re-raised SCRUBBED and unchained -- the
        #    raw error's text carries `input_value=<the card number>` and
        #    `InvalidEventPayloadError` embeds `str(cause)` in its message.
        try:
            model.model_validate(data)
        except ValidationError as exc:
            raise scrub(exc) from None

    _validate.__name__ = f"validate_{model.__name__}"
    _validate.__xsm_event_model__ = model  # type: ignore[attr-defined]
    return _validate


def events_union(
    *models: Type[EventModel],
) -> Dict[str, Callable[[Any], None]]:
    """Build the ``event_schemas=`` mapping for `create_machine()` from
    `EventModel` subclasses -- one validator per declared ``type``.

    ::

        machine = create_machine(cfg, event_schemas=events_union(Pay, Cancel))

    A payload that does not fit raises `InvalidEventPayloadError` at the
    `send()` call site (the existing #51 path) with the pydantic
    `ValidationError` as ``cause``. Two models declaring the same ``type``
    is a `TypeError` -- a discriminated union needs unique discriminators.
    Each validator remembers its model, so `machine_json_schema` can
    rebuild the discriminated union from the mapping.
    """
    out: Dict[str, Callable[[Any], None]] = {}
    seen: Dict[str, Type[EventModel]] = {}
    for model in models:
        if not (isinstance(model, type) and issubclass(model, EventModel)):
            raise TypeError(
                f"events_union() takes EventModel subclasses, got {model!r}"
            )
        et = model.event_type()
        if et in seen:
            raise TypeError(
                f"event type {et!r} declared by both {seen[et].__name__} and "
                f"{model.__name__}; discriminators must be unique"
            )
        seen[et] = model
        out[et] = _validator_for(model, et)
    return out


def models_of(schemas: Any) -> Tuple[Type[EventModel], ...]:
    """The `EventModel`s behind an `events_union()` mapping (each validator
    carries its model), in declaration order."""
    if not isinstance(schemas, dict):
        return ()
    found = []
    for v in schemas.values():
        m = getattr(v, "__xsm_event_model__", None)
        if m is not None:
            found.append(m)
    return tuple(found)
