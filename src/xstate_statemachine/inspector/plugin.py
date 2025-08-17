# src/xstate_statemachine/inspector/plugin.py
try:
    import json
    from datetime import datetime, UTC
    from copy import deepcopy
    from typing import Any, Dict, Set
except ImportError:
    raise ImportError(
        "The 'inspector' feature requires additional dependencies. "
        "Please install them with 'pip install xstate-statemachine[inspector]'"
    )

from ..plugins import PluginBase
from ..events import Event
from ..models import (
    StateNode,
    TransitionDefinition,
    ActionDefinition,
    InvokeDefinition,
)
from ..base_interpreter import BaseInterpreter

from .server import (
    active_interpreters,
    _active_interpreters_lock,
    start_inspector_server,
    message_queue,
)
from .db import get_session, EventLog


def _get_leaf_state_ids(states: Set[StateNode]) -> Set[str]:
    """Helper to get a set of atomic or final state IDs from StateNode objects."""
    return {s.id for s in states if s.is_atomic or s.is_final}


class InspectorPlugin(PluginBase[Any]):
    """
    A plugin that inspects a state machine and sends the data to a web UI.
    """

    def __init__(self, session_factory=None):
        start_inspector_server()
        self._contexts: Dict[str, Any] = {}  # Store context per machine_id
        self.session_factory = session_factory or get_session

    def _handle_inspection_event(
        self,
        event_type: str,
        interpreter: BaseInterpreter,
        payload: Dict[str, Any],
    ):
        """
        Central handler for all inspection events. It formats the message,
        queues it for broadcast, and stores it in the database.
        """
        message = {
            "type": event_type,
            "machine_id": interpreter.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        # Use a compact JSON representation for efficiency
        json_message = json.dumps(message, default=str, separators=(",", ":"))

        # Queue for WebSocket broadcast
        message_queue.put(json_message)

        # Store in database
        with self.session_factory() as session:
            log_entry = EventLog(
                session_id=interpreter.id,
                event_type=event_type,
                data=json_message,  # Store the raw JSON message for easy playback
            )
            session.add(log_entry)
            session.commit()

    def on_interpreter_start(self, interpreter: BaseInterpreter):
        with _active_interpreters_lock:
            active_interpreters[interpreter.id] = interpreter
        self._contexts[interpreter.id] = deepcopy(interpreter.context)

        # Send a rich payload with the full definition for the frontend
        self._handle_inspection_event(
            "machine_registered",
            interpreter,
            {
                "machine_id": interpreter.id,
                "initial_state_ids": list(
                    _get_leaf_state_ids(interpreter._active_state_nodes)
                ),
                "initial_context": interpreter.context,
                "definition": interpreter.machine.to_dict(),
            },
        )

    def on_interpreter_stop(self, interpreter: BaseInterpreter):
        with _active_interpreters_lock:
            active_interpreters.pop(interpreter.id, None)

    def on_event_received(self, interpreter: BaseInterpreter, event: Event):
        # Store the context before it's potentially modified by the transition
        self._contexts[interpreter.id] = deepcopy(interpreter.context)
        self._handle_inspection_event(
            "event_received",
            interpreter,
            {"event_type": event.type, "payload": event.payload},
        )

    def on_transition(
        self,
        interpreter: BaseInterpreter,
        from_states: Set[StateNode],
        to_states: Set[StateNode],
        transition: TransitionDefinition,
    ):
        # The frontend only needs the destination leaf states and new context
        self._handle_inspection_event(
            "transition",
            interpreter,
            {
                "to_state_ids": list(_get_leaf_state_ids(to_states)),
                "event": transition.event,
                "full_context": interpreter.context,
            },
        )
        # Update the stored context
        self._contexts[interpreter.id] = deepcopy(interpreter.context)

    def on_action_execute(
        self, interpreter: BaseInterpreter, action: ActionDefinition
    ):
        self._handle_inspection_event(
            "action_executed", interpreter, {"action": action.type}
        )

    def on_guard_evaluated(
        self,
        interpreter: BaseInterpreter,
        guard_name: str,
        event: Event,
        result: bool,
    ):
        self._handle_inspection_event(
            "guard_evaluated",
            interpreter,
            {"guard": guard_name, "event": event.type, "result": result},
        )

    def on_service_start(
        self, interpreter: BaseInterpreter, invocation: InvokeDefinition
    ):
        # Send an event for both the log and to add the service to the UI list
        self._handle_inspection_event(
            "service_started",  # Generic event for the log
            interpreter,
            {"service": invocation.src, "id": invocation.id},
        )
        self._handle_inspection_event(
            "service_invoked",  # Specific event for the UI state
            interpreter,
            {"service": invocation.src, "id": invocation.id},
        )

    def on_service_done(
        self,
        interpreter: BaseInterpreter,
        invocation: InvokeDefinition,
        result: Any,
    ):
        try:
            json.dumps(result)
            serializable_result = result
        except (TypeError, OverflowError):
            serializable_result = str(result)

        # Log the specific result
        self._handle_inspection_event(
            "service_done",
            interpreter,
            {
                "service": invocation.src,
                "id": invocation.id,
                "result": serializable_result,
            },
        )
        # Tell the UI to remove the service from the active list
        self._handle_inspection_event(
            "service_stopped", interpreter, {"id": invocation.id}
        )

    def on_service_error(
        self,
        interpreter: BaseInterpreter,
        invocation: InvokeDefinition,
        error: Exception,
    ):
        # Log the specific error
        self._handle_inspection_event(
            "service_error",
            interpreter,
            {
                "service": invocation.src,
                "id": invocation.id,
                "error": str(error),
            },
        )
        # Tell the UI to remove the service from the active list
        self._handle_inspection_event(
            "service_stopped", interpreter, {"id": invocation.id}
        )
