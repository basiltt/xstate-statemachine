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
import logging
import threading
import time
import uuid
from collections import deque
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    overload,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .base_interpreter import BaseInterpreter, _RollbackRequested
from .clock import Clock, SimulatedClock
from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
    NotSupportedError,
    StateNotFoundError,
)
from .actions import (
    ESCALATE,
    FORWARD_TO,
    RAISE,
    SEND_PARENT,
    SEND_TO,
    SPAWN_CHILD,
    STOP_CHILD,
    is_builtin,
    resolve_builtin,
)
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
    TransitionDefinition,
    DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS,
    SPAWN_BLOCKING_PREFIX,
    spawn_service_key,
)
from .resolver import resolve_target_state

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ⛓️ SyncInterpreter Class Definition
# -----------------------------------------------------------------------------
class SyncInterpreter(BaseInterpreter[TContext, TEvent]):
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
        _event_queue (Deque[Union[Event, AfterEvent, DoneEvent]]): A queue to
            manage the event processing sequence in a first-in, first-out (FIFO) manner.
        _is_processing (bool): A flag to prevent re-entrant event processing,
            ensuring atomicity of a single `send` call's execution loop.
        _timer_handles (Dict[str, List[Any]]): Clock handles for `after` timers
            and delayed sends, keyed by owning state id.
    """

    # -------------------------------------------------------------------------
    # 🧙 Magic Methods & Initialization
    # -------------------------------------------------------------------------

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        input: Optional[Any] = None,
        clock: Optional[Clock] = None,
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
        )
        #: ⏱️ Live clock handles per owning state id, so exiting a state
        #: cancels its timers on any Clock (#49/#50).
        self._timer_handles: Dict[str, List[Any]] = {}
        logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")

        # ⚙️ Initialize synchronous-specific attributes
        self._event_queue: Deque[Union[Event, DoneEvent, AfterEvent]] = deque()
        self._is_processing: bool = False
        # 🏛️ #50: `_after_threads` / `_after_events` / `_pending_send_cancels`
        #    are gone. Timers no longer own threads; see `_after_timer`.

        logger.info("✅ Synchronous Interpreter '%s' initialized. 🎉", self.id)

    # -------------------------------------------------------------------------
    # 🌐 Public API
    # -------------------------------------------------------------------------

    def start(self) -> "SyncInterpreter":
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
        if self.status == "running" and self._event_queue:
            # ♻️ Restored from a snapshot WITH a persisted inbox (review F8):
            #    `from_snapshot` sets status "running" and re-enqueues the
            #    events, so the plain "already running" early-return below
            #    would leave them sitting until an unrelated send() happened
            #    to flush them, interleaved with new work. Replay them now,
            #    in order -- the async engine's run loop does the same the
            #    moment it starts.
            logger.info("♻️ Resuming restored interpreter '%s'...", self.id)
            self._process_event_queue()
            self._process_transient_transitions()
            return self
        if self.status != "uninitialized":
            logger.info(
                "🚧 Interpreter '%s' already running. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting sync interpreter '%s'...", self.id)
        self.status = "running"
        # 🧪 A SimulatedClock drives us through `tick()` after each increment
        #    so `clock.increment(ms)` leaves the machine settled (#49).
        if isinstance(self.clock, SimulatedClock):
            self.clock._attach(self.tick)

        # ✅ Define a pseudo-transition for the initial state entry
        initial_transition = TransitionDefinition(
            event="___xstate_statemachine_init___",
            config={},
            source=self.machine,
        )

        # 🔌 Notify plugins about the interpreter start
        for plugin in self._plugins:
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
            self._enter_states([self.machine])
        finally:
            self._is_processing = False
        # 📬 Drain anything an entry action raised during that descent.
        self._process_event_queue()
        # 🔄 Process any immediate "always" transitions upon startup.
        self._process_transient_transitions()

        # Capture the post-transition state set after initialization
        post_states = set(self._active_state_nodes)

        # 🔌 Notify plugins about the initial transition with accurate state info
        for plugin in self._plugins:
            plugin.on_transition(
                self, pre_states, post_states, initial_transition
            )

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

    @overload
    def send(self, event_type: str, **payload: Any) -> None: ...  # noqa: E704

    @overload
    def send(  # noqa: PyMethodOverriding
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None:  # noqa
        ...

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> None:
        """Sends an event to the machine for immediate, synchronous processing."""
        if self.status != "running":
            logger.warning("🚫 Cannot send event. Interpreter is not running.")
            return

        event_obj = self._prepare_event(event_or_type, **payload)
        # ⏰ #50: deliver every deadline that has elapsed BEFORE this event,
        #    on this thread, in due order -- the pump.
        self._pump_timers()
        self._event_queue.append(event_obj)
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

        # 4️⃣ Drop our own registry entry so the root does not pin us.
        self._unregister_from_system()

    # -------------------------------------------------------------------------
    # 📬 Inbox (#47)
    # -------------------------------------------------------------------------
    def _snapshot_pending_events(
        self,
    ) -> List[Union[Event, DoneEvent, AfterEvent]]:
        return list(self._event_queue)

    def _enqueue_restored(self, event: Event) -> None:
        self._event_queue.append(event)

    def drain_pending(self) -> List[Union[Event, DoneEvent, AfterEvent]]:
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
            event_obj = self._prepare_event(event_or_type)
            self._event_queue.append(event_obj)

        self._process_event_queue()

    def _process_event_queue(self) -> None:
        """Processes all events in the queue until it is empty.

        If event processing is already underway, this method returns immediately
        to prevent re-entrant execution.
        """
        if self._is_processing:
            return

        self._is_processing = True
        # 🛟 Bound the macrostep. The `raise` built-in re-enters this queue, so
        #    an action that raises its own trigger event feeds itself forever.
        #    `max_iterations` previously guarded only the eventless (`always`)
        #    path, leaving this loop unbounded: `send()` never returned, with
        #    no timeout and no way to interrupt it. The same ceiling now
        #    applies to both paths.
        processed = 0
        limit = getattr(self.machine, "max_iterations", 1000)
        # 📨 Replayed deferred events are NOT new work the machine generated
        #    for itself; they are user events that already waited their turn.
        #    Counting them against the runaway-`raise` budget let a full
        #    `DEFER_MAX` replay exhaust it and `clear()` live events behind
        #    it -- data loss the async engine did not have (#28 review).
        replay_credit = 0
        try:
            while self._event_queue:
                if replay_credit:
                    replay_credit -= 1
                else:
                    processed += 1
                if processed > limit:
                    logger.error(
                        "🛑 Exceeded %d queued events in a single macrostep on "
                        "'%s'. This usually means an action raises the event "
                        "that triggers it. Discarding %d pending event(s).",
                        limit,
                        self.id,
                        len(self._event_queue),
                    )
                    self._event_queue.clear()
                    break

                # ⏰ #50: a deadline that elapsed while THIS macrostep was
                #    busy is delivered in-loop, in due order, rather than
                #    waiting for the next external send(). Due timers land
                #    at the tail; the acceptance criterion is "not dropped
                #    and drained in the same loop", which this satisfies.
                self._pump_timers()
                current_event = self._event_queue.popleft()
                logger.debug(
                    "⚙️ Processing event: '%s'", current_event.type
                )  # 📉 #55: hot path, DEBUG

                for plugin in self._plugins:
                    plugin.on_event_received(self, current_event)

                before = frozenset(self._active_state_nodes)
                self._process_event(current_event)
                self._process_transient_transitions()

                # 📨 Replay deferred events at the HEAD of the queue, ahead of
                #    live traffic and in original order (LC-18). `extendleft`
                #    reverses, so feed it reversed to preserve order. Events
                #    still unhandled in the new state come straight back
                #    through `_handle_unhandled_event` and are re-deferred.
                if before != frozenset(self._active_state_nodes):
                    held = self._take_deferred_for_replay()
                    if held:
                        self._event_queue.extendleft(reversed(held))
                        replay_credit += len(held)
        finally:
            self._is_processing = False
            logger.debug("🎉 Event processing cycle completed. Queue empty.")

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (Private)
    # -------------------------------------------------------------------------

    def _process_event(
        self, event: Union[Event, DoneEvent, AfterEvent]
    ) -> None:
        """Finds and executes the optimal transition set for a given event.

        Mirrors the asynchronous `BaseInterpreter._process_event`: one
        transition is selected per orthogonal region and each is executed in
        turn.

        Args:
            event: The event object to process.
        """
        # 1. Select every transition this event triggers (one per region).
        transitions = self._select_transitions(event)
        if not transitions:
            self._handle_unhandled_event(event)
            return

        # 2. Execute each in turn, skipping any invalidated by an earlier one.
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
            self._execute_transition_sync(transition, event)

    def _execute_transition_sync(
        self,
        transition: TransitionDefinition,
        event: Union[Event, DoneEvent, AfterEvent],
    ) -> None:
        """Executes one selected transition synchronously.

        Args:
            transition: The transition to execute.
            event: The event that triggered this transition.
        """
        # 1. A "targetless" transition only executes actions without changing state.
        if not transition.target_str:
            logger.debug("🔄 Executing internal transition actions.")
            self._execute_internal_transition(transition, event)
            return

        # 2. Resolve the target state node.
        target_state = self._resolve_target_state_robustly(transition)

        # 3. A self-transition without `reenter: True` is also internal.
        if target_state == transition.source and not transition.reenter:
            logger.debug("🔄 Executing internal transition actions.")  # 📉 #55
            self._execute_internal_transition(transition, event)
            return

        # 4. All other transitions are external; process the state change.
        self._process_single_transition(transition, event, target_state)

    def _execute_internal_transition(
        self, transition: TransitionDefinition, event: Event
    ) -> None:
        """Sync mirror of `BaseInterpreter._execute_internal_transition`.

        Context-only transaction for targetless / internal self-transitions
        so `actionErrorPolicy` applies to action-only handlers (#27 review).
        """
        context_before: Optional[TContext] = (
            copy.deepcopy(self.context)
            if self.machine.action_error_policy != "continue"
            else None
        )
        try:
            failed = self._execute_actions(transition.actions, event)
            if failed:
                self._apply_action_error_policy(transition, failed)
        except _RollbackRequested as cause:
            logger.warning(
                "💥 Internal transition on '%s' failed; restoring context.",
                transition.source.id,
            )
            self._finish_rollback(cause, transition, context_before)
            return
        if not failed:
            self.last_transition_ok = True
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                self._active_state_nodes,
                self._active_state_nodes,
                transition,
            )

    def _execute_lifecycle_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """Sync mirror of `BaseInterpreter._execute_lifecycle_actions`."""
        failed = self._execute_actions(actions, event)
        if not failed:
            return
        if self._lifecycle_failures:
            self._lifecycle_failures[-1][1].extend(failed)
            return
        self._report_start_failure(failed)

    def _process_single_transition(
        self,
        transition: TransitionDefinition,
        event: Event,
        target_state: StateNode,
    ) -> None:
        """Processes a single, specific external transition.

        Args:
            transition: The external `TransitionDefinition` to execute.
            event: The event that triggered this transition.
            target_state: The pre-resolved target `StateNode`.
        """
        # For external transitions, prepare for state changes.
        snapshot_before_transition = self._active_state_nodes.copy()
        # 🧷 See BaseInterpreter._execute_transition: context is only
        #    snapshotted when a rollback could need it.
        context_before: Optional[TContext] = (
            copy.deepcopy(self.context)
            if self.machine.action_error_policy != "continue"
            else None
        )
        domain = self._find_transition_domain(transition, target_state)

        # Determine the full path of states to exit and enter.
        path_to_enter = self._get_path_to_state(target_state, stop_at=domain)
        states_to_exit: Set[StateNode] = self._compute_states_to_exit(
            domain, target_state
        )

        # 🕰️ A history pseudo-state is never entered itself; expand it to the
        #    remembered configuration. Mirrors BaseInterpreter._execute_transition.
        history_targets: List[StateNode] = []
        if target_state.type == "history":
            history_targets = self._resolve_history_target(target_state)
            path_to_enter = []

        # Execute the transition sequence (Exit -> Actions -> Enter)
        #
        # 🏛️ Architecture decision: `_exit_states`/`_enter_states` own all
        # mutation of `_active_state_nodes`. A previous implementation also ran
        # `difference_update(states_to_exit)` after entry, which deleted the
        # initial children just entered by the recursive descent and left the
        # machine with no active leaf. See `BaseInterpreter._execute_transition`.
        #
        # ⚛️ ATOMICITY: the three steps below are one transaction. If a user
        #    action raises between exit and enter, the source has already been
        #    left and the target was never reached, so the machine would be
        #    holding an EMPTY configuration while still reporting "running" —
        #    permanently dead and advertising itself as healthy. Restoring the
        #    pre-transition configuration keeps the interpreter in a state that
        #    actually exists, then re-raises so the caller still learns of the
        #    failure. A torn configuration is strictly worse than a rolled-back
        #    one: it is unrecoverable and silently swallows every later event.
        # 🧾 Entry/exit failures are collected here and judged once the whole
        #    sequence has run -- see `BaseInterpreter._execute_lifecycle_actions`.
        self._lifecycle_failures.append((transition, []))
        try:
            self._exit_states(
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
            failed_actions = self._execute_actions(transition.actions, event)
            if failed_actions:
                self._apply_action_error_policy(transition, failed_actions)
            self._enter_states(path_to_enter, event)

            # 🕰️ Restore the remembered configuration for a history target.
            #    ONE combined call — see `BaseInterpreter._execute_transition`.
            #    Entering each remembered leaf separately let every ancestor
            #    run its default `initial` descent as well, activating two
            #    leaves in one region.
            if target_state.type == "history":
                combined_path: List[StateNode] = []
                for node in history_targets:
                    for step in self._get_path_to_state(node, stop_at=domain):
                        if step not in combined_path:
                            combined_path.append(step)
                if combined_path:
                    self._enter_states(combined_path, event)
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
            # ⏱️ Cancel timers/invokes armed by the PARTIAL entry -- see the
            #    matching comment in `BaseInterpreter._execute_transition`.
            for node in self._active_state_nodes - snapshot_before_transition:
                self._cancel_state_tasks(node)
            self._active_state_nodes.clear()
            self._active_state_nodes.update(snapshot_before_transition)

            # ⏱️ Re-arm cancelled timers/services — see the matching comment
            #    in `BaseInterpreter._execute_transition`. Without this the
            #    restored configuration is inert.
            for node in snapshot_before_transition:
                if node in states_to_exit:
                    self._schedule_state_tasks(node)
            if self._finish_rollback(
                rollback_cause, transition, context_before
            ):
                return
            raise
        finally:
            self._lifecycle_failures.pop()

        # Notify plugins and subscribers of the completed transition.
        if not failed_actions:
            self.last_transition_ok = True
        self._notify_subscribers()
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                snapshot_before_transition,
                self._active_state_nodes.copy(),
                transition,
            )

    def _process_transient_transitions(self) -> None:
        """Continuously processes event-less ("always") transitions until stable.

        These transitions are checked after any state change. They allow for
        conditional, immediate jumps without an external event. The loop

        continues until no more "always" transitions are available and the
        state configuration is stable.
        """
        logger.debug("🔍 Checking for transient ('always') transitions...")
        # 🛟 Bound the microstep loop. A pair of `always` transitions that
        #    target each other spins forever; XState added the same guard in
        #    v5.31.0. `max_iterations` is configurable on the machine.
        iterations = 0
        limit = getattr(self.machine, "max_iterations", 1000)
        while True:
            iterations += 1
            if iterations > limit:
                logger.error(
                    "🔁 Exceeded %d microsteps while settling transient "
                    "transitions in '%s'. Aborting to avoid an infinite "
                    "loop; check for mutually-targeting 'always' transitions.",
                    limit,
                    self.id,
                )
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
                self._process_event(transient_event)
            else:
                # ✅ No more transient transitions found. The state is stable.
                logger.debug(
                    "🧘 State is stable. No more transient transitions."
                )
                break

    # -------------------------------------------------------------------------
    # ➡️⬅️ State Lifecycle Hooks (Private)
    # -------------------------------------------------------------------------

    def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Synchronously enters a list of states and executes their entry logic.

        This method handles adding states to the active set, executing 'on_entry'
        actions, invoking services, scheduling timers, and recursively entering
        initial states for compound/parallel states.

        Args:
            states_to_enter: A list of `StateNode` objects to enter,
                ordered from parent to child.
            event: The optional event that triggered the state entry.
        """
        # 🗺️ Index the remaining path so a compound state can tell whether the
        #    caller already named which child to descend into. See the matching
        #    comment in `BaseInterpreter._enter_states`: descending into
        #    `initial` unconditionally, in addition to walking the explicit
        #    path, leaves two simultaneously active leaves in one region.
        explicit_children = {
            node.parent.id
            for node in states_to_enter
            if node.parent is not None
        }
        explicit_child_ids = {
            node.id for node in states_to_enter if node.parent is not None
        }

        for state in states_to_enter:
            logger.debug("➡️ Entering state: '%s'", state.id)  # 📉 #55
            self._active_state_nodes.add(state)
            # 📨 Pass the REAL triggering event through. Synthesising an
            #    `entry.<id>` event here discarded the payload, so an entry
            #    action reading `event.payload` — the normal way to seed state
            #    from an event — silently received nothing. The async engine
            #    always forwarded the real event, so this also made the two
            #    engines disagree. `event` may be None during initial entry,
            #    which is why the fallback is retained.
            self._execute_lifecycle_actions(
                state.entry,
                event if event is not None else Event(f"entry.{state.id}"),
            )

            # 🏁 Handle final state logic by firing a `done` event if applicable.
            if state.type == "final":
                logger.debug(
                    "🏁 Final state '%s' entered. Checking parent for 'on_done'.",
                    state.id,
                )
                self._check_and_fire_on_done(state)

            # 🌳 For compound states, recursively enter their initial child state.
            if state.type == "compound" and state.initial:
                # ⏭️ Skip the default descent when the entry path already
                #    specifies which child of this state to enter.
                if state.id in explicit_children:
                    self._schedule_state_tasks(state)
                    logger.debug(
                        "✅ State '%s' entered successfully.", state.id
                    )
                    continue
                initial_child = state.states.get(state.initial)
                if initial_child:
                    logger.debug(
                        "🌲 Entering initial child '%s' for compound state '%s'.",
                        initial_child.id,
                        state.id,
                    )
                    self._enter_states([initial_child])
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

            # 🌐 For parallel states, recursively enter all child regions.
            elif state.type == "parallel":
                logger.debug(
                    "🌐 Entering all regions for parallel state '%s'.",
                    state.id,
                )
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
                    self._enter_states(regions)

            # ⚙️ Schedule any tasks (invokes, timers).
            self._schedule_state_tasks(state)
            logger.debug("✅ State '%s' entered successfully.", state.id)

    def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Synchronously exits a list of states and executes their exit logic.

        This handles canceling any tasks associated with the state, executing
        'on_exit' actions, and removing states from the active set.

        Args:
            states_to_exit: A list of `StateNode` objects to exit,
                ordered from child to parent.
            event: The optional event that triggered the state exit.
        """
        # 🕰️ Record history *before* anything is removed, so the
        #    remembered configuration reflects the pre-transition state.
        self._record_history(states_to_exit)

        # 🧹 Cancel tasks BEFORE any other processing to prevent race conditions.
        for state in states_to_exit:
            self._cancel_state_tasks(state)

        # 🏃‍♂️ Then proceed with normal exit processing.
        for state in states_to_exit:
            logger.debug("⬅️ Exiting state: '%s'", state.id)  # 📉 #55
            # 📨 Forward the real triggering event; see `_enter_states`.
            self._execute_lifecycle_actions(
                state.exit,
                event if event is not None else Event(f"exit.{state.id}"),
            )
            self._active_state_nodes.discard(state)
            logger.debug("✅ State '%s' exited successfully.", state.id)

    def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Checks if an ancestor state is "done" and queues a `done.state.*` event.

        Triggered when a final state is entered. It checks if the parent
        state has met its completion criteria (e.g., all parallel regions
        are in final states). If so, it queues the corresponding `on_done` event.

        Args:
            final_state: The final state that was just entered.
        """
        ancestor = final_state.parent
        logger.debug(
            "🔍 Checking 'done' status for ancestors of final state '%s'.",
            final_state.id,
        )
        while ancestor:
            # 🧐 Check if the ancestor has an `on_done` handler and is fully completed.
            if ancestor.on_done and self._is_state_done(ancestor):
                done_event_type = f"done.state.{ancestor.id}"
                logger.info(
                    "🥳 State '%s' is done! Queuing onDone event: '%s'",
                    ancestor.id,
                    done_event_type,
                )
                # 📬 Send the `done.state.*` event for the next processing
                #    cycle, carrying the final state's `output` as done data.
                self.send(
                    DoneEvent(
                        type=done_event_type,
                        data=self._resolve_output(final_state),
                        src=ancestor.id,
                    )
                )
                return  # 🛑 Only fire the event for the nearest completed ancestor.

            ancestor = ancestor.parent

        # 🏁 A top-level final state completes the machine itself.
        if final_state.parent is self.machine or final_state.parent is None:
            # 📝 A machine-level `output` wins over the final state's own,
            #    matching XState. See BaseInterpreter._check_and_fire_on_done.
            machine_output = getattr(self.machine, "machine_output", None)
            if machine_output is not None:
                self._complete(self._resolve_output_value(machine_output))
            else:
                self._complete(self._resolve_output(final_state))

    # -------------------------------------------------------------------------
    # ⚡ Action & Service Execution (Private Overrides)
    # -------------------------------------------------------------------------

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> List[Tuple[ActionDefinition, BaseException]]:
        """Synchronously executes a list of actions.

        This method iterates through action definitions, validates them, and
        executes the corresponding implementation from the machine's logic.
        It specifically handles spawning actors and raises errors for async actions.

        Args:
            actions: The list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.

        Returns:
            The ``(action, exception)`` pairs for actions that raised, in
            execution order; empty when all succeeded. Mirrors
            `Interpreter._execute_actions` so both engines feed the same
            ``action_error_policy`` logic in `BaseInterpreter`.

        Raises:
            ImplementationMissingError: If an action implementation is not found.
            NotSupportedError: If an async action is encountered.
        """
        failed: List[Tuple[ActionDefinition, BaseException]] = []
        if not actions:
            return failed

        for action_def in actions:
            # 🔌 Notify plugins before execution
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 🎭 Handle actor spawning actions
            if action_def.type.startswith(
                (SPAWN_BLOCKING_PREFIX, "spawn_")
            ) and not is_builtin(action_def.type):
                self._spawn_actor(action_def, event)
                continue

            # ⚙️ Handle normal actions
            action_impl = self.machine.logic.actions.get(action_def.type)

            # 🎬 Built-in action creators, resolved only when the user has NOT
            #    supplied an action of the same name so a machine defining its
            #    own `log` or `assign` keeps working.
            if action_impl is None:
                canonical = resolve_builtin(action_def.type)
                if canonical is not None:
                    # 🛡️ See Interpreter._execute_actions: built-ins resolve
                    #    user callables and can raise like any user action.
                    try:
                        self._execute_builtin_action(
                            canonical, action_def, event
                        )
                    except Exception as exc:
                        logger.exception(
                            "🔥 Built-in action '%s' raised while handling "
                            "'%s'; skipping remaining actions.",
                            action_def.type,
                            event.type,
                        )
                        # 🔔 The async engine already fired this hook for
                        #    built-in failures; the sync engine did not, so
                        #    the same machine reported different things on
                        #    the two engines. Aligned in 0.8.0.
                        for plugin in self._plugins:
                            plugin.on_action_error(self, action_def, exc)
                        failed.append((action_def, exc))
                        return failed
                    continue

            if not action_impl:
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' not implemented."
                )
            # 🚫 Reject async actions
            if self._is_async_callable(action_impl):
                raise NotSupportedError(
                    f"Async action '{action_def.type}' not supported by SyncInterpreter."
                )
            # ▶️ Execute the synchronous action.
            #
            # 🏛️ Architecture decision: an exception raised *inside* a
            # user-supplied action is contained. Per the documented contract
            # the error is logged, the remaining actions in this list are
            # skipped, and the state change still completes — a buggy side
            # effect must not corrupt the configuration or kill the machine.
            # Configuration errors (missing/async action) are raised above and
            # deliberately remain fatal.
            try:
                action_impl(self, self.context, event, action_def)
            except Exception as exc:
                logger.exception(
                    "🔥 Action '%s' raised while handling event '%s'; "
                    "skipping remaining actions in this list.",
                    action_def.type,
                    event.type,
                )
                # 🔔 Surface the failure programmatically. Containment keeps
                #    the machine alive, but it also makes the error invisible:
                #    the transition completes as though the action succeeded.
                #    A log line is not something an application can act on, so
                #    this hook is the supported way to route the failure to
                #    Sentry, a metric, or a dead-letter queue.
                for plugin in self._plugins:
                    plugin.on_action_error(self, action_def, exc)
                failed.append((action_def, exc))
                return failed
        return failed

    def _execute_builtin_action(
        self,
        canonical: str,
        action_def: ActionDefinition,
        event: Event,
    ) -> None:
        """Executes a built-in action creator synchronously.

        Mirrors `Interpreter._execute_builtin_action`. Delayed sends are
        backed by `threading.Timer` rather than asyncio tasks, matching how
        this engine already implements `after`.

        Args:
            canonical (str): The canonical built-in action name.
            action_def (ActionDefinition): The action being executed.
            event (Event): The triggering event.
        """
        followups = self._collect_builtin_followups(
            canonical, action_def, event
        )
        if followups:
            self._action_depth += 1
            try:
                self._execute_actions(
                    [ActionDefinition(f) for f in followups], event
                )
            finally:
                self._action_depth -= 1

        params = self._resolve_params(action_def.params, event) or {}

        if canonical == RAISE:
            self._deliver(
                self,
                self._resolve_event_spec(params.get("event"), event),
                self._resolve_delay(params.get("delay"), event),
                params.get("id"),
            )

        elif canonical == SEND_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            if actor is None:
                logger.warning(
                    "⚠️ sendTo could not resolve target %r; event dropped.",
                    params.get("to"),
                )
                return
            self._deliver(
                actor,
                self._resolve_event_spec(params.get("event"), event),
                self._resolve_delay(params.get("delay"), event),
                params.get("id"),
            )

        elif canonical == SEND_PARENT:
            if self.parent is None:
                logger.warning("⚠️ sendParent called with no parent actor.")
                return
            self._deliver(
                self.parent,
                self._resolve_event_spec(params.get("event"), event),
                self._resolve_delay(params.get("delay"), event),
                params.get("id"),
            )

        elif canonical == FORWARD_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            if actor is None:
                logger.warning(
                    "⚠️ forwardTo could not resolve target %r.",
                    params.get("to"),
                )
                return
            self._deliver(actor, event, None, None)

        elif canonical == ESCALATE:
            escalate_event = Event(
                type=f"xstate.error.actor.{self.id}",
                payload={"error": params.get("error")},
            )
            if self.parent is not None:
                self._deliver(self.parent, escalate_event, None, None)
            else:
                logger.error(
                    "🔥 escalate() with no parent actor: %r",
                    params.get("error"),
                )

        elif canonical == STOP_CHILD:
            actor = self._resolve_actor_target(params.get("id"), event)
            if actor is None:
                logger.warning(
                    "⚠️ stopChild could not resolve %r.", params.get("id")
                )
                return
            for actor_id, candidate in list(self._actors.items()):
                if candidate is actor:
                    del self._actors[actor_id]
                    self._actor_sources.pop(actor_id, None)
                    break
            # 🌐 Also drop it from the actor-system registry, otherwise a
            #    stopped actor stays addressable by systemId.
            registry = self._system_registry()
            for system_id, candidate in list(registry.items()):
                if candidate is actor:
                    del registry[system_id]
            actor.stop()

        elif canonical == SPAWN_CHILD:
            src = params.get("src")
            if not isinstance(src, str):
                logger.warning("⚠️ spawnChild requires a string 'src'.")
                return
            self._spawn_actor(
                ActionDefinition(
                    {
                        "type": f"spawn_{src}",
                        "params": {
                            "id": params.get("id"),
                            "systemId": params.get("systemId"),
                            "input": params.get("input"),
                        },
                    }
                ),
                event,
            )

    def _deliver(
        self,
        actor: Any,
        target_event: Event,
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
            actor.send(target_event)
            return

        key = str(send_id) if send_id else None

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

        handle = self.clock.set_timeout(_fire, delay / 1000.0, owner=self.id)
        self._timer_handles.setdefault(self.id, []).append(handle)

        # 🔁 Reusing a send id supersedes the earlier send. Without this the
        #    first timer is orphaned: the registry entry is overwritten, so
        #    `cancel(id)` can no longer reach it and it fires anyway.
        def _cancel() -> None:
            self.clock.clear_timeout(handle)

        if key is not None:
            previous = self._scheduled_sends.get(key)
            if previous is not None:
                previous()
            self._scheduled_sends[key] = _cancel

    def _spawn_actor(
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
        child = SyncInterpreter(actor_machine, input=spawn_params.get("input"))
        child.parent = self
        child.id = actor_id
        # 🌐 Register under a systemId so siblings can address it.
        self._register_in_system(spawn_params.get("systemId"), child)
        self._actors[actor_id] = child
        self._actor_sources[actor_id] = key

        # 🧹 Review F3: a child that finishes on its own leaves the map.
        child._terminal_listeners.append(
            lambda _s, aid=actor_id: self._actors.pop(aid, None)
        )

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
        def _runner() -> None:
            """Starts the child and cleans up when it's done or stopped."""
            try:
                # 🚀 Start the actor in the background thread.
                child.start()
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

        # 🚀 Start the thread
        threading.Thread(
            target=_runner, daemon=True, name=f"actor-{actor_id}"
        ).start()

    def _wait_for_child_terminal(self, child: "SyncInterpreter") -> None:
        """Block until *child* is done/error, or `spawnBlockingTimeout` lapses.

        Uses the shared terminal-listener hook (#43) rather than polling
        `status`, so completion is observed the instant it happens.
        """
        if child.status in ("done", "error"):
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

        done_event = DoneEvent(
            type=f"done.invoke.{invoke_id}",
            data=child.context,
            src=invoke_id,
        )
        logger.info("🏁 Child actor '%s' completed; firing onDone.", child.id)
        self.send(done_event)

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """Cancel every clock timer (`after`, delayed send) a state owns.

        Args:
            state (StateNode): The state being exited.
        """
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

        handle = self.clock.set_timeout(_fire, delay_sec, owner=owner_id)
        self._timer_handles.setdefault(owner_id, []).append(handle)

    def _pump_timers(self) -> int:
        """Fire every due clock deadline onto the queue (the timer pump).

        Called at the top of `send()` and by `tick()`. Returns how many
        fired. Does NOT process the queue; the caller does.
        """
        return self.clock.pump()

    def tick(self) -> None:
        """Deliver every `after` / delayed send whose deadline has passed.

        🏛️ #50: with no timer threads, a machine that receives no events
        needs a caller to advance it. `tick()` is that pump: it fires due
        deadlines onto the queue and processes them, all on the calling
        thread. It is also the seam a `SimulatedClock` drives.
        """
        if self.status != "running":
            return
        self._pump_timers()
        if self._event_queue and not self._is_processing:
            self._process_event_queue()
            self._process_transient_transitions()

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
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
                    DoneEvent(
                        type=f"error.platform.{invocation.id}",
                        data=exc,
                        src=invocation.id,
                    )
                )
                return
            if child_input is not None:
                params["input"] = child_input
            self._spawn_actor(
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
            self.send(done_event)
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
            error_event = DoneEvent(
                f"error.platform.{invocation.id}", data=e, src=invocation.id
            )
            # 🚨 Unhandled service failures must be observable, not just
            #    logged. See BaseInterpreter._fail.
            handled = self._has_error_handler(invocation)
            self.send(error_event)
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
            if not handled:
                self._fail(e)

    # -------------------------------------------------------------------------
    # 🛠️ Helper & Utility Methods (Private)
    # -------------------------------------------------------------------------

    def _resolve_target_state_robustly(
        self, transition: TransitionDefinition
    ) -> StateNode:
        """Resolve a transition's target or raise `StateNotFoundError`.

        🏛️ Architecture decision (#34, #60): this used to be a 100-line copy
        of `BaseInterpreter._resolve_target_state_node` -- including the
        three fuzzy fallbacks that bound typos to unrelated states. Two
        copies of one algorithm is how the engines drifted apart. It now
        delegates to the single shared implementation and only adds the
        sync engine's raise-instead-of-None contract.

        Raises:
            StateNotFoundError: The target resolves to nothing. The message
                names the target AND the source state so the failing
                transition is identifiable from the exception alone.
            ValueError: Empty target on an external transition.
        """
        if not transition.target_str:
            raise ValueError("Target string cannot be empty for resolution.")
        state = self._resolve_target_state_node(transition)
        if state is None:
            raise StateNotFoundError(
                transition.target_str, transition.source.id
            )
        return state

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
        # A coroutine function's code object has the CO_COROUTINE flag set.
        return hasattr(callable_obj, "__code__") and (
            callable_obj.__code__.co_flags & 0x80  # noqa
        )
