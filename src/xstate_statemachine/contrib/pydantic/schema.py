# src/xstate_statemachine/contrib/pydantic/schema.py
"""`machine_json_schema()` -- JSON Schema for a machine's events, context
and state ids, for frontend teams and OpenAPI (#266)."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Type

from pydantic import BaseModel, TypeAdapter

from ...validation import walk
from .events import EventModel, models_of

__all__ = ["machine_json_schema"]


def _leaf_and_all_ids(machine: Any) -> List[str]:
    return sorted(n.id for n in walk(machine))


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
      ``x-leaf-states`` listing the leaves.

    The document round-trips through ``json`` and carries
    ``x-machine-id`` / ``x-machine-version`` / ``x-machine-hash`` so a
    consumer can detect which chart revision it was generated from.
    """
    event_models = (
        tuple(events)
        if events is not None
        else models_of(getattr(machine, "event_schemas", None))
    )
    defs: Dict[str, Any] = {}
    props: Dict[str, Any] = {}

    if event_models:
        if len(event_models) == 1:
            union_schema = TypeAdapter(event_models[0]).json_schema(
                ref_template="#/$defs/{model}"
            )
        else:
            # A discriminated union on `type`: pydantic emits oneOf +
            # discriminator mapping when given the Union directly.
            from typing import Annotated, Union

            from pydantic import Field

            U = Annotated[Union[event_models], Field(discriminator="type")]  # type: ignore[valid-type]
            union_schema = TypeAdapter(U).json_schema(
                ref_template="#/$defs/{model}"
            )
        defs.update(union_schema.pop("$defs", {}))
        props["event"] = union_schema

    if context_model is not None:
        ctx_schema = TypeAdapter(context_model).json_schema(
            ref_template="#/$defs/{model}"
        )
        defs.update(ctx_schema.pop("$defs", {}))
        props["context"] = ctx_schema

    all_ids = _leaf_and_all_ids(machine)
    leaves = sorted(n.id for n in walk(machine) if not n.states)
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
