# /src/xstate_statemachine/base_interpreter.py
# -----------------------------------------------------------------------------
# 🏛️ Base State Machine Interpreter
# -----------------------------------------------------------------------------
# This module provides the `BaseInterpreter` class, which contains the
# core, mode-agnostic logic for state machine execution. It embodies the
# "Template Method" design pattern, where the overall algorithm for state
# transition is defined, but specific steps (like how actions are executed
# or events are dispatched) are deferred to subclasses.
#
# This design cleanly separates the fundamental statechart algorithm from
# the execution mode (synchronous vs. asynchronous), promoting code reuse
# and maintainability.
# -----------------------------------------------------------------------------
"""
Provides the foundational, mode-agnostic logic for interpreting a state machine.

This module contains the `BaseInterpreter` class, which should not be
instantiated directly. Instead, developers should use one of its concrete
subclasses, `Interpreter` for asynchronous operations or `SyncInterpreter` for
synchronous, blocking operations.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import functools
import copy
import inspect
import json
import logging
import threading
import time
import warnings
from typing import (
    cast,
    Any,
    Awaitable,
    NamedTuple,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    overload,
    TypeVar,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import (
    SYSTEM_EVENT_PREFIXES,
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    is_system_event,
    persist_event,
    restore_event,
    system_event,
)
from .exceptions import (
    InvalidEventError,
    SnapshotMidStepError,
    SnapshotCorruptError,
    SnapshotSerializationError,
    NotSupportedError,
    InvalidEventPayloadError,
    UnknownEventError,
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
    RestoredError,
    StateNotFoundError,
    TransitionFailedError,
    UnhandledEventError,
)
from .actions import (
    SPAWN_CHILD,
    STOP_CHILD,
    ESCALATE,
    FORWARD_TO,
    SEND_PARENT,
    SEND_TO,
    RAISE,
    is_builtin,
    resolve_builtin,
    ASSIGN,
    CANCEL,
    CHOOSE,
    EMIT,
    ENQUEUE_ACTIONS,
    LOG,
    PURE,
    ActionEnqueuer,
)
from .models import (
    SPAWN_BLOCKING_PREFIX,
    ActionDefinition,
    GuardDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TransitionDefinition,
)
from .plugins import PluginBase
from .resolver import resolve_target_state
from . import persistence
from .clock import Clock, RealClock

# This TypeVar allows methods to return the specific subclass instance (self).
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter")

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Establishes a logger for this module, allowing for detailed, context-aware
# logging that can be configured by the end-user's application.
logger = logging.getLogger(__name__)

#: Every event kind the core algorithm can be asked to process.
AnyEvent = Union[Event, DoneEvent, AfterEvent, ErrorEvent]


# -----------------------------------------------------------------------------
# 🏛️ BaseInterpreter Class Definition
# -----------------------------------------------------------------------------


class ActorSystem:
    """A read-only view over the actor registry of one machine hierarchy.

    Mirrors XState's actor system: actors that declare a `systemId` can be
    looked up by that name from anywhere in the hierarchy, which is what makes
    sibling-to-sibling messaging possible.

    Attributes:
        _registry (Dict[str, BaseInterpreter]): The shared registry.
    """

    __slots__ = ("_registry",)

    def __init__(self, registry: Dict[str, "BaseInterpreter[Any]"]):
        """Initializes the view.

        Args:
            registry: The root interpreter's live registry.
        """
        self._registry = registry

    def get(self, system_id: str) -> Optional["BaseInterpreter[Any]"]:
        """Looks up an actor by its `systemId`.

        Args:
            system_id (str): The registered system id.

        Returns:
            Optional[BaseInterpreter]: The actor, or `None`.
        """
        return self._registry.get(system_id)

    def get_all(self) -> Dict[str, "BaseInterpreter[Any]"]:
        """Returns every registered actor.

        Returns:
            Dict[str, BaseInterpreter]: A copy of the registry.
        """
        return dict(self._registry)

    def __contains__(self, system_id: object) -> bool:
        """Supports ``system_id in interpreter.system``."""
        return system_id in self._registry

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"ActorSystem(actors={sorted(self._registry)})"


# -----------------------------------------------------------------------------
# 🛡️ Plugin Error Containment
# -----------------------------------------------------------------------------
class _SafePlugin:
    """Wraps a plugin so a failing hook cannot break the interpreter.

    🏛️ Architecture decision: containment lives at the registration boundary
    rather than at each of the ~27 hook dispatch sites. Wrapping once keeps
    every call site free of defensive noise and makes it impossible to add a
    new dispatch that forgets to guard.

    Observability must never be able to break the thing it observes. An
    exception from a metrics exporter or an audit logger previously
    propagated out of `send()` on the sync engine and killed the run loop on
    the async engine — a monitoring bug taking down the state machine.
    Actions and subscribers were already contained; plugins were the
    outlier.

    Attributes:
        _plugin: The wrapped plugin instance.
    """

    __slots__ = ("_plugin",)

    def __init__(self, plugin: Any) -> None:
        """Stores the plugin being wrapped.

        Args:
            plugin (Any): Any object exposing the plugin hooks.
        """
        object.__setattr__(self, "_plugin", plugin)

    @property
    def wrapped(self) -> Any:
        """Returns the underlying plugin instance."""
        return object.__getattribute__(self, "_plugin")

    def __getattr__(self, name: str) -> Any:
        """Returns a hook wrapped in error containment.

        Args:
            name (str): The attribute being accessed.

        Returns:
            Any: A guarded callable, or the raw attribute if not callable.
        """
        plugin = object.__getattribute__(self, "_plugin")
        # 🦆 Duck-typed plugins only need the hooks they care about. Letting
        #    the AttributeError escape would make a partial plugin crash the
        #    interpreter at the first hook it omitted — the very failure mode
        #    this wrapper exists to prevent.
        attribute = getattr(plugin, name, None)
        if attribute is None:
            return lambda *_a, **_k: None
        if not callable(attribute):
            return attribute

        @functools.wraps(attribute)
        def _guarded(*args: Any, **kwargs: Any) -> Any:
            """Invokes the hook, containing any failure.

            🏛️ #114: `asyncio.CancelledError` is a `BaseException` since
            3.8, so the old `except Exception` let a plugin that raised it
            (or `concurrent.futures.CancelledError`, which IS it) unwind the
            run loop -- leaving `status="running"` on a dead machine with
            every pending receipt hung. A hook raising CancelledError is a
            plugin bug like any other and is contained the same way. Real
            task cancellation never passes through a plugin hook.

            🔔 #127: an `async def` override returns a coroutine the engine
            cannot await from a synchronous dispatch site. It used to be
            dropped on the floor with only a Python `RuntimeWarning: coroutine
            was never awaited`. Now it is closed explicitly and reported
            through the same failure surface as a raising hook.
            """
            try:
                result = attribute(*args, **kwargs)
            except asyncio.CancelledError as exc:
                _SafePlugin._report(plugin, name, exc, args)
                return None
            except Exception as exc:
                _SafePlugin._report(plugin, name, exc, args)
                return None
            if inspect.iscoroutine(result):
                result.close()
                _SafePlugin._report(
                    plugin,
                    name,
                    TypeError(
                        f"{type(plugin).__name__}.{name} is 'async def'; "
                        f"plugin hooks are synchronous callbacks and are "
                        f"never awaited. Make it a plain 'def' and schedule "
                        f"your own task inside it if you need async work."
                    ),
                    args,
                )
                return None
            return result

        return _guarded

    @staticmethod
    def _report(
        plugin: Any, hook: str, exc: BaseException, args: tuple
    ) -> None:
        """Log a contained hook failure and offer it to `on_plugin_error`.

        🏛️ #127: swallowing a hook failure protected the machine but left
        the *plugin author* with no programmatic signal. The interpreter
        (``args[0]`` by hook convention) now records it on
        `last_plugin_error` and fires `on_plugin_error` on every OTHER
        plugin, so a metrics exporter can count observability failures
        without the failing plugin being able to recurse into itself.
        """
        logger.error(
            "🔌 Plugin '%s' failed in '%s'; contained so the interpreter "
            "keeps running: %r",
            type(plugin).__name__,
            hook,
            exc,
            exc_info=isinstance(exc, Exception),
        )
        interp = args[0] if args else None
        if interp is None or not hasattr(interp, "_plugins"):
            return
        interp.last_plugin_error = (type(plugin).__name__, hook, exc)
        if hook == "on_plugin_error":
            return  # never recurse
        for other in interp._plugins:
            inner = other.wrapped if isinstance(other, _SafePlugin) else other
            if inner is plugin:
                continue  # the failing plugin never hears about itself
            other.on_plugin_error(interp, plugin, hook, exc)

    def __eq__(self, other: Any) -> bool:
        """Compares against the wrapped plugin so `in` checks work."""
        target = object.__getattribute__(self, "_plugin")
        if isinstance(other, _SafePlugin):
            return bool(target == other.wrapped)
        return bool(target == other)

    def __hash__(self) -> int:
        """Hashes as the wrapped plugin."""
        return hash(object.__getattribute__(self, "_plugin"))

    def __repr__(self) -> str:
        """Mirrors the wrapped plugin's repr."""
        return repr(object.__getattribute__(self, "_plugin"))


# 🏛️ Prefixes of events the ENGINE synthesises (`done.invoke.*`,
#    `error.platform.*`, `after.*`, `xstate.error.actor.*` from `escalate`,
#    and the init/exit sentinels). Shared by the wildcard matcher, the
#    unhandled-event policy and strict mode so the three can never disagree
#    about what counts as a system event (#28 review, #79). The single
#    source of truth lives in `events.py`.
_SYSTEM_EVENT_PREFIXES: Tuple[str, ...] = SYSTEM_EVENT_PREFIXES

#: Process-wide latch for the `actionErrorPolicy` default-flip warning (#27).
_WARNED_ACTION_ERROR_POLICY_DEFAULT: bool = False


#: ⚡ Memo for `_accepts_kwarg`, keyed on the UNDERLYING function (a bound
#: method's `__func__`) so every interpreter sharing a clock class hits the
#: cache. `inspect.signature` was 32% of interpreter construction (#S6).
_ACCEPTS_KWARG_CACHE: Dict[Tuple[int, str], bool] = {}


def _accepts_kwarg(fn: Callable[..., Any], name: str) -> bool:
    """``True`` if calling *fn* with keyword *name* is signature-legal.

    Memoised per ``(function, name)``: a function's signature does not
    change, and this is called from every ``BaseInterpreter.__init__``.

    Used to detect 0.8.0-era `Clock` implementations whose `set_timeout`
    predates the ``sync=`` keyword (#76). Only an EXPLICITLY named
    parameter counts (#89): a ``**kwargs`` catch-all is how a legacy
    wrapper forwards to a backend that has never heard of ``sync``, so
    feeding it the keyword broke it. Un-introspectable callables (C
    builtins, some mocks) are assumed NOT to accept it -- the legacy call
    shape is the safe default.
    """
    target = getattr(fn, "__func__", fn)
    key = (id(target), name)
    cached = _ACCEPTS_KWARG_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):  # pragma: no cover -- exotic callables
        return False
    param = params.get(name)
    result = (
        param is not None and param.kind is not inspect.Parameter.VAR_KEYWORD
    )
    # 🧷 Keep the function alive so its id() cannot be recycled by a later,
    #    different function (which would make the memo lie).
    _ACCEPTS_KWARG_CACHE[key] = result
    _ACCEPTS_KWARG_KEEPALIVE.append(target)
    return result


_ACCEPTS_KWARG_KEEPALIVE: List[Any] = []

#: ⚡ The init / exit trigger events are constant, payload-less sentinels;
#: `Event` is an immutable NamedTuple, so one instance each is safe to share
#: across every interpreter instead of minting one per `start()`.
_INIT_EVENT: Event = system_event("___xstate_statemachine_init___")
_EXIT_EVENT: Event = system_event("___xstate_statemachine_exit___")


class PendingInvocation(NamedTuple):
    """An `invoke` that is part of the configuration but has no live task.

    Returned by :meth:`BaseInterpreter.pending_invocations` (#44).

    Attributes:
        state_id: The state that owns the invoke.
        invoke_id: The invoke's id (explicit, or the parser default).
        src: The service key.
    """

    state_id: str
    invoke_id: str
    src: str


class _RollbackRequested(Exception):
    """Internal signal: an action raised and the policy is not ``continue``.

    Raised inside `_execute_transition`'s atomic block so the EXISTING
    rollback path (built for transition-resolution failures in 0.6.0) is
    reused for action failures. Never escapes `_execute_transition`.
    """

    def __init__(
        self, action_def: ActionDefinition, original: BaseException
    ) -> None:
        super().__init__(action_def.type)
        self.action_def = action_def
        self.original = original


