# src/xstate_statemachine/events.py

# -----------------------------------------------------------------------------
# ✉️ Event System
# -----------------------------------------------------------------------------
# This module defines the core event structures used throughout the state
# machine interpreter. These immutable, typed data classes ensure consistent
# and predictable communication for external events, internal "done" events,
# and delayed "after" events.
#
# By standardizing these structures, we create a clear and maintainable
# contract for how different parts of the system interact with the state
# machine.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Imports
# -----------------------------------------------------------------------------
from typing import Any, Dict, NamedTuple


# -----------------------------------------------------------------------------
# 📨 Event Definitions
# -----------------------------------------------------------------------------
# These classes represent the different types of events that can be processed
# by the state machine interpreter. Using NamedTuples makes them lightweight,
# immutable, and self-documenting.
# -----------------------------------------------------------------------------


class Event(NamedTuple):
    """Represents a standard event sent to the state machine.

    This is the most common type of event, typically triggered by external
    inputs or user actions. It serves as the primary mechanism for driving
    state transitions.

    Attributes:
        type: The name of the event, which is used to match against
            transitions defined in the machine's `on` property.
        payload: An optional dictionary containing extra
            data associated with the event. This data is accessible to
            actions and guards.

    Example:
        >>> # An event representing a user login attempt
        >>> user_login_event = Event(type="USER_LOGIN", payload={"username": "alice"})
        >>> print(user_login_event)
        Event(type='USER_LOGIN', payload={'username': 'alice'})

        >>> # A simple event with no payload
        >>> timer_tick_event = Event(type="TICK")
        >>> print(timer_tick_event)
        Event(type='TICK', payload={})
    """

    # 🏷️ The unique identifier for the event type.
    type: str

    # 📦 A dictionary for any additional data. Defaults to an empty dict.
    payload: Dict[str, Any] = {}


class DoneEvent(NamedTuple):
    """Represents the completion of a background service or a final state.

    This event is generated internally by the interpreter when:
    1. An invoked service finishes its work successfully.
    2. A compound or parallel state reaches its final state(s).

    The event `type` follows a specific convention to avoid collisions with
    user-defined events, making it easier to target `onDone` transitions.

    Attributes:
        type: The event name, following the convention:
            - `done.invoke.<service_id>` for invoked services.
            - `done.state.<state_id>` for states reaching a final state.
        data: The data returned by the completed service or final state.
        src: The unique identifier of the service or state that
            generated this event.

    Example:
        >>> # Event from a completed 'fetchData' service
        >>> done_invoke_event = DoneEvent(
        ...     type="done.invoke.fetchData",
        ...     data={"user_id": 123, "name": "Alice"},
        ...     src="fetchData"
        ... )
        >>> print(done_invoke_event)
        DoneEvent(type='done.invoke.fetchData', data={'user_id': 123, 'name': 'Alice'}, src='fetchData')
    """

    # 🏷️ The structured name of the completion event.
    type: str

    # 📊 The data payload returned from the source.
    data: Any

    # 📍 The ID of the invoked service or state that completed.
    src: str


class AfterEvent(NamedTuple):
    """Represents a delayed event used for timed transitions.

    This event is scheduled by the interpreter when it enters a state that
    has an `after` transition defined. After the specified delay, this
    event is sent back to the machine to trigger the corresponding transition.

    Attributes:
        type: The event name, which is defined in the machine configuration
            and used to match the specific `after` transition. The interpreter
            internally maps this to a timer.

    Example:
        >>> # In a machine, an 'after' transition might be defined like:
        >>> # "after": { "2000": { "target": "idle", "actions": [...] } }
        >>> # The interpreter would create an event like this after 2 seconds.
        >>> after_event = AfterEvent(type="after.2000.myState") # Example internal type
        >>> print(after_event)
        AfterEvent(type='after.2000.myState')
    """

    # 🏷️ The structured name of the delayed event.
    type: str
