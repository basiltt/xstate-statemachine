# /src/xstate_statemachine/models.py
# -----------------------------------------------------------------------------
# 🏛️ State Machine Model Definitions
# -----------------------------------------------------------------------------
# This module defines the core data structures that represent a state machine's
# configuration in memory. It uses a class-based, object-oriented approach to
# parse and build a traversable tree from a JSON or dictionary configuration,
# adhering to XState conventions.
#
# The primary classes are:
#   - `StateNode`: Represents a single state (atomic, compound, parallel, or final).
#     This class, along with its children, forms a Composite design pattern,
#     creating a tree structure for the entire statechart.
#   - `MachineNode`: A specialized `StateNode` that acts as the root of the
#     state machine tree, providing machine-wide utilities.
#   - `ActionDefinition`, `TransitionDefinition`, `InvokeDefinition`: These are
#     data-holding classes that represent the executable or dynamic parts of
#     the state machine, such as actions, transitions, and services.
#
# This structured representation enables robust validation, introspection, and
# serves as the foundation for the interpreter to execute the machine's logic.
# -----------------------------------------------------------------------------

import logging
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    TypeVar,
    Union,
)

from .events import Event
from .exceptions import InvalidConfigError, StateNotFoundError
from .machine_logic import MachineLogic
from .resolver import resolve_target_state

# 🪵 Initialize the logger for this module
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🧬 Type Variables & Generics
# -----------------------------------------------------------------------------
# Using TypeVars allows for creating generic machine definitions. This provides
# a foundation for full static type checking of a machine's context and events,
# leading to more robust and self-documenting code.
# -----------------------------------------------------------------------------

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

# Define a specific type for state types for clarity and reuse.
StateType = Literal["atomic", "compound", "parallel", "final"]


# -----------------------------------------------------------------------------
# 🎬 Action & Transition Models
# -----------------------------------------------------------------------------
# These classes serve as the data structures for representing the executable
# parts of the state machine, such as actions, transitions, and invocations.
# They provide a standardized, object-oriented way to interact with the parsed
# JSON configuration.
# -----------------------------------------------------------------------------


class ActionDefinition:
    """Represents a single action to be executed within the state machine.

    This class standardizes the representation of an action defined in the
    machine's configuration, accommodating both shorthand string definitions
    and more detailed object definitions that can include parameters.

    Attributes:
        type (str): The name or type identifier of the action.
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters
                                           associated with the action.
    """

    def __init__(self, config: Union[str, Dict[str, Any]]):
        """Initializes the ActionDefinition by parsing its configuration.

        Args:
            config (Union[str, Dict[str, Any]]): The action configuration.
                It can be a `str` (action name) or a `Dict` (action object).

        Raises:
            InvalidConfigError: If the config is not a string or dictionary.
        """
        if isinstance(config, str):
            logger.debug(
                "🔧 Parsing action definition from string: '%s'", config
            )
            self.type: str = config
            self.params: Optional[Dict[str, Any]] = None
        elif isinstance(config, dict):
            logger.debug("🔧 Parsing action definition from dict: %s", config)
            self.type: str = config.get("type", "UnknownAction")
            self.params: Optional[Dict[str, Any]] = config.get("params")
        else:
            logger.error(
                "❌ Invalid action configuration type: %s (expected str or dict)",
                type(config),
            )
            raise InvalidConfigError(
                f"Action definition must be a string or a dictionary, got {type(config)}"
            )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Action(type='{self.type}')"


class TransitionDefinition:
    """Represents a potential transition between states for a given event.

    It holds all information about a transition, including its target state,
    the actions to execute, and any conditional guard.

    Attributes:
        event (str): The name of the event that triggers this transition.
        source (StateNode): The source `StateNode` where this transition originates.
        target_str (Optional[str]): The string representation of the target state.
        actions (List[ActionDefinition]): A list of actions to execute on this transition.
        guard (Optional[str]): The name of the guard condition to evaluate.
    """

    def __init__(
        self,
        event: str,
        config: Dict[str, Any],
        source: "StateNode",
        actions: Optional[List[ActionDefinition]] = None,
    ):
        """Initializes the TransitionDefinition.

        Args:
            event (str): The name of the event that triggers this transition.
            config (Dict[str, Any]): The dictionary defining the transition's
                                     properties (target, guard).
            source (StateNode): The `StateNode` where this transition is defined.
            actions (Optional[List[ActionDefinition]]): A list of actions.
                Default values to an empty list if not provided.
        """
        logger.debug(
            "🔧 Creating transition for event '%s' from config: %s",
            event,
            config,
        )
        self.event: str = event
        self.source: "StateNode" = source
        self.target_str: Optional[str] = config.get("target")
        # ✅ FIX: Default to an empty list if actions are None.
        self.actions: List[ActionDefinition] = (
            actions if actions is not None else []
        )
        self.guard: Optional[str] = config.get("guard")

        logger.debug(
            "✅ Created TransitionDefinition: event='%s', target='%s', actions=%d, guard='%s'",
            self.event,
            self.target_str,
            len(self.actions),
            self.guard,
        )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Transition(event='{self.event}', target='{self.target_str}')"


