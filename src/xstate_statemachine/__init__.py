# /src/xstate_statemachine/__init__.py
# -----------------------------------------------------------------------------
# 📦 Public API & Package Entry Point
# -----------------------------------------------------------------------------
# This __init__.py file serves as the public-facing API for the
# `xstate_statemachine` library. It carefully exposes the core components
# needed to build, interpret, and extend state machines, acting as a
# "facade" to the underlying modules.
#
# By explicitly defining `__all__`, we create a clean and stable contract
# for library users, ensuring that only intended classes and functions are
# accessible at the top level. This improves usability, documentation, and
# long-term maintainability.
# -----------------------------------------------------------------------------
"""
A robust, asynchronous, and feature-complete Python library for parsing
and executing state machines defined in XState-compatible JSON.

This library brings the power and clarity of formal state machines and
statecharts, as popularized by XState, to the Python ecosystem. It allows
you to define complex application logic as a clear, traversable graph and
execute it in a fully asynchronous, predictable, and debuggable way.

Attributes:
    __version__ (str): The current version of the library.

Example:
    A simple, runnable example of creating and using a state machine.

    >>> import asyncio
    >>> import json
    >>> from xstate_statemachine import create_machine, Interpreter, MachineLogic
    ...
    >>> # 1. Define the machine's structure in JSON
    >>> light_switch_config = {
    ...     "id": "lightSwitch",
    ...     "initial": "off",
    ...     "context": {"flips": 0},
    ...     "states": {
    ...         "off": {"on": {"TOGGLE": {"target": "on", "actions": "increment_flips"}}},
    ...         "on": {"on": {"TOGGLE": {"target": "off", "actions": "increment_flips"}}}
    ...     }
    ... }
    ...
    >>> # 2. Define the implementation logic
    >>> def increment_flips_action(i, ctx, e, a):
    ...     ctx["flips"] += 1
    ...     print(f"💡 Flipped! Total: {ctx['flips']}")
    ...
    >>> light_switch_logic = MachineLogic(actions={"increment_flips": increment_flips_action})
    ...
    >>> # 3. Create and run the machine
    >>> async def main():
    ...     machine = create_machine(light_switch_config, logic=light_switch_logic)
    ...
    ...     # FIX: Renamed 'interpreter' to 'service' to resolve the IDE warning
    ...     # about "shadowing name from outer scope". This is a common linter
    ...     # best practice to avoid name collisions.
    ...     service = await Interpreter(machine).start()
    ...
    ...     # FIX: Calling methods on the 'service' object resolves the
    ...     # "Cannot find reference" warnings in the IDE.
    ...     await service.send("TOGGLE")
    ...     await service.send("TOGGLE")
    ...     await service.stop()
    ...
    >>> asyncio.run(main())
    💡 Flipped! Total: 1
    💡 Flipped! Total: 2
"""

# -----------------------------------------------------------------------------
# ⚙️ Core Components
# -----------------------------------------------------------------------------
from .factory import create_machine
from .interpreter import Interpreter
from .sync_interpreter import SyncInterpreter
from .machine_logic import MachineLogic
from .logic_loader import LogicLoader

# -----------------------------------------------------------------------------
# ✉️ Event & Model Definitions
# -----------------------------------------------------------------------------
from .events import Event
from .models import ActionDefinition, MachineNode

# -----------------------------------------------------------------------------
# 🔌 Extensibility & Plugins
# -----------------------------------------------------------------------------
from .plugins import LoggingInspector, PluginBase

# -----------------------------------------------------------------------------
# 🚨 Custom Exception Hierarchy
# -----------------------------------------------------------------------------
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
    NotSupportedError,
    StateNotFoundError,
    XStateMachineError,
)

# -----------------------------------------------------------------------------
# 📦 Version Information
# -----------------------------------------------------------------------------

# 📦 The official version number for the library.
__version__ = "0.4.2"

# -----------------------------------------------------------------------------
# 🌐 Public API Definition
# -----------------------------------------------------------------------------
# This list defines the public API of the library. Only names listed here
# will be imported when a user does `from xstate_statemachine import *`.
# It's organized to match the import sections above for clarity and
# maintainability.
# -----------------------------------------------------------------------------
__all__ = [
    # ⚙️ Core Components
    "create_machine",
    "Interpreter",
    "SyncInterpreter",
    "MachineLogic",
    "LogicLoader",
    # ✉️ Event & Model Definitions
    "Event",
    "ActionDefinition",
    # 🔌 Extensibility & Plugins
    "PluginBase",
    "LoggingInspector",
    # 🚨 Custom Exception Hierarchy
    "XStateMachineError",
    "InvalidConfigError",
    "StateNotFoundError",
    "ImplementationMissingError",
    "ActorSpawningError",
    "NotSupportedError",
    "MachineNode",
    "__version__",
]
