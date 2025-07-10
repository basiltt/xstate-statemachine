# src/xstate_statemachine/sync_interpreter.py

# -----------------------------------------------------------------------------
# ⛓️ Synchronous Interpreter
# -----------------------------------------------------------------------------
# This module provides the `SyncInterpreter`, a fully synchronous engine for
# executing state machines. It inherits from `BaseInterpreter` and implements
# a synchronous event processing model.
#
# This interpreter is designed for use cases where asynchronous programming is
# not necessary or desired. It does not support timed transitions (`after`)
# or long-running asynchronous services (`invoke`), as these are fundamentally
# asynchronous operations. It overrides the core async methods from the base
# class to provide a purely blocking execution flow.
#
# This design adheres to the "Template Method" pattern by overriding specific
# steps (like action execution and task scheduling/cancellation) defined in
# the `BaseInterpreter` to provide a synchronous implementation.
# -----------------------------------------------------------------------------

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Union, overload, Callable, Optional

from .base_interpreter import BaseInterpreter
from .events import AfterEvent, DoneEvent, Event
from .exceptions import NotSupportedError, ImplementationMissingError
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
    """
    Brings a state machine definition to life by interpreting its behavior
    synchronously.

    The `SyncInterpreter` manages the machine's state and processes events
    sequentially and immediately within the `send` method call. It is suitable
    for simpler, blocking workflows.

    **Limitations**: This interpreter does not support features that require
    a background event loop, such as:
    - Timed `after` transitions.
    - Asynchronous `invoke` services that run in the background.
    - Spawning child actors (`spawn_` actions).

    An attempt to use a machine with these features will result in a
    `NotSupportedError`.

    Attributes:
        _event_queue (Deque[Union[Event, AfterEvent, DoneEvent]]): A deque used to manage the event processing sequence.
        _is_processing (bool): A flag to prevent re-entrant event processing.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]) -> None:
        """
        Initializes a new synchronous Interpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The machine definition
                (`MachineNode` instance) that this interpreter will run.
        """
        super().__init__(machine, interpreter_class=SyncInterpreter)
        logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")
        self._event_queue: Deque[Union[Event, AfterEvent, DoneEvent]] = deque()
        self._is_processing: bool = False
        logger.info("Synchronous Interpreter '%s' initialized. 🎉", self.id)

    # -------------------------------------------------------------------------
    # Public API (Synchronous Implementation)
    # -------------------------------------------------------------------------

    def start(self) -> "SyncInterpreter":
        """
        Starts the interpreter by transitioning it to its initial state and
        begins processing events from the queue. It is idempotent; calling
        `start` on an already running interpreter has no effect.

        Unlike the async version, this does not start a background event loop.
        It simply sets the machine to its entry state.

        Returns:
            SyncInterpreter: The interpreter instance for method chaining.
        """
        # 🚦 Check if the interpreter is already running or stopped.
        if self.status != "uninitialized":
            logger.info(
                "⛓️ Interpreter '%s' already running or stopped. Skipping start. 🚧",
                self.id,
            )
            return self

        logger.info("🏁 Starting sync interpreter '%s'...", self.id)
        self.status = "running"

        # ✅ Explicitly notify plugins about the initial transition.
        initial_transition = TransitionDefinition(
            event="___xstate_statemachine_init___",
            config={},
            source=self.machine,
        )
        # 🔌 Iterate through all registered plugins and call their on_interpreter_start method.
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)
            # Pass empty set as from_states for the initial transition
            plugin.on_transition(
                self, set(), self._active_state_nodes, initial_transition
            )

        # ➡️ Enter the machine's initial states.
        self._enter_states([self.machine])
        # 🔄 Process any immediate transient transitions.
        self._process_transient_transitions()

        logger.info(
            "✅ Sync interpreter '%s' started. Current states: %s ✨",
            self.id,
            self.current_state_ids,
        )
        return self

    def stop(self) -> None:
        """
        Stops the interpreter by updating its status.

        This prevents further events from being processed.

        Returns:
            None
        """
        # 🚦 Check if the interpreter is currently running.
        if self.status != "running":
            logger.debug(
                "🛑 Interpreter '%s' is not running. No need to stop. 😴",
                self.id,
            )
            return

        logger.info("🛑 Stopping sync interpreter '%s'...", self.id)
        self.status = "stopped"
        # 🔌 Notify all registered plugins about the interpreter stopping.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)
        logger.info(
            "✅ Sync interpreter '%s' stopped successfully. 🕊️", self.id
        )

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
        """
        Sends an event to the machine for immediate, synchronous processing.

        Events are queued and processed sequentially. If an event is sent while
        the interpreter is already processing another event, it will be added
        to the queue and handled once the current processing cycle completes.

        Args:
            event_or_type (Union[str, Dict[str, Any], Event, DoneEvent, AfterEvent]):
                The event to send. This can be:
                - A `str`: The type of the event, with optional `payload` as keyword arguments.
                - A `dict`: A dictionary representing the event, which must contain a 'type' key.
                - An `Event`, `DoneEvent`, or `AfterEvent` object.
            **payload (Any): Additional keyword arguments representing the event's payload,
                used only if `event_or_type` is a `str`.

        Returns:
            None

        Raises:
            TypeError: If an unsupported event type is passed.
        """
        # 🚦 Check if the interpreter is in a running state before processing events.
        if self.status != "running":
            logger.warning(
                "⚠️ Cannot send event. Interpreter is not running. 🚫"
            )
            return

        event_obj: Union[Event, DoneEvent, AfterEvent]
        # 📋 Normalize the input into an Event object.
        if isinstance(event_or_type, str):
            event_obj = Event(type=event_or_type, payload=payload)
        elif isinstance(event_or_type, dict):
            local_payload = event_or_type.copy()
            event_type = local_payload.pop(
                "type", "UnnamedEvent"
            )  # ℹ️ Default type if not provided.
            event_obj = Event(type=event_type, payload=local_payload)
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            event_obj = event_or_type
        else:
            # ❌ Raise an error for unsupported event types.
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)} 🤷"
            )

        # 📥 Add the event to the processing queue.
        self._event_queue.append(event_obj)
        # 🔒 If already processing, simply return and let the existing loop handle the new event.
        if self._is_processing:
            logger.debug(
                "🔄 Interpreter already processing. Event queued: %s",
                event_obj.type,
            )
            return

        self._is_processing = True
        try:
            # 🔁 Process events from the queue until it's empty.
            while self._event_queue:
                event = self._event_queue.popleft()
                logger.info("➡️ Processing event: '%s' ⚙️", event.type)
                # 🔌 Notify plugins that an event has been received.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)
                # 🎯 Process the event, which may lead to state transitions.
                self._process_event(event)
                # 🔄 After processing an external event, check for any resulting transient transitions.
                self._process_transient_transitions()
        finally:
            # 🔓 Ensure the processing flag is reset even if an error occurs.
            self._is_processing = False
            logger.debug(
                "✅ Event processing cycle completed. Queue empty. 🎉"
            )

    # -------------------------------------------------------------------------
    # Core Synchronous State Transition Logic (Overrides BaseInterpreter)
    # -------------------------------------------------------------------------

    def _process_transient_transitions(self) -> None:
        """
        Continuously processes event-less ("always") transitions until the state stabilizes.

        These transitions occur immediately after state entry or other transitions,
        without requiring an external event. They are typically used for conditional
        logic or immediate state changes based on context.

        Returns:
            None
        """
        logger.debug("🔍 Checking for transient transitions...")
        while True:
            # 👻 Use a dummy event for guard evaluation if needed for "always" transitions.
            transient_event = Event(
                type=""
            )  # Empty type signifies an always transition.
            # 🎯 Find the most appropriate transient transition to take.
            transition = self._find_optimal_transition(transient_event)

            # 🚦 An event-less transition is one with an empty event string.
            if transition and transition.event == "":
                logger.info(
                    "⚡ Processing transient transition: from %s to %s (target: %s) 🚀",
                    transition.source.id,
                    transition.target_str or "self",
                    transition.target_str if transition.target_str else "self",
                )
                # ➡️ Recursively call _process_event to handle the transition logic.
                self._process_event(transient_event)
            else:
                # 🛑 No more transient transitions to take. State has stabilized.
                logger.debug(
                    "✅ No more transient transitions found. State stable. 🧘"
                )
                break

    def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Synchronously finds and executes a transition."""
        transition = self._find_optimal_transition(event)
        if not transition:
            # 🚫 No transition found, nothing to do.
            return

        # ⚡ Execute actions associated with the transition BEFORE state change
        self._execute_actions(transition.actions, event)

        # 🚦 If there is NO target state (internal transition or action-only)
        if not transition.target_str:
            # For internal transitions or transitions without target,
            # we still want to notify plugins of an "identity" transition.
            # The active states do not change, so from_states == to_states
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,  # Current states
                    self._active_state_nodes,  # Same as current states
                    transition,
                )
            logger.debug(
                "✅ Internal transition or action-only completed. State remains: %s",
                self.current_state_ids,
            )
            return  # IMPORTANT: Exit after handling internal transition

        # 🔄 For external transitions that DO change the active state
        from_states_snapshot = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s != domain
        }
        self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )
        # Note: actions were already executed above for all transition types.

        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )
        self._enter_states(path_to_enter)
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                from_states_snapshot,
                self._active_state_nodes,
                transition,
            )

    def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """
        Synchronously enters a list of states.

        This method handles adding states to the active state set, executing
        entry actions, and recursively entering child states for compound
        and parallel states. It also checks for "done" conditions.

        Args:
            states_to_enter (List[StateNode]): A list of `StateNode` objects
                representing the states to be entered.
            event (Optional[Event]): An optional event that triggered the state entry.

        Returns:
            None
        """
        for state in states_to_enter:
            logger.info("➡️ Entering state: '%s' 🟢", state.id)
            # ➕ Add the state to the set of currently active states.
            self._active_state_nodes.add(state)
            # ⚡ Execute entry actions defined for the state.
            self._execute_actions(state.entry, Event(f"entry.{state.id}"))

            # 🎯 Special handling for final states.
            if state.type == "final":
                logger.debug(
                    "🏁 Final state '%s' entered. Checking parent done status.",
                    state.id,
                )
                self._check_and_fire_on_done(state)
            # 📦 Special handling for compound states.
            if (
                state.type == "compound" and state.initial
            ):  # Changed from 'if' to 'if' as original was 'if' for `state.initial in state.states` and original image shows 'if' as well.
                # 🔍 Ensure the initial state is a valid child.
                if state.initial in state.states:
                    logger.debug(
                        "🌲 Entering initial state '%s' for compound state '%s'.",
                        state.initial,
                        state.id,
                    )
                    # ➡️ Recursively enter the initial child state.
                    self._enter_states([state.states[state.initial]])
                else:
                    # ❌ Log an error if the initial state is misconfigured.
                    logger.error(
                        "❌ Initial state '%s' not found for compound state '%s'. Check machine definition. 🐛",
                        state.initial,
                        state.id,
                    )
            # 🤝 Special handling for parallel states.
            elif state.type == "parallel":
                logger.debug(
                    "🌐 Entering all parallel regions for state '%s'.",
                    state.id,
                )
                # ➡️ Recursively enter all child states of a parallel state.
                self._enter_states(list(state.states.values()))

            # ⏰ Schedule any tasks associated with the state (no-op for SyncInterpreter).
            self._schedule_state_tasks(state)
            logger.debug("✅ State '%s' entered successfully.", state.id)

    def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """
        Synchronously exits a list of states.

        This method handles canceling tasks, executing exit actions, and
        removing states from the active state set.

        Args:
            states_to_exit (List[StateNode]): A list of `StateNode` objects
                representing the states to be exited.
            event (Optional[Event]): An optional event that triggered the state exit.

        Returns:
            None
        """
        for state in states_to_exit:
            logger.info("⬅️ Exiting state: '%s' 🔴", state.id)
            # ⏰ Cancel any scheduled tasks for the state (no-op in sync interpreter).
            self._cancel_state_tasks(state)
            # ⚡ Execute exit actions defined for the state.
            self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            # ➖ Remove the state from the set of currently active states.
            self._active_state_nodes.discard(state)
            logger.debug("✅ State '%s' exited successfully.", state.id)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Synchronously checks if an ancestor state is "done" and queues the corresponding
        `done.state` event if all its child states are in their final configurations.

        Args:
            final_state (StateNode): The final state that was just entered,
                triggering the check.

        Returns:
            None
        """
        current_ancestor: Union[StateNode, None] = final_state.parent
        logger.debug(
            "🔍 Checking 'done' status for ancestors of final state '%s'.",
            final_state.id,
        )
        while current_ancestor:
            # 🧐 Check if the current ancestor has an on_done handler and if it's considered done.
            if current_ancestor.on_done and self._is_state_done(
                current_ancestor
            ):
                logger.info(
                    "✅ State '%s' is done, queuing onDone event: '%s' 🥳",
                    current_ancestor.id,
                    f"done.state.{current_ancestor.id}",
                )
                # 📬 Send the `done.state` event, which will be processed in the next cycle.
                self.send(Event(type=f"done.state.{current_ancestor.id}"))
                return  # 🛑 Only fire done.state for the immediate done ancestor.
            current_ancestor = current_ancestor.parent
        logger.debug(
            "No 'done' ancestors found for state '%s'.", final_state.id
        )

    # -------------------------------------------------------------------------
    # Internal Execution and Unsupported Feature Handling (Overrides BaseInterpreter)
    # -------------------------------------------------------------------------

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """
        Synchronously executes a list of action definitions.

        This method iterates through the provided actions, executes the corresponding
        callable from the machine's logic, and specifically raises an error if an
        asynchronous action is encountered, as `SyncInterpreter` does not support them.

        Args:
            actions (List[ActionDefinition]): A list of `ActionDefinition` objects
                to be executed.
            event (Event): The event that triggered these actions.

        Returns:
            None

        Raises:
            ImplementationMissingError: If an action's implementation is not found
                in the machine's logic.
            NotSupportedError: If an attempt is made to execute an asynchronous
                action or to spawn an actor (which is not supported).
        """
        if not actions:
            logger.debug("No actions to execute. Skipping. 🤷")
            return

        for action_def in actions:
            logger.debug(
                "⚡ Executing action: '%s' for event '%s'.",
                action_def.type,
                event.type,
            )
            # 🔌 Notify plugins before executing each action.
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 🚫 Handle unsupported `spawn_` actions.
            if action_def.type.startswith("spawn_"):
                self._spawn_actor(
                    action_def, event
                )  # This will raise NotSupportedError.
                continue  # Should not be reached if _spawn_actor raises.

            # 🔍 Retrieve the callable associated with the action type.
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                # ❌ Raise an error if the action is not implemented.
                logger.error(
                    "❌ Action '%s' not implemented in machine logic. 🛠️",
                    action_def.type,
                )
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' not implemented."
                )

            # 🚫 Validate that the action is not an asynchronous function.
            # We use `hasattr(action_callable, '__await__')` as a general check for awaitables
            # as `asyncio.iscoroutinefunction` might not catch all cases (e.g., async methods
            # of objects that aren't functions directly).
            if (
                hasattr(action_callable, "__await__")
                or hasattr(action_callable, "__call__")
                and getattr(action_callable, "__code__", None)
                and (action_callable.__code__.co_flags & 0x80)
            ):  # noqa
                logger.error(
                    "❌ Action '%s' is async/awaitable and not supported by SyncInterpreter. 🚫",
                    action_def.type,
                )
                raise NotSupportedError(
                    f"Action '{action_def.type}' is async/awaitable and not supported by SyncInterpreter."
                )

            # ✅ Execute the synchronous action.
            action_callable(self, self.context, event, action_def)
            logger.debug(
                "✅ Action '%s' executed successfully. ✨", action_def.type
            )

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> None:
        """
        Raises a `NotSupportedError` as actor spawning is not supported in the
        synchronous interpreter.

        Args:
            action_def (ActionDefinition): The action definition for spawning an actor.
            event (Event): The event that triggered this action.

        Raises:
            NotSupportedError: Always, as actor spawning is not supported.
        """
        logger.error(
            "❌ Actor spawning action '%s' is not supported by SyncInterpreter. 🎭",
            action_def.type,
        )
        raise NotSupportedError(
            "Actor spawning is not supported by SyncInterpreter."
        )

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """
        A no-operation method, as the synchronous interpreter does not manage
        background tasks or timers.

        This method exists to satisfy the `BaseInterpreter` interface.

        Args:
            state (StateNode): The state for which tasks might be cancelled (no-op).

        Returns:
            None
        """
        logger.debug(
            "Skipping state task cancellation for sync interpreter (no-op). 🧹"
        )
        pass  # 🚫 No-op, as the sync interpreter has no background tasks.

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """
        Raises a `NotSupportedError` as `after` transitions (timed events) are
        not supported by the synchronous interpreter.

        Args:
            delay_sec (float): The delay in seconds.
            event (AfterEvent): The after event.
            owner_id (str): The ID of the state node that owns this timer.

        Raises:
            NotSupportedError: Always, as `after` transitions are not supported.
        """
        logger.error(
            "❌ `after` transitions are not supported by SyncInterpreter. ⏰"
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
        """
        Handles invoked services, supporting only synchronous callables.

        If an asynchronous service is provided, a `NotSupportedError` is raised.
        Synchronous services are executed immediately, and their results (or errors)
        are translated into `done.invoke` or `error.platform` events.

        Args:
            invocation (InvokeDefinition): The definition of the invoked service.
            service (Callable[..., Any]): The callable representing the service logic.
            owner_id (str): The ID of the state node that owns this invocation.

        Returns:
            None

        Raises:
            NotSupportedError: If the provided service is an asynchronous function.
        """
        # 🚫 Validate that the service is not an asynchronous function.
        if (
            hasattr(service, "__await__")
            or hasattr(service, "__call__")
            and getattr(service, "__code__", None)
            and (service.__code__.co_flags & 0x80)
        ):  # noqa
            logger.error(
                "❌ Service '%s' is async/awaitable and not supported by SyncInterpreter. 🚫",
                invocation.src,
            )
            raise NotSupportedError(
                f"Service '{invocation.src}' is async/awaitable and not supported by SyncInterpreter."
            )

        logger.info(
            "📞 Invoking sync service '%s' (ID: '%s')... ➡️",
            invocation.src,
            invocation.id,
        )
        try:
            # 🎁 Prepare the event payload for the service.
            invoke_event = Event(
                f"invoke.{invocation.id}", {"input": invocation.input or {}}
            )
            # 🚀 Execute the synchronous service.
            result = service(self, self.context, invoke_event)
            # ✅ Send a done.invoke event with the service's result.
            self.send(
                DoneEvent(
                    f"done.invoke.{invocation.id}",
                    data=result,
                    src=invocation.id,
                )
            )
            logger.info(
                "✅ Sync service '%s' completed successfully. ✨",
                invocation.src,
            )
        except Exception as e:
            # 💥 Handle any exceptions during service execution and send an error.platform event.
            logger.error(
                "💥 Sync service '%s' failed: %s 💔",
                invocation.src,
                e,
                exc_info=True,  # Include traceback in logs for debugging.
            )
            self.send(
                DoneEvent(
                    f"error.platform.{invocation.id}",
                    data=e,
                    src=invocation.id,
                )
            )
