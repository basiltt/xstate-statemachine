# src/xstate_statemachine/models.py
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

# Initialize the logger for this module
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
        """Initializes the ActionDefinition.

        Parses the provided configuration to extract the action type and any
        associated parameters.

        Args:
            config: The action configuration. It can be:
                    - A `str`: representing the action's name (e.g., "myAction").
                    - A `Dict[str, Any]`: an object definition with a "type" key
                      and an optional "params" key (e.g., {"type": "myAction",
                      "params": {"value": 42}}).
        """
        if isinstance(config, str):
            # ✅ Handle shorthand string definition (e.g., "myAction").
            logger.debug("Parsing action definition from string: '%s'", config)
            self.type: str = config
            self.params: Optional[Dict[str, Any]] = None
        elif isinstance(config, dict):
            # ✅ Handle object definition (e.g., {"type": "myAction", "params": {...}}).
            logger.debug("Parsing action definition from dict: %s", config)
            self.type: str = config.get("type", "UnknownAction")
            self.params: Optional[Dict[str, Any]] = config.get("params")
        else:
            # ❌ Invalid configuration type
            logger.error(
                "❌ Invalid action configuration type: %s (expected str or dict)",
                type(config),
            )
            raise InvalidConfigError(
                f"Action definition must be a string or a dictionary, got {type(config)}"
            )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation of the ActionDefinition.

        Returns:
            str: A string showing the action type.
        """
        return f"Action(type='{self.type}')"


class TransitionDefinition:
    """Represents a potential transition between states for a given event.

    It holds all information about a transition, including its target, the
    actions to execute, and any conditional guard.
    """

    def __init__(
        self, event: str, config: Dict[str, Any], source: "StateNode"
    ):
        """Initializes the TransitionDefinition.

        Args:
            event (str): The name of the event that triggers this transition.
            config (Dict[str, Any]): The dictionary defining the transition's properties.
            source (StateNode): The `StateNode` where this transition is defined.
        """
        logger.debug(
            "Parsing transition for event '%s' from config: %s", event, config
        )
        self.event: str = event
        self.source: "StateNode" = source
        self.target_str: Optional[str] = config.get("target")

        # Parse actions, ensuring they are always a list of ActionDefinition objects
        actions_config = config.get("actions", [])
        self.actions: List[ActionDefinition] = [
            ActionDefinition(a) for a in StateNode._ensure_list(actions_config)
        ]
        self.guard: Optional[str] = config.get("guard")
        logger.debug(
            "Created TransitionDefinition: event='%s', target='%s', actions=%d, guard='%s'",
            self.event,
            self.target_str,
            len(self.actions),
            self.guard,
        )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation of the TransitionDefinition.

        Returns:
            str: A string showing the event and target state.
        """
        return f"Transition(event='{self.event}', target='{self.target_str}')"


