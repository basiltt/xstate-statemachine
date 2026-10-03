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
from .base_interpreter import PendingInvocation
from .base_interpreter import BaseInterpreter
from .interpreter import (
    DEFAULT_CHILDREN_TIMEOUT,
    DEFAULT_SERVICE_POOL_SIZE,
    Interpreter,
)
from .sync_interpreter import SyncInterpreter
from .machine_logic import MachineLogic
from .logic_loader import LogicLoader

# -----------------------------------------------------------------------------
# ✉️ Event & Model Definitions
# -----------------------------------------------------------------------------
from .events import (
    ENGINE_EVENT_SHAPES,
    SYSTEM_EVENT_PREFIXES,
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    Receipt,
    StreamEvent,
    is_system_event,
    re_mint,
    system_event,
)
from .models import ActionDefinition, MachineNode, OverflowPolicy

# -----------------------------------------------------------------------------
# 🔌 Extensibility & Plugins
# -----------------------------------------------------------------------------
from .context_keys import (  # 🔑 #265
    PRIVATE_CONTEXT_PREFIX,
    is_private_context_key,
    public_context,
)
from .plugins import (
    LoggingInspector,
    PluginBase,
    global_plugins,
    register_global,
    unregister_global,
)

# -----------------------------------------------------------------------------
# 🚨 Custom Exception Hierarchy
# -----------------------------------------------------------------------------
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InterpreterStoppedError,
    InvalidConfigError,
    InvalidEventError,
    InvalidEventPayloadError,
    MissingExtraError,
    NotSupportedError,
    QueueOverflowError,
    ReentrantWaitError,
    RestoredChainError,
    RestoredError,
    RootTargetError,
    RunawayChainError,
    SnapshotCorruptError,
    SnapshotDriftError,
    SnapshotMidStepError,
    SnapshotSerializationError,
    SnapshotVersionError,
    StateNotFoundError,
    TransitionFailedError,
    UnhandledEventError,
    UnknownEventError,
    WrongThreadError,
    XStateMachineError,
    StoreError,
    ConflictError,
    LockTimeoutError,
    SnapshotTooLargeError,
    InvalidKeyError,
)
from .persistence.migration import (
    MachineVersionMismatchError,
    NoMigrationPathError,
)

# -------------------------------------------------------------------------
# 🐍 Pythonic API
# -------------------------------------------------------------------------
from .clock import Clock, RealClock, SimulatedClock
from .pythonic import (
    State,
    StateMachine,
    MachineBuilder,
    build_machine,
    transition,
    action,
    guard,
    service,
)

# -----------------------------------------------------------------------------
# 🎬 Built-in Action Creators
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `raise_` keeps its trailing underscore because
# `raise` is a Python keyword, and `assign_`/`log_` are aliased alongside the
# plain names so a user who has shadowed them locally still has an escape
# hatch.
from .actions import (
    ActionEnqueuer,
    assign,
    cancel,
    choose,
    emit,
    enqueue_actions,
    escalate,
    forward_to,
    log,
    pure,
    raise_,
    send_parent,
    send_to,
    spawn_child,
    stop_child,
)

# -----------------------------------------------------------------------------
# 🧰 Helpers & Pure Transition API
# -----------------------------------------------------------------------------
# 📝 `transition` is already exported by the Pythonic DSL (it builds a
# transition definition). The pure reducer is therefore exported under its
# XState-adjacent aliases plus an explicit `pure_transition` name, so neither
# meaning shadows the other.
from .helpers import (
    PureSnapshot,
    get_initial_snapshot,
    get_next_snapshot,
    initial_transition,
    to_promise,
    wait_for,
    wait_for_sync,
)
from .helpers import transition as pure_transition

# -------------------------------------------------------------------------
# 🧪 Testing utilities (#304) -- drive any chart without its real logic
# -------------------------------------------------------------------------
from .testing_utils import logic_names, stub_logic

# -------------------------------------------------------------------------
# 🗺️ Graph algorithms (#269) -- paths and reachability from the real engine
# -------------------------------------------------------------------------
from .graph import (
    Path,
    Step,
    reachable_states,
    shortest_paths,
    simple_paths,
    transition_coverage_targets,
)

