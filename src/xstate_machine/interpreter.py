# src/xstate_machine/interpreter.py
import asyncio
import json
import uuid
from typing import Any, Dict, Generic, List, Optional, Set, Union, overload

from .events import AfterEvent, DoneEvent, Event
from .exceptions import ActorSpawningError, ImplementationMissingError
from .logger import logger
from .models import (
    ActionDefinition,
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

    The Interpreter manages the current state, processes events, executes actions,
    and handles the full state transition lifecycle, including asynchronous
    operations like services, delays, and spawned actors.

    It is designed to be highly extensible through a plugin architecture and
    provides features for testing, visualization, and state persistence.

    Attributes:
        machine (MachineNode): The static machine definition to interpret.
        context (TContext): The current context (extended state) of the machine.
        status (str): The current status of the interpreter ('uninitialized',
                      'running', 'stopped').
        id (str): The unique identifier for this interpreter instance.
        parent (Optional[Interpreter]): A reference to the parent interpreter if
                                        this interpreter was spawned as an actor.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]):
        """Initializes the Interpreter.

        Args:
            machine: The `MachineNode` instance to interpret.
        """
        # 🧍‍♂️ Core Properties
        self.machine: MachineNode[TContext, TEvent] = machine
        self.context: TContext = machine.initial_context.copy()
        self.status: str = "uninitialized"
        self.id: str = machine.id
        self.parent: Optional[Interpreter] = None

        # 🚀 Concurrency & Task Management
        self.task_manager: TaskManager = TaskManager()
        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()
        self._event_loop_task: Optional[asyncio.Task] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        self._actors: Dict[str, "Interpreter"] = {}

        # 🔗 Extensibility
        self._plugins: List[PluginBase] = []

    # -----------------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------------

    @property
    def current_state_ids(self) -> Set[str]:
        """Gets a set of the string IDs of all currently active atomic states.

        This is useful for asserting the machine's current position.

        Returns:
            A set of fully qualified state IDs (e.g., {"machine.group.state"}).
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(self, plugin: PluginBase) -> None:
        """Registers a plugin with the interpreter.

        Plugins hook into the interpreter's lifecycle to add functionality like
        logging, debugging, or persistence.

        Args:
            plugin: An instance of a class that inherits from `PluginBase`.
        """
        self._plugins.append(plugin)
        logger.info(
            f"🔌 Plugin '{type(plugin).__name__}' registered with '{self.id}'."
        )

    async def start(self) -> "Interpreter":
        """Starts the interpreter and its event loop.

        This will transition the machine to its initial state and begin processing
        events. If the interpreter is already running, this is a no-op.

        Returns:
            The interpreter instance, for chaining.
        """
        if self.status != "uninitialized":
            return self

        logger.info(f"🏁 Starting interpreter for machine '{self.id}'...")
        self.status = "running"
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        # 📢 Notify plugins that the interpreter is starting.
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)

        # 🎬 Enter the machine's top-level state to kick things off.
        await self._enter_states([self.machine])
        return self

    async def stop(self) -> None:
        """Stops the interpreter and cleans up all background tasks and actors.

        This is a graceful shutdown process.
        """
        if self.status != "running":
            return

        logger.info(f"🛑 Gracefully stopping interpreter '{self.id}'...")
        self.status = "stopped"

        # 📢 Notify plugins of the shutdown.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        # 👶 Stop all child actors recursively.
        for actor_id, actor in self._actors.items():
            logger.info(f"👨‍👧‍👦 Stopping child actor '{actor_id}'...")
            await actor.stop()

        # 🗑️ Clean up all pending tasks.
        await self.task_manager.cancel_all()
        if self._event_loop_task:
            self._event_loop_task.cancel()
            await asyncio.gather(self._event_loop_task, return_exceptions=True)

        logger.info(f"✅ Interpreter '{self.id}' stopped successfully.")

    @overload
    async def send(self, event_type: str, **payload: Any) -> None:
        """Sends an event to the machine with a string type and keyword arguments.

        This is the most common and user-friendly way to send events.

        Args:
            event_type: The string representing the event type (e.g., "CLICK").
            **payload: Key-value arguments to include in the event payload.

        Example:
            >>> await interpreter.send("USER_UPDATE", name="John", age=30)
        """
        ...

    @overload
    async def send(
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None:
        """Sends a pre-structured event object or dictionary to the machine.

        This is useful for internal events or when the event data is already
        in dictionary form.

        Args:
            event: An `Event` object or a dictionary with a "type" key.

        Example:
            >>> await interpreter.send({"type": "TAKEOFF"})
        """
        ...

    async def send(
        self,
        event_or_type: Union[str, Dict, Event, DoneEvent, AfterEvent],
        **payload: Any,
    ) -> None:
        """Sends an event to the machine's event queue.

        This method is overloaded to provide a flexible and type-safe API. It
        normalizes different calling styles into a standard `Event` object before
        processing.
        """
        event_obj: Union[Event, DoneEvent, AfterEvent]

        #  Normalize the input into a standard Event object
        if isinstance(event_or_type, str):
            event_obj = Event(type=event_or_type, payload=payload)
        elif isinstance(event_or_type, dict):
            local_payload = event_or_type.copy()
            event_type = local_payload.pop("type", "UnnamedEvent")
            event_obj = Event(type=event_type, payload=local_payload)
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            event_obj = event_or_type
        else:
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        # 📨 Add the standardized event to the processing queue.
        await self._event_queue.put(event_obj)

    # -----------------------------------------------------------------------------
    # Snapshot & Persistence API
    # -----------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON serializable snapshot of the interpreter's current state.

        This includes the active state configuration and the machine's context,
        allowing for state restoration.

        Returns:
            A JSON string representing the machine's state.
        """
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
            # Note: A full persistence solution would also need to serialize and
            # restore the state of spawned actors.
        }
        return json.dumps(snapshot, indent=2)

    @classmethod
    def from_snapshot(
        cls, snapshot_str: str, machine: MachineNode[TContext, TEvent]
    ) -> "Interpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a snapshot.

        This method initializes an interpreter and immediately places it in the
        saved state, bypassing the normal initial state transition. The event
        loop is not started automatically.

        Args:
            snapshot_str: The JSON string generated by `get_snapshot()`.
            machine: The `MachineNode` definition corresponding to the snapshot.

        Returns:
            A new `Interpreter` instance restored to the saved state.
        """
        snapshot = json.loads(snapshot_str)
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # 🌳 Restore the active state configuration from the snapshot.
        for state_id in snapshot["state_ids"]:
            node = machine.get_state_by_id(state_id)
            if node:
                # This is a simplified restoration. A full implementation would need
                # to reconstruct the entire state hierarchy for perfect restoration.
                interpreter._active_state_nodes.add(node)

        logger.info(
            f"✅ Interpreter '{machine.id}' restored from snapshot to state: {interpreter.current_state_ids}"
        )
        return interpreter

    # -----------------------------------------------------------------------------
    # Internal Event Loop & State Orchestration
    # -----------------------------------------------------------------------------

    async def _run_event_loop(self) -> None:
        """The main private loop that processes events from the queue."""
        while self.status == "running":
            try:
                # 📥 Wait for the next event from the queue.
                event = await self._event_queue.get()

                # 📢 Notify plugins that an event is about to be processed.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🧠 Process the event to determine the next state.
                await self._process_event(event)
            except asyncio.CancelledError:
                # This is expected during shutdown.
                break
            except Exception as e:
                logger.error(
                    f"💥 Unhandled error in event loop for '{self.id}': {e}",
                    exc_info=True,
                )
        logger.debug(f"Event loop for '{self.id}' has finished.")

    async def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Finds and executes a transition based on the given event.

        This method implements the core state transition algorithm (based on SCXML).

        Args:
            event: The event to process.
        """
        # 1. 🔍 Find the single, optimal transition to take.
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                f"🤷 No transition found for event '{event.type}' in states {self.current_state_ids}"
            )
            return

        # Handle internal (target-less) transitions, which only run actions.
        if not transition.target_str:
            logger.info(
                f"⚡ Performing internal transition on event '{event.type}'"
            )
            await self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        logger.info(
            f"⚡ Transitioning on event '{event.type}' from source '{transition.source.id}'"
        )
        from_states_snapshot = self._active_state_nodes.copy()

        # 2. 🌳 Find the transition domain (Least Common Ancestor).
        domain = self._find_transition_domain(transition)

        # 3. ⬅️ Exit all states from the current configuration up to the domain.
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain)
        }
        await self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )

        # 4. 🎬 Execute the transition's actions.
        await self._execute_actions(transition.actions, event)

        # 5. ➡️ Enter all states from the domain down to the target state(s).
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_target = self._get_path_to_state(target_state, stop_at=domain)
        await self._enter_states(path_to_target)

        # 6. 📢 Notify plugins about the completed transition.
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                from_states_snapshot,
                self._active_state_nodes,
                transition,
            )

    # -----------------------------------------------------------------------------
    # State Management Helpers
    # -----------------------------------------------------------------------------

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the best transition to take, prioritizing deeper states.

        This function is the core of the event processing logic. It searches for
        a valid transition by checking the current atomic states and bubbling
        up their parents.

        ✨ FIX: This version correctly checks all possible transition sources:
        1. On the state's `on` property for regular events.
        2. On the state's `after` property for delayed events.
        3. On the state's `invoke` property for `onDone`/`onError` events.

        Args:
            event: The event being processed.

        Returns:
            The single best `TransitionDefinition` to take, or `None`.
        """
        eligible_transitions: List[TransitionDefinition] = []

        # Iterate through all active states to find matching transitions.
        for state in self._active_state_nodes:
            current: Optional[StateNode] = state
            while current:
                # 1. ✅ Check for standard `on` transitions.
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # 2. ✅ Check for `after` transitions if it's an AfterEvent.
                if isinstance(event, AfterEvent):
                    for delay, transitions in current.after.items():
                        for transition in transitions:
                            if (
                                transition.event == event.type
                                and self._is_guard_satisfied(
                                    transition.guard, event
                                )
                            ):
                                eligible_transitions.append(transition)

                # 3. ✅ Check for `invoke` transitions if it's a DoneEvent.
                if isinstance(event, DoneEvent) and current.invoke:
                    # Check if the event source matches the invoke ID
                    if event.src == current.invoke.id:
                        # Check both onDone and onError transitions
                        invoke_transitions = (
                            current.invoke.on_done + current.invoke.on_error
                        )
                        for transition in invoke_transitions:
                            if (
                                transition.event == event.type
                                and self._is_guard_satisfied(
                                    transition.guard, event
                                )
                            ):
                                eligible_transitions.append(transition)

                # Bubble up to the parent state to check for transitions there.
                current = current.parent

        if not eligible_transitions:
            return None

        # The optimal transition is the one defined on the deepest state node.
        return max(eligible_transitions, key=lambda t: len(t.source.id))

    async def _enter_states(self, states_to_enter: List[StateNode]) -> None:
        """Enters a list of states and executes their entry actions.

        This method is now asynchronous to ensure entry actions complete before
        the logic proceeds, which is critical for `spawn` and `invoke`.

        Args:
            states_to_enter: An ordered list of states to enter, from outermost
                             to innermost.
        """
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug(f"➡️  Entering state: {state.id}")

            # 🎬 Execute entry actions for this state and wait for them to complete.
            await self._execute_actions(
                state.entry, Event(f"entry.{state.id}")
            )

            # 🚀 If it's a compound state, recursively enter its initial child.
            if state.type == "compound" and state.initial:
                await self._enter_states([state.states[state.initial]])
            # 🚀 If it's a parallel state, enter all its child states.
            elif state.type == "parallel":
                await self._enter_states(list(state.states.values()))

            # ⏰ Schedule any `after` or `invoke` tasks for this state.
            self._schedule_state_tasks(state)

    async def _exit_states(self, states_to_exit: List[StateNode]) -> None:
        """Exits a list of states and executes their exit actions.

        This method is now asynchronous to ensure exit actions complete.

        Args:
            states_to_exit: An ordered list of states to exit, from innermost
                            to outermost.
        """
        for state in states_to_exit:
            logger.debug(f"⬅️  Exiting state: {state.id}")

            # 🗑️ Cancel any running tasks associated with this state.
            self._cancel_state_tasks(state)

            # 🎬 Execute exit actions and wait for them to complete.
            await self._execute_actions(state.exit, Event(f"exit.{state.id}"))

            # 🌳 Remove the state from the active configuration.
            self._active_state_nodes.discard(state)

    # -----------------------------------------------------------------------------
    # Action, Service, and Actor Execution
    # -----------------------------------------------------------------------------

    async def _execute_actions(
        self,
        actions: List[ActionDefinition],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> None:
        """Executes a list of actions, handling special cases like 'spawn'.

        Args:
            actions: The list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.
        """
        for action_def in actions:
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            if action_def.type.startswith("spawn_"):
                await self._spawn_actor(action_def, event)
                continue

            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                logger.warning(
                    f"🤔 Action '{action_def.type}' is not implemented. Skipping."
                )
                continue

            logger.debug(f"🎬 Executing action: {action_def.type}")
            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self, self.context, event)
            else:
                action_callable(self, self.context, event)

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """Handles the logic for the 'spawn' action to create a child interpreter.

        Args:
            action_def: The action definition, where the type indicates which
                        machine to spawn (e.g., "spawn_my_child_machine").
            event: The event that triggered the spawn.
        """
        actor_machine_key = action_def.type.replace("spawn_", "")
        actor_machine = self.machine.logic.services.get(actor_machine_key)

        if not isinstance(actor_machine, MachineNode):
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. "
                "The corresponding item in `services` logic is not a valid MachineNode."
            )

        actor_id = f"{self.id}:{actor_machine_key}:{uuid.uuid4()}"
        logger.info(f"👶 Spawning new actor: {actor_id}")

        actor_interpreter = Interpreter(actor_machine)
        actor_interpreter.parent = self
        actor_interpreter.id = actor_id
        await actor_interpreter.start()

        self._actors[actor_id] = actor_interpreter
        self.context.setdefault("actors", {})[actor_id] = actor_interpreter

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Creates background tasks for `after` and `invoke` definitions."""
        for delay, transitions in state.after.items():
            task = asyncio.create_task(
                self._after_timer(
                    delay / 1000.0, AfterEvent(transitions[0].event)
                )
            )
            self.task_manager.add(state.id, task)

        if state.invoke:
            service = self.machine.logic.services.get(state.invoke.src)
            if not service:
                raise ImplementationMissingError(
                    f"Service '{state.invoke.src}' is not implemented."
                )
            task = asyncio.create_task(
                self._invoke_service(state.invoke.id, service)
            )
            self.task_manager.add(state.id, task)

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """Cancels all background tasks associated with a state that is being exited."""
        self.task_manager.cancel_by_owner(state.id)

    async def _after_timer(self, delay_sec: float, event: AfterEvent) -> None:
        """Coroutine that waits for a delay and then sends an event to itself."""
        await asyncio.sleep(delay_sec)
        logger.info(f"🕒 'after' timer fired: {event.type}")
        await self.send(event)

    async def _invoke_service(
        self, service_id: str, service: callable
    ) -> None:
        """Coroutine that runs an invoked service and sends a done/error event."""
        logger.info(f"📞 Invoking service: {service_id}")
        try:
            result = await service(
                self, self.context, Event(f"invoke.{service_id}")
            )
            event = DoneEvent(
                type=f"done.invoke.{service_id}", data=result, src=service_id
            )
            await self.send(event)
        except Exception as e:
            logger.error(f"💥 Service '{service_id}' failed: {e}")
            event = DoneEvent(
                type=f"error.platform.{service_id}", data=e, src=service_id
            )
            await self.send(event)

    # -----------------------------------------------------------------------------
    # Private State Tree Helpers
    # -----------------------------------------------------------------------------

    def _is_guard_satisfied(
        self,
        guard_name: Optional[str],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Checks if a guard condition is met."""
        if not guard_name:
            return True
        guard = self.machine.logic.guards.get(guard_name)
        if not guard:
            raise ImplementationMissingError(
                f"Guard '{guard_name}' is not implemented."
            )
        result = guard(self.context, event)
        logger.info(
            f"🛡️  Evaluating guard '{guard_name}': {'✅' if result else '❌'}"
        )
        return result

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Finds the least common compound ancestor of the source and target states."""
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)
        common_ancestors = source_ancestors.intersection(target_ancestors)
        if not common_ancestors:
            return None
        return max(common_ancestors, key=lambda s: len(s.id))

    def _get_ancestors(self, node: StateNode) -> Set[StateNode]:
        """Gets a set of all ancestors of a node, including the node itself."""
        ancestors = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """Checks if a node is a descendant of another node."""
        if not ancestor:
            return True
        return node.id.startswith(ancestor.id + ".") or node == ancestor

    @staticmethod
    def _get_path_to_state(
        node: StateNode, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Gets the list of states from an ancestor down to a specific node."""
        path = []
        current: Optional[StateNode] = node
        while current and current != stop_at:
            path.append(current)
            current = current.parent
        return list(reversed(path))
