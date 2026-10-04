# src/xstate_statemachine/contrib/pydantic/__init__.py
# -----------------------------------------------------------------------------
# 🧷 [pydantic] -- typed context, typed events, config validation, schema
# -----------------------------------------------------------------------------
# 🏛️ Modern Python expects typed, validated data at every boundary; XState
#    v5's `setup()` gives TypeScript users typed context/events, and in
#    Python the idiomatic equivalent is Pydantic v2 -- the validation layer
#    the FastAPI (#277), DRF (#282) and agents (phase E) integrations all
#    reuse. "Silent acceptance is a bug": a typo'd context key or a
#    malformed payload must fail at the boundary, not deep in an action.
#
# 📝 Core never learns the word "pydantic" (review amendment). Everything
#    here plugs into seams that already exist in core:
#      * `create_machine(context_validator=)` (#305) -- `context_model()`
#        builds that callable from a BaseModel; a raise is an ACTION error,
#        so `actionErrorPolicy: rollback` keeps the machine valid.
#      * `create_machine(event_schemas=)` (#51) -- `events_union()` builds
#        the type → validator mapping from `EventModel` subclasses.
#      * `__xstate_event__` (#305) -- an `EventModel` instance IS an event.
#      * The store codec seam (#259) -- `PydanticCodec` handles `Decimal` /
#        `datetime` in snapshots, which `json.dumps` alone cannot.
# -----------------------------------------------------------------------------
"""Pydantic v2 integration.

Install with ``pip install "xstate-statemachine[pydantic]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("pydantic", "pydantic")

from .config import (  # noqa: E402
    ActionObject,
    ActionSpec,
    InvokeConfig,
    MachineConfig,
    StateConfig,
    TransitionConfig,
    validate_machine_json,
)
from .context import (  # noqa: E402
    ContextValidationError,
    PydanticCodec,
    TypedContextPlugin,
    context_model,
    context_of,
    typed_context,
)
from .events import (  # noqa: E402
    EventModel,
    event_type_of,
    events_union,
    models_of,
)
from .schema import machine_json_schema  # noqa: E402

__all__ = [
    "ActionObject",
    "ActionSpec",
    "ContextValidationError",
    "EventModel",
    "InvokeConfig",
    "MachineConfig",
    "PydanticCodec",
    "StateConfig",
    "TransitionConfig",
    "TypedContextPlugin",
    "context_model",
    "context_of",
    "event_type_of",
    "events_union",
    "machine_json_schema",
    "models_of",
    "typed_context",
    "validate_machine_json",
]
