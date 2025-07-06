# src/xstate_machine/__init__.py

__version__ = "0.1.0"

from .factory import create_machine
from .interpreter import Interpreter
from .machine_logic import MachineLogic
from .events import Event
from .exceptions import (
    XStateMachineError,
    InvalidConfigError,
    StateNotFoundError,
    ImplementationMissingError,
)

# This is the public API of the library.
# By exposing these components here, users can import them directly, like:
# from xstate_machine import create_machine, Interpreter
__all__ = [
    "create_machine",
    "Interpreter",
    "MachineLogic",
    "Event",
    "XStateMachineError",
    "InvalidConfigError",
    "StateNotFoundError",
    "ImplementationMissingError",
]
