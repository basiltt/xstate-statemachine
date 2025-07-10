# src/xstate_statemachine/machine_logic.py

# -----------------------------------------------------------------------------
# 🧠 Machine Logic
# -----------------------------------------------------------------------------
# This module defines the `MachineLogic` class, which acts as a centralized
# registry for all custom behaviors (actions, guards, and services) that a
# state machine can invoke. This adheres to the "Separation of Concerns"
# principle, keeping the machine definition declarative and the implementation
# details separate.
# -----------------------------------------------------------------------------

from __future__ import annotations
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Union,
    TypeVar,
    Generic,
    TYPE_CHECKING,
    Optional,
)
from .events import Event

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for External Dependencies
# -----------------------------------------------------------------------------
if TYPE_CHECKING:
    from .base_interpreter import BaseInterpreter  # noqa: F401
    from .models import ActionDefinition  # noqa: F401

# -----------------------------------------------------------------------------
# 🧬 Type Variables & Callables
# -----------------------------------------------------------------------------
# These generic TypeVars and more specific Callable type aliases are used to
# document the ideal function signatures and provide strong typing internally.
# -----------------------------------------------------------------------------

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

ActionCallable = Callable[
    ["BaseInterpreter", TContext, Event, "ActionDefinition"],
    Union[None, Awaitable[None]],
]
GuardCallable = Callable[[TContext, Event], bool]
# ✅ FIX: ServiceCallable now correctly allows both sync and async return values.
ServiceCallable = Callable[
    ["BaseInterpreter", TContext, Event], Union[Any, Awaitable[Any]]
]


# -----------------------------------------------------------------------------
# 🧠 MachineLogic Class Definition
# -----------------------------------------------------------------------------


class MachineLogic(Generic[TContext, TEvent]):
    """
    A container for the implementation logic of a state machine.

    This class serves as a registry for custom actions, guards (conditional
    logic for transitions), and services (asynchronous operations) that are
    referenced by name within a state machine's declarative configuration.
    It separates the "what" (machine definition) from the "how" (logic implementation).

    Attributes:
        actions (Dict[str, Callable]): A dictionary mapping action names
            to their executable callable implementations.
        guards (Dict[str, Callable]): A dictionary mapping guard names
            to their boolean-returning callable implementations.
        services (Dict[str, Callable]): A dictionary mapping service names
            to their callable implementations.
    """

    def __init__(
        self,
        # ✅ FIX: Use a more generic Callable hint for constructor arguments.
        # This makes the class more flexible and resolves type checking errors
        # when users provide functions with more specific interpreter types
        # (e.g., SyncInterpreter instead of BaseInterpreter).
        actions: Optional[Dict[str, Callable[..., Any]]] = None,
        guards: Optional[Dict[str, Callable[..., bool]]] = None,
        services: Optional[Dict[str, Callable[..., Any]]] = None,
    ):
        """
        Initializes the MachineLogic instance.

        Args:
            actions (Optional[Dict[str, Callable]]): A dictionary of
                action implementations. Defaults to an empty dictionary.
            guards (Optional[Dict[str, Callable]]): A dictionary of
                guard implementations. Defaults to an empty dictionary.
            services (Optional[Dict[str, Callable]]): A dictionary of
                service implementations. Defaults to an empty dictionary.
        """
        logger.info("Initializing MachineLogic...")
        self.actions: Dict[str, Callable[..., Any]] = actions or {}
        self.guards: Dict[str, Callable[..., bool]] = guards or {}
        self.services: Dict[str, Callable[..., Any]] = services or {}
        logger.info(
            "MachineLogic initialized with %d actions, %d guards, %d services.",
            len(self.actions),
            len(self.guards),
            len(self.services),
        )
