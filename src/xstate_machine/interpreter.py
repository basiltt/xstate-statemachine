# src/xstate_machine/interpreter.py
import asyncio
import json
import uuid
import logging
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Union,
    overload,
    Callable,  # ✅ FIX: Added Callable to imports
    Awaitable,  # ✅ FIX: Added Awaitable to imports for consistency with Callable
)

from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
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
from .plugins import PluginBase
from .resolver import resolve_target_state
from .task_manager import TaskManager

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# ⚙️ Interpreter Class Definition
# -----------------------------------------------------------------------------
# This module contains the core state machine engine. The `Interpreter` class
# brings a static `MachineNode` definition to life. It embodies several key
# design patterns:
#
# - State Pattern: The interpreter's behavior is dictated by its current
#   active state configuration.
# - Actor Model: For handling concurrent, communicating processes (`spawn`).
# - Observer Pattern: The plugin system allows external code to subscribe to
#   lifecycle events without being tightly coupled.
# - Strategy Pattern: `MachineLogic` injects the concrete implementations
#   (strategies) for actions, guards, and services.
# -----------------------------------------------------------------------------


class Interpreter(Generic[TContext, TEvent]):
    """
    Brings a state machine definition to life by interpreting its behavior.

    The `Interpreter` class is the core runtime engine of the state machine.
    It manages the machine's current state configuration, processes incoming
    events, executes associated actions and side effects, and orchestrates the
    full state transition lifecycle. This includes handling asynchronous
    operations such as services, delays, and spawned child actors.

    It is designed with extensibility in mind through a plugin architecture,
    allowing for easy integration of features like logging, debugging, or
    state persistence. It also provides methods for testing transitions and
    generating state machine snapshots.

    Attributes:
        machine (MachineNode[TContext, TEvent]): The static machine definition
            (`MachineNode` instance) that this interpreter will execute.
        context (TContext): The current extended state (context) of the machine.
            This is a mutable dictionary holding dynamic data.
        status (str): The current operational status of the interpreter.
            Possible values include 'uninitialized', 'running', 'stopped'.
        id (str): The unique identifier for this specific interpreter instance.
            By default, it inherits the ID of the root `MachineNode`.
        parent (Optional[Interpreter]): A reference to the parent interpreter if
            this interpreter was spawned as a child actor.
            `None` for the root interpreter.
        task_manager (TaskManager): Manages all background asyncio tasks
            (e.g., for `after` delays, `invoke` services) owned by this interpreter.
        _event_queue (asyncio.Queue[Union[Event, AfterEvent, DoneEvent]]): An
            internal asynchronous queue used to buffer incoming events for
            sequential processing by the event loop.
        _event_loop_task (Optional[asyncio.Task]): The asyncio task running the
            main event processing loop (`_run_event_loop`). `None` if not started.
        _active_state_nodes (Set[StateNode]): A set of `StateNode` objects
            representing the currently active state configuration. For compound
            states, this includes the active atomic substates.
        _actors (Dict[str, 'Interpreter']): A dictionary mapping IDs of spawned
            child actors (which are themselves `Interpreter` instances) to their
            respective interpreter objects.
        _plugins (List[PluginBase]): A list of registered `PluginBase` instances
            that will receive lifecycle callbacks.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]):
        """
        Initializes a new Interpreter instance for a given machine definition.

        Args:
            machine (MachineNode[TContext, TEvent]): The compiled machine definition
                (`MachineNode` instance) that this interpreter will run.
        """
        logger.info("Initializing Interpreter for machine '%s'...", machine.id)

        # 🧍‍♂️ Core Properties: These define the fundamental identity and state of the interpreter.
        self.machine: MachineNode[TContext, TEvent] = machine
        self.context: TContext = (
            machine.initial_context.copy()
        )  # Context is a copy to ensure isolation
        self.status: str = "uninitialized"  # Initial status
        self.id: str = machine.id  # Inherit ID from the root machine
        self.parent: Optional[Interpreter] = None  # No parent initially

        # 🚀 Concurrency & Task Management: Components for handling asynchronous operations.
        self.task_manager: TaskManager = (
            TaskManager()
        )  # Manages tasks for 'after' and 'invoke'
        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()  # Queue for incoming events
        self._event_loop_task: Optional[asyncio.Task] = (
            None  # Reference to the main event loop task
        )

        # 🌳 State & Actor Management: Internal tracking of active states and spawned sub-interpreters.
        self._active_state_nodes: Set[StateNode] = (
            set()
        )  # Set of currently active state nodes
        self._actors: Dict[str, "Interpreter"] = (
            {}
        )  # Dictionary of spawned child actors

        # 🔗 Extensibility: List of plugins to notify during lifecycle events.
        self._plugins: List[PluginBase] = []  # List of registered plugins
        logger.info(
            "Interpreter '%s' initialized. Status: '%s'.", self.id, self.status
        )

    # -----------------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------------

    @property
    def current_state_ids(self) -> Set[str]:
        """
        Gets a set of the string IDs of all currently active atomic states.

        For compound states, this property returns the IDs of their active
        atomic substates. For parallel states, it returns the IDs of all
        active atomic states within each parallel region. This is useful for
        asserting the machine's current position and for snapshotting.

        Returns:
            Set[str]: A set of fully qualified state IDs (e.g., `{"machine.group.state"}`).
        """
        # Iterate through all active state nodes and collect IDs of atomic or final states.
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(self, plugin: PluginBase) -> None:
        """
        Registers a plugin with the interpreter.

        Plugins provide a way to extend the interpreter's functionality by
        hooking into its lifecycle events (e.g., start, stop, event received,
        transition, action execution). This adheres to the Observer Pattern.

        Args:
            plugin (PluginBase): An instance of a class that inherits from `PluginBase`.
        """
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )

    async def start(self) -> "Interpreter":
        """
        Starts the interpreter and its main event loop.

        This method initializes the machine by transitioning it to its initial
        state and begins processing events from its queue. If the interpreter
        is already running, calling `start()` again has no effect.

        Returns:
            Interpreter: The interpreter instance itself, allowing for method chaining.
        """
        if self.status != "uninitialized":
            logger.info(
                "🏁 Interpreter '%s' is already running or stopped. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting interpreter for machine '%s'...", self.id)
        self.status = "running"  # Update interpreter status
        # Create and start the main event loop task as a background coroutine
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        # 🔔 Notify all registered plugins that the interpreter is starting
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)

        # 🎬 Enter the machine's top-level initial state to kick things off.
        # This will trigger entry actions, initial child states, and task scheduling.
        await self._enter_states([self.machine])
        logger.info(
            "✅ Interpreter '%s' started. Current states: %s",
            self.id,
            self.current_state_ids,
        )
        return self

    async def stop(self) -> None:
        """
        Stops the interpreter and cleans up all associated background tasks and spawned actors.

        This method performs a graceful shutdown:
        1. Sets the interpreter's status to 'stopped'.
        2. Notifies all registered plugins about the interpreter's shutdown.
        3. Recursively stops any spawned child actors.
        4. Cancels all background tasks managed by the `TaskManager`.
        5. Cancels and awaits the completion of the main event loop task.

        If the interpreter is not currently running, this method does nothing.
        """
        if self.status != "running":
            logger.info(
                "🛑 Interpreter '%s' is not running. Skipping stop.", self.id
            )
            return

        logger.info("🛑 Gracefully stopping interpreter '%s'...", self.id)
        self.status = (
            "stopped"  # Update status to prevent new events from processing
        )

        # 🔔 Notify plugins about the interpreter stopping
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        # 👨‍👧‍👦 Stop all spawned child actors
        for actor_id, actor in self._actors.items():
            logger.info(
                "👨‍👧‍👦 Stopping child actor '%s' associated with '%s'...",
                actor_id,
                self.id,
            )
            await actor.stop()  # Recursively stop child interpreters
        self._actors.clear()  # Clear the actors dictionary

        # 🗑️ Cancel all background tasks (e.g., 'after' timers, 'invoke' services)
        await self.task_manager.cancel_all()

        # ❌ Cancel and await the main event loop task to ensure it finishes cleanly
        if self._event_loop_task:
            self._event_loop_task.cancel()
            # `return_exceptions=True` ensures gather doesn't fail if a task raises CancelledError
            await asyncio.gather(self._event_loop_task, return_exceptions=True)
            self._event_loop_task = None  # Clear task reference

        logger.info("✅ Interpreter '%s' stopped successfully.", self.id)

    @overload
    async def send(self, event_type: str, **payload: Any) -> None:
        """
        Overload: Sends an event to the machine using a string event type and keyword arguments for payload.
        """
        ...

    @overload
    async def send(
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None:
        """
        Overload: Sends a pre-structured event object (dict, Event, DoneEvent, AfterEvent) to the machine.
        """
        ...

    async def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> None:
        """
        Sends an event to the machine's internal event queue for processing.

        This method is the primary way to interact with a running state machine
        by providing it with events that can trigger transitions. It supports
        multiple ways to define an event: as a simple string, a dictionary,
        or a pre-instantiated `Event` object.

        Args:
            event_or_type (Union[str, Dict, Event, DoneEvent, AfterEvent]):
                The event to send. Can be:
                - `str`: The event type (e.g., "USER_CLICK").
                - `Dict[str, Any]`: A dictionary representing the event,
                  must contain a "type" key (e.g., `{"type": "DATA_LOADED", "data": {...}}`).
                - `Event`, `DoneEvent`, `AfterEvent`: A pre-created event object.
            **payload (Any): Optional keyword arguments that will be added
                to the event's payload if `event_or_type` is a string.

        Raises:
            TypeError: If an unsupported type is passed for `event_or_type`.
        """
        event_obj: Union[Event, DoneEvent, AfterEvent]

        if isinstance(event_or_type, str):
            # 📝 Create a new Event object from a string type and keyword args payload
            event_obj = Event(type=event_or_type, payload=payload)
            logger.debug(
                "📥 Event string '%s' converted to Event object with payload: %s",
                event_or_type,
                payload,
            )
        elif isinstance(event_or_type, dict):
            # 📝 Create a new Event object from a dictionary
            local_payload = (
                event_or_type.copy()
            )  # Make a copy to safely pop 'type'
            event_type = local_payload.pop(
                "type", "UnnamedEvent"
            )  # Extract type, default if missing
            event_obj = Event(type=event_type, payload=local_payload)
            logger.debug(
                "📥 Event dict converted to Event object '%s' with payload: %s",
                event_type,
                local_payload,
            )
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            # ✅ Directly use pre-existing Event objects
            event_obj = event_or_type
            logger.debug(
                "📥 Existing Event object of type '%s' received.",
                event_obj.type,
            )
        else:
            # ❌ Raise TypeError for unsupported input types
            logger.error(
                "❌ Unsupported event type passed to send(): %s",
                type(event_or_type),
            )
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        # ➡️ Add the constructed event object to the internal queue for asynchronous processing
        await self._event_queue.put(event_obj)
        logger.debug("Event '%s' enqueued successfully.", event_obj.type)

    # -----------------------------------------------------------------------------
    # Snapshot & Persistence API
    # -----------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """
        Returns a JSON serializable snapshot of the interpreter's current state.

        This snapshot includes the interpreter's status, its current context
        data, and the IDs of all currently active atomic states. This allows
        the machine's state to be saved and later restored.

        Returns:
            str: A JSON formatted string representing the interpreter's snapshot.
        """
        logger.info("📸 Capturing interpreter snapshot for '%s'...", self.id)
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(
                self.current_state_ids
            ),  # Convert set to list for JSON serialization
        }
        json_snapshot = json.dumps(snapshot, indent=2)
        logger.debug("Snapshot captured: %s", json_snapshot)
        return json_snapshot

    @classmethod
    def from_snapshot(
        cls, snapshot_str: str, machine: MachineNode[TContext, TEvent]
    ) -> "Interpreter[TContext, TEvent]":
        """
        Creates and restores an interpreter instance from a previously saved snapshot.

        This class method takes a JSON snapshot string and a `MachineNode`
        definition, then reconstructs an `Interpreter` instance to the exact
        state captured in the snapshot. This is vital for persistence and debugging.

        Args:
            snapshot_str (str): A JSON string representing the interpreter's state,
                                 obtained from `get_snapshot()`.
            machine (MachineNode[TContext, TEvent]): The `MachineNode` instance
                                                      that this interpreter will
                                                      interpret. It must match
                                                      the machine from which
                                                      the snapshot was taken.

        Returns:
            Interpreter[TContext, TEvent]: A new `Interpreter` instance
                                           restored to the snapshot's state.

        Raises:
            json.JSONDecodeError: If `snapshot_str` is not valid JSON.
            StateNotFoundError: If a state ID in the snapshot cannot be found
                                in the provided machine definition.
        """
        logger.info(
            "🔄 Restoring interpreter from snapshot for machine '%s'...",
            machine.id,
        )
        snapshot = json.loads(
            snapshot_str
        )  # Parse the JSON string into a dictionary

        # Create a new interpreter instance
        interpreter = cls(machine)
        # Restore context and status
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # Restore active state nodes by looking them up in the machine definition
        interpreter._active_state_nodes.clear()  # Ensure clean slate before adding
        for state_id in snapshot["state_ids"]:
            node = machine.get_state_by_id(state_id)
            if node:
                interpreter._active_state_nodes.add(node)
                logger.debug("   Restored active state: '%s'", state_id)
            else:
                logger.error(
                    "❌ State ID '%s' from snapshot not found in machine '%s'.",
                    state_id,
                    machine.id,
                )
                # It's critical to raise an error if a state from snapshot is missing
                raise StateNotFoundError(
                    f"State ID '{state_id}' from snapshot not found in machine '{machine.id}'."
                )

        logger.info(
            "✅ Interpreter '%s' restored from snapshot. Current states: %s, Status: '%s'",
            interpreter.id,
            interpreter.current_state_ids,
            interpreter.status,
        )
        return interpreter

    # -----------------------------------------------------------------------------
    # Internal Event Loop & State Orchestration
    # -----------------------------------------------------------------------------

    async def _run_event_loop(self) -> None:
        """
        The main asynchronous event loop for the interpreter.

        This coroutine continuously dequeues events from `_event_queue` and
        passes them to `_process_event` for state transition logic. It is
        designed to run as a background `asyncio.Task`.

        Workflow
        --------
        1. While the interpreter's status is 'running', it attempts to retrieve
           the next event from `self._event_queue`.
        2. Each received event is forwarded to all registered `PluginBase`
           instances via their `on_event_received` method.
        3. The event is then passed to `_process_event` to drive the state machine.
        4. **Cancellation** (`asyncio.CancelledError`): If the task running this
           loop is cancelled (e.g., by `stop()`), this exception is caught, and
           the loop exits gracefully. This is the normal shutdown signal.
        5. **Any other exception** (`Exception`): Any unexpected exception
           occurring within the event loop is considered *fatal*:
           * It is logged at a `CRITICAL` level for immediate attention.
           * The interpreter's `status` is immediately set to 'stopped'.
           * All background tasks (from `after` and `invoke`) and any spawned
             child actors are stopped and cleaned up to prevent resource leaks.
           * The exception is then re-raised, causing the `asyncio.Task` that
             is running this loop to finish in an "errored" state. This allows
             calling code (e.g., test suites) to detect the failure using
             `task.done()` and `task.exception()`.
        """
        logger.debug("Starting event loop for interpreter '%s'...", self.id)
        try:
            while self.status == "running":
                # ⏳ Wait for the next event to arrive in the queue
                event = await self._event_queue.get()
                logger.debug("🔥 Event '%s' dequeued.", event.type)

                # 🔔 Notify plugins that the event was received before processing
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🚀 Drive the state machine: find and execute transitions
                await self._process_event(event)
                self._event_queue.task_done()  # Mark the event as processed

        except asyncio.CancelledError:
            # 🛑 This is the normal shutdown path (e.g., via interpreter.stop())
            logger.debug(
                "🛑 Event loop for '%s' cancelled; exiting cleanly.", self.id
            )

        except (
            Exception
        ) as exc:  # noqa: BLE001 (Blanket except is intentional here for fatal errors)
            # 💥 Anything else is an unexpected and fatal error within the event loop
            logger.critical(
                "💥 Fatal error in event loop for '%s': %s",
                self.id,
                exc,
                exc_info=True,  # Log with traceback
            )
            self.status = "stopped"  # Mark interpreter as stopped

            # 🧹 Clean up resources to prevent leaks after a fatal error
            logger.info(
                "Cleaning up resources after fatal error for '%s'...", self.id
            )
            await self.task_manager.cancel_all()  # Cancel all owned background tasks
            for actor in list(
                self._actors.values()
            ):  # Iterate over a copy to avoid modification during iteration
                await actor.stop()  # Stop all spawned child actors
            self._actors.clear()  # Clear actors dictionary

            # 🚨 Re-raise the exception to signal the failure to the task's caller
            raise

        finally:
            logger.debug("⚓ Event loop coroutine for '%s' exited.", self.id)

    async def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """
        Finds and executes a transition based on the given event.

        This method is the core logic for how the interpreter reacts to events.
        It first attempts to find an optimal transition, then performs exit
        actions on states being left, executes transition actions, and finally
        enters new states, triggering their entry actions and scheduling new tasks.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event to process.
                                                        This can be a regular
                                                        event, a delayed event,
                                                        or a service completion/error event.
        """
        logger.debug(
            "Processing event '%s' for interpreter '%s'.", event.type, self.id
        )

        # 🔍 Find the most specific (optimal) transition that can be taken for this event.
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                "🤷 No eligible transition found for event '%s' in current states %s. Event consumed.",
                event.type,
                self.current_state_ids,
            )
            return

        # Handle internal transitions (transitions without a target)
        if not transition.target_str:
            logger.info(
                "⚡ Performing internal transition (no target change) on event '%s' in state '%s'.",
                event.type,
                transition.source.id,
            )
            # Only execute actions for internal transitions
            await self._execute_actions(transition.actions, event)
            # 🔔 Notify plugins about the internal transition (states don't change)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,  # from_states (unchanged)
                    self._active_state_nodes,  # to_states (unchanged)
                    transition,
                )
            logger.debug("Internal transition for '%s' complete.", event.type)
            return

        # Handle external transitions (transitions with a target)
        logger.info(
            "⚡ Transitioning on event '%s' from source '%s' to target '%s'.",
            event.type,
            transition.source.id,
            transition.target_str,
        )
        # 📸 Snapshot active states before transition for plugin notification
        from_states_snapshot = self._active_state_nodes.copy()

        # 🌳 Determine the transition domain (least common ancestor)
        # States within this domain that are not part of the target path will be exited.
        domain = self._find_transition_domain(transition)

        # ⬅️ Identify and exit states that are descendants of the domain and currently active
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain)
            and s != domain  # Exclude domain itself if it's not a direct exit
        }
        # Sort by depth (deepest first) for correct exit action order
        await self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )
        logger.debug("   Exited states: %s", {s.id for s in states_to_exit})

        # 🎬 Execute actions defined on the transition itself
        await self._execute_actions(transition.actions, event)
        logger.debug("   Executed transition actions.")

        # ➡️ Resolve the absolute target state and determine the path to enter
        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        # Get the path of states to enter, starting from the domain to the target
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )
        # Enter states in order from the domain down to the target
        await self._enter_states(path_to_enter)
        logger.debug("   Entered states: %s", {s.id for s in path_to_enter})

        # 🔔 Notify plugins about the completed transition
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                from_states_snapshot,  # States before the transition
                self._active_state_nodes,  # States after the transition
                transition,
            )
        logger.info(
            "✅ Transition on event '%s' complete. Current states: %s",
            event.type,
            self.current_state_ids,
        )

    # -----------------------------------------------------------------------------
    # State Management Helpers
    # -----------------------------------------------------------------------------

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """
        Finds the most specific and eligible transition to take for a given event.

        This method searches for a transition in the currently active states,
        prioritizing transitions defined on deeper (more specific) states.
        It considers standard `on` transitions, `onDone` transitions (for
        compound/parallel states), `after` transitions (for `AfterEvent`),
        and `invoke` related transitions (for `DoneEvent`). Guards are evaluated.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event triggering the search.

        Returns:
            Optional[TransitionDefinition]: The most specific `TransitionDefinition`
                                           found, or `None` if no eligible transition exists.
        """
        logger.debug(
            "🔍 Searching for optimal transition for event '%s'...", event.type
        )
        eligible_transitions: List[TransitionDefinition] = []

        # Iterate through all active atomic states (deepest first for prioritization)
        # Sorting ensures that transitions defined on deeper states are considered first
        # by the `max` function if their source.id length is longer.
        sorted_active_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: len(s.id),
            reverse=True,
        )

        for state in sorted_active_nodes:
            current: Optional[StateNode] = state
            while current:  # Bubble up through ancestors
                logger.debug(
                    "   Checking state '%s' for transitions to event '%s'.",
                    current.id,
                    event.type,
                )

                # 1. Check for standard `on` transitions defined for this event type.
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        # 🛡️ Evaluate guard before considering the transition eligible
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)
                            logger.debug(
                                "      Found eligible 'on' transition for '%s' in '%s'.",
                                event.type,
                                current.id,
                            )

                # 2. Check for the state's `onDone` transition if a `done.state.*` event occurs.
                # This specifically handles the completion of a compound/parallel state itself.
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)
                        logger.debug(
                            "      Found eligible 'onDone' transition for '%s' in '%s'.",
                            event.type,
                            current.id,
                        )

                # 3. Check for `after` transitions (only for AfterEvent types).
                if isinstance(event, AfterEvent):
                    # `event.type` for an AfterEvent will be something like "after.50.stateId"
                    # We match this full event type.
                    for delay, transitions_list in current.after.items():
                        for transition_def in transitions_list:
                            if (
                                transition_def.event == event.type
                                and self._is_guard_satisfied(
                                    transition_def.guard, event
                                )
                            ):
                                eligible_transitions.append(transition_def)
                                logger.debug(
                                    "      Found eligible 'after' transition for '%s' in '%s'.",
                                    event.type,
                                    current.id,
                                )

                # 4. Check for `invoke` transitions (only for DoneEvent types, which cover done.invoke and error.platform).
                if isinstance(event, DoneEvent):
                    for invocation in current.invoke:
                        # Ensure the event's source matches this invocation's ID
                        if event.src == invocation.id:
                            # Consider both onDone and onError transitions of the invocation
                            invoke_transitions = (
                                invocation.on_done + invocation.on_error
                            )
                            for transition_def in invoke_transitions:
                                if (
                                    transition_def.event == event.type
                                    and self._is_guard_satisfied(
                                        transition_def.guard, event
                                    )
                                ):
                                    eligible_transitions.append(transition_def)
                                    logger.debug(
                                        "      Found eligible 'invoke' related transition for '%s' (from invoke ID '%s') in '%s'.",
                                        event.type,
                                        invocation.id,
                                        current.id,
                                    )

                current = current.parent  # Move up to the parent state

        if not eligible_transitions:
            logger.debug(
                "   No eligible transitions found for event '%s'.", event.type
            )
            return None

        # Prioritize the most specific transition (i.e., defined on the deepest state node).
        # This is achieved by using the length of the state ID as a key for `max`.
        optimal_transition = max(
            eligible_transitions, key=lambda t: len(t.source.id)
        )
        logger.debug(
            "   Optimal transition found: event='%s', source='%s', target='%s'",
            optimal_transition.event,
            optimal_transition.source.id,
            optimal_transition.target_str,
        )
        return optimal_transition

    async def _enter_states(self, states_to_enter: List[StateNode]) -> None:
        """
        Enters a list of states in hierarchical order, executing entry actions and scheduling tasks.

        This recursive method ensures that states are entered from the top-most
        ancestor down to the deepest child. As each state is entered, its entry
        actions are executed, and if it's a compound/parallel state, its initial
        children are also entered. Background tasks (for `after` and `invoke`)
        are scheduled. If a final state is entered, it triggers an `onDone` check
        on its parent.

        Args:
            states_to_enter (List[StateNode]): A list of `StateNode` objects
                                               representing the path of states to enter,
                                               ordered from shallowest to deepest.
        """
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug(
                "➡️  Entering state: '%s'. Current active states: %s",
                state.id,
                self.current_state_ids,
            )

            # 🎬 Execute entry actions for the current state
            await self._execute_actions(
                state.entry,
                Event(
                    type=f"entry.{state.id}"
                ),  # Provide a synthetic event for entry actions
            )
            logger.debug("   Entry actions executed for '%s'.", state.id)

            # 🏁 If the entered state is a final state, check if its parent is now "done".
            if state.type == "final":
                await self._check_and_fire_on_done(state)
                logger.debug(
                    "   '%s' is a final state; checked for parent 'onDone'.",
                    state.id,
                )

            # 🌳 Recursively enter child states based on state type
            if state.type == "compound" and state.initial:
                # For compound states, enter their designated initial child state
                if state.initial in state.states:
                    await self._enter_states([state.states[state.initial]])
                    logger.debug(
                        "   Entering initial state '%s' of compound state '%s'.",
                        state.initial,
                        state.id,
                    )
                else:
                    logger.error(
                        "❌ Initial state '%s' not found in compound state '%s'.",
                        state.initial,
                        state.id,
                    )
            elif state.type == "parallel":
                # For parallel states, enter all of their immediate child regions
                await self._enter_states(list(state.states.values()))
                logger.debug(
                    "   Entering all regions of parallel state '%s'.", state.id
                )

            # ⏰📞 Schedule background tasks (after timers, invoked services) for the entered state
            self._schedule_state_tasks(state)
            logger.debug("   Scheduled tasks for state '%s'.", state.id)

    async def _exit_states(self, states_to_exit: List[StateNode]) -> None:
        """
        Exits a list of states in hierarchical order, executes their exit actions, and cancels related tasks.

        This recursive method ensures that states are exited from the deepest
        child up to the shallowest ancestor in the exit path. As each state
        is exited, its background tasks are cancelled, and its exit actions
        are executed.

        Args:
            states_to_exit (List[StateNode]): A list of `StateNode` objects
                                              representing the path of states to exit,
                                              ordered from deepest to shallowest.
        """
        for state in states_to_exit:
            logger.debug(
                "⬅️  Exiting state: '%s'. Current active states: %s",
                state.id,
                self.current_state_ids,
            )
            self._cancel_state_tasks(
                state
            )  # 🗑️ Cancel any running background tasks for this state
            logger.debug("   Tasks cancelled for '%s'.", state.id)

            # 🎬 Execute exit actions for the current state
            await self._execute_actions(
                state.exit, Event(f"exit.{state.id}")
            )  # Provide a synthetic event for exit actions
            logger.debug("   Exit actions executed for '%s'.", state.id)

            # ❌ Remove the state from the set of active states
            self._active_state_nodes.discard(state)
            logger.debug("   State '%s' removed from active states.", state.id)

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Checks if an ancestor state is now "done" because a child has entered
        a final state, and if so, fires the appropriate `onDone` event.

        This method is called when a `final_state` is entered. It then bubbles
        up through the parent hierarchy to determine if any compound or parallel
        ancestor states have now completed all their required work (i.e.,
        all active children are in a final state for parallel, or the single
        active child is final for compound).

        Args:
            final_state (StateNode): The `StateNode` that has just become a final state.
        """
        logger.debug(
            "Checking 'onDone' for ancestors of final state '%s'.",
            final_state.id,
        )
        # Start checking from the parent of the state that became final.
        current_ancestor = final_state.parent

        while current_ancestor:
            logger.debug(
                "   Evaluating 'onDone' for ancestor state '%s'.",
                current_ancestor.id,
            )
            # We only care about states that have an `onDone` transition defined.
            if current_ancestor.on_done:
                is_ancestor_done = False

                # Logic for Compound States: A compound state is done if its *active* substate is a final state.
                if current_ancestor.type == "compound":
                    # Find all currently active children of this compound ancestor
                    active_children = {
                        s
                        for s in self._active_state_nodes
                        if s.parent == current_ancestor
                    }
                    # If any of these active children is a final state, the compound parent is done
                    if any(s.type == "final" for s in active_children):
                        is_ancestor_done = True
                        logger.debug(
                            "      Compound state '%s' is done because an active child is final.",
                            current_ancestor.id,
                        )

                # Logic for Parallel States: A parallel state is done if *ALL* of its regions are in a final state.
                elif current_ancestor.type == "parallel":
                    all_regions_done = True
                    # Iterate through each defined top-level region (direct child state) of the parallel state.
                    for region_node in current_ancestor.states.values():
                        # Check if there is at least one active state within this specific region
                        # and if that active state is a final state for its region.
                        active_states_in_region = {
                            s
                            for s in self._active_state_nodes
                            if self._is_descendant(
                                s, region_node
                            )  # Check for descendants within this region
                        }
                        # If no active state in this region is final, then this region is NOT done.
                        if not any(
                            s.type == "final" for s in active_states_in_region
                        ):
                            all_regions_done = False
                            logger.debug(
                                "      Parallel region '%s' of '%s' is NOT done.",
                                region_node.id,
                                current_ancestor.id,
                            )
                            break  # One region isn't done, so the parallel state isn't done.

                    if all_regions_done:
                        is_ancestor_done = True
                        logger.debug(
                            "      Parallel state '%s' is done because all its regions are final.",
                            current_ancestor.id,
                        )

                if is_ancestor_done:
                    logger.info(
                        "✅ State '%s' is done. Firing onDone event 'done.state.%s'.",
                        current_ancestor.id,
                        current_ancestor.id,
                    )
                    # Create and send the special internal event for this state being done.
                    # This event will be processed by the main event loop.
                    await self.send(
                        Event(type=f"done.state.{current_ancestor.id}")
                    )

                    # Important: Once we fire an `onDone` event for an ancestor, we stop
                    # bubbling further up. The new `done.state` event will trigger its
                    # own transition cycle, which may, in turn, cause *its* parent to
                    # become done, and so on. This prevents redundant event firing.
                    return

            # Move up to the next ancestor to check it.
            current_ancestor = current_ancestor.parent

    # -----------------------------------------------------------------------------
    # Action, Service, and Actor Execution
    # -----------------------------------------------------------------------------

    async def _execute_actions(
        self,
        actions: List[ActionDefinition],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> None:
        """
        Executes a list of `ActionDefinition` objects.

        This method iterates through the provided actions, logging their execution,
        notifying plugins, and invoking the corresponding callable from `MachineLogic`.
        It also handles the special "spawn_" action type.

        Args:
            actions (List[ActionDefinition]): The list of `ActionDefinition` objects to execute.
            event (Union[Event, AfterEvent, DoneEvent]): The event that triggered these actions.
                                                        The event's payload is accessible to actions.
        """
        if not actions:
            logger.debug("   No actions to execute.")
            return

        logger.debug("🎬 Executing %d actions...", len(actions))
        for action_def in actions:
            # 🔔 Notify plugins before executing each action
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # Handle special 'spawn_' action type
            if action_def.type.startswith("spawn_"):
                logger.debug(
                    "   Special action: spawning actor via '%s'",
                    action_def.type,
                )
                await self._spawn_actor(action_def, event)
                continue  # Move to the next action

            # Retrieve the actual action callable from MachineLogic
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                logger.warning(
                    "🤔 Action '%s' is not implemented in MachineLogic. Skipping execution.",
                    action_def.type,
                )
                continue  # Skip to the next action if not implemented

            logger.debug(
                "   Executing action: '%s' with params: %s",
                action_def.type,
                action_def.params,
            )
            # ⏳ Execute the action callable. Check if it's an async function and await it.
            # Pass interpreter, context, event, and the action_def itself.
            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self, self.context, event, action_def)
            else:
                action_callable(self, self.context, event, action_def)
            logger.debug("   Action '%s' executed.", action_def.type)

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """
        Handles the logic for the special 'spawn_' action to create a child interpreter.

        This method extracts the machine key from the action definition, looks
        up the corresponding `MachineNode` in `MachineLogic.services`, creates
        a new `Interpreter` instance for it, links it as a child, and starts it.
        The spawned actor's interpreter is also stored in the parent's context.

        Args:
            action_def (ActionDefinition): The `ActionDefinition` for the spawn action
                                           (e.g., `type="spawn_childMachine"`).
            event (Event): The event that triggered this spawn action.
                            Its payload can potentially be used as input for the actor.

        Raises:
            ActorSpawningError: If the `src` specified for spawning is not a valid `MachineNode`.
        """
        logger.info(
            "👶 Attempting to spawn actor for action: '%s'", action_def.type
        )
        actor_machine_key = action_def.type.replace(
            "spawn_", ""
        )  # Extract machine key (e.g., "childMachine")

        # Lookup the machine definition in services (services can also contain other machines)
        actor_machine = self.machine.logic.services.get(actor_machine_key)

        # 🧪 Validate that the found service is indeed a MachineNode
        if not isinstance(actor_machine, MachineNode):
            logger.error(
                "❌ Cannot spawn '%s'. The corresponding item in `services` logic is not a valid MachineNode. Type: %s",
                actor_machine_key,
                type(actor_machine),
            )
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. "
                + "The corresponding item in `services` logic is not a valid MachineNode."
            )

        # Generate a unique ID for the new actor instance
        actor_id = f"{self.id}:{actor_machine_key}:{uuid.uuid4()}"
        logger.info("👶 Spawning new actor interpreter: '%s'", actor_id)

        # Create and configure the new child interpreter
        actor_interpreter = Interpreter(actor_machine)
        actor_interpreter.parent = self  # Set the parent reference
        actor_interpreter.id = actor_id  # Assign the unique ID

        # 🏁 Start the child interpreter
        await actor_interpreter.start()

        # Store the spawned actor in the parent's internal actors dict and context
        self._actors[actor_id] = actor_interpreter
        self.context.setdefault("actors", {})[
            actor_id
        ] = actor_interpreter  # Store in context under "actors" key

        logger.info(
            "✅ Actor '%s' spawned successfully and added to context.",
            actor_id,
        )

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """
        Creates and schedules background asyncio tasks for `after` delays and `invoke` services
        associated with the given state.

        Tasks are added to the `TaskManager` and owned by the state's ID,
        allowing for easy cancellation when the state is exited.

        Args:
            state (StateNode): The state node for which to schedule tasks.
        """
        logger.debug("⏰📞 Scheduling tasks for state '%s'...", state.id)

        # Schedule tasks for `after` delays
        for delay_ms, transitions in state.after.items():
            # For 'after' transitions, only the first transition in the list is typically used
            # to derive the event type, as 'after' usually implies a single outcome.
            if transitions:
                event_type = transitions[
                    0
                ].event  # The specific 'after.delay.stateId' event type
                task = asyncio.create_task(
                    self._after_timer(
                        delay_ms / 1000.0, AfterEvent(event_type)
                    )
                )
                self.task_manager.add(state.id, task)
                logger.debug(
                    "   Scheduled 'after' task for '%s' (delay: %dms).",
                    state.id,
                    delay_ms,
                )
            else:
                logger.warning(
                    "⚠️ State '%s' has 'after' defined for %dms but no transitions.",
                    state.id,
                    delay_ms,
                )

        # Schedule tasks for `invoke` services
        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            if not service_callable:
                logger.error(
                    "❌ Service '%s' referenced by invoke ID '%s' in state '%s' is not implemented.",
                    invocation.src,
                    invocation.id,
                    state.id,
                )
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' is not implemented."
                )

            # Create a task for the invoked service
            task = asyncio.create_task(
                self._invoke_service(invocation, service_callable)
            )
            self.task_manager.add(
                state.id, task
            )  # Add task to manager, owned by the state
            logger.debug(
                "   Scheduled 'invoke' task for service '%s' (ID: '%s') for state '%s'.",
                invocation.src,
                invocation.id,
                state.id,
            )

        logger.debug("Scheduled tasks for state '%s' complete.", state.id)

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """
        Cancels all background tasks associated with a specific state.

        This method is typically called when a state is being exited to
        clean up any pending `after` timers or ongoing `invoke` services
        that were started when the state was entered.

        Args:
            state (StateNode): The state node whose tasks should be cancelled.
        """
        logger.debug("🗑️  Cancelling tasks for state '%s'...", state.id)
        self.task_manager.cancel_by_owner(state.id)
        logger.debug(
            "Tasks for state '%s' cancelled via TaskManager.", state.id
        )

    async def _after_timer(self, delay_sec: float, event: AfterEvent) -> None:
        """
        A coroutine that waits for a specified delay and then sends a delayed event to the interpreter.

        This function is executed as a background task. It's responsible for
        implementing the `after` transition logic by timing out and then
        queuing a specific `AfterEvent`.

        Args:
            delay_sec (float): The delay duration in seconds.
            event (AfterEvent): The `AfterEvent` object to send to the interpreter
                                once the delay has passed.
        """
        logger.debug(
            "🕒 Starting 'after' timer for event '%s' with delay %.2f seconds.",
            event.type,
            delay_sec,
        )
        try:
            await asyncio.sleep(delay_sec)
            logger.info(
                "🕒 'after' timer fired: '%s'. Sending event to interpreter.",
                event.type,
            )
            await self.send(
                event
            )  # Send the delayed event back to the interpreter's queue
        except asyncio.CancelledError:
            logger.debug(
                "🚫 'after' timer for event '%s' was cancelled.", event.type
            )
        except Exception as e:
            logger.error(
                "❌ Error in 'after' timer for event '%s': %s",
                event.type,
                e,
                exc_info=True,
            )

    async def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Awaitable[Any]],
    ) -> None:
        """
        A coroutine that runs an invoked service and sends a `DoneEvent` or `ErrorEvent`
        back to the interpreter upon completion or failure.

        This function acts as a wrapper for user-defined asynchronous services.
        It handles the execution, captures the result or exception, and
        communicates it back to the state machine via specialized events.

        Args:
            invocation (InvokeDefinition): The `InvokeDefinition` object containing
                                           details about the service invocation.
            service (Callable[..., Awaitable[Any]]): The actual callable (async function)
                                                  implementing the service logic.
        """
        # ✅ FIX: Use invocation.source.id which is now correctly stored in InvokeDefinition
        logger.info(
            "📞 Invoking service '%s' (ID: '%s') for state '%s'...",
            invocation.src,
            invocation.id,
            invocation.source.id,
        )
        try:
            # Create a synthetic event for the service to receive, if it needs input
            invoke_event = Event(
                type=f"invoke.{invocation.id}",
                payload=(
                    {"input": invocation.input} if invocation.input else {}
                ),
            )

            # ⏳ Await the execution of the actual service logic
            result = await service(self, self.context, invoke_event)

            # ✅ On successful completion, create and send a DoneEvent
            done_event = DoneEvent(
                type=f"done.invoke.{invocation.id}",
                data=result,
                src=invocation.id,
            )
            await self.send(done_event)
            logger.info(
                "✅ Service '%s' (ID: '%s') completed successfully. Result sent.",
                invocation.src,
                invocation.id,
            )

        except asyncio.CancelledError:
            logger.debug(
                "🚫 Service invocation '%s' (ID: '%s') was cancelled.",
                invocation.src,
                invocation.id,
            )
        except Exception as e:
            # 💥 On failure, create and send an ErrorEvent
            logger.error(
                "💥 Service '%s' (ID: '%s') failed: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            error_event = DoneEvent(  # DoneEvent is reused for errors by convention, with type 'error.platform'
                type=f"error.platform.{invocation.id}",
                data=e,  # The exception object itself can be part of the data
                src=invocation.id,
            )
            await self.send(error_event)

    # -----------------------------------------------------------------------------
    # Private State Tree Helpers
    # -----------------------------------------------------------------------------

    def _is_guard_satisfied(
        self,
        guard_name: Optional[str],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """
        Checks if a guard condition is met.

        A guard is a boolean-returning function that must evaluate to `True`
        for a transition to be taken.

        Args:
            guard_name (Optional[str]): The name of the guard function
                                        as defined in `MachineLogic.guards`.
                                        If `None`, the guard is considered
                                        satisfied (no guard condition).
            event (Union[Event, AfterEvent, DoneEvent]): The event that
                                                        triggered the potential
                                                        transition. Its payload
                                                        is passed to the guard.

        Returns:
            bool: `True` if the guard is satisfied or not defined, `False` otherwise.

        Raises:
            ImplementationMissingError: If a `guard_name` is specified but
                                        no corresponding implementation is found
                                        in `MachineLogic.guards`.
        """
        if not guard_name:
            logger.debug(
                "   No guard specified. Guard is satisfied by default."
            )
            return True  # No guard means the condition is always met

        guard_callable = self.machine.logic.guards.get(guard_name)
        if not guard_callable:
            logger.error(
                "❌ Guard '%s' is not implemented in MachineLogic.", guard_name
            )
            raise ImplementationMissingError(
                f"Guard '{guard_name}' is not implemented."
            )

        # 🛡️ Execute the guard callable with current context and event
        result = guard_callable(self.context, event)
        logger.info(
            "🛡️  Evaluating guard '%s': %s",
            guard_name,
            "✅ True" if result else "❌ False",
        )
        return result

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """
        Finds the least common compound ancestor (LCCA) of the transition's source and target states.

        This "domain" node represents the highest common state in the hierarchy
        that must be exited for the transition to occur. States outside this domain
        and not in the path to the target will be exited.

        Args:
            transition (TransitionDefinition): The transition for which to find the domain.

        Returns:
            Optional[StateNode]: The `StateNode` representing the LCCA, or `None` if
                                 the source and target share no common ancestor
                                 (which should not happen in a well-formed machine with a root).
        """
        logger.debug(
            "🌳 Finding transition domain for transition from '%s' to '%s'.",
            transition.source.id,
            transition.target_str,
        )

        # Resolve the absolute target state node
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )

        # Get all ancestors for both source and target, including themselves
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)

        # Find common ancestors
        common_ancestors = source_ancestors.intersection(target_ancestors)

        if not common_ancestors:
            logger.warning(
                "⚠️ No common ancestors found between source '%s' and target '%s'.",
                transition.source.id,
                target_state.id,
            )
            return None

        # The domain is the deepest (longest ID) common ancestor
        domain = max(common_ancestors, key=lambda s: len(s.id))
        logger.debug("   Transition domain found: '%s'.", domain.id)
        return domain

    def _get_ancestors(self, node: StateNode) -> Set[StateNode]:
        """
        Gets a set of all ancestors of a given state node, including the node itself.

        Args:
            node (StateNode): The starting state node.

        Returns:
            Set[StateNode]: A set containing the node itself and all its parent nodes
                            up to the root of the machine.
        """
        ancestors = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """
        Checks if a given state `node` is a descendant of a specified `ancestor` state.

        A node is considered a descendant if its fully qualified ID starts with
        the ancestor's ID followed by a dot, or if the node itself *is* the ancestor.

        Args:
            node (StateNode): The potential descendant node.
            ancestor (Optional[StateNode]): The potential ancestor node. If `None`,
                                            all nodes are considered descendants (base case).

        Returns:
            bool: `True` if `node` is a descendant of `ancestor` (or `node` is `ancestor`),
                  `False` otherwise.
        """
        if not ancestor:
            return True  # If there's no specific ancestor, any node is considered a "descendant" of the implicit root.

        # Check if node's ID starts with ancestor's ID + '.', or if node IS the ancestor.
        # This handles direct children and deeply nested descendants.
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    @staticmethod
    def _get_path_to_state(
        node: StateNode, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """
        Gets the hierarchical path of states from a given `stop_at` ancestor down to a specific `node`.

        This utility is crucial for correctly entering a new state configuration
        by ensuring all intervening parent states are entered in the correct order.

        Args:
            node (StateNode): The target state node for which to find the path.
            stop_at (Optional[StateNode]): An optional ancestor node. The path will
                                           start *after* this node and go down to `node`.
                                           If `None`, the path will start from the machine's root.

        Returns:
            List[StateNode]: A list of `StateNode` objects representing the path
                             from `stop_at`'s child down to `node`, inclusive.
                             The list is ordered from shallowest to deepest.
        """
        path = []
        current: Optional[StateNode] = node
        # Traverse upwards from the node until the stop_at ancestor or the root is reached
        while current and current != stop_at:
            path.append(current)
            current = current.parent

        # The path is built in reverse order (node -> parent -> ...). Reverse it
        # to get the correct entry order (ancestor's child -> ... -> node).
        return list(reversed(path))