# -------------------------------------------------------------------------
# 🎭 Actor logic helpers (#267) -- fromCallback / fromObservable parity
# -------------------------------------------------------------------------
from .actor_logic import (
    DEFAULT_CLEANUP_TIMEOUT,
    RunningLogic,
    drain_pending_cleanups,
    from_async_iterator,
    from_callable,
    from_callback,
    from_coroutine,
    from_interpreter,
    from_iterator,
)

# -------------------------------------------------------------------------
# 🧾 Receipt codec (#305) -- one JSON shape / HTTP status for every adapter
# -------------------------------------------------------------------------
from .receipts import receipt_from_json, receipt_to_json, receipt_to_status

# -----------------------------------------------------------------------------
# 📦 Version Information
# -----------------------------------------------------------------------------

# 📦 The official version number for the library.
__version__ = "0.11.0"

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
    "BaseInterpreter",
    "Interpreter",
    "DEFAULT_CHILDREN_TIMEOUT",
    "DEFAULT_SERVICE_POOL_SIZE",
    "SyncInterpreter",
    "MachineLogic",
    "LogicLoader",
    # ✉️ Event & Model Definitions
    "Event",
    "SYSTEM_EVENT_PREFIXES",
    "ENGINE_EVENT_SHAPES",
    "AfterEvent",
    "DoneEvent",
    "is_system_event",
    "re_mint",
    "system_event",
    "ErrorEvent",
    "StreamEvent",
    "ActionDefinition",
    # 🔌 Extensibility & Plugins
    "PluginBase",
    "PRIVATE_CONTEXT_PREFIX",
    "is_private_context_key",
    "public_context",
    "LoggingInspector",
    "register_global",
    "unregister_global",
    "global_plugins",
    # 🚨 Custom Exception Hierarchy
    "XStateMachineError",
    "InvalidConfigError",
    "StateNotFoundError",
    "ImplementationMissingError",
    "ActorSpawningError",
    "NotSupportedError",
    "InvalidEventError",
    "RootTargetError",
    "ReentrantWaitError",
    "RunawayChainError",
    "SnapshotCorruptError",
    "SnapshotMidStepError",
    "SnapshotSerializationError",
    "UnhandledEventError",
    "TransitionFailedError",
    "WrongThreadError",
    "StoreError",
    "ConflictError",
    "LockTimeoutError",
    "SnapshotTooLargeError",
    "InvalidKeyError",
    "MachineVersionMismatchError",
    "NoMigrationPathError",
    "SnapshotDriftError",
    "SnapshotVersionError",
    "RestoredChainError",
    "RestoredError",
    "QueueOverflowError",
    "InterpreterStoppedError",
    "UnknownEventError",
    "InvalidEventPayloadError",
    "MissingExtraError",
    "Receipt",
    "OverflowPolicy",
    "MachineNode",
    "PendingInvocation",
    # ⏱️ Clock
    "Clock",
    "RealClock",
    "SimulatedClock",
    # 🐍 Pythonic API
    "State",
    "StateMachine",
    "MachineBuilder",
    "build_machine",
    "transition",
    "action",
    "guard",
    "service",
    # 🎬 Built-in Action Creators
    "ActionEnqueuer",
    "assign",
    "cancel",
    "choose",
    "emit",
    "enqueue_actions",
    "escalate",
    "forward_to",
    "log",
    "pure",
    "raise_",
    "send_parent",
    "send_to",
    "spawn_child",
    "stop_child",
    # 🧰 Helpers & Pure Transition API
    "PureSnapshot",
    "get_initial_snapshot",
    "get_next_snapshot",
    "initial_transition",
    "pure_transition",
    "to_promise",
    "wait_for",
    "wait_for_sync",
    # 🧪 Testing utilities (#304)
    "stub_logic",
    "logic_names",
    # graph (#269)
    "Path",
    "Step",
    "reachable_states",
    "shortest_paths",
    "simple_paths",
    "transition_coverage_targets",
    # 🎭 Actor logic (#267)
    "from_callback",
    "from_async_iterator",
    "from_iterator",
    "RunningLogic",
    "drain_pending_cleanups",
    "DEFAULT_CLEANUP_TIMEOUT",
    "from_coroutine",
    "from_callable",
    "from_interpreter",
    # 🧾 Receipt codec (#305)
    "receipt_to_status",
    "receipt_to_json",
    "receipt_from_json",
    "__version__",
]
