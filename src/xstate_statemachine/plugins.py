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
    Dict,
    Any,
    Generic,
    List,  # Core typing utilities
    Set,
    Tuple,
    TypeVar,
    Union,
)

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
from .events import ErrorEvent, Event  # noqa: E402

if TYPE_CHECKING:
    from .base_interpreter import BaseInterpreter
    from .events import AfterEvent, DoneEvent
    from .models import (
        ActionDefinition,
        InvokeDefinition,
        StateNode,
        TransitionDefinition,
    )

# -----------------------------------------------------------------------------
# 🔹 Runtime Event Union (issue #60)
# -----------------------------------------------------------------------------
# 🐛 The interpreter's dispatch pipeline funnels three distinct event shapes
# through the *same* call sites that invoke these hooks: user-sent `Event`s,
# internally-synthesized `AfterEvent`s (delayed `after` transitions), and
# `DoneEvent`s (`invoke`/child-machine completion). Typing hook parameters as
# a plain `Event` therefore doesn't match what actually gets passed at
# runtime, and silently hid real mypy `arg-type` errors at every call site.
AnyEvent = Union["Event", "AfterEvent", "DoneEvent", "ErrorEvent"]

# -----------------------------------------------------------------------------
# 🔹 Type Variable for Generic Plugin
# -----------------------------------------------------------------------------
# This TypeVar is key to a fully type-safe plugin system. It allows a plugin
# to be defined for a specific `BaseInterpreter` subclass (e.g., `AsyncInterpreter`
# or `SyncInterpreter`), enabling precise autocompletion and static analysis
# in the developer's IDE.
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter[Any]")


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
        self, interpreter: TInterpreter, event: "AnyEvent"
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

    def on_action_error(
        self,
        interpreter: TInterpreter,
        action: "ActionDefinition",
        error: BaseException,
    ) -> None:
        """Called when a user-supplied action raises.

        What happens *next* is decided by the machine's
        ``action_error_policy`` (see :func:`create_machine`):

        * ``"continue"`` — the remaining actions in the list are skipped and
          the transition still completes. The failure is reported through
          :meth:`on_transition_failed` and ``interpreter.last_transition_ok``.
        * ``"rollback"`` — the transition is aborted and the pre-transition
          configuration and context are restored.
        * ``"fail"`` — rolled back, then the interpreter stops with
          ``status == "error"``.

        This hook fires under every policy, before the policy is applied, so
        it is the right place to route failures to Sentry, a metrics counter
        or a dead-letter queue regardless of how the machine recovers.

        Args:
            interpreter: The interpreter instance.
            action: The `ActionDefinition` whose implementation raised.
            error: The exception that was raised.

        Example:
            >>> class ActionErrorReporter(PluginBase):
            ...     def on_action_error(self, interpreter, action, error):
            ...         sentry_sdk.capture_exception(error)  # noqa
        """
        pass  # pragma: no cover

    def on_transition_failed(
        self,
        interpreter: TInterpreter,
        transition: "TransitionDefinition",
        failed_actions: List[Tuple["ActionDefinition", BaseException]],
    ) -> None:
        """Called when a transition's action list did not run to completion.

        🏛️ Architecture decision: :meth:`on_transition` documents itself as
        firing after a *successful* transition, yet before 0.8.0 it also
        fired when an action had raised part-way through the list — the
        machine reported a state its own actions never finished building,
        and that state could be persisted as truth. This hook exists so a
        partially-executed transition is *distinguishable* from a complete
        one.

        Fires under every ``action_error_policy``. Under ``"continue"`` it is
        followed by :meth:`on_transition` (the transition did commit); under
        ``"rollback"`` and ``"fail"`` it is not (nothing committed).

        Args:
            interpreter: The interpreter instance.
            transition: The transition whose actions failed.
            failed_actions: ``(action, exception)`` pairs, in execution
                order. Never empty.
        """
        pass  # pragma: no cover

    def on_resolve_error(
        self,
        interpreter: TInterpreter,
        error: BaseException,
        event: "AnyEvent",
    ) -> None:
        """Called when a transition's target cannot be resolved at runtime.

        Only reachable under ``create_machine(strict_targets=False)``, where
        an unresolvable target string is deferred to runtime instead of
        rejected at build. The third per-transition failure category
        alongside :meth:`on_action_error` and :meth:`on_guard_error` (#134);
        the same failure is also on ``interpreter.last_error`` and the
        event's `Receipt`.

        Args:
            interpreter: The interpreter instance.
            error: The `StateNotFoundError` describing the target.
            event: The event whose transition failed to resolve.
        """
        pass  # pragma: no cover

    def on_invalid_event(
        self,
        interpreter: TInterpreter,
        error: BaseException,
        raw_event: Any,
    ) -> None:
        """Called when `send()` refuses a malformed event (#159).

        Fires immediately before the `InvalidEventError` propagates to the
        caller -- the hook is observability, not containment; the caller
        still gets the exception. Without it, a plugin bound to every hook
        saw only routine traffic while `send(42)` was raising.

        Args:
            interpreter: The interpreter instance.
            error: The `InvalidEventError` about to be raised.
            raw_event: Whatever the caller passed to `send()`.
        """
        pass  # pragma: no cover

    def on_snapshot_error(
        self,
        interpreter: TInterpreter,
        error: BaseException,
    ) -> None:
        """Called when a snapshot is refused (#159).

        Fires immediately before a `SnapshotMidStepError` (mid-macrostep
        snapshot) or `SnapshotSerializationError` (non-JSON pending data)
        propagates from `get_persisted_snapshot()` / `get_snapshot()`. As
        with :meth:`on_invalid_event`, the exception still reaches the
        caller; this is the audit surface.

        Args:
            interpreter: The interpreter instance.
            error: The snapshot error about to be raised.
        """
        pass  # pragma: no cover

    def on_plugin_error(
        self,
        interpreter: TInterpreter,
        plugin: Any,
        hook: str,
        error: BaseException,
    ) -> None:
        """Called when ANOTHER plugin's hook failed and was contained (#127).

        Plugin failures never propagate into the interpreter; this hook is
        the programmatic surface for them, so an observability plugin can
        count or alert on failures in its peers. It is never invoked for the
        plugin that failed (no recursion). The same triple is on
        ``interpreter.last_plugin_error``.

        Args:
            interpreter: The interpreter instance.
            plugin: The plugin instance whose hook failed.
            hook: The hook method name (``"on_transition"``, …).
            error: The exception raised, or the `TypeError` describing an
                ``async def`` hook that was never awaited.
        """
        pass  # pragma: no cover

    def on_guard_error(
        self,
        interpreter: TInterpreter,
        guard_name: str,
        event: "AnyEvent",
        error: BaseException,
    ) -> None:
        """Called when a guard implementation raises instead of returning.

        Before 0.8.0 a raising guard was silently treated as ``False`` — a
        crashing risk check and a failing one were indistinguishable to
        every observer. This hook fires with the original exception under
        every ``guard_error_policy``, immediately before
        :meth:`on_guard_evaluated` reports the substituted result.

        Args:
            interpreter: The interpreter instance.
            guard_name: The guard that raised.
            event: The event being evaluated when it raised.
            error: The exception the guard raised.
        """
        pass  # pragma: no cover

    def on_unhandled_event(
        self,
        interpreter: TInterpreter,
        event: "AnyEvent",
        active_state_ids: Set[str],
        disposition: str,
    ) -> None:
        """Called when an event selects no transition in the current state.

        Per XState semantics an unhandled event is not an error — it is
        ignored. But "ignored" and "lost" look identical from the outside,
        and for a machine on a critical path (an order lifecycle, a payment)
        a typo'd event name is a silent no-op that no test can catch. This
        hook makes every such event observable, whatever the machine's
        ``onUnhandled`` policy did with it. Fires exactly once per event,
        in both engines.

        Args:
            interpreter: The interpreter instance.
            event: The event that matched nothing.
            active_state_ids: The state ids active when it arrived.
            disposition: What happened to it — ``"ignored"``,
                ``"deferred"``, ``"errored"`` or ``"dropped"`` (the deferral
                buffer was full and the oldest entry was evicted).
        """
        pass  # pragma: no cover

    def on_invocation_stranded(
        self,
        interpreter: TInterpreter,
        state_id: str,
        invoke_id: str,
        error: BaseException,
    ) -> None:
        """Called when a chain-budget cut leaves an invocation that can
        never complete (#207).

        The `maxIterations` guard discarded a `done.invoke` /
        `error.platform` for an invocation whose state is still active.
        Nothing is running for it and no completion will ever arrive, so
        the machine rests in a state that declares `invoke` -- a state it
        was never meant to come to rest in. Distinguishes "the storm
        settled" from "the storm was cut and the machine is parked".
        `has_dormant_invocations` / `pending_invocations()` answer the same
        question on demand; this is the push notification.

        Args:
            interpreter: The interpreter instance.
            state_id: The active state whose invocation was stranded.
            invoke_id: The invocation's `id`.
            error: The `RunawayChainError` carrying the cut.
        """
        pass  # pragma: no cover

    def on_event_dropped(
        self, interpreter: TInterpreter, event: "AnyEvent", reason: str
    ) -> None:
        """Called when an accepted-looking event is discarded unprocessed.

        Fires under ``OverflowPolicy.DROP_NEWEST`` when the bounded inbox is
        full (``reason == "queue_full"``), and when a send reaches a
        machine that is stopped/done/errored (``reason == "not_running"``).
        The drop is also logged at WARNING. This is the observability hook
        for load shedding (#38).

        Args:
            interpreter: The interpreter instance.
            event: The event that was not queued.
            reason: Why -- ``"queue_full"`` or ``"not_running"``.
        """
        pass  # pragma: no cover

    def on_error(
        self, interpreter: TInterpreter, error: BaseException
    ) -> None:
        """Called when the interpreter enters the ``"error"`` status.

        This is the terminal failure signal: the machine has stopped and
        will process no further events. ``interpreter.error`` holds the same
        exception.

        Args:
            interpreter: The interpreter instance.
            error: The exception that stopped the machine.
        """
        pass  # pragma: no cover

    def on_done(self, interpreter: TInterpreter, output: Any) -> None:
        """Called when the machine reaches a top-level final state.

        Args:
            interpreter: The interpreter instance.
            output: The machine's ``output`` value (may be ``None``).
        """
        pass  # pragma: no cover

    def on_guard_evaluated(
        self,
        interpreter: TInterpreter,
        guard_name: str,
        event: "AnyEvent",
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
#: Default redaction denylist for `LoggingInspector` (#126). Any context or
#: payload KEY containing one of these substrings (case-insensitive) is
#: logged as ``"***"``. Extend with ``LoggingInspector(redact_keys=[...])``.
DEFAULT_REDACT_KEYS: Tuple[str, ...] = (
    # credentials
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "credential",
    "private_key",
    "cookie",
    "session",  # sessionId, session_token, ...
    "signature",
    "otp",
    "pin",
    # payment / banking (#160)
    "card",
    "cvv",
    "cvc",
    "pan",
    "iban",
    "account_number",
    "account_no",
    "routing",
    "swift",
    # crypto
    "mnemonic",
    "seed_phrase",
    "seed",
    # personal identifiers
    "ssn",
    "dob",
    "date_of_birth",
    "email",
    "phone",
    "passport",
)


def redact(value: Any, keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS) -> Any:
    """Return *value* with sensitive mapping keys replaced by ``"***"``.

    Recurses into nested dicts and lists; leaves everything else untouched.
    Keys are matched by case-insensitive substring so ``apiKey``,
    ``API_KEY`` and ``x-api-key`` all redact. Pure; never mutates input.
    """
    if isinstance(value, dict):
        out: Dict[Any, Any] = {}
        for k, v in value.items():
            ks = str(k).lower()
            out[k] = "***" if any(s in ks for s in keys) else redact(v, keys)
        return out
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v, keys) for v in value)
    return value


