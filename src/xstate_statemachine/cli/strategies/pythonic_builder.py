# src/xstate_statemachine/cli/strategies/pythonic_builder.py
"""Strategy for pythonic builder-based code generation."""

from .base import BaseStrategy, GenerationContext


class PythonicBuilderStrategy(BaseStrategy):
    """Generates pythonic builder-based state machine code."""

    @property
    def name(self) -> str:
        return "pythonic-builder"

    def generate_logic(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5
