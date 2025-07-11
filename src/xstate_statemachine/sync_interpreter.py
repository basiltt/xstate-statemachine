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
# fundamentally asynchronous (e.g., `after` timers, spawning actors).
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
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
    ImplementationMissingError,
    NotSupportedError,
    StateNotFoundError,
)
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
    TransitionDefinition,
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

    **Limitations**:
    This interpreter does not support features that require a background event
    loop or timer. Any attempt to use a machine with these features will
    result in a `NotSupportedError`. Unsupported features include:
    - ⏰ Timed `after` transitions.
    - 🎭 Spawning child actors (`spawn_` actions).
    - ⏳ Asynchronous `invoke` services that need to run in the background.

    Attributes:
        _event_queue (Deque[Union[Event, AfterEvent, DoneEvent]]): A queue to
            manage the event processing sequence in a first-in, first-out (FIFO) manner.
        _is_processing (bool): A flag to prevent re-entrant event processing,
            ensuring atomicity of a single `send` call's execution loop.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]) -> None:
        """Initializes a new synchronous Interpreter instance.

        Args:
            machine: The state machine definition (`MachineNode` instance)
                that this interpreter will run.
        """
        # 🤝 Initialize the base interpreter first
        super().__init__(machine, interpreter_class=SyncInterpreter)
        logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")

        # ⚙️ Initialize synchronous-specific attributes
        self._event_queue: Deque[Union[Event, AfterEvent, DoneEvent]] = deque()
        self._is_processing: bool = False

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
                `interpreter = SyncInterpreter(machine).start()`
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

        # 🔌 Notify plugins about the interpreter start and initial transition
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)
            # Pass an empty set as `from_states` for the initial transition
            plugin.on_transition(
                self, set(), self._active_state_nodes, initial_transition
            )

        # ➡️ Enter the machine's initial states.
        self._enter_states([self.machine])
        # 🔄 Process any immediate "always" transitions upon startup.
        self._process_transient_transitions()

        logger.info(
            "✨ Sync interpreter '%s' started. Current states: %s",
            self.id,
            self.current_state_ids,
        )
        return self

    def stop(self) -> None:
        """Stops the interpreter, preventing further event processing.

        Once stopped, any subsequent calls to `send` will be ignored.
        This method is idempotent; calling it on an already stopped interpreter
        has no effect.
        """
        # 🚦 Idempotency check: only stop if currently running.
        if self.status != "running":
            logger.debug(
                "😴 Interpreter '%s' is not running. No need to stop.", self.id
            )
            return

        logger.info("🛑 Stopping sync interpreter '%s'...", self.id)
        self.status = "stopped"

        # 🔌 Notify all registered plugins that the interpreter is stopping.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        logger.info("🕊️ Sync interpreter '%s' stopped successfully.", self.id)

    @overload
    def send(self, event_type: str, **payload: Any) -> None: ...  # noqa: E704

    @overload
    def send(  # noqa
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None: ...

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> None:
        """Sends an event to the machine for immediate, synchronous processing.

        Events are queued and processed sequentially. If an event is sent while
        the interpreter is already processing another, it's added to the queue
        and handled once the current processing cycle completes. This method
        blocks until the entire event processing loop is finished.

        Args:
            event_or_type: The event to send. This can be:
                - A `str`: The type of the event, with `payload` as kwargs.
                - A `dict`: An event object, which must contain a 'type' key.
                - An `Event`, `DoneEvent`, or `AfterEvent` instance.
            **payload: Additional keyword arguments for the event's payload,
                used only when `event_or_type` is a string.

        Raises:
            TypeError: If an unsupported event type is passed.
        """
        # 🚦 Halt if the interpreter is not in a 'running' state.
        if self.status != "running":
            logger.warning("🚫 Cannot send event. Interpreter is not running.")
            return

        # 📦 Normalize the input into a standardized Event object.
        event_obj: Union[Event, DoneEvent, AfterEvent]
        if isinstance(event_or_type, str):
            event_obj = Event(type=event_or_type, payload=payload)
        elif isinstance(event_or_type, dict):
            local_payload = event_or_type.copy()
            event_type = local_payload.pop("type", "UnnamedEvent")
            event_obj = Event(type=event_type, payload=local_payload)
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            event_obj = event_or_type
        else:
            # ❌ Raise an error for unsupported event types.
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        # 📥 Add the normalized event to the processing queue.
        self._event_queue.append(event_obj)

        # 🔒 If already processing, the event is queued and will be handled
        #    by the existing processing loop. Avoid re-entrant execution.
        if self._is_processing:
            logger.debug(
                "🔄 Interpreter already processing. Event '%s' queued.",
                event_obj.type,
            )
            return

        # 🎬 Start the main event processing loop.
        self._is_processing = True
        try:
            # 🔁 Process events from the queue until it's empty.
            while self._event_queue:
                event = self._event_queue.popleft()
                logger.info("⚙️ Processing event: '%s'", event.type)

                # 🔌 Notify plugins that an event is being processed.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🎯 Find and execute the transition for the current event.
                self._process_event(event)
                # 🔄 Check for any resulting event-less ("always") transitions.
                self._process_transient_transitions()
        finally:
            # 🔓 Reset the processing flag, allowing new `send` calls to start the loop.
            self._is_processing = False
            logger.debug("🎉 Event processing cycle completed. Queue empty.")

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic
    # -------------------------------------------------------------------------

    def _process_event(
        self, event: Union[Event, DoneEvent, AfterEvent]
    ) -> None:
        """Finds and executes the optimal transition for a given event.

        This method orchestrates the entire state transition process:
        1.  Finds the best transition that matches the event and its guard.
        2.  Determines the states to exit and enter.
        3.  Executes exit actions, transition actions, and entry actions in order.
        4.  Updates the set of active states.

        The state resolution logic is robust, attempting to find the target state
        through multiple strategies for maximum flexibility in machine definition.

        Args:
            event: The event object to process.
        """
        # 1️⃣ Select the winning transition based on event, guards, and state depth.
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                "🤷 No valid transition found for event '%s'.", event.type
            )
            return

        # 2️⃣ Handle internal transitions: only actions are executed, no state change.
        if not transition.target_str:
            logger.info("🔄 Executing internal transition actions.")
            self._execute_actions(transition.actions, event)
            for plug in self._plugins:
                plug.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 3️⃣ For external transitions, prepare for state changes.
        snapshot_before_transition = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)

        # 🔍 Resolve the target state node using a multi-step strategy.
        target_state = self._resolve_target_state_robustly(transition)

        # 🗺️ Determine the full path of states to exit and enter.
        path_to_enter = self._get_path_to_state(target_state, stop_at=domain)
        states_to_exit: Set[StateNode] = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s is not domain
        }

        # 🏃‍♂️ Execute the transition sequence according to SCXML algorithm.
        #    (Exit -> Transition Actions -> Enter)
        self._exit_states(
            # Sort by depth (desc) to exit deepest children first.
            sorted(
                list(states_to_exit), key=lambda s: len(s.id), reverse=True
            ),
            event,
        )
        self._execute_actions(transition.actions, event)
        self._enter_states(path_to_enter, event)

        # ✅ Finalize the state change and notify plugins.
        self._active_state_nodes.difference_update(states_to_exit)
        self._active_state_nodes.update(path_to_enter)
        for plug in self._plugins:
            plug.on_transition(
                self,
                snapshot_before_transition,
                self._active_state_nodes.copy(),
                transition,
            )

    def _process_transient_transitions(self) -> None:
        """Continuously processes event-less ("always") transitions until stable.

        These transitions are checked after any state change. They allow for
        conditional, immediate jumps without needing an external event, modeling
        a "while" loop or conditional branching in the statechart. The loop
        continues until no more "always" transitions are available.
        """
        logger.debug("🔍 Checking for transient ('always') transitions...")
        while True:
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
                # 🔄 Use the main event processor to handle the transition.
                self._process_event(transient_event)
            else:
                # ✅ No more transient transitions found. The state is stable.
                logger.debug(
                    "🧘 State is stable. No more transient transitions."
                )
                break

    # -------------------------------------------------------------------------
    # ➡️⬅️ State Lifecycle Hooks
    # -------------------------------------------------------------------------

    def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Synchronously enters a list of states and executes their entry logic.

        This method handles:
        - Adding states to the active set.
        - Executing 'on_entry' actions.
        - Invoking services and scheduling tasks.
        - Recursively entering initial states for compound/parallel states.

        Args:
            states_to_enter: A list of `StateNode` objects to enter, typically
                ordered from parent to child.
            event: The optional event that triggered the state entry.
        """
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
                initial_child = state.states.get(state.initial)
                if initial_child:
                    logger.debug(
                        "🌲 Entering initial child '%s' for compound state '%s'.",
                        initial_child.id,
                        state.id,
                    )
                    self._enter_states([initial_child])
                else:
                    logger.error(
                        "🐛 Initial state '%s' not found for compound state '%s'.",
                        state.initial,
                        state.id,
                    )

            # 🌐 For parallel states, recursively enter all child regions.
            elif state.type == "parallel":
                logger.debug(
                    "🌐 Entering all regions for parallel state '%s'.",
                    state.id,
                )
                self._enter_states(list(state.states.values()))

            # ⚙️ "Schedule" any tasks (invokes, etc.). In sync mode, this means
            #    immediate execution for synchronous services.
            self._schedule_state_tasks(state)
            logger.debug("✅ State '%s' entered successfully.", state.id)

    def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Synchronously exits a list of states and executes their exit logic.

        Handles:
        - Canceling any tasks associated with the state.
        - Executing 'on_exit' actions.
        - Removing states from the active set.

        Args:
            states_to_exit: A list of `StateNode` objects to exit, typically
                ordered from child to parent.
            event: The optional event that triggered the state exit.
        """
        for state in states_to_exit:
            logger.info("⬅️ Exiting state: '%s'", state.id)
            # ⏰ Cancel any running tasks/services associated with this state.
            self._cancel_state_tasks(state)
            # ⚡ Execute all 'on_exit' actions.
            self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            # ➖ Remove the state from the active configuration.
            self._active_state_nodes.discard(state)
            logger.debug("✅ State '%s' exited successfully.", state.id)

    # -------------------------------------------------------------------------
    # 🛠️ Helper & Private Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_async_callable(callable_obj: Callable[..., Any]) -> bool:
        """Checks if a callable is an async function (`async def`).

        Args:
            callable_obj: The function or method to check.

        Returns:
            True if the callable is an awaitable coroutine, False otherwise.
        """
        return hasattr(callable_obj, "__await__") or (
            hasattr(callable_obj, "__code__")
            and (
                callable_obj.__code__.co_flags & 0x80
            )  # CO_COROUTINE flag  # noqa
        )

    @staticmethod
    def _walk_tree(node: StateNode):
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

    def _resolve_target_state_robustly(
        self, transition: TransitionDefinition
    ) -> StateNode:
        """Resolves a target state string into a StateNode object robustly.

        This method attempts multiple resolution strategies in a specific order
        to provide flexibility in how transitions are defined in the machine.

        The resolution order is:
        1.  Standard `resolve_target_state` relative to source, its parent, and the root.
        2.  Direct attribute lookup on the machine root (for top-level states).
        3.  Key lookup in the machine root's `states` dictionary.
        4.  Depth-first search of the entire state tree as a final fallback.

        Args:
            transition: The transition definition containing the target string.

        Returns:
            The resolved `StateNode` object.

        Raises:
            StateNotFoundError: If the target state cannot be found after all
                attempts have failed.
        """
        target_str = transition.target_str
        if not target_str:  # Should not happen for external transitions
            raise ValueError("Target string cannot be empty for resolution.")

        root = self.machine
        source = transition.source
        parent = source.parent
        logger.debug("🔄 Resolving target state: '%s'", target_str)

        # 1️⃣ Standard resolution attempts relative to source and parents
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
                transition.target_str = tgt  # Update for consistency
                return state
            except StateNotFoundError:
                continue  # Try the next method

        # 2️⃣ Direct attribute lookup on root
        if hasattr(root, target_str):
            candidate = getattr(root, target_str)
            if isinstance(candidate, StateNode):
                logger.debug(
                    "✅ Resolved '%s' via root attribute lookup.", target_str
                )
                return candidate

        # 3️⃣ Root states dictionary lookup (by key, then by local name)
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

        # 4️⃣ Depth-first tree walk fallback
        for candidate in self._walk_tree(root):
            # Check if the last part of the candidate's ID matches the target
            if candidate.id.split(".")[-1] == target_str:
                logger.debug(
                    "✅ Resolved '%s' via deep tree walk to find '%s'.",
                    target_str,
                    candidate.id,
                )
                return candidate

        # 🔚 Absolute failure
        available = []
        if hasattr(root, "states"):
            available.extend(root.states.keys())
        if hasattr(root, "__dict__"):
            available.extend(
                [
                    k
                    for k in root.__dict__.keys()
                    if not k.startswith("_") and k != "states"
                ]
            )
        logger.error(
            "❌ All resolution attempts failed for target: '%s'. Available top-level states: %s",
            target_str,
            list(set(available)),
        )
        raise StateNotFoundError(target_str, root.id)

    def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Checks if an ancestor state is "done" and queues a `done.state.*` event.

        This is triggered when a final state is entered. It checks if the parent
        state (or any ancestor) has met its completion criteria (e.g., all its
        parallel regions are in final states). If so, it queues the corresponding
        `on_done` event.

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
                # 📬 Send the `done.state.*` event for the next processing cycle.
                self.send(Event(type=done_event_type))
                return  # 🛑 Only fire the event for the nearest completed ancestor.

            ancestor = ancestor.parent

    # -------------------------------------------------------------------------
    # 🚫 Unsupported Asynchronous Feature Handlers (Overrides from BaseInterpreter)
    # -------------------------------------------------------------------------

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """Synchronously executes a list of action definitions.

        This method validates that actions are synchronous callables. It will
        intentionally fail if an `async def` function is provided as an action
        implementation, as this is not supported in the `SyncInterpreter`.

        Args:
            actions: A list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.

        Raises:
            ImplementationMissingError: If an action's implementation is not
                found in the machine's logic.
            NotSupportedError: If an async action (`async def`) or a `spawn`
                action is attempted.
        """
        if not actions:
            return  # 🤔 No actions to execute.

        for action_def in actions:
            logger.debug(
                "⚡ Executing action '%s' for event '%s'.",
                action_def.type,
                event.type,
            )
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 🚫 Explicitly block `spawn_` actions.
            if action_def.type.startswith("spawn_"):
                self._spawn_actor(action_def, event)  # This will raise

            # 🔎 Look up the action's implementation in the machine logic.
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                logger.error(
                    "🛠️ Action '%s' not implemented in machine logic.",
                    action_def.type,
                )
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' not implemented."
                )

            # 🧐 Validate that the action is not an async function.
            if self._is_async_callable(action_callable):
                logger.error(
                    "🚫 Action '%s' is async and not supported by SyncInterpreter.",
                    action_def.type,
                )
                raise NotSupportedError(
                    f"Action '{action_def.type}' is async and not supported by SyncInterpreter."
                )

            # ✅ Execute the synchronous action.
            action_callable(self, self.context, event, action_def)
            logger.debug(
                "✨ Action '%s' executed successfully.", action_def.type
            )

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> None:
        """Raises `NotSupportedError` as actor spawning is not supported.

        This override explicitly prevents the use of `spawn_` actions, which
        are inherently asynchronous.

        Raises:
            NotSupportedError: Always, as this feature is unsupported.
        """
        logger.error(
            "🎭 Actor spawning ('%s') is not supported by SyncInterpreter.",
            action_def.type,
        )
        raise NotSupportedError(
            "Actor spawning is not supported by SyncInterpreter."
        )

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """A no-op method, as the sync interpreter does not manage background tasks.

        This method exists to satisfy the `BaseInterpreter` interface. In a
        synchronous context, there are no long-running timers or services to cancel
        upon state exit.

        Args:
            state: The state for which tasks would be cancelled.
        """
        logger.debug(
            "🧹 Skipping state task cancellation for '%s' (no-op in sync mode).",
            state.id,
        )
        # 🤫 Nothing to do here in a synchronous world.

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Raises `NotSupportedError` as `after` transitions are not supported.

        This override explicitly prevents the use of timed `after` transitions,
        which require an event loop and timers.

        Raises:
            NotSupportedError: Always, as this feature is unsupported.
        """
        logger.error(
            "⏰ Timed 'after' transitions are not supported by SyncInterpreter."
        )
        raise NotSupportedError(
            "`after` transitions are not supported by SyncInterpreter."
        )

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> None:
        """Handles invoked services, supporting only synchronous callables.

        Synchronous services are executed immediately and block the interpreter.
        The service's return value is sent as a `done.invoke.*` event. If the
        service raises an exception, an `error.platform.*` event is sent.

        Args:
            invocation: The definition of the invoked service.
            service: The callable representing the service logic.
            owner_id: The ID of the state node owning this invocation.

        Raises:
            NotSupportedError: If the provided service is an `async def` function.
        """
        # 🧐 Validate that the service is not an async function.
        if self._is_async_callable(service):
            logger.error(
                "🚫 Service '%s' is async and not supported by SyncInterpreter.",
                invocation.src,
            )
            raise NotSupportedError(
                f"Service '{invocation.src}' is async and not supported by SyncInterpreter."
            )

        logger.info(
            "📞 Invoking sync service '%s' (id: '%s')...",
            invocation.src,
            invocation.id,
        )
        # 🔌 Notify plugins that the service is starting.
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
                f"done.invoke.{invocation.id}",
                data=result,
                src=invocation.id,
            )
            self.send(done_event)
            logger.info(
                "✅ Sync service '%s' completed successfully.", invocation.src
            )
            # 🔌 Notify plugins about successful completion.
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, result)

        except Exception as e:
            # 💥 On failure, immediately queue an 'error' event with the exception.
            logger.error(
                "💔 Sync service '%s' failed: %s",
                invocation.src,
                e,
                exc_info=True,  # Include traceback in logs for debugging.
            )
            error_event = DoneEvent(
                f"error.platform.{invocation.id}",
                data=e,
                src=invocation.id,
            )
            self.send(error_event)
            # 🔌 Notify plugins about the failure.
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
