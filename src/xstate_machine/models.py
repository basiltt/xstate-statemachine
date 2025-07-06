# src/xstate_machine/models.py
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from .machine_logic import MachineLogic
from .exceptions import InvalidConfigError


# -----------------------------------------------------------------------------
# 🏛️ Machine Definition Models
# -----------------------------------------------------------------------------
# These classes represent the static structure of the state machine, parsed
# from the input JSON. They form a traversable graph data structure.
# -----------------------------------------------------------------------------


class ActionDefinition:
    """Represents a single action to be executed."""

    def __init__(self, config: Union[str, Dict[str, Any]]):
        if isinstance(config, str):
            self.type = config
        else:
            self.type = config.get("type", "UnknownAction")

    def __repr__(self) -> str:
        return f"Action(type='{self.type}')"


class TransitionDefinition:
    """Represents a transition between states for a given event."""

    def __init__(self, event: str, config: Dict[str, Any], source: StateNode):
        self.event = event
        self.source = source
        self.target_str: Optional[str] = config.get("target")
        self.actions = [ActionDefinition(a) for a in config.get("actions", [])]
        self.guard: Optional[str] = config.get("guard")

    def __repr__(self) -> str:
        return f"Transition(event='{self.event}', target='{self.target_str}')"


class InvokeDefinition:
    """Represents an invoked service within a state."""

    def __init__(self, config: Dict[str, Any], source: StateNode):
        self.id = config.get("id", source.id)
        self.src = config.get("src")
        self.on_done = [
            TransitionDefinition(f"done.invoke.{self.id}", t, source)
            for t in config.get("onDone", [])
        ]
        self.on_error = [
            TransitionDefinition(f"error.platform.{self.id}", t, source)
            for t in config.get("onError", [])
        ]


class StateNode:
    """Represents a single state in the state machine graph."""

    def __init__(
        self,
        machine: MachineNode,
        config: Dict,
        key: str,
        parent: Optional[StateNode] = None,
    ):
        self.key = key
        self.parent = parent
        self.machine = machine
        self.id = f"{parent.id}.{key}" if parent else key

        # State Type
        if "states" in config:
            self.type: Literal["compound", "parallel"] = config.get(
                "type", "compound"
            )
        elif config.get("type") == "final":
            self.type: Literal["final"] = "final"
        else:
            self.type: Literal["atomic"] = "atomic"

        self.initial: Optional[str] = config.get("initial")

        # -----------------------------------------------------------------------------
        # ✨ FIX: Normalize and parse transitions robustly
        # -----------------------------------------------------------------------------
        self.on: Dict[str, List[TransitionDefinition]] = {
            event: [
                TransitionDefinition(event, t_config, self)
                for t_config in self._normalize_transitions(transitions)
            ]
            for event, transitions in config.get("on", {}).items()
        }
        # -----------------------------------------------------------------------------

        # Delayed Transitions
        self.after: Dict[int, List[TransitionDefinition]] = {
            int(delay): [
                TransitionDefinition(f"after.{delay}.{self.id}", t, self)
                for t in self._normalize_transitions(transitions)
            ]
            for delay, transitions in config.get("after", {}).items()
        }

        # Actions & Services
        self.entry = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("entry", []))
        ]
        self.exit = [
            ActionDefinition(a)
            for a in self._ensure_list(config.get("exit", []))
        ]
        self.invoke = (
            InvokeDefinition(config["invoke"], self)
            if "invoke" in config
            else None
        )

        # Child States
        self.states: Dict[str, StateNode] = {
            state_key: StateNode(machine, state_config, state_key, self)
            for state_key, state_config in config.get("states", {}).items()
        }

    @staticmethod
    def _normalize_transitions(config: Any) -> List[Dict[str, Any]]:
        """
        Ensures transition configs are always a list of dicts to handle
        XState's various shorthand syntaxes.
        """
        # Case 1: "EVENT": "targetState"
        if isinstance(config, str):
            return [{"target": config}]
        # Case 2: "EVENT": { "target": "targetState", ... }
        if isinstance(config, dict):
            return [config]
        # Case 3: "EVENT": [{...}, {...}]
        if isinstance(config, list):
            # It's possible the list contains string shorthands, so we normalize recursively
            normalized_list = []
            for item in config:
                if isinstance(item, str):
                    normalized_list.append({"target": item})
                elif isinstance(item, dict):
                    normalized_list.append(item)
            return normalized_list
        # Should not happen with a valid config
        return []

    @staticmethod
    def _ensure_list(config_item: Any) -> List:
        """Helper to ensure a config item is always a list for consistent parsing."""
        return config_item if isinstance(config_item, list) else [config_item]

    @property
    def is_atomic(self) -> bool:
        return self.type == "atomic"

    @property
    def is_final(self) -> bool:
        return self.type == "final"

    def __repr__(self) -> str:
        return f"StateNode(id='{self.id}', type='{self.type}')"


class MachineNode(StateNode):
    """The root node of a state machine."""

    def __init__(self, config: Dict[str, Any], logic: MachineLogic):
        if not config.get("id"):
            raise InvalidConfigError(
                "Machine configuration must have an 'id'."
            )
        self.logic = logic
        self.initial_context = config.get("context", {})
        super().__init__(self, config, config["id"])
