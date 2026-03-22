# src/xstate_statemachine/cli/strategies/class_json.py
"""Strategy for class-based JSON code generation."""

from .base import BaseStrategy, GenerationContext


class ClassJsonStrategy(BaseStrategy):
    """Generates class-based logic with JSON config loading."""

    @property
    def name(self) -> str:
        return "class-json"

    def generate_logic(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5
