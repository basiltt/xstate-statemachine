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
# fundamentally asynchronous (e.g., `after` timers).
# -----------------------------------------------------------------------------
"""
Provides the synchronous interpreter for running state machines.

The `SyncInterpreter` class manages the state machine's lifecycle in a
blocking fashion. Each call to `.send()` processes an event and any resulting
transitions to completion before returning.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Union, overload

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
        _event_queue (Deque[Union[Event, AfterEvent, DoneEvent]]): A deque used
            to manage the event processing sequence.
        _is_processing (bool): A flag to prevent re-entrant event processing.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]) -> None:
        """
        Initializes a new synchronous Interpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The machine definition
                (`MachineNode` instance) that this interpreter will run.
        """
        # 🤝 Initialize the base interpreter
        super().__init__(machine, interpreter_class=SyncInterpreter)
        logger.info("⛓️ Initializing Synchronous Interpreter... 🚀")

        # ⚙️ Initialize synchronous-specific attributes
        self._event_queue: Deque[Union[Event, AfterEvent, DoneEvent]] = deque()
        self._is_processing: bool = False

        logger.info("Synchronous Interpreter '%s' initialized. 🎉", self.id)

    # -------------------------------------------------------------------------
    # 🌐 Public API
    # -------------------------------------------------------------------------

    def start(self) -> "SyncInterpreter":
        """
        Starts the interpreter and transitions it to its initial state.

        This method is idempotent; calling `start` on an already running or
        stopped interpreter has no effect. Unlike asynchronous interpreters,
        this does not start a background event loop but simply sets the machine
        to its entry state and processes any immediate transitions.

        Returns:
            The interpreter instance, allowing for method chaining.
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

        # ✅ Define the initial pseudo-transition for logging and plugins
        initial_transition = TransitionDefinition(
            event="___xstate_statemachine_init___",
            config={},
            source=self.machine,
        )

        # 🔌 Notify plugins about the interpreter start and initial transition
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)
            # Pass an empty set as from_states for the initial transition
            plugin.on_transition(
                self, set(), self._active_state_nodes, initial_transition
            )

        # ➡️ Enter the machine's initial states.
        self._enter_states([self.machine])
        # 🔄 Process any immediate "always" transitions upon startup.
        self._process_transient_transitions()

        logger.info(
            "✅ Sync interpreter '%s' started. Current states: %s ✨",
            self.id,
            self.current_state_ids,
        )
        return self

    def stop(self) -> None:
        """
        Stops the interpreter, preventing further event processing.

        This method is idempotent; calling it on an already stopped interpreter
        has no effect.
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
        the interpreter is already processing another, it's added to the queue
        and handled once the current processing cycle completes.

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
            logger.warning(
                "⚠️ Cannot send event. Interpreter is not running. 🚫"
            )
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
                f"Unsupported event type passed to send(): {type(event_or_type)} 🤷"
            )

        # 📥 Add the normalized event to the processing queue.
        self._event_queue.append(event_obj)

        # 🔒 If already processing, the event is queued and will be handled
        # by the existing processing loop.
        if self._is_processing:
            logger.debug(
                "🔄 Interpreter already processing. Event queued: %s",
                event_obj.type,
            )
            return

        # 🎬 Start the event processing loop.
        self._is_processing = True
        try:
            # 🔁 Process events from the queue until it's empty.
            while self._event_queue:
                event = self._event_queue.popleft()
                logger.info("➡️ Processing event: '%s' ⚙️", event.type)

                # 🔌 Notify plugins that an event is being processed.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🎯 Find and execute the transition for the current event.
                self._process_event(event)
                # 🔄 Check for any resulting event-less ("always") transitions.
                self._process_transient_transitions()
        finally:
            # 🔓 Reset the processing flag, allowing new events to trigger the loop.
            self._is_processing = False
            logger.debug(
                "✅ Event processing cycle completed. Queue empty. 🎉"
            )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic
    # -------------------------------------------------------------------------

    def _process_event(
        self, event: Union[Event, DoneEvent, AfterEvent]
    ) -> None:
        """
        Execute a single event through the sync interpreter.

        Enhanced state resolution
        =========================
        ▸ Identical to async version for consistent behavior
        ▸ Added comprehensive logging for resolution attempts
        ▸ Handles top-level states defined as direct attributes
        """

        # 1️⃣  Select the winning transition
        transition = self._find_optimal_transition(event)
        if transition is None:
            return

        # 2️⃣  Internal transition → only actions
        if not transition.target_str:
            self._execute_actions(transition.actions, event)
            for plug in self._plugins:
                plug.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 3️⃣  External transition set-up
        snapshot = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s is not domain
        }

        root = self.machine
        parent = transition.source.parent

        # 🔍 Enhanced debugging
        logger.debug("🔄 Resolving state: %s", transition.target_str)
        logger.debug("🌳 Machine root ID: %s", root.id)
        if hasattr(root, "states"):
            logger.debug("🌿 Root states: %s", list(root.states.keys()))
        if hasattr(root, "__dict__"):
            logger.debug("🔑 Root attributes: %s", list(root.__dict__.keys()))

        # 4️⃣  Standard resolution attempts
        attempts = [
            (transition.target_str, transition.source),
            (transition.target_str, parent) if parent else None,
            (transition.target_str, root),
            (f"{root.id}.{transition.target_str}", root),
        ]

        target_state = None
        for tgt, ref in filter(None, attempts):
            try:
                logger.debug(
                    "🔍 Attempting resolution: %s from %s", tgt, ref.id
                )
                target_state = resolve_target_state(tgt, ref)
                transition.target_str = tgt
                logger.debug(
                    "✅ Resolved via standard method: %s", target_state.id
                )
                break
            except StateNotFoundError:
                logger.debug("🚫 Resolution failed: %s from %s", tgt, ref.id)
                continue

        # 5️⃣  Direct attribute lookup (top-level state)
        if target_state is None:
            # Check if it's a direct attribute of root
            if hasattr(root, transition.target_str):
                candidate = getattr(root, transition.target_str)
                # Validate it's a state node (has id and states properties)
                if hasattr(candidate, "id") and (
                    hasattr(candidate, "states")
                    or hasattr(candidate, "is_atomic")
                ):
                    target_state = candidate
                    logger.debug(
                        "✅ Resolved via root attribute: %s", target_state.id
                    )

        # 6️⃣  States dictionary lookup
        if target_state is None and hasattr(root, "states"):
            states_dict = getattr(root, "states", {})
            # Try exact match first
            if transition.target_str in states_dict:
                target_state = states_dict[transition.target_str]
                logger.debug(
                    "✅ Resolved via states dict: %s", target_state.id
                )
            # Then try local name match
            else:
                for state in states_dict.values():
                    if state.id.split(".")[-1] == transition.target_str:
                        target_state = state
                        logger.debug(
                            "✅ Resolved via local name in states: %s",
                            target_state.id,
                        )
                        break

        # 7️⃣  Depth-first tree walk fallback
        if target_state is None:

            def _walk(node):
                yield node
                if hasattr(node, "states"):
                    for child in node.states.values():
                        yield from _walk(child)

            for candidate in _walk(root):
                if candidate.id.split(".")[-1] == transition.target_str:
                    target_state = candidate
                    logger.debug(
                        "✅ Resolved via tree walk: %s", target_state.id
                    )
                    break

        # 🔚 Absolute failure
        if target_state is None:
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
                "🚫 All resolution attempts failed for: %s",
                transition.target_str,
            )
            logger.error("📂 Available states: %s", available)
            raise StateNotFoundError(transition.target_str, root.id)

        # 🔟  Build path & apply SCXML order
        path_to_enter = self._get_path_to_state(target_state, stop_at=domain)

        self._exit_states(
            sorted(states_to_exit, key=lambda s: len(s.id), reverse=True),
            event,
        )
        self._execute_actions(transition.actions, event)
        self._enter_states(path_to_enter, event)

        # 🔟  Update active set & notify plugins
        self._active_state_nodes.difference_update(states_to_exit)
        self._active_state_nodes.update(path_to_enter)
        for plug in self._plugins:
            plug.on_transition(
                self, snapshot, self._active_state_nodes.copy(), transition
            )

    def _process_transient_transitions(self) -> None:
        """
        Continuously processes event-less ("always") transitions.

        These transitions occur immediately after a state entry or another
        transition, allowing for conditional logic without external events.
        The loop continues until no more "always" transitions are available,
        at which point the state is considered stable.
        """
        logger.debug("🔍 Checking for transient ('always') transitions...")
        while True:
            # 👻 Use a dummy event for guard evaluation in "always" transitions.
            transient_event = Event(type="")  # Empty type signifies "always".

            # 🎯 Find the most specific transient transition available.
            transition = self._find_optimal_transition(transient_event)

            # ⚡ An event-less transition is one with an empty event string.
            if transition and transition.event == "":
                logger.info(
                    "⚡ Processing transient transition: from %s to target: %s 🚀",
                    transition.source.id,
                    transition.target_str or "self",
                )
                # 🔄 Recursively call _process_event to handle the transition.
                self._process_event(transient_event)
            else:
                # ✅ No more transient transitions found. State has stabilized.
                logger.debug("🧘 No more transient transitions. State stable.")
                break

    def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """
        Synchronously enters a list of states and executes their entry logic.

        This method handles adding states to the active set, executing entry
        actions, and recursively entering child states for compound/parallel
        states.

        Args:
            states_to_enter: A list of `StateNode` objects to enter.
            event: The optional event that triggered the state entry.
        """
        for state in states_to_enter:
            logger.info("➡️ Entering state: '%s' 🟢", state.id)
            self._active_state_nodes.add(state)
            self._execute_actions(state.entry, Event(f"entry.{state.id}"))

            # 🏁 Handle final state logic.
            if state.type == "final":
                logger.debug(
                    "🏁 Final state '%s' entered. Checking parent 'done' status.",
                    state.id,
                )
                self._check_and_fire_on_done(state)

            # 📦 Handle compound state initial entry.
            if state.type == "compound" and state.initial:
                if state.initial in state.states:
                    logger.debug(
                        "🌲 Entering initial state '%s' for compound state '%s'.",
                        state.initial,
                        state.id,
                    )
                    # ➡️ Recursively enter the initial child state.
                    self._enter_states([state.states[state.initial]])
                else:
                    logger.error(
                        "❌ Initial state '%s' not found for compound state '%s'. Check machine definition. 🐛",
                        state.initial,
                        state.id,
                    )
            # 🤝 Handle parallel state entry.
            elif state.type == "parallel":
                logger.debug(
                    "🌐 Entering all parallel regions for state '%s'.",
                    state.id,
                )
                # ➡️ Recursively enter all child states of the parallel state.
                self._enter_states(list(state.states.values()))

            # ⏰ "Schedule" any tasks (no-op for SyncInterpreter, but part of the template).
            self._schedule_state_tasks(state)
            logger.debug("✅ State '%s' entered successfully.", state.id)

    def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """
        Synchronously exits a list of states and executes their exit logic.

        Handles canceling tasks, executing exit actions, and removing states
        from the active set.

        Args:
            states_to_exit: A list of `StateNode` objects to exit.
            event: The optional event that triggered the state exit.
        """
        for state in states_to_exit:
            logger.info("⬅️ Exiting state: '%s' 🔴", state.id)
            # ⏰ Cancel any scheduled tasks (no-op in sync mode).
            self._cancel_state_tasks(state)
            # ⚡ Execute exit actions.
            self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            # ➖ Remove the state from the active set.
            self._active_state_nodes.discard(state)
            logger.debug("✅ State '%s' exited successfully.", state.id)

    # -------------------------------------------------------------------------
    # 🛠️ Helper Methods
    # -------------------------------------------------------------------------

    def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Checks if an ancestor state is "done" and queues a `done.state` event.

        This is triggered when a final state is entered. It checks if the parent
        state (or any ancestor) has met its completion criteria (e.g., all its
        parallel regions are in final states).

        Args:
            final_state: The final state that was just entered.
        """
        current_ancestor: Optional[StateNode] = final_state.parent
        logger.debug(
            "🔍 Checking 'done' status for ancestors of final state '%s'.",
            final_state.id,
        )
        while current_ancestor:
            # 🧐 Check if the ancestor has an `on_done` handler and is fully completed.
            if current_ancestor.on_done and self._is_state_done(
                current_ancestor
            ):
                done_event_type = f"done.state.{current_ancestor.id}"
                logger.info(
                    "✅ State '%s' is done, queuing onDone event: '%s' 🥳",
                    current_ancestor.id,
                    done_event_type,
                )
                # 📬 Send the `done.state.*` event for the next processing cycle.
                self.send(Event(type=done_event_type))
                return  # 🛑 Only fire the event for the first completed ancestor.

            current_ancestor = current_ancestor.parent

        logger.debug(
            "No 'done' ancestors found for state '%s'.", final_state.id
        )

    # -------------------------------------------------------------------------
    # 🚫 Unsupported Feature Handling (Overrides from BaseInterpreter)
    # -------------------------------------------------------------------------

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """
        Synchronously executes a list of action definitions.

        This method validates that actions are synchronous and raises an error
        if an async action or `spawn` is encountered.

        Args:
            actions: A list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.

        Raises:
            ImplementationMissingError: If an action's implementation is not found.
            NotSupportedError: If an async action or spawn is attempted.
        """
        if not actions:
            return  # 🤔 No actions to execute.

        for action_def in actions:
            logger.debug(
                "⚡ Executing action: '%s' for event '%s'.",
                action_def.type,
                event.type,
            )
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 🚫 Explicitly block `spawn_` actions.
            if action_def.type.startswith("spawn_"):
                self._spawn_actor(
                    action_def, event
                )  # Raises NotSupportedError
                continue  # Should not be reached.

            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                logger.error(
                    "❌ Action '%s' not implemented in machine logic. 🛠️",
                    action_def.type,
                )
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' not implemented."
                )

            # 🧐 Validate that the action is not an async function.
            is_async = hasattr(action_callable, "__await__") or (
                hasattr(action_callable, "__code__")
                and (action_callable.__code__.co_flags & 0x80)  # noqa
            )
            if is_async:
                logger.error(
                    "❌ Action '%s' is async and not supported by SyncInterpreter. 🚫",
                    action_def.type,
                )
                raise NotSupportedError(
                    f"Action '{action_def.type}' is async and not supported by SyncInterpreter."
                )

            # ✅ Execute the synchronous action.
            action_callable(self, self.context, event, action_def)
            logger.debug(
                "✅ Action '%s' executed successfully. ✨", action_def.type
            )

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> None:
        """
        Raises `NotSupportedError` as actor spawning is not supported.

        Args:
            action_def: The definition for the spawn action.
            event: The event that triggered this action.

        Raises:
            NotSupportedError: Always, as this feature is unsupported.
        """
        logger.error(
            "❌ Actor spawning ('%s') is not supported by SyncInterpreter. 🎭",
            action_def.type,
        )
        raise NotSupportedError(
            "Actor spawning is not supported by SyncInterpreter."
        )

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """
        No-op method, as the sync interpreter does not manage background tasks.

        This method exists to satisfy the `BaseInterpreter` interface.

        Args:
            state: The state for which tasks would be cancelled.
        """
        logger.debug(
            "🧹 Skipping state task cancellation for sync interpreter (no-op)."
        )
        # 🤫 Nothing to do here in a synchronous world.

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """
        Raises `NotSupportedError` as `after` transitions are not supported.

        Args:
            delay_sec: The delay in seconds.
            event: The after event.
            owner_id: The ID of the state node owning the timer.

        Raises:
            NotSupportedError: Always, as this feature is unsupported.
        """
        logger.error(
            "❌ Timed 'after' transitions are not supported by SyncInterpreter. ⏰"
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

        Synchronous services are executed immediately. Their results are sent
        as a `done.invoke` event, or errors are sent as `error.platform`.

        Args:
            invocation: The definition of the invoked service.
            service: The callable representing the service logic.
            owner_id: The ID of the state node owning this invocation.

        Raises:
            NotSupportedError: If the provided service is asynchronous.
        """
        # 🧐 Validate that the service is not an async function.
        is_async = hasattr(service, "__await__") or (
            hasattr(service, "__code__")
            and (service.__code__.co_flags & 0x80)  # noqa
        )
        if is_async:
            logger.error(
                "❌ Service '%s' is async and not supported by SyncInterpreter. 🚫",
                invocation.src,
            )
            raise NotSupportedError(
                f"Service '{invocation.src}' is async and not supported by SyncInterpreter."
            )

        logger.info(
            "📞 Invoking sync service '%s' (ID: '%s')... ➡️",
            invocation.src,
            invocation.id,
        )
        # 🔔 Notify plugins that the service is starting.
        for plugin in self._plugins:
            plugin.on_service_start(self, invocation)

        try:
            # 🎁 Prepare the event payload for the service.
            invoke_event = Event(
                f"invoke.{invocation.id}", {"input": invocation.input or {}}
            )
            # 🚀 Execute the synchronous service.
            result = service(self, self.context, invoke_event)
            # ✅ Send a 'done' event with the service's result.
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
            # 🔔 Notify plugins that the service completed.
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, result)

        except Exception as e:
            # 💥 Handle any exceptions and send an 'error' event.
            logger.error(
                "💥 Sync service '%s' failed: %s 💔",
                invocation.src,
                e,
                exc_info=True,  # 📝 Include traceback in logs.
            )
            self.send(
                DoneEvent(
                    f"error.platform.{invocation.id}",
                    data=e,
                    src=invocation.id,
                )
            )
            # 🔔 Notify plugins that the service failed.
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