class InvokeDefinition:
    """Represents an invoked service or child actor within a state.

    Attributes:
        id (str): The unique identifier for this invocation instance.
        src (Optional[str]): The name of the service to be invoked.
        input (Optional[Dict[str, Any]]): Data to pass to the invoked service.
        on_done (List[TransitionDefinition]): Transitions for successful completion.
        on_error (List[TransitionDefinition]): Transitions for errors.
        source (StateNode): The `StateNode` that hosts this invocation.
    """

    def __init__(
        self,
        invoke_id: str,
        config: Dict[str, Any],
        source: "StateNode",
        on_done: List[TransitionDefinition],
        on_error: List[TransitionDefinition],
    ):
        """Initializes the InvokeDefinition.

        Args:
            invoke_id (str): The pre-calculated unique ID for the invocation.
            config (Dict[str, Any]): The raw dictionary from the `invoke` key.
            source (StateNode): The `StateNode` that hosts this invocation.
            on_done (List[TransitionDefinition]): Pre-parsed 'onDone' transitions.
            on_error (List[TransitionDefinition]): Pre-parsed 'onError' transitions.
        """
        logging.debug(
            "🔧 Creating invoke definition for source state '%s' with config: %s",
            source.id,
            config,
        )
        self.id: str = invoke_id
        self.src: Optional[str] = config.get("src")
        self.input: Optional[Dict[str, Any]] = config.get("input")
        self.source: "StateNode" = source
        self.on_done: List[TransitionDefinition] = on_done
        self.on_error: List[TransitionDefinition] = on_error

        if not self.src:
            logging.warning(
                "⚠️ Invoke definition in state '%s' is missing a 'src' property.",
                self.source.id,
            )
        logging.debug("✅ Created InvokeDefinition with ID '%s'", self.id)

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Invoke(id='{self.id}', src='{self.src}')"


# -----------------------------------------------------------------------------
# 🌳 Core State Tree Models
# -----------------------------------------------------------------------------
# The `StateNode` and `MachineNode` classes implement the Composite design
# pattern to build a traversable graph (a tree) of the state machine's
# structure from the parsed JSON configuration.
# -----------------------------------------------------------------------------