class InvokeDefinition:
    """Represents an invoked service or child actor within a state.

    An invoked service or actor is a long-running process that is started
    when its host state is entered and can communicate back to the state machine.
    This class models the configuration for such invocations, including the
    source of the service/actor and handlers for its completion or error.

    Attributes:
        id (str): The unique identifier for this invocation instance. If not
                  explicitly provided in the config, it defaults to the ID of
                  the `source` state.
        src (Optional[str]): The name of the service or machine to be invoked,
                             which should be defined in `MachineLogic.services`.
        input (Optional[Dict[str, Any]]): Optional data to pass as input to the
                                          invoked service/actor.
        on_done (List[TransitionDefinition]): A list of `TransitionDefinition`
                                             objects that are evaluated when
                                             the invoked service/actor completes
                                             successfully.
        on_error (List[TransitionDefinition]): A list of `TransitionDefinition`
                                              objects that are evaluated when
                                              the invoked service/actor encounters
                                              an error.
        source (StateNode): The `StateNode` that hosts this invocation.
    """

    def __init__(self, config: Dict[str, Any], source: "StateNode"):
        """Initializes the InvokeDefinition.

        This constructor robustly parses `onDone` and `onError` handlers,
        accommodating all valid XState shorthand syntaxes by utilizing the
        `_normalize_transitions` helper.

        Args:
            config (Dict[str, Any]): The dictionary from the `invoke` key in
                                     the machine configuration.
            source (StateNode): The `StateNode` that hosts this invocation.
                                Used for default ID and relative target resolution.
        """
        logging.debug(
            "Parsing invoke definition for source state '%s' with config: %s",
            source.id,
            config,
        )
        self.id: str = config.get(
            "id", source.id
        )  # Default ID to source state ID
        self.src: Optional[str] = config.get("src")
        self.input: Optional[Dict[str, Any]] = config.get("input")
        self.source: "StateNode" = (
            source  # ✅ FIX: Store the source StateNode directly
        )

        # Parse onDone transitions
        on_done_config = config.get("onDone", [])
        # Call to StateNode._normalize_transitions requires StateNode class to be fully loaded
        # This assumes _normalize_transitions exists as a static method on StateNode
        normalized_on_done_configs = StateNode._normalize_transitions(
            on_done_config
        )
        self.on_done: List[TransitionDefinition] = [
            TransitionDefinition(f"done.invoke.{self.id}", t_config, source)
            for t_config in normalized_on_done_configs
        ]
        logging.debug(
            "   Parsed %d onDone transitions for invoke ID '%s'",
            len(self.on_done),
            self.id,
        )

        # Parse onError transitions
        on_error_config = config.get("onError", [])
        # Call to StateNode._normalize_transitions requires StateNode class to be fully loaded
        normalized_on_error_configs = StateNode._normalize_transitions(
            on_error_config
        )
        self.on_error: List[TransitionDefinition] = [
            TransitionDefinition(f"error.platform.{self.id}", t_config, source)
            for t_config in normalized_on_error_configs
        ]
        logging.debug(
            "   Parsed %d onError transitions for invoke ID '%s'",
            len(self.on_error),
            self.id,
        )

        if not self.src:
            logging.warning(
                "⚠️ Invoke definition '%s' is missing a 'src' property.",
                self.id,
            )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation of the InvokeDefinition.

        Returns:
            str: A string showing the invoke ID and source.
        """
        return f"Invoke(id='{self.id}', src='{self.src}')"


# -----------------------------------------------------------------------------
# 🌳 Core State Tree Models
# -----------------------------------------------------------------------------
# The `StateNode` and `MachineNode` classes implement the Composite design
# pattern to build a traversable graph (a tree) of the state machine's
# structure from the parsed JSON. `StateNode` represents an individual state
# or composite state, while `MachineNode` is the root of this hierarchy,
# providing overall machine-level utilities.
# -----------------------------------------------------------------------------


class StateNode(Generic[TContext, TEvent]):
    """Represents a single state in the state machine graph.

    A `StateNode` can be atomic (no children), compound (has children, one active at a time),
    parallel (has children, all active concurrently), or final (marks completion of a parent).
    It encapsulates its own transitions, entry/exit actions, invoked services, and child states.

    Attributes:
        key (str): The local key of the state within its parent (e.g., "idle").
        parent (Optional[StateNode]): The parent `StateNode` if this is a substate; `None` for the root.
        machine (MachineNode): A reference to the root `MachineNode` of this state tree.
        id (str): The fully qualified, unique ID of the state (e.g., "machine.parent.child").
        type (Literal["atomic", "compound", "parallel", "final"]): The type of the state.
        initial (Optional[str]): The key of the initial substate for compound states.
        on (Dict[str, List[TransitionDefinition]]): Mappings of event names to a list of
                                                   `TransitionDefinition` objects for that event.
        on_done (Optional[TransitionDefinition]): The transition to take when a compound or
                                                 parallel state reaches its "done" condition
                                                 (i.e., all child final states are reached).
        after (Dict[int, List[TransitionDefinition]]): Mappings of delay durations (in ms) to
                                                      a list of `TransitionDefinition` objects
                                                      for delayed transitions.
        entry (List[ActionDefinition]): A list of `ActionDefinition` objects to execute
                                       upon entering this state.
        exit (List[ActionDefinition]): A list of `ActionDefinition` objects to execute
                                      upon exiting this state.
        invoke (List[InvokeDefinition]): A list of `InvokeDefinition` objects for
                                        services or actors to be invoked when entering this state.
        states (Dict[str, StateNode]): A dictionary mapping child state keys to their
                                      corresponding `StateNode` objects.
    """

    def __init__(
        self,
        machine: "MachineNode",
        config: Dict[str, Any],
        key: str,
        parent: Optional["StateNode"] = None,
    ):
        """Initializes a StateNode from its configuration dictionary."""
        logger.debug(
            "Initializing StateNode: key='%s', parent_id='%s', config_keys=%s",
            key,
            parent.id if parent else "N/A",
            list(config.keys()),
        )

        self.key: str = key
        self.parent: Optional["StateNode"] = parent
        self.machine: "MachineNode" = machine
        # Construct the fully qualified ID
        self.id: str = f"{parent.id}.{key}" if parent else key

        # Determine state type based on presence of 'states' or 'type: "final"'
        if "states" in config:
            self.type: Literal["compound", "parallel"] = config.get(
                "type", "compound"
            )
            if self.type not in ["compound", "parallel"]:
                logger.warning(
                    "⚠️ Invalid 'type' specified for state '%s' with children: '%s'. Defaulting to 'compound'.",
                    self.id,
                    self.type,
                )
                self.type = (
                    "compound"  # Fallback for invalid types with sub-states
                )
        elif config.get("type") == "final":
            self.type: Literal["final"] = "final"
        else:
            self.type: Literal["atomic"] = "atomic"
        logger.debug(
            "   StateNode '%s' identified as type: '%s'", self.id, self.type
        )

        self.initial: Optional[str] = config.get("initial")
        if self.type in ["compound", "parallel"] and not self.initial:
            logger.debug(
                "   Compound/Parallel state '%s' has no initial state defined.",
                self.id,
            )

        # Parse 'on' transitions
        self.on: Dict[str, List[TransitionDefinition]] = {}
        for event, transitions in config.get("on", {}).items():
            # Use _normalize_transitions to handle shorthand syntax
            normalized_transitions = self._normalize_transitions(transitions)
            self.on[event] = [
                TransitionDefinition(event, t_config, self)
                for t_config in normalized_transitions
            ]
            logger.debug(
                "   Parsed %d transitions for event '%s' on state '%s'",
                len(self.on[event]),
                event,
                self.id,
            )

        # Parse 'onDone' transition (for compound/parallel states completing)
        self.on_done: Optional[TransitionDefinition] = None
        on_done_config = config.get("onDone")
        if on_done_config:
            # ⬇️ Handle string shorthand for onDone transition ⬇️
            if isinstance(on_done_config, str):
                on_done_config = {"target": on_done_config}

            # ⬇️ Normalize to a list to create TransitionDefinition ⬇️
            normalized_on_done_list = self._normalize_transitions(
                on_done_config
            )
            if (
                normalized_on_done_list
            ):  # Ensure there's at least one valid transition
                # For onDone, we typically expect a single transition or the first in a list
                self.on_done = TransitionDefinition(
                    f"done.state.{self.id}", normalized_on_done_list[0], self
                )
                logger.debug(
                    "   Parsed onDone transition for state '%s' with target '%s'",
                    self.id,
                    self.on_done.target_str,
                )
            else:
                logger.warning(
                    "⚠️ onDone configuration for state '%s' is invalid and will be ignored: %s",
                    self.id,
                    on_done_config,
                )

        # Parse 'after' delayed transitions
        self.after: Dict[int, List[TransitionDefinition]] = {
            int(delay): [
                TransitionDefinition(f"after.{delay}.{self.id}", t, self)
                for t in self._normalize_transitions(transitions)
            ]
            for delay, transitions in config.get("after", {}).items()
        }
        self.entry: List[ActionDefinition] = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("entry", []))
        ]
        self.exit: List[ActionDefinition] = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("exit", []))
        ]
        self.invoke: List[InvokeDefinition] = []
        invoke_config = config.get("invoke")
        if invoke_config:
            self.invoke = [
                InvokeDefinition(i, self)
                for i in self._ensure_list(invoke_config)
            ]
        self.states: Dict[str, "StateNode"] = {
            state_key: StateNode(machine, state_config, state_key, self)
            for state_key, state_config in config.get("states", {}).items()
        }

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_transitions(config: Any) -> List[Dict[str, Any]]:
        """Ensures transition configs are always a list of dicts.

        This helper makes the parser robust by handling all valid XState
        shorthand syntaxes for transitions (string, object, or list).

        Args:
            config: The raw transition configuration for a single event.

        Returns:
            A list of transition configuration dictionaries.

        Raises:
            InvalidConfigError: If the config is not a str, dict, or list.
        """
        # Case 1: "EVENT": "targetState"
        if isinstance(config, str):
            return [{"target": config}]
        # Case 2: "EVENT": { "target": "targetState", ... }
        if isinstance(config, dict):
            return [config]
        # Case 3: "EVENT": [{...}, {...}]
        if isinstance(config, list):
            normalized_list = []
            for item in config:
                if isinstance(item, str):
                    normalized_list.append({"target": item})
                elif isinstance(item, dict):
                    normalized_list.append(item)
                else:
                    # ✅ FIX: Raise error for invalid items within a list
                    raise InvalidConfigError(
                        f"Invalid transition item in list: {item}. Must be str or dict."
                    )
            return normalized_list
        # ✅ FIX: Raise an error for any other invalid type.
        raise InvalidConfigError(
            f"Invalid transition config: {config}. Must be str, dict, or list."
        )

    @staticmethod
    def _ensure_list(config_item: Any) -> List:
        """A simple helper to ensure a config item is always a list."""
        return config_item if isinstance(config_item, list) else [config_item]

    # -------------------------------------------------------------------------
    # Properties & Representations
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


class MachineNode(StateNode[TContext, TEvent]):
    """The root node of a state machine, with added developer utilities."""

    def __init__(
        self, config: Dict[str, Any], logic: MachineLogic[TContext, TEvent]
    ):
        """Initializes the root MachineNode.

        Args:
            config: The root JSON configuration of the entire machine.
            logic: The provided implementation for the machine's logic.

        Raises:
            InvalidConfigError: If the machine configuration lacks a root 'id'.
        """
        if not config.get("id"):
            raise InvalidConfigError(
                "Machine configuration must have a root 'id'."
            )
        self.logic: MachineLogic[TContext, TEvent] = logic
        self.initial_context: TContext = config.get("context", {})
        super().__init__(self, config, config["id"])

    def get_state_by_id(self, state_id: str) -> Optional[StateNode]:
        """Finds and returns a state node by its full ID (e.g., "machine.state.child").

        Args:
            state_id: The fully qualified ID of the state to find.

        Returns:
            The `StateNode` if found, otherwise `None`.
        """
        path = state_id.split(".")
        # 🧪 Validate that the path starts with this machine's ID.
        if path and path[0] != self.key:
            return None

        node = self
        for key in path[1:]:
            if key not in node.states:
                return None
            node = node.states[key]
        return node

    # -------------------------------------------------------------------------
    # 🧪 Testing Utilities
    # -------------------------------------------------------------------------

    def get_next_state(
        self, from_state_id: str, event: Event
    ) -> Optional[Set[str]]:
        """Calculates the target state(s) for an event without executing actions.

        This is a pure function useful for testing transition logic in isolation.
        Note: This utility does not evaluate guards.

        Args:
            from_state_id: The ID of the current state (e.g., "idle").
            event: The event to process.

        Returns:
            A set of target state IDs, or `None` if no transition is found.
        """
        from_node = self.get_state_by_id(from_state_id)
        if not from_node:
            return None

        # 🔍 Search for a matching transition by bubbling up from the source node.
        current = from_node
        while current:
            if event.type in current.on:
                for transition in current.on[event.type]:
                    if transition.target_str:
                        # ✅ Transition found, resolve its target.
                        target_node = resolve_target_state(
                            transition.target_str, current
                        )
                        # NOTE: A full implementation would calculate the complete
                        # final state configuration, but for testing, returning
                        # the direct target is often sufficient.
                        return {target_node.id}
            current = current.parent
        return None

    # -------------------------------------------------------------------------
    # 🎨 Visualization Utilities
    # -------------------------------------------------------------------------

    def to_plantuml(self) -> str:
        """Generates a PlantUML string representation of the state machine.

        Returns:
            A string that can be rendered by PlantUML into a state diagram.
        """
        content = ["@startuml", "hide empty description"]

        # 1. Recursively define all states and their hierarchy.
        def build_puml_states(node: StateNode, level: int):
            indent = "  " * level
            safe_id = node.id.replace(
                ".", "_"
            )  # PlantUML doesn't like dots in names.
            if node.states:
                content.append(f'{indent}state "{node.key}" as {safe_id} {{')
                if node.initial:
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

        # 2. Define all transitions between the states.
        def build_puml_transitions(node: StateNode):
            source_id = node.id.replace(".", "_")
            # Regular 'on' transitions
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = self.get_state_by_id(
                                resolve_target_state(t.target_str, node).id
                            )
                            if target_node:
                                target_id = target_node.id.replace(".", "_")
                                content.append(
                                    f"{source_id} --> {target_id} : {event}"
                                )
                        except StateNotFoundError:
                            pass

            # 'onDone' transition
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = self.get_state_by_id(
                        resolve_target_state(node.on_done.target_str, node).id
                    )
                    if target_node:
                        target_id = target_node.id.replace(".", "_")
                        content.append(f"{source_id} --> {target_id} : onDone")
                except StateNotFoundError:
                    pass

            for child in node.states.values():
                build_puml_transitions(child)

        # kick off the transitions build
        if self.initial and self.states.get(self.initial):
            content.append(
                f'[*] --> {self.states[self.initial].id.replace(".", "_")}'
            )
        build_puml_transitions(self)
        content.append("@enduml")
        return "\n".join(content)

    def to_mermaid(self) -> str:
        """Generates a Mermaid.js string representation of the state machine.

        Returns:
            A string that can be rendered by Mermaid.js into a state diagram.
        """
        content = ["stateDiagram-v2"]

        # 1. Define state hierarchy (Mermaid handles this slightly differently).
        def build_mmd_states(node: StateNode, level: int):
            indent = "    " * level
            if node.states:
                content.append(f"{indent}state {node.key} {{")
                if node.initial:
                    initial_target_id = node.states[node.initial].key
                    content.append(f"{indent}    [*] --> {initial_target_id}")
                for child in node.states.values():
                    build_mmd_states(child, level + 1)
                content.append(f"{indent}}}")

        # 2. Define all transitions at the top level.
        def build_mmd_transitions(node: StateNode):
            # Regular 'on' transitions
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = self.get_state_by_id(
                                resolve_target_state(t.target_str, node).id
                            )
                            if target_node:
                                content.append(
                                    f"{node.key} --> {target_node.key} : {event}"
                                )
                        except StateNotFoundError:
                            pass

            # 'onDone' transition
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = self.get_state_by_id(
                        resolve_target_state(node.on_done.target_str, node).id
                    )
                    if target_node:
                        content.append(
                            f"{node.key} --> {target_node.key} : onDone"
                        )
                except StateNotFoundError:
                    pass

            # Recurse for all children.
            for child in node.states.values():
                build_mmd_transitions(child)

        if self.initial and self.states.get(self.initial):
            content.append(f"[*] --> {self.states[self.initial].key}")
        build_mmd_states(self, 0)
        build_mmd_transitions(self)
        return "\n".join(content)
