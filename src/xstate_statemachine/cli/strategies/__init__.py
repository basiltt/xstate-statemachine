# src/xstate_statemachine/cli/strategies/__init__.py
"""Strategy-based code generation for the CLI."""

from typing import Dict, Type

from ...exceptions import InvalidConfigError
from .base import BaseStrategy, GenerationContext
from .class_json import ClassJsonStrategy
from .function_json import FunctionJsonStrategy
from .pythonic_builder import PythonicBuilderStrategy
from .pythonic_class import PythonicClassStrategy
from .pythonic_functional import PythonicFunctionalStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "class-json": ClassJsonStrategy,
    "function-json": FunctionJsonStrategy,
    "pythonic-class": PythonicClassStrategy,
    "pythonic-builder": PythonicBuilderStrategy,
    "pythonic-functional": PythonicFunctionalStrategy,
}


def get_strategy(template: str) -> BaseStrategy:
    """Look up and instantiate the strategy for a template.

    Args:
        template: Template name (e.g. 'pythonic-class').

    Returns:
        An instantiated strategy.

    Raises:
        InvalidConfigError: If template is unknown.
    """
    cls = STRATEGY_REGISTRY.get(template)
    if cls is None:
        valid = ", ".join(sorted(STRATEGY_REGISTRY))
        raise InvalidConfigError(
            f"Unknown template: {template}. " f"Valid templates: {valid}"
        )
    return cls()


__all__ = [
    "BaseStrategy",
    "GenerationContext",
    "STRATEGY_REGISTRY",
    "get_strategy",
]
