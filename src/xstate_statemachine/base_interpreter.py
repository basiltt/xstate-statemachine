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
import copy
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
        self.context: TContext = copy.deepcopy(machine.initial_context)
        self.status: str = "uninitialized"
        self.id: str = machine.id
        self.parent: Optional[BaseInterpreter] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        self._actors: Dict[str, "BaseInterpreter"] = {}

        # 🔗 Extensibility
        self._plugins: List[PluginBase] = []
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
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(self, plugin: PluginBase) -> "BaseInterpreter":
        """
        Registers a plugin with the interpreter.
        """
        # ✅ FIX: Return `self` to make this method chainable.
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )
        return self

    # -------------------------------------------------------------------------
    # Snapshot & Persistence API
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """
        Returns a JSON serializable snapshot of the interpreter's current state.
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
        """
        logger.info(
            "🔄 Restoring interpreter from snapshot for machine '%s'...",
            machine.id,
        )
        snapshot = json.loads(snapshot_str)

        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

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
                raise StateNotFoundError(target=state_id)

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
        """
        logger.debug(
            "⚙️  Processing event '%s' for interpreter '%s'.",
            event.type,
            self.id,
        )

        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                "🤷 No eligible transition for event '%s'. Event ignored.",
                event.type,
            )
            return

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

        await self._execute_actions(transition.actions, event)
        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )
        await self._enter_states(path_to_enter)

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
        """
        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            await self._cancel_state_tasks(state)
            await self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            self._active_state_nodes.discard(state)

    def _is_state_done(self, state_node: StateNode) -> bool:
        """
        Returns ``True`` when *state_node* has reached its “done” condition,
        walking the hierarchy recursively so that nested finals correctly
        bubble up.

        ─ Final   : always done.
        ─ Compound : its single active child is final **or** already done.
        ─ Parallel : every region has at least one active descendant that is
                     final **or** done.
        """
        # 1 – final states
        if state_node.is_final:
            return True

        # collect the *direct* active children of this state
        direct_active = [
            s for s in self._active_state_nodes if s.parent == state_node
        ]

        if state_node.type == "compound":
            if not direct_active:
                return False
            child = direct_active[0]  # exactly one for compounds
            return child.is_final or self._is_state_done(child)

        if state_node.type == "parallel":
            for region in state_node.states.values():
                # active leaves whose ancestry contains *region*
                active_desc = [
                    s
                    for s in self._active_state_nodes
                    if self._is_descendant(s, region)
                ]
                if not active_desc:
                    return False
                if not any(
                    d.is_final or self._is_state_done(d) for d in active_desc
                ):
                    return False
            return True

        # atomic / history (non-final)
        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """
        Checks if an ancestor state is "done" and fires the `onDone` event.
        """
        current_ancestor = final_state.parent
        while current_ancestor:
            if current_ancestor.on_done and self._is_state_done(
                current_ancestor
            ):
                logger.info(
                    "✅ State '%s' is done, firing onDone event.",
                    current_ancestor.id,
                )
                # The key is to await the send here, which allows the async interpreter
                # to handle the event correctly. The SyncInterpreter will override this.
                await self.send(
                    Event(type=f"done.state.{current_ancestor.id}")
                )
                return

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

        is_transient_check = not (
            event.type.startswith("done.")
            or event.type.startswith("error.")
            or event.type.startswith("after.")
        )

        for state in sorted_active_nodes:
            current: Optional[StateNode] = state
            while current:
                # Regular event transitions
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # Event-less transitions
                if is_transient_check and "" in current.on:
                    for transition in current.on[""]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # onDone transitions
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)

                # after transitions
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

                # invoke onDone/onError transitions
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
        """
        Schedules `after` and `invoke` tasks for a state.

        This method is called upon state entry. It iterates through the state's
        `after` and `invoke` definitions and delegates them to the appropriate
        handler (`_after_timer` or `_invoke_service`), which must be implemented
        by the concrete interpreter subclass.
        """
        # Schedule 'after' events
        for delay, transitions in state.after.items():
            for t_def in transitions:
                delay_sec = float(delay) / 1000.0
                # FIX: Do not pass owner_id to the event constructor.
                after_event = AfterEvent(type=t_def.event)
                # The owner_id is correctly passed to the timer scheduler here.
                self._after_timer(delay_sec, after_event, owner_id=state.id)

        # Schedule 'invoke' services
        if not state.invoke:
            return

        # normalise – allow a single dict instead of a list
        invocations = state.invoke
        if not isinstance(invocations, (list, tuple)):
            invocations = [invocations]

        for invocation in invocations:
            service_callable = self.machine.logic.services.get(invocation.src)
            if service_callable is None:
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' referenced by "
                    f"state '{state.id}' is not registered."
                )
            self._invoke_service(
                invocation, service_callable, owner_id=state.id
            )

    async def _cancel_state_tasks(self, state: StateNode) -> None:
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
