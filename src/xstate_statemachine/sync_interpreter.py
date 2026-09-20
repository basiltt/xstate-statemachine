# /src/xstate_statemachine/sync_interpreter.py
# -----------------------------------------------------------------------------
# ⛓️ Synchronous State Machine Interpreter
# -----------------------------------------------------------------------------
# This module provides the `SyncInterpreter`, a fully synchronous engine for
# executing state machines. It inherits from `BaseInterpreter` and implements
# a blocking, sequential event processing model.
#
# This interpreter is designed for use cases where asynchronous programming is
# not necessary or desired, such as in command-line tools, desktop GUI
# event loops, or for simpler, predictable testing scenarios.
#
# It adheres to the "Template Method" pattern by overriding the abstract async
# methods from `BaseInterpreter` with concrete synchronous implementations,
# while intentionally raising `NotSupportedError` for features that are
# incompatible with a purely synchronous runtime (e.g., async services,
# async actions, or timers requiring an event loop).

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import copy
import functools
import inspect
import logging
import threading
import time
import uuid
from collections import deque
from typing import (
    Literal,
    Any,
    Callable,
    Deque,
    Dict,
    FrozenSet,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    overload,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .base_interpreter import AnyEvent, BaseInterpreter, _RollbackRequested
from .exceptions import RunawayChainError
from .clock import Clock, SimulatedClock
from .events import (
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    Receipt,
    is_system_event,
)
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
    NotSupportedError,
    StateNotFoundError,
)
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TransitionDefinition,
    DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS,
    SPAWN_BLOCKING_PREFIX,
    spawn_service_key,
)

# 🧹 #60: built-in action dispatch (.actions) and target resolution
# (.resolver) now live entirely in base_interpreter.py after the "one
# core algorithm" consolidation -- nothing here references them anymore.

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ⛓️ SyncInterpreter Class Definition
# -----------------------------------------------------------------------------
_T = TypeVar("_T")


class _Done(Generic[_T]):
    """An already-finished awaitable.

    🏛️ #60: the base algorithm is written once, as coroutines that `await`
    only the interpreter's own LEAF methods. On the sync engine every leaf
    has finished by the time it returns, so it returns one of these:
    `await _Done(v)` yields `v` immediately, never suspending. `_drive()`
    can therefore run any base coroutine to completion in a single
    `send(None)`, and if some leaf ever does suspend, that is a bug the
    driver reports instead of silently hanging.

    Also truthy/falsy like its value for callers that never await it
    (`if interp.send(...)`), which keeps `send()`'s return usable both
    ways.
    """

    __slots__ = ("value",)

    def __init__(self, value: _T) -> None:
        self.value = value

    def __await__(self):  # type: ignore[no-untyped-def]
        if False:  # pragma: no cover - makes this a generator
            yield
        return self.value

    def __bool__(self) -> bool:
        return bool(self.value)

    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __repr__(self) -> str:
        return repr(self.value)


