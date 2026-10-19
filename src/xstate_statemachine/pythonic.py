# src/xstate_statemachine/pythonic.py
"""
🐍 Pythonic API for xstate-statemachine.

This module provides three API styles for defining state machines
in pure Python, without writing JSON config dicts:

1. **Class-based** — ``StateMachine`` base class with metaclass
2. **Builder** — ``MachineBuilder`` fluent API
3. **Functional** — ``build_machine()`` with module-level helpers

All three styles compile to the same JSON config dict +
``MachineLogic`` pair and delegate to the existing
``create_machine()`` factory.

The implementation lives in ``_pythonic_core`` (State, Transition,
decorators, compilers), ``_pythonic_builder`` (MachineBuilder) and
``_pythonic_class`` (StateMachine); this module is the public surface.
"""

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from ._pythonic_builder import MachineBuilder
from ._pythonic_class import StateMachine, _validate_logic
from ._pythonic_core import (
    BoundState,
    State,
    Transition,
    TransitionGroup,
    _attr_to_event,
    _compile_config,
    _compile_logic_from_functions,
    _compile_logic_from_instance,
    _compile_state,
    _snake_to_camel,
    action,
    build_machine,
    guard,
    service,
    transition,
)

__all__ = [
    "BoundState",
    "MachineBuilder",
    "State",
    "StateMachine",
    "Transition",
    "TransitionGroup",
    "action",
    "build_machine",
    "guard",
    "service",
    "transition",
    "_attr_to_event",
    "_compile_config",
    "_compile_logic_from_functions",
    "_compile_logic_from_instance",
    "_compile_state",
    "_snake_to_camel",
    "_validate_logic",
]
