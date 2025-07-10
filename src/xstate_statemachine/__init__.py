# src/xstate_statemachine/__init__.py

__version__ = "0.3.0"  # Version bump for sync feature

from .factory import create_machine
from .interpreter import Interpreter
from .sync_interpreter import SyncInterpreter
from .machine_logic import MachineLogic
from .events import Event
from .models import ActionDefinition
from .plugins import PluginBase, LoggingInspector
from .exceptions import (
    XStateMachineError,
    InvalidConfigError,
    StateNotFoundError,
    ImplementationMissingError,
    ActorSpawningError,
    NotSupportedError,
)
from .logic_loader import LogicLoader


# This is the public API of the library.
__all__ = [
    "create_machine",
    "Interpreter",
    "SyncInterpreter",
    "MachineLogic",
    "Event",
    "PluginBase",
    "LoggingInspector",
    "XStateMachineError",
    "InvalidConfigError",
    "StateNotFoundError",
    "ImplementationMissingError",
    "ActorSpawningError",
    "NotSupportedError",
    "LogicLoader",
    "ActionDefinition",
]