class LoggingInspector(PluginBase[Any]):
    """A built-in plugin for detailed, real-time inspection of a machine.

    This plugin provides clear, emoji-prefixed logs for events, transitions,
    and action executions, making it invaluable for debugging complex state
    machines. It serves as a canonical example of how to implement a
    `PluginBase` subclass. It uses `Generic[Any]` to work with both the
    sync and async interpreters.

    🔒 #126: context and event payloads are **redacted** before logging.
    Any key matching :data:`DEFAULT_REDACT_KEYS` (``password``, ``token``,
    ``secret``, ``api_key``, …) is written as ``"***"``. Pass
    ``redact_keys=(...)`` to extend or replace the list, or
    ``redact_keys=()`` to log everything verbatim -- an explicit opt-in,
    because a debugging plugin attached "just for a minute" is exactly how
    credentials end up in a log aggregator.

    Args:
        redact_keys: Substrings (case-insensitive) of keys to redact.
            Defaults to :data:`DEFAULT_REDACT_KEYS`.
        log_context: Log the full (redacted) context after each
            transition. ``True`` by default; set ``False`` for high-volume
            machines where the context is large.
    """

    def __init__(
        self,
        *,
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
        log_context: bool = True,
    ) -> None:
        self._redact_keys = tuple(redact_keys)
        self._log_context = log_context

    def _log_ctx(self, interpreter: Any) -> None:
        if self._log_context:
            logger.info(
                "🕵️ [INSPECT] New Context: %s",
                self._safe(interpreter.context),
            )

    def _safe(self, value: Any) -> Any:
        return redact(value, self._redact_keys) if self._redact_keys else value

    def on_event_received(
        self, interpreter: "BaseInterpreter[Any]", event: "AnyEvent"
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
        data_to_log: Any
        if isinstance(event, Event):
            data_to_log = self._safe(event.payload)
        #    `ErrorEvent` carries the exception on `.error` (#80); reading
        #    its deprecated `.data` alias here tripped the library's own
        #    DeprecationWarning under `-W error` (#95).
        elif isinstance(event, ErrorEvent):
            # 🔒 #160: the message may echo the failed request; redact
            #    structured args, keep the type.
            err = event.error
            data_to_log = (
                f"{type(err).__name__}: {self._safe(err.args[0])}"
                if getattr(err, "args", None)
                else err
            )
        #    For `DoneEvent` / `AfterEvent`, it's in `data`. 🔒 #160: a
        #    service RESULT is data like any other -- redact it too.
        else:
            data_to_log = self._safe(getattr(event, "data", None))

        # 2️⃣ Compose and emit the final log message.
        message = f"🕵️ [INSPECT] Event Received: {event.type}"
        if data_to_log is not None:
            message += f" | Data: {data_to_log}"
        logger.info(message)

    def on_transition(
        self,
        interpreter: "BaseInterpreter[Any]",
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
            self._log_ctx(interpreter)
        # внутрішній (Internal) transition: No state change, but actions ran.
        elif transition.actions:
            logger.info(
                "🕵️ [INSPECT] Internal transition on Event '%s'",
                transition.event,
            )
            self._log_ctx(interpreter)

    def on_action_execute(
        self,
        interpreter: "BaseInterpreter[Any]",
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
        interpreter: "BaseInterpreter[Any]",
        guard_name: str,
        event: "AnyEvent",
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
        interpreter: "BaseInterpreter[Any]",
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
        interpreter: "BaseInterpreter[Any]",
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
            self._safe(result),  # 🔒 #160: a service result is data too
        )

    def on_service_error(
        self,
        interpreter: "BaseInterpreter[Any]",
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
            "❌ [INSPECT] Service '%s' (ID: %s) failed. Error: %s: %s",
            invocation.src,
            invocation.id,
            type(error).__name__,
            # 🔒 #160: an exception's message may echo the request that
            #    failed (a card number in a gateway error). Redact when it
            #    carries structured args; the traceback is kept.
            self._safe(error.args[0]) if error.args else "",
            exc_info=True,  # 🐛 Include full traceback for debugging.
        )

    # -------------------------------------------------------------------------
    # 🚨 Error-observability hooks (0.8.0, #33)
    # -------------------------------------------------------------------------

    def on_transition_failed(
        self,
        interpreter: "BaseInterpreter[Any]",
        transition: "TransitionDefinition",
        failed_actions: List[Tuple["ActionDefinition", BaseException]],
    ) -> None:
        """Logs a transition whose action list did not run to completion."""
        logger.error(
            "💥 [INSPECT] Transition from '%s' on '%s' had %d failing "
            "action(s): %s (policy=%s)",
            transition.source.id,
            transition.event or "always",
            len(failed_actions),
            ", ".join(f"{a.type}: {e!r}" for a, e in failed_actions),
            interpreter.machine.action_error_policy,
        )

    def on_guard_error(
        self,
        interpreter: "BaseInterpreter[Any]",
        guard_name: str,
        event: "AnyEvent",
        error: BaseException,
    ) -> None:
        """Logs a guard that raised instead of returning."""
        logger.error(
            "🔥 [INSPECT] Guard '%s' RAISED on event '%s' (policy=%s): %r",
            guard_name,
            event.type,
            interpreter.machine.guard_error_policy,
            error,
        )

    def on_unhandled_event(
        self,
        interpreter: "BaseInterpreter[Any]",
        event: "AnyEvent",
        active_state_ids: Set[str],
        disposition: str,
    ) -> None:
        """Logs an event that matched no transition."""
        logger.warning(
            "🍃 [INSPECT] Event '%s' unhandled in %s -> %s",
            event.type,
            sorted(active_state_ids),
            disposition,
        )

    def on_error(
        self, interpreter: "BaseInterpreter[Any]", error: BaseException
    ) -> None:
        """Logs the interpreter entering the terminal error status."""
        logger.error(
            "🚨 [INSPECT] Interpreter '%s' entered status 'error': %r",
            interpreter.id,
            error,
        )

    def on_done(
        self, interpreter: "BaseInterpreter[Any]", output: Any
    ) -> None:
        """Logs the machine reaching a top-level final state."""
        logger.info(
            "🏁 [INSPECT] Interpreter '%s' is done. Output: %r",
            interpreter.id,
            output,
        )
