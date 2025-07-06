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

        for plugin in self._plugins:
            plugin.on_interpreter_start(self)

        # 🎬 Enter the machine's top-level state to kick things off.
        await self._enter_states([self.machine])
        return self

    async def stop(self) -> None:
        """Stops the interpreter and cleans up all background tasks and actors."""
        if self.status != "running":
            return

        logger.info(f"🛑 Gracefully stopping interpreter '{self.id}'...")
        self.status = "stopped"

        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        for actor_id, actor in self._actors.items():
            logger.info(f"👨‍👧‍👦 Stopping child actor '{actor_id}'...")
            await actor.stop()

        await self.task_manager.cancel_all()
        if self._event_loop_task:
            self._event_loop_task.cancel()
            await asyncio.gather(self._event_loop_task, return_exceptions=True)

        logger.info(f"✅ Interpreter '{self.id}' stopped successfully.")

    @overload
    async def send(self, event_type: str, **payload: Any) -> None:
        """Sends an event to the machine with a string type and keyword arguments."""
        ...

    @overload
    async def send(
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None:
        """Sends a pre-structured event object or dictionary to the machine."""
        ...

    async def send(
        self,
        event_or_type: Union[str, Dict, Event, DoneEvent, AfterEvent],
        **payload: Any,
    ) -> None:
        """Sends an event to the machine's event queue."""
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
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        await self._event_queue.put(event_obj)

    # -----------------------------------------------------------------------------
    # Snapshot & Persistence API
    # -----------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON serializable snapshot of the interpreter's current state."""
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
        }
        return json.dumps(snapshot, indent=2)

    @classmethod
    def from_snapshot(
        cls, snapshot_str: str, machine: MachineNode[TContext, TEvent]
    ) -> "Interpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a snapshot."""
        snapshot = json.loads(snapshot_str)
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        for state_id in snapshot["state_ids"]:
            node = machine.get_state_by_id(state_id)
            if node:
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
                event = await self._event_queue.get()
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)
                await self._process_event(event)
            except asyncio.CancelledError:
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
        """Finds and executes a transition based on the given event."""
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                f"🤷 No transition found for event '{event.type}' in states {self.current_state_ids}"
            )
            return

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

        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain)
        }
        await self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )

        await self._execute_actions(transition.actions, event)

        target_state = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_target = self._get_path_to_state(target_state, stop_at=domain)
        await self._enter_states(path_to_target)

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
        """Finds the best transition to take from all possible sources."""
        eligible_transitions: List[TransitionDefinition] = []

        for state in self._active_state_nodes:
            current: Optional[StateNode] = state
            while current:
                # 1. Check for standard `on` transitions.
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # ✨ FIX: Check for the state's `onDone` transition if a `done.state.*` event occurs.
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)

                # 2. Check for `after` transitions.
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

                # 3. Check for `invoke` transitions.
                if isinstance(event, DoneEvent):
                    for invocation in current.invoke:
                        if event.src == invocation.id:
                            invoke_transitions = (
                                invocation.on_done + invocation.on_error
                            )
                            for transition in invoke_transitions:
                                if (
                                    transition.event == event.type
                                    and self._is_guard_satisfied(
                                        transition.guard, event
                                    )
                                ):
                                    eligible_transitions.append(transition)

                current = current.parent

        if not eligible_transitions:
            return None

        return max(eligible_transitions, key=lambda t: len(t.source.id))

    async def _enter_states(self, states_to_enter: List[StateNode]) -> None:
        """Enters a list of states, executes entry actions, and schedules tasks."""
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug(f"➡️  Entering state: {state.id}")

            await self._execute_actions(
                state.entry, Event(type=f"entry.{state.id}")
            )

            # ✨ FIX: After entering a state, check if its entry completes a parent state.
            # This is the trigger for the onDone logic.
            if state.type == "final":
                await self._check_and_fire_on_done(state)

            # Recurse for nested states.
            if state.type == "compound" and state.initial:
                await self._enter_states([state.states[state.initial]])
            elif state.type == "parallel":
                await self._enter_states(list(state.states.values()))

            self._schedule_state_tasks(state)

    async def _exit_states(self, states_to_exit: List[StateNode]) -> None:
        """Exits a list of states and executes their exit actions."""
        for state in states_to_exit:
            logger.debug(f"⬅️  Exiting state: {state.id}")
            self._cancel_state_tasks(state)
            await self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            self._active_state_nodes.discard(state)

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Checks if an ancestor state is now "done" because a child has entered
        a final state, and if so, fires the appropriate `onDone` event.

        This method bubbles up from the parent of the newly entered final state
        to check all relevant ancestors.

        Args:
            final_state: The state that has just become final.
        """
        # Start checking from the parent of the state that became final.
        current = final_state.parent

        while current:
            # We only care about states that have an onDone transition defined.
            if current.on_done:
                is_done = False

                # A compound state is done if its active substate is a final state.
                if current.type == "compound":
                    active_children = {
                        s
                        for s in self._active_state_nodes
                        if s.parent == current
                    }
                    if any(s.type == "final" for s in active_children):
                        is_done = True

                # A parallel state is done if ALL of its regions are in a final state.
                elif current.type == "parallel":
                    all_regions_done = True
                    # Iterate through each defined region (child state) of the parallel state.
                    for region in current.states.values():
                        # Check if there is an active state within this region that is final.
                        active_states_in_region = {
                            s
                            for s in self._active_state_nodes
                            if self._is_descendant(s, region)
                        }
                        if not any(
                            s.type == "final" for s in active_states_in_region
                        ):
                            all_regions_done = False
                            break  # One region isn't done, so the parallel state isn't done.

                    if all_regions_done:
                        is_done = True

                if is_done:
                    logger.info(
                        f"✅ State '{current.id}' is done. Firing onDone event."
                    )
                    # Create and send the special event for this state being done.
                    await self.send(Event(type=f"done.state.{current.id}"))

                    # Once we fire an onDone event, we stop bubbling. The new event
                    # will trigger its own transition cycle.
                    return

            # Move up to the next ancestor to check it.
            current = current.parent

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
            # ✨ FIX: Pass the `action_def` itself as the fourth argument to the
            # action callable. This prevents mutating the immutable Event object.
            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self, self.context, event, action_def)
            else:
                action_callable(self, self.context, event, action_def)

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """Handles the logic for the 'spawn' action to create a child interpreter."""
        actor_machine_key = action_def.type.replace("spawn_", "")
        actor_machine = self.machine.logic.services.get(actor_machine_key)
        if not isinstance(actor_machine, MachineNode):
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. "
                + "The corresponding item in `services` logic is not a valid MachineNode."
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
        for invocation in state.invoke:
            service = self.machine.logic.services.get(invocation.src)
            if not service:
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' is not implemented."
                )
            task = asyncio.create_task(
                self._invoke_service(invocation, service)
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
        self, invocation: InvokeDefinition, service: callable
    ) -> None:
        """Coroutine that runs an invoked service and sends a done/error event."""
        logger.info(
            f"📞 Invoking service: {invocation.src} (id: {invocation.id})"
        )
        try:
            invoke_event = Event(
                type=f"invoke.{invocation.id}",
                payload={"input": invocation.input},
            )
            result = await service(self, self.context, invoke_event)
            done_event = DoneEvent(
                type=f"done.invoke.{invocation.id}",
                data=result,
                src=invocation.id,
            )
            await self.send(done_event)
        except Exception as e:
            logger.error(f"💥 Service '{invocation.id}' failed: {e}")
            error_event = DoneEvent(
                type=f"error.platform.{invocation.id}",
                data=e,
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