class StateNode(Generic[TContext, TEvent]):
    """Represents a single state in the state machine graph.

    A `StateNode` can be atomic, compound, parallel, or final. It encapsulates
    all its own behavior, including transitions, actions, services, and child states.

    Attributes:
        key (str): The local key of the state within its parent (e.g., "idle").
        parent (Optional[StateNode]): The parent `StateNode`, or `None` for the root.
        machine (MachineNode): A reference to the root `MachineNode`.
        id (str): The fully qualified, unique ID of the state (e.g., "machine.parent.child").
        type (StateType): The type of the state.
        initial (Optional[str]): The key of the initial substate for compound states.
        on (Dict[str, List[TransitionDefinition]]): Event-to-transition mappings.
        on_done (Optional[TransitionDefinition]): Transition for when a state is "done".
        after (Dict[int, List[TransitionDefinition]]): Delayed transitions.
        entry (List[ActionDefinition]): Actions to execute upon entering this state.
        exit (List[ActionDefinition]): Actions to execute upon exiting this state.
        invoke (List[InvokeDefinition]): Services to invoke when entering this state.
        states (Dict[str, StateNode]): Child state key-to-`StateNode` mappings.
    """

    def __init__(
        self,
        machine: "MachineNode",
        config: Dict[str, Any],
        key: str,
        parent: Optional["StateNode"] = None,
    ):
        """Initializes a StateNode and its subtree from a configuration dictionary.

        Args:
            machine (MachineNode): The root machine node.
            config (Dict[str, Any]): The configuration dictionary for this state.
            key (str): The key for this state within its parent's `states` object.
            parent (Optional[StateNode]): The parent state node, if any.
        """
        logger.debug(
            "🚀 Initializing StateNode: key='%s', parent_id='%s'",
            key,
            parent.id if parent else "ROOT",
        )
        self.key: str = key
        self.parent: Optional["StateNode"] = parent
        self.machine: "MachineNode" = machine
        self.id: str = f"{parent.id}.{key}" if parent else key

        # ⚙️ Determine and strictly type the state's type.
        self.type: StateType
        if "states" in config:
            state_type = config.get("type", "compound")
            if state_type not in ["compound", "parallel"]:
                logger.warning(
                    "⚠️ Invalid 'type' ('%s') for state '%s' with children. Defaulting to 'compound'.",
                    state_type,
                    self.id,
                )
                self.type = "compound"
            else:
                self.type = state_type  # type: ignore
        elif config.get("type") == "final":
            self.type = "final"
        else:
            self.type = "atomic"
        logger.debug(
            "  -> StateNode '%s' identified as type: '%s'", self.id, self.type
        )

        # ⚙️ Parse all properties. The parsing logic is now encapsulated here.
        self.initial: Optional[str] = self._parse_initial(config)
        self.on: Dict[str, List[TransitionDefinition]] = self._parse_on(config)
        self.on_done: Optional[TransitionDefinition] = self._parse_on_done(
            config
        )
        self.after: Dict[int, List[TransitionDefinition]] = self._parse_after(
            config
        )
        self.entry: List[ActionDefinition] = self._parse_actions(
            config.get("entry")
        )
        self.exit: List[ActionDefinition] = self._parse_actions(
            config.get("exit")
        )
        self.invoke: List[InvokeDefinition] = self._parse_invoke(config)

        #  Recursively build child states.
        self.states: Dict[str, "StateNode"] = {
            state_key: StateNode(machine, state_config, state_key, self)
            for state_key, state_config in config.get("states", {}).items()
        }
        logger.debug("✅ StateNode '%s' initialized successfully.", self.id)

    # -------------------------------------------------------------------------
    # Internal Parsing Methods (Encapsulated Logic)
    # -------------------------------------------------------------------------

    def _parse_initial(self, config: Dict[str, Any]) -> Optional[str]:
        """Parses the initial state key from the config."""
        initial = config.get("initial")
        if self.type == "compound" and not initial:
            logger.warning(
                "⚠️ Compound state '%s' is missing an 'initial' state.", self.id
            )
        return initial

    def _parse_actions(self, config: Optional[Any]) -> List[ActionDefinition]:
        """Parses an action or list of actions from config."""
        if not config:
            return []
        return [ActionDefinition(a) for a in self._ensure_list(config)]

    def _parse_on(
        self, config: Dict[str, Any]
    ) -> Dict[str, List[TransitionDefinition]]:
        """Parses all event transitions from the 'on' property."""  # noqa: E501
        on_map: Dict[str, List[TransitionDefinition]] = {}
        for event, transitions_config in config.get("on", {}).items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            on_map[event] = [
                self._create_transition(event, t_config)
                for t_config in normalized_configs
            ]
            logger.debug(
                "  -> Parsed %d transitions for event '%s'",
                len(on_map[event]),
                event,
            )
        return on_map

    def _parse_on_done(
        self, config: Dict[str, Any]
    ) -> Optional[TransitionDefinition]:
        """Parses the 'onDone' transition for a compound/parallel state."""
        on_done_config = config.get("onDone")
        if not on_done_config:
            return None

        normalized_list = self._normalize_transitions(on_done_config)
        if not normalized_list:
            return None

        transition = self._create_transition(
            f"done.state.{self.id}", normalized_list[0]
        )
        logger.debug(
            "  -> Parsed onDone transition with target: '%s'",
            transition.target_str,
        )
        return transition

    def _parse_after(
        self, config: Dict[str, Any]
    ) -> Dict[int, List[TransitionDefinition]]:
        """Parses all delayed transitions from the 'after' property."""
        after_map: Dict[int, List[TransitionDefinition]] = {}
        for delay, transitions_config in config.get("after", {}).items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            after_map[int(delay)] = [
                self._create_transition(f"after.{delay}.{self.id}", t_config)
                for t_config in normalized_configs
            ]
        return after_map

    def _parse_invoke(self, config: Dict[str, Any]) -> List[InvokeDefinition]:
        """Parses all invoked services from the 'invoke' property."""
        invoke_configs = self._ensure_list(config.get("invoke", []))
        invokes: List[InvokeDefinition] = []
        for i_config in invoke_configs:
            if not isinstance(i_config, dict):
                continue
            invoke_id = i_config.get("id", self.id)
            on_done_transitions = [
                self._create_transition(f"done.invoke.{invoke_id}", t)
                for t in self._normalize_transitions(
                    i_config.get("onDone", [])
                )
            ]
            on_error_transitions = [
                self._create_transition(f"error.platform.{invoke_id}", t)
                for t in self._normalize_transitions(
                    i_config.get("onError", [])
                )
            ]
            invokes.append(
                InvokeDefinition(
                    invoke_id=invoke_id,
                    config=i_config,
                    source=self,
                    on_done=on_done_transitions,
                    on_error=on_error_transitions,
                )
            )
        return invokes

    def _create_transition(
        self, event: str, config: Dict[str, Any]
    ) -> TransitionDefinition:
        """Factory method to create a TransitionDefinition, handling action parsing."""
        actions = self._parse_actions(config.get("actions"))
        return TransitionDefinition(
            event=event, config=config, source=self, actions=actions
        )

    # -------------------------------------------------------------------------
    # Static Helpers (for internal use by the class)
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_transitions(config: Any) -> List[Dict[str, Any]]:
        """Ensures transition configs are always a list of dictionaries."""
        if isinstance(config, str):
            return [{"target": config}]
        if isinstance(config, dict):
            return [config]
        if isinstance(config, list):
            normalized_list = []
            for item in config:
                if isinstance(item, str):
                    normalized_list.append({"target": item})
                elif isinstance(item, dict):
                    normalized_list.append(item)
                else:
                    raise InvalidConfigError(
                        f"❌ Invalid transition item in list: {item}. Must be str or dict."
                    )
            return normalized_list
        if config is not None:
            raise InvalidConfigError(
                f"❌ Invalid transition config: {config}. Must be str, dict, or list."
            )
        return []

    @staticmethod
    def _ensure_list(config_item: Any) -> List[Any]:
        """A simple helper to ensure a configuration item is always a list."""
        if config_item is None:
            return []
        return config_item if isinstance(config_item, list) else [config_item]

    # -------------------------------------------------------------------------
    # Public Properties & Representations
    # -------------------------------------------------------------------------

    @property
    def is_atomic(self) -> bool:
        """Returns `True` if the state has no child states."""
        return self.type == "atomic"

    @property
    def is_final(self) -> bool:
        """Returns `True` if the state is a final state."""
        return self.type == "final"

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"StateNode(id='{self.id}', type='{self.type}')"

    # -------------------------------------------------------------------------
    # Tree Traversal Helpers
    # -------------------------------------------------------------------------

    def _get_ancestors(self) -> Set["StateNode"]:
        """Gets a set of all ancestors of a node, including the node itself."""
        ancestors: Set["StateNode"] = set()
        current: Optional[StateNode] = self
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(
        node: "StateNode", ancestor: Optional["StateNode"]
    ) -> bool:
        """Checks if a node is a descendant of a specified ancestor."""
        if not ancestor:
            return True
        return node == ancestor or node.id.startswith(f"{ancestor.id}.")

    def _get_path_to_state(  # noqa
        self,
        to_state: "StateNode",
        *,
        stop_at: Optional["StateNode"] = None,
    ) -> List["StateNode"]:
        """Builds the list of states to enter to reach a target state."""
        path: List["StateNode"] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        path.reverse()
        return path


