# /src/xstate_statemachine/base_interpreter.py
# -----------------------------------------------------------------------------
# 🏛️ Base State Machine Interpreter
# -----------------------------------------------------------------------------
# This module defines the `BaseInterpreter`, the abstract foundation for state
# machine execution. It leverages the "Template Method" design pattern to
# establish a consistent algorithm for state transitions (`_process_event`),
# while deferring mode-specific implementations (like synchronous vs.
# asynchronous action execution) to its concrete subclasses.
#
# This architectural choice promotes high cohesion and low coupling, cleanly
# separating the universal statechart algorithm from the execution strategy,
# which significantly enhances code reuse and maintainability.
# -----------------------------------------------------------------------------
"""
Provides the foundational, mode-agnostic logic for interpreting a state machine.

This module contains the `BaseInterpreter` class, which should not be
instantiated directly. Instead, developers should use one of its concrete
subclasses, `Interpreter` for asynchronous operations or `SyncInterpreter` for
synchronous, blocking operations.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
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

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import AfterEvent, DoneEvent, Event
from .exceptions import ImplementationMissingError, StateNotFoundError
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
# Establishes a logger for this module, allowing for detailed, context-aware
# logging that can be configured by the end-user's application.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ BaseInterpreter Class Definition
# -----------------------------------------------------------------------------


class BaseInterpreter(Generic[TContext, TEvent]):
    """Provides the foundational logic for state machine interpretation.

    This class implements the "Template Method" design pattern. It defines the
    main algorithm for state transitions but allows subclasses to redefine
    certain steps, thereby separating the core statechart logic from the
    execution mode (e.g., synchronous vs. asynchronous).

    This class should not be instantiated directly. Use concrete subclasses like
    `Interpreter` (async) or `SyncInterpreter` (sync).

    Attributes:
        machine: The static `MachineNode` definition.
        context: The current extended state (context) of the machine.
        status: The operational status: 'uninitialized', 'running', 'stopped'.
        id: The unique identifier for this interpreter instance, inherited
            from the machine's ID.
        parent: A reference to the parent interpreter if this is a
                spawned actor, or `None` if it is a root machine.
    """

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
    ) -> None:
        """Initializes the BaseInterpreter instance.

        Args:
            machine: The `MachineNode` instance that defines the statechart's
                     structure, transitions, and logic references.
            interpreter_class: The concrete class being instantiated (e.g.,
                `Interpreter` or `SyncInterpreter`). This is used for
                correctly restoring an interpreter from a snapshot. If not
                provided, it defaults to the class of the current instance.
        """
        logger.info(
            "🧠 Initializing BaseInterpreter for machine '%s'...", machine.id
        )
        # 🧍‍♂️ Core Properties
        self.machine: MachineNode[TContext, TEvent] = machine
        self.context: TContext = copy.deepcopy(machine.initial_context)
        self.status: str = "uninitialized"
        self.id: str = machine.id
        self.parent: Optional["BaseInterpreter[Any, Any]"] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        self._actors: Dict[str, "BaseInterpreter[Any, Any]"] = {}

        # 🔗 Extensibility & Introspection
        self._plugins: List[PluginBase["BaseInterpreter[Any, Any]"]] = []
        self._interpreter_class: Type["BaseInterpreter[Any, Any]"] = (
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
        """Gets a set of the string IDs of all currently active atomic states.

        This property is the primary way to check the current state of the
        machine from outside the interpreter. Since a machine can be in
        multiple states at once (due to parallel states), this always
        returns a set.

        Returns:
            A set of unique string identifiers for the active leaf states.
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(
        self, plugin: PluginBase["BaseInterpreter[Any, Any]"]
    ) -> "BaseInterpreter[TContext, TEvent]":
        """Registers a plugin with the interpreter via the Observer pattern.

        Plugins hook into the interpreter's lifecycle to add cross-cutting
        concerns like logging, analytics, or persistence without modifying the
        core interpreter logic.

        Args:
            plugin: The plugin instance to register.

        Returns:
            The interpreter instance (`self`) to allow for method chaining,
            e.g., `Interpreter(m).use(p1).use(p2).start()`.
        """
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )
        return self

    # -------------------------------------------------------------------------
    # 📸 Snapshot & Persistence API (Memento Pattern)
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON-serializable snapshot of the interpreter's state.

        This method implements the Memento pattern, capturing the essential
        state (status, context, and active states) without exposing the
        internal implementation details of the interpreter. The resulting
        string can be persisted to disk or a database.

        Returns:
            A JSON string representing the interpreter's current state.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
        }
        # Use a default handler to gracefully handle non-serializable types
        json_snapshot = json.dumps(snapshot, indent=2, default=str)
        logger.debug("🖼️ Snapshot captured: %s", json_snapshot)
        return json_snapshot

    @classmethod
    def from_snapshot(
        cls: Type["BaseInterpreter[Any, Any]"],
        snapshot_str: str,
        machine: MachineNode[TContext, TEvent],
    ) -> "BaseInterpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a saved snapshot.

        This class method acts as a factory for restoring an interpreter to a
        previous state. It deserializes the snapshot and carefully reconstructs
        the interpreter's `context` and `_active_state_nodes`.

        Note:
            This method does not re-run entry actions or restart services from
            the snapshot's state. It provides a static restoration.

        Args:
            snapshot_str: The JSON string generated by `get_snapshot()`.
            machine: The corresponding `MachineNode` definition for the snapshot.

        Returns:
            A new interpreter instance restored to the snapshot's state.

        Raises:
            StateNotFoundError: If a state ID from the snapshot is not found
                in the provided machine definition.
            json.JSONDecodeError: If the snapshot string is not valid JSON.
        """
        logger.info(
            "🔄 Restoring interpreter from snapshot for machine '%s'...",
            machine.id,
        )
        snapshot = json.loads(snapshot_str)

        # 🧪 Create a new instance of the correct interpreter class (sync/async)
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # 🌳 Reconstruct the set of active state nodes
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
    # 📝 Abstract Methods (Template Method Hooks for Subclasses)
    # -------------------------------------------------------------------------
    # These methods define the "pluggable" parts of the state transition
    # algorithm. Concrete subclasses MUST override them to provide
    # mode-specific (sync or async) behavior.

    def start(
        self,
    ) -> Union[
        "BaseInterpreter[TContext, TEvent]",
        Awaitable["BaseInterpreter[TContext, TEvent]"],
    ]:
        """Starts the interpreter. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the 'start' method."
        )

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the 'stop' method."
        )

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
        """Sends an event for processing. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the 'send' method."
        )

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> Union[None, Awaitable[None]]:
        """Executes actions. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the '_execute_actions' method."
        )

    def _cancel_state_tasks(
        self, state: StateNode
    ) -> Union[None, Awaitable[None]]:
        """Cancels tasks for a state. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the '_cancel_state_tasks' method."
        )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Handles delayed events. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the '_after_timer' method."
        )

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> None:
        """Handles invoked services. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the '_invoke_service' method."
        )

    def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> Union[None, Awaitable[None]]:
        """Handles spawning child actors. Must be implemented by a subclass."""
        raise NotImplementedError(
            "Subclasses must implement the '_spawn_actor' method."
        )

    # -------------------------------------------------------------------------
    # ✉️ Event Preparation Helper (Static Method & DRY Principle)
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
        adhering to the "Don't Repeat Yourself" (DRY) principle. It ensures
        that both `Interpreter` and `SyncInterpreter` handle event creation
        identically, which prevents subtle bugs and improves maintainability.

        Args:
            event_or_type: The raw event input, which can be a simple string
                (e.g., "SUBMIT"), a dictionary (e.g., `{"type": "SUBMIT"}`),
                or a pre-constructed `Event` object.
            **payload: Keyword arguments that become the event's payload if
                `event_or_type` is a string.

        Returns:
            A standardized `Event`, `DoneEvent`, or `AfterEvent` object,
            ready for processing.

        Raises:
            TypeError: If an unsupported type (e.g., an integer or list)
                is passed as an event.
        """
        if isinstance(event_or_type, str):
            return Event(type=event_or_type, payload=payload)
        if isinstance(event_or_type, dict):
            # 🛡️ Defensively copy to avoid mutating the caller's dictionary
            local_payload = event_or_type.copy()
            event_type = local_payload.pop("type", "UnnamedEvent")
            return Event(type=event_type, payload=local_payload)
        if isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            return event_or_type
        # ❌ Rejects any type that is not a string, dict, or Event object
        raise TypeError(
            f"Unsupported event type passed to send(): {type(event_or_type)}"
        )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (The Template Method's Main Algorithm)
    # -------------------------------------------------------------------------

    async def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Finds and executes a single, optimal transition for a given event.

        This is the heart of the interpreter. It implements the W3C SCXML
        algorithm for event processing, ensuring that transitions are
        selected deterministically and executed in the correct order.

        The algorithm steps:
        1. Find the most specific, eligible transition for the event.
        2. If none, ignore the event.
        3. If it's an internal transition (no target), just run actions.
        4. If it's an external transition:
           a. Find the transition's "domain" (least common ancestor).
           b. Exit all states from the current state up to the domain.
           c. Execute the transition's actions.
           d. Enter all states from the domain down to the target state.
           e. Notify plugins of the completed transition.

        Args:
            event: The event object to process.
        """
        logger.debug(
            "⚙️  Processing event '%s' in interpreter '%s'.",
            event.type,
            self.id,
        )

        # 1️⃣ Find the optimal transition based on current state and event
        transition = self._find_optimal_transition(event)
        if not transition:
            logger.debug(
                "🤷 No eligible transition for event '%s'. Event ignored.",
                event.type,
            )
            return

        # 2️⃣ Handle internal transitions (no state change)
        if not transition.target_str:
            logger.info("🎬 Performing internal transition with actions.")
            await self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,  # from_states == to_states
                    self._active_state_nodes,
                    transition,
                )
            return

        # 3️⃣ Handle external transitions (state change)
        from_states_snapshot = self._active_state_nodes.copy()

        # 🗺️ Calculate the path for the transition
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

        # 🏃‍♂️ Execute the transition steps in order
        await self._exit_states(
            sorted(
                list(states_to_exit), key=lambda s: len(s.id), reverse=True
            ),
            event,
        )
        await self._execute_actions(transition.actions, event)
        await self._enter_states(path_to_enter, event)

        # 🔔 Notify plugins about the successful transition
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
        """Recursively enters a list of states and their children.

        This method executes entry actions and schedules tasks for each state
        in the entry path. It handles entering compound and parallel states
        by recursively calling itself for the appropriate child states.

        Args:
            states_to_enter: A list of `StateNode` objects to enter, ordered
                from outermost to innermost.
            event: The event that triggered this state entry.
        """
        # 🎁 Use a synthetic event for initial state entry
        triggering_event = event or Event(
            type="___xstate_statemachine_init___"
        )

        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug("➡️  Entering state: '%s'.", state.id)

            # ⚙️ Run entry actions and schedule tasks
            await self._execute_actions(state.entry, triggering_event)
            self._schedule_state_tasks(state)  # Schedules `after` and `invoke`

            # ✅ If we entered a final state, check if its parent is now done
            if state.is_final:
                await self._check_and_fire_on_done(state)

            # Recursively enter children for compound/parallel states
            if state.type == "compound" and state.initial:
                initial_child = state.states.get(state.initial)
                if initial_child:
                    await self._enter_states([initial_child], triggering_event)
                else:
                    logger.error(
                        "❌ Misconfiguration: Initial state '%s' not found "
                        "in compound state '%s'.",
                        state.initial,
                        state.id,
                    )
            elif state.type == "parallel":
                await self._enter_states(
                    list(state.states.values()), triggering_event
                )

    async def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Recursively exits a list of states.

        This method cancels any running tasks for the exited states and
        executes their exit actions.

        Args:
            states_to_exit: A list of `StateNode` objects to exit, ordered
                from innermost to outermost.
            event: The event that triggered this state exit.
        """
        triggering_event = event or Event(
            type="___xstate_statemachine_exit___"
        )

        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            # 🛑 Cancel any background tasks owned by this state FIRST
            await self._cancel_state_tasks(state)
            # ⚙️ Then, run exit actions
            await self._execute_actions(state.exit, triggering_event)
            # 🗑️ Finally, remove from the set of active states
            self._active_state_nodes.discard(state)

    # -------------------------------------------------------------------------
    # 🔎 State Evaluation & Pathfinding Helpers
    # -------------------------------------------------------------------------

    def _is_state_done(self, state_node: StateNode) -> bool:
        """Determines if a compound or parallel state is "done".

        This is a key part of the SCXML algorithm, especially for `onDone`
        transitions. The logic is recursive to handle deeply nested states.

        - A state is done if its `type` is `final`.
        - A `compound` state is done if its active child state is also done.
        - A `parallel` state is done only if ALL of its child regions are done.

        Args:
            state_node: The compound or parallel state to check.

        Returns:
            `True` if the state is considered done, `False` otherwise.
        """
        # 🔑 A final state is the base case for the recursion.
        if state_node.is_final:
            return True

        # 🧠 For a compound state, its "doneness" is determined by its child.
        if state_node.type == "compound":
            # Find the single active child of this compound state.
            active_child = next(
                (
                    s
                    for s in self._active_state_nodes
                    if s.parent == state_node
                ),
                None,
            )
            if not active_child:
                return False

            # ✅ FIX: Recursively call _is_state_done on the child.
            # This correctly handles cases where the child is also a
            # compound or parallel state.
            return self._is_state_done(active_child)

        #  parallelism: all children must be done
        if state_node.type == "parallel":
            # 🌐 For a parallel state, every single region must be "done".
            for region in state_node.states.values():
                # Find all active states within this region.
                active_descendants = [
                    s
                    for s in self._active_state_nodes
                    if self._is_descendant(s, region)
                ]

                # If a region has no active descendants, it can't be done.
                if not active_descendants:
                    return False

                # ✅ FIX: Check if ANY active descendant in the region is "done".
                # The original logic was more robust and is restored here.
                if not any(self._is_state_done(d) for d in active_descendants):
                    return False

            # If all regions passed the check, the parallel state is done.
            return True

        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Checks if an ancestor is "done" and fires its `onDone` event.

        This method bubbles up from a newly entered final state to check if
        any of its parents have now met their completion criteria.

        Args:
            final_state: The final state that was just entered.
        """
        current_ancestor = final_state.parent
        while current_ancestor:
            if current_ancestor.on_done and self._is_state_done(
                current_ancestor
            ):
                logger.info(
                    "🎉 State '%s' is done, firing onDone event.",
                    current_ancestor.id,
                )
                # 📨 Send the synthetic `done.state.*` event to be processed
                await self.send(
                    Event(type=f"done.state.{current_ancestor.id}")
                )
                return  # Only fire for the first completed ancestor
            current_ancestor = current_ancestor.parent

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the most specific, eligible transition for an event.

        This implements the logic for selecting which transition to take when
        multiple could potentially handle an event. The rule is to choose
        the transition defined on the most deeply nested state that is
        currently active. This ensures that child states can override parent
        behavior.

        Args:
            event: The event to find a transition for.

        Returns:
            The highest-priority `TransitionDefinition` if one is found,
            otherwise `None`.
        """
        eligible_transitions: List[TransitionDefinition] = []

        # Sort active states by depth, so we check deepest children first.
        sorted_active_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: len(s.id),
            reverse=True,
        )

        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        # 🌳 Traverse up the tree from each active leaf node
        for state in sorted_active_nodes:
            current: Optional[StateNode] = state
            while current:
                # Standard `on` transitions
                if (
                    not is_explicit_transient_event
                    and event.type in current.on
                ):
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # Transient ("always") transitions
                if is_transient_check and "" in current.on:
                    for transition in current.on[""]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)

                # `onDone` transitions for compound states
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)

                # `after` transitions for timed events
                if isinstance(event, AfterEvent):
                    for transitions in current.after.values():
                        for t_def in transitions:
                            if (
                                t_def.event == event.type
                                and self._is_guard_satisfied(
                                    t_def.guard, event
                                )
                            ):
                                eligible_transitions.append(t_def)

                # `onDone`/`onError` for invoked services
                if isinstance(event, DoneEvent):
                    for inv in current.invoke:
                        if event.src == inv.id:
                            transitions_to_check = inv.on_done + inv.on_error
                            for t_def in transitions_to_check:
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

        # 🏆 Return the most deeply nested (highest priority) transition
        return max(eligible_transitions, key=lambda t: len(t.source.id))

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Finds the least common compound ancestor of source and target.

        This is a critical step for determining which states to exit and enter
        during an external transition, ensuring atomicity.
        """
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )

        # Handle external self-transitions where the domain is the parent
        if transition.target_str and target_state == transition.source:
            return transition.source.parent

        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)

        # The domain is the most deeply nested common ancestor
        common_ancestors = source_ancestors.intersection(target_ancestors)
        return (
            max(common_ancestors, key=lambda s: len(s.id))
            if common_ancestors
            else None
        )

    @staticmethod
    def _get_path_to_state(
        to_state: StateNode, *, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Builds the list of states to enter to reach a target state."""
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        path.reverse()  # reversing to get parent -> child order
        return path

    @staticmethod
    def _get_ancestors(node: StateNode) -> Set[StateNode]:
        """Gets a set of all ancestors of a node, including the node itself."""
        ancestors: Set[StateNode] = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """Checks if a node is a descendant of a specified ancestor."""
        if not ancestor:
            return True  # All nodes are descendants of the machine's null root
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    # -------------------------------------------------------------------------
    # 🛡️ Task & Guard Management
    # -------------------------------------------------------------------------

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules `after` and `invoke` tasks for a state upon entry.

        This method dispatches to the abstract `_after_timer` and
        `_invoke_service` methods, which are implemented by the concrete
        sync/async subclasses.
        """
        # Schedule `after` timers
        for delay, transitions in state.after.items():
            for t_def in transitions:
                delay_sec = float(delay) / 1000.0
                after_event = AfterEvent(type=t_def.event)
                self._after_timer(delay_sec, after_event, owner_id=state.id)

        # Schedule `invoke` services
        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            # 💥 Fail-fast if the implementation is missing
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
        """Checks if a guard condition (a synchronous, pure function) is met.

        Args:
            guard_name: The name of the guard function to check. If `None`,
                the guard is considered to have passed.
            event: The current event being processed, which is passed to the
                guard function for context-aware decisions.

        Returns:
            `True` if the guard passes or if there is no guard, `False` otherwise.

        Raises:
            ImplementationMissingError: If the guard function is named in the
                machine definition but not provided in the machine's logic.
        """
        # ✅ A transition without a guard is always allowed to proceed.
        if not guard_name:
            return True

        guard_callable = self.machine.logic.guards.get(guard_name)
        if not guard_callable:
            raise ImplementationMissingError(
                f"Guard '{guard_name}' not implemented."
            )

        # ✅ Execute the guard function and log the result.
        result = guard_callable(self.context, event)
        logger.info(
            "🛡️  Evaluating guard '%s': %s",
            guard_name,
            "✅ Passed" if result else "❌ Failed",
        )
        return result
