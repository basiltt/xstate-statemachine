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
from ..models import StateNode, TransitionDefinition, ActionDefinition, InvokeDefinition
from ..base_interpreter import BaseInterpreter

from .server import start_inspector_server, message_queue
from .db import SessionLocal, EventLog


def _get_state_ids(states: Set[StateNode]) -> Set[str]:
    """Helper to get a set of state IDs from StateNode objects."""
    return {s.id for s in states}

class InspectorPlugin(PluginBase[Any]):
    """
    A plugin that inspects a state machine and sends the data to a web UI.
    """

    def __init__(self, session_factory=None):
        start_inspector_server()
        self._contexts: Dict[str, Any] = {}  # Store context per machine_id
        self.session_factory = session_factory or SessionLocal

    def _handle_inspection_event(
        self, event_type: str, interpreter: BaseInterpreter, payload: Dict[str, Any]
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
        json_message = json.dumps(message, default=str)

        # Queue for WebSocket broadcast
        message_queue.put(json_message)

        # Store in database
        db = self.session_factory()
        try:
            log_entry = EventLog(
                session_id=interpreter.id,
                event_type=event_type,
                data=json_message,  # Store the raw JSON message for easy playback
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()

    def on_interpreter_start(self, interpreter: BaseInterpreter):
        self._contexts[interpreter.id] = deepcopy(interpreter.context)
        self._handle_inspection_event(
            "machine_registered",
            interpreter,
            {
                "machine_id": interpreter.id,
                "initial_state": list(
                    _get_state_ids(interpreter.current_states)
                ),
                "initial_context": interpreter.context,
                "definition": interpreter.machine.to_dict(),
            },
        )

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
        old_context = self._contexts.get(interpreter.id, {})
        new_context = interpreter.context

        # Simple context diff
        context_diff = {
            "added": {
                k: new_context[k]
                for k in new_context
                if k not in old_context
            },
            "removed": {
                k: old_context[k]
                for k in old_context
                if k not in new_context
            },
            "changed": {
                k: {"old": old_context[k], "new": new_context[k]}
                for k in old_context
                if k in new_context and old_context[k] != new_context[k]
            },
        }

        self._handle_inspection_event(
            "transition",
            interpreter,
            {
                "from_states": list(_get_state_ids(from_states)),
                "to_states": list(_get_state_ids(to_states)),
                "event": transition.event,
                "context_diff": context_diff,
                "full_context": new_context,
            },
        )
        # Update the stored context
        self._contexts[interpreter.id] = deepcopy(new_context)

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
        self._handle_inspection_event(
            "service_started",
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

        self._handle_inspection_event(
            "service_done",
            interpreter,
            {
                "service": invocation.src,
                "id": invocation.id,
                "result": serializable_result,
            },
        )

    def on_service_error(
        self,
        interpreter: BaseInterpreter,
        invocation: InvokeDefinition,
        error: Exception,
    ):
        self._handle_inspection_event(
            "service_error",
            interpreter,
            {
                "service": invocation.src,
                "id": invocation.id,
                "error": str(error),
            },
        )
