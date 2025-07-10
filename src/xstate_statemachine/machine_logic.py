# /src/xstate_statemachine/machine_logic.py
# -----------------------------------------------------------------------------
# 🧠 Machine Logic Container
# -----------------------------------------------------------------------------
# This module defines the `MachineLogic` class, which serves as a centralized
# container or "registry" for all custom behaviors (actions, guards, and
# services) that a state machine can invoke.
#
# This class is fundamental to the "Separation of Concerns" principle that
# underpins the library. It allows developers to keep the declarative state
# machine definition (the JSON) separate from its imperative implementation
# details (the Python code). This makes both the logic and the state flow
# easier to manage, test, and reason about.
# -----------------------------------------------------------------------------
"""
Provides a data structure for holding a state machine's implementation logic.

This module contains the `MachineLogic` class, which is used to explicitly
bind the string names of actions, guards, and services from a machine's
configuration to their corresponding Python callable functions.
"""
# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from __future__ import (
    annotations,
)  # Enables postponed evaluation of type annotations

import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import Event

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for Forward References
# -----------------------------------------------------------------------------
# This block is used for type hinting to prevent circular import errors at
# runtime, which can occur when two modules depend on each other. The type
# hints are only evaluated by static type checkers.
if TYPE_CHECKING:
    from .base_interpreter import BaseInterpreter  # noqa: F401
    from .models import ActionDefinition  # noqa: F401

# -----------------------------------------------------------------------------
# 🧬 Type Variables & Callable Signatures
# -----------------------------------------------------------------------------
# These generic TypeVars and specific Callable type aliases are used to
# document the ideal function signatures for actions, guards, and services.
# They provide strong typing support for developers implementing machine logic.
# -----------------------------------------------------------------------------

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

# A blueprint for any action function. It receives the interpreter instance,
# the mutable context, the triggering event, and its own definition.
ActionCallable = Callable[
    ["BaseInterpreter", TContext, Event, "ActionDefinition"],
    Union[None, Awaitable[None]],
]

# A blueprint for any guard function. It must be a pure, synchronous function
# that returns a boolean.
GuardCallable = Callable[[TContext, Event], bool]

# A blueprint for any service function. It can be sync or async.
ServiceCallable = Callable[
    ["BaseInterpreter", TContext, Event], Union[Any, Awaitable[Any]]
]


# -----------------------------------------------------------------------------
# 🧠 MachineLogic Class Definition
# -----------------------------------------------------------------------------


class MachineLogic(Generic[TContext, TEvent]):
    """A container for the implementation logic of a state machine.

    This class serves as a simple registry for custom actions, guards, and
    services. An instance of this class is passed to `create_machine` when
    using the "explicit binding" pattern. It cleanly separates the "what"
    (the machine's JSON definition) from the "how" (the Python code that
    executes the defined behaviors).

    Attributes:
        actions: A dictionary mapping action names to their callable
                 implementations.
        guards: A dictionary mapping guard names to their boolean-returning
                callable implementations.
        services: A dictionary mapping service names to their callable
                  implementations, which can be sync or async.
    """

    def __init__(
        self,
        actions: Optional[Dict[str, Callable[..., Any]]] = None,
        guards: Optional[Dict[str, Callable[..., bool]]] = None,
        services: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        """Initializes the MachineLogic instance.

        This constructor accepts dictionaries of callables. Using a more
        generic `Callable[..., Any]` hint makes the class flexible, allowing
        users to provide functions with more specific interpreter type hints
        (e.g., `SyncInterpreter` instead of `BaseInterpreter`) without causing
        type-checking errors.

        Args:
            actions: A dictionary mapping action names (str) to their
                Python function implementations. Defaults to an empty dict.
            guards: A dictionary mapping guard names (str) to their
                Python function implementations. Defaults to an empty dict.
            services: A dictionary mapping service names (str) to their
                Python function implementations. Defaults to an empty dict.
        """
        logger.info("🧠 Initializing MachineLogic container...")

        # ✅ Use `or {}` as a robust way to default to an empty dictionary
        #    if None is passed.
        self.actions: Dict[str, Callable[..., Any]] = actions or {}
        self.guards: Dict[str, Callable[..., bool]] = guards or {}
        self.services: Dict[str, Callable[..., Any]] = services or {}

        logger.info(
            "✅ MachineLogic initialized with %d actions, %d guards, and %d services.",
            len(self.actions),
            len(self.guards),
            len(self.services),
        )
