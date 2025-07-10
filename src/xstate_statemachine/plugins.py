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
# This makes the system highly extensible and maintainable, allowing developers
# to "observe" the state machine's lifecycle and react accordingly.
# -----------------------------------------------------------------------------
"""
Provides an extensible plugin system for the state machine interpreter.

This module contains the `PluginBase` abstract class, which defines the
interface for creating new plugins, and `LoggingInspector`, a powerful,
built-in plugin for debugging.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from __future__ import (
    annotations,
)  # Enables postponed evaluation of type annotations

from typing import TYPE_CHECKING, Generic, Set, TypeVar, Any

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .logger import logger

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for Forward References
# -----------------------------------------------------------------------------
# The `if TYPE_CHECKING:` block allows us to import types for hinting
# without causing circular import errors at runtime. This is a standard
# practice for type-safe architectures with interdependent modules.
if TYPE_CHECKING:
    from .base_interpreter import BaseInterpreter
    from .events import Event
    from .models import ActionDefinition, StateNode, TransitionDefinition

# -----------------------------------------------------------------------------
# 🔹 Type Variable for Generic Plugin
# -----------------------------------------------------------------------------

# This TypeVar is the key to making the plugin system fully type-safe.
# It allows a plugin to be defined for a specific subclass of BaseInterpreter,
# such as `Interpreter` or `SyncInterpreter`, enabling precise autocompletion
# and static analysis in the developer's IDE.
# The `noqa` comment below is to suppress a linter warning about "BaseInterpreter"
# not being defined yet, which is handled by the forward reference string.
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter")  # noqa: F821


# -----------------------------------------------------------------------------
# 🏛️ Base Plugin Class (The "Observer" Interface)
# -----------------------------------------------------------------------------


class PluginBase(Generic[TInterpreter]):
    """Abstract base class for creating an interpreter plugin.

    Plugins hook into the interpreter's lifecycle to add features like logging,
    debugging, or persistence. Subclasses should override the methods they are
    interested in. This class is generic, enabling plugins to be type-safe
    with the specific interpreter (`Interpreter` or `SyncInterpreter`) they
    are designed to work with.

    Example:
        A simple plugin that only works with the async `Interpreter`.

        >>> from xstate_statemachine import Interpreter, PluginBase, Event
        >>>
        >>> class AsyncOnlyDebugger(PluginBase[Interpreter]):
        ...     def on_event_received(self, interpreter: Interpreter, event: Event):
        ...         # This plugin now has full autocompletion for the async Interpreter
        ...         print(f"Async event received: {event.type}")
    """

    def on_interpreter_start(self, interpreter: TInterpreter) -> None:
        """Hook called when the interpreter's `start()` method begins.

        This hook is useful for setup tasks, such as connecting to a
        database or initializing a metrics counter.

        Args:
            interpreter: The interpreter instance that has been started.
        """
        pass

    def on_interpreter_stop(self, interpreter: TInterpreter) -> None:
        """Hook called when the interpreter's `stop()` method begins.

        This hook is useful for teardown tasks, like flushing log buffers or
        closing network connections.

        Args:
            interpreter: The interpreter instance that is being stopped.
        """
        pass

    def on_event_received(  # noqa: D401  – imperative mood is appropriate
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        event: "Event",
    ) -> None:
        """Log an event without ever triggering ``Event.data`` errors.

        A plain ``Event`` raises a ``TypeError`` if its ``payload`` is *not*
        a ``dict`` and code accesses ``event.data``.  This version:

        1. Uses ``event.payload`` **only** when the attribute exists.
        2. Falls back to ``event.data`` for internal events
           (``DoneEvent``, ``AfterEvent``).
        3. Emits a concise log line – no helper that re-accesses ``event.data``.

        That makes the inspector safe for string, ``None``, or other primitive
        payloads and fixes the failing test cases.
        """
        # ---------------------------------------------------------------------
        # 1️⃣  Determine what we can safely display
        # ---------------------------------------------------------------------
        if hasattr(event, "payload"):  # Standard Event
            data_to_log = event.payload  # may be str / int / None / dict
        else:  # DoneEvent / AfterEvent
            data_to_log = getattr(event, "data", None)

        # ---------------------------------------------------------------------
        # 2️⃣  Build & emit the log message
        # ---------------------------------------------------------------------
        message = f"🕵️ [INSPECT] Event Received: {event.type}"
        if data_to_log is not None:
            message += f" | Data: {data_to_log}"
        logger.info(message)

    def on_transition(
        self,
        interpreter: TInterpreter,
        from_states: Set["StateNode"],
        to_states: Set["StateNode"],
        transition: "TransitionDefinition",
    ) -> None:
        """Hook called after a successful state transition has completed.

        This hook fires after states have been exited, actions executed, and
        new states have been entered. It provides a complete picture of the
        change that occurred, which is ideal for state-based analytics or
        detailed logging.

        Args:
            interpreter: The interpreter instance.
            from_states: A set of `StateNode`s that were active before the
                         transition.
            to_states: A set of `StateNode`s that are active after the
                       transition.
            transition: The `TransitionDefinition` that was taken.
        """
        pass

    def on_action_execute(
        self, interpreter: TInterpreter, action: "ActionDefinition"
    ) -> None:
        """Hook called right before an action's implementation is executed.

        This allows for inspection or logging of which specific actions are
        being run as part of a transition or state entry/exit.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` of the action about to be executed.
        """
        pass


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

    def on_event_received(  # noqa: D401 – “Log …” (imperative) is acceptable
        self,
        interpreter: "BaseInterpreter[Any, Any]",
        event: "Event",
    ) -> None:
        """Log the event in a **TypeError-free** fashion.

        The inspector must *never* raise when the event’s ``payload`` is a
        primitive (``str``, ``int``, ``None``).  The old implementation
        accessed ``event.data`` unconditionally, which *raises* for such
        cases.  The logic is now:

        1. **If** the event has a ``payload`` attribute (standard ``Event``),
           log that *value as-is* — do **not** touch ``event.data``.
        2. **Else** (``DoneEvent`` / ``AfterEvent``), safely read
           ``event.data``.
        """
        # 1️⃣  Extract something loggable without risking TypeError
        if hasattr(event, "payload"):
            data_to_log = event.payload  # may be primitive / dict / None
        else:
            data_to_log = getattr(event, "data", None)

        # 2️⃣  Compose and emit log line
        msg = f"🕵️ [INSPECT] Event Received: {event.type}"
        if data_to_log is not None:
            msg += f" | Data: {data_to_log}"
        logger.info(msg)

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
            from_states: The set of `StateNode`s active before the transition.
            to_states: The set of `StateNode`s active after the transition.
            transition: The `TransitionDefinition` that was taken.
        """
        # Get the string IDs of the leaf states for clean logging.
        from_ids = {s.id for s in from_states if s.is_atomic or s.is_final}
        to_ids = {s.id for s in to_states if s.is_atomic or s.is_final}

        # ✅ Only log a full transition if a state change actually happened.
        if from_ids != to_ids:
            logger.info(
                "🕵️ [INSPECT] Transition: %s -> %s on Event '%s'",
                from_ids,
                to_ids,
                transition.event,
            )
            logger.info("🕵️ [INSPECT] New Context: %s", interpreter.context)
        # 🎬 For internal transitions (no state change but with actions),
        # still log the context, as it may have changed.
        elif transition.actions:
            logger.info(
                "🕵️ [INSPECT] Internal transition on Event '%s'. "
                "Context may have changed.",
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
