# /src/xstate_statemachine/base_interpreter.py
# -----------------------------------------------------------------------------
# 🏛️ Base State Machine Interpreter
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
    TypeVar,
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

# This TypeVar allows methods to return the specific subclass instance (self).
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter")

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

    This abstract base class implements the "Template Method" design pattern.
    It defines the complete, final algorithm for processing events and
    transitioning between states (`_process_event`), but it defers the
    implementation of specific execution steps (like running actions or timers)
    to its concrete subclasses. This architecture cleanly separates the universal
    statechart algorithm from the execution strategy (e.g., synchronous vs.
    asynchronous).

    This class should not be instantiated directly. Use `Interpreter` (async)
    or `SyncInterpreter` (sync).

    Attributes:
        machine (MachineNode[TContext, TEvent]): The static `MachineNode`
            definition that represents the statechart's structure.
        context (TContext): The current extended state (context) of the
            machine, holding all dynamic data.
        status (str): The operational status of the interpreter:
            'uninitialized', 'running', or 'stopped'.
        id (str): A unique identifier for this interpreter instance, inherited
            from the machine's ID.
        parent (Optional[BaseInterpreter[Any, Any]]): A reference to the parent
            interpreter if this instance was spawned as part of an actor model,
            otherwise `None`.
    """

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
    ) -> None:
        """Initializes the BaseInterpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The `MachineNode` instance
                that defines the statechart's structure, transitions, and
                logic references.
            interpreter_class (Optional[Type["BaseInterpreter"]]): The concrete
                class being instantiated (e.g., `Interpreter` or
                `SyncInterpreter`). This is used internally for correctly
                restoring an interpreter from a snapshot. If not provided, it
                defaults to the class of the current instance.
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
        returns a set of the most specific, leaf-node state identifiers.

        Returns:
            Set[str]: A set of unique string identifiers for the active atomic
            or final leaf states.
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    def use(
        self: TInterpreter, plugin: PluginBase["BaseInterpreter[Any, Any]"]
    ) -> TInterpreter:
        """Registers a plugin with the interpreter via the Observer pattern.

        Plugins hook into the interpreter's lifecycle (e.g., `on_transition`,
        `on_guard_evaluated`) to add cross-cutting concerns like logging,
        analytics, or state persistence without modifying the core interpreter
        logic. This promotes a clean and extensible architecture.

        Args:
            plugin: The plugin instance to register.

        Returns:
            The interpreter instance (`self`) with the correct subclass type
            to allow for convenient and type-safe method chaining.
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

        This method implements the Memento design pattern by capturing the
        essential state of the interpreter (its status, context, and active
        states) without exposing its internal implementation details. The
        resulting JSON string can be persisted to a file, database, or sent
        over a network.

        Returns:
            str: A JSON string representing the interpreter's current state.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = {
            "status": self.status,
            "context": self.context,
            "state_ids": list(self.current_state_ids),
        }
        # Use a default handler to gracefully handle non-serializable types.
        json_snapshot = json.dumps(snapshot, indent=2, default=str)
        logger.debug(
            "🖼️ Snapshot for '%s' captured: %s", self.id, json_snapshot
        )
        return json_snapshot

    @classmethod
    def from_snapshot(
        cls: Type["BaseInterpreter[Any, Any]"],
        snapshot_str: str,
        machine: MachineNode[TContext, TEvent],
    ) -> "BaseInterpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a saved snapshot.

        This factory method reconstructs an interpreter's state from a JSON
        snapshot. It deserializes the snapshot, finds the corresponding state
        nodes in the provided machine definition, and sets the context and
        status, effectively restoring the machine to a previous point in time.

        Note:
            This method performs a static restoration. It does not re-run
            entry actions of the restored states or restart any invoked
            services or `after` timers that were active when the snapshot
            was taken.

        Args:
            snapshot_str (str): The JSON string previously generated by
                `get_snapshot()`.
            machine (MachineNode[TContext, TEvent]): The corresponding
                `MachineNode` definition that the snapshot belongs to.

        Returns:
            BaseInterpreter[TContext, TEvent]: A new interpreter instance
                restored to the snapshot's state.

        Raises:
            StateNotFoundError: If a state ID from the snapshot cannot be found
                in the provided machine definition.
            json.JSONDecodeError: If the snapshot string is not valid JSON.
        """
        logger.info(
            "🔄 Restoring interpreter for machine '%s' from snapshot...",
            machine.id,
        )
        try:
            snapshot = json.loads(snapshot_str)
        except json.JSONDecodeError as e:
            logger.error("❌ Invalid JSON in snapshot string: %s", e)
            raise

        # 🧪 Create a new instance of the correct interpreter class (sync/async)
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # 🌳 Reconstruct the set of active state nodes from their IDs
        interpreter._active_state_nodes.clear()
        for state_id in snapshot["state_ids"]:
            node = machine.get_state_by_id(state_id)
            if node:
                interpreter._active_state_nodes.add(node)
                logger.debug("    ↳ Restored active state: '%s'", state_id)
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
    # mode-specific (synchronous or asynchronous) behavior.

    def start(
        self,
    ) -> Union[
        "BaseInterpreter[TContext, TEvent]",
        Awaitable["BaseInterpreter[TContext, TEvent]"],
    ]:
        """Starts the interpreter by entering the initial state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass (e.g., `Interpreter`, `SyncInterpreter`).
        """
        raise NotImplementedError(
            "Subclasses must implement the 'start' method."
        )

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter and cleans up resources.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
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
        """Sends an event to the running interpreter for processing.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'send' method."
        )

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> Union[None, Awaitable[None]]:
        """Executes a list of action definitions.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass to handle sync/async execution.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_execute_actions' method."
        )

    def _cancel_state_tasks(
        self, state: StateNode
    ) -> Union[None, Awaitable[None]]:
        """Cancels all background tasks associated with a given state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_cancel_state_tasks' method."
        )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Handles a delayed event (`after` transition).

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_after_timer' method."
        )

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> Union[None, Awaitable[None]]:
        """Handles an invoked service.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_invoke_service' method."
        )

    def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> Union[None, Awaitable[None]]:
        """Handles the spawning of a child state machine actor.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_spawn_actor' method."
        )

    # -------------------------------------------------------------------------
    # ✉️ Event Preparation Helper
    # -------------------------------------------------------------------------

    @staticmethod
    def _prepare_event(
        event_or_type: Union[str, Dict[str, Any], Any],
        **payload: Any,
    ) -> Union[Event, DoneEvent, AfterEvent]:
        """Normalizes various event inputs into a concrete `Event` object.

        This helper ensures that the interpreter can robustly handle events
        passed as strings, dictionaries, or `Event` instances. It uses
        duck-typing to handle a specific edge case where the library might be
        imported twice in a testing environment, resulting in two distinct
        `Event` class identities.

        Args:
            event_or_type (Union[str, Dict[str, Any], Any]): The event to be
                normalized. Can be:
                - A string (`"EVENT_TYPE"`)
                - A dictionary with a "type" key (`{"type": "EVENT_TYPE", ...}`)
                - An instance of `Event`, `DoneEvent`, or `AfterEvent`.
                - A duck-typed object with `.type` and `.payload` attributes.
            **payload (Any): Additional keyword arguments to be used as the
                event's payload if `event_or_type` is a string.

        Returns:
            Union[Event, DoneEvent, AfterEvent]: A concrete event object ready
            for processing.

        Raises:
            TypeError: If the input cannot be resolved into a valid event format.
        """
        # 1️⃣ Input is a simple string: create a new Event.
        if isinstance(event_or_type, str):
            return Event(type=event_or_type, payload=payload)

        # 2️⃣ Input is a dictionary: convert to an Event.
        if isinstance(event_or_type, dict):
            data = event_or_type.copy()
            event_type = data.pop("type", "UnnamedEvent")
            return Event(type=event_type, payload=data)

        # 3️⃣ Input is already a native Event instance: use as-is.
        if isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            return event_or_type

        # 4️⃣ Duck-typing: handle "foreign" Event objects (for testing robustness).
        if hasattr(event_or_type, "type") and hasattr(
            event_or_type, "payload"
        ):
            # Trust and forward as-is to preserve any subclass information.
            return event_or_type  # type: ignore[return-value]

        # 5️⃣ Anything else is an unsupported format.
        raise TypeError(
            f"Unsupported event type passed to send(): {type(event_or_type)}"
        )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (The Template Method)
    # -------------------------------------------------------------------------

    async def _process_event(
        self, event: Union[Event, DoneEvent, AfterEvent]
    ) -> None:
        """Executes a single, complete "step" of the SCXML algorithm.

        This method is the heart of the interpreter. It takes a single event
        and orchestrates the entire state transition process:
        1.  Finds the optimal transition to take based on the current state and event.
        2.  Calculates the set of states to exit and enter.
        3.  Executes exit actions, transition actions, and entry actions in the
            correct SCXML-specified order.
        4.  Updates the set of active states.

        Args:
            event (Union[Event, DoneEvent, AfterEvent]): The event to process.
        """
        # 1️⃣ Select the winning transition based on event, current state, and guards.
        transition = self._find_optimal_transition(event)
        if transition is None:
            logger.debug("🍃 No transition found for event '%s'.", event.type)
            return  # ➡️ No transition matched, so the step is complete.

        # 2️⃣ Handle "internal" transitions (no state change).
        # These transitions only execute actions without exiting or entering any states.
        if not transition.target_str:
            logger.debug(
                "🎬 Executing internal transition for event '%s'.", event.type
            )
            await self._execute_actions(transition.actions, event)
            # Notify plugins about the self-transition.
            for plug in self._plugins:
                plug.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 3️⃣ Set up for an "external" transition (state change).
        snapshot_before = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s is not domain
        }

        # 🚀 Begin multi-stage target state resolution.
        root = self.machine
        parent = transition.source.parent
        target_str = transition.target_str
        target_state: Optional[StateNode] = None

        logger.debug(
            "🔄 Resolving target state '%s' from source '%s'.",
            target_str,
            transition.source.id,
        )

        # 4️⃣ Standard resolution attempts (most common paths).
        resolution_attempts = [
            (target_str, transition.source),  # Relative to source
            (target_str, parent) if parent else None,  # Relative to parent
            (target_str, root),  # Relative to root
            (
                f"{root.id}.{target_str}",
                root,
            ),  # Assuming relative from root ID
        ]

        for tgt, ref in filter(None, resolution_attempts):
            try:
                target_state = resolve_target_state(tgt, ref)
                transition.target_str = (
                    tgt  # Update transition with fully resolved path
                )
                logger.debug(
                    "✅ Resolved via standard method: '%s'", target_state.id
                )
                break
            except StateNotFoundError:
                logger.debug(
                    "    ↳ Failed standard resolution of '%s' from '%s'",
                    tgt,
                    ref.id,
                )
                continue

        # 5️⃣ Fallback 1: Direct attribute lookup on the root machine.
        if target_state is None and hasattr(root, target_str):
            candidate = getattr(root, target_str)
            if isinstance(candidate, StateNode):
                target_state = candidate
                logger.debug(
                    "✅ Resolved via root attribute lookup: '%s'",
                    target_state.id,
                )

        # 6️⃣ Fallback 2: Lookup in the root's `states` dictionary.
        if target_state is None and hasattr(root, "states"):
            states_dict = getattr(root, "states", {})
            if target_str in states_dict:
                target_state = states_dict[target_str]
                logger.debug(
                    "✅ Resolved via root states dict (exact match): '%s'",
                    target_state.id,
                )
            else:  # Check for local name match
                for state in states_dict.values():
                    if state.id.split(".")[-1] == target_str:
                        target_state = state
                        logger.debug(
                            "✅ Resolved via root states dict (local name): '%s'",
                            target_state.id,
                        )
                        break

        # 7️⃣ Fallback 3: Exhaustive depth-first tree walk.
        if target_state is None:

            def _walk(node):
                yield node
                if hasattr(node, "states"):
                    for child in node.states.values():
                        yield from _walk(child)

            for candidate in _walk(root):
                if candidate.id.split(".")[-1] == target_str:
                    target_state = candidate
                    logger.debug(
                        "✅ Resolved via full tree walk: '%s'", target_state.id
                    )
                    break

        # 8️⃣ Final failure if no resolution succeeded.
        if target_state is None:
            available = list(getattr(root, "states", {}).keys())
            logger.error(
                "🚫 All resolution attempts failed for target: '%s'",
                target_str,
            )
            logger.error(
                "📂 Available top-level states in machine '%s': %s",
                root.id,
                available,
            )
            raise StateNotFoundError(target_str, root.id)

        # 9️⃣ Calculate path to enter and execute the transition sequence.
        # This order is mandated by SCXML: exit -> transition -> enter.
        path_to_enter = self._get_path_to_state(target_state, stop_at=domain)

        await self._exit_states(
            sorted(states_to_exit, key=lambda s: len(s.id), reverse=True),
            event,
        )
        await self._execute_actions(transition.actions, event)
        await self._enter_states(path_to_enter, event)

        # 🔟 Finalize the new state configuration and notify plugins.
        self._active_state_nodes.difference_update(states_to_exit)
        self._active_state_nodes.update(path_to_enter)
        for plug in self._plugins:
            plug.on_transition(
                self,
                snapshot_before,
                self._active_state_nodes.copy(),
                transition,
            )

    # -------------------------------------------------------------------------
    # ⏯️ State Management Sub-Routines
    # -------------------------------------------------------------------------

    async def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Enters a list of states in order, running actions and tasks.

        This method follows the SCXML algorithm for state entry. For each
        state, it:
        1.  Adds the state to the active configuration.
        2.  Executes all 'entry' actions.
        3.  Schedules any `after` timers or `invoke` services defined on the state.
        4.  If the state is a final state, it checks if its parent is now "done".
        5.  Recursively enters the initial substate of a compound state or all
            substates of a parallel state.

        Args:
            states_to_enter (List[StateNode]): An ordered list of states to
                enter, from the outermost ancestor to the innermost child.
            event (Optional[Event]): The event that triggered this state entry.
        """
        trigger_event = event or Event(type="___xstate_statemachine_init___")

        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug("➡️  Entering state: '%s'.", state.id)

            # ⚙️ Run entry actions and schedule background tasks.
            await self._execute_actions(state.entry, trigger_event)
            self._schedule_state_tasks(state)

            # 🎉 If we entered a final state, check if its parent is now complete.
            if state.is_final:
                await self._check_and_fire_on_done(state)

            # 🗺️ Handle automatic entry into child states.
            if state.type == "compound" and state.initial:
                initial_child = state.states.get(state.initial)
                if initial_child:
                    await self._enter_states([initial_child], trigger_event)
                else:
                    logger.error(
                        "❌ Misconfiguration: Initial state '%s' not found in compound state '%s'.",
                        state.initial,
                        state.id,
                    )
            elif state.type == "parallel":
                # For parallel states, enter all child regions simultaneously.
                await self._enter_states(
                    list(state.states.values()), trigger_event
                )

    async def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Exits a list of states in order, canceling tasks and running actions.

        This method follows the SCXML algorithm for state exit. For each state, it:
        1.  Cancels any running tasks (`after` timers, `invoke` services)
            owned by the state.
        2.  Executes all 'exit' actions.
        3.  Removes the state from the active configuration.

        Args:
            states_to_exit (List[StateNode]): An ordered list of states to
                exit, from the innermost child to the outermost ancestor.
            event (Optional[Event]): The event that triggered the state exit.
        """
        trigger_event = event or Event(type="___xstate_statemachine_exit___")

        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            # 🛑 Crucially, cancel tasks before running exit actions.
            await self._cancel_state_tasks(state)
            # ⚙️ Then, run the synchronous exit actions.
            await self._execute_actions(state.exit, trigger_event)
            # 🗑️ Finally, remove from the active set.
            self._active_state_nodes.discard(state)

    # -------------------------------------------------------------------------
    # 🔎 State Evaluation & Pathfinding Helpers
    # -------------------------------------------------------------------------

    def _is_state_done(self, state_node: StateNode) -> bool:
        """Recursively determines if a compound or parallel state is "done".

        This is a key part of the SCXML algorithm for `onDone` transitions.
        - A state with `type: 'final'` is always done.
        - A `compound` state is done if its currently active child state is done.
        - A `parallel` state is done only if ALL of its child regions are done.

        Args:
            state_node (StateNode): The state to check for completion.

        Returns:
            bool: `True` if the state is considered "done", otherwise `False`.
        """
        # 🏁 Base case: A final state is inherently "done".
        if state_node.is_final:
            return True

        # 🧠 Compound state: Its "doneness" is determined by its active child.
        if state_node.type == "compound":
            active_child = next(
                (
                    s
                    for s in self._active_state_nodes
                    if s.parent == state_node
                ),
                None,
            )
            # If no child is active, it cannot be done.
            if not active_child:
                return False
            # Recursively check the child, handling nested complex states.
            return self._is_state_done(active_child)

        # 🌐 Parallel state: All child regions must be independently "done".
        if state_node.type == "parallel":
            for region in state_node.states.values():
                active_in_region = [
                    d
                    for d in self._active_state_nodes
                    if self._is_descendant(d, region)
                ]
                # If a region is not active, the parallel state is not done.
                if not active_in_region:
                    return False
                # The region itself is "done" if any of its active states are done.
                if not any(self._is_state_done(d) for d in active_in_region):
                    return False
            # If all regions passed the check, the parallel state is done.
            return True

        # For atomic, non-final states.
        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Bubbles up from a final state to fire parent `onDone` transitions.

        When a state machine enters a `final` state, this method is called to
        check if the parent (or any ancestor) is now considered "done"
        according to `_is_state_done`. If so, it dispatches the corresponding
        `done.state.*` event to trigger the `onDone` transition.

        Args:
            final_state (StateNode): The final state that was just entered.
        """
        ancestor = final_state.parent
        while ancestor:
            if ancestor.on_done and self._is_state_done(ancestor):
                logger.info(
                    "🎉 State '%s' is done, firing onDone event.", ancestor.id
                )
                # 📨 Create and send the synthetic `done.state.*` event.
                done_event = Event(type=f"done.state.{ancestor.id}")
                await self.send(done_event)
                # Per SCXML, only fire for the first completed ancestor.
                return
            ancestor = ancestor.parent

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the most specific, eligible transition for an event.

        This implements the SCXML rule for transition selection: choose the
        transition defined on the most deeply nested active state that matches
        the event and satisfies its guard condition. This ensures that child
        states can override the behavior of their parents.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event being processed.

        Returns:
            Optional[TransitionDefinition]: The highest-priority transition
            that should be taken, or `None` if no eligible transition is found.
        """
        eligible_transitions: List[TransitionDefinition] = []

        # 1️⃣ Sort active states by depth (most specific first).
        sorted_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: len(s.id),
            reverse=True,
        )

        # 2️⃣ Determine if we should check for transient ("always") transitions.
        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        # 3️⃣ Traverse up the tree from each active leaf node.
        for state in sorted_nodes:
            current: Optional[StateNode] = state
            while current:
                # Check standard `on` event transitions.
                if (
                    not is_explicit_transient_event
                    and event.type in current.on
                ):
                    for t in current.on[event.type]:
                        if self._is_guard_satisfied(t.guard, event):
                            eligible_transitions.append(t)

                # Check transient `""` (always) transitions.
                if is_transient_check and "" in current.on:
                    for t in current.on[""]:
                        if self._is_guard_satisfied(t.guard, event):
                            eligible_transitions.append(t)

                # Check `onDone` transitions for compound/parallel states.
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(current.on_done.guard, event):
                        eligible_transitions.append(current.on_done)

                # Check `after` transitions for timed events.
                if isinstance(event, AfterEvent):
                    for transitions in current.after.values():
                        for t in transitions:
                            if (
                                t.event == event.type
                                and self._is_guard_satisfied(t.guard, event)
                            ):
                                eligible_transitions.append(t)

                # Check `onDone`/`onError` for invoked services.
                if isinstance(event, DoneEvent):
                    for inv in current.invoke:
                        if event.src == inv.id:
                            for t in inv.on_done + inv.on_error:
                                if (
                                    t.event == event.type
                                    and self._is_guard_satisfied(
                                        t.guard, event
                                    )
                                ):
                                    eligible_transitions.append(t)
                current = current.parent

        if not eligible_transitions:
            return None

        # 🏆 The winning transition is the one defined on the deepest state.
        return max(
            eligible_transitions, key=lambda t: len(t.source.id)  # noqa
        )  # noqa

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Calculates the transition domain (LCCA) for an external transition.

        The "domain" is the least common compound ancestor (LCCA) of the source
        and target states. It determines which states are exited and entered.

        A key feature of this implementation is that if the target state cannot
        be immediately resolved (e.g., using a shorthand like `"sibling_state"`),
        it does not fail. Instead, it conservatively falls back to the source's
        parent as the domain, deferring final resolution to `_process_event`.

        Args:
            transition (TransitionDefinition): The external transition to analyze.

        Returns:
            Optional[StateNode]: The state node that is the LCCA, or None if the
            root is the domain.
        """
        # 🩹 Late imports to avoid circular dependency issues.
        from .exceptions import StateNotFoundError
        from .resolver import resolve_target_state

        parent = transition.source.parent or self.machine

        # 1️⃣ Attempt a quick resolution of the target state.
        try:
            target_state = resolve_target_state(
                transition.target_str, transition.source
            )
        except StateNotFoundError:
            # If it fails, defer by using the parent as a safe domain.
            logger.debug(
                "⏳ Target '%s' not immediately resolvable. Deferring domain calculation.",
                transition.target_str,
            )
            return parent

        # 2️⃣ An external self-transition's domain is always the parent.
        if target_state == transition.source:
            return parent

        # 3️⃣ Standard case: Compute the Least Common Compound Ancestor.
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)
        common_ancestors = source_ancestors & target_ancestors

        if not common_ancestors:
            return parent  # Fallback to parent (or root) if no commonality.

        # The LCCA is the common ancestor with the longest (deepest) ID.
        return max(common_ancestors, key=lambda n: len(n.id))

    @staticmethod
    def _get_path_to_state(
        to_state: StateNode, *, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Builds the ordered list of states to enter to reach a target.

        This method traces the ancestry from the target state (`to_state`) up
        to, but not including, a specified `stop_at` ancestor (typically the
        transition domain). The resulting path is then reversed to provide the
        correct parent-to-child entry order.

        Args:
            to_state (StateNode): The destination state.
            stop_at (Optional[StateNode]): The ancestor at which to stop
                traversing.

        Returns:
            List[StateNode]: A list of states to be entered, from outermost
            to innermost.
        """
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        # Reverse to get parent -> child order for correct state entry.
        path.reverse()
        return path

    @staticmethod
    def _get_ancestors(node: StateNode) -> Set[StateNode]:
        """Gets the set of all ancestors of a node, including the node itself.

        Args:
            node (StateNode): The node from which to find ancestors.

        Returns:
            Set[StateNode]: A set containing the node and all of its parents.
        """
        ancestors: Set[StateNode] = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """Checks if a node is a descendant of a specified ancestor.

        A node is considered a descendant of another if its ID starts with the
        ancestor's ID followed by a dot, or if it is the ancestor itself.

        Args:
            node (StateNode): The potential descendant node.
            ancestor (Optional[StateNode]): The potential ancestor node. If
                `None`, it represents the machine root, and this method will
                always return `True`.

        Returns:
            bool: `True` if `node` is a descendant of `ancestor`.
        """
        # If no ancestor is specified, it's the machine root, so all nodes are descendants.
        if not ancestor:
            return True
        # Check for self or if the ID indicates a child relationship.
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    # -------------------------------------------------------------------------
    # 🛡️ Task & Guard Management
    # -------------------------------------------------------------------------

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules `after` and `invoke` tasks for a state upon its entry.

        This method dispatches to the abstract `_after_timer` and
        `_invoke_service` methods, which are implemented by the concrete
        sync/async subclasses to handle the actual execution.

        Args:
            state (StateNode): The state being entered.
        """
        # 🕒 Schedule `after` timers.
        for delay_ms, transitions in state.after.items():
            for t_def in transitions:
                delay_sec = float(delay_ms) / 1000.0
                after_event = AfterEvent(type=t_def.event)
                self._after_timer(delay_sec, after_event, owner_id=state.id)
                logger.debug(
                    "🕒 Scheduled 'after' event '%s' in %.2fs for state '%s'.",
                    t_def.event,
                    delay_sec,
                    state.id,
                )

        # 📞 Schedule `invoke` services.
        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            # 💥 Fail-fast if the service implementation is missing.
            if service_callable is None:
                # FIX: Reverted error message to match test suite expectations.
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' referenced by "
                    f"state '{state.id}' is not registered."
                )
            self._invoke_service(
                invocation, service_callable, owner_id=state.id
            )
            logger.debug(
                "📞 Invoking service '%s' for state '%s'.",
                invocation.src,
                state.id,
            )

    def _is_guard_satisfied(
        self,
        guard_name: Optional[str],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Checks if a guard condition (a synchronous, pure function) is met.

        Guard functions receive the current context and event, and must return
        `True` (allow transition) or `False` (block transition).

        Args:
            guard_name (Optional[str]): The name of the guard function to
                execute. If `None`, the guard is considered to have passed.
            event (Union[Event, AfterEvent, DoneEvent]): The current event
                being processed, which is passed to the guard function.

        Returns:
            bool: `True` if the guard passes or if there is no guard, `False`
            otherwise.

        Raises:
            ImplementationMissingError: If a `guard_name` is provided but no
                corresponding function is found in the machine's logic.
        """
        # ✅ A transition without a guard is always allowed.
        if not guard_name:
            return True

        # 🔍 Find the guard function in the machine's logic.
        guard_callable = self.machine.logic.guards.get(guard_name)
        if not guard_callable:
            # FIX: Reverted error message to match test suite expectations.
            raise ImplementationMissingError(
                f"Guard '{guard_name}' not implemented."
            )

        # 🏃 Execute the guard function.
        result = guard_callable(self.context, event)
        logger.info(
            "🛡️  Evaluating guard '%s': %s",
            guard_name,
            "✅ Passed" if result else "❌ Failed",
        )

        # 🔔 Notify any registered plugins about the evaluation.
        for plugin in self._plugins:
            plugin.on_guard_evaluated(self, guard_name, event, result)

        return result