class MachineNode(StateNode[TContext, TEvent]):
    """The root node of a state machine, with added developer utilities.

    Attributes:
        logic (MachineLogic): The implementation for the machine's logic.
        initial_context (TContext): The initial context of the machine.
    """

    def __init__(
        self, config: Dict[str, Any], logic: MachineLogic[TContext, TEvent]
    ):
        """Initializes the root MachineNode and builds the entire state tree.

        Args:
            config (Dict[str, Any]): The root JSON configuration of the machine.
            logic (MachineLogic[TContext, TEvent]): The implementation of logic.

        Raises:
            InvalidConfigError: If the machine configuration lacks a root 'id'.
        """
        if not config.get("id"):
            raise InvalidConfigError(
                "❌ Machine configuration must have a root 'id'."
            )
        self.logic: MachineLogic[TContext, TEvent] = logic
        self.initial_context: TContext = config.get("context", {})
        super().__init__(self, config, config["id"])

    def get_state_by_id(self, state_id: str) -> Optional[StateNode]:
        """Finds a state node by its full ID, returning None if not found.

        Args:
            state_id (str): The fully qualified ID of the state to find.

        Returns:
            Optional[StateNode]: The `StateNode` if found, otherwise `None`.
        """
        logger.debug("🔍 Searching for state with ID: '%s'", state_id)
        path = state_id.split(".")

        if not path or path[0] != self.key:
            logger.warning(
                "⚠️ State ID '%s' does not start with machine ID '%s'. Lookup will fail.",
                state_id,
                self.key,
            )
            return None

        node: StateNode = self
        for key in path[1:]:
            if key not in node.states:
                logger.warning(
                    "❌ State not found. Could not find key '%s' in state '%s'.",
                    key,
                    node.id,
                )
                return None
            node = node.states[key]

        logger.debug("✅ Found state: %s", node)
        return node

    # -------------------------------------------------------------------------
    # 🧪 Testing Utilities
    # -------------------------------------------------------------------------

    def get_next_state(
        self, from_state_id: str, event: Event
    ) -> Optional[Set[str]]:
        """Calculates the target state(s) for an event without executing actions.

        This is a pure function for testing transition logic. It finds the first
        valid transition by bubbling up the state hierarchy.
        Note: This utility does not evaluate guards.

        Args:
            from_state_id (str): The ID of the current state.
            event (Event): The event to process.

        Returns:
            Optional[Set[str]]: A set of target state IDs, or `None` if no
                                transition is found.
        """
        from_node = self.get_state_by_id(from_state_id)
        if not from_node:
            return None

        current: Optional[StateNode] = from_node
        while current:
            if event.type in current.on:
                for transition in current.on[event.type]:
                    if transition.target_str:
                        try:
                            target_node = resolve_target_state(
                                transition.target_str, current
                            )
                            return {target_node.id}
                        except StateNotFoundError:
                            pass
            current = current.parent

        return None

    # -------------------------------------------------------------------------
    # 🎨 Visualization Utilities
    # -------------------------------------------------------------------------

    def to_plantuml(self) -> str:
        """Generates a PlantUML string representation of the state machine.

        Returns:
            str: A string formatted for PlantUML.
        """
        content = ["@startuml", "hide empty description"]

        def build_puml_states(node: StateNode, level: int):
            indent = "  " * level
            safe_id = node.id.replace(".", "_")
            if node.states:
                content.append(f'{indent}state "{node.key}" as {safe_id} {{')
                if node.initial and node.states.get(node.initial):
                    initial_target_id = node.states[node.initial].id.replace(
                        ".", "_"
                    )
                    content.append(f"{indent}  [*] --> {initial_target_id}")
                for child in node.states.values():
                    build_puml_states(child, level + 1)
                content.append(f"{indent}}}")
            else:
                content.append(f'{indent}state "{node.key}" as {safe_id}')

        build_puml_states(self, 0)

        def build_puml_transitions(node: StateNode):
            source_id = node.id.replace(".", "_")
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = resolve_target_state(
                                t.target_str, node
                            )
                            target_id = target_node.id.replace(".", "_")
                            content.append(
                                f"{source_id} --> {target_id} : {event}"
                            )
                        except StateNotFoundError:
                            pass
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = resolve_target_state(
                        node.on_done.target_str, node
                    )
                    target_id = target_node.id.replace(".", "_")
                    content.append(f"{source_id} --> {target_id} : onDone")
                except StateNotFoundError:
                    pass
            for child in node.states.values():
                build_puml_transitions(child)

        if self.initial and self.states.get(self.initial):
            initial_id = self.states[self.initial].id.replace(".", "_")
            content.append(f"[*] --> {initial_id}")
        build_puml_transitions(self)

        content.append("@enduml")
        return "\n".join(content)

    def to_mermaid(self) -> str:
        """Generates a Mermaid.js string representation of the state machine.

        Returns:
            str: A string formatted for Mermaid.js.
        """
        content = ["stateDiagram-v2"]

        def build_mmd_states(node: StateNode, level: int):
            indent = "    " * level
            if node.states:
                content.append(f'{indent}state "{node.key}" as {node.key} {{')
                if node.initial and node.states.get(node.initial):
                    initial_key = node.states[node.initial].key
                    content.append(f"{indent}    [*] --> {initial_key}")
                for child in node.states.values():
                    build_mmd_states(child, level + 1)
                content.append(f"{indent}}}")

        def build_mmd_transitions(node: StateNode):
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = resolve_target_state(
                                t.target_str, node
                            )
                            content.append(
                                f"{node.key} --> {target_node.key} : {event}"
                            )
                        except StateNotFoundError:
                            pass
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = resolve_target_state(
                        node.on_done.target_str, node
                    )
                    content.append(
                        f"{node.key} --> {target_node.key} : onDone"
                    )
                except StateNotFoundError:
                    pass
            for child in node.states.values():
                build_mmd_transitions(child)

        if self.initial and self.states.get(self.initial):
            content.append(f"[*] --> {self.states[self.initial].key}")
        build_mmd_states(self, 0)
        build_mmd_transitions(self)

        return "\n".join(content)
