# src/xstate_statemachine/events.py
from typing import Any, Dict, Literal, NamedTuple


# -----------------------------------------------------------------------------
# ✉️ Event Definitions
# -----------------------------------------------------------------------------
# Standardizing event structures within the machine ensures consistency and
# clear communication between components.
# -----------------------------------------------------------------------------


class Event(NamedTuple):
    """Represents an event sent to the machine."""

    type: str
    payload: Dict[str, Any] = {}


class DoneEvent(NamedTuple):
    """
    Represents the completion of an invoked service.

    The type follows the convention 'done.invoke.<service_id>'.
    """

    type: str
    data: Any
    src: str


class AfterEvent(NamedTuple):
    """
    Represents the firing of a delayed transition.

    The type follows the convention 'after.<delay>.<state_id>'.
    """

    type: str
