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
    ...     service = await Interpreter(machine).start()
    ...
    ...     # 📝 `send()` only QUEUES the event; `wait=True` returns once it
    ...     # has been processed. (A bare `send()` followed by `stop()` would
    ...     # discard the queued events: `stop()` does not drain by default.)
    ...     await service.send("TOGGLE", wait=True)
    ...     await service.send("TOGGLE", wait=True)
    ...     await service.stop()
    ...
    >>> asyncio.run(main())
    💡 Flipped! Total: 1
    💡 Flipped! Total: 2

Import cost:
    ``import xstate_statemachine`` only loads the engine core (machines,
    interpreters, events, exceptions, plugins, the Pythonic DSL and the
    built-in action creators). The graph algorithms (``reachable_states``,
    ``shortest_paths``, ...), the pure transition API (``wait_for``,
    ``get_next_snapshot``, ...), the testing utilities (``stub_logic``,
    ``logic_names``) and the receipt codec are resolved on first access
    through a module-level ``__getattr__`` (PEP 562). The optional
    subpackages (``cli``, ``contrib``, ``eda``, ``patterns``, ``inspect``)
    and the file / SQLite stores are never imported by the package itself.
    ``__all__`` is unchanged, ``from xstate_statemachine import <name>``
    works for every name in it, and type checkers see every name through
    the ``TYPE_CHECKING`` block below.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

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
from .models import (
    ActionDefinition,
    MachineNode,
    OverflowPolicy,
    event_payload,
)

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
    UnresolvedTargetError,
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
    TransitionNotAllowedError,
    UnhandledEventError,
    UnknownEventError,
    WrongThreadError,
    XStateMachineError,
    StoreError,
    StoreUnavailableError,
    ConflictError,
    LockTimeoutError,
    SnapshotTooLargeError,
    InvalidKeyError,
    ExplorationLimitError,
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

# -----------------------------------------------------------------------------
# 💤 Lazily-resolved public names (PEP 562)
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `import xstate_statemachine` is paid by every
# user, including those who never touch graph analysis, the pure transition
# API, stub logic or the receipt codec. Those names stay in `__all__` and stay
# importable (`from xstate_statemachine import shortest_paths`), but their
# modules are only imported on first access, via the module-level
# `__getattr__` at the bottom of this file. The resolved value is cached in
# the module namespace, so every later access is a plain attribute lookup.
#
# 📝 Only side-effect-free modules belong here: nothing in this table may
# register plugins, patch anything or read global state at import time (the
# global plugin registry is read in `BaseInterpreter.__init__`, not here).
# 📝 Each entry maps public name -> (submodule, attribute in that submodule);
# the `TYPE_CHECKING` block mirrors it so mypy/pyright see the real types.
_LAZY_ATTRS: Dict[str, Tuple[str, str]] = {
    # 🧰 Helpers & pure transition API
    "PureSnapshot": (".helpers", "PureSnapshot"),
    "get_initial_snapshot": (".helpers", "get_initial_snapshot"),
    "get_next_snapshot": (".helpers", "get_next_snapshot"),
    "initial_transition": (".helpers", "initial_transition"),
    # 📝 `transition` is the Pythonic DSL's name; the pure reducer is
    # exported as `pure_transition` so neither meaning shadows the other.
    "pure_transition": (".helpers", "transition"),
    "to_promise": (".helpers", "to_promise"),
    "wait_for": (".helpers", "wait_for"),
    "wait_for_sync": (".helpers", "wait_for_sync"),
    # 🧪 Testing utilities (#304)
    "logic_names": (".testing_utils", "logic_names"),
    "stub_logic": (".testing_utils", "stub_logic"),
    # 🗺️ Graph algorithms (#269)
    "Path": (".graph", "Path"),
    "Step": (".graph", "Step"),
    "reachable_states": (".graph", "reachable_states"),
    "shortest_paths": (".graph", "shortest_paths"),
    "simple_paths": (".graph", "simple_paths"),
    "transition_coverage_targets": (".graph", "transition_coverage_targets"),
    # 🧾 Receipt codec (#305)
    "receipt_from_json": (".receipts", "receipt_from_json"),
    "receipt_to_json": (".receipts", "receipt_to_json"),
    "receipt_to_status": (".receipts", "receipt_to_status"),
}

if TYPE_CHECKING:  # pragma: no cover
    # 💡 Type checkers cannot follow `__getattr__`; these imports give them
    # the real definitions. They never execute at runtime.
    from .graph import (
        Path,
        Step,
        reachable_states,
        shortest_paths,
        simple_paths,
        transition_coverage_targets,
    )
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
    from .receipts import (
        receipt_from_json,
        receipt_to_json,
        receipt_to_status,
    )
    from .testing_utils import logic_names, stub_logic

# -----------------------------------------------------------------------------
# 📦 Version Information
# -----------------------------------------------------------------------------

# 📦 The official version number for the library.
__version__ = "0.12.1"

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
    "UnresolvedTargetError",
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
    "TransitionNotAllowedError",
    "WrongThreadError",
    "StoreError",
    "StoreUnavailableError",
    "ConflictError",
    "LockTimeoutError",
    "SnapshotTooLargeError",
    "InvalidKeyError",
    "ExplorationLimitError",
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
    "event_payload",
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


# -----------------------------------------------------------------------------
# 💤 PEP 562 hooks -- resolve the names in `_LAZY_ATTRS` on first access
# -----------------------------------------------------------------------------
def __getattr__(name: str) -> Any:
    """Import and cache a lazily-provided public name.

    Args:
        name: The attribute being looked up on the package.

    Returns:
        The resolved object (also stored in the module namespace, so this
        hook runs at most once per name).

    Raises:
        AttributeError: If ``name`` is not a lazily-provided public name.
    """
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module_name, attr = target
    value = getattr(importlib.import_module(module_name, __name__), attr)
    globals()[name] = value  # 💡 cache: later lookups skip this hook
    return value


def __dir__() -> List[str]:
    """List every public name, including the not-yet-resolved lazy ones.

    📝 RU-40: limited to ``__all__`` plus module dunders, so the ``typing``
    helpers and submodules that merely happened to be imported do not show
    up in ``dir()`` / tab completion as if they were API.
    """
    dunders = {n for n in globals() if n.startswith("__")}
    return sorted({*__all__, *_LAZY_ATTRS, *dunders})
