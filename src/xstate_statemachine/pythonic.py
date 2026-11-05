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
from ._pythonic_class import StateMachine
from ._pythonic_class import _validate_logic as _validate_logic
from ._pythonic_core import (
    BoundState,
    State,
    Transition,
    TransitionGroup,
    action,
    build_machine,
    guard,
    service,
    transition,
)

# 📝 `import X as X` is the explicit re-export form (mypy strict
#    `no_implicit_reexport`); these stay importable without being in
#    `__all__`.
from ._pythonic_core import _attr_to_event as _attr_to_event
from ._pythonic_core import _compile_config as _compile_config
from ._pythonic_core import (
    _compile_logic_from_functions as _compile_logic_from_functions,
)
from ._pythonic_core import (
    _compile_logic_from_instance as _compile_logic_from_instance,
)
from ._pythonic_core import _compile_state as _compile_state
from ._pythonic_core import _snake_to_camel as _snake_to_camel

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
]

# 📝 The underscore helpers imported above (`_compile_config`,
#    `_snake_to_camel`, ...) stay importable from this module for the CLI
#    and existing callers, but are not public API and are deliberately
#    kept out of `__all__` so `from ... import *` does not leak them.
