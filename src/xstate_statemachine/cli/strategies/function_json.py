# src/xstate_statemachine/cli/strategies/function_json.py
"""Strategy for function-based JSON code generation."""

from .base import BaseStrategy, GenerationContext


class FunctionJsonStrategy(BaseStrategy):
    """Generates function-based logic with JSON config loading."""

    @property
    def name(self) -> str:
        return "function-json"

    def generate_logic(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5
