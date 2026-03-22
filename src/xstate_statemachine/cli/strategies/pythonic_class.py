# src/xstate_statemachine/cli/strategies/pythonic_class.py
"""Strategy for pythonic class-based code generation."""

from .base import BaseStrategy, GenerationContext


class PythonicClassStrategy(BaseStrategy):
    """Generates pythonic class-based state machine code."""

    @property
    def name(self) -> str:
        return "pythonic-class"

    def generate_logic(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5
