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

# -----------------------------------------------------------------------------
# 📦 Imports
# -----------------------------------------------------------------------------
import copy
import json
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    Union,
    overload,
)

from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
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

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ BaseInterpreter Class Definition
# -----------------------------------------------------------------------------


class BaseInterpreter(Generic[TContext, TEvent]):
    """Provides the foundational, mode-agnostic logic for interpreting a state machine.

    This class implements the "Template Method" design pattern. It defines the
    main algorithm for state transitions (`_process_event`) but allows subclasses
    to redefine certain steps (`_execute_actions`, `send`, `start`, etc.),
    thereby separating the core statechart logic from the execution mode
    (e.g., synchronous vs. asynchronous).

    This class should not be instantiated directly. Use concrete subclasses like
    `Interpreter` (async) or `SyncInterpreter` (sync).

    Attributes:
        machine: The static machine definition.
        context: The current extended state (context) of the machine.
        status: The operational status: 'uninitialized', 'running', 'stopped'.
        id: The unique identifier for this interpreter instance.
        parent: A reference to the parent interpreter if this is a spawned actor.
    """

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
    ) -> None:
        """Initializes the BaseInterpreter.

        Args:
            machine: The machine definition to interpret.
            interpreter_class: The concrete class (e.g., `Interpreter` or
                `SyncInterpreter`) being instantiated. This is used for
                snapshot restoration. If not provided, it defaults to the
                class of the current instance.
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

        # 🔗 Extensibility & Introspection
        self._plugins: List[PluginBase[BaseInterpreter]] = []
        self._interpreter_class: Type["BaseInterpreter"] = (
            interpreter_class or self.__class__
        )

        logger.info(
            "✅ BaseInterpreter '%s' initialized. Status: '%s'.",
            self.id,
            self.status,
        )

    # -------------------------------------------------------------------------
    # 🔍 Public Properties & Methods
    # -------------------------------------------------------------------------

    @property
    def current_state_ids(self) -> Set[str]:
        """Gets a set of the string IDs of all currently active atomic or final states.

        Returns:
            A set of string identifiers for the active leaf states.
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(self, plugin: PluginBase["BaseInterpreter"]) -> "BaseInterpreter":
        """Registers a plugin with the interpreter.

        Args:
            plugin: The plugin instance to register.

        Returns:
            The interpreter instance (`self`) to allow for method chaining.
        """
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )
        return self

    # -------------------------------------------------------------------------
    # 📸 Snapshot & Persistence API
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON serializable snapshot of the interpreter's current state.

        Returns:
            A JSON string representing the interpreter's state.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
        }
        json_snapshot = json.dumps(snapshot, indent=2)
        logger.debug("🖼️ Snapshot captured: %s", json_snapshot)
        return json_snapshot

    @classmethod
    def from_snapshot(
        cls: Type["BaseInterpreter"],
        snapshot_str: str,
        machine: MachineNode[TContext, TEvent],
    ) -> "BaseInterpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a saved snapshot.

        Args:
            snapshot_str: The JSON string snapshot.
            machine: The machine definition corresponding to the snapshot.

        Returns:
            A new interpreter instance restored to the snapshot's state.

        Raises:
            StateNotFoundError: If a state ID from the snapshot is not found.
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
                logger.debug("   ↳ Restored active state: '%s'", state_id)
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
    # 📝 Abstract Methods (Template Pattern Hooks)
    # -------------------------------------------------------------------------

    def start(self) -> Union["BaseInterpreter", Awaitable["BaseInterpreter"]]:
        """Starts the interpreter. Must be implemented by subclasses."""
        raise NotImplementedError

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter. Must be implemented by subclasses."""
        raise NotImplementedError

    @overload
    def send(self, event_type: str, **payload: Any) -> Any: ...  # noqa

    @overload
    def send(  # noqa
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> Any: ...

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> Any:
        """Sends an event for processing. Must be implemented by subclasses."""
        raise NotImplementedError

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> Any:
        """Executes actions. Must be implemented by subclasses."""
        raise NotImplementedError

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

    # -------------------------------------------------------------------------
    # ✉️ Event Preparation Helper (DRY Principle)
    # -------------------------------------------------------------------------

    @staticmethod
    def _prepare_event(
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> Union[Event, DoneEvent, AfterEvent]:
        """Prepares a standardized event object from various input formats.

        This static helper centralizes the logic for creating event objects,
        adhering to the DRY principle and resolving IDE warnings about
        duplicated code in `Interpreter` and `SyncInterpreter`.

        Args:
            event_or_type: The raw event input (string, dict, or Event object).
            **payload: Payload for string-based event types.

        Returns:
            A standardized `Event`, `DoneEvent`, or `AfterEvent` object.

        Raises:
            TypeError: If an unsupported type is passed as an event.
        """
        if isinstance(event_or_type, str):
            return Event(type=event_or_type, payload=payload)
        if isinstance(event_or_type, dict):
            local_payload = event_or_type.copy()
            event_type = local_payload.pop("type", "UnnamedEvent")
            return Event(type=event_type, payload=local_payload)
        if isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            return event_or_type
        raise TypeError(
            f"Unsupported event type passed to send(): {type(event_or_type)}"
        )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (The Template Method)
    # -------------------------------------------------------------------------

    async def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Finds and executes a transition based on the given event.

        This is the heart of the interpreter, defining the W3C SCXML algorithm
        for event processing.

        Args:
            event: The event to process.
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
            logger.info("🎬 Performing internal transition with actions.")
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
        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )

        await self._exit_states(
            sorted(
                list(states_to_exit), key=lambda s: len(s.id), reverse=True
            ),
            event,
        )
        await self._execute_actions(transition.actions, event)
        await self._enter_states(path_to_enter, event)

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

    async def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Enters a list of states, executing entry actions and scheduling tasks."""
        triggering_event = event or Event(
            type="___xstate_statemachine_init___"
        )

        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug("➡️  Entering state: '%s'.", state.id)

            await self._execute_actions(state.entry, triggering_event)

            if state.is_final:
                await self._check_and_fire_on_done(state)

            if state.type == "compound" and state.initial:
                initial_child = state.states.get(state.initial)
                if initial_child:
                    await self._enter_states([initial_child], triggering_event)
                else:
                    logger.error(
                        "❌ Initial state '%s' not found.", state.initial
                    )
            elif state.type == "parallel":
                await self._enter_states(
                    list(state.states.values()), triggering_event
                )

            self._schedule_state_tasks(state)

    async def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Exits a list of states, executing exit actions and canceling tasks."""
        triggering_event = event or Event(
            type="___xstate_statemachine_exit___"
        )

        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            await self._cancel_state_tasks(state)
            await self._execute_actions(state.exit, triggering_event)
            self._active_state_nodes.discard(state)

    # -------------------------------------------------------------------------
    # 🔎 State Evaluation & Pathfinding Helpers
    # -------------------------------------------------------------------------

    def _is_state_done(self, state_node: StateNode) -> bool:
        """Determines if a state has reached its "done" condition."""
        if state_node.is_final:
            return True

        direct_active = [
            s for s in self._active_state_nodes if s.parent == state_node
        ]

        if state_node.type == "compound":
            if not direct_active:
                return False
            child = direct_active[0]
            return child.is_final or self._is_state_done(child)

        if state_node.type == "parallel":
            for region in state_node.states.values():
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

        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Checks if an ancestor is "done" and fires the `onDone` event."""
        current_ancestor = final_state.parent
        while current_ancestor:
            if current_ancestor.on_done and self._is_state_done(
                current_ancestor
            ):
                logger.info(
                    "✅ State '%s' is done, firing onDone event.",
                    current_ancestor.id,
                )
                await self.send(
                    Event(type=f"done.state.{current_ancestor.id}")
                )
                return
            current_ancestor = current_ancestor.parent

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the most specific, eligible transition for an event."""
        eligible_transitions: List[TransitionDefinition] = []
        sorted_active_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: len(s.id),
            reverse=True,
        )

        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        for state in sorted_active_nodes:
            current: Optional[StateNode] = state
            while current:
                if (
                    not is_explicit_transient_event
                    and event.type in current.on
                ):
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                if is_transient_check and "" in current.on:
                    for transition in current.on[""]:
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
                            for t_def in inv.on_done + inv.on_error:
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

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Finds the least common compound ancestor of source and target."""
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )

        if transition.target_str and target_state == transition.source:
            return transition.source.parent

        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)
        common_ancestors = source_ancestors.intersection(target_ancestors)
        return (
            max(common_ancestors, key=lambda s: len(s.id))
            if common_ancestors
            else None
        )

    def _get_path_to_state(  # noqa E266
        self,
        to_state: StateNode,
        *,
        stop_at: Optional[StateNode] = None,
    ) -> List[StateNode]:
        """Builds the list of states to enter to reach a target state."""
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    def _get_ancestors(self, node: StateNode) -> Set[StateNode]:  # noqa E266
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

    # -------------------------------------------------------------------------
    # 🛡️ Task & Guard Management
    # -------------------------------------------------------------------------

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules `after` and `invoke` tasks for a state upon entry."""
        for delay, transitions in state.after.items():
            for t_def in transitions:
                delay_sec = float(delay) / 1000.0
                after_event = AfterEvent(type=t_def.event)
                self._after_timer(delay_sec, after_event, owner_id=state.id)

        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            if service_callable is None:
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' referenced by "
                    f"state '{state.id}' is not registered."
                )
            self._invoke_service(
                invocation, service_callable, owner_id=state.id
            )

    def _is_guard_satisfied(
        self,
        guard_name: Optional[str],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Checks if a guard condition is met.

        Args:
            guard_name: The name of the guard to check.
            event: The current event being processed. It can be any event type
                as guards only need access to common event properties.

        Returns:
            `True` if the guard passes or if there is no guard, `False` otherwise.

        Raises:
            ImplementationMissingError: If the guard function is not defined.
        """
        # ✅ FIX: The type hint for `event` is broadened to accept any event type.
        # This resolves the type mismatch error when called from `_find_optimal_transition`.
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
            "✅ Passed" if result else "❌ Failed",
        )
        return result
