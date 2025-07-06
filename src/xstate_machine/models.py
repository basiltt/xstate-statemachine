# src/xstate_machine/models.py
from __future__ import annotations

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


# -----------------------------------------------------------------------------
# 🧬 Type Variables & Generics
# -----------------------------------------------------------------------------
# Using TypeVars allows for creating generic machine definitions. This provides
# a foundation for full static type checking of a machine's context and events,
# leading to more robust and self-documenting code.

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])


# -----------------------------------------------------------------------------
# 🎬 Action & Transition Models
# -----------------------------------------------------------------------------


class ActionDefinition:
    """Represents a single action to be executed.

    This class standardizes the representation of an action defined in the
    machine's configuration.
    """

    def __init__(self, config: Union[str, Dict[str, Any]]):
        """Initializes the ActionDefinition.

        Args:
            config: The action configuration, which can be a string (the
                    action's name) or a dictionary with a "type" key.
        """
        if isinstance(config, str):
            # ✅ Handle shorthand string definition (e.g., "myAction").
            self.type: str = config
        else:
            # ✅ Handle object definition (e.g., {"type": "myAction"}).
            self.type: str = config.get("type", "UnknownAction")

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Action(type='{self.type}')"


class TransitionDefinition:
    """Represents a potential transition between states for a given event.

    It holds all information about a transition, including its target, the
    actions to execute, and any conditional guard.
    """

    def __init__(self, event: str, config: Dict[str, Any], source: StateNode):
        """Initializes the TransitionDefinition.

        Args:
            event: The name of the event that triggers this transition.
            config: The dictionary defining the transition's properties.
            source: The `StateNode` where this transition is defined.
        """
        self.event: str = event
        self.source: StateNode = source
        self.target_str: Optional[str] = config.get("target")
        self.actions: List[ActionDefinition] = [
            ActionDefinition(a) for a in config.get("actions", [])
        ]
        self.guard: Optional[str] = config.get("guard")

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Transition(event='{self.event}', target='{self.target_str}')"


class InvokeDefinition:
    """Represents an invoked service or actor within a state.

    This class models a long-running process that is started when its host
    state is entered and can communicate back to the state machine.
    """

    def __init__(self, config: Dict[str, Any], source: StateNode):
        """Initializes the InvokeDefinition.

        This constructor uses the `_normalize_transitions` helper to robustly
        parse `onDone` and `onError` handlers, accommodating all valid XState
        shorthand syntaxes.

        Args:
            config: The dictionary from the `invoke` key in the machine config.
            source: The `StateNode` that hosts this invocation.
        """
        self.id: str = config.get("id", source.id)
        self.src: Optional[str] = config.get("src")

        # ✨ FIX: Robustly parse onDone/onError using the normalizer to
        # handle all valid shorthands (string, object, or list of objects).
        on_done_config = config.get("onDone", [])
        self.on_done: List[TransitionDefinition] = [
            TransitionDefinition(f"done.invoke.{self.id}", t, source)
            for t in StateNode._normalize_transitions(on_done_config)
        ]

        on_error_config = config.get("onError", [])
        self.on_error: List[TransitionDefinition] = [
            TransitionDefinition(f"error.platform.{self.id}", t, source)
            for t in StateNode._normalize_transitions(on_error_config)
        ]


# -----------------------------------------------------------------------------
# 🌳 Core State Tree Models
# -----------------------------------------------------------------------------


