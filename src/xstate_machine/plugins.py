# src/xstate_machine/plugins.py
from __future__ import annotations

from typing import TYPE_CHECKING, Set

from .events import Event
from .logger import logger

if TYPE_CHECKING:
    from .interpreter import Interpreter
    from .models import ActionDefinition, StateNode, TransitionDefinition


# -----------------------------------------------------------------------------
# 🔗 Plugin Architecture
# -----------------------------------------------------------------------------
# This module provides the base class for creating plugins that can hook into
# the interpreter's lifecycle. This follows the Observer and Strategy design
# patterns, allowing for a clean separation of concerns where cross-cutting
# logic like logging, debugging, or persistence can be added without modifying
# the core interpreter. This makes the system highly extensible and maintainable.
# -----------------------------------------------------------------------------


class PluginBase:
    """Abstract base class for creating an interpreter plugin.

    Plugins can hook into various lifecycle events of the interpreter
    to add logging, debugging, persistence, or other custom features. Subclasses
    should override the methods they are interested in.
    """

    def on_interpreter_start(self, interpreter: "Interpreter") -> None:
        """Called when the interpreter's `start()` method is first initiated.

        This hook is useful for setup tasks or for logging the beginning of a
        machine's lifecycle.

        Args:
            interpreter: The interpreter instance that has been started.
        """
        pass

    def on_interpreter_stop(self, interpreter: "Interpreter") -> None:
        """Called when the interpreter's `stop()` method is initiated.

        This hook is useful for teardown tasks or for logging the end of a
        machine's lifecycle.

        Args:
            interpreter: The interpreter instance that is being stopped.
        """
        pass

    def on_event_received(
        self, interpreter: "Interpreter", event: Event
    ) -> None:
        """Called immediately after an event is received, before processing.

        This provides a look at the raw event that is about to trigger a
        potential state transition.

        Args:
            interpreter: The interpreter instance processing the event.
            event: The `Event` object that was received.
        """
        pass

    def on_transition(
        self,
        interpreter: "Interpreter",
        from_states: Set["StateNode"],
        to_states: Set["StateNode"],
        transition: "TransitionDefinition",
    ) -> None:
        """Called after a successful state transition has completed.

        This hook fires after states have been exited, actions executed, and
        new states have been entered. It provides a complete picture of the
        change that occurred.

        Args:
            interpreter: The interpreter instance.
            from_states: A set of `StateNode`s that were active before the transition.
            to_states: A set of `StateNode`s that are active after the transition.
            transition: The `TransitionDefinition` that was taken.
        """
        pass

    def on_action_execute(
        self, interpreter: "Interpreter", action: "ActionDefinition"
    ) -> None:
        """Called right before an action is executed.

        This allows for inspection of which actions are being run as part of a
        transition or state entry/exit.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` of the action about to be executed.
        """
        pass


class LoggingInspector(PluginBase):
    """A built-in plugin for detailed, real-time inspection of a machine.

    This provides clear, emoji-prefixed logs for events, transitions, and
    action executions, making it invaluable for debugging complex state machines.
    It serves as a canonical example of how to implement a plugin.
    """

    def on_event_received(
        self, interpreter: "Interpreter", event: Event
    ) -> None:
        """Logs the details of every event processed by the machine.

        This method robustly handles different event structures (like `Event`
        and `DoneEvent`) to prevent errors during inspection.

        Args:
            interpreter: The interpreter instance processing the event.
            event: The `Event` object that was received.
        """
        # ✨ FIX: Safely access event data to handle different event types.
        # Use getattr to check for a 'payload' attribute, falling back to 'data',
        # and then to None if neither exists. This makes the logger robust.
        data_or_payload = getattr(
            event, "payload", getattr(event, "data", None)
        )

        log_message = f"🕵️ [INSPECT] Event Received: {event.type}"
        if data_or_payload is not None:
            log_message += f" | Data: {data_or_payload}"

        logger.info(log_message)

    def on_transition(
        self,
        interpreter: "Interpreter",
        from_states: Set["StateNode"],
        to_states: Set["StateNode"],
        transition: "TransitionDefinition",
    ) -> None:
        """Logs the state change and the new context after a transition.

        It formats the state IDs for clear readability and only logs if an
        actual state change has occurred.

        Args:
            interpreter: The interpreter instance.
            from_states: The set of `StateNode`s active before the transition.
            to_states: The set of `StateNode`s active after the transition.
            transition: The `TransitionDefinition` that was taken.
        """
        from_ids = {s.id for s in from_states if s.is_atomic or s.is_final}
        to_ids = {s.id for s in to_states if s.is_atomic or s.is_final}

        # ✅ Only log if a state change actually happened.
        if from_ids != to_ids:
            logger.info(
                f"🕵️ [INSPECT] Transition: {from_ids} -> {to_ids} on Event '{transition.event}'"
            )
            logger.info(f"🕵️ [INSPECT] New Context: {interpreter.context}")
        # For internal transitions, we also log the context change if any.
        elif transition.actions:
            logger.info(
                f"🕵️ [INSPECT] Internal transition on '{transition.event}'. Context may have changed."
            )
            logger.info(f"🕵️ [INSPECT] New Context: {interpreter.context}")

    def on_action_execute(
        self, interpreter: "Interpreter", action: "ActionDefinition"
    ) -> None:
        """Logs the name of each action right before it is executed.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` of the action to be run.
        """
        logger.info(f"🕵️ [INSPECT] Executing Action: {action.type}")