class BaseInterpreter(Generic[TContext]):
    """Provides the foundational logic for state machine interpretation.

    This abstract base class implements the "Template Method" design pattern.
    It defines the complete, final algorithm for processing events and
    transitioning between states (`_process_event`), but it defers the
    implementation of specific execution steps (like running actions or timers)
    to its concrete subclasses. This architecture cleanly separates the universal
    statechart algorithm from the execution strategy (e.g., synchronous vs.
    asynchronous).

    This class should not be instantiated directly. Use `Interpreter` (async)
    or `SyncInterpreter` (sync).

    Attributes:
        machine (MachineNode[TContext]): The static `MachineNode`
            definition that represents the statechart's structure.
        context (TContext): The current extended state (context) of the
            machine, holding all dynamic data.
        status (str): The operational status of the interpreter:
            'uninitialized', 'running', or 'stopped'.
        id (str): A unique identifier for this interpreter instance, inherited
            from the machine's ID.
        parent (Optional[BaseInterpreter[Any]]): A reference to the parent
            interpreter if this instance was spawned as part of an actor model,
            otherwise `None`.
    """

    #: Maximum depth of nested action expansion (`pure` / `choose` /
    #: `enqueueActions` returning further actions). Guards against a callback
    #: that re-enqueues itself.
    MAX_ACTION_DEPTH: int = 50

    # ⚡ Perf: an interpreter carries ~44 attributes. In a plain `__dict__`
    #    that is a 1.6 KB hash table per instance; as slots it is ~400 B of
    #    contiguous pointers, which is what makes 1,000 live interpreters
    #    cache-friendly (+24% construct-and-touch throughput measured at this
    #    attribute count). `__dict__` is kept so subclasses that add state
    #    (test spies, `helpers._Probe`) and ad-hoc attributes keep working;
    #    the declared slots still take the fast path. Every subclass must
    #    declare its OWN additions in its own `__slots__`.
    __slots__ = (
        "_action_depth",
        "_active_state_nodes",
        "_actor_sources",
        "_actors",
        "_clock_accepts_sync",
        "_clock_sync_lane",
        "_deferred_events",
        "_deferred_this_step",
        "_emit_listeners",
        "_event_queue",
        "_guard_denied_this_step",
        "_history",
        "_internal_queue",
        "_interpreter_class",
        "_invoked_as",
        "_last_action_error",
        "_lifecycle_failures",
        "_pending_actor_snapshots",
        "_pending_guard_error",
        "_plugins",
        "_restart_services_on_start",
        "_restart_timers_on_start",
        "_scheduled_sends",
        "_step_soft_error",
        "_subscribers",
        "_system",
        "_terminal_listeners",
        "_timer_handles",
        "clock",
        "context",
        "error",
        "id",
        "input",
        "last_plugin_error",
        "last_transition_ok",
        "machine",
        "output",
        "parent",
        "status",
        "strict",
        "__dict__",
        "__weakref__",
    )

    def __init__(
        self,
        machine: MachineNode[TContext],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
        input: Optional[Any] = None,
        clock: Optional[Clock] = None,
        strict: Optional[bool] = None,
    ) -> None:
        """Initializes the BaseInterpreter instance.

        Args:
            machine (MachineNode[TContext]): The `MachineNode` instance
                that defines the statechart's structure, transitions, and
                logic references.
            interpreter_class (Optional[Type["BaseInterpreter"]]): The concrete
                class being instantiated (e.g., `Interpreter` or
                `SyncInterpreter`). This is used internally for correctly
                restoring an interpreter from a snapshot. If not provided, it
                defaults to the class of the current instance.
            input (Optional[Any]): Creation input, exposed to a `context`
                factory as ``{"input": ...}``.
            clock (Optional[Clock]): Source of time for `after` delays and
                delayed sends (#49). Defaults to :class:`RealClock`; pass a
                :class:`SimulatedClock` for deterministic tests. Invoked
                children inherit it.
            strict (Optional[bool]): (#51) When `True`, `send()` of an
                event type the machine never declares raises
                `UnknownEventError` at the call site instead of being a
                silent no-op. `None` (default) defers to the machine's
                ``strict`` config key. Declared-but-unhandled events stay
                silent no-ops (XState semantics).
        """
        # ⚡ Two INFO records per interpreter were ~6% of a 1,000-instance
        #    fan-out; one level check per construction instead.
        _info = logger.isEnabledFor(logging.INFO)
        if _info:
            logger.info(
                "🧠 Initializing BaseInterpreter for machine '%s'...",
                machine.id,
            )
        # 🧍‍♂️ Core Properties
        self.machine: MachineNode[TContext] = machine
        #: Input supplied at creation, available to context factories and
        #: readable afterwards as `interpreter.input`.
        self.input: Optional[Any] = input
        self.context: TContext = self._build_initial_context(machine, input)
        self.status: str = "uninitialized"
        self.id: str = machine.id
        #: ⏱️ Every timing path -- `after`, delayed `raise`/`sendTo` -- goes
        #: through this object and nothing else (#49). See `clock.py`.
        self.clock: Clock = clock if clock is not None else RealClock()
        #: ⏱️ #76: which delivery lane THIS engine can drain. `RealClock`
        #: uses it to pick heap vs `call_later` by owner, not by whether a
        #: loop happens to be running on the constructing thread.
        self._clock_sync_lane: bool = False
        #: ⏱️ Does `self.clock.set_timeout` accept the 0.8.1 `sync=` kwarg?
        #: Decided ONCE here by inspecting the signature, so `_set_timeout`
        #: is a single call. The previous try/except-TypeError fallback
        #: invoked a clock TWICE when its body raised TypeError for an
        #: unrelated reason, and surfaced that error with the lane lost.
        self._clock_accepts_sync: bool = _accepts_kwarg(
            self.clock.set_timeout, "sync"
        )
        #: 🛡️ #51: effective strictness -- the ctor flag wins over config.
        self.strict: bool = machine.strict if strict is None else bool(strict)
        self.parent: Optional["BaseInterpreter[Any]"] = None
        #: 🎯 #156: the `invoke.id` this actor was invoked under, as the
        #: PARENT declared (or defaulted) it. `escalate` reports this as
        #: `ErrorEvent.src` so the parent's `onError` collector matches it
        #: by id. Parsing it back out of the runtime actor id worked only
        #: when the id was explicit (`parent:kid`); an anonymous invoke's
        #: runtime id is `parent:<src>:<uuid>`, whose first segment is the
        #: SERVICE key, not the invoke id.
        self._invoked_as: Optional[str] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        #: Remembered configurations for history pseudo-states, keyed by the
        #: *parent* state id. Recorded on exit, replayed when a transition
        #: targets a `type: "history"` child of that parent.
        self._history: Dict[str, List[StateNode]] = {}
        #: Listeners registered via :meth:`subscribe`.
        self._subscribers: List[Callable[[Any], None]] = []
        #: The machine's final output, set when a top-level final state is
        #: reached. `None` until then.
        self.output: Any = None
        #: The error that put the machine into the "error" status, if any.
        self.error: Optional[BaseException] = None
        #: False when the most recent transition's action list did not run to
        #: completion. A persistence layer can gate snapshot writes on this
        #: so a state built by a half-executed action list is never written
        #: as truth.
        self.last_transition_ok: bool = True
        #: The exception behind the most recent `last_transition_ok=False`.
        self._last_action_error: Optional[BaseException] = None
        #: 🔔 #133: a non-fatal built-in failure recorded mid-transition and
        #: published by the transition epilogue.
        self._step_soft_error: Optional[BaseException] = None
        #: 🛡️ #152: a guard that RAISED under ``guardErrorPolicy: "raise"``
        #: during the current selection pass. Selection treats that
        #: candidate as unsatisfied and keeps walking (SCXML §5.9), so an
        #: unguarded fallback is still taken; the exception is re-raised by
        #: `_process_event` once the pass -- and the fallback -- has run.
        self._pending_guard_error: Optional[BaseException] = None
        #: ⏱️ Live clock handles per owning state id. Declared here so the
        #: shared restore / dormancy logic (#128) can read it; each engine
        #: re-binds the same attribute in its own `__init__`.
        self._timer_handles: Dict[str, List[Any]] = {}
        #: 🔌 #127: `(plugin class name, hook name, exception)` of the most
        #: recent contained plugin-hook failure, or ``None``.
        self.last_plugin_error: Optional[Tuple[str, str, BaseException]] = None
        # 🧾 Stack of open action-error transactions; see
        #    `_execute_lifecycle_actions`. Each entry is
        #    ``(transition, failures_collected_so_far)``.
        self._lifecycle_failures: List[
            Tuple[
                TransitionDefinition,
                List[Tuple[ActionDefinition, BaseException]],
            ]
        ] = []
        #: Events held back under ``onUnhandled: "defer"``, replayed after
        #: the next successful transition. Empty under other policies.
        self._deferred_events: List[Event] = []
        #: 🧾 #84/#106: the event objects `onUnhandled: "defer"` held during
        #: the CURRENT step, so `send(wait=True)` can report `deferred=True`.
        #: Holds references (not `id()`s -- an id is recycled the moment
        #: its object dies, which mislabelled unrelated later events) and is
        #: cleared at the start of every step, so it never outgrows one
        #: step's worth of deferrals.
        self._deferred_this_step: List[Any] = []
        #: 🚦 #153: set by `_collect_eligible_transitions` when a candidate
        #: MATCHED the event type but its guard said no. Read by
        #: `_handle_unhandled_event` (disposition) and by the receipt
        #: builders (`Receipt.denied`); cleared per step like `_deferred_this_step`.
        self._guard_denied_this_step: bool = False
        #: Listeners registered via :meth:`on`, keyed by emitted event type.
        self._emit_listeners: Dict[str, List[Callable[[Any], None]]] = {}
        #: Cancellation callbacks for pending delayed sends, keyed by send id.
        self._scheduled_sends: Dict[str, Callable[[], None]] = {}
        #: Actor-system registry. Only the ROOT interpreter's copy is used;
        #: children reach it by walking up `parent`.
        self._system: Dict[str, "BaseInterpreter[Any]"] = {}
        #: Callbacks to run the moment `status` becomes terminal
        #: ("done" / "error"). The async engine registers one that resolves
        #: its completion future; the parent awaits that instead of polling
        #: (#43). Fired at most once.
        self._terminal_listeners: List[Callable[[str], None]] = []
        #: Snapshots of child actors that could not be rebuilt on restore
        #: (their service was not registered). Preserved rather than dropped
        #: so no data is lost and the caller can recover them.
        self._pending_actor_snapshots: Dict[str, Any] = {}
        #: 🔁 #44: set by `from_snapshot(restart_services=True)`; consumed by
        #: the engine's `start()` resume path, which re-invokes every
        #: dormant invoke in the restored configuration.
        self._restart_services_on_start: bool = False
        #: ⏱️ #128: re-arm `after` timers of the restored configuration on
        #: the next `start()`.
        self._restart_timers_on_start: bool = False
        #: Maps a spawned actor id to the `services` key it came from, so a
        #: snapshot can record enough to rebuild it.
        self._actor_sources: Dict[str, str] = {}
        #: Current nesting depth of action expansion.
        self._action_depth: int = 0
        self._actors: Dict[str, "BaseInterpreter[Any]"] = {}

        # 🔗 Extensibility & Introspection
        self._plugins: List[PluginBase["BaseInterpreter[Any]"]] = []
        self._interpreter_class: Type["BaseInterpreter[Any]"] = (
            interpreter_class or self.__class__
        )

        if _info:
            logger.info(
                "✅ BaseInterpreter '%s' initialized. Status: '%s'.",
                self.id,
                self.status,
            )

    @staticmethod
    def _build_initial_context(
        machine: MachineNode[Any], input: Optional[Any]
    ) -> Any:
        """Builds the starting context, resolving a factory if one is given.

        🏛️ Architecture decision: XState allows `context` to be a function of
        `{input}` so an actor can be parameterised at creation. Previously a
        callable was stored verbatim, so the runtime context *was* the
        function object — silent corruption that surfaced far from its cause
        as a `TypeError` on first subscript.

        Args:
            machine (MachineNode): The machine definition.
            input (Optional[Any]): Input supplied at creation.

        Returns:
            Any: A fresh, deep-copied context.
        """
        raw = machine.initial_context
        if callable(raw):
            produced = raw({"input": input})
            return copy.deepcopy(produced) if produced is not None else {}
        # ⚡ A flat dict of immutable scalars (the overwhelmingly common
        #    initial context, decided once at build: `context_is_flat`) is
        #    copied with `dict()` -- 11x cheaper than `deepcopy` and
        #    observationally identical, since there is nothing nested to
        #    alias. Anything else keeps the deep copy.
        context = dict(raw) if machine.context_is_flat else copy.deepcopy(raw)
        # 📥 Expose input to the machine even without a context factory.
        #    Deliberately ONLY under `context["input"]` (0.7.x contract):
        #    letting input overwrite declared keys would make
        #    `Interpreter(m, input=untrusted)` a context-injection vector
        #    (review F11). A child wanting its keys filled from the parent
        #    declares a `context` factory -- see `InvokeDefinition.input`.
        if input is not None and isinstance(context, dict):
            context.setdefault("input", input)
        return context

    # -------------------------------------------------------------------------
    # 🔍 Public Properties & Methods
    # -------------------------------------------------------------------------

    @property
    def current_state_ids(self) -> Set[str]:
        """Gets a set of the string IDs of all currently active atomic states.

        This property is the primary way to check the current state of the
        machine from outside the interpreter. Since a machine can be in
        multiple states at once (due to parallel states), this always
        returns a set of the most specific, leaf-node state identifiers.

        Returns:
            Set[str]: A set of unique string identifiers for the active atomic
            or final leaf states.
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    @property
    def active_state_ids(self) -> Set[str]:
        """Alias of :attr:`current_state_ids`.

        🏛️ Architecture decision: this name is used throughout the README and
        the `docs/` guides, but was never implemented — every documented
        example raised `AttributeError`. Rather than rewrite ~130 published
        snippets (and break anyone who copied them), the documented name is
        provided as a first-class alias. `current_state_ids` remains the
        canonical spelling used internally.

        Returns:
            Set[str]: A set of unique string identifiers for the active atomic
            or final leaf states.
        """
        return self.current_state_ids

    @property
    def is_running(self) -> bool:
        """Indicates whether the interpreter is currently running.

        Convenience wrapper over :attr:`status`, matching the documented
        public API.

        Returns:
            bool: `True` between a successful `start()` and a `stop()`.
        """
        return self.status == "running"

    # -------------------------------------------------------------------------
    # 🔭 Observation & Introspection
    # -------------------------------------------------------------------------

    @property
    def value(self) -> Union[str, Dict[str, Any]]:
        """The active configuration in XState's hierarchical ``value`` form.

        * atomic / final state  -> its key, e.g. ``"booking"``
        * compound state        -> ``{"life": "booking"}``
        * parallel state        -> one key per region, recursively
        * not started           -> ``{}``
        * mid-transition        -> the deepest ACTIVE ancestor's key for a
          compound whose child is momentarily absent (never raises)

        🏛️ Architecture decision (#58): `current_state_ids` is a flat set of
        leaf ids -- exactly right for ``"x" in ids`` checks and deliberately
        unchanged. But a UI, a metrics label or a ``matches({...})`` call
        needs the TREE, and rebuilding it from dotted ids breaks the moment
        a key contains a dot. This walks `StateNode`s, so ``"v2.0"`` is a
        key, not two path segments. Derived on every read; never persisted
        as truth (the snapshot carries it for consumers, restore ignores it).

        Returns:
            Union[str, Dict[str, Any]]: The state value.
        """
        if not self._active_state_nodes:
            return {}
        return self._value_of(self.machine)

    def _value_of(self, node: StateNode) -> Union[str, Dict[str, Any]]:
        """Recursive worker for :attr:`value`; *node* must be active.

        Returns the value of *node*'s active DESCENDANTS. For the root that
        is the whole tree; for a compound child it is what sits under the
        child's key.
        """
        active = self._active_state_nodes
        if node.type == "parallel":
            return {
                key: self._value_of(child)
                for key, child in node.states.items()
                if child in active
            }
        # 🌿 Compound: normally exactly one active child. But `value` is
        #    read from plugins, entry/exit actions and periodic snapshotters
        #    WHILE a transition is unwinding -- `_exit_states` discards the
        #    leaf before its ancestor, and `_enter_states` adds the parent
        #    before descending -- so "compound with no active child" is a
        #    routine transient, not corruption. Raising here made
        #    `get_snapshot()` throw on a healthy machine (review F1).
        child = next((c for c in node.states.values() if c in active), None)
        if child is None:
            # Momentarily childless. The deepest active node is `node`
            # itself; represent it as a LEAF (its key), the same shape an
            # atomic state has, so callers never see a half-tree.
            return node.key if node is not self.machine else {}
        if child.is_atomic or child.is_final or self._is_childless(child):
            return child.key
        return {child.key: self._value_of(child)}

    def _is_childless(self, node: StateNode) -> bool:
        """True when a compound/parallel *node* has no active child (F1)."""
        active = self._active_state_nodes
        return not any(c in active for c in node.states.values())

    def matches(self, state: Union[str, Dict[str, Any]]) -> bool:
        """Reports whether a state is part of the active configuration.

        Accepts either form XState's ``snapshot.matches()`` accepts:

        * a **string** -- a fully-qualified id (``"machine.parent.child"``),
          the same with a leading ``#``, or a trailing partial path
          (``"parent.child"``);
        * a **dict** -- a partial :attr:`value` tree, e.g.
          ``{"protection": {"risk": "armed"}}``. Every key named must be
          active; a leaf given as a string matches when that child (or
          any of ITS descendants) is active.

        Matching an ancestor returns `True` when any descendant is active.

        Args:
            state: The state to test for.

        Returns:
            bool: `True` if the state (or one of its descendants) is active.
        """
        if isinstance(state, dict):
            return self._matches_value(self.machine, state)
        if not state:
            return False
        target = state[1:] if state.startswith("#") else state
        for node in self._active_state_nodes:
            if node.id == target or node.id.endswith("." + target):
                return True
        return False

    def _matches_value(
        self, node: StateNode, pattern: Union[str, Dict[str, Any]]
    ) -> bool:
        """Recursive worker for the dict form of :meth:`matches`."""
        active = self._active_state_nodes
        if isinstance(pattern, str):
            child = node.states.get(pattern)
            return child is not None and child in active
        for key, sub in pattern.items():
            child = node.states.get(key)
            if child is None or child not in active:
                return False
            if not self._matches_value(child, sub):
                return False
        return True

    def has_tag(self, tag: str) -> bool:
        """Reports whether any active state declares the given tag.

        Args:
            tag (str): The tag to look for.

        Returns:
            bool: `True` if an active state carries the tag.
        """
        return any(tag in node.tags for node in self._active_state_nodes)

    @property
    def tags(self) -> Set[str]:
        """The union of tags across every active state.

        Returns:
            Set[str]: All tags currently in effect.
        """
        tags: Set[str] = set()
        for node in self._active_state_nodes:
            tags |= node.tags
        return tags

    def get_meta(self) -> Dict[str, Any]:
        """Collects the `meta` of every active state, keyed by state id.

        Returns:
            Dict[str, Any]: Mapping of state id to that state's `meta`.
        """
        return {
            node.id: node.meta
            for node in self._active_state_nodes
            if node.meta
        }

    def can(self, event: Union[str, Event, Dict[str, Any]]) -> bool:
        """Reports whether an event would cause a transition right now.

        Guards are evaluated, so this is an accurate prediction rather than a
        purely structural check. It has no side effects on the configuration.

        Args:
            event (Union[str, Event, Dict[str, Any]]): The event to test.

        Returns:
            bool: `True` if at least one transition would be taken.
        """
        event_obj = self._coerce_event(event)
        try:
            return bool(self._select_transitions(event_obj))
        except Exception:
            logger.exception(
                "🔥 can() failed while evaluating '%s'; reporting False.",
                event_obj.type,
            )
            return False

    @staticmethod
    def _coerce_event(
        event: Union[str, Event, Dict[str, Any], AfterEvent, DoneEvent],
    ) -> AnyEvent:
        """Normalises the accepted event spellings into an event object.

        Args:
            event: A type string, a mapping with a `type` key, or an event.

        Returns:
            AnyEvent: The normalised event.

        Raises:
            TypeError: If the value cannot be interpreted as an event.
        """
        if isinstance(event, (Event, AfterEvent, DoneEvent, ErrorEvent)):
            return event
        if isinstance(event, str):
            return Event(type=event)
        if isinstance(event, dict):
            event_type = event.get("type")
            if not isinstance(event_type, str):
                raise TypeError(
                    "❌ Event dict must contain a string 'type' key."
                )
            payload = {k: v for k, v in event.items() if k != "type"}
            return Event(type=event_type, payload=payload)
        raise TypeError(f"❌ Unsupported event type: {type(event).__name__}")

    def subscribe(
        self, listener: Callable[["BaseInterpreter[Any]"], None]
    ) -> Callable[[], None]:
        """Registers a listener invoked after every settled change.

        Mirrors XState's ``actor.subscribe()``. The listener receives this
        interpreter, from which `current_state_ids`, `context` and `status`
        can be read.

        Args:
            listener (Callable): Called after each transition and on
                completion.

        Returns:
            Callable[[], None]: An unsubscribe function.
        """
        self._subscribers.append(listener)

        def _unsubscribe() -> None:
            """Removes the listener if it is still registered."""
            if listener in self._subscribers:
                self._subscribers.remove(listener)

        return _unsubscribe

    def _notify_subscribers(self) -> None:
        """Invokes every subscriber, isolating listener failures.

        📝 A listener raising must not corrupt the machine, so exceptions are
        logged and swallowed — the same contract XState adopted in v5.20.2 for
        emitted-event listeners.
        """
        for listener in list(self._subscribers):
            try:
                listener(self)
            except Exception:
                logger.exception(
                    "🔥 Subscriber raised while observing '%s'; ignoring.",
                    self.id,
                )

    @property
    def plugins(self) -> List[PluginBase["BaseInterpreter[Any]"]]:
        """The list of plugin instances attached to this interpreter.

        Assigning to this property replaces the whole set of plugins, which is
        the form used in the documentation::

            interpreter.plugins = [LoggingInspector()]

        📝 Returns a shallow copy. Mutating the returned list does not affect
        the interpreter — use assignment or :meth:`use` to register plugins.
        Returning the live list would let `interpreter.plugins.append(...)`
        bypass the type validation performed by the setter.

        📝 Returns the plugin objects the caller registered, NOT the internal
        error-containment wrappers. Leaking wrappers would break `is`
        comparisons, `isinstance(p, PluginBase)`, and attribute access on the
        user's own plugin object.

        Returns:
            List[PluginBase]: A copy of the currently registered plugins.
        """
        return [
            item.wrapped if isinstance(item, _SafePlugin) else item
            for item in self._plugins
        ]

    @plugins.setter
    def plugins(self, value: List[PluginBase["BaseInterpreter[Any]"]]) -> None:
        """Replaces the registered plugins.

        Args:
            value (List[PluginBase]): The plugins to register.

        Raises:
            TypeError: If `value` is not a list/tuple, or if any element does
                not implement the plugin hook interface.
        """
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                "❌ 'plugins' must be assigned a list of plugin instances."
            )
        # 🛡️ Validate elements. Without this the failure surfaces later as an
        #    AttributeError from deep inside event processing, pointing at
        #    interpreter internals rather than the offending assignment.
        #
        # 🏛️ Architecture decision: the check is *structural* (does it provide
        # the hooks?) rather than a strict `isinstance(PluginBase)`. `use()`
        # has always accepted any duck-typed object exposing the hooks, and the
        # two entry points into `_plugins` must not disagree — otherwise
        # `interpreter.use(p)` would succeed where `interpreter.plugins = [p]`
        # raises, for the very same object.
        required_hooks = ("on_transition", "on_event_received")
        for item in value:
            if not all(
                callable(getattr(item, h, None)) for h in required_hooks
            ):
                raise TypeError(
                    "❌ 'plugins' elements must implement the plugin hook "
                    f"interface (e.g. subclass PluginBase); got "
                    f"{type(item).__name__}."
                )
        # 🧷 `_SafePlugin` is a `__getattr__` proxy that forwards every hook
        #    with error containment; it cannot subclass `PluginBase` (the
        #    base's real no-op methods would shadow the proxy). It IS
        #    plugin-shaped, so the cast records that fact for the checker.
        self._plugins = [
            cast(PluginBase["BaseInterpreter[Any]"], _SafePlugin(item))
            for item in value
        ]

    def use(
        self: TInterpreter, plugin: PluginBase["BaseInterpreter[Any]"]
    ) -> TInterpreter:
        """Registers a plugin with the interpreter via the Observer pattern.

        Plugins hook into the interpreter's lifecycle (e.g., `on_transition`,
        `on_guard_evaluated`) to add cross-cutting concerns like logging,
        analytics, or state persistence without modifying the core interpreter
        logic. This promotes a clean and extensible architecture.

        Args:
            plugin: The plugin instance to register.

        Returns:
            The interpreter instance (`self`) with the correct subclass type
            to allow for convenient and type-safe method chaining.
        """
        self._plugins.append(
            cast(PluginBase["BaseInterpreter[Any]"], _SafePlugin(plugin))
        )
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )
        return self

    # -------------------------------------------------------------------------
    # 📸 Snapshot & Persistence API (Memento Pattern)
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON-serializable snapshot of the interpreter's state.

        This method implements the Memento design pattern by capturing the
        essential state of the interpreter (its status, context, and active
        states) without exposing its internal implementation details. The
        resulting JSON string can be persisted to a file, database, or sent
        over a network.

        Returns:
            str: A JSON string representing the interpreter's current state.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = self.get_persisted_snapshot()
        # Use a default handler to gracefully handle non-serializable types.
        json_snapshot = json.dumps(snapshot, indent=2, default=str)
        if logger.isEnabledFor(logging.DEBUG):
            # 🔒 #160: the raw blob carries the whole `context`. Log a
            #    REDACTED rendering -- turning on DEBUG in staging must not
            #    write every secret in context to the log, with or without
            #    a `LoggingInspector` attached.
            from .plugins import redact

            logger.debug(
                "🖼️ Snapshot for '%s' captured: %s",
                self.id,
                json.dumps(redact(snapshot), indent=2, default=str),
            )
        return json_snapshot

    def _report_unresolved_target(
        self, action: str, to: Any, undelivered: Any
    ) -> None:
        """An addressed event reached no live actor (#133): `sendTo` and
        `forwardTo` share this so the two siblings cannot drift.

        An accepted-for-delivery event with no destination is a DROP, and
        every other drop site fires `on_event_dropped`. It is also recorded
        as this step's SOFT error -- the transition still commits (its other
        actions ran), but the epilogue must not report a clean step, so a
        `Receipt` / `last_error` shows the transition did not do what it
        said. `_step_soft_error` survives the epilogue's
        `last_transition_ok = True` reset.
        """
        logger.warning(
            "⚠️ %s could not resolve target %r; event '%s' dropped.",
            action,
            to,
            getattr(undelivered, "type", undelivered),
        )
        for plugin in self._plugins:
            plugin.on_event_dropped(self, undelivered, "unresolved_target")
        self._step_soft_error = ActorSpawningError(
            f"{action} target {to!r} did not resolve to a live actor; "
            f"'{getattr(undelivered, 'type', undelivered)}' was not delivered."
        )

    def _persist_event_reporting(self, event: Any) -> Dict[str, Any]:
        # 🔔 #159: `persist_event` raises `SnapshotSerializationError` (#131)
        #    for a pending event with non-JSON data; this is the one place it
        #    enters the snapshot, so report it via `on_snapshot_error` before
        #    re-raising -- the caller still gets the exception.
        try:
            return persist_event(event)
        except SnapshotSerializationError as exc:
            self._report_snapshot_error(exc)
            raise

    def _prepare_event_reporting(self, raw: Any, **payload: Any) -> AnyEvent:
        # 🔔 #159: the public entry points (`send`, `send_threadsafe`,
        #    `send_events`) go through this so a plugin bound to every hook
        #    sees a refused event; the caller still gets `InvalidEventError`.
        # ⚡ `str` is the overwhelmingly common shape and cannot be invalid
        #    (a non-empty str IS an event type; an empty one is caught by
        #    `_prepare_event`); skip the try/except frame for it.
        if type(raw) is str and raw:
            return Event(type=raw, payload=payload)
        try:
            return self._prepare_event(raw, **payload)
        except InvalidEventError as exc:
            self._report_invalid_event(exc, raw)
            raise

    def _report_snapshot_error(self, exc: BaseException) -> None:
        """Fire `on_snapshot_error` before a snapshot refusal propagates (#159)."""
        for plugin in self._plugins:
            plugin.on_snapshot_error(self, exc)

    def _report_invalid_event(self, exc: BaseException, raw: Any) -> None:
        """Fire `on_invalid_event` before an `InvalidEventError` propagates (#159)."""
        for plugin in self._plugins:
            plugin.on_invalid_event(self, exc, raw)

    def _report_resolve_error(self, exc: BaseException, event: Any) -> None:
        """Fire `on_resolve_error` for an unresolvable transition target (#134).

        The third per-transition failure category alongside
        `on_action_error` and `on_guard_error`; observability code no longer
        has to poll `last_error` for this one case.
        """
        for plugin in self._plugins:
            plugin.on_resolve_error(self, exc, event)

    def _detach_clock(self) -> None:
        """Unregister this interpreter's settle hook from a `SimulatedClock`
        (#115). Called from both engines' `_teardown`. Every restored /
        restarted interpreter used to leave its bound method in the clock's
        settler list forever, keeping the whole object graph alive and
        growing per-tick settle cost without bound."""
        detach = getattr(self.clock, "_detach", None)
        if callable(detach):
            for hook in (
                getattr(self, "_settle_for_clock", None),
                getattr(self, "tick", None),
            ):
                if hook is not None:
                    detach(hook)

    def _publish_soft_step_error(self) -> None:
        """Surface a non-fatal built-in failure recorded mid-step (#133).

        A `sendTo` whose target does not resolve cannot roll the transition
        back -- the other actions ran and the target state was entered --
        but the step did not do what the config claimed. Both transition
        epilogues (external and internal) call this after their own
        `last_transition_ok = True` reset, so the receipt / `last_error`
        report the failure on the same channel an action error uses.
        """
        soft = self._step_soft_error
        if soft is not None:
            self._step_soft_error = None
            self.last_transition_ok = False
            self._last_action_error = soft

    def _repair_configuration(self) -> None:
        """Make the live configuration legal: every active node's ancestors
        are active too (#112).

        A settling pass that trips its budget mid-microstep can leave a leaf
        whose parent chain was exited but never re-entered. `from_snapshot`
        already re-derives ancestors from leaves, so a persist/restore
        silently "fixed" the live machine -- meaning the two disagreed.
        Apply the same rule in place so what runs is what would restore.
        """
        for node in list(self._active_state_nodes):
            ancestor = node.parent
            while ancestor is not None:
                self._active_state_nodes.add(ancestor)
                ancestor = ancestor.parent

    def _await_settled_for_snapshot(self, timeout_s: float = 0.5) -> bool:
        """Block (briefly) until this actor's in-flight step finishes.

        Only used when snapshotting a CHILD recursively (#102), and only
        when that child runs on a DIFFERENT thread from the caller (a
        non-blocking `SyncInterpreter` actor on its pump thread), because
        that is the only case in which waiting can let it progress. A
        child on the caller's own thread (an async child on the same event
        loop, a blocking sync child) cannot advance while the caller spins
        -- #184: an earlier version did exactly that on the event-loop
        thread, burned the full budget and then returned the torn blob
        anyway. Such a child is refused instead (see the caller).

        🛡️ #183: the wait is for SETTLED, not merely legal. Inside an entry
        action the configuration is legal while the context is
        half-written; a snapshot there is torn on the read side (#169).

        Returns:
            bool: ``True`` when the child settled within the budget.
        """
        deadline = time.monotonic() + timeout_s
        while self._step_in_flight() and time.monotonic() < deadline:
            time.sleep(0.0005)
        return not self._step_in_flight()

    def _step_thread_ident(self) -> Optional[int]:
        """Engine hook: ident of the thread that runs this actor's steps, or
        ``None`` when steps run on whichever thread calls in (#183/#184)."""
        return None

    def _step_in_flight(self) -> bool:
        """Engine hook: is a macrostep currently executing? (#102)"""
        return bool(
            getattr(self, "_processing", False)
            or getattr(self, "_is_processing", False)
        )

    def _configuration_is_legal(self) -> bool:
        """SCXML configuration legality: exactly one active leaf per region.

        🏛️ #142 / #143: `_active_leaf_present` ("some atomic node is
        active") is not legality. In a `parallel` machine one region can
        be mid-transition with no leaf while another region's leaf keeps
        the any-leaf test true. The rule is recursive:

        * an active **atomic/final** node is legal;
        * an active **compound** node is legal iff exactly one of its
          children is active and that child is legal;
        * an active **parallel** node is legal iff every non-history
          child is active and legal.

        The machine root is a compound (or parallel) node like any other.
        An empty configuration is illegal.
        """
        active = self._active_state_nodes
        if not active:
            return False

        def legal(node: StateNode) -> bool:
            if node.type == "parallel":
                regions = [
                    c for c in node.states.values() if c.type != "history"
                ]
                return bool(regions) and all(
                    c in active and legal(c) for c in regions
                )
            if node.states and node.type != "final":
                live = [c for c in node.states.values() if c in active]
                return len(live) == 1 and legal(live[0])
            return True

        return legal(self.machine)

    def _active_leaf_present(self) -> bool:
        """``True`` when the configuration contains at least one atomic
        state -- i.e. it is a legal SCXML configuration (#102/#108)."""
        return any(
            not node.states or node.is_final
            for node in self._active_state_nodes
            if node is not self.machine
        )

    def get_persisted_snapshot(
        self, _seen: Optional[Set[int]] = None
    ) -> Dict[str, Any]:
        """Returns a deep, JSON-serialisable snapshot as a dictionary.

        Mirrors XState's ``actor.getPersistedSnapshot()``. Unlike the earlier
        shallow form, this captures the *whole* actor hierarchy.

        Raises:
            SnapshotMidStepError: if a macrostep is in flight (#102). Between
                a transition's exit set and entry set the configuration has
                no leaf; persisting that would restore as a permanently inert
                machine reporting ``running``.

        🏛️ Architecture decision: child actors were previously omitted
        entirely. A parent with live children serialised to just
        ``{status, context, state_ids}`` and restoring produced an actor with
        zero children — silent, unrecoverable data loss for anyone persisting
        a workflow. Recording actors recursively (plus history and output)
        makes a snapshot a faithful representation of the machine.

        Returns:
            Dict[str, Any]: The persisted snapshot.
        """
        # 🛡️ #102: a snapshot is only meaningful at a macrostep boundary.
        #    `_step_in_flight()` is engine-specific (`_processing` on the
        #    async engine, `_is_processing` on the sync one) and is True
        #    exactly while exit -> actions -> enter is open.
        #
        #    For the ROOT of the call (``_seen is None``) that is a caller
        #    error and is refused. For a CHILD actor reached recursively the
        #    parent is settled and the caller cannot see the child's step;
        #    a non-blocking sync child runs on its own thread and may be
        #    mid-microstep at any instant. Wait briefly for it to settle
        #    rather than fail the parent's whole snapshot on a race.
        # 🛡️ #142: the test is configuration LEGALITY (one leaf per
        #    region), not "some leaf exists" -- in a parallel machine one
        #    region mid-transition left the other region's leaf to satisfy
        #    the any-leaf test, and the snapshot recorded a torn region.
        # 🛡️ #169: at the ROOT, "in flight" alone refuses. Legality is a
        #    necessary condition, not a sufficient one: inside an ENTRY
        #    action the new leaf is already active (legal) while the context
        #    that entry is still writing is half-applied -- a snapshot there
        #    persisted `filled` with `filled_qty=0` and restored cleanly.
        #    The documented contract ("from inside an action -> refused")
        #    is what callers rely on; legality stays the test for the
        #    bounded wait on a CHILD caught mid-step by its parent.
        if self._step_in_flight():
            if _seen is None:
                exc = SnapshotMidStepError(self.id)
                self._report_snapshot_error(exc)  # #159
                raise exc
            # 👶 A CHILD caught mid-step by its parent's snapshot (#183):
            #    its half-applied context would be harvested into the
            #    parent's blob and restore cleanly, because its
            #    configuration is legal. If the child steps on another
            #    thread, wait (bounded) for it to settle; if it steps on
            #    THIS thread it cannot settle while we hold the thread
            #    (#184), so the parent's snapshot is refused -- honestly,
            #    and instantly, rather than after a blocked half-second.
            own = self._step_thread_ident()
            settled = (
                own is not None
                and own != threading.get_ident()
                and self._await_settled_for_snapshot()
            )
            if not settled:
                exc = SnapshotMidStepError(self.id, child=True)
                self._report_snapshot_error(exc)  # #159
                raise exc
        # 🔁 Guard against an actor cycle. The registry makes a cycle
        #    constructible, and unbounded recursion would blow the stack
        #    instead of failing cleanly.
        seen = _seen if _seen is not None else set()
        if id(self) in seen:
            return {"ref": self.id, "cycle": True}
        seen = seen | {id(self)}

        return {
            # 📦 #45: envelope. `version` is the payload LAYOUT version (see
            #    persistence.SNAPSHOT_VERSION), not the package version.
            #    `machine_hash` lets `from_snapshot` refuse a blob taken from
            #    a machine whose structure has since changed.
            "version": persistence.SNAPSHOT_VERSION,
            "machine_id": self.machine.id,
            "machine_hash": self.machine.structure_hash,
            "taken_at": time.time(),
            "status": self.status,
            # 🧊 Deep-copy so the snapshot is a true point-in-time capture.
            #    Returning the live dict made later execution retroactively
            #    rewrite an already-taken snapshot.
            "context": copy.deepcopy(self.context),
            "state_ids": sorted(self.current_state_ids),
            # 🌲 #58: the hierarchical form, for downstream consumers (UIs,
            #    dashboards) that read snapshots. DERIVED: `from_snapshot`
            #    rebuilds from `configuration` and ignores this key.
            "value": self.value,
            # 🌳 Full configuration, so ancestors are restored exactly rather
            #    than re-derived from leaves.
            "configuration": sorted(
                node.id for node in self._active_state_nodes
            ),
            "output": self.output,
            "error": str(self.error) if self.error is not None else None,
            # 📨 Deferred events survive a crash: drained on start()
            #    before any invoke is re-driven.
            "deferred": [
                self._persist_event_reporting(e) for e in self._deferred_events
            ],
            # 📬 #47: the inbox. Events `send()` ACCEPTED but has not yet
            #    processed. Without this a crash between accept and process
            #    lost them with no trace; with it a restored machine resumes
            #    with its mailbox intact.
            # 🏛️ #86/#87: EVERY kind round-trips -- `DoneEvent` /
            #    `ErrorEvent` / `AfterEvent` and engine-minted `Event`s
            #    carry a `kind` discriminator so an accepted invoke failure
            #    is not silently dropped and provenance survives a restore.
            "pending_events": [
                self._persist_event_reporting(e) for e in self.pending_events
            ],
            # 🕰️ Remembered history, so a restored machine can still honour a
            #    later transition to a history state.
            "history": {
                parent_id: sorted(node.id for node in nodes)
                for parent_id, nodes in self._history.items()
            },
            # 👶 Recursive child-actor snapshots, keyed by actor id.
            "actors": self._persist_actors(seen),
            # 🌐 Persist systemId -> actor-id so `sendTo("sys", ...)` still
            #    resolves after a restore. Without this the registry came back
            #    empty and every systemId-addressed event was silently dropped.
            "system": {
                system_id: actor.id
                for system_id, actor in self._system.items()
            },
        }

    def _persist_actors(self, seen: Set[int]) -> Dict[str, Any]:
        """Serialises child actors, including any that could not be restored.

        🏛️ Architecture decision: actors parked in `_pending_actor_snapshots`
        (their service was absent when this interpreter was restored) are
        re-emitted verbatim. Without this the "preserved" snapshot was
        write-only: the next save silently dropped the child, its context, its
        own grandchildren and its history — reintroducing exactly the data
        loss deep persistence was written to prevent, one round-trip later.

        Args:
            seen (Set[int]): Interpreter ids already visited, for cycle
                detection.

        Returns:
            Dict[str, Any]: Persisted records keyed by actor id.
        """
        records: Dict[str, Any] = {
            actor_id: {
                "machine_id": actor.machine.id,
                # 🔑 Persist the originating service key. Deriving it from the
                #    actor id is unreliable: an explicit `id` param replaces
                #    the key segment entirely.
                "src": self._actor_sources.get(actor_id),
                "snapshot": actor.get_persisted_snapshot(seen),
            }
            for actor_id, actor in self._actors.items()
        }
        # ♻️ Carry forward actors we could not rebuild, so they survive
        #    an arbitrary number of save/restore cycles.
        for actor_id, record in self._pending_actor_snapshots.items():
            records.setdefault(actor_id, record)
        return records

    def _resolve_actor_machine(
        self, service_key: Optional[str]
    ) -> Optional[MachineNode[Any]]:
        """Finds the machine definition for a persisted child actor.

        Args:
            service_key (Optional[str]): The `services` key the actor was
                originally spawned from.

        Returns:
            Optional[MachineNode]: The child's machine definition, or `None`
            when the service is not registered on this interpreter.
        """
        if service_key is None:
            return None
        source = self.machine.logic.services.get(service_key)
        if source is None:
            return None
        if isinstance(source, MachineNode):
            return source
        if callable(source):
            try:
                produced = source(
                    self, self.context, system_event("__restore__")
                )
            except Exception:
                logger.exception(
                    "🔥 Actor factory for '%s' raised during restore.",
                    service_key,
                )
                return None
            if isinstance(produced, MachineNode):
                return produced
        return None

    @classmethod
    def from_snapshot(
        cls: Type[TInterpreter],
        snapshot_str: str,
        machine: MachineNode[Any],
        *,
        verify_machine_hash: bool = True,
        restart_services: bool = False,
        restart_timers: Optional[bool] = None,
        clock: Optional[Clock] = None,
    ) -> TInterpreter:
        """Creates and restores an interpreter instance from a saved snapshot.

        This factory method reconstructs an interpreter's state from a JSON
        snapshot. It deserializes the snapshot, finds the corresponding state
        nodes in the provided machine definition, and sets the context and
        status, effectively restoring the machine to a previous point in time.

        Note:
            By default this is a STATIC restoration: entry actions are not
            re-run and no invoked service or `after` timer is restarted, so
            a machine snapshotted mid-`invoke` comes back parked in that
            state. Inspect what is parked with :meth:`pending_invocations`;
            opt in to re-driving it with ``restart_services=True`` (#44).

        Args:
            snapshot_str (str): The JSON string previously generated by
                `get_snapshot()`.
            machine (MachineNode[TContext]): The corresponding
                `MachineNode` definition that the snapshot belongs to.
            verify_machine_hash (bool): When `True` (default) refuse a
                snapshot whose recorded ``machine_hash`` differs from
                *machine*'s -- the machine's structure changed since the
                snapshot was taken. Pass `False` after migrating the payload
                for a known-compatible change. No-op for unversioned
                (0.7.x) snapshots, which carry no hash.
            restart_services (bool): When `True`, `start()` on the restored
                interpreter re-invokes every `invoke` in the restored
                configuration -- **from scratch, not resumed** (#44). The
                service therefore runs again; for an order placement that
                means a client-supplied idempotency key. Opt-in for exactly
                that reason. Default `False` keeps the static restore.

                ⚠️ **`status` is not a liveness signal between
                `from_snapshot()` and `start()`** (#135). The restored
                object reports the persisted ``"running"`` immediately --
                meaning "the state machine is in a running configuration",
                not "a loop is driving it". Nothing is re-invoked and no
                timer is re-armed until `start()` runs. In that window (and
                after a static restore) check `has_dormant_invocations` and
                `has_dormant_timers`, which are `True` exactly while work
                the configuration relies on is parked.
            restart_timers (Optional[bool]): When `True`, `start()` re-arms
                every `after` timer of the restored configuration **from
                zero** (#128) -- a snapshot records that a timer was pending,
                not how far along it was. Defaults to the value of
                `restart_services`, so "bring it all back" is one flag.
            clock (Optional[Clock]): Clock for the restored interpreter
                (#117). The other half of construct-then-restore: without
                it every restored machine ran on `RealClock`, which broke
                `SimulatedClock`-based deterministic replay.

        Returns:
            BaseInterpreter[TContext]: A new interpreter instance
                restored to the snapshot's state.

        Raises:
            StateNotFoundError: If a state ID from the snapshot cannot be found
                in the provided machine definition.
            InvalidConfigError: If the snapshot string is not valid JSON, or
                does not decode to a JSON object.
            SnapshotVersionError: The snapshot was written by a newer
                library version.
            SnapshotDriftError: The snapshot belongs to a different machine
                id, or the machine's structure has changed.
        """
        logger.info(
            "🔄 Restoring interpreter for machine '%s' from snapshot...",
            machine.id,
        )
        # 🧯 Wrap the decode error. Snapshots come back from Redis, disk or a
        #    queue, so corruption is an ordinary runtime condition callers are
        #    expected to handle. Leaking `json.JSONDecodeError` meant
        #    `except XStateMachineError` — the documented way to catch this
        #    library's failures — silently missed it.
        # 🛡️ #146: a non-`str` payload (None, bytes, an already-parsed
        #    dict) raised TypeError from `json.loads` itself.
        if not isinstance(snapshot_str, str):
            raise SnapshotCorruptError(
                f"Snapshot payload must be a JSON string, got "
                f"{type(snapshot_str).__name__}."
            )
        try:
            snapshot = json.loads(snapshot_str)
        except json.JSONDecodeError as e:
            logger.error("❌ Invalid JSON in snapshot string: %s", e)
            raise InvalidConfigError(f"Snapshot is not valid JSON: {e}") from e

        if not isinstance(snapshot, dict):
            raise InvalidConfigError(
                f"Snapshot must decode to a JSON object, got "
                f"{type(snapshot).__name__}."
            )

        # 📦 #45: envelope checks FIRST, before any state is touched, so a
        #    refused restore leaves nothing half-built behind.
        version = persistence.check_version(snapshot)
        persistence.check_identity(
            snapshot,
            machine,
            verify_hash=verify_machine_hash,
            version=version,  # #185: bypass keyed on declared version
        )
        snapshot = persistence.upcast(snapshot, version)

        # 🛡️ #110: validate the payload SHAPE before touching it, so a
        #    corrupted blob is a typed `SnapshotCorruptError` rather than a
        #    bare KeyError/AttributeError -- or, worse, silently accepted.
        persistence.check_shape(snapshot)

        # 🧪 Create a new instance of the correct interpreter class (sync/async)
        # ⏱️ #117: honour an injected clock -- the other half of the
        #    construct-then-restore lifecycle. Without it every restored
        #    machine ran on `RealClock`, breaking deterministic replay.
        interpreter = (
            cls(machine, clock=clock) if clock is not None else cls(machine)
        )
        # 🧊 #46: layer the persisted context over the machine's CURRENT
        #    defaults, and deep-copy so the caller's parsed dict does not
        #    alias live state. Persisted values win for every key present;
        #    defaults fill only keys the snapshot never had (e.g. a field
        #    added to the machine after the snapshot was written). The
        #    merge is deliberately SHALLOW: a recursive merge would
        #    resurrect nested keys the application intentionally deleted.
        restored = copy.deepcopy(snapshot["context"])
        if isinstance(interpreter.context, dict) and isinstance(
            restored, dict
        ):
            interpreter.context = {**interpreter.context, **restored}
        else:
            interpreter.context = restored
        # 🏛️ #135: `status` is restored as persisted -- "running" means the
        #    STATE MACHINE is in a running configuration, not that a loop is
        #    driving it. Liveness after a restore is `has_dormant_invocations`
        #    / `has_dormant_timers` (#128), documented on both. See the
        #    `restart_services` note in the docstring.
        interpreter.status = snapshot["status"]
        # ⏱️ #128: `after` timers are not persisted (a deadline is relative
        #    to a clock that no longer exists). Opt in to re-arming them from
        #    zero on `start()`; defaults to the `restart_services` choice so
        #    the common "bring it all back" call is one flag.
        interpreter._restart_timers_on_start = (
            restart_services if restart_timers is None else restart_timers
        )

        # 🌳 Reconstruct the set of active state nodes from their IDs.
        #    Prefer the full `configuration` when present (it includes
        #    ancestors); fall back to leaf ids for snapshots written by
        #    older versions.
        interpreter._active_state_nodes.clear()
        restore_ids = snapshot.get("configuration") or snapshot["state_ids"]
        for state_id in restore_ids:
            node = machine.get_state_by_id(state_id)
            if node:
                interpreter._active_state_nodes.add(node)
                # 🌲 Ancestors must be active too, otherwise the transition
                #    algorithm cannot resolve domains correctly.
                ancestor = node.parent
                while ancestor is not None:
                    interpreter._active_state_nodes.add(ancestor)
                    ancestor = ancestor.parent
                logger.debug("    ↳ Restored active state: '%s'", state_id)
            else:
                logger.error(
                    "❌ State ID '%s' from snapshot not found in machine '%s'.",
                    state_id,
                    machine.id,
                )
                raise StateNotFoundError(target=state_id)

        # 🏁 Restore completion output and any recorded error.
        # 🛡️ #143: the WRITE side refuses a leafless configuration (#102);
        #    the READ side must too, or a truncated `configuration` list
        #    restores as a `running` machine with no active leaf that is
        #    permanently inert. Legality is per REGION, not "any leaf".
        if (
            snapshot["status"] == "running"
            and not interpreter._configuration_is_legal()
        ):
            raise SnapshotCorruptError(
                "Snapshot is malformed: status is 'running' but the "
                "configuration has no active leaf in every region "
                f"(restored {sorted(n.id for n in interpreter._active_state_nodes)!r}). "
                "The 'configuration' list has lost its leaf entries."
            )

        interpreter.output = snapshot.get("output")
        recorded_error = snapshot.get("error")
        interpreter._deferred_events = [
            restore_event(d) for d in (snapshot.get("deferred") or [])
        ]
        # 📬 #47: re-enqueue the persisted inbox in original order.
        for record in snapshot.get("pending_events") or []:
            interpreter._enqueue_restored(restore_event(record))
        if recorded_error:
            # 📝 The original exception type cannot survive JSON, so the
            #    message is preserved in a dedicated wrapper. Without this a
            #    restored machine sat in `error` status with `error is None`,
            #    so no caller could discover what went wrong — the exact
            #    observability the error-snapshot feature exists to provide.
            interpreter.error = RestoredError(str(recorded_error))

        # 🕰️ Restore remembered history so a later transition to a history
        #    state still resolves after a restart.
        for parent_id, node_ids in (snapshot.get("history") or {}).items():
            nodes = [
                node
                for node in (machine.get_state_by_id(nid) for nid in node_ids)
                if node is not None
            ]
            if nodes:
                interpreter._history[parent_id] = nodes

        # 👶 Restore child actors. Their machine definitions are resolved from
        #    the parent's `services` registry, which is the same source the
        #    original spawn used.
        for actor_id, record in (snapshot.get("actors") or {}).items():
            child_machine = interpreter._resolve_actor_machine(
                record.get("src")
            )
            if child_machine is None:
                logger.warning(
                    "⚠️ Could not restore actor '%s': no matching service. "
                    "Its snapshot is preserved under _pending_actor_snapshots.",
                    actor_id,
                )
                interpreter._pending_actor_snapshots[actor_id] = record
                continue
            child = cls.from_snapshot(
                json.dumps(record["snapshot"], default=str),
                child_machine,
                verify_machine_hash=verify_machine_hash,
                restart_services=restart_services,
            )
            child.parent = interpreter
            child.id = actor_id
            interpreter._actors[actor_id] = child
            if record.get("src"):
                interpreter._actor_sources[actor_id] = record["src"]

        # 🌐 Re-register restored actors under their original systemIds.
        for system_id, actor_id in (snapshot.get("system") or {}).items():
            restored_actor = interpreter._actors.get(actor_id)
            if restored_actor is not None:
                interpreter._system[system_id] = restored_actor

        interpreter._restart_services_on_start = restart_services
        logger.info(
            "✅ Interpreter '%s' restored. States: %s, Status: '%s'",
            interpreter.id,
            interpreter.current_state_ids,
            interpreter.status,
        )
        return interpreter

    # -------------------------------------------------------------------------
    # 🔁 Dormant invokes after a restore (#44)
    # -------------------------------------------------------------------------
    def pending_invocations(self) -> List["PendingInvocation"]:
        """Invokes in the active configuration that have NO live service.

        After a static `from_snapshot` every `invoke` of a restored state is
        dormant: the configuration says the work is in flight, but nothing
        is running it. This is the truthful signal a health check needs, and
        the list an application re-drives on its own terms (check the
        exchange first, THEN decide) without walking `machine.states`.
        Empty on a live machine and after ``restart_services=True``.
        """
        return [
            PendingInvocation(state.id, inv.id, inv.src or "")
            for state in sorted(self._active_state_nodes, key=lambda s: s.id)
            for inv in state.invoke
            if not self._invocation_is_live(state, inv)
        ]

    @property
    def has_dormant_invocations(self) -> bool:
        """``True`` when the configuration claims work is in flight that
        nothing is actually running (#44).

        🏛️ Architecture decision: `status` stays ``"running"`` after a
        static `from_snapshot()` -- the machine IS processing events; it is
        the invokes that are parked. Introducing a new `status` value would
        break every consumer that switches on the existing four, so the
        liveness signal is a separate boolean instead. **`status` is not a
        liveness signal after a restore; check this (or
        :meth:`pending_invocations`) in health checks.**
        """
        return any(
            not self._invocation_is_live(state, inv)
            for state in self._active_state_nodes
            for inv in state.invoke
        )

    def _invocation_is_live(
        self, state: StateNode, invocation: InvokeDefinition
    ) -> bool:
        """Engine-specific: is a service/actor currently running for this?"""
        raise NotImplementedError  # pragma: no cover

    @property
    def has_dormant_timers(self) -> bool:
        """``True`` when an active state declares an ``after`` timer that is
        not currently armed (#128) -- the case after a static restore.

        `from_snapshot()` cannot know how much of a delay had elapsed, so
        it does not re-arm timers on its own. `start(restart_services=True)`
        (or `restart_timers=True`) re-arms them from zero; otherwise this
        flag tells a health check that a deadline the configuration relies
        on will never fire.
        """
        if not any(state.after for state in self._active_state_nodes):
            return False
        return not any(
            self._timer_handles.get(state.id)
            for state in self._active_state_nodes
            if state.after
        )

    def _rearm_dormant_timers(self) -> int:
        """Arm every ``after`` timer of the active configuration that has
        no live handle (#128). Returns how many were armed.

        Deadlines restart from zero: a snapshot records that a timer was
        pending, not how far along it was. That is the SCXML `<send delay>`
        contract -- scheduled relative to when the actor (re)starts -- and
        is strictly better than a timer that never fires.
        """
        armed = 0
        for state in list(self._active_state_nodes):
            if not state.after or self._timer_handles.get(state.id):
                continue
            self._schedule_state_timers(state)
            armed += 1
        return armed

    def _restart_dormant_invocations(self) -> None:
        """Re-invoke every dormant invoke through the normal entry path.

        Uses `_invoke_service` exactly as `_enter_states` does, so restarted
        work is owner-registered and exiting the state still cancels it.
        """
        for pending in self.pending_invocations():
            state = self.machine.get_state_by_id(pending.state_id)
            if state is None:  # pragma: no cover - configuration is trusted
                continue
            for invocation in state.invoke:
                if invocation.id != pending.invoke_id:
                    continue
                service = (
                    self.machine.logic.services.get(invocation.src)
                    if invocation.src
                    else None
                )
                if service is None:
                    raise ImplementationMissingError(
                        f"Service '{invocation.src}' referenced by state "
                        f"'{state.id}' is not registered."
                    )
                logger.info(
                    "🔁 Restarting dormant invoke '%s' (src '%s') in '%s'.",
                    invocation.id,
                    invocation.src,
                    state.id,
                )
                self._invoke_service(invocation, service, owner_id=state.id)

    # -------------------------------------------------------------------------
    # 📝 Abstract Methods (Template Method Hooks for Subclasses)
    # -------------------------------------------------------------------------
    # These methods define the "pluggable" parts of the state transition
    # algorithm. Concrete subclasses MUST override them to provide
    # mode-specific (synchronous or asynchronous) behavior.

    def start(
        self,
    ) -> Union[
        "BaseInterpreter[TContext]",
        Awaitable["BaseInterpreter[TContext]"],
    ]:
        """Starts the interpreter by entering the initial state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass (e.g., `Interpreter`, `SyncInterpreter`).
        """
        raise NotImplementedError(
            "Subclasses must implement the 'start' method."
        )

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter and cleans up resources.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'stop' method."
        )

    # -------------------------------------------------------------------------
    # 📬 Inbox (#47)
    # -------------------------------------------------------------------------
    # 🏛️ Architecture decision: `send()` ACCEPTS an event; processing happens
    # later (next loop turn on the async engine, end of the current macrostep
    # on the sync one). Between the two the event lives only in a private
    # queue -- invisible, not persisted, and thrown away by `stop()`. For a
    # machine on a critical path that is silent data loss. These hooks make
    # the inbox first-class: readable, drainable and part of the snapshot.

    @property
    def queue_depth(self) -> int:
        """Events accepted but not yet processed (#38). Read-only."""
        return len(self._snapshot_pending_events())

    @property
    def pending_events(
        self,
    ) -> Tuple[AnyEvent, ...]:
        """Events accepted by `send()` but not yet processed, in order."""
        return tuple(self._snapshot_pending_events())

    def _snapshot_pending_events(
        self,
    ) -> List[AnyEvent]:
        """Return the queue contents WITHOUT removing them. Engine-specific."""
        raise NotImplementedError  # pragma: no cover

    def _enqueue_restored(self, event: Event) -> None:
        """Place a persisted inbox event back on the queue (restore path)."""
        raise NotImplementedError  # pragma: no cover

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = False,
        priority: bool = False,
        **payload: Any,
    ) -> Any:
        """Sends an event to the running interpreter for processing.

        🧷 The engines refine the return type with overloads (`wait=True`
        gives a :class:`Receipt`, sync inline / async awaited). This base
        signature carries the same keyword flags so those overloads are
        true refinements, and an actor addressed as a `BaseInterpreter`
        can still be sent `wait=`/`priority=` without a checker error.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'send' method."
        )

    def send_events(
        self, events: List[Union[Dict[str, Any], Event, str]]
    ) -> Any:
        """Sends a list of events to the running interpreter for processing.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'send_events' method."
        )

    def _cancel_state_tasks(
        self, state: StateNode
    ) -> Union[None, Awaitable[None]]:
        """Cancels all background tasks associated with a given state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_cancel_state_tasks' method."
        )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Handles a delayed event (`after` transition).

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_after_timer' method."
        )

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Union[Callable[..., Any], "MachineNode[Any]"],
        owner_id: str,
    ) -> Union[None, Awaitable[None]]:
        """Handles an invoked service -- a callable, or a child MACHINE.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_invoke_service' method."
        )

    def _check_strict(self, event: Any) -> None:
        """Raise for an undeclared type or an invalid payload (#51).

        🏛️ Called SYNCHRONOUSLY at the call site of `send()` -- before the
        event is queued -- because the async `send()` is fire-and-forget: a
        violation raised later inside the run loop could never reach the
        caller. Also applied to the `raise` built-in so an internal typo is
        caught too. Engine-synthesised events are always known.

        Raises:
            UnknownEventError: `strict` and the type is undeclared.
            InvalidEventPayloadError: a schema is registered for the type
                and rejected the payload (applies regardless of `strict`).
        """
        # 🏛️ #79: engine-minted events are never "unknown"; a USER event
        #    is checked whatever it is called -- `Event("done.typo")` from
        #    application code is a typo like any other.
        # 🏛️ #79/#98: engine-minted events are never "unknown"; a USER
        #    event is checked whatever it is called. `is_known_event` no
        #    longer grants a by-name exemption, so a forged
        #    `done.invoke.NEVER` or `___xstate_x` is rejected like `TYPO`.
        # ⚡ Nothing to check for the common configuration: not strict and
        #    no schemas. Decided before the (comparatively costly)
        #    provenance test so the hot path is one attribute read.
        if not self.strict and not self.machine.event_schemas:
            return
        if is_system_event(event) or not isinstance(event, Event):
            return
        if self.strict and not self.machine.is_known_event(
            event.type, user_sent=True
        ):
            raise UnknownEventError(
                event.type, self.machine.id, sorted(self.machine.known_events)
            )
        schema = self.machine.event_schemas.get(event.type)
        if schema is not None:
            validate = getattr(schema, "validate", None)
            fn = validate if callable(validate) else schema
            try:
                fn(event.payload)
            except Exception as exc:  # noqa: BLE001 -- user validator
                raise InvalidEventPayloadError(event.type, exc) from exc

    #: Keyword arguments of `send()` that are NOT payload (#39). A dict-form
    #: event carrying one of these keys is honoured but warns, because the
    #: string-form `send("E", wait=True)` cannot express it as payload.
    _RESERVED_SEND_KWARGS: Tuple[str, ...] = ("wait", "priority")

    def _warn_reserved_payload_keys(self, event: Any) -> None:
        payload = getattr(event, "payload", None)
        # ⚡ `if payload` -- an empty dict (the overwhelmingly common
        #    `send("TYPE")` case) cannot clash; skip the comprehension.
        if payload and isinstance(payload, dict):
            clash = [k for k in self._RESERVED_SEND_KWARGS if k in payload]
            if clash:
                warnings.warn(
                    f"Event '{event.type}' payload uses reserved send() "
                    f"keyword(s) {clash}. They are kept in the payload for "
                    f"this dict-form send, but `send('{event.type}', "
                    f"{clash[0]}=...)` would be read as a send() option. "
                    f"Rename the key.",
                    DeprecationWarning,
                    stacklevel=4,
                )

    @staticmethod
    def _prepare_event(
        event_or_type: Union[str, Dict[str, Any], Any],
        **payload: Any,
    ) -> AnyEvent:
        """Normalizes various event inputs into a concrete `Event` object.

        This helper ensures that the interpreter can robustly handle events
        passed as strings, dictionaries, or `Event` instances. It uses
        duck-typing to handle a specific edge case where the library might be
        imported twice in a testing environment, resulting in two distinct
        `Event` class identities.

        Args:
            event_or_type (Union[str, Dict[str, Any], Any]): The event to be
                normalized. Can be:
                - A string (`"EVENT_TYPE"`)
                - A dictionary with a "type" key (`{"type": "EVENT_TYPE", ...}`)
                - An instance of `Event`, `DoneEvent`, or `AfterEvent`.
                - A duck-typed object with `.type` and `.payload` attributes.
            **payload (Any): Additional keyword arguments to be used as the
                event's payload if `event_or_type` is a string.

        Returns:
            AnyEvent: A concrete event object ready
            for processing.

        Raises:
            InvalidEventError: If the input cannot be resolved into a valid
                event -- a non-``str`` ``type``, a dict without ``type``, or
                an unsupported object (#113). A typed member of the
                documented hierarchy, so ``except XStateMachineError``
                catches it.
        """
        # 1️⃣ Input is a simple string: create a new Event.
        if isinstance(event_or_type, str):
            return Event(type=event_or_type, payload=payload)

        # 2️⃣ Input is a dictionary: convert to an Event.
        if isinstance(event_or_type, dict):
            data = event_or_type.copy()
            if "type" not in data:
                raise InvalidEventError(
                    "A dict event must carry a 'type' key; got keys "
                    f"{sorted(map(str, data))}."
                )
            event_type = data.pop("type")
            if not isinstance(event_type, str) or not event_type:
                raise InvalidEventError(
                    f"Event 'type' must be a non-empty str, got "
                    f"{type(event_type).__name__}: {event_type!r}."
                )
            # 🛡️ #161: the mapping form validates `type` and the KEY shape
            #    only. Non-`str` keys cannot be JSON-persisted (#131) and
            #    are almost certainly a caller bug; payload VALUES are the
            #    caller's -- their semantics are domain-specific and belong
            #    to `event_schemas` (#51), not to this shape check.
            bad_keys = [k for k in data if not isinstance(k, str)]
            if bad_keys:
                raise InvalidEventError(
                    f"Event '{event_type}' payload keys must be str; got "
                    f"{bad_keys!r}."
                )
            return Event(type=event_type, payload=data)

        # 3️⃣ Input is already a native Event instance: use as-is.
        if isinstance(
            event_or_type, (Event, DoneEvent, AfterEvent, ErrorEvent)
        ):
            return event_or_type

        # 4️⃣ Duck-typing: handle "foreign" Event objects (for testing robustness).
        if hasattr(event_or_type, "type") and hasattr(
            event_or_type, "payload"
        ):
            # Trust and forward as-is to preserve any subclass information.
            return event_or_type  # type: ignore[return-value]

        # 5️⃣ Anything else is an unsupported format.
        raise InvalidEventError(
            f"Unsupported event type passed to send(): {type(event_or_type).__name__}. "
            f"Pass a str, a dict with a 'type' key, or an Event."
        )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (The Template Method)
    # -------------------------------------------------------------------------

    def _resolve_target_state_node(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Resolves a transition's target string to a concrete StateNode."""
        root = self.machine
        parent = transition.source.parent
        target_str = transition.target_str

        if not target_str:
            return None

        logger.debug(
            "🔄 Resolving target state '%s' from source '%s'.",
            target_str,
            transition.source.id,
        )

        target_state: Optional[StateNode] = None

        # Standard resolution attempts
        resolution_attempts = [
            (target_str, transition.source),
            (target_str, parent) if parent else None,
            (target_str, root),
            (f"{root.id}.{target_str}", root),
        ]

        for tgt, ref in filter(None, resolution_attempts):
            try:
                target_state = resolve_target_state(tgt, ref)
                # 🚫 #59: do NOT write back to `transition.target_str`. The
                #    TransitionDefinition is shared by every interpreter of
                #    this machine; rewriting it to the qualified form from
                #    one interpreter changed what every other one saw, and
                #    raced under threads. The resolved node is what matters
                #    and it is returned; the original string stays intact.
                logger.debug(
                    "✅ Resolved '%s' via standard method: '%s'",
                    tgt,
                    target_state.id,
                )
                break
            except StateNotFoundError:
                logger.debug(
                    "    ↳ Failed standard resolution of '%s' from '%s'",
                    tgt,
                    ref.id,
                )
                continue

        if target_state:
            return target_state

        # 🔑 Exact top-level KEY. Keys may contain dots ("v2.0"), which the
        #    path-splitting resolver above cannot express; this is the one
        #    non-path lookup that is still unambiguous.
        exact = root.states.get(target_str)
        if exact is not None:
            logger.debug("✅ Resolved via exact top-level key: '%s'", exact.id)
            return exact

        # 🏛️ #34 (LC-06): there are deliberately NO further fallbacks.
        #
        #    Three used to follow here -- a `getattr(root, target)`, a scan of
        #    top-level states by LAST id segment, and an exhaustive walk of the
        #    whole tree by last segment. Short leaf names (`filled`, `done`,
        #    `idle`) recur in every real machine, so the walk was far more
        #    likely to find a WRONG match than no match: a transition in
        #    `order` targeting a non-existent `filled` moved the unrelated
        #    `audit` region to `audit.archive.filled` while `order` stayed
        #    put. XState and SCXML scope targets lexically (sibling / `#id` /
        #    `.child`); an unresolvable target is an error, never a search.
        #    `validation.resolve_strict` mirrors exactly this set of
        #    strategies, so build-time and runtime can never disagree.
        available = sorted(root.states.keys())
        logger.error(
            "🚫 Target '%s' from '%s' does not resolve. Top-level states in "
            "'%s': %s. Use a sibling key, '#%s.<path>' or '.<child>'.",
            target_str,
            transition.source.id,
            root.id,
            available,
            root.id,
        )
        return None

    async def _process_event(self, event: AnyEvent) -> None:
        """Executes a single, complete "step" of the SCXML algorithm.

        Selects the optimal transition set for `event` — one transition per
        orthogonal region — and executes each in turn.

        Args:
            event (AnyEvent): The event to process.
        """
        # 1. Select every transition this event triggers (one per region).
        self._pending_guard_error = None
        transitions = self._select_transitions(event)
        guard_error = self._pending_guard_error
        if guard_error is not None:
            self._pending_guard_error = None
        if not transitions:
            if guard_error is None:
                self._handle_unhandled_event(event)
                return
        # 2. Execute each selected transition in isolation. A transition may
        #    be invalidated by an earlier one in the same macrostep (its source
        #    is no longer active), so re-check liveness before executing.
        #    (⚡ Inlined rather than a helper coroutine: on the sync engine's
        #    trampoline every extra `async def` frame is ~0.7 µs per event.)
        for transition in transitions:
            if (
                len(transitions) > 1
                and transition.source not in self._active_state_nodes
            ):
                logger.debug(
                    "⏭️  Skipping stale transition from '%s'.",
                    transition.source.id,
                )
                continue
            await self._execute_transition(transition, event)

        # -------------------------------------------------------------------------
        # 🎬 Built-in Action Support
        # -------------------------------------------------------------------------

        if guard_error is None:
            return
        # 🛡️ #152: a guard raised under "raise" during this pass. The
        #    fallback (if any) has already run above -- that is the point.
        #    Now report the raise on the surface that matches the trigger:
        #    * a CALLER-driven event propagates, so the sync `send()` caller
        #      / async `wait=True` receipt receive it (the documented
        #      "raise" contract);
        #    * an ENGINE-driven event (`done.invoke`, `after`, `always`)
        #      has no caller to receive it -- raising would escape
        #      `start()`/the run loop for a completion the machine itself
        #      produced. Record it on `last_transition_ok` / `last_error`
        #      (the same channel a failed action uses) and carry on; the
        #      `on_guard_error` hook already fired.
        if is_system_event(event):
            self.last_transition_ok = False
            self._last_action_error = guard_error
            return
        raise guard_error

    def _resolve_event_spec(self, spec: Any, event: AnyEvent) -> Event:
        """Turns an event specification from action params into an `Event`.

        Accepts a plain type string, a mapping with a `type` key, an existing
        event object, or a callable of `{context, event}` returning one of
        those.

        Args:
            spec (Any): The declared event specification.
            event (AnyEvent): The triggering event,
                used to resolve callables.

        Returns:
            Event: The concrete event to dispatch.

        Raises:
            TypeError: If the specification cannot be interpreted.
        """
        if callable(spec):
            spec = spec({"context": self.context, "event": event})
        resolved = self._coerce_event(spec)
        if isinstance(resolved, Event):
            return resolved
        # 🔁 Normalise engine events into a plain Event for re-sending.
        #    `Event.payload` is a Dict by contract (#96): a `DoneEvent.data`
        #    that is not a mapping, or an `ErrorEvent.error`, is wrapped
        #    rather than assigned as the payload itself.
        if isinstance(resolved, ErrorEvent):
            return Event(
                type=resolved.type,
                payload={"error": resolved.error, "src": resolved.src},
            )
        data = getattr(resolved, "data", None)
        if isinstance(data, dict):
            return Event(type=resolved.type, payload=dict(data))
        payload: Dict[str, Any] = {}
        if data is not None:
            payload["data"] = data
        src = getattr(resolved, "src", None)
        if src is not None:
            payload["src"] = src
        return Event(type=resolved.type, payload=payload)

    def _resolve_actor_target(
        self, spec: Any, event: AnyEvent
    ) -> Optional["BaseInterpreter[Any]"]:
        """Resolves a `sendTo`/`forwardTo` target to a live interpreter.

        Lookup order: the actor system registry (`system_id`), then this
        interpreter's own children, then a suffix match on child ids — actor
        ids are namespaced (`parent:key:uuid`), so users naturally refer to
        the bare key.

        Args:
            spec (Any): The declared target: an id string, a callable
                resolving one, or an interpreter instance.
            event (AnyEvent): The triggering event.

        Returns:
            Optional[BaseInterpreter]: The resolved actor, or `None`.
        """
        if callable(spec) and not isinstance(spec, BaseInterpreter):
            spec = spec(
                {
                    "context": self.context,
                    "event": event,
                    "system": self.system,
                }
            )
        if isinstance(spec, BaseInterpreter):
            return spec
        if not isinstance(spec, str):
            return None

        # 🌐 Actor-system registration wins: it is the explicit, stable name.
        registry = self._system_registry()
        if spec in registry:
            return registry[spec]
        if spec in self._actors:
            return self._actors[spec]
        # 🎯 #40: an EXPLICIT child id is `f"{self.id}:{spec}"` exactly.
        #    Check it before the fuzzy segment scan so a declared name is
        #    never reported "ambiguous" against same-src siblings.
        exact = f"{self.id}:{spec}"
        if exact in self._actors:
            return self._actors[exact]
        # 🔑 Actor ids are namespaced as `parent:key` or `parent:key:uuid`, so
        #    a bare service key must match the MIDDLE segment too. Matching
        #    only the suffix silently missed every auto-id actor (the uuid is
        #    the last segment), so `send_to("worker", ...)` dropped the event.
        matches = [
            actor
            for actor_id, actor in self._actors.items()
            if spec in actor_id.split(":")[1:]
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # 🔊 Escalated from warning: a dropped event on the actor path is
            #    a correctness failure, not a nuisance (#40).
            logger.error(
                "🚫 Actor key '%s' is ambiguous (%d matches). Use an explicit "
                "`id` or `systemId` to disambiguate; event dropped.",
                spec,
                len(matches),
            )
            return None
        # 🗺️ Fall back to the originating service key recorded at spawn time.
        for actor_id, source_key in self._actor_sources.items():
            if source_key == spec and actor_id in self._actors:
                return self._actors[actor_id]
        if spec in ("parent", "#parent") and self.parent is not None:
            return self.parent
        return None

    def _system_registry(self) -> Dict[str, "BaseInterpreter[Any]"]:
        """Returns the actor-system registry shared by the whole hierarchy.

        🏛️ Architecture decision: the registry lives on the *root* interpreter
        so `system_id` is global to one machine hierarchy, exactly like
        XState's actor system. Children reach it by walking up `parent`.

        Returns:
            Dict[str, BaseInterpreter]: Mapping of `system_id` to actor.
        """
        root: "BaseInterpreter[Any]" = self
        while root.parent is not None:
            root = root.parent
        return root._system

    @property
    def system(self) -> "ActorSystem":
        """The actor system this interpreter belongs to.

        Returns:
            ActorSystem: A view exposing `get()` and `get_all()`.
        """
        return ActorSystem(self._system_registry())

    def _register_in_system(
        self, system_id: Optional[str], actor: "BaseInterpreter[Any]"
    ) -> None:
        """Registers an actor under a `system_id`, if one was declared.

        Args:
            system_id (Optional[str]): The requested system id.
            actor (BaseInterpreter): The actor to register.
        """
        if not system_id:
            return
        registry = self._system_registry()
        existing = registry.get(system_id)
        if existing is not None and existing is not actor:
            # 🛡️ #40 (LC-13): a duplicate systemId used to silently REPLACE
            #    the previous actor, so every later `sendTo` reached the
            #    wrong child. A stopped/finished actor may be superseded;
            #    a live one may not.
            if existing.status in ("running", "uninitialized"):
                raise ActorSpawningError(
                    f"systemId '{system_id}' is already registered to a "
                    f"live actor ('{existing.id}'). systemIds must be "
                    f"unique within a machine hierarchy."
                )
            logger.info(
                "♻️ systemId '%s' re-registered: previous actor '%s' had "
                "status '%s'.",
                system_id,
                existing.id,
                existing.status,
            )
        registry[system_id] = actor

    def _resolve_delay(self, spec: Any, event: Any) -> Optional[float]:
        """Resolves a delay specification to milliseconds.

        Accepts a number, a callable of `{context, event}`, or a named delay
        resolved from `MachineLogic.delays`.

        Args:
            spec (Any): The declared delay.
            event (Any): The triggering event.

        Returns:
            Optional[float]: The delay in milliseconds, or `None`.
        """
        if spec is None:
            return None
        if callable(spec):
            spec = spec({"context": self.context, "event": event})
        if isinstance(spec, (int, float)):
            return float(spec)
        if isinstance(spec, str):
            named = self.machine.logic.delays.get(spec)
            if named is None:
                logger.warning(
                    "⚠️ Named delay '%s' is not defined in MachineLogic."
                    " Treating as no delay.",
                    spec,
                )
                return None
            if callable(named):
                # 🔀 Accept BOTH calling conventions. Everything else in this
                #    release (action/guard `params`, `output`, inline `delay`)
                #    passes a single `{context, event}` mapping, so a named
                #    delay written that way must not be a hard TypeError at
                #    startup. The legacy `(context, event)` form still works.
                named = self._call_delay_callable(named, event)
            # 🛡️ A misconfigured delay must not crash the machine at start.
            #    `float()` on a string or dict raises, and this runs inside
            #    `_schedule_state_tasks` during entry, so an unusable value
            #    took the whole interpreter down instead of disabling one
            #    timer.
            try:
                return float(named) if named is not None else None
            except (TypeError, ValueError):
                logger.error(
                    "🔥 Named delay '%s' resolved to %r, which is not a "
                    "number of milliseconds. Ignoring this timer.",
                    spec,
                    named,
                )
                return None
        return None

    def _call_delay_callable(self, fn: Callable[..., Any], event: Any) -> Any:
        """Invokes a named-delay callable under either calling convention.

        Args:
            fn (Callable[..., Any]): The delay implementation.
            event (Any): The triggering event.

        Returns:
            Any: Whatever the callable returns, or `None` if it raised.
        """
        args = {"context": self.context, "event": event}
        try:
            signature = inspect.signature(fn)
            positional = [
                p
                for p in signature.parameters.values()
                if p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]
            takes_varargs = any(
                p.kind is inspect.Parameter.VAR_POSITIONAL
                for p in signature.parameters.values()
            )
        except (TypeError, ValueError):  # pragma: no cover - builtins
            positional, takes_varargs = [], False

        try:
            if not takes_varargs and len(positional) == 1:
                return fn(args)
            return fn(self.context, event)
        except Exception:
            logger.exception(
                "🔥 Named delay callable raised; ignoring this timer."
            )
            return None

    def _emit(self, event: Event) -> None:
        """Publishes an emitted event to registered listeners.

        Args:
            event (Event): The event to publish.
        """
        listeners = self._emit_listeners.get(event.type, [])
        wildcard = self._emit_listeners.get("*", [])
        for listener in list(listeners) + list(wildcard):
            try:
                listener(event)
            except Exception:
                # 📝 A listener failure must not disturb the machine — the
                #    same contract XState adopted in v5.20.2.
                logger.exception(
                    "🔥 Emit listener for '%s' raised; ignoring.", event.type
                )

    def on(
        self, event_type: str, listener: Callable[[Event], None]
    ) -> Callable[[], None]:
        """Registers a listener for events published via the `emit` action.

        Args:
            event_type (str): The emitted event type, or `"*"` for all.
            listener (Callable[[Event], None]): The callback.

        Returns:
            Callable[[], None]: An unsubscribe function.
        """
        self._emit_listeners.setdefault(event_type, []).append(listener)

        def _off() -> None:
            """Removes the listener if still registered."""
            bucket = self._emit_listeners.get(event_type, [])
            if listener in bucket:
                bucket.remove(listener)

        return _off

    def _apply_assign(self, params: Any, event: AnyEvent) -> None:
        """Applies an `assign` action to the machine context.

        Args:
            params (Any): The action's params, carrying `assignment`.
            event (AnyEvent): The triggering event.
        """
        assignment = (
            params.get("assignment") if isinstance(params, dict) else params
        )
        if assignment is None:
            return
        args = {"context": self.context, "event": event}
        # 🧷 `TContext` is bound to `Mapping` so a user's TypedDict qualifies;
        #    at runtime the context is always the mutable dict the machine
        #    built, and `assign` is the one place the ENGINE writes to it.
        ctx = cast(Dict[str, Any], self.context)
        if callable(assignment):
            produced = assignment(args)
            if isinstance(produced, dict):
                ctx.update(produced)
            return
        if isinstance(assignment, dict):
            for key, value in assignment.items():
                ctx[key] = value(args) if callable(value) else value

    def _collect_builtin_followups(
        self,
        canonical: str,
        action_def: ActionDefinition,
        event: AnyEvent,
    ) -> List[Any]:
        """Handles a built-in action, returning any actions it produced.

        This is the engine-agnostic half of built-in action execution. Effects
        that need to await (sending, spawning) are returned as follow-up work
        for the concrete interpreter, so the sync and async engines share one
        implementation of the semantics.

        Args:
            canonical (str): The canonical built-in action name.
            action_def (ActionDefinition): The action being executed.
            event (AnyEvent): The triggering event.

        Returns:
            List[Any]: Nested action definitions to execute next.
        """
        params = self._resolve_params(action_def.params, event) or {}

        # 🛟 Bound nested action expansion. `pure`, `choose` and
        #    `enqueueActions` all return further actions, so a callback that
        #    (directly or indirectly) enqueues itself recurses until Python
        #    raises RecursionError — which, being a BaseException subclass in
        #    older versions and an Exception here, previously left the machine
        #    in an indeterminate state. A depth counter turns an authoring
        #    mistake into a clear, contained log message.
        depth = getattr(self, "_action_depth", 0)
        if depth > self.MAX_ACTION_DEPTH:
            logger.error(
                "🔁 Nested action expansion exceeded %d levels while handling "
                "'%s'. Aborting this branch; check for an enqueueActions or "
                "pure callback that re-enqueues itself.",
                self.MAX_ACTION_DEPTH,
                action_def.type,
            )
            return []

        if canonical == ASSIGN:
            self._apply_assign(params, event)
            return []

        if canonical == LOG:
            expr = params.get("expr", "") if isinstance(params, dict) else ""
            label = params.get("label") if isinstance(params, dict) else None
            message = (
                expr({"context": self.context, "event": event})
                if callable(expr)
                else expr
            )
            logger.info("📝 %s%s", f"[{label}] " if label else "", message)
            return []

        if canonical == EMIT:
            self._emit(self._resolve_event_spec(params.get("event"), event))
            return []

        if canonical == PURE:
            getter = params.get("get") if isinstance(params, dict) else None
            if not callable(getter):
                return []
            produced = getter({"context": self.context, "event": event})
            if produced is None:
                return []
            return produced if isinstance(produced, list) else [produced]

        if canonical == CHOOSE:
            conditions = (
                params.get("conditions", [])
                if isinstance(params, dict)
                else []
            )
            for branch in conditions:
                guard_cfg = branch.get("guard", branch.get("cond"))
                if guard_cfg is None or self._is_guard_satisfied(
                    GuardDefinition(guard_cfg), event
                ):
                    chosen = branch.get("actions", [])
                    return chosen if isinstance(chosen, list) else [chosen]
            return []

        if canonical == ENQUEUE_ACTIONS:
            callback = (
                params.get("callback") if isinstance(params, dict) else None
            )
            if not callable(callback):
                return []
            enqueue = ActionEnqueuer(self, event)

            def _check(guard_cfg: Any) -> bool:
                """Evaluates a guard from inside the callback."""
                return self._is_guard_satisfied(
                    GuardDefinition(guard_cfg), event
                )

            callback(
                {
                    "context": self.context,
                    "event": event,
                    "enqueue": enqueue,
                    "check": _check,
                    "self": self,
                    "system": self.system,
                }
            )
            return enqueue.items

        if canonical == CANCEL:
            send_id = (
                params.get("sendId") if isinstance(params, dict) else None
            )
            if send_id:
                self._cancel_scheduled_send(str(send_id))
            return []

        # 📨 Remaining built-ins need interpreter-specific delivery and are
        #    handled by the concrete engines.
        return []

    def _cancel_scheduled_send(self, send_id: str) -> None:
        """Cancels a pending delayed send.

        Args:
            send_id (str): The identifier given to the original send.
        """
        canceller = self._scheduled_sends.pop(send_id, None)
        if canceller is None:
            logger.debug("🤷 No pending send with id '%s' to cancel.", send_id)
            return
        try:
            canceller()
            logger.info("🚫 Cancelled scheduled send '%s'.", send_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("🔥 Failed to cancel send '%s'.", send_id)

    async def _execute_transition(
        self,
        transition: TransitionDefinition,
        event: AnyEvent,
    ) -> None:
        """Executes one selected transition, mutating the active configuration.

        Args:
            transition (TransitionDefinition): The transition to execute.
            event (AnyEvent): The triggering event.

        Raises:
            StateNotFoundError: If the transition's target cannot be resolved.
        """
        # 1. A "targetless" transition only executes actions without changing state.
        if not transition.target_str:
            logger.debug(
                "🎬 Executing targetless transition for event '%s'.",
                event.type,
            )
            await self._execute_internal_transition(transition, event)
            return

        # 2. Resolve the target state node. ⚡ Build-time validation already
        #    resolved and memoised it on the transition; only a target the
        #    validator could not resolve (`strict_targets=False`) takes the
        #    slow multi-strategy path here.
        target_state = (
            transition.resolved_target
            or self._resolve_target_state_node(transition)
        )
        if target_state is None:
            # Name the SOURCE too, so the failing transition is identifiable
            # from the exception alone (the sync engine always did this).
            exc = StateNotFoundError(
                transition.target_str, transition.source.id
            )
            # 🔔 #134: fire `on_resolve_error` HERE, at the one place both
            #    engines raise it, so the hook cannot fire on one engine and
            #    not the other (it used to live in the async loop only).
            self._report_resolve_error(exc, event)
            raise exc

        # 3. A self-transition without `reenter: True` is an "internal" transition.
        # It executes actions but does not exit or re-enter the source state.
        if target_state == transition.source and not transition.reenter:
            logger.debug(
                "🎬 Executing internal self-transition for event '%s'.",
                event.type,
            )
            await self._execute_internal_transition(transition, event)
            return

        # 4. All other transitions are "external" and will cause a state change.
        snapshot_before = self._active_state_nodes.copy()
        # 👶 #60 review: remember which actors already existed so a rollback
        #    can tell which ones a `spawn_*` action in THIS transition's
        #    action list created. Without this snapshot, a spawn that
        #    succeeds and is followed by a later action that raises left the
        #    child running and registered even after the whole transition was
        #    undone -- orphaned from any active state and reachable only
        #    until the parent itself eventually stopped.
        actor_ids_before = set(self._actors.keys())
        domain, path_to_enter = self._transition_geometry(
            transition, target_state
        )
        states_to_exit = self._compute_states_to_exit(domain, target_state)

        # 🧷 Context is snapshotted only when a rollback could need it: a
        #    deepcopy per transition on the "continue" hot path would be a
        #    measurable tax for a feature the machine has opted out of.
        # ⚡ #27 follow-up: ...and only when a user action can actually
        #    RUN. The checkpoint cost ~22% throughput on an idle `rollback`
        #    machine whose transitions had no actions at all. History
        #    targets are conservatively treated as "may run actions".
        context_before: Optional[TContext] = (
            copy.deepcopy(self.context)
            if self.machine.action_error_policy != "continue"
            and (
                transition.actions
                or target_state.type == "history"
                or any(s.exit for s in states_to_exit)
                or any(s.subtree_has_actions for s in path_to_enter)
            )
            else None
        )
        internal_depth_before = self._internal_queue_depth()

        # 🕰️ A history pseudo-state is never entered itself. Replace it with
        #    the remembered configuration (or the default), computed *before*
        #    exiting so the recorded history is the pre-transition one.
        history_targets: List[StateNode] = []
        if target_state.type == "history":
            history_targets = self._resolve_history_target(target_state)
            # Enter down to the history node's parent, then the remembered
            # set. The parent is entered as part of each remembered node's own
            # path, so entering it here as well would trigger its default
            # `initial` descent and activate the wrong child alongside the
            # restored one.
            path_to_enter = []

        # 5. Execute the transition sequence in the correct SCXML order.
        #
        # 🏛️ Architecture decision: `_exit_states` and `_enter_states` are the
        # sole authorities on `_active_state_nodes` membership — they discard
        # and add as they go. A previous implementation additionally applied
        # `difference_update(states_to_exit)` *after* entry, which removed the
        # initial children that `_enter_states` had just recursively entered
        # (those children were themselves members of `states_to_exit`). The
        # machine was left on a non-atomic ancestor with no active leaf,
        # rendering it permanently unresponsive. Do not reintroduce that step.
        #
        # ⚛️ ATOMICITY: exit → actions → enter is ONE transaction. If a user
        #    action raises in the middle, the source has been left and the
        #    target never reached, so the configuration would be EMPTY while
        #    `status` still read "running" — permanently dead and reporting
        #    itself healthy. Rolling back to the pre-transition configuration
        #    keeps the machine in a state that genuinely exists; the exception
        #    still propagates so the caller learns the transition failed.
        # 🧾 #27 review: entry/exit actions are part of the transaction too.
        #    `_enter_states`/`_exit_states` report their action failures via
        #    this stack instead of raising, so the policy is applied once,
        #    here, for every action slot. See `_execute_lifecycle_actions`.
        self._lifecycle_failures.append((transition, []))
        try:
            await self._exit_states(
                sorted(
                    list(states_to_exit),
                    # 🔀 Depth alone leaves ties between sibling parallel
                    #    regions, so set iteration order decided which exited
                    #    first — the same machine and event could emit exit
                    #    actions in a different order between runs, which is
                    #    untestable and makes cleanup logic subtly unreliable.
                    #    `id` is a stable secondary key.
                    key=lambda s: (s.depth, s.id),
                    reverse=True,
                ),
                event,
            )
            failed_actions: List[Tuple[ActionDefinition, BaseException]] = (
                await self._execute_actions(transition.actions, event)
                if transition.actions  # ⚡ no coroutine for an empty list
                else []
            )
            if failed_actions:
                self._apply_action_error_policy(transition, failed_actions)
            await self._enter_states(path_to_enter, event)

            # 🕰️ Restore the remembered configuration for a history target.
            #
            # 🏛️ Architecture decision: build ONE combined entry path and make
            #    a SINGLE `_enter_states` call. The explicit-child guard inside
            #    `_enter_states` is computed per call, so entering each
            #    remembered leaf separately meant each call saw only its own
            #    path: restoring `r1.y` walked through `r1`, which could not
            #    tell that `y` was explicitly targeted and so ALSO ran its
            #    default `initial` descent into `r1.x`. Deep history into a
            #    parallel state therefore activated TWO leaves in one region —
            #    a configuration SCXML forbids and that breaks the
            #    one-state-per-region invariant the whole library rests on.
            if target_state.type == "history":
                combined_path: List[StateNode] = []
                for node in history_targets:
                    for step in self._get_path_to_state(node, stop_at=domain):
                        if step not in combined_path:
                            combined_path.append(step)
                if combined_path:
                    await self._enter_states(combined_path, event)
            # 🧾 Entry/exit failures surface here, after the whole sequence
            #    ran, so `"continue"` still commits the complete new
            #    configuration while `"rollback"`/`"fail"` undo all of it.
            lifecycle_failed = self._lifecycle_failures[-1][1]
            if lifecycle_failed:
                self._apply_action_error_policy(transition, lifecycle_failed)
            failed_actions = failed_actions or lifecycle_failed
        except Exception as rollback_cause:
            requested = isinstance(rollback_cause, _RollbackRequested)
            logger.log(
                logging.WARNING if requested else logging.ERROR,
                "💥 Transition on '%s' failed; rolling back to the "
                "pre-transition configuration.",
                transition.source.id,
                exc_info=not requested,
            )
            # ⏱️ Tear down what a PARTIAL entry armed. States entered before
            #    the failure already scheduled their `after` timers and
            #    invokes; left running, a timer belonging to a state the
            #    machine has rolled out of would later fire and drive a
            #    transition from a configuration that no longer exists.
            for node in self._active_state_nodes - snapshot_before:
                _maybe = self._cancel_state_tasks(node)
                if _maybe is not None:
                    await _maybe
            self._active_state_nodes.clear()
            self._active_state_nodes.update(snapshot_before)

            # ⏱️ Re-arm what exiting tore down. `_exit_states` cancels each
            #    exited state's `after` timers and invoked services, so a
            #    configuration restored without them looks right but is inert:
            #    a rolled-back state with `after: {250: "timeout"}` would never
            #    time out again. Re-scheduling makes the rollback a true
            #    restore rather than a cosmetic one.
            for node in snapshot_before:
                if node in states_to_exit:
                    self._schedule_state_tasks(node)

            # 👶 #60 review: stop and unregister any actor a `spawn_*`
            #    action in THIS transition's action list created before a
            #    LATER action raised. Left alone, the child interpreter's
            #    event loop task kept running and it stayed reachable via
            #    `self._actors`/the system registry even though the
            #    transition that spawned it was fully undone -- an orphaned,
            #    leaked actor unreachable from any active state.
            spawned_ids = set(self._actors.keys()) - actor_ids_before
            if spawned_ids:
                registry = self._system_registry()
                for actor_id in spawned_ids:
                    actor = self._actors.pop(actor_id, None)
                    self._actor_sources.pop(actor_id, None)
                    for system_id, candidate in list(registry.items()):
                        if candidate is actor:
                            del registry[system_id]
                    if actor is not None:
                        await self._stop_actor_leaf(actor)

            if self._finish_rollback(
                rollback_cause,
                transition,
                context_before,
                internal_depth_before,
            ):
                return
            raise
        finally:
            self._lifecycle_failures.pop()

        # 6. Notify plugins and subscribers of the completed transition.
        if not failed_actions:
            self.last_transition_ok = True
        self._publish_soft_step_error()  # #133
        for plug in self._plugins:
            plug.on_transition(
                self,
                snapshot_before,
                self._active_state_nodes.copy(),
                transition,
            )
        self._notify_subscribers()

    async def _execute_internal_transition(
        self,
        transition: TransitionDefinition,
        event: AnyEvent,
    ) -> None:
        """Run a targetless or internal self-transition atomically.

        🏛️ Architecture decision (#27 review): these two shapes used to call
        `_execute_actions` and fire `on_transition` unconditionally, so a
        raising action under ``"rollback"``/``"fail"`` still committed its
        partial context mutation and `last_transition_ok` stayed ``True`` --
        the policy simply did not apply to the most common machine shape
        (an action-only event handler). No configuration changes here, so
        the transaction is context-only: snapshot, run, restore on failure.
        """
        context_before: Optional[TContext] = (
            copy.deepcopy(self.context)
            if self.machine.action_error_policy != "continue"
            and transition.actions
            else None
        )
        internal_depth_before = self._internal_queue_depth()
        try:
            failed = await self._execute_actions(transition.actions, event)
            if failed:
                self._apply_action_error_policy(transition, failed)
        except _RollbackRequested as cause:
            logger.warning(
                "💥 Internal transition on '%s' failed; restoring context.",
                transition.source.id,
            )
            self._finish_rollback(
                cause, transition, context_before, internal_depth_before
            )
            return
        if not failed:
            self.last_transition_ok = True
        self._publish_soft_step_error()  # #133
        for plug in self._plugins:
            plug.on_transition(
                self,
                self._active_state_nodes,
                self._active_state_nodes,
                transition,
            )

    async def _execute_actions(
        self, actions: List[ActionDefinition], event: AnyEvent
    ) -> List[Tuple[ActionDefinition, BaseException]]:
        """Run an action list; return the ``(action, exception)`` failures.

        🏛️ Architecture decision (#60): this is the ONE implementation.
        Each engine used to carry its own ~90-line copy, differing only in
        how a single action is called (`await` vs inline) and in which
        callables it refuses. Those two decisions are now the leaves
        `_run_user_action` and `_execute_builtin_action`; everything else
        -- spawn dispatch, built-in resolution, error containment, the
        `on_action_execute` / `on_action_error` hooks, first-failure
        short-circuit -- is written once here.

        Returns the failures rather than swallowing them so the caller can
        apply the machine's ``actionErrorPolicy``; before 0.8.0 this
        returned ``None`` and a half-run list committed like a full one.
        The first failure stops the remaining actions in the list.

        Raises:
            ImplementationMissingError: A named action has no implementation
                and is not a built-in. Configuration errors stay fatal.
        """
        failed: List[Tuple[ActionDefinition, BaseException]] = []
        if not actions:
            return failed
        for action_def in actions:
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 👶 Spawning is a built-in ACTION shape on both engines (#41:
            #    `spawn_blocking_` is a distinct mode, not a longer prefix).
            # 🎭 #155: the `spawn_` prefix is a BUILT-IN like `log` /
            #    `assign`, and built-ins are used only when the user has NOT
            #    supplied an action of the same name. Checking the prefix
            #    before consulting `logic.actions` was the single place that
            #    claimed a name out of the user's own namespace: a user
            #    action `spawn_place_order` was hijacked into a spawn of a
            #    service called "place_order" that did not exist.
            if (
                action_def.type.startswith((SPAWN_BLOCKING_PREFIX, "spawn_"))
                and not is_builtin(action_def.type)
                and action_def.type not in self.machine.logic.actions
            ):
                # A spawn that cannot be satisfied (unknown service, bad
                # factory) is a CONFIGURATION error and stays fatal, like a
                # missing action -- both engines behaved this way before.
                await self._spawn_actor(action_def, event)
                continue

            impl = self.machine.logic.actions.get(action_def.type)

            # 🎬 Built-in action creators. Resolved only when the user has
            #    NOT supplied an action of the same name, so a machine that
            #    legitimately defines its own `log` or `assign` keeps working.
            if impl is None:
                canonical = resolve_builtin(action_def.type)
                if canonical is not None:
                    try:
                        await self._execute_builtin_action(
                            canonical, action_def, event
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001 -- user params
                        self._report_action_failure(action_def, event, exc)
                        failed.append((action_def, exc))
                        return failed
                    continue
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' is not implemented."
                )

            # 🏃 The one engine-specific line: HOW to call it.
            #
            # 🏛️ Exceptions from user actions are contained. `send()` is
            #    fire-and-forget on the async engine, so an escaping error
            #    would kill the run loop while callers saw "running". The
            #    error is logged, reported via `on_action_error`, the rest of
            #    the list is skipped, and the POLICY decides what happens.
            try:
                await self._run_user_action(impl, action_def, event)
            except asyncio.CancelledError:
                raise
            except NotSupportedError:
                raise  # configuration error (async action on sync engine)
            except Exception as exc:  # noqa: BLE001 -- user code
                self._report_action_failure(action_def, event, exc)
                failed.append((action_def, exc))
                return failed
        return failed

    def _report_action_failure(
        self, action_def: ActionDefinition, event: Any, exc: BaseException
    ) -> None:
        """Log + `on_action_error` for one failed action (shared)."""
        logger.exception(
            "🔥 Action '%s' raised while handling event '%s'; skipping "
            "remaining actions in this list.",
            action_def.type,
            getattr(event, "type", event),
        )
        for plugin in self._plugins:
            plugin.on_action_error(self, action_def, exc)

    async def _execute_builtin_action(
        self,
        canonical: str,
        action_def: ActionDefinition,
        event: AnyEvent,
    ) -> None:
        """Executes a built-in action creator asynchronously.

        🏛️ #60: ONE implementation for both engines. Pure-state effects
        (`assign`, `log`, `emit`, `pure`, `choose`, `enqueueActions`,
        `cancel`) resolve in `_collect_builtin_followups`; delivery effects
        (`raise`, `sendTo`, `sendParent`, `forwardTo`, `escalate`,
        `stopChild`, `spawnChild`) go through the engine LEAVES `_deliver`,
        `_spawn_actor` and `_stop_actor_leaf`, each of which the sync
        engine implements as a finished awaitable.

        Args:
            canonical (str): The canonical built-in action name.
            action_def (ActionDefinition): The action being executed.
            event (Event): The triggering event.
        """
        # 🧮 Shared semantics first; may yield nested actions to run.
        followups = self._collect_builtin_followups(
            canonical, action_def, event
        )
        if followups:
            self._action_depth += 1
            try:
                await self._execute_actions(
                    [ActionDefinition(f) for f in followups], event
                )
            finally:
                self._action_depth -= 1

        params = self._resolve_params(action_def.params, event) or {}

        if canonical == RAISE:
            target_event = self._resolve_event_spec(params.get("event"), event)
            self._check_strict(target_event)  # #51: internal typos too
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(self, target_event, delay, params.get("id"))

        elif canonical == SEND_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            target_event = self._resolve_event_spec(params.get("event"), event)
            if actor is None:
                self._report_unresolved_target(
                    "sendTo", params.get("to"), target_event
                )
                return
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(actor, target_event, delay, params.get("id"))

        elif canonical == SEND_PARENT:
            if self.parent is None:
                logger.warning("⚠️ sendParent called with no parent actor.")
                return
            target_event = self._resolve_event_spec(params.get("event"), event)
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(
                self.parent, target_event, delay, params.get("id")
            )

        elif canonical == FORWARD_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            if actor is None:
                # 🔔 #133 (reopened): the SIBLING of sendTo went through
                #    the same silent-drop surface. One helper for both.
                self._report_unresolved_target(
                    "forwardTo", params.get("to"), event
                )
                return
            await self._deliver(actor, event, None, None)

        elif canonical == ESCALATE:
            error_payload = params.get("error")
            # 🏛️ #97: `escalate` is a FAILURE, so it rides the same type as
            #    every other failure (#80). Handlers written to the documented
            #    `event.error` pattern work; `event.type` is unchanged.
            err = (
                error_payload
                if isinstance(error_payload, BaseException)
                else RuntimeError(str(error_payload))
            )
            # 🎯 #130: `src` must equal the invoke's DECLARED id for the
            #    parent's `onError` collector to match; the runtime actor id
            #    is `parent:declared_id` (or `parent:src:uuid` when
            #    anonymous). Strip the parent prefix so an escalation
            #    reaches `onError` exactly like a child that ended in
            #    `error` does. The event `type` keeps the runtime id -- a
            #    literal `on: {"xstate.error.actor.p:kid": ...}` still works.
            # 🎯 #130 / #156: `src` is the invoke id the parent knows this
            #    actor by. Prefer what the parent recorded at spawn
            #    (`_invoked_as`); fall back to the explicit-id runtime shape
            #    for a `spawnChild` actor that was never `invoke`d.
            declared = self._invoked_as or self.id
            if self._invoked_as is None and self.parent is not None:
                prefix = self.parent.id + ":"
                if declared.startswith(prefix):
                    declared = declared[len(prefix) :].split(":")[0]
            escalate_event = ErrorEvent(
                type=f"xstate.error.actor.{self.id}", error=err, src=declared
            )
            if self.parent is not None:
                await self._deliver(self.parent, escalate_event, None, None)
            else:
                logger.error(
                    "🔥 escalate() with no parent actor: %r", error_payload
                )

        elif canonical == STOP_CHILD:
            await self._stop_child_actor(params.get("id"), event)

        elif canonical == SPAWN_CHILD:
            await self._spawn_child_action(params, event)

    async def _stop_child_actor(self, spec: Any, event: AnyEvent) -> None:
        """Stops a spawned child actor by id.

        Args:
            spec (Any): The child's id, or a callable resolving one.
            event (Event): The triggering event.
        """
        actor = self._resolve_actor_target(spec, event)
        if actor is None:
            logger.warning("⚠️ stopChild could not resolve %r.", spec)
            return
        for actor_id, candidate in list(self._actors.items()):
            if candidate is actor:
                del self._actors[actor_id]
                self._actor_sources.pop(actor_id, None)
                break
        # 🌐 Also drop it from the actor-system registry, otherwise a stopped
        #    actor stays addressable by systemId and silently swallows events.
        registry = self._system_registry()
        for system_id, candidate in list(registry.items()):
            if candidate is actor:
                del registry[system_id]
        await self._stop_actor_leaf(actor)

    async def _spawn_child_action(
        self, params: Dict[str, Any], event: AnyEvent
    ) -> None:
        """Spawns an actor declaratively via the `spawnChild` action.

        Args:
            params (Dict[str, Any]): Params carrying `src`, `id`, `systemId`
                and `input`.
            event (Event): The triggering event.
        """
        src = params.get("src")
        if not isinstance(src, str):
            logger.warning("⚠️ spawnChild requires a string 'src'.")
            return
        synthetic = ActionDefinition(
            {
                "type": f"spawn_{src}",
                "params": {
                    "id": params.get("id"),
                    "systemId": params.get("systemId"),
                    "input": params.get("input"),
                },
            }
        )
        await self._spawn_actor(synthetic, event)

    async def _dispatch_internal(self, event: Any) -> None:
        """Leaf: queue an engine-generated event (``done.state.*``) on self.

        Kept separate from the public `send()` so that method's return
        contract stays clean on both engines (#60).
        """
        raise NotImplementedError  # pragma: no cover

    async def _stop_actor_leaf(self, actor: Any) -> None:
        """Leaf: stop a child actor (awaited on async; inline on sync)."""
        raise NotImplementedError  # pragma: no cover

    async def _deliver(
        self,
        actor: Any,
        target_event: AnyEvent,
        delay: Optional[float],
        send_id: Optional[str],
    ) -> None:
        """Leaf: deliver an event to an actor, honouring an optional delay."""
        raise NotImplementedError  # pragma: no cover

    async def _run_user_action(
        self,
        impl: Callable[..., Any],
        action_def: ActionDefinition,
        event: Any,
    ) -> None:
        """Leaf: invoke ONE user action. Engine-specific (#60)."""
        raise NotImplementedError  # pragma: no cover

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Any
    ) -> None:
        """Leaf: spawn a child actor. Engine-specific (#60)."""
        raise NotImplementedError  # pragma: no cover

    async def _execute_lifecycle_actions(
        self, actions: List[ActionDefinition], event: AnyEvent
    ) -> None:
        """Run a state's ``entry``/``exit`` list and record any failures.

        🏛️ Architecture decision (#27 review): `_enter_states` and
        `_exit_states` are recursive and are called from several places
        (transitions, `start()`, history restore). Raising from inside them
        would unwind that recursion at an arbitrary depth and leave the
        configuration torn -- exactly what the rollback exists to prevent.
        Instead, failures are appended to the innermost open transaction on
        `_lifecycle_failures`; the transaction owner applies the policy once
        the whole exit → actions → enter sequence has run. Outside any
        transaction (`start()`), failures are reported against a synthetic
        init transition so `start()` honours the policy too.
        """
        failed = await self._execute_actions(actions, event)
        if not failed:
            return
        if self._lifecycle_failures:
            self._lifecycle_failures[-1][1].extend(failed)
            return
        # 🚀 No open transaction: this is initial entry from `start()`.
        self._report_start_failure(failed)

    def _report_start_failure(
        self, failed: List[Tuple[ActionDefinition, BaseException]]
    ) -> None:
        """Apply the action-error policy to a failure during ``start()``.

        There is no pre-start configuration to roll back to, so both
        ``"rollback"`` and ``"fail"`` stop the machine with
        `TransitionFailedError`; ``"continue"`` reports and carries on.
        """
        init = TransitionDefinition(
            event="___xstate_init___", config={}, source=self.machine
        )
        try:
            self._apply_action_error_policy(init, failed)
        except _RollbackRequested as cause:
            err = TransitionFailedError(cause.action_def.type, self.machine.id)
            err.__cause__ = cause.original
            self._stop_failed(err)

    # -------------------------------------------------------------------------
    # ⏯️ State Management Sub-Routines
    # -------------------------------------------------------------------------

    async def _enter_states(
        self,
        states_to_enter: List[StateNode],
        event: Optional[AnyEvent] = None,
    ) -> None:
        """Enters a list of states in order, running actions and tasks.

        This method follows the SCXML algorithm for state entry. For each
        state, it:
        1.  Adds the state to the active configuration.
        2.  Executes all 'entry' actions.
        3.  Schedules any `after` timers or `invoke` services defined on the state.
        4.  If the state is a final state, it checks if its parent is now "done".
        5.  Recursively enters the initial substate of a compound state or all
            substates of a parallel state.

        Args:
            states_to_enter (List[StateNode]): An ordered list of states to
                enter, from the outermost ancestor to the innermost child.
            event (Optional[Event]): The event that triggered this state entry.
        """
        trigger_event = event or _INIT_EVENT  # ⚡ shared immutable sentinel

        # 🗺️ Index the remaining path so a compound state can tell whether the
        #    caller already named which child to descend into.
        #
        # 🏛️ Architecture decision: `_enter_states` used to descend into a
        # compound's `initial` child unconditionally, *in addition* to walking
        # the explicit entry path. When the path already named a deeper sibling
        # (e.g. an external transition targeting `B.b2` while `B.initial` is
        # `b1`), both `b1` and `b2` ended up active — two simultaneously active
        # leaves inside one non-parallel region, which SCXML forbids. The
        # phantom leaf then participated in the next selection pass and could
        # win, executing the wrong transition and duplicating its actions.
        explicit_children = {
            state.parent.id: state
            for state in states_to_enter
            if state.parent is not None
        }
        explicit_child_ids = {
            state.id for state in states_to_enter if state.parent is not None
        }

        # ⚡ One level check per call, not one per state: `logger.debug`
        #    costs ~0.4 us even when disabled, and this runs per entered node.
        debug = logger.isEnabledFor(logging.DEBUG)
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            if debug:
                logger.debug("➡️  Entering state: '%s'.", state.id)

            # ⚙️ Run entry actions and schedule background tasks. ⚡ The
            #    coroutine is only created when there is something to run:
            #    two frames per entered state for an empty list was ~15%
            #    of a flat macrostep on the trampoline-driven sync engine.
            if state.entry:
                await self._execute_lifecycle_actions(
                    state.entry, trigger_event
                )
            if state.owns_tasks:  # ⚡ no `after` / `invoke` -> nothing to arm
                self._schedule_state_tasks(state)

            # 🎉 If we entered a final state, check if its parent is now complete.
            if state.is_final:
                await self._check_and_fire_on_done(state)

            # 🗺️ Handle automatic entry into child states.
            if state.type == "compound" and state.initial:
                # ⏭️ Skip the default descent when the entry path already
                #    specifies which child of this state to enter.
                if state.id in explicit_children:
                    continue
                initial_child = state.states.get(state.initial)
                if initial_child:
                    await self._enter_states([initial_child], trigger_event)
                else:
                    raise InvalidConfigError(
                        f"❌ Initial state '{state.initial}' not found in "
                        f"compound state '{state.id}'."
                    )
            elif state.type == "compound" and state.states:
                # 🚨 A compound state with children but no resolvable
                #    `initial` cannot produce an active leaf. Left unchecked
                #    the machine starts "successfully" with an empty
                #    configuration and silently drops every event.
                raise InvalidConfigError(
                    f"❌ Compound state '{state.id}' has no 'initial' state, "
                    "so entering it yields no active leaf. Declare "
                    "'initial' explicitly."
                )
            elif state.type == "parallel":
                # For parallel states, enter all child regions simultaneously.
                # 🌐 Enter every region EXCEPT one already named by the entry
                #    path (that region is walked explicitly, and entering
                #    it again would trigger its default `initial` descent
                #    and activate the wrong child alongside the target).
                #    History pseudo-states are never entered as regions.
                regions = [
                    child
                    for child in state.states.values()
                    if child.type != "history"
                    and child.id not in explicit_child_ids
                ]
                if regions:
                    await self._enter_states(regions, trigger_event)

    def _record_history(self, states_to_exit: List[StateNode]) -> None:
        """Remembers the active configuration of states being exited.

        Called immediately before exit actions run. For every state that owns
        at least one `type: "history"` child, the currently active descendants
        are stored so a later transition targeting that history node can
        restore them.

        🏛️ Architecture decision: history is keyed by the *parent* id rather
        than by the history node itself. A parent may declare both a shallow
        and a deep history child, and both must see the same recorded
        configuration — the shallow/deep distinction is applied at restore
        time, not at record time.

        Args:
            states_to_exit (List[StateNode]): The states about to be exited.
        """
        if not self.machine.has_history_states:
            return  # ⚡ nothing to remember for; see MachineNode.has_history_states
        exiting = set(states_to_exit)
        # 🕰️ Candidates are the exiting states *and* their ancestors: a
        #    transition out of a nested leaf exits the leaf and its parents,
        #    and it is the history-owning ancestor whose configuration must be
        #    remembered. Walking up from each exiting node covers both the
        #    "parent is exiting too" and "only descendants are exiting" cases.
        candidates: Set[StateNode] = set()
        for node in exiting:
            current: Optional[StateNode] = node
            while current is not None:
                candidates.add(current)
                current = current.parent

        for state in candidates:
            # 🕰️ Only parents that actually declare a history child matter.
            if not any(
                child.type == "history" for child in state.states.values()
            ):
                continue
            remembered = [
                node
                for node in self._active_state_nodes
                if node is not state and self._is_descendant(node, state)
            ]
            if remembered:
                self._history[state.id] = remembered
                logger.debug(
                    "🕰️ Recorded history for '%s': %s",
                    state.id,
                    [n.id for n in remembered],
                )

    def _resolve_history_target(
        self, history_node: StateNode
    ) -> List[StateNode]:
        """Expands a history pseudo-state into the states to actually enter.

        Args:
            history_node (StateNode): A node whose `type` is `"history"`.

        Returns:
            List[StateNode]: The states to enter. Falls back to the parent's
            default `initial` child when nothing has been recorded yet, which
            matches XState and SCXML semantics for an unvisited history state.
        """
        parent = history_node.parent
        if parent is None:  # pragma: no cover - a root history node is invalid
            return []

        remembered = self._history.get(parent.id)

        if not remembered:
            # 🌱 Never visited: fall back to the declared default target, or
            #    the parent's initial child.
            default_target = history_node.target_str
            if default_target:
                resolved = self._resolve_state_by_target(
                    default_target, history_node
                )
                if resolved:
                    return [resolved]
            if parent.initial and parent.initial in parent.states:
                return [parent.states[parent.initial]]
            return []

        if history_node.history == "deep":
            # 🌊 Deep history restores the full nested configuration; entering
            #    the deepest leaves re-enters their ancestors on the way.
            leaves = [
                node
                for node in remembered
                if node.is_atomic or node.is_final or not node.states
            ]
            return leaves or remembered

        # 🏖️ Shallow history restores only the parent's immediate child; its
        #    own `initial` chain then applies below that.
        shallow = [node for node in remembered if node.parent is parent]
        return shallow or remembered

    def _resolve_state_by_target(
        self, target: str, reference: StateNode
    ) -> Optional[StateNode]:
        """Resolves a target string relative to a reference node.

        Args:
            target (str): The target expression (e.g. `"#m.a.b"` or `"b"`).
            reference (StateNode): The node the target is written relative to.

        Returns:
            Optional[StateNode]: The resolved node, or `None`.
        """
        try:
            return resolve_target_state(target, reference)
        except StateNotFoundError:
            logger.warning(
                "⚠️ Could not resolve history default target '%s' on '%s'.",
                target,
                reference.id,
            )
            return None

    async def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[AnyEvent] = None
    ) -> None:
        """Exits a list of states in order, canceling tasks and running actions.

        This method follows the SCXML algorithm for state exit. For each state, it:
        1.  Cancels any running tasks (`after` timers, `invoke` services)
            owned by the state.
        2.  Executes all 'exit' actions.
        3.  Removes the state from the active configuration.

        Args:
            states_to_exit (List[StateNode]): An ordered list of states to
                exit, from the innermost child to the outermost ancestor.
            event (Optional[Event]): The event that triggered the state exit.
        """
        trigger_event = event or _EXIT_EVENT  # ⚡ shared immutable sentinel

        # 🕰️ Record history *before* anything is removed, so the remembered
        #    configuration reflects the state of the machine as it was.
        self._record_history(states_to_exit)

        debug = logger.isEnabledFor(logging.DEBUG)  # ⚡ see _enter_states
        for state in states_to_exit:
            if debug:
                logger.debug("⬅️  Exiting state: '%s'.", state.id)
            # 🛑 Crucially, cancel tasks before running exit actions.
            #    ⚡ A state that declares no `after` / `invoke` owns nothing
            #    to cancel (delayed sends are owned by the root, which is
            #    never exited by a transition).
            if state.owns_tasks:
                _pending = self._cancel_state_tasks(state)
                if _pending is not None:
                    await _pending
            # ⚙️ Then, run the synchronous exit actions (⚡ only if any).
            if state.exit:
                await self._execute_lifecycle_actions(
                    state.exit, trigger_event
                )
            # 🗑️ Finally, remove from the active set.
            self._active_state_nodes.discard(state)

    # -------------------------------------------------------------------------
    # 🔎 State Evaluation & Pathfinding Helpers
    # -------------------------------------------------------------------------

    def _is_state_done(self, state_node: StateNode) -> bool:
        """Recursively determines if a compound or parallel state is "done".

        This is a key part of the SCXML algorithm for `onDone` transitions.
        - A state with `type: 'final'` is always done.
        - A `compound` state is done if its currently active child state is done.
        - A `parallel` state is done only if ALL of its child regions are done.

        Args:
            state_node (StateNode): The state to check for completion.

        Returns:
            bool: `True` if the state is considered "done", otherwise `False`.
        """
        # 🏁 Base case: A final state is inherently "done".
        if state_node.is_final:
            return True

        # 🧠 Compound state: Its "doneness" is determined by its active child.
        if state_node.type == "compound":
            active_child = next(
                (
                    s
                    for s in self._active_state_nodes
                    if s.parent == state_node
                ),
                None,
            )
            # If no child is active, it cannot be done.
            if not active_child:
                return False
            # Recursively check the child, handling nested complex states.
            return self._is_state_done(active_child)

        # 🌐 Parallel state: All child regions must be independently "done".
        if state_node.type == "parallel":
            for region in state_node.states.values():
                # 🕰️ A history child is a pseudo-state, not a region. It is
                #    never entered, so demanding that it be "done" made a
                #    parallel state with a history child NEVER complete —
                #    `onDone` silently never fired.
                if region.type == "history":
                    continue
                active_in_region = [
                    d
                    for d in self._active_state_nodes
                    if self._is_descendant(d, region)
                ]
                # If a region is not active, the parallel state is not done.
                if not active_in_region:
                    return False
                # The region itself is "done" if any of its active states are done.
                if not any(self._is_state_done(d) for d in active_in_region):
                    return False
            # If all regions passed the check, the parallel state is done.
            return True

        # For atomic, non-final states.
        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Bubbles up from a final state to fire parent `onDone` transitions.

        When a state machine enters a `final` state, this method is called to
        check if the parent (or any ancestor) is now considered "done"
        according to `_is_state_done`. If so, it dispatches the corresponding
        `done.state.*` event to trigger the `onDone` transition.

        Args:
            final_state (StateNode): The final state that was just entered.
        """
        ancestor = final_state.parent
        while ancestor:
            if ancestor.on_done and self._is_state_done(ancestor):
                logger.info(
                    "🎉 State '%s' is done, firing onDone event.", ancestor.id
                )
                # 📨 Create and send the synthetic `done.state.*` event,
                #    carrying the final state's `output` as done data.
                done_event = DoneEvent(
                    type=f"done.state.{ancestor.id}",
                    data=self._resolve_output(final_state),
                    src=ancestor.id,
                )
                await self._dispatch_internal(done_event)
                # Per SCXML, only fire for the first completed ancestor.
                return
            ancestor = ancestor.parent

        # 🏁 A top-level final state completes the machine itself.
        #
        # 📝 A machine-level `output` declaration wins over the final state's
        #    own, matching XState: the machine describes what the *actor*
        #    produces, the final state only contributes done-data upward.
        if final_state.parent is self.machine or final_state.parent is None:
            machine_output = getattr(self.machine, "machine_output", None)
            if machine_output is not None:
                self._complete(self._resolve_output_value(machine_output))
            else:
                self._complete(self._resolve_output(final_state))

    def _resolve_output_value(self, output: Any) -> Any:
        """Resolves an `output` declaration to a concrete value.

        Args:
            output (Any): A literal, or a callable of `{context, event}`.

        Returns:
            Any: The resolved output, or `None` if a callable raised.
        """
        if output is None:
            return None
        if callable(output):
            try:
                return output({"context": self.context, "event": None})
            except Exception:
                logger.exception(
                    "🔥 Machine-level output function raised; using None."
                )
                return None
        return output

    def _resolve_output(self, final_state: StateNode) -> Any:
        """Computes the done data contributed by a final state.

        `output` may be a literal or a callable of ``{context, event}``,
        matching XState's dynamic-output form.

        Args:
            final_state (StateNode): The final state that was entered.

        Returns:
            Any: The resolved output, or `None` when none is declared.
        """
        output = final_state.output
        if output is None:
            return None
        if callable(output):
            try:
                return output({"context": self.context, "event": None})
            except Exception:
                logger.exception(
                    "🔥 Output function on '%s' raised; using None.",
                    final_state.id,
                )
                return None
        return output

    @property
    def last_error(self) -> Optional[BaseException]:
        """The exception behind the most recent ``last_transition_ok=False``.

        ``None`` while the last step ran cleanly. Covers every per-step
        failure both engines can report without a receipt: an action that
        raised under ``actionErrorPolicy``, an unresolvable transition
        target (#31), a missing implementation, or a `RunawayChainError`
        (#77). Reset to ``None`` at the start of each processed event.
        """
        return None if self.last_transition_ok else self._last_action_error

    def _has_error_handler_for_id(self, invoke_id: str) -> bool:
        """`_has_error_handler` by invoke id, for engines that only hold the
        id at completion time (the sync actor runner, #99)."""
        for state in list(self._active_state_nodes):
            for inv in state.invoke:
                if inv.id == invoke_id:
                    return self._has_error_handler(inv)
        return False

    def _has_error_handler(self, invocation: Any) -> bool:
        """Reports whether an invocation declares any `onError` handler.

        🏛️ Architecture decision: this asks whether a handler was *declared*,
        not whether one would currently fire. A guarded `onError` whose guard
        happens to be false still means the author considered the failure and
        chose to handle it conditionally — treating that as an unhandled crash
        would be surprising and would break existing machines. Only a total
        absence of `onError` counts as unhandled.

        Args:
            invocation (Any): The `InvokeDefinition` that failed.

        Returns:
            bool: `True` if any `onError` transition is declared.
        """
        return bool(getattr(invocation, "on_error", None))

    # 📨 Maximum events held under ``onUnhandled: "defer"`` before the
    #    oldest is evicted. A permanently-unhandled event type must not
    #    grow the buffer without bound.
    DEFER_MAX: int = 1000

    def _handle_unhandled_event(self, event: AnyEvent) -> None:
        """Apply the machine's ``onUnhandled`` policy to a matched-nothing event.

        🏛️ Architecture decision: per XState an unhandled event is silently
        ignored, and that remains the default. But on a critical path a
        typo'd event name is a silent no-op no test can catch, and a fill
        that arrives one microstep before its handler is armed is *lost*.
        Both engines route here so they cannot disagree.

        System events (``done.*``, ``after.*``, the init event) are exempt:
        the machine did not ask for them and cannot be blamed for not
        handling them.
        """
        # 🏛️ #79: exempt by PROVENANCE, not by name. A user-sent
        #    `Event("done.review")` is user traffic and must trip the policy;
        #    only events the engine minted are excused.
        if is_system_event(event) or not isinstance(event, Event):
            logger.debug("🍃 No transition for system event '%s'.", event.type)
            return

        policy = self.machine.on_unhandled
        # Report the LEAF ids the user sees, not the internal configuration
        # (which also holds every ancestor including the root).
        active = self.current_state_ids

        if policy == "error":
            err = UnhandledEventError(event.type, active)
            self._notify_unhandled(event, active, "errored")
            # 🧾 #189: the SENDER must see the kill on its receipt. `_fail`
            #    flips `status`/`error`, but the receipt is built from the
            #    step's `last_transition_ok` / `_last_action_error`, so a
            #    success-shaped `Receipt(changed=False, error=None)` went
            #    back to the very caller whose event stopped the machine.
            #    Record it as this step's failure: `Receipt.error` is the
            #    `UnhandledEventError`, on both engines.
            self.last_transition_ok = False
            self._last_action_error = err
            self._fail(err)
            return

        if policy == "defer":
            disposition = "deferred"
            if len(self._deferred_events) >= self.DEFER_MAX:
                evicted = self._deferred_events.pop(0)
                # 🔔 Report the eviction against the EVICTED event, so the
                #    caller learns which one was lost.
                self._notify_unhandled(evicted, active, "dropped")
            self._deferred_events.append(event)
            # 🧾 #84: a `wait=True` caller must not read the resulting
            #    `changed=False` as "processed, no-op". Record the hold so
            #    the receipt can say `deferred=True`.
            self._deferred_this_step.append(event)
            self._notify_unhandled(event, active, disposition)
            logger.debug(
                "📨 Deferred '%s' (%d held).",
                event.type,
                len(self._deferred_events),
            )
            return

        logger.debug("🍃 No transition found for event '%s'.", event.type)
        # 🚦 #153: "ignored" meant both "no handler declared" and "declared
        #    but every guard refused". A caller auditing per-event outcomes
        #    could not tell a typo'd event from a business-rule refusal.
        self._notify_unhandled(
            event,
            active,
            "guard_denied" if self._guard_denied_this_step else "ignored",
        )

    def _notify_unhandled(
        self, event: Event, active: Set[str], disposition: str
    ) -> None:
        for plugin in self._plugins:
            plugin.on_unhandled_event(self, event, active, disposition)

    @property
    def deferred_count(self) -> int:
        """Events currently held under ``onUnhandled: "defer"``."""
        return len(self._deferred_events)

    def _take_deferred_for_replay(self) -> List[Event]:
        """Detach the deferral buffer for replay after a state change.

        Returns the held events in original order and clears the buffer.
        The caller re-injects them at the HEAD of its queue, ahead of live
        traffic; any that are still unhandled in the new state come straight
        back through `_handle_unhandled_event` and are re-deferred, so
        nothing is re-dropped.
        """
        if not self._deferred_events:
            return []
        held, self._deferred_events = self._deferred_events, []
        return held

    def _apply_action_error_policy(
        self,
        transition: TransitionDefinition,
        failed_actions: List[Tuple[ActionDefinition, BaseException]],
    ) -> None:
        """Report a partially-executed action list and apply the policy.

        🏛️ Architecture decision: this is the single place both engines call
        when `_execute_actions` returns failures, so the two never disagree
        about what an action error means. Before 0.8.0 `_execute_actions`
        returned ``None`` unconditionally and execution fell straight through
        to `_enter_states` and `on_transition` whether or not the list had
        completed -- the machine reported a state its own actions never
        finished building.

        Under ``"continue"`` this reports and returns; the caller commits.
        Under ``"rollback"`` / ``"fail"`` it raises `_RollbackRequested`,
        which the caller's atomic block turns into a restore.
        """
        self.last_transition_ok = False
        # 🧾 Remember the first failure so a `send(wait=True)` receipt can
        #    carry it (#39). Overwritten per failing action list.
        self._last_action_error = failed_actions[0][1]
        for plug in self._plugins:
            plug.on_transition_failed(self, transition, failed_actions)
        global _WARNED_ACTION_ERROR_POLICY_DEFAULT
        if (
            self.machine.action_error_policy_is_default
            and not _WARNED_ACTION_ERROR_POLICY_DEFAULT
        ):
            # 📢 The 1.0 default will be "rollback". Warn once per PROCESS
            #    (#27 follow-up: per-MachineNode meant a service that built
            #    interpreters from one module-level machine warned exactly
            #    once, ever -- likely in a warm-up path nobody reads).
            _WARNED_ACTION_ERROR_POLICY_DEFAULT = True
            warnings.warn(
                f"Machine '{self.machine.id}': an action raised and the "
                f"transition was committed anyway because "
                f"'actionErrorPolicy' is unset (default 'continue'). This "
                f"default becomes 'rollback' in 1.0. Set 'actionErrorPolicy' "
                f"explicitly on every machine to silence this "
                f"(reported once per process).",
                DeprecationWarning,
                stacklevel=3,
            )
        if self.machine.action_error_policy != "continue":
            action_def, exc = failed_actions[0]
            raise _RollbackRequested(action_def, exc)

    def _internal_queue_depth(self) -> int:
        """How many self-raised events are queued right now (#27)."""
        queue = getattr(self, "_internal_queue", None)
        return len(queue) if queue is not None else 0

    def _discard_raised_since(self, depth_before: int) -> int:
        """Drop internal events enqueued after *depth_before* (#27).

        🏛️ Architecture decision: `rollback` restores configuration and
        context. It cannot un-send a `sendTo` to another actor -- that
        effect has left the machine -- but a `raise` is an event the
        machine queued FOR ITSELF and has not yet processed, so it is
        still ours to withdraw. Leaving it would deliver an event that
        the (now undone) transition produced into a configuration that
        never entered the state the event was meant for.

        The internal queue is never drained mid-transition, so everything
        appended since the checkpoint sits at the tail.
        """
        queue = getattr(self, "_internal_queue", None)
        if queue is None:
            return 0
        excess = max(0, len(queue) - depth_before)
        withdrawn = [queue.pop() for _ in range(excess)]
        if withdrawn:
            self._on_internal_events_withdrawn(withdrawn)
        return excess

    def _on_internal_events_withdrawn(self, events: List[Any]) -> None:
        """Engine hook: bookkeeping for events removed by a rollback.

        The async engine uses this to un-count them from its runaway-chain
        depth and to resolve any receipt a blocked self-`send()` attached.
        """

    def _finish_rollback(
        self,
        cause: BaseException,
        transition: TransitionDefinition,
        context_before: Optional[TContext],
        internal_depth_before: Optional[int] = None,
    ) -> bool:
        """Common tail of both engines' rollback paths.

        Restores context (when snapshotted), withdraws any `raise`d events
        the failed action list queued (#27), then decides what the caller
        should do with *cause*.

        Returns:
            ``True`` if the caller should swallow the exception and return
            normally (a policy-driven rollback); ``False`` if it should
            re-raise (a genuine transition-resolution failure).
        """
        if context_before is not None:
            self.context = context_before
        if internal_depth_before is not None:
            dropped = self._discard_raised_since(internal_depth_before)
            if dropped:
                logger.warning(
                    "↩️ Rolled back %d self-raised event(s) queued by the "
                    "failed transition on '%s'.",
                    dropped,
                    transition.source.id,
                )
        if not isinstance(cause, _RollbackRequested):
            return False
        if self.machine.action_error_policy == "fail":
            err = TransitionFailedError(
                cause.action_def.type, transition.source.id
            )
            err.__cause__ = cause.original
            self._stop_failed(err)
        return True

    def _set_timeout(
        self, fn: Callable[[], Any], delay_sec: float, *, owner: Any
    ) -> Any:
        """Schedule on `self.clock`, telling it which lane we drain (#76).

        Third-party clocks written against the 0.8.0 `Clock` protocol take
        no ``sync`` keyword; `_clock_accepts_sync` (decided at construction)
        selects the call shape, so the clock is invoked exactly once and any
        exception it raises is its own.
        """
        if self._clock_accepts_sync:
            return self.clock.set_timeout(
                fn, delay_sec, owner=owner, sync=self._clock_sync_lane
            )
        return self.clock.set_timeout(fn, delay_sec, owner=owner)

    def _stop_failed(self, error: TransitionFailedError) -> None:
        """``actionErrorPolicy: "fail"`` -- STOP the machine (#145).

        🏛️ The documented contract ("also stops with
        `TransitionFailedError`") is a specific outcome: ``status ==
        "stopped"``, configuration cleared, children reaped, timers
        cancelled. Routing this through `_fail` instead produced
        ``status == "error"`` with a *running-shaped* configuration still
        naming the pre-transition leaf -- a machine that looked resumable,
        answered every `send()` with a no-op, and persisted as such. The
        ``"error"`` status is for an invoked service that died (where the
        configuration legitimately still says where); a policy-driven halt
        is a stop. The exception is retained on ``error`` so the reason is
        readable after the fact; `on_error` fires because this is a
        failure, then `on_interpreter_stop` because the machine stopped.
        """
        if self.status not in ("running", "uninitialized"):
            return
        self.error = error
        logger.error(
            "🛑 Machine '%s' stopped by actionErrorPolicy='fail': %r",
            self.id,
            error,
        )
        for plugin in self._plugins:
            plugin.on_error(self, error)
        # 🧹 The configuration is gone: the failed transition rolled it back,
        #    and a stopped machine has no active state by definition. This
        #    is what makes `current_state_ids` stop lying about the leaf.
        self._active_state_nodes.clear()
        self.status = "stopped"
        self._notify_subscribers()
        self._on_terminal("stopped")
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

    def _fail(self, error: BaseException) -> None:
        """Puts the machine into the terminal `error` status.

        🏛️ Architecture decision: `status` previously only ever moved between
        `uninitialized`, `running` and `stopped`. An invoked service that
        failed with no `onError` handler logged a message and the machine kept
        running as though nothing had happened — the failure was invisible to
        any caller. XState models this as an error snapshot, so a distinct
        `"error"` status plus `interpreter.error` makes it observable.

        Args:
            error (BaseException): The unhandled error.
        """
        if self.status not in ("running", "uninitialized"):
            return
        self.status = "error"
        self.error = error
        logger.error(
            "🚨 Machine '%s' entered the error state: %r", self.id, error
        )
        for plugin in self._plugins:
            hook = getattr(plugin, "on_error", None)
            if callable(hook):
                hook(self, error)
        self._notify_subscribers()
        self._on_terminal("error")

    def _complete(self, output: Any) -> None:
        """Marks the machine as finished and records its output.

        🏛️ Architecture decision: `status` previously only ever moved between
        `uninitialized`, `running` and `stopped`, so reaching a top-level final
        state was **unobservable** from the public API. That blocked any
        `to_promise()`-style "await completion" helper. A distinct `"done"`
        status makes completion a first-class, checkable outcome.

        Args:
            output (Any): The machine's final output, if any.
        """
        if self.status != "running":
            return
        self.status = "done"
        self.output = output
        logger.info(
            "🏁 Machine '%s' reached a top-level final state. Output: %r",
            self.id,
            output,
        )
        for plugin in self._plugins:
            hook = getattr(plugin, "on_done", None)
            if callable(hook):
                hook(self, output)
        # 🧹 #57: completion REAPS. Order matters -- `on_done` above and the
        #    subscriber notification inside `_teardown` both run BEFORE
        #    children are stopped, so an observer reading `system` or a
        #    child's context at completion sees a consistent picture.
        self._on_terminal("done")

    def _on_terminal(self, status: str) -> None:
        """Common tail of `_complete()` and `_fail()`.

        Fires the completion listeners (the parent's await, #43) and then
        schedules teardown of everything the machine still holds (#57):
        child actors, timers, invoked services and its actor-system
        registration. `status`, `output`, `error` and `context` are
        deliberately RETAINED -- reading a result after completion is the
        normal pattern, and the owner can drop the reference.
        """
        listeners, self._terminal_listeners = self._terminal_listeners, []
        for listener in listeners:
            listener(status)
        self._schedule_teardown()

    def _schedule_teardown(self) -> None:
        """Engine-specific: run `_teardown()` now (sync) or as a task (async)."""
        raise NotImplementedError  # pragma: no cover

    def _unregister_from_system(self) -> None:
        """Remove every registry entry pointing at THIS interpreter (#57).

        The counterpart `_register_in_system` never had: without it the
        root's registry held a strong reference to every child that ever
        declared a `systemId`, for the life of the root.
        """
        registry = self._system_registry()
        for system_id in [k for k, v in registry.items() if v is self]:
            del registry[system_id]

    @staticmethod
    def _matching_descriptors(
        node: StateNode, event_type: str, *, system: bool = False
    ) -> List[str]:
        """Finds the `on` keys that match an event type, most specific first.

        Implements XState's event-descriptor matching:

        - an exact key (``"mouse.click"``) wins outright;
        - partial descriptors match by dot-segment prefix, longest first
          (``"mouse.click.*"`` beats ``"mouse.*"``);
        - the bare wildcard ``"*"`` matches anything and is always last.

        🏛️ Architecture decision: ordering matters -- SCXML and XState both
        require the most specific descriptor to win. Engine-synthesised
        events (`done.*`, `error.*`, `after.*`, `xstate.*`) match ONLY an
        exact key: a user's ``"*"`` means "any event I might receive", not
        "swallow my own timers and service results".

        ⚡ #55 part 2: reads the index `StateNode` precompiles at build
        time (`_on_partials`, `_on_has_wildcard`) instead of scanning the
        `on` dict per event. For the common machine with no partial
        descriptors the loop body never executes.
        """
        on_map = node.on
        if not on_map or not event_type:
            return []
        matches: List[str] = []
        if event_type in on_map:
            matches.append(event_type)
        # 🏛️ #79: engine-synthesised events match ONLY an exact key -- a
        #    `"*"` handler must not swallow `done.invoke.*`. Decided by
        #    provenance: a user event that merely LOOKS reserved still
        #    reaches `"*"` and `"prefix.*"` descriptors.
        if system:
            return matches
        for key, prefix in node._on_partials:  # already longest-first
            if event_type == prefix or event_type.startswith(prefix + "."):
                matches.append(key)
        if node._on_has_wildcard:
            matches.append("*")
        return matches

    def _collect_eligible_transitions(
        self,
        state: StateNode,
        event: AnyEvent,
        guard_cache: Optional[Dict[int, bool]] = None,
    ) -> List[TransitionDefinition]:
        """Collects every eligible transition on one state's ancestor chain.

        Walks from `state` up to the machine root, gathering transitions that
        match `event` and whose guard is satisfied. This is the per-leaf half
        of transition selection; callers decide how to rank the results.

        Args:
            state (StateNode): The active state to start the upward walk from.
            event (AnyEvent): The event being
                processed.
            guard_cache (Optional[Dict[int, bool]]): Memo of guard results for
                the current selection pass, keyed by transition identity. When
                several parallel regions share an ancestor, this ensures that
                ancestor's guard is evaluated exactly once. Pass `None` to
                disable memoisation.

        Returns:
            List[TransitionDefinition]: Eligible transitions, ordered from the
            deepest source state upward.
        """
        eligible: List[TransitionDefinition] = []

        def _passes(transition: TransitionDefinition) -> bool:
            """Evaluates a transition's guard, memoised per selection pass.

            🏛️ Architecture decision: guards are documented as pure predicates,
            but in practice users write ones with side effects (counters,
            metrics, logging). Evaluating a shared ancestor's guard once per
            region would multiply those side effects by the region count and
            fire `on_guard_evaluated` plugin hooks N times for a single logical
            decision. Memoising keeps evaluation count independent of the
            machine's parallel width.
            """
            if guard_cache is None:
                return self._is_guard_satisfied(transition.guard_def, event)
            key = id(transition)
            if key not in guard_cache:
                guard_cache[key] = self._is_guard_satisfied(
                    transition.guard_def, event
                )
            return guard_cache[key]

        # 🧭 Determine which transition flavours are in play for this event.
        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        current: Optional[StateNode] = state
        while current:
            # 📨 Standard `on` event transitions, including wildcard and
            #    partial descriptors, most specific first.
            if not is_explicit_transient_event:
                blocked = False
                for key in self._matching_descriptors(
                    current, event.type, system=is_system_event(event)
                ):
                    for t in current.on[key]:
                        # 🚫 A forbidden transition consumes the event here so
                        #    no ancestor handler can see it.
                        if t.forbidden:
                            blocked = True
                            break
                        if _passes(t):
                            eligible.append(t)
                        elif (
                            t.guard_def is not None
                            and self._pending_guard_error is None
                        ):
                            # 🚦 #153: declared, matched, refused by guard.
                            # 🧯 #170: a guard that CRASHED under
                            #    guardErrorPolicy="raise" is not a denial;
                            #    `Receipt.error` carries that case and
                            #    `denied` stays False, as documented ("the
                            #    guard returned False").
                            self._guard_denied_this_step = True
                    if blocked:
                        break
                if blocked:
                    logger.debug(
                        "🚫 Event '%s' forbidden at '%s'; stopping upward "
                        "search.",
                        event.type,
                        current.id,
                    )
                    break

            # ⚡ Transient `""` ("always") transitions.
            if is_transient_check and "" in current.on:
                for t in current.on[""]:
                    if _passes(t):
                        eligible.append(t)

            # 🏁 `onDone` transitions for compound/parallel states.
            if current.on_done and current.on_done.event == event.type:
                if _passes(current.on_done):
                    eligible.append(current.on_done)

            # ⏰ `after` transitions for timed events.
            if isinstance(event, AfterEvent):
                for transitions in current.after.values():
                    for t in transitions:
                        if t.event == event.type and _passes(t):
                            eligible.append(t)

            # 🤖 `onDone`/`onError` for invoked services. `ErrorEvent`
            #    (#80) is a distinct type so consumers can branch on it,
            #    but it routes through `inv.on_error` the same way.
            if isinstance(event, (DoneEvent, ErrorEvent)):
                for inv in current.invoke:
                    if event.src != inv.id:
                        continue
                    for t in inv.on_done + inv.on_error:
                        if t.event == event.type and _passes(t):
                            eligible.append(t)
                    # 🎯 #130: an `escalate` from the invoked child arrives as
                    #    `ErrorEvent(type="xstate.error.actor.<runtime id>")`,
                    #    not `error.platform.<id>`. It is a failure of THIS
                    #    invocation and XState routes it to `onError`; match
                    #    the declared `onError` transitions by `src` alone.
                    if isinstance(event, ErrorEvent) and event.type.startswith(
                        "xstate.error.actor."
                    ):
                        for t in inv.on_error:
                            if _passes(t):
                                eligible.append(t)

            current = current.parent

        return eligible

    def _select_transitions(
        self, event: AnyEvent
    ) -> List[TransitionDefinition]:
        """Selects the optimal transition set for an event, one per region.

        Implements the SCXML `selectTransitions` rule. For each active atomic
        state, the most deeply nested eligible transition is chosen. Because
        orthogonal (parallel) regions each contribute their own active leaf,
        this naturally yields one transition *per region* rather than a single
        winner for the whole machine.

        🏛️ Architecture decision: a previous implementation returned a single
        `max(...)` across the entire configuration, so an event handled by two
        parallel regions advanced only one of them. Selecting per leaf and then
        de-duplicating fixes that while preserving the single-fire behaviour
        for a transition defined on a shared ancestor — the same object is
        selected by several leaves but executed only once.

        Args:
            event (AnyEvent): The event being
                processed.

        Returns:
            List[TransitionDefinition]: The transitions to execute, ordered
            deepest-source-first and free of duplicates.
        """
        # 🍃 Only atomic/final leaves seed selection; ancestors are reached by
        #    the upward walk inside `_collect_eligible_transitions`.
        leaves = [
            s
            for s in self._active_state_nodes
            if s.is_atomic or s.is_final or not s.states
        ]
        # 🛟 Fallback: if the configuration has no leaf (defensive), consider
        #    every active node so behaviour degrades gracefully.
        if not leaves:
            leaves = list(self._active_state_nodes)

        selected: List[TransitionDefinition] = []
        seen: Set[int] = set()
        # 🧠 Memo shared across all leaves in this pass, so a transition on an
        #    ancestor common to several regions is guard-evaluated exactly once.
        guard_cache: Dict[int, bool] = {}

        # 🔽 Deterministic ordering: deepest leaves first, then by id.
        #    ⚡ A non-parallel machine has exactly one leaf; skip the sort.
        if len(leaves) > 1:
            leaves.sort(key=lambda s: (-s.depth, s.id))
        for leaf in leaves:
            eligible = self._collect_eligible_transitions(
                leaf, event, guard_cache
            )
            if not eligible:
                continue

            # 🏆 This leaf's winner is the transition on its deepest ancestor.
            winner = max(eligible, key=lambda t: t.source.depth)

            # 🧹 De-duplicate by identity so an ancestor transition shared by
            #    several regions fires exactly once.
            if id(winner) not in seen:
                seen.add(id(winner))
                selected.append(winner)

        # 🔽 Execute deepest-source-first for predictable action ordering.
        selected.sort(key=lambda t: -t.source.depth)
        return selected

    def _compute_states_to_exit(
        self, domain: Optional[StateNode], target_state: StateNode
    ) -> Set[StateNode]:
        """Determines which active states an external transition must exit.

        Normally every active descendant of the transition domain is exited.
        When the domain is a `parallel` state, that would sweep up the *sibling*
        regions as well — but only the branch containing the target is re-entered
        by `_get_path_to_state`, so the siblings would be exited and never
        restored, silently killing them.

        🏛️ Architecture decision: this is why the exit set is scoped to the
        domain's child that actually contains the target whenever the domain is
        parallel. Orthogonal regions are independent by definition: a transition
        inside one region must not disturb the others unless it exits the
        parallel state itself (in which case the domain is an ancestor of the
        parallel node, not the node itself, and the full sweep is correct).

        Args:
            domain (Optional[StateNode]): The transition domain (LCCA), or
                `None` when the machine root is the domain.
            target_state (StateNode): The resolved target of the transition.

        Returns:
            Set[StateNode]: The active states to exit, innermost-first ordering
            applied by the caller.
        """
        candidates = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s is not domain
        }

        # 🌐 Scope to one region when the domain is a parallel state, so
        #    orthogonal siblings are left untouched.
        if domain is not None and domain.type == "parallel":
            branch: Optional[StateNode] = target_state
            while branch is not None and branch.parent is not domain:
                branch = branch.parent
            if branch is not None:
                candidates = {
                    s
                    for s in candidates
                    if s is branch or self._is_descendant(s, branch)
                }

        return candidates

    def _transition_geometry(
        self, transition: TransitionDefinition, target_state: StateNode
    ) -> Tuple[Optional[StateNode], List[StateNode]]:
        """The static part of a transition's execution plan, memoised.

        ⚡ Returns ``(domain, path_to_enter)``. Both depend only on the
        machine tree and the resolved target, never on the live
        configuration, so they are computed once per transition and served
        from `TransitionDefinition._geometry` thereafter. History targets
        are handled by the caller (their entry path is resolved live).

        The memo is keyed on ``id(target_state)``: a transition that is
        resolved at run time (unresolvable at build under
        ``strict_targets=False``) may legitimately land on a different node
        later, and must not be served the first answer.

        Returns:
            Tuple[Optional[StateNode], List[StateNode]]: the LCCA (``None``
            when the machine root is the domain) and the parent-to-child
            entry path from the domain down to the target. The list is a
            fresh copy so callers may mutate it.
        """
        memo = transition._geometry
        if memo is not None and memo[0] == id(target_state):
            return memo[1], list(memo[2])
        domain = self._find_transition_domain(transition, target_state)
        path = self._get_path_to_state(target_state, stop_at=domain)
        transition._geometry = (id(target_state), domain, tuple(path))
        return domain, path

    def _find_transition_domain(
        self, transition: TransitionDefinition, target_state: StateNode
    ) -> Optional[StateNode]:
        """Calculates the transition domain (LCCA) for an external transition.

        The "domain" is the least common compound ancestor (LCCA) of the source
        and target states. It determines which states are exited and entered.

        For a self-transition (including re-entering ones), the domain is
        always the parent state, which ensures the source state is correctly
        exited and re-entered.

        Args:
            transition (TransitionDefinition): The external transition to analyze.
            target_state (StateNode): The pre-resolved target state node.

        Returns:
            Optional[StateNode]: The state node that is the LCCA, or None if the
            root is the domain.
        """
        parent = transition.source.parent or self.machine

        # For any self-transition, the domain is the parent. This forces an
        # exit/re-entry cycle for the source state.
        if target_state == transition.source:
            return parent

        # Standard case: Compute the Least Common Compound Ancestor (LCCA).
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)
        common_ancestors = source_ancestors & target_ancestors

        # 🎯 When the target is an ancestor of the source, the LCCA *is* the
        # target. Using it directly as the domain would make
        # `_get_path_to_state(target, stop_at=domain)` return an empty path,
        # so the machine would exit down to the target and never re-enter it —
        # left on a non-atomic ancestor with no active leaf.
        #
        # 🏛️ Architecture decision: step up to the target's PARENT rather than
        # discarding the target from the candidate set. Discarding re-ran
        # `max()` over the remaining common ancestors, which for a region of a
        # `parallel` state selected the parallel node itself — placing every
        # *sibling* region in `states_to_exit` while the entry path only
        # re-entered the targeted region. The siblings were exited and never
        # restored, permanently killing them. The parent is the correct domain:
        # it exits and re-enters exactly the target subtree.
        if target_state in source_ancestors:
            return target_state.parent or self.machine

        if not common_ancestors:
            # Fallback to parent (or machine root) if no commonality is found.
            return parent

        # The LCCA is the deepest common ancestor.
        return max(common_ancestors, key=lambda n: n.depth)

    @staticmethod
    def _get_path_to_state(
        to_state: StateNode, *, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Builds the ordered list of states to enter to reach a target.

        This method traces the ancestry from the target state (`to_state`) up
        to, but not including, a specified `stop_at` ancestor (typically the
        transition domain). The resulting path is then reversed to provide the
        correct parent-to-child entry order.

        Args:
            to_state (StateNode): The destination state.
            stop_at (Optional[StateNode]): The ancestor at which to stop
                traversing.

        Returns:
            List[StateNode]: A list of states to be entered, from outermost
            to innermost.
        """
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        # Reverse to get parent -> child order for correct state entry.
        path.reverse()
        return path

    @staticmethod
    def _get_ancestors(node: StateNode) -> Set[StateNode]:
        """Gets the set of all ancestors of a node, including the node itself.

        Args:
            node (StateNode): The node from which to find ancestors.

        Returns:
            Set[StateNode]: A set containing the node and all of its parents.
        """
        ancestors: Set[StateNode] = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """Checks if a node is a descendant of a specified ancestor.

        A node is considered a descendant of another if its ID starts with the
        ancestor's ID followed by a dot, or if it is the ancestor itself.

        Args:
            node (StateNode): The potential descendant node.
            ancestor (Optional[StateNode]): The potential ancestor node. If
                `None`, it represents the machine root, and this method will
                always return `True`.

        Returns:
            bool: `True` if `node` is a descendant of `ancestor`.
        """
        # If no ancestor is specified, it's the machine root, so all nodes are descendants.
        if not ancestor:
            return True
        # Check for self or if the ID indicates a child relationship.
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    # -------------------------------------------------------------------------
    # 🛡️ Task & Guard Management
    # -------------------------------------------------------------------------

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules `after` and `invoke` tasks for a state upon its entry.

        This method dispatches to the abstract `_after_timer` and
        `_invoke_service` methods, which are implemented by the concrete
        sync/async subclasses to handle the actual execution.

        Args:
            state (StateNode): The state being entered.
        """
        self._schedule_state_timers(state)
        self._schedule_state_invokes(state)

    def _schedule_state_timers(self, state: StateNode) -> None:
        """Arm every ``after`` timer *state* declares (#128 split).

        Separate from invoke scheduling so a restore can re-arm timers
        without re-invoking services (or vice versa).
        """
        # 🕒 Schedule `after` timers.
        for delay_ms, transitions in state.after.items():
            # 🏷️ Symbolic delays resolve through MachineLogic.delays.
            resolved_ms = self._resolve_delay(delay_ms, None)
            if resolved_ms is None:
                logger.warning(
                    "⚠️ Skipping 'after' transition on '%s': delay %r could "
                    "not be resolved.",
                    state.id,
                    delay_ms,
                )
                continue
            for t_def in transitions:
                delay_sec = float(resolved_ms) / 1000.0
                # 📏 #48: record the deadline so the fired event can report
                #    its own lateness.
                after_event = AfterEvent(
                    type=t_def.event,
                    scheduled_for=self.clock.now() + delay_sec,
                )
                self._after_timer(delay_sec, after_event, owner_id=state.id)
                logger.debug(
                    "🕒 Scheduled 'after' event '%s' in %.2fs for state '%s'.",
                    t_def.event,
                    delay_sec,
                    state.id,
                )

    def _schedule_state_invokes(self, state: StateNode) -> None:
        """Start every ``invoke`` *state* declares (#128 split)."""
        # 📞 Schedule `invoke` services.
        for invocation in state.invoke:
            service_callable = (
                self.machine.logic.services.get(invocation.src)
                if invocation.src
                else None
            )
            # 💥 Fail-fast if the service implementation is missing.
            if service_callable is None:
                # FIX: Reverted error message to match test suite expectations.
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' referenced by "
                    f"state '{state.id}' is not registered."
                )
            self._invoke_service(
                invocation, service_callable, owner_id=state.id
            )
            logger.debug(
                "📞 Invoking service '%s' for state '%s'.",
                invocation.src,
                state.id,
            )

    def _is_guard_satisfied(
        self,
        guard: Optional[Union[str, "GuardDefinition"]],
        event: AnyEvent,
    ) -> bool:
        """Evaluates a transition guard in any of its supported forms.

        Handles the four shapes XState accepts:

        - a named predicate (``"isReady"``),
        - a parameterised predicate (``{"type": ..., "params": ...}``),
        - a higher-order composition (``and`` / ``or`` / ``not``),
        - the built-in ``stateIn`` guard.

        Args:
            guard (Optional[Union[str, GuardDefinition]]): The guard to
                evaluate. `None` means the transition is unguarded.
            event (AnyEvent): The current event,
                passed to user predicates.

        Returns:
            bool: `True` if the guard passes or there is no guard. A guard
            that raises is treated as `False`.

        Raises:
            ImplementationMissingError: If a named guard has no implementation
                in the machine's logic.
        """
        # ✅ A transition without a guard is always allowed.
        if guard is None:
            return True

        # 🔁 Accept a bare string for backward compatibility with callers that
        #    still pass `transition.guard`.
        if isinstance(guard, str):
            guard = GuardDefinition(guard)

        # 🌳 Composite guards recurse and short-circuit, exactly like XState's
        #    `and()` / `or()` / `not()` helpers.
        if guard.is_composite:
            if guard.type == "and":
                return all(
                    self._is_guard_satisfied(child, event)
                    for child in guard.children
                )
            if guard.type == "or":
                return any(
                    self._is_guard_satisfied(child, event)
                    for child in guard.children
                )
            # `not` is validated at parse time to have exactly one child.
            return not self._is_guard_satisfied(guard.children[0], event)

        # 📍 The built-in `stateIn` guard is answered from the active
        #    configuration; it needs no user implementation.
        #
        # 🏛️ Architecture decision: a USER implementation wins, mirroring the
        # documented resolution order for actions (`actions.is_builtin`).
        # Without this a guard the user registered as `stateIn` was never
        # called and the transition was silently decided by the built-in
        # state test instead — a silent behaviour swap, the worst kind.
        if guard.is_state_in and guard.type not in self.machine.logic.guards:
            return self._is_state_in(guard, event)

        # 🔍 Find the guard function in the machine's logic.
        guard_callable = self.machine.logic.guards.get(guard.type)
        if not guard_callable:
            # FIX: Reverted error message to match test suite expectations.
            raise ImplementationMissingError(
                f"Guard '{guard.type}' not implemented."
            )

        # 🏃 Execute the guard function.
        #
        # 🏛️ Architecture decision: a guard is a *predicate supplied by the
        # user*, so a raised exception is a defect in that predicate rather
        # than a machine-level failure. Per the documented contract it
        # evaluates to `False`, blocking this transition while leaving the
        # machine responsive and allowing any lower-priority transition (e.g.
        # an unguarded fallback in the same `on` array) to be considered.
        # A *missing* guard still raises above — that is a configuration
        # error, not a runtime condition, and must fail loudly.
        try:
            params = self._resolve_params(guard.params, event)
            result = bool(
                self._call_with_optional_params(
                    guard_callable, self.context, event, params
                )
            )
        except Exception as exc:
            # 🛡️ #35: apply the machine's guard_error_policy. Before 0.8.0 a
            #    raising guard was unconditionally `False` -- a crashing
            #    risk check and a failing one were indistinguishable to
            #    every observer. The hook fires under EVERY policy so the
            #    failure is observable even when the default keeps the
            #    0.7.x behaviour.
            policy = self.machine.guard_error_policy
            logger.exception(
                "🔥 Guard '%s' raised an exception while evaluating event "
                "'%s'; guardErrorPolicy=%r.",
                guard.type,
                event.type,
                policy,
            )
            for plugin in self._plugins:
                plugin.on_guard_error(self, guard.type, event, exc)
            if policy == "raise":
                # 🛡️ #152: do NOT propagate out of the selection pass. That
                #    cancelled every lower-priority candidate in the same
                #    transition array -- the unguarded fallback that exists
                #    to catch a failing check was never evaluated, and on an
                #    engine-driven event (`invoke.onDone`) the completion was
                #    simply lost. Record it; `_process_event` raises it after
                #    the pass, so the caller-facing contract ("the exception
                #    propagates") holds while the fallback is still taken.
                if self._pending_guard_error is None:
                    self._pending_guard_error = exc
                # A raised guard has no RESULT to report: `on_guard_error`
                # already fired, and the pre-#152 trace never followed it
                # with `on_guard_evaluated`. Keep that surface stable.
                return False
            result = policy == "true"

        # 📉 #55: DEBUG, not INFO. This runs on EVERY guard evaluation; at
        #    INFO it was one of four hot-path log calls costing ~4x
        #    throughput for anyone with INFO logging configured.
        logger.debug(
            "🛡️  Evaluating guard '%s': %s",
            guard.type,
            "✅ Passed" if result else "❌ Failed",
        )

        # 🔔 Notify any registered plugins about the evaluation.
        for plugin in self._plugins:
            plugin.on_guard_evaluated(self, guard.type, event, result)

        return result

    def _is_state_in(
        self,
        guard: "GuardDefinition",
        event: AnyEvent,
    ) -> bool:
        """Evaluates the built-in ``stateIn`` guard.

        Satisfied when the named state is part of the active configuration —
        either as an active leaf or as an ancestor of one.

        Args:
            guard (GuardDefinition): The `stateIn` guard, whose params carry
                the state id under `state` (or `value`).
            event (AnyEvent): The current event,
                used only to resolve callable params.

        Returns:
            bool: `True` when the named state is active.
        """
        params = self._resolve_params(guard.params, event)
        target = None
        if isinstance(params, dict):
            target = params.get("state", params.get("value"))
        elif isinstance(params, str):
            target = params
        if not isinstance(target, str) or not target:
            logger.warning(
                "⚠️ 'stateIn' guard has no state id in its params; "
                "treating as False."
            )
            return False

        # 🎯 Accept both '#machine.a.b' and 'machine.a.b' spellings.
        normalised = target[1:] if target.startswith("#") else target
        # 🏛️ #132: a BARE name (no dot) is a convenience, not a guess. If more
        #    than one state in the whole machine has that bare name, the
        #    guard used to match whichever happened to be active -- a
        #    silently wrong answer in a parallel machine. Reject at first
        #    use with a typed error naming every candidate.
        if "." not in normalised:
            matches = [
                sid for sid in self.machine.state_ids_by_bare_name(normalised)
            ]
            if len(matches) > 1:
                raise InvalidConfigError(
                    f"'stateIn' guard '{target}' is ambiguous: it names "
                    f"{sorted(matches)}. Use a fully qualified id."
                )
        for node in self._active_state_nodes:
            if node.id == normalised or node.id.endswith("." + normalised):
                return True
        return False

    def _resolve_params(self, params: Any, event: AnyEvent) -> Any:
        """Resolves action/guard params, invoking them if they are callable.

        🏛️ Architecture decision: XState v5 allows `params` to be a function of
        `{context, event}`, evaluated fresh on every use. Previously a callable
        was passed through verbatim, so user code received a raw function
        object where it expected a dict — silent corruption that surfaced far
        from its cause.

        Args:
            params (Any): The declared params, possibly a callable.
            event (AnyEvent): The triggering event.

        Returns:
            Any: The resolved params.
        """
        if callable(params):
            return params({"context": self.context, "event": event})
        return params

    @staticmethod
    def _call_with_optional_params(
        fn: Callable[..., Any],
        context: Any,
        event: AnyEvent,
        params: Any,
    ) -> Any:
        """Calls a guard, passing `params` only if it accepts a third argument.

        📝 Guards have always been `(context, event)`. Parameterised guards
        need a third argument, but existing two-argument guards must keep
        working unchanged, so the arity is inspected once per call.

        Args:
            fn (Callable[..., Any]): The guard implementation.
            context (Any): The interpreter's context.
            event (AnyEvent): The current event.
            params (Any): Resolved params, or `None`.

        Returns:
            Any: Whatever the guard returns.
        """
        if params is None:
            return fn(context, event)
        try:
            signature = inspect.signature(fn)
            accepts = len(
                [
                    p
                    for p in signature.parameters.values()
                    if p.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]
            )
            has_varargs = any(
                p.kind is inspect.Parameter.VAR_POSITIONAL
                for p in signature.parameters.values()
            )
        except (TypeError, ValueError):  # pragma: no cover - builtins
            return fn(context, event)

        if has_varargs or accepts >= 3:
            return fn(context, event, params)
        return fn(context, event)