class SyncInterpreter(BaseInterpreter[TContext]):
    """Brings a state machine definition to life by interpreting its behavior synchronously.

    The `SyncInterpreter` manages the machine's state and processes events
    sequentially and immediately within the `send` method call. It is suitable
    for simpler, blocking workflows where asynchronous operations are not needed.

    **Key Characteristics**:
    - **Blocking Execution**: The `send` method blocks until the current event
      and all resulting transitions (including transient "always" transitions)
      are fully processed.
    - **Sequential Processing**: Events are handled one at a time from an
      internal queue, ensuring a predictable order of operations.

    **Design Pattern**:
    This class is a concrete implementation of the "Template Method" pattern
    defined in `BaseInterpreter`. It provides synchronous versions of abstract
    methods related to action execution and service invocation.

    Attributes:
        _event_queue (Deque[AnyEvent]): A queue to
            manage the event processing sequence in a first-in, first-out (FIFO) manner.
        _is_processing (bool): A flag to prevent re-entrant event processing,
            ensuring atomicity of a single `send` call's execution loop.
        _timer_handles (Dict[str, List[Any]]): Clock handles for `after` timers
            and delayed sends, keyed by owning state id.
    """

    # -------------------------------------------------------------------------
    # 🧙 Magic Methods & Initialization
    # -------------------------------------------------------------------------

    # ⚡ See BaseInterpreter.__slots__.
    __slots__ = (
        "_held_replays",
        "_is_processing",
        "_pump_thread_ident",
        "_settle_iterations",
        "_settle_tripped",
    )

    def __init__(
        self,
        machine: MachineNode[TContext],
        input: Optional[Any] = None,
        clock: Optional[Clock] = None,
        strict: Optional[bool] = None,
    ) -> None:
        """Initializes a new synchronous Interpreter instance.

        Args:
            machine: The state machine definition that this interpreter will run.
            input: Creation input for a `context` factory.
            clock: Source of time (#49). Defaults to `RealClock`, whose
                sync-side timers are a thread-free deadline list drained by
                :meth:`tick` / :meth:`send` (#50).
        """
        # 🤝 Initialize the base interpreter first
        super().__init__(
            machine,
            interpreter_class=SyncInterpreter,
            input=input,
            clock=clock,
            strict=strict,
        )
        #: 🔁 #103: settle-loop budget for the CURRENT drain; reset per drain.
        self._settle_iterations: int = 0
        self._settle_tripped: bool = False
        #: ⏱️ #76: the sync engine only ever drains the clock's heap (via
        #: `tick()` and the pump in `send()`), so its deadlines must land
        #: there even when it is constructed inside a running asyncio loop.
        self._clock_sync_lane = True
        #: ⏱️ Live clock handles per owning state id, so exiting a state
        #: cancels its timers on any Clock (#49/#50).
        self._timer_handles: Dict[str, List[Any]] = {}
        _info = logger.isEnabledFor(logging.INFO)  # ⚡ per construction
        if _info:
            logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")

        # ⚙️ Initialize synchronous-specific attributes
        self._event_queue: Deque[AnyEvent] = deque()
        #: 🔁 #36: events raised BY this machine during a macrostep, drained
        #: before the next external event (SCXML internal queue).
        self._internal_queue: Deque[AnyEvent] = deque()
        self._is_processing: bool = False
        #: 🧵 #183/#184: ident of the pump thread when this interpreter runs
        #: as a non-blocking child actor; `None` when steps run on the
        #: caller's thread. Read by a parent's snapshot to decide whether a
        #: bounded wait can let a mid-step child settle.
        self._pump_thread_ident: Optional[int] = None
        #: 📨 #125: deferred events whose replay was EARNED by the drain in
        #: progress (a configuration change) but must not run inside it --
        #: the caller's `Receipt` is built from the drain's result, and a
        #: replay folding into it made `send("ARM")` report the state the
        #: replayed event reached. Held here, run as a separate drain by the
        #: public entry point once the receipt is final. Mirrors the async
        #: engine's `_replay_pending`.
        self._held_replays: List[AnyEvent] = []
        # 🏛️ #50: `_after_threads` / `_after_events` / `_pending_send_cancels`
        #    are gone. Timers no longer own threads; see `_after_timer`.

        if _info:
            logger.info(
                "✅ Synchronous Interpreter '%s' initialized. 🎉", self.id
            )

    # -------------------------------------------------------------------------
    # 🚗 Driving the shared algorithm (#60)
    # -------------------------------------------------------------------------
    @staticmethod
    def _drive(coro: Any) -> Any:
        """Run a base-algorithm coroutine to completion, synchronously.

        The base steps await only leaves that return `_Done`, so the very
        first `send(None)` must raise `StopIteration`. If it does not, a
        leaf genuinely suspended -- an async action slipped through, or a
        new leaf awaits real I/O -- and that is reported loudly rather
        than left to hang.
        """
        try:
            coro.send(None)
        except StopIteration as stop:
            return stop.value
        coro.close()
        raise RuntimeError(
            "SyncInterpreter: a core-algorithm coroutine suspended. A leaf "
            "method awaited real I/O; every sync leaf must return `_Done`."
        )

    # -------------------------------------------------------------------------
    # 🌐 Public API
    # -------------------------------------------------------------------------

    def start(self) -> "SyncInterpreter[TContext]":
        """Starts the interpreter and transitions it to its initial state.

        This method is idempotent; calling `start` on an already running or
        stopped interpreter has no effect. Unlike asynchronous interpreters,
        this does not start a background event loop but simply sets the machine
        to its entry state and processes any immediate "always" transitions.

        Returns:
            The interpreter instance itself, allowing for method chaining.

        Example:
            >>> machine = create_machine(...) # noqa
            >>> interpreter = SyncInterpreter(machine).start()
            >>> print(interpreter.status)
            'running'
        """
        # 🚦 Idempotency check: only start if uninitialized.
        #
        # 🛑 A STOPPED interpreter is a different case from an already-running
        #    one. Silently returning `self` made restart look like it worked:
        #    the state ids still read as live, but `status` stayed "stopped"
        #    and every subsequent `send()` was dropped. Interpreters are not
        #    restartable — build a fresh one (optionally from a snapshot) —
        #    so say so loudly instead of handing back a corpse.
        if self.status == "stopped":
            raise InvalidConfigError(
                f"Interpreter '{self.id}' has been stopped and cannot be "
                f"restarted. Create a new interpreter, or restore one with "
                f"`SyncInterpreter.from_snapshot(...)`."
            )
        if self.status == "running" and (
            self._restart_services_on_start or self._restart_timers_on_start
        ):
            # 🔁 #44: restored with restart_services=True. Sync services run
            #    inline, so this both re-invokes and processes their results.
            # ⏱️ #128: restart_timers re-arms `after` deadlines from zero.
            logger.info("♻️ Resuming restored interpreter '%s'...", self.id)
            # 🕰️ #154: the restore branches returned BEFORE the normal
            #    path's `clock._attach(self.tick)`, so a deadline re-armed
            #    by `restart_timers=True` sat on a `SimulatedClock` that had
            #    no settler -- `increment()` fired nothing. Attach first.
            self._attach_clock()
            if self._restart_services_on_start:
                self._restart_services_on_start = False
                self._restart_dormant_invocations()
            if self._restart_timers_on_start:
                self._restart_timers_on_start = False
                self._rearm_dormant_timers()
            self._process_event_queue()
            self._process_transient_transitions()
            return self
        if self.status == "running" and self._event_queue:
            # ♻️ Restored from a snapshot WITH a persisted inbox (review F8):
            #    `from_snapshot` sets status "running" and re-enqueues the
            #    events, so the plain "already running" early-return below
            #    would leave them sitting until an unrelated send() happened
            #    to flush them, interleaved with new work. Replay them now,
            #    in order -- the async engine's run loop does the same the
            #    moment it starts.
            logger.info("♻️ Resuming restored interpreter '%s'...", self.id)
            self._attach_clock()  # #154: see above
            self._process_event_queue()
            self._process_transient_transitions()
            return self
        if self.status != "uninitialized":
            logger.info(
                "🚧 Interpreter '%s' already running. Skipping start.",
                self.id,
            )
            return self

        _info = logger.isEnabledFor(logging.INFO)  # ⚡ per start()
        if _info:
            logger.info("🏁 Starting sync interpreter '%s'...", self.id)
        self.status = "running"
        # 🧪 A SimulatedClock drives us through `tick()` after each increment
        #    so `clock.increment(ms)` leaves the machine settled (#49).
        self._attach_clock()

        # ✅ Define a pseudo-transition for the initial state entry. ⚡ It
        #    exists only to be reported to `on_transition`; do not build it
        #    (a TransitionDefinition plus a system event, ~1.3 µs) when
        #    nobody is listening.
        plugins = self._plugins
        initial_transition = (
            TransitionDefinition(
                event="___xstate_statemachine_init___",
                config={},
                source=self.machine,
            )
            if plugins
            else None
        )

        # 🔌 Notify plugins about the interpreter start
        for plugin in plugins:
            plugin.on_interpreter_start(self)

        # Capture the pre-transition state set (empty before initialization)
        pre_states = set(self._active_state_nodes)

        # ➡️ Enter the machine's initial states.
        #
        # 🏛️ Architecture decision: initial entry runs behind the re-entrancy
        # guard. An entry action may `raise` an event, and `send` processes
        # the queue immediately; without the guard that event would be handled
        # *while the machine was still descending into its initial states*,
        # transitioning away from a half-built configuration and leaving two
        # active leaves. Guarding defers such events until entry has settled,
        # after which the queue is drained normally.
        self._is_processing = True
        try:
            self._drive(self._enter_states([self.machine]))
        finally:
            self._is_processing = False
        # 📬 Drain anything an entry action raised during that descent.
        self._process_event_queue()
        # 🔄 Process any immediate "always" transitions upon startup.
        self._process_transient_transitions()

        # Capture the post-transition state set after initialization
        post_states = set(self._active_state_nodes)

        # 🔌 Notify plugins about the initial transition with accurate state info
        if initial_transition is not None:
            for plugin in plugins:
                plugin.on_transition(
                    self, pre_states, post_states, initial_transition
                )

        if _info:
            logger.info(
                "✨ Sync interpreter '%s' started. Current states: %s",
                self.id,
                self.current_state_ids,
            )
        return self

    def stop(self, *, drain: bool = False) -> None:
        """Stops the interpreter and cleans up all associated resources.

        This method stops all child actors, cancels any pending `after` timers,
        and sets the interpreter's status to 'stopped', preventing further
        event processing. It's idempotent.

        Args:
            drain: Process any events still queued before tearing down
                (#47). The sync engine processes inline, so the queue is
                only ever non-empty when `stop()` is called from INSIDE an
                action; `drain=True` finishes that macrostep first.
        """
        # 🚦 Idempotency check.
        if self.status in ("uninitialized", "stopped"):
            return
        # 🏁 #57: a terminal machine already reaped itself in `_on_terminal`;
        #    `stop()` is a quiet no-op that keeps `status` as "done"/"error".
        if self.status in ("done", "error"):
            self._teardown()
            return

        if drain and self.status == "running" and not self._is_processing:
            self._process_event_queue()
        if self._event_queue:
            logger.warning(
                "📬 Interpreter '%s' stopping with %d pending event(s) that "
                "will NOT be processed. Use stop(drain=True), or read "
                "`pending_events` / `get_snapshot()` to persist them.",
                self.id,
                len(self._event_queue),
            )
            # 🔔 #129: every other loss site fires the hook; `stop()` was
            #    the one that did not. An accepted event that will never run
            #    is a drop, reason "stopped".
            for ev in list(self._event_queue):
                for plugin in self._plugins:
                    plugin.on_event_dropped(self, ev, "stopped")

        logger.info(
            "🛑 Stopping sync interpreter '%s' and its actors…", self.id
        )

        # 📝 Status is set to "stopped" FIRST so a cyclic actor graph
        #    terminates: the child's own `stop()` re-enters this one, which
        #    now hits the idempotency guard instead of recursing forever.
        self.status = "stopped"
        self._teardown()

        # 4️⃣ Notify plugins about the stop event
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        logger.info("🕊️ Sync interpreter '%s' stopped successfully.", self.id)

    # 🧷 Overloads: `wait=True` -> Receipt; otherwise None. The two
    #    keyword flags are spelled in every overload so a checker rejects
    #    `wait="yes"` / `priority="high"` instead of swallowing them into
    #    `**payload` -- which is exactly what happened before, silently.
    @overload
    def send(  # noqa: E704
        self,
        event_type: str,
        /,
        *,
        wait: Literal[True],
        priority: bool = ...,
        **payload: Any,
    ) -> Receipt: ...

    @overload
    def send(  # noqa: E704
        self,
        event_type: str,
        /,
        *,
        wait: Literal[False] = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> None: ...

    @overload
    def send(  # noqa: E704
        self,
        event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent],
        /,
        *,
        wait: Literal[True],
        priority: bool = ...,
        **payload: Any,
    ) -> Receipt: ...

    @overload
    def send(  # noqa: E704
        self,
        event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent],
        /,
        *,
        wait: Literal[False] = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> None: ...

    @overload
    def send(  # noqa: E704
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> Optional[Receipt]: ...

    def send(  # type: ignore[override, misc]
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = False,
        priority: bool = False,
        **payload: Any,
    ) -> Optional[Receipt]:
        """Sends an event to the machine for immediate, synchronous processing.

        The sync engine already answers inline: by the time `send()`
        returns, the macrostep has run. `wait=True` therefore returns a
        :class:`Receipt` for API symmetry with the async engine (#39);
        `priority` is accepted and irrelevant (there is no backlog to
        jump -- the queue is drained before `send()` returns).

        Event shapes and what is validated (#113 / #161): a ``str`` is the
        type; a ``dict`` must carry a non-empty ``str`` ``"type"`` and every
        other key must be a ``str`` (those become the payload; their VALUES
        are not inspected -- payload semantics are domain-specific and belong
        to ``event_schemas``); an `Event` / `DoneEvent` / `AfterEvent` /
        `ErrorEvent` is passed through. Anything else raises
        `InvalidEventError` (also a `TypeError`), and `on_invalid_event`
        fires first (#159).
        """
        if self.status != "running":
            # 🔔 #123: parity with the async engine -- a send to a stopped /
            #    done / errored machine is a DROP and fires the hook, so an
            #    audit trail built from plugin hooks sees it on both engines.
            logger.warning("🚫 Cannot send event. Interpreter is not running.")
            try:
                dropped = self._prepare_event(event_or_type, **payload)
            except Exception:  # noqa: BLE001 -- malformed AND misdirected
                return None
            for plugin in self._plugins:
                plugin.on_event_dropped(self, dropped, "not_running")
            return None

        event_obj = self._prepare_event_reporting(event_or_type, **payload)
        self._warn_reserved_payload_keys(event_obj)
        self._check_strict(event_obj)  # #51
        # ⚡ Everything that exists only to build a `Receipt` is skipped for
        #    the fire-and-forget (`wait=False`) shape: the before-snapshot
        #    of the configuration, the context deep-copy (see
        #    Interpreter._run_event_loop: no actions -> context is fixed) and
        #    the per-step bookkeeping flags are read by nobody when no
        #    receipt is returned.
        config_before: Optional[FrozenSet[StateNode]] = None
        context_before: Optional[Any] = None
        # 🧹 #188: the per-step scopes are reset on EVERY step, not only
        #    when a receipt will read them. `_deferred_this_step` is a list
        #    that `_defer_event` appends to; skipping the clear on the
        #    fire-and-forget path let it grow by one entry per deferred
        #    event for the life of the process and left the next `wait=True`
        #    receipt reading a `deferred` flag contaminated by earlier steps.
        #    Two O(1) writes; the deep-copy below is the only thing worth
        #    gating on `wait`.
        self._deferred_this_step.clear()  # #106: per-step scope
        self._guard_denied_this_step = False  # #153: per-step scope
        if wait:
            config_before = frozenset(self._active_state_nodes)
            if not self.machine.context_is_immutable:
                context_before = copy.deepcopy(self.context)
        self.last_transition_ok = True
        step_error: Optional[BaseException] = None
        # ⏰ #50: deliver every deadline that has elapsed BEFORE this event,
        #    on this thread, in due order -- the pump.
        self._pump_timers()
        self._event_queue.append(event_obj)
        try:
            self._process_event_queue()
        except Exception as exc:
            # 🏛️ #31 (runtime parity): whatever the caller sees, the
            #    interpreter's own record must agree with the async engine's
            #    -- a step that raised is not `last_transition_ok`.
            self.last_transition_ok = False
            self._last_action_error = exc
            if not wait:
                raise
            step_error = exc
        if not wait:
            self._run_held_replays()
            return None
        if step_error is None and not self.last_transition_ok:
            step_error = self._last_action_error
        changed = frozenset(self._active_state_nodes) != config_before or (
            context_before is not None and self.context != context_before
        )
        deferred = any(ev is event_obj for ev in self._deferred_this_step)
        receipt = Receipt(
            frozenset(self.current_state_ids),
            changed,
            step_error,
            deferred,
            denied=not changed and self._guard_denied_this_step,
        )
        # 📨 #125: the caller's receipt is FINAL before any replay runs.
        self._run_held_replays()
        return receipt

    def _run_held_replays(self) -> None:
        """Run deferred events earned by the last drain, as their own
        macrostep(s) (#125). Each replay may itself earn further replays;
        loop until none are held. Bounded by the drain's own chain budget.
        """
        # ⚡ Common case: nothing held -- one attribute read, no loop.
        if not self._held_replays:
            return
        while self._held_replays and self.status == "running":
            held, self._held_replays = self._held_replays, []
            self._event_queue.extend(held)
            self._process_event_queue()

    # -------------------------------------------------------------------------
    # 🏁 Reaping (#57)
    # -------------------------------------------------------------------------
    def _schedule_teardown(self) -> None:
        # 🧵 Sync engine: no loop to defer to, and `_complete()` runs at the
        #    end of a macrostep, so tearing down inline is safe.
        self._teardown()

    def _teardown(self) -> None:
        """Release everything except `status` / `output` / `error` / `context`.

        Shared by `stop()` and by reaching a terminal status (#57).
        """
        self._detach_clock()  # #115
        # 1️⃣ Stop every child actor (blocking & non-blocking).
        for actor_id, actor in list(self._actors.items()):
            try:
                actor.stop()
            finally:
                self._actors.pop(actor_id, None)

        # 2️⃣ Cancel every clock-scheduled timer and delayed send (#50).
        for handles in self._timer_handles.values():
            for handle in handles:
                self.clock.clear_timeout(handle)
        self._timer_handles.clear()
        self._scheduled_sends.clear()
        self._internal_queue.clear()  # mid-macrostep state; never persisted

        # 4️⃣ Drop our own registry entry so the root does not pin us.
        self._unregister_from_system()

    # -------------------------------------------------------------------------
    # 📬 Inbox (#47)
    # -------------------------------------------------------------------------
    def _snapshot_pending_events(
        self,
    ) -> List[AnyEvent]:
        return list(self._event_queue)

    def _enqueue_restored(self, event: Event) -> None:
        self._event_queue.append(event)

    def drain_pending(self) -> List[AnyEvent]:
        """Remove and return every accepted-but-unprocessed event.

        The events are NOT processed. Sync mirror of
        `Interpreter.drain_pending` (a plain method: nothing to await).
        """
        drained = list(self._event_queue)
        self._event_queue.clear()
        return drained

    def send_events(
        self, events: List[Union[Dict[str, Any], Event, str]]
    ) -> None:
        """Sends a list of events to the machine for immediate, synchronous processing."""
        if self.status != "running":
            logger.warning(
                "🚫 Cannot send events. Interpreter is not running."
            )
            return

        for event_or_type in events:
            event_obj = self._prepare_event_reporting(event_or_type)
            self._event_queue.append(event_obj)

        self._process_event_queue()
        self._run_held_replays()  # #125

    def _process_event_queue(self) -> None:
        """Processes all events in the queue until it is empty.

        If event processing is already underway, this method returns immediately
        to prevent re-entrant execution.
        """
        if self._is_processing:
            return

        self._is_processing = True
        # 🔁 #103: one settle budget per drain (see
        #    `_process_transient_transitions`).
        self._settle_iterations = 0
        self._settle_tripped = False
        # 🛟 Bound the macrostep. The `raise` built-in re-enters this queue, so
        #    an action that raises its own trigger event feeds itself forever.
        #    `max_iterations` previously guarded only the eventless (`always`)
        #    path, leaving this loop unbounded: `send()` never returned, with
        #    no timeout and no way to interrupt it. The same ceiling now
        #    applies to both paths.
        #
        # 🏛️ #77: measure SELF-GENERATED work, not throughput. The sync
        #    caller is blocked for the whole drain, so every event that was
        #    already in the inbox when the drain began -- or is replayed
        #    from the defer buffer -- is a user event and is never counted.
        #    Anything that ARRIVES during the drain (a `raise`, an action
        #    calling `send()` on its own interpreter, a `done.invoke` from a
        #    sync service, a due timer) was produced by the machine itself
        #    and counts against `max_iterations`. The count is per CHAIN,
        #    not per drain: it resets whenever a macrostep generates nothing
        #    (see the reset below), so N independent one-deep raises never
        #    trip it. A 5,000-event batch is processed in full; a
        #    self-feeding loop -- via `raise` OR via an external self-send --
        #    is still broken. On overflow the external
        #    budget is, by construction, already spent, so everything left in
        #    both queues is self-generated and dropping it loses nothing the
        #    caller was told was accepted.
        external_budget = len(self._event_queue)
        # 🔗 Internal events ALREADY queued when the drain opens were raised
        #    by whatever ran before it -- the initial entry in `start()`, a
        #    restored inbox -- not by this drain. Give them the same standing
        #    as a user event so the chain count starts at their FIRST
        #    descendant, which is what the async engine's `_raise_depth`
        #    does. Without this the sync engine cut a chain one link short.
        seed_internal = len(self._internal_queue)
        generated = 0
        # 🏛️ #88: `tripped` is per CHAIN, not per drain. It is cleared by
        #    the same condition that resets `generated` (a step that produced
        #    nothing), so one runaway `SPIN` cannot starve five unrelated
        #    `WORK` events queued behind it. Within a chain it stays sticky:
        #    each further self-event the runaway produces is dropped on
        #    arrival instead of earning a fresh budget.
        tripped = False
        dropped_total = 0
        limit = getattr(self.machine, "max_iterations", 1000)
        debug = logger.isEnabledFor(logging.DEBUG)  # ⚡ once per macrostep
        try:
            while self._event_queue or self._internal_queue:
                # ⏰ #50: a deadline that elapsed while THIS macrostep was
                #    busy is delivered in-loop, in due order, rather than
                #    waiting for the next external send(). Due timers land
                #    at the tail; the acceptance criterion is "not dropped
                #    and drained in the same loop", which this satisfies.
                self._pump_timers()
                # 🔁 #36: internal (self-raised) events first, in order.
                is_generated = True
                if self._internal_queue:
                    current_event = self._internal_queue.popleft()
                    if seed_internal > 0:
                        seed_internal -= 1
                        is_generated = False
                elif external_budget > 0:
                    external_budget -= 1
                    is_generated = False
                    current_event = self._event_queue.popleft()
                else:
                    current_event = self._event_queue.popleft()
                # 🏛️ #94: an ENGINE completion (`done.invoke`, `error.platform`,
                #    a due `after`) is the result of work that already
                #    finished. Dropping one strands the machine in the
                #    invoking state forever -- strictly worse than the
                #    runaway the budget prevents -- so completions are NEVER
                #    dropped (see the trip handler). They ARE counted like
                #    any other self-generated event: a rollback that re-arms
                #    an invoke whose `onDone` fails again is a genuine
                #    self-feeding cycle made entirely of completions, and the
                #    count is the only thing that breaks it. In the normal
                #    case a sync service's completion is one deep and the
                #    per-step reset below clears it immediately.
                is_completion = is_generated and is_system_event(current_event)
                if not is_generated:
                    # 🔗 #88: a USER event starts a fresh chain. Whatever a
                    #    previous runaway did, this event and everything it
                    #    generates get a clean budget -- mirrors the async
                    #    engine, whose `_raise_depth` only ever counts
                    #    internal events and is reset per macrostep.
                    generated = 0
                    tripped = False
                    # 🔁 #151: the `always`-settle budget is per MACROSTEP
                    #    (per user event), not per drain. Reset once per
                    #    drain (#103), two independent events that each
                    #    legitimately settle in 40 hops under a limit of 50
                    #    shared one allowance inside `send_events([A, B])`,
                    #    and B tripped where `send(A); send(B)` did not.
                    #    #103's terminating property is preserved: the
                    #    settle budget for the *generated* tail of a chain is
                    #    still not renewed, because only an external event
                    #    resets it.
                    self._settle_iterations = 0
                    self._settle_tripped = False
                if is_generated:
                    generated += 1
                if is_generated and (tripped or generated > limit):
                    # ✂️ The chain is over budget. Internal events drain
                    #    first, so the user's own events may still sit at the
                    #    HEAD of the inbox with self-generated ones appended
                    #    behind them: discard the self-generated tail, keep
                    #    the user's. Within this chain `tripped` stays set so
                    #    each further self-event is dropped on arrival.
                    #
                    #    Engine completions are never discarded (#94): a
                    #    completion found in the tail is re-queued ahead of
                    #    it, and a completion that IS the tripping event is
                    #    processed (falls through below) rather than
                    #    re-queued -- re-queueing would dequeue it again on
                    #    the next iteration, still tripped, forever.
                    victims: List[AnyEvent] = []
                    keep: List[AnyEvent] = []
                    # A completion is spared ONLY at the moment of the trip
                    # (`not tripped`): it is the result of real work and is
                    # delivered. Once the chain is tripped, a further
                    # completion IS the cycle (rollback -> re-arm -> done ->
                    # rollback ...) and must be dropped or the drain never
                    # ends.
                    spare = is_completion and not tripped
                    if not spare:
                        victims.append(current_event)
                    while self._internal_queue:
                        ev = self._internal_queue.popleft()
                        (keep if is_system_event(ev) else victims).append(ev)
                    tail = max(0, len(self._event_queue) - external_budget)
                    for _ in range(tail):
                        ev = self._event_queue.pop()
                        (keep if is_system_event(ev) else victims).append(ev)
                    for ev in reversed(keep):
                        self._internal_queue.appendleft(ev)
                    dropped_total += len(victims)
                    if not tripped:
                        logger.error(
                            "🛑 Exceeded %d self-generated events in a single "
                            "macrostep on '%s'. An action raises or sends the "
                            "event that triggers it. Discarding the "
                            "self-generated tail; every event the caller "
                            "queued is still processed.",
                            limit,
                            self.id,
                        )
                    # 🔔 #77 criterion 6: the break is OBSERVABLE. Each
                    #    victim fires `on_event_dropped`; the step is marked
                    #    failed so `Receipt.error` / `last_transition_ok`
                    #    carry a `RunawayChainError`.
                    for ev in victims:
                        for plugin in self._plugins:
                            plugin.on_event_dropped(self, ev, "chain_budget")
                    self.last_transition_ok = False
                    self._last_action_error = RunawayChainError(
                        self.id, limit, dropped_total
                    )
                    tripped = True
                    if not spare:
                        continue
                    # The spared completion falls through and is processed.
                    # It does NOT reset the chain: `generated` stays over
                    # budget so anything it produces is dropped on arrival.
                if debug:  # 📉 #55: hot path, DEBUG
                    logger.debug(
                        "⚙️ Processing event: '%s'", current_event.type
                    )

                for plugin in self._plugins:
                    plugin.on_event_received(self, current_event)

                # ⚡ The configuration snapshot exists only to decide whether
                #    deferred events earned a replay; skip both frozensets
                #    when nothing is deferred (the common case).
                before = (
                    frozenset(self._active_state_nodes)
                    if self._deferred_events
                    else None
                )
                queued_before = len(self._internal_queue) + len(
                    self._event_queue
                )
                self._drive(self._process_event(current_event))
                self._process_transient_transitions()
                # 🔗 Chain accounting -- parity with the async engine, which
                #    resets `_raise_depth` when a macrostep raised nothing
                #    (`interpreter.py`). A step that added NOTHING to either
                #    queue ended the self-feeding chain, so the next user
                #    event starts with a fresh budget. Without this, 3,000
                #    independent one-deep raises in one `send_events()` batch
                #    were truncated to 1,000 on this engine only -- no loop
                #    anywhere -- while `send()` one at a time processed all of
                #    them. `tripped` is deliberately NOT cleared: once a drain
                #    has overflowed it stays in drop-on-arrival mode until the
                #    caller returns, so a machine that keeps regenerating
                #    cannot earn a fresh 1,000 per user event.
                # 🔗 A step that produced nothing ends the current chain
                #    (parity with the async `_raise_depth` reset). `tripped`
                #    is cleared here too: the runaway is over once it stops
                #    regenerating.
                #
                # 🛡️ #144: "produced nothing" is not enough on its own. A
                #    conservative cycle -- a step that dequeues one event and
                #    enqueues one (a nested invoke whose `onDone` re-enters
                #    the ancestor and re-arms both invokes: one step grows
                #    the queue by one, the next shrinks it by one) -- made
                #    every second step look like the end of a chain, so the
                #    budget reset on every lap and `start()` never returned,
                #    regardless of `maxIterations`. A chain has genuinely
                #    ended only when the step generated nothing AND no
                #    self-generated work remains queued: the internal queue
                #    is empty (the inbox may still hold the caller's own
                #    events, which are not part of any chain).
                if (
                    len(self._internal_queue) + len(self._event_queue)
                    <= queued_before
                    and not self._internal_queue
                ):
                    generated = 0
                    tripped = False

                # 📨 Replay deferred events at the HEAD of the queue, ahead of
                #    live traffic and in original order (LC-18). `extendleft`
                #    reverses, so feed it reversed to preserve order. Events
                #    still unhandled in the new state come straight back
                #    through `_handle_unhandled_event` and are re-deferred.
                if before is not None and before != frozenset(
                    self._active_state_nodes
                ):
                    # 📨 #125: do NOT re-queue into this drain. Park the
                    #    replays; `_run_held_replays` (called by `send` /
                    #    `send_events` / `tick` after the receipt is built)
                    #    runs them as their own macrostep.
                    self._held_replays.extend(self._take_deferred_for_replay())
        finally:
            self._is_processing = False
            if debug:
                logger.debug(
                    "🎉 Event processing cycle completed. Queue empty."
                )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (Private)
    # -------------------------------------------------------------------------

    def _process_transient_transitions(self) -> None:
        """Continuously processes event-less ("always") transitions until stable.

        These transitions are checked after any state change. They allow for
        conditional, immediate jumps without an external event. The loop

        continues until no more "always" transitions are available and the
        state configuration is stable.
        """
        if not self.machine.has_always_transitions:
            return  # ⚡ nothing to settle; see MachineNode.has_always_transitions
        logger.debug("🔍 Checking for transient ('always') transitions...")
        # 🛟 Bound the microstep loop. A pair of `always` transitions that
        #    target each other spins forever; XState added the same guard in
        #    v5.31.0. `max_iterations` is configurable on the machine.
        # 🏛️ #103: the counter lives on the INSTANCE and is reset by
        #    `_process_event_queue` at the start of each drain, not here.
        #    A settle pass that re-arms an `invoke` whose sync completion
        #    lands on the queue returns to the drain, which calls back in;
        #    a per-call counter restarted at 0 every time, so the budget
        #    tripped repeatedly and terminated never -- `start()` hung.
        limit = getattr(self.machine, "max_iterations", 1000)
        while True:
            self._settle_iterations += 1
            if self._settle_iterations > limit:
                if not self._settle_tripped:
                    logger.error(
                        "🔁 Exceeded %d microsteps while settling transient "
                        "transitions in '%s'. Aborting to avoid an infinite "
                        "loop; check for mutually-targeting 'always' "
                        "transitions or an 'always' into an invoking state.",
                        limit,
                        self.id,
                    )
                # 🔔 #112: the trip is OBSERVABLE, like the chain budget.
                self._settle_tripped = True
                self.last_transition_ok = False
                self._last_action_error = RunawayChainError(self.id, limit, 0)
                # 🧹 #112: a half-applied microstep can leave a leaf whose
                #    ancestors are inactive. Re-derive the configuration
                #    from its leaves so the live machine matches what a
                #    restore would rebuild.
                self._repair_configuration()
                break
            # 👻 Use a dummy event for guard evaluation in "always" transitions.
            transient_event = Event(type="")  # Empty type signifies "always".

            # 🎯 Find transient transitions via the memoised selection path,
            #    so a guard on a shared ancestor is evaluated once rather than
            #    once per active leaf.
            selected = self._select_transitions(transient_event)

            # ⚡ An event-less transition is one with an empty event string ("").
            if selected and any(t.event == "" for t in selected):
                logger.info(
                    "🚀 Processing transient transition(s) in '%s'", self.id
                )
                # 🔄 Directly process the *found* transition, which is more efficient.
                self._drive(self._process_event(transient_event))
            else:
                # ✅ No more transient transitions found. The state is stable.
                logger.debug(
                    "🧘 State is stable. No more transient transitions."
                )
                break

    # -------------------------------------------------------------------------
    # ➡️⬅️ State Lifecycle Hooks (Private)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # ⚡ Action & Service Execution (Private Overrides)
    # -------------------------------------------------------------------------

    def _run_user_action(  # type: ignore[override]
        self,
        impl: Callable[..., Any],
        action_def: ActionDefinition,
        event: Any,
    ) -> "_Done[None]":
        """Leaf: call one action inline; refuse every async shape (LC-58)."""
        if self._is_async_callable(impl):
            raise NotSupportedError(
                f"Async action '{action_def.type}' not supported by "
                f"SyncInterpreter."
            )
        impl(self, self.context, event, action_def)
        return _Done(None)

    def _deliver_completion(self, event: AnyEvent) -> None:
        """Queue a service completion produced INSIDE the current macrostep.

        🏛️ #116: a plain-sync service finishes while the state that invoked
        it is still being entered. Its `done.invoke` is a consequence of
        THIS step and must run before any external event already waiting
        in the inbox -- otherwise `send_events(["GO", "X"])` delivered `X`
        before the completion while `send("GO"); send("X")` (and the async
        engine) delivered the completion first. Route it through the
        internal queue, which the drain empties before touching the inbox
        (#36 ordering). Outside a drain -- a completion arriving from a
        non-blocking actor thread -- `send()` is the correct entry.
        """
        if self._is_processing:
            self._internal_queue.append(event)
        else:
            self.send(event)

    def _dispatch_internal(  # type: ignore[override]
        self, event: Any
    ) -> "_Done[None]":
        # Onto our own queue; the macrostep loop already running will take
        # it (a `done.state.*` is raised from INSIDE `_enter_states`).
        self._event_queue.append(event)
        return _Done(None)

    def _stop_actor_leaf(  # type: ignore[override]
        self, actor: Any
    ) -> "_Done[None]":
        actor.stop()
        return _Done(None)

    def _deliver(  # type: ignore[override]
        self,
        actor: Any,
        target_event: AnyEvent,
        delay: Optional[float],
        send_id: Optional[str],
    ) -> "_Done[None]":
        self._deliver_sync(actor, target_event, delay, send_id)
        return _Done(None)

    def _deliver_sync(
        self,
        actor: Any,
        target_event: AnyEvent,
        delay: Optional[float],
        send_id: Optional[str],
    ) -> None:
        """Send an event to an actor, honouring an optional delay.

        A delayed send is a clock deadline (#50), not a thread; it is
        delivered by the next pump on the caller's thread.

        Args:
            actor (Any): The recipient interpreter.
            target_event (Event): The event to deliver.
            delay (Optional[float]): Delay in milliseconds, or `None`.
            send_id (Optional[str]): Id allowing later cancellation.
        """
        if not delay:
            if actor is self and self._is_processing:
                # 🔁 #36: a `raise` to OURSELVES mid-macrostep is INTERNAL:
                #    it must run before any external event already queued.
                #    It goes to `_internal_queue`, which the macrostep loop
                #    drains ahead of `_event_queue`; a chain of raises stays
                #    FIFO among themselves -- see `_process_event_queue`.
                self._internal_queue.append(target_event)
                return
            actor.send(target_event)
            return

        key = str(send_id) if send_id else None
        # 🧷 Declared before `_fire` so the closure's reference resolves for
        #    the type checker; bound below once the timer handle exists.
        handle: Any = None

        def _cancel() -> None:
            self.clock.clear_timeout(handle)

        def _fire() -> None:
            if key is not None and self._scheduled_sends.get(key) is _cancel:
                self._scheduled_sends.pop(key, None)
            if self.status != "running":
                return
            if actor is self:
                # To OURSELVES: straight onto our queue; the pump that fired
                # us is about to drain it on this thread.
                self._event_queue.append(target_event)
            else:
                try:
                    actor.send(target_event)
                except Exception:  # pragma: no cover - defensive
                    logger.exception(
                        "🔥 Delayed send of '%s' failed.", target_event.type
                    )

        handle = self._set_timeout(_fire, delay / 1000.0, owner=self.id)
        self._timer_handles.setdefault(self.id, []).append(handle)

        # 🔁 Reusing a send id supersedes the earlier send. Without this the
        #    first timer is orphaned: the registry entry is overwritten, so
        #    `cancel(id)` can no longer reach it and it fires anyway.
        if key is not None:
            previous = self._scheduled_sends.get(key)
            if previous is not None:
                previous()
            self._scheduled_sends[key] = _cancel

    def _spawn_actor(  # type: ignore[override]
        self,
        action_def: ActionDefinition,
        event: Event,
        on_complete: Optional[str] = None,
    ) -> "_Done[None]":
        """Leaf: spawn inline, hand back a finished awaitable (#60)."""
        self._spawn_actor_sync(action_def, event, on_complete)
        return _Done(None)

    def _spawn_actor_sync(
        self,
        action_def: ActionDefinition,
        event: Event,
        on_complete: Optional[str] = None,
    ) -> None:
        """Spawns a child state machine actor in blocking or non-blocking mode.

        Args:
            action_def: The action definition for spawning the actor.
            event: The event that triggered the spawn action.
            on_complete: When set, the invoke id to report completion under.
                Reaching a top-level final state queues
                `done.invoke.<id>` so an `invoke` of a child MACHINE fires
                `onDone`. Spawning alone never signalled completion, so a
                parent waited forever even when the child finished
                immediately.

        Raises:
            ActorSpawningError: If the specified service is not a valid
                `MachineNode` or a factory that returns one.
        """
        # 🕵️ Determine mode (blocking vs. non-blocking) and service key
        blocking = action_def.type.startswith(SPAWN_BLOCKING_PREFIX)
        key = spawn_service_key(action_def.type)
        logger.info("🎭 Spawning actor '%s' (Blocking: %s)", key, blocking)

        # 🏭 Get the actor's machine definition from the services registry
        source = self.machine.logic.services.get(key)
        actor_machine = (
            source
            if isinstance(source, MachineNode)
            else (
                source(self, self.context, event) if callable(source) else None
            )
        )
        if not isinstance(actor_machine, MachineNode):
            raise ActorSpawningError(
                f"Cannot spawn '{key}'. Service not a MachineNode or factory."
            )

        # 🆔 Create and register the child interpreter (actor). An explicit
        #    `id` in params wins so `stop_child("worker")` can address it.
        spawn_params = action_def.params or {}
        explicit_id = spawn_params.get("id")
        actor_id = (
            f"{self.id}:{explicit_id}"
            if explicit_id
            else f"{self.id}:{key}:{uuid.uuid4()}"
        )
        # 📥 Input goes in at CONSTRUCTION so a child `context` factory
        #    receives `{input}` (#42); `_build_initial_context` also seeds
        #    declared keys and exposes `context["input"]`.
        # 🕰️ #60: propagate `clock` and `strict` to the child so it shares
        #    the parent's timeline (SimulatedClock-driven `after` timers
        #    fire deterministically instead of a fresh RealClock ticking
        #    real wall-clock seconds) and its strict-mode setting (an
        #    undeclared event sent to the child must raise, not silently
        #    fall back to `machine.strict`).
        child = SyncInterpreter(
            actor_machine,
            input=spawn_params.get("input"),
            clock=self.clock,
            strict=self.strict,
        )
        child.parent = self
        child.id = actor_id
        # 🎯 #156: an `invoke`d child (spawned with `on_complete`) is known
        #    to the parent by its invoke id; record it for `escalate`.
        child._invoked_as = on_complete
        # 🌐 Register under a systemId so siblings can address it.
        self._register_in_system(spawn_params.get("systemId"), child)
        self._actors[actor_id] = child
        self._actor_sources[actor_id] = key

        # 🧹 Review F3: a child that finishes on its own leaves the map.
        # 🩹 mypy: an explicit statement body (rather than a lambda whose
        #    expression value is `dict.pop`'s return) keeps this closure's
        #    inferred type as `Callable[[str], None]`, matching
        #    `_terminal_listeners`, instead of leaking the popped actor's
        #    type into the lambda's return annotation.
        def _on_child_terminal(_s: str, aid: str = actor_id) -> None:
            self._actors.pop(aid, None)

        child._terminal_listeners.append(_on_child_terminal)

        # --- Blocking Execution Path ---
        if blocking:
            child.start()
            # ⏸️ #41: "blocking" means the child runs to COMPLETION before the
            #    parent's next action -- on both engines. `start()` alone only
            #    covers a child whose work is synchronous entry actions; one
            #    driven by `after` timers (background threads here) is still
            #    running when `start()` returns. Wait on its terminal signal,
            #    bounded by `spawnBlockingTimeout` (ms) like the async engine.
            self._wait_for_child_terminal(child)
            if on_complete is not None:
                self._queue_actor_done(child, on_complete)
            return

        # --- Non-Blocking Execution Path (via a background thread) ---
        # 🚀 Start the child HERE, on the spawning thread, before the pump
        #    thread exists. Starting it on the runner made "spawned" and
        #    "started" two different instants: a parent that snapshotted,
        #    `sendTo`'d or `stop_child`'d right after the spawn action could
        #    observe a registered child whose entry actions (and its own
        #    grandchildren) did not exist yet -- a rare, load-dependent
        #    flake. The async engine starts a spawned child in the same loop
        #    turn; this restores that parity. `start()` on a sync child is
        #    bounded work (entry actions; `after` timers arm, they do not
        #    block), so the parent's own step is not held up.
        child.start()

        def _runner() -> None:
            """Pumps the already-started child until it ends or is stopped."""
            try:
                # 🔄 Keep the thread alive while the child runs. This thread
                #    is the child's pump: with no timer threads (#50), the
                #    child's `after` deadlines fire only when someone calls
                #    `tick()`, and for a non-blocking actor that someone is
                #    this runner -- so every action the child runs executes
                #    on THIS thread, never on a timer thread.
                while child.status == "running":
                    # 🏁 Exit loop if the child reaches a top-level final state.
                    if any(
                        s.is_final and s.parent == child.machine
                        for s in child._active_state_nodes
                    ):
                        break
                    child.tick()
                    time.sleep(0.01)  # 🤏 Yield to prevent busy-waiting.
            finally:
                # 🧹 Ensure cleanup happens whether the child finishes or is stopped.
                if on_complete is not None:
                    self._queue_actor_done(child, on_complete)
                child.stop()
                self._actors.pop(actor_id, None)
                logger.info("🧹 Actor thread for '%s' cleaned up.", actor_id)

        # 🚀 Start the thread. #183/#184: the child records the thread its
        #    steps run on, so a parent snapshot that catches it mid-step
        #    knows a bounded wait CAN let it settle.
        def _runner_recording() -> None:
            child._pump_thread_ident = threading.get_ident()
            _runner()

        threading.Thread(
            target=_runner_recording, daemon=True, name=f"actor-{actor_id}"
        ).start()

    def _wait_for_child_terminal(self, child: "SyncInterpreter") -> None:
        """Block until *child* is done/error, or `spawnBlockingTimeout` lapses.

        Uses the shared terminal-listener hook (#43) rather than polling
        `status`, so completion is observed the instant it happens.
        """
        if child.status in ("done", "error", "stopped"):
            return
        # 🧭 A child with nothing in flight -- no `after` timers and no
        #    actors of its own -- has already done everything `start()`
        #    can make it do; it is idle, not "still working". Waiting on it
        #    would block forever, and 0.7.x machines relied on this case
        #    returning immediately. Only wait when the child can still
        #    progress on its own.
        if not child._timer_handles and not child._actors:
            return
        finished = threading.Event()
        child._terminal_listeners.append(lambda _status: finished.set())
        timeout_ms = self.machine.spawn_blocking_timeout_ms
        if timeout_ms is None:
            timeout_ms = DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS  # review F2
        if not finished.wait(timeout_ms / 1000.0):
            logger.warning(
                "⏱️ Blocking spawn of '%s' did not finish within %s ms; "
                "continuing without it.",
                child.id,
                timeout_ms,
            )

    def _queue_actor_done(
        self, child: "SyncInterpreter", invoke_id: str
    ) -> None:
        """Queues `done.invoke.<id>` for a completed child machine.

        Only fires when the child actually reached a top-level final state —
        a child that was stopped early (because the parent left the invoking
        state) must NOT report success.

        Args:
            child: The spawned child interpreter.
            invoke_id: The `invoke` id to report completion under.
        """
        # 💥 #99: a child that ENDED IN ERROR must satisfy `onError`, not
        #    fall through as "did not reach final". Same shape as the async
        #    engine's `_deliver_invoked_completion`; with no handler the
        #    parent fails like it does for a failing callable service.
        # 💥 `error`, or `stopped` BY a policy failure (#145) -- see the
        #    async engine's `_deliver_invoked_completion`.
        if child.status == "error" or (
            child.status == "stopped" and child.error is not None
        ):
            failure = child.error or RuntimeError(
                f"Invoked machine '{child.id}' failed."
            )
            logger.warning(
                "💥 Invoked machine '%s' ended in error; firing onError.",
                child.id,
            )
            error_event = ErrorEvent(
                type=f"error.platform.{invoke_id}",
                error=failure,
                src=invoke_id,
            )
            handled = self._has_error_handler_for_id(invoke_id)
            self.send(error_event)
            if not handled:
                self._fail(failure)
            return
        reached_final = any(
            node.is_final and node.parent is child.machine
            for node in child._active_state_nodes
        )
        if not reached_final:
            logger.debug(
                "🚫 Child '%s' did not reach a final state; no onDone.",
                child.id,
            )
            return

        # 📤 #109: `onDone` carries the child's declared OUTPUT, not its
        #    private context (same rule as the async engine).
        done_event = DoneEvent(
            type=f"done.invoke.{invoke_id}",
            data=child.output if child.output is not None else child.context,
            src=invoke_id,
        )
        logger.info("🏁 Child actor '%s' completed; firing onDone.", child.id)
        self.send(done_event)

    def _cancel_state_tasks(  # type: ignore[override]
        self, state: StateNode
    ) -> "_Done[None]":
        """Leaf: cancel a state's timers; finished awaitable (#60)."""
        # 🧹 Fire-and-forget: helper returns None, no value to thread
        # through `_Done` (#60 mypy func-returns-value cleanup).
        self._cancel_state_tasks_sync(state)
        return _Done(None)

    def _cancel_state_tasks_sync(self, state: StateNode) -> None:
        """Cancel every clock timer (`after`, delayed send) a state owns."""
        handles = self._timer_handles.pop(state.id, [])
        for handle in handles:
            self.clock.clear_timeout(handle)
        if handles:
            logger.debug(
                "🧹 Cancelled %d timer(s) for state '%s'.",
                len(handles),
                state.id,
            )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Schedule a delayed `AfterEvent` on the interpreter's clock.

        🏛️ Architecture decision (#50): before 0.8.0 this started a daemon
        OS THREAD per timer which called `send()` when the delay elapsed --
        so actions ran on timer threads and mutated `context` under no lock
        while the class advertised itself as single-threaded. Now the
        deadline is a record in `self.clock`; `_pump_timers()` (run at the
        top of every `send()` and by `tick()`) fires due timers on the
        CALLER's thread by appending the event to the queue, where the
        ordinary macrostep loop processes it in order. Exiting the owning
        state cancels the handle. A `SimulatedClock` fires them from
        `increment()` (#49).

        Args:
            delay_sec (float): Delay before the event is due.
            event (AfterEvent): The event to deliver.
            owner_id (str): Owning state id; used for cancellation.
        """
        logger.info(
            "⏰ Scheduling 'after' (%s) in %.2fs for state '%s'",
            event.type,
            delay_sec,
            owner_id,
        )

        def _fire() -> None:
            # Fire only if still running AND the owner is still active; a
            # late pump after the state was left must not resurrect it.
            if self.status != "running" or not any(
                s.id == owner_id for s in self._active_state_nodes
            ):
                return
            self._event_queue.append(event._replace(fired_at=self.clock.now()))

        handle = self._set_timeout(_fire, delay_sec, owner=owner_id)
        self._timer_handles.setdefault(owner_id, []).append(handle)

    def _invocation_is_live(
        self, state: StateNode, invocation: InvokeDefinition
    ) -> bool:
        # Sync services complete inline, so the only long-lived invoke is a
        # child ACTOR; a callable service is never "live" between sends.
        if f"{self.id}:{invocation.id}" in self._actors:
            return True
        return any(
            src == invocation.src for src in self._actor_sources.values()
        )

    def _pump_timers(self) -> int:
        """Fire every due clock deadline onto the queue (the timer pump).

        Called at the top of `send()` and by `tick()`. Returns how many
        fired. Does NOT process the queue; the caller does.
        """
        return self.clock.pump()

    def _step_thread_ident(self) -> Optional[int]:
        """A non-blocking actor steps on its pump thread (#183/#184)."""
        return self._pump_thread_ident

    def _attach_clock(self) -> None:
        """Register `tick` as this interpreter's settler on a `SimulatedClock`.

        Idempotent (the clock de-duplicates by identity). Every path that
        leaves `start()` with the machine running must call this -- the
        fresh start and BOTH restore branches (#154) -- or a virtual-time
        `increment()` fires deadlines that nothing drains.
        """
        if isinstance(self.clock, SimulatedClock):
            self.clock._attach(self.tick)

    def tick(self) -> None:
        """Deliver every `after` / delayed send whose deadline is DUE NOW.

        Contract (#122): one call drains every deadline that has elapsed at
        the current clock reading, including a chain of zero-delay
        deadlines armed by the transitions it takes. It does NOT advance
        time: a ladder of real delays (``after: 50`` -> ``after: 50`` ->
        ...) needs one `tick()` per rung, each after that rung's delay has
        actually passed on a `RealClock` -- no synchronous call can
        honestly make wall time pass. For deterministic chains use a
        `SimulatedClock` and `increment()`, which settles every rung that
        becomes due.

        🏛️ #50: with no timer threads, a machine that receives no events
        needs a caller to advance it. `tick()` is that pump: it fires due
        deadlines onto the queue and processes them, all on the calling
        thread. It is also the seam a `SimulatedClock` drives.
        """
        if self.status != "running" or self._is_processing:
            return
        # 🔁 #122: a deadline delivered by this tick may take a transition
        #    into a state whose OWN deadline is already due -- or is armed
        #    NOW and due by the time this call returns. `tick()` means
        #    "process everything that is due"; the caller (a poll loop, a
        #    test) reads the state right after it returns, so we drain
        #    until a pump delivers nothing. The wall clock keeps moving
        #    during the drain, so a 50 ms ladder of three rungs that is
        #    already 250 ms late walks all three in one call, exactly as
        #    the async engine's settle does. Bounded by `maxIterations`
        #    so a genuine zero-delay cycle cannot spin.
        limit = getattr(self.machine, "max_iterations", 1000)
        for _ in range(limit):
            fired = self._pump_timers()
            if self._event_queue:
                self._process_event_queue()
                self._run_held_replays()  # #125
                self._process_transient_transitions()
                continue  # the step may have armed an already-due timer
            if not fired:
                break

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Union[Callable[..., Any], "MachineNode[Any]"],
        owner_id: str,
    ) -> None:
        """Handles invoked services, supporting only synchronous callables.

        Synchronous services are executed immediately, blocking the interpreter.
        The service's return value is sent as a `done.invoke.*` event. If it
        raises an exception, an `error.platform.*` event is sent instead.

        Args:
            invocation: The definition of the invoked service.
            service: The callable representing the service logic.
            owner_id: The ID of the state node owns this invocation.

        Raises:
            NotSupportedError: If the provided service is an `async def` function.
        """
        # 🤖 A `MachineNode` used as `src` means "run this machine as a child
        #    actor", not "call this object". Without this branch it fell
        #    through to `service(...)` and raised
        #    `TypeError: 'MachineNode' object is not callable`.
        if isinstance(service, MachineNode):
            logger.info(
                "🤖 Invoking machine '%s' as a child actor (id: '%s').",
                invocation.src,
                invocation.id,
            )
            # 🏛️ #40: only a DECLARED id becomes the actor address; the
            #    parser's default (the hosting state's id) is shared by every
            #    anonymous invoke in that state. `systemId` is threaded
            #    through so the child is addressable system-wide.
            params: Dict[str, Any] = {}
            if invocation.id_is_explicit:
                params["id"] = invocation.id
            if invocation.system_id:
                params["systemId"] = invocation.system_id
            # 📥 #42: resolve `input` against the parent's live context so
            #    the child machine is parameterised exactly as in XState. A
            #    raising resolver is a child FAILURE -> `error.platform`,
            #    exactly as on the async engine (review F10).
            try:
                child_input = invocation.resolve_input(self.context, None)
            except Exception as exc:  # noqa: BLE001 -- user code
                self.send(
                    ErrorEvent(
                        type=f"error.platform.{invocation.id}",
                        error=exc,
                        src=invocation.id,
                    )
                )
                return
            if child_input is not None:
                params["input"] = child_input
            self._spawn_actor_sync(
                ActionDefinition(
                    {"type": f"spawn_{invocation.src}", "params": params}
                ),
                Event(type=f"invoke.{invocation.id}"),
                on_complete=invocation.id,
            )
            return

        # 🧐 Validate that the service is not an async function.
        if self._is_async_callable(service):
            logger.error(
                "🚫 Service '%s' is async and not supported by SyncInterpreter.",
                invocation.src,
            )
            raise NotSupportedError(
                f"Service '{invocation.src}' is async and not supported."
            )

        logger.info(
            "📞 Invoking sync service '%s' (id: '%s')...",
            invocation.src,
            invocation.id,
        )
        for plugin in self._plugins:
            plugin.on_service_start(self, invocation)

        try:
            # 🎁 Prepare a synthetic event for the service.
            invoke_event = Event(
                f"invoke.{invocation.id}",
                {"input": invocation.resolve_input(self.context, None) or {}},
            )
            # 🚀 Execute the synchronous service.
            result = service(self, self.context, invoke_event)
            # ✅ On success, immediately queue a 'done' event with the result.
            done_event = DoneEvent(
                f"done.invoke.{invocation.id}", data=result, src=invocation.id
            )
            self._deliver_completion(done_event)
            logger.info(
                "✅ Sync service '%s' completed successfully.", invocation.src
            )
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, result)

        except Exception as e:
            # 💥 On failure, immediately queue an 'error' event with the exception.
            logger.error(
                "💔 Sync service '%s' failed: %s",
                invocation.src,
                e,
                exc_info=True,
            )
            error_event = ErrorEvent(
                f"error.platform.{invocation.id}", error=e, src=invocation.id
            )
            # 🚨 Unhandled service failures must be observable, not just
            #    logged. See BaseInterpreter._fail.
            handled = self._has_error_handler(invocation)
            self._deliver_completion(error_event)
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
            if not handled:
                self._fail(e)

    # -------------------------------------------------------------------------
    # 🛠️ Helper & Utility Methods (Private)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 🛠️ Static Helper Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_async_callable(callable_obj: Callable[..., Any]) -> bool:
        """Checks if a callable is an async function (`async def`).

        This helper is used to prevent async logic from being run by the
        synchronous interpreter, which would cause runtime errors.

        Args:
            callable_obj: The function or method to check.

        Returns:
            True if the callable is an awaitable coroutine, False otherwise.
        """
        # 🏛️ #60 / LC-58: the old check read `__code__.co_flags` directly,
        #    which sees only a bare `async def`. `functools.partial(async_fn)`,
        #    an object with `async def __call__`, and an async generator all
        #    slipped through and were CALLED -- the coroutine object was then
        #    silently discarded, so the action never ran and nobody was told.
        #    Unwrap partials and decorators, then check every async shape.
        fn: Any = callable_obj
        while isinstance(fn, functools.partial):
            fn = fn.func
        fn = inspect.unwrap(fn)
        if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
            return True
        call = getattr(type(fn), "__call__", None)
        if call is not None and not inspect.isfunction(fn):
            call = inspect.unwrap(call)
            if inspect.iscoroutinefunction(call) or inspect.isasyncgenfunction(
                call
            ):
                return True
        return False
