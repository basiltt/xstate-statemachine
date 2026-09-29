"""A minimal third-party plugin package (test fixture for #296)."""

from typing import Any, List

from xstate_statemachine import PluginBase


class AuditPlugin(PluginBase[Any]):
    """Records every transition. Overrides two hooks."""

    def __init__(self) -> None:
        self.started: List[str] = []
        self.transitions: List[Any] = []

    def on_interpreter_start(self, interpreter: Any) -> None:
        self.started.append(interpreter.id)

    def on_transition(self, interpreter, from_states, to_states, transition):
        self.transitions.append(sorted(s.id for s in to_states))


class MemoryStore:
    """A store adapter: discovered and described, never instantiated."""
