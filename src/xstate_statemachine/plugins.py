# /src/xstate_statemachine/plugins.py
# -----------------------------------------------------------------------------
# 🔌 Plugin System (Observer Pattern)
# -----------------------------------------------------------------------------
# This module defines the base class for plugins, which allows for extending
# the interpreter's functionality using the "Observer" design pattern. This
# architecture provides a clean separation of concerns where cross-cutting
# logic like logging, debugging, or persistence can be added without modifying
# the core interpreter code.
#
# This design makes the system highly extensible and maintainable, allowing
# developers to "observe" the state machine's lifecycle and react accordingly.
# It is a cornerstone of the library's flexibility.
# -----------------------------------------------------------------------------
"""Provides an extensible plugin system for the state machine interpreter.

This module contains the `PluginBase` abstract class, which defines the
interface for creating new plugins, and `LoggingInspector`, a powerful,
built-in plugin for debugging state machine execution.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from __future__ import (
    annotations,
)  # Enables postponed evaluation of type annotations
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Set,
    TypeVar,
)  # Core typing utilities

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .logger import logger  # Centralized logger instance

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for Forward References
# -----------------------------------------------------------------------------
# This `if TYPE_CHECKING:` block prevents circular import errors at runtime
# by only importing types for static analysis. This is a standard Python
# practice for creating type-safe, decoupled modules.
if TYPE_CHECKING:
    from .base_interpreter import BaseInterpreter
    from .events import Event
    from .models import (
        ActionDefinition,
        InvokeDefinition,
        StateNode,
        TransitionDefinition,
    )

# -----------------------------------------------------------------------------
# 🔹 Type Variable for Generic Plugin
# -----------------------------------------------------------------------------
# This TypeVar is key to a fully type-safe plugin system. It allows a plugin
# to be defined for a specific `BaseInterpreter` subclass (e.g., `AsyncInterpreter`
# or `SyncInterpreter`), enabling precise autocompletion and static analysis
# in the developer's IDE.
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter[Any, Any]")


# -----------------------------------------------------------------------------
# 🏛️ Base Plugin Class (The "Observer" Interface)
# -----------------------------------------------------------------------------
class PluginBase(Generic[TInterpreter]):
    """Abstract base class for creating an interpreter plugin.

    Plugins hook into the interpreter's lifecycle to add features like logging,
    debugging, or persistence. This class implements the "Observer" design
    pattern, where each method represents a different event in the interpreter's
    lifecycle that can be "observed."

    Subclasses should override the methods they are interested in. This class
    is generic, enabling plugins to be type-safe with the specific interpreter
    they are designed to work with.

    Example:
        A simple plugin that prints events and only works with the async `Interpreter`.

        >>> from xstate_statemachine import Interpreter, PluginBase, Event
        >>>
        >>> class AsyncEventDebugger(PluginBase[Interpreter]):
        ...     def on_event_received(self, interpreter: Interpreter, event: Event):
        ...         # `interpreter` is correctly typed as `Interpreter`,
        ...         # enabling full IDE autocompletion for async-specific methods.
        ...         print(f"🕵️ Async event received: {event.type}")
    """

    def on_interpreter_start(self, interpreter: TInterpreter) -> None:
        """Called when the interpreter's `start()` method begins.

        This hook is useful for setup tasks, such as connecting to a
        database, initializing a metrics counter, or logging the start time.

        Args:
            interpreter: The interpreter instance that has been started.
        """
        pass  # pragma: no cover

    def on_interpreter_stop(self, interpreter: TInterpreter) -> None:
        """Called when the interpreter's `stop()` method begins.

        This hook is useful for teardown tasks, like flushing log buffers,
        closing network connections, or calculating total run time.

        Args:
            interpreter: The interpreter instance that is being stopped.
        """
        pass  # pragma: no cover

    def on_event_received(
        self, interpreter: TInterpreter, event: "Event"
    ) -> None:
        """Called immediately after an event is passed to the interpreter.

        This hook allows for inspecting raw events before they are processed,
        which can be useful for debugging event sources or data payloads.

        Args:
            interpreter: The interpreter instance receiving the event.
            event: The `Event` object that was received.
        """
        pass  # pragma: no cover

    def on_transition(
        self,
        interpreter: TInterpreter,
        from_states: Set["StateNode"],
        to_states: Set["StateNode"],
        transition: "TransitionDefinition",
    ) -> None:
        """Called after a successful state transition has completed.

        This hook fires after states have been exited, actions executed, and
        new states entered. It provides a complete snapshot of the change,
        which is ideal for state-based analytics or detailed logging.

        Args:
            interpreter: The interpreter instance.
            from_states: A set of `StateNode` objects that were active before
                the transition.
            to_states: A set of `StateNode` objects that are active after the
                transition.
            transition: The `TransitionDefinition` that was taken.
        """
        pass  # pragma: no cover

    def on_action_execute(
        self, interpreter: TInterpreter, action: "ActionDefinition"
    ) -> None:
        """Called right before an action's implementation is executed.

        This allows for inspection or logging of which specific actions are
        being run as part of a transition or state entry/exit event.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` of the action about to be executed.
        """
        pass  # pragma: no cover

    def on_guard_evaluated(
        self,
        interpreter: TInterpreter,
        guard_name: str,
        event: "Event",
        result: bool,
    ) -> None:
        """Called after a guard condition has been evaluated.

        This is useful for debugging why certain transitions are (or are not)
        being taken based on the current context and event.

        Args:
            interpreter: The interpreter instance.
            guard_name: The name of the guard function that was evaluated.
            event: The event that triggered the guard evaluation.
            result: The boolean result (`True` if passed, `False` if failed).
        """
        pass  # pragma: no cover

    def on_service_start(
        self, interpreter: TInterpreter, invocation: "InvokeDefinition"
    ) -> None:
        """Called when an invoked service is about to start.

        Args:
            interpreter: The interpreter instance.
            invocation: The `InvokeDefinition` of the service about to start.
        """
        pass  # pragma: no cover

    def on_service_done(
        self,
        interpreter: TInterpreter,
        invocation: "InvokeDefinition",
        result: Any,
    ) -> None:
        """Called when an invoked service completes successfully.

        Args:
            interpreter: The interpreter instance.
            invocation: The `InvokeDefinition` of the service that completed.
            result: The data returned by the completed service.
        """
        pass  # pragma: no cover

    def on_service_error(
        self,
        interpreter: TInterpreter,
        invocation: "InvokeDefinition",
        error: Exception,
    ) -> None:
        """Called when an invoked service fails with an error.

        Args:
            interpreter: The interpreter instance.
            invocation: The `InvokeDefinition` of the service that failed.
            error: The `Exception` object raised by the service.
        """
        pass  # pragma: no cover


# -----------------------------------------------------------------------------
# 🕵️ Built-in Logging Plugin
# -----------------------------------------------------------------------------
class LoggingInspector(PluginBase[Any]):
    """A built-in plugin for detailed, real-time inspection of a machine.

    This plugin provides clear, emoji-prefixed logs for events, transitions,
    and action executions, making it invaluable for debugging complex state
    machines. It serves as a canonical example of how to implement a
    `PluginBase` subclass. It uses `Generic[Any]` to work with both the
    sync and async interpreters.
    """

    def on_event_received(
        self, interpreter: "BaseInterpreter[Any, Any]", event: "Event"
    ) -> None:
        """Logs received events in a type-safe manner.

        This implementation is carefully designed to never raise a `TypeError`
        when an event's payload is a primitive type (like `str`, `int`, or
        `None`). It safely accesses the correct data attribute based on the
        event's structure.

        Args:
            interpreter: The interpreter instance receiving the event.
            event: The `Event` object that was received.
        """
        # 1️⃣ Safely determine what data to log from the event.
        #    For a standard `Event`, the data is in the `payload` attribute.
        if hasattr(event, "payload"):
            data_to_log = event.payload
        #    For internal events like `DoneEvent` or `AfterEvent`, it's in `data`.
        else:
            data_to_log = getattr(event, "data", None)

        # 2️⃣ Compose and emit the final log message.
        message = f"🕵️ [INSPECT] Event Received: {event.type}"
        if data_to_log is not None:
            message += f" | Data: {data_to_log}"
        logger.info(message)

    def on_transition(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        from_states: Set["StateNode"],
        to_states: Set["StateNode"],
        transition: "TransitionDefinition",
    ) -> None:
        """Logs the state change and the new context after a transition.

        It formats the state IDs for clear readability and intelligently handles
        both external (state-changing) and internal (action-only) transitions.

        Args:
            interpreter: The interpreter instance.
            from_states: The set of `StateNode` objects active before the transition.
            to_states: The set of `StateNode` objects active after the transition.
            transition: The `TransitionDefinition` that was taken.
        """
        # 🍃 Extract leaf state IDs for clean and concise logging.
        from_ids = {s.id for s in from_states if s.is_atomic or s.is_final}
        to_ids = {s.id for s in to_states if s.is_atomic or s.is_final}

        #  зовнішній (External) transition: A state change occurred.
        if from_ids != to_ids:
            logger.info(
                "🕵️ [INSPECT] Transition: %s -> %s on Event '%s'",
                sorted(list(from_ids)),
                sorted(list(to_ids)),
                transition.event,
            )
            logger.info("🕵️ [INSPECT] New Context: %s", interpreter.context)
        # внутрішній (Internal) transition: No state change, but actions ran.
        elif transition.actions:
            logger.info(
                "🕵️ [INSPECT] Internal transition on Event '%s'",
                transition.event,
            )
            logger.info("🕵️ [INSPECT] New Context: %s", interpreter.context)

    def on_action_execute(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        action: "ActionDefinition",
    ) -> None:
        """Logs the name of each action right before it is executed.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` of the action to be run.
        """
        logger.info("🕵️ [INSPECT] Executing Action: %s", action.type)

    def on_guard_evaluated(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        guard_name: str,
        event: "Event",
        result: bool,
    ) -> None:
        """Logs the result of a guard evaluation.

        Args:
            interpreter: The interpreter instance.
            guard_name: The name of the guard function.
            event: The event that triggered the evaluation.
            result: The boolean result of the guard.
        """
        # ✅ Determine the outcome for logging.
        outcome = "✅ Passed" if result else "❌ Failed"
        logger.info(
            "🕵️ [INSPECT] Guard '%s' evaluated for event '%s' -> %s",
            guard_name,
            event.type,
            outcome,
        )

    def on_service_start(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        invocation: "InvokeDefinition",
    ) -> None:
        """Logs when an invoked service is about to start.

        Args:
            interpreter: The interpreter instance.
            invocation: The definition of the service being invoked.
        """
        logger.info(
            "🚀 [INSPECT] Service '%s' (ID: %s) starting...",
            invocation.src,
            invocation.id,
        )

    def on_service_done(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        invocation: "InvokeDefinition",
        result: Any,
    ) -> None:
        """Logs when an invoked service completes successfully.

        Args:
            interpreter: The interpreter instance.
            invocation: The definition of the completed service.
            result: The data returned by the service.
        """
        logger.info(
            "✅ [INSPECT] Service '%s' (ID: %s) completed. Result: %s",
            invocation.src,
            invocation.id,
            result,
        )

    def on_service_error(
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        invocation: "InvokeDefinition",
        error: Exception,
    ) -> None:
        """Logs when an invoked service fails with an error.

        Args:
            interpreter: The interpreter instance.
            invocation: The definition of the failed service.
            error: The exception raised by the service.
        """
        logger.error(
            "❌ [INSPECT] Service '%s' (ID: %s) failed. Error: %s",
            invocation.src,
            invocation.id,
            error,
            exc_info=True,  # 🐛 Include full traceback for debugging.
        )
