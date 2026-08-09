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
    Union,
    overload,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .base_interpreter import BaseInterpreter
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
        _after_threads (Dict[str, threading.Thread]): Tracks background threads for `after` timers.
        _after_events (Dict[str, threading.Event]): Manages cancellation signals for `after` timers.
    """

    # -------------------------------------------------------------------------
    # 🧙 Magic Methods & Initialization
    # -------------------------------------------------------------------------

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        input: Optional[Any] = None,
    ) -> None:
        """Initializes a new synchronous Interpreter instance.

        Args:
            machine: The state machine definition that this interpreter will run.
        """
        # 🤝 Initialize the base interpreter first
        super().__init__(
            machine, interpreter_class=SyncInterpreter, input=input
        )
        logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")

        # ⚙️ Initialize synchronous-specific attributes
        self._event_queue: Deque[Union[Event, DoneEvent, AfterEvent]] = deque()
        self._is_processing: bool = False
        self._after_threads: Dict[str, threading.Thread] = {}
        self._after_events: Dict[str, threading.Event] = {}
        #: Cancellation flags for pending delayed sends, released by `stop()`.
        self._pending_send_cancels: Set[threading.Event] = set()

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
        if self.status != "uninitialized":
            logger.info(
                "🚧 Interpreter '%s' already running or stopped. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting sync interpreter '%s'...", self.id)
        self.status = "running"

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

    def stop(self) -> None:
        """Stops the interpreter and cleans up all associated resources.

        This method stops all child actors, cancels any pending `after` timers,
        and sets the interpreter's status to 'stopped', preventing further
        event processing. It's idempotent.
        """
        # 🚦 Idempotency check.
        #
        # 🏛️ `done` and `error` are terminal but NOT torn down: reaching a
        # top-level final state must still release child actors and timers.
        # Guarding on `!= "running"` made `stop()` a silent no-op for every
        # machine that completed, leaking actors and their timer threads.
        if self.status in ("uninitialized", "stopped"):
            return

        logger.info(
            "🛑 Stopping sync interpreter '%s' and its actors…", self.id
        )

        # 1️⃣ Stop every child actor (blocking & non-blocking).
        #
        # 📝 Status is set to "stopped" FIRST so a cyclic actor graph
        #    terminates: the child's own `stop()` re-enters this one, which
        #    now hits the idempotency guard instead of recursing forever.
        self.status = "stopped"
        for actor_id, actor in list(self._actors.items()):
            try:
                actor.stop()
            finally:
                self._actors.pop(actor_id, None)

        # 2️⃣ Cancel all `after` timers by signaling their cancellation events
        for state_id in list(self._after_events.keys()):
            self._after_events[state_id].set()
        self._after_events.clear()
        self._after_threads.clear()

        # 2️⃣.5 Release any waiting delayed-send threads. They are daemons, so
        #      they never block process exit, but a long delay would otherwise
        #      keep one alive for its full duration after shutdown.
        for cancel_flag in list(self._pending_send_cancels):
            cancel_flag.set()
        self._pending_send_cancels.clear()
        self._scheduled_sends.clear()

        # 3️⃣ Update status to prevent further operations
        self.status = "stopped"

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
        self._event_queue.append(event_obj)
        self._process_event_queue()

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
        try:
            while self._event_queue:
                current_event = self._event_queue.popleft()
                logger.info("⚙️ Processing event: '%s'", current_event.type)

                for plugin in self._plugins:
                    plugin.on_event_received(self, current_event)

                self._process_event(current_event)
                self._process_transient_transitions()
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
            logger.debug(
                "🤷 No valid transition found for event '%s'.", event.type
            )
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
            logger.info("🔄 Executing internal transition actions.")
            self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 2. Resolve the target state node.
        target_state = self._resolve_target_state_robustly(transition)

        # 3. A self-transition without `reenter: True` is also internal.
        if target_state == transition.source and not transition.reenter:
            logger.info("🔄 Executing internal transition actions.")
            self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 4. All other transitions are external; process the state change.
        self._process_single_transition(transition, event, target_state)

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
        self._exit_states(
            sorted(list(states_to_exit), key=lambda s: s.depth, reverse=True),
            event,
        )
        self._execute_actions(transition.actions, event)
        self._enter_states(path_to_enter, event)

        # 🕰️ Restore the remembered configuration for a history target.
        if target_state.type == "history":
            for node in history_targets:
                self._enter_states(
                    self._get_path_to_state(node, stop_at=domain), event
                )

        # Notify plugins and subscribers of the completed transition.
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

            # 🎯 Find the most specific transient transition available.
            transition = self._find_optimal_transition(transient_event)

            # ⚡ An event-less transition is one with an empty event string ("").
            if transition and transition.event == "":
                logger.info(
                    "🚀 Processing transient transition from '%s' to target '%s'",
                    transition.source.id,
                    transition.target_str or "self (internal)",
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
            logger.info("➡️ Entering state: '%s'", state.id)
            self._active_state_nodes.add(state)
            self._execute_actions(state.entry, Event(f"entry.{state.id}"))

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
            logger.info("⬅️ Exiting state: '%s'", state.id)
            self._execute_actions(state.exit, Event(f"exit.{state.id}"))
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
    ) -> None:
        """Synchronously executes a list of actions.

        This method iterates through action definitions, validates them, and
        executes the corresponding implementation from the machine's logic.
        It specifically handles spawning actors and raises errors for async actions.

        Args:
            actions: The list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.

        Raises:
            ImplementationMissingError: If an action implementation is not found.
            NotSupportedError: If an async action is encountered.
        """
        if not actions:
            return

        for action_def in actions:
            # 🔌 Notify plugins before execution
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 🎭 Handle actor spawning actions
            if action_def.type.startswith(
                ("spawn_", "spawn_blocking_")
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
                    self._execute_builtin_action(canonical, action_def, event)
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
            except Exception:
                logger.exception(
                    "🔥 Action '%s' raised while handling event '%s'; "
                    "skipping remaining actions in this list.",
                    action_def.type,
                    event.type,
                )
                return

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
        """Sends an event to an actor, honouring an optional delay.

        Args:
            actor (Any): The recipient interpreter.
            target_event (Event): The event to deliver.
            delay (Optional[float]): Delay in milliseconds, or `None`.
            send_id (Optional[str]): Id allowing later cancellation.
        """
        if not delay:
            actor.send(target_event)
            return

        cancel_flag = threading.Event()

        def _fire() -> None:
            """Delivers the event unless cancelled while waiting."""
            if cancel_flag.wait(delay / 1000.0):
                return
            if send_id:
                self._scheduled_sends.pop(str(send_id), None)
            self._pending_send_cancels.discard(cancel_flag)
            try:
                actor.send(target_event)
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "🔥 Delayed send of '%s' failed.", target_event.type
                )

        # 🔁 Reusing a send id supersedes the earlier send. Without this the
        #    first timer is orphaned: the registry entry is overwritten, so
        #    `cancel(id)` can no longer reach it and it fires anyway.
        if send_id:
            previous = self._scheduled_sends.get(str(send_id))
            if previous is not None:
                previous()
            self._scheduled_sends[str(send_id)] = cancel_flag.set

        # 🧹 Track every pending waiter so `stop()` can release it. The
        #    threads are daemons (they cannot block interpreter exit), but a
        #    long delay would otherwise keep one alive for its full duration
        #    after the machine has shut down.
        self._pending_send_cancels.add(cancel_flag)

        timer = threading.Thread(
            target=_fire, name=f"send-{target_event.type}", daemon=True
        )
        timer.start()

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> None:
        """Spawns a child state machine actor in blocking or non-blocking mode.

        Args:
            action_def: The action definition for spawning the actor.
            event: The event that triggered the spawn action.

        Raises:
            ActorSpawningError: If the specified service is not a valid
                `MachineNode` or a factory that returns one.
        """
        # 🕵️ Determine mode (blocking vs. non-blocking) and service key
        blocking = action_def.type.startswith("spawn_blocking_")
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
        child = SyncInterpreter(actor_machine)
        child.parent = self
        child.id = actor_id
        # 📥 Seed the child's context with any declared input.
        child_input = spawn_params.get("input")
        if child_input is not None:
            child.context.setdefault("input", child_input)
        # 🌐 Register under a systemId so siblings can address it.
        self._register_in_system(spawn_params.get("systemId"), child)
        self._actors[actor_id] = child
        self._actor_sources[actor_id] = key

        # --- Blocking Execution Path ---
        if blocking:
            child.start()
            return

        # --- Non-Blocking Execution Path (via a background thread) ---
        def _runner() -> None:
            """Starts the child and cleans up when it's done or stopped."""
            try:
                # 🚀 Start the actor in the background thread.
                child.start()
                # 🔄 Keep the thread alive while the child runs.
                while child.status == "running":
                    # 🏁 Exit loop if the child reaches a top-level final state.
                    if any(
                        s.is_final and s.parent == child.machine
                        for s in child._active_state_nodes
                    ):
                        break
                    time.sleep(0.01)  # 🤏 Yield to prevent busy-waiting.
            finally:
                # 🧹 Ensure cleanup happens whether the child finishes or is stopped.
                child.stop()
                self._actors.pop(actor_id, None)
                logger.info("🧹 Actor thread for '%s' cleaned up.", actor_id)

        # 🚀 Start the thread
        threading.Thread(
            target=_runner, daemon=True, name=f"actor-{actor_id}"
        ).start()

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """Cancel all pending **after** timers that belong to a state.

        This handles *multiple* timers per state by matching a prefix-based key.
        Older code assumed one timer per state and leaked others.

        Args:
            state (StateNode): The state whose timers should be cancelled.
        """
        state_prefix = f"{state.id}::"  # our internal key scheme
        to_cancel = [
            k
            for k in list(self._after_events.keys())
            if k == state.id or k.startswith(state_prefix)
        ]

        if not to_cancel:
            logger.debug(
                "🧹 No 'after' timers to cancel for state '%s'.", state.id
            )
            return

        for key in to_cancel:
            try:
                logger.debug(
                    "🧹 Cancelling 'after' timer key='%s' (owner='%s')",
                    key,
                    state.id,
                )
                self._after_events[key].set()  # signal cancellation
            finally:
                # Remove from tracking dicts whether the thread is alive or not;
                # the thread cleans itself up on exit as well.
                self._after_events.pop(key, None)
                self._after_threads.pop(key, None)

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Schedule a delayed `AfterEvent` on a background thread.

        Supports **multiple timers per owner** by storing them under unique keys.
        Threads watch a cancellation `Event` so exits cleanly on state leave.

        Args:
            delay_sec (float): Delay (seconds) before firing.
            event (AfterEvent): Event to send when the timer expires.
            owner_id (str): ID of the state that owns this timer.
        """
        # Generate a unique handle so a state can own several timers simultaneously.
        unique_key = f"{owner_id}::{uuid.uuid4()}"
        cancel_event = threading.Event()

        logger.info(
            "⏰ Scheduling 'after' (%s) in %.2fs for state '%s' [key=%s]",
            event.type,
            delay_sec,
            owner_id,
            unique_key,
        )

        # Register for lifecycle management.
        self._after_events[unique_key] = cancel_event

        def timer_thread() -> None:
            """Worker that waits, checks cancellation, and sends the event."""
            try:
                cancelled = cancel_event.wait(timeout=delay_sec)
                if cancelled:
                    logger.debug(
                        "🚫 Timer cancelled before firing [key=%s].",
                        unique_key,
                    )
                    return

                # Fire only if interpreter still running AND owner still active.
                if self.status == "running" and any(
                    s.id == owner_id for s in self._active_state_nodes
                ):
                    logger.debug(
                        "🕒 Timer expired -> sending event '%s' [key=%s].",
                        event.type,
                        unique_key,
                    )
                    self.send(event)
                else:
                    logger.debug(
                        "⚠️ Timer expired but owner inactive or interpreter stopped [key=%s].",
                        unique_key,
                    )
            except Exception as exc:  # pragma: no cover (safety net)
                logger.error(
                    "💥 Error in after-timer thread [key=%s]: %s",
                    unique_key,
                    exc,
                    exc_info=True,
                )
            finally:
                # Ensure we don't leak references.
                self._after_threads.pop(unique_key, None)
                self._after_events.pop(unique_key, None)

        thread = threading.Thread(
            target=timer_thread, daemon=True, name=f"after-{unique_key}"
        )
        self._after_threads[unique_key] = thread
        thread.start()

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
            self._spawn_actor(
                ActionDefinition(
                    {
                        "type": f"spawn_{invocation.src}",
                        "params": {"id": invocation.id},
                    }
                ),
                Event(type=f"invoke.{invocation.id}"),
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
                f"invoke.{invocation.id}", {"input": invocation.input or {}}
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
        """Resolves a target state string into a StateNode object robustly.

        This method attempts multiple resolution strategies in a specific order
        to provide flexibility in how transitions are defined in the machine.

        Args:
            transition: The transition containing the target string.

        Returns:
            The resolved `StateNode` object.

        Raises:
            StateNotFoundError: If the target state cannot be found after all attempts.
            ValueError: If the target string is empty for an external transition.
        """
        target_str = transition.target_str
        if not target_str:
            raise ValueError("Target string cannot be empty for resolution.")

        root, source = self.machine, transition.source
        parent = source.parent
        logger.debug(
            "🔄 Resolving target state: '%s' from source '%s'",
            target_str,
            source.id,
        )

        # 1️⃣ Standard resolution (relative to source, parent, root, and absolute)
        # This logic is restored from the original implementation to fix the regression.
        attempts = [
            (target_str, source),
            (target_str, parent) if parent else None,
            (target_str, root),
            (f"{root.id}.{target_str}", root),  # Absolute from root
        ]
        for tgt, ref in filter(None, attempts):
            try:
                state = resolve_target_state(tgt, ref)
                logger.debug(
                    "✅ Resolved '%s' via standard method from '%s'.",
                    tgt,
                    ref.id,
                )
                # ‼️ CRITICAL: This mutation logic is restored from the original code.
                transition.target_str = tgt
                return state
            except StateNotFoundError:
                continue  # Try the next method

        # 2️⃣ Direct attribute lookup on root
        if hasattr(root, target_str) and isinstance(
            getattr(root, target_str), StateNode
        ):
            logger.debug(
                "✅ Resolved '%s' via root attribute lookup.", target_str
            )
            return getattr(root, target_str)

        # 3️⃣ Root states dictionary lookup
        if hasattr(root, "states"):
            states_dict = root.states
            if target_str in states_dict:
                logger.debug(
                    "✅ Resolved '%s' via root states dictionary key.",
                    target_str,
                )
                return states_dict[target_str]
            for state in states_dict.values():
                if state.id.split(".")[-1] == target_str:
                    logger.debug(
                        "✅ Resolved '%s' via local name in states dict.",
                        target_str,
                    )
                    return state

        # 4️⃣ Depth-first tree walk fallback (match local ID part)
        for candidate in self._walk_tree(root):
            if candidate.id.split(".")[-1] == target_str:
                logger.debug(
                    "✅ Resolved '%s' via deep tree walk to find '%s'.",
                    target_str,
                    candidate.id,
                )
                return candidate

        # 🔚 Absolute failure
        available_toplevel = list(root.states.keys())
        logger.error(
            "❌ All resolution attempts failed for target: '%s'. Available top-level states: %s",
            target_str,
            available_toplevel,
        )
        raise StateNotFoundError(target_str, root.id)

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

    @staticmethod
    def _walk_tree(node: StateNode) -> "SyncInterpreter._walk_tree":
        """Recursively yields all nodes in a state tree using depth-first traversal.

        This is a generator function used as a fallback mechanism for resolving
        state targets when standard resolution methods fail.

        Args:
            node: The root `StateNode` from which to start the traversal.

        Yields:
            Each `StateNode` in the tree, starting with the root.
        """
        # 🚶‍♂️ Yield the current node first
        yield node
        # 🌳 If the node has children, recurse into them
        if hasattr(node, "states"):
            for child in node.states.values():
                yield from SyncInterpreter._walk_tree(child)