class StateNode(Generic[TContext, TEvent]):
    """Represents a single state in the state machine graph.

    This class is the core of the machine's structure, applying the Composite
    design pattern. A StateNode can be atomic, compound, or parallel, and it
    holds its own transitions, actions, and potential child states.

    Attributes:
        id (str): The fully qualified, unique ID of the state (e.g., "machine.group.state").
        key (str): The local key of the state within its parent.
        machine (MachineNode): A reference to the root machine node.
        parent (Optional[StateNode]): The parent state, if this is a substate.
        type (str): The type of the state: 'atomic', 'compound', 'parallel', or 'final'.
        initial (Optional[str]): The key of the initial substate for compound states.
        on (Dict): Mappings of event names to their possible transitions.
        after (Dict): Mappings of delays to their delayed transitions.
        entry (List): A list of actions to execute upon entering the state.
        exit (List): A list of actions to execute upon exiting the state.
        invoke (Optional[InvokeDefinition]): An invoked service definition.
        states (Dict): A dictionary of child `StateNode`s.
    """

    def __init__(
        self,
        machine: MachineNode,
        config: Dict,
        key: str,
        parent: Optional[StateNode] = None,
    ):
        """Initializes a StateNode from its configuration.

        Args:
            machine: The root machine instance.
            config: The JSON configuration object for this state.
            key: The key of this state within its parent's `states` object.
            parent: The parent of this state, or `None` if it's the root.
        """
        # 📝 Core properties and hierarchical links.
        self.key: str = key
        self.parent: Optional[StateNode] = parent
        self.machine: MachineNode = machine
        self.id: str = f"{parent.id}.{key}" if parent else key

        # 🧐 Determine the type of state based on its configuration.
        if "states" in config:
            self.type: Literal["compound", "parallel"] = config.get(
                "type", "compound"
            )
        elif config.get("type") == "final":
            self.type: Literal["final"] = "final"
        else:
            self.type: Literal["atomic"] = "atomic"

        self.initial: Optional[str] = config.get("initial")

        # 🔀 Parse transitions robustly using the normalizer helper.
        self.on: Dict[str, List[TransitionDefinition]] = {
            event: [
                TransitionDefinition(event, t_config, self)
                for t_config in self._normalize_transitions(transitions)
            ]
            for event, transitions in config.get("on", {}).items()
        }

        # ⏰ Parse delayed transitions.
        self.after: Dict[int, List[TransitionDefinition]] = {
            int(delay): [
                TransitionDefinition(f"after.{delay}.{self.id}", t, self)
                for t in self._normalize_transitions(transitions)
            ]
            for delay, transitions in config.get("after", {}).items()
        }

        # 🎬 Parse entry/exit actions and invoked services.
        self.entry: List[ActionDefinition] = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("entry", []))
        ]
        self.exit: List[ActionDefinition] = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("exit", []))
        ]
        self.invoke: Optional[InvokeDefinition] = (
            InvokeDefinition(config["invoke"], self)
            if "invoke" in config
            else None
        )

        # 👶 Parse nested states recursively to build the state tree.
        self.states: Dict[str, StateNode] = {
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
        """
        # Case 1: "EVENT": "targetState"
        if isinstance(config, str):
            return [{"target": config}]
        # Case 2: "EVENT": { "target": "targetState", ... }
        if isinstance(config, dict):
            return [config]
        # Case 3: "EVENT": [{...}, {...}]
        if isinstance(config, list):
            # It's possible the list contains string shorthands, so normalize recursively.
            normalized_list = []
            for item in config:
                if isinstance(item, str):
                    normalized_list.append({"target": item})
                elif isinstance(item, dict):
                    normalized_list.append(item)
            return normalized_list
        # Should not happen with a valid config.
        return []

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
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            # Resolve the target to get its safe ID.
                            target_node = self.get_state_by_id(
                                resolve_target_state(t.target_str, node).id
                            )
                            if target_node:
                                target_id = target_node.id.replace(".", "_")
                                content.append(
                                    f"{source_id} --> {target_id} : {event}"
                                )
                        except StateNotFoundError:
                            # Gracefully skip transitions with unresolvable targets.
                            pass

            for child in node.states.values():
                build_puml_transitions(child)

        # kick off the transitions build
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
            # Recurse for all children.
            for child in node.states.values():
                build_mmd_transitions(child)

        content.append(f"[*] --> {self.states[self.initial].key}")
        build_mmd_states(self, 0)
        build_mmd_transitions(self)
        return "\n".join(content)
