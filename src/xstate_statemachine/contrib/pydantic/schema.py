# src/xstate_statemachine/contrib/pydantic/schema.py
"""`machine_json_schema()` -- JSON Schema for a machine's events, context
and state ids, for frontend teams and OpenAPI (#266)."""

from __future__ import annotations

from typing import (
    Annotated,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseModel, Field, create_model

from ...validation import walk
from .events import EventModel, event_type_of, models_of

__all__ = ["machine_json_schema"]

_REF = "#/$defs/{model}"


def _leaf_and_all_ids(machine: Any) -> Tuple[List[str], List[str]]:
    """(every state id, the ids that can be ACTIVE leaves).

    📝 #266 battle (B): a history pseudo-state has no children, so it was
    listed in ``x-leaf-states`` -- but it is never active and never
    appears in ``current_state_ids``. It stays in the ``enum`` (it IS a
    state id of the chart; ``#id`` targets may name it).
    """
    nodes = list(walk(machine))
    all_ids = sorted(n.id for n in nodes)
    leaves = sorted(
        n.id for n in nodes if not n.states and n.type != "history"
    )
    return all_ids, leaves


def _event_type(models: Tuple[Type[EventModel], ...]) -> Any:
    """The annotation for the ``event`` property: one model, or a union
    discriminated on ``type`` (pydantic emits ``oneOf`` + mapping)."""
    if len(models) == 1:
        return models[0]
    for m in models:
        if event_type_of(m) is None:
            # 📝 #266 battle (B): escaped as a bare PydanticUserError.
            raise TypeError(
                f"{m.__name__}.type must be a Literal[...] with one value "
                f"to take part in a discriminated event union"
            )
    return Annotated[
        Union[models],  # Union[tuple] is the runtime-built union
        Field(discriminator="type"),
    ]


def machine_json_schema(
    machine: Any,
    *,
    events: Optional[Iterable[Type[EventModel]]] = None,
    context_model: Optional[Type[BaseModel]] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """A JSON Schema (draft 2020-12, as pydantic emits) describing what a
    client may SEND and what it will READ back.

    Returns an object schema with ``$defs`` and three top-level properties:

    * ``event`` -- a discriminated union (``oneOf`` on ``type``) of the
      given `EventModel`s (default: the models behind the machine's
      ``event_schemas``, when built by `events_union`);
    * ``context`` -- the context model's schema (omitted when none);
    * ``state`` -- an ``enum`` of every state id in the chart, plus
      ``x-leaf-states`` listing the leaves that can be active (history
      pseudo-states excluded).

    The document round-trips through ``json`` and carries
    ``x-machine-id`` / ``x-machine-version`` / ``x-machine-hash`` so a
    consumer can detect which chart revision it was generated from.

    📝 ``Decimal`` fields appear as ``anyOf: [number, string]`` (pydantic's
    serialisation schema accepts both) -- send money as a string to keep
    precision.

    Raises:
        TypeError: when an event model in a union of two or more has no
            ``Literal`` ``type`` (it cannot be discriminated).
    """
    event_models = (
        tuple(events)
        if events is not None
        else models_of(getattr(machine, "event_schemas", None))
    )
    # 🏛️ #266 battle (B): ONE schema generation for events + context. Two
    #    separate TypeAdapter passes each named their nested models from
    #    the class name alone, and `defs.update()` let a context `Item`
    #    silently replace an event's (different) `Item` -- the event's
    #    `$ref` then described the wrong shape. A single pass makes
    #    pydantic disambiguate colliding names itself.
    fields: Dict[str, Any] = {}
    if event_models:
        fields["event"] = (_event_type(event_models), ...)
    if context_model is not None:
        fields["context"] = (context_model, ...)
    props: Dict[str, Any] = {}
    defs: Dict[str, Any] = {}
    if fields:
        holder = create_model("XsmMachineDocument", **fields)
        whole = holder.model_json_schema(ref_template=_REF)
        defs = whole.get("$defs", {})
        for key in fields:
            prop = dict(whole["properties"][key])
            prop.pop("title", None)  # the holder's field title, not ours
            ref = prop.get("$ref")
            if set(prop) == {"$ref"} and isinstance(ref, str):
                # Keep the pre-battle shape: a single model is INLINED
                # (its def stays in `$defs` -- self-references need it).
                prop = dict(defs[ref.rsplit("/", 1)[-1]])
            props[key] = prop

    all_ids, leaves = _leaf_and_all_ids(machine)
    props["state"] = {
        "type": "string",
        "enum": all_ids,
        "x-leaf-states": leaves,
        "description": "A state id of the chart (fully qualified).",
    }

    doc: Dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title or f"{machine.id} statechart",
        "type": "object",
        "properties": props,
        "x-machine-id": machine.id,
        "x-machine-version": getattr(machine, "version", None),
        "x-machine-hash": machine.structure_hash,
    }
    if defs:
        doc["$defs"] = defs
    return doc
