# src/xstate_statemachine/base_interpreter.py

# -----------------------------------------------------------------------------
# 🏛️ Base Interpreter
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

import json
import logging
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Union,
    Callable,
    Type,
    Awaitable,
)

from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
    ImplementationMissingError,
    StateNotFoundError,
    NotSupportedError,
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

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ BaseInterpreter Class Definition
# -----------------------------------------------------------------------------


class BaseInterpreter(Generic[TContext, TEvent]):
    """
    Provides the foundational, mode-agnostic logic for interpreting a state machine.

    This class should not be instantiated directly. It serves as a base for
    concrete synchronous and asynchronous interpreter implementations.

    Attributes:
        machine (MachineNode[TContext, TEvent]): The static machine definition.
        context (TContext): The current extended state (context) of the machine.
        status (str): The operational status: 'uninitialized', 'running', 'stopped'.
        id (str): The unique identifier for this interpreter instance.
        parent (Optional["BaseInterpreter"]): A reference to the parent interpreter.
        _active_state_nodes (Set[StateNode]): The set of currently active states.
        _plugins (List[PluginBase]): A list of registered plugins.
    """

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
    ) -> None:
        """
        Initializes the BaseInterpreter.

        Args:
            machine (MachineNode[TContext, TEvent]): The machine definition to run.
            interpreter_class (Optional[Type["BaseInterpreter"]]): The concrete
                class (e.g., Interpreter or SyncInterpreter) being instantiated.
                Used for snapshot restoration. If not provided, it defaults to
                the class of the current instance.
        """
        logger.info(
            "🧠 Initializing BaseInterpreter for machine '%s'...", machine.id
        )
        # 🧍‍♂️ Core Properties
        self.machine: MachineNode[TContext, TEvent] = machine
        self.context: TContext = machine.initial_context.copy()
        self.status: str = "uninitialized"
        self.id: str = machine.id
        self.parent: Optional[BaseInterpreter] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        self._actors: Dict[str, "BaseInterpreter"] = {}

        # 🔗 Extensibility
        self._plugins: List[PluginBase] = []
        # ✅ Default to self.__class__ for robustness.
        self._interpreter_class: Type["BaseInterpreter"] = (
            interpreter_class or self.__class__
        )

        logger.info(
            "BaseInterpreter '%s' initialized. Status: '%s'.",
            self.id,
            self.status,
        )

    @property
    def current_state_ids(self) -> Set[str]:
        """
        Gets a set of the string IDs of all currently active atomic states.

        For compound states, this returns the IDs of their active atomic
        substates. For parallel states, it returns the IDs of all active
        atomic states within each parallel region.

        Returns:
            Set[str]: A set of fully qualified state IDs (e.g., `{"machine.group.state"}`).
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(self, plugin: PluginBase) -> None:
        """
        Registers a plugin with the interpreter.

        Plugins provide a way to hook into the interpreter's lifecycle events
        (e.g., start, stop, transition) via the Observer Pattern.

        Args:
            plugin (PluginBase): An instance of a class that inherits from `PluginBase`.
        """
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )

    # -------------------------------------------------------------------------
    # Snapshot & Persistence API
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """
        Returns a JSON serializable snapshot of the interpreter's current state.

        This includes the status, context, and active state IDs, allowing the
        machine's state to be saved and later restored.

        Returns:
            str: A JSON formatted string representing the interpreter's snapshot.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
        }
        json_snapshot = json.dumps(snapshot, indent=2)
        logger.debug("Snapshot captured: %s", json_snapshot)
        return json_snapshot

    @classmethod
    def from_snapshot(
        cls: Type["BaseInterpreter"],
        snapshot_str: str,
        machine: MachineNode[TContext, TEvent],
    ) -> "BaseInterpreter[TContext, TEvent]":
        """
        Creates and restores an interpreter instance from a saved snapshot.

        This class method reconstructs an interpreter to the exact state captured
        in the snapshot, which is vital for persistence.

        Args:
            snapshot_str (str): A JSON string from `get_snapshot()`.
            machine (MachineNode[TContext, TEvent]): The machine definition
                that the snapshot corresponds to.

        Returns:
            A new interpreter instance of the correct subclass, restored to the snapshot's state.

        Raises:
            json.JSONDecodeError: If `snapshot_str` is not valid JSON.
            StateNotFoundError: If a state ID in the snapshot is not found in the machine.
        """
        logger.info(
            "🔄 Restoring interpreter from snapshot for machine '%s'...",
            machine.id,
        )
        snapshot = json.loads(snapshot_str)

        # 🏗️ Create a new interpreter instance of the correct concrete class.
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # 🌳 Restore active state nodes.
        interpreter._active_state_nodes.clear()
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
                raise StateNotFoundError(
                    f"State ID '{state_id}' from snapshot not found in machine '{machine.id}'."
                )

        logger.info(
            "✅ Interpreter '%s' restored. States: %s, Status: '%s'",
            interpreter.id,
            interpreter.current_state_ids,
            interpreter.status,
        )
        return interpreter

    # -------------------------------------------------------------------------
    # Abstract Methods for Subclass Implementation
    # -------------------------------------------------------------------------
    # These methods define the interface that concrete interpreters must implement.

    def start(self) -> Union["BaseInterpreter", Awaitable["BaseInterpreter"]]:
        """Starts the interpreter. Must be implemented by subclasses."""
        raise NotImplementedError

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter. Must be implemented by subclasses."""
        raise NotImplementedError

    def send(self, event_or_type: Any, **payload: Any) -> Any:
        """Sends an event for processing. Must be implemented by subclasses."""
        raise NotImplementedError

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> Any:
        """Executes actions. Must be implemented by subclasses."""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Core State Transition Logic (Defined as Async for Awaitable Actions)
    # -------------------------------------------------------------------------

    async def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """
        Finds and executes a transition based on the given event.

        This is the heart of the state transition logic. It finds the optimal
        transition, exits old states, executes transition actions, and enters
        new states.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event to process.
        """
        logger.debug(
            "⚙️  Processing event '%s' for interpreter '%s'.",
            event.type,
            self.id,
        )

        # 🔍 Find the most specific transition for this event.
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                "🤷 No eligible transition for event '%s'. Event ignored.",
                event.type,
            )
            return

        # ⚡ Handle internal transitions (no target state).
        if not transition.target_str:
            await self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # ⚡ Handle external transitions (with a target state).
        from_states_snapshot = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s != domain
        }
        await self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )

        # 🎬 Execute transition actions and enter new states.
        await self._execute_actions(transition.actions, event)
        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )
        await self._enter_states(path_to_enter)

        # 🔔 Notify plugins about the completed transition.
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                from_states_snapshot,
                self._active_state_nodes,
                transition,
            )
        logger.info(
            "✅ Transition complete. Current states: %s",
            self.current_state_ids,
        )

    async def _enter_states(self, states_to_enter: List[StateNode]) -> None:
        """
        Enters a list of states, executing entry actions and scheduling tasks.

        Args:
            states_to_enter (List[StateNode]): An ordered list of states to
                enter, from shallowest to deepest.
        """
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug("➡️  Entering state: '%s'.", state.id)

            await self._execute_actions(
                state.entry, Event(type=f"entry.{state.id}")
            )

            if state.type == "final":
                await self._check_and_fire_on_done(state)

            if state.type == "compound" and state.initial:
                if state.initial in state.states:
                    await self._enter_states([state.states[state.initial]])
                else:
                    logger.error(
                        "❌ Initial state '%s' not found.", state.initial
                    )
            elif state.type == "parallel":
                await self._enter_states(list(state.states.values()))

            self._schedule_state_tasks(state)

    async def _exit_states(self, states_to_exit: List[StateNode]) -> None:
        """
        Exits a list of states, executing exit actions and canceling tasks.

        Args:
            states_to_exit (List[StateNode]): An ordered list of states to
                exit, from deepest to shallowest.
        """
        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            self._cancel_state_tasks(state)
            await self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            self._active_state_nodes.discard(state)

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Checks if an ancestor state is "done" and fires the `onDone` event.

        Args:
            final_state (StateNode): The final state that was just entered.
        """
        current_ancestor = final_state.parent
        while current_ancestor:
            if current_ancestor.on_done:
                is_done = False
                if current_ancestor.type == "compound":
                    active_children = {
                        s
                        for s in self._active_state_nodes
                        if s.parent == current_ancestor
                    }
                    if any(s.type == "final" for s in active_children):
                        is_done = True
                elif current_ancestor.type == "parallel":
                    all_regions_done = all(
                        any(
                            s.type == "final"
                            for s in self._active_state_nodes
                            if self._is_descendant(s, region)
                        )
                        for region in current_ancestor.states.values()
                    )
                    if all_regions_done:
                        is_done = True

                if is_done:
                    # 📨 Send the event. Subclass handles how.
                    await self.send(
                        Event(type=f"done.state.{current_ancestor.id}")
                    )
                    return  # Stop bubbling up.

            current_ancestor = current_ancestor.parent

    # -------------------------------------------------------------------------
    # Shared Logic (implementations deferred to subclasses)
    # -------------------------------------------------------------------------

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the most specific, eligible transition for a given event."""
        eligible_transitions: List[TransitionDefinition] = []
        sorted_active_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: len(s.id),
            reverse=True,
        )
        for state in sorted_active_nodes:
            current: Optional[StateNode] = state
            while current:
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)
                if isinstance(event, AfterEvent):
                    for tl in current.after.values():
                        for t_def in tl:
                            if (
                                t_def.event == event.type
                                and self._is_guard_satisfied(
                                    t_def.guard, event
                                )
                            ):
                                eligible_transitions.append(t_def)
                if isinstance(event, DoneEvent):
                    for inv in current.invoke:
                        if event.src == inv.id:
                            it = inv.on_done + inv.on_error
                            for t_def in it:
                                if (
                                    t_def.event == event.type
                                    and self._is_guard_satisfied(
                                        t_def.guard, event
                                    )
                                ):
                                    eligible_transitions.append(t_def)
                current = current.parent
        if not eligible_transitions:
            return None
        return max(eligible_transitions, key=lambda t: len(t.source.id))

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules tasks for `after` and `invoke`."""
        if state.after:
            for delay_ms, transitions in state.after.items():
                if transitions:
                    self._after_timer(
                        delay_ms / 1000.0,
                        AfterEvent(transitions[0].event),
                        state.id,
                    )
        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            if not service_callable:
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' not implemented."
                )
            self._invoke_service(invocation, service_callable, state.id)

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """Cancels tasks for a state. Must be implemented by subclasses."""
        raise NotImplementedError

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Handles delayed events. Must be implemented by subclasses."""
        raise NotImplementedError

    def _invoke_service(
        self, invocation: InvokeDefinition, service: Callable, owner_id: str
    ) -> None:
        """Handles invoked services. Must be implemented by subclasses."""
        raise NotImplementedError

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> Any:
        """Handles spawning child actors. Must be implemented by subclasses."""
        raise NotImplementedError

    def _is_guard_satisfied(
        self, guard_name: Optional[str], event: Event
    ) -> bool:
        """Checks if a guard condition is met."""
        if not guard_name:
            return True
        guard_callable = self.machine.logic.guards.get(guard_name)
        if not guard_callable:
            raise ImplementationMissingError(
                f"Guard '{guard_name}' not implemented."
            )
        result = guard_callable(self.context, event)
        logger.info(
            "🛡️  Evaluating guard '%s': %s",
            guard_name,
            "✅" if result else "❌",
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
        return (
            max(common_ancestors, key=lambda s: len(s.id))
            if common_ancestors
            else None
        )

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
        """Checks if a node is a descendant of a specified ancestor."""
        if not ancestor:
            return True
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    @staticmethod
    def _get_path_to_state(
        node: StateNode, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Gets the hierarchical path of states from an ancestor down to a node."""
        path = []
        current: Optional[StateNode] = node
        while current and current != stop_at:
            path.append(current)
            current = current.parent
        return list(reversed(path))
