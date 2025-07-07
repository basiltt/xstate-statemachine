# src/xstate_machine/machine_logic.py
from __future__ import annotations
import logging  # 📝 Added import for logging
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
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for External Dependencies
# -----------------------------------------------------------------------------
# These imports are only for type checking purposes to avoid circular
# dependencies at runtime.
# -----------------------------------------------------------------------------
if TYPE_CHECKING:
    from .interpreter import Interpreter
    from .models import (
        ActionDefinition,
    )  # ✅ Corrected import for ActionDefinition


# -----------------------------------------------------------------------------
# 🧬 Type Variables & Callables
# -----------------------------------------------------------------------------
# Defining generic TypeVars and Callable types for actions, guards, and services
# ensures strong static type checking and improves code readability by clearly
# specifying the expected signatures of these machine logic components.
# -----------------------------------------------------------------------------

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

ActionCallable = Callable[
    [
        "Interpreter",
        TContext,
        Event,
        "ActionDefinition",
    ],  # ✅ Event is now a full object
    Union[None, Awaitable[None]],
]
GuardCallable = Callable[
    [TContext, Event], bool
]  # ✅ Event is now a full object
ServiceCallable = Callable[
    ["Interpreter", TContext, Event], Awaitable[Any]
]  # ✅ Event is now a full object


# -----------------------------------------------------------------------------
# 🧠 Machine Logic Implementation
# -----------------------------------------------------------------------------
# The `MachineLogic` class acts as a centralized registry for all custom
# behaviors (actions, guards, and services) that a state machine can invoke.
# This adheres to the "Separation of Concerns" principle, keeping the machine
# definition declarative and the implementation details separate.
# -----------------------------------------------------------------------------


class MachineLogic(Generic[TContext, TEvent]):
    """
    A container for the implementation logic of a state machine.

    This class serves as a registry for custom actions, guards (conditional
    logic for transitions), and services (asynchronous operations) that are
    referenced by name within a state machine's declarative configuration.
    It separates the "what" (machine definition) from the "how" (logic implementation).

    Attributes:
        actions (Dict[str, ActionCallable]): A dictionary mapping action names
            (as strings) to their executable `ActionCallable` implementations.
            These functions typically modify context or trigger side effects.
        guards (Dict[str, GuardCallable]): A dictionary mapping guard names
            (as strings) to their `GuardCallable` implementations. These are
            functions that return a boolean, determining if a transition is allowed.
        services (Dict[str, ServiceCallable]): A dictionary mapping service names
            (as strings) to their `ServiceCallable` implementations. These are
            asynchronous functions that can be invoked by the machine.
    """

    def __init__(
        self,
        actions: Optional[
            Dict[str, ActionCallable]
        ] = None,  # ✅ Used Optional for default None
        guards: Optional[
            Dict[str, GuardCallable]
        ] = None,  # ✅ Used Optional for default None
        services: Optional[
            Dict[str, ServiceCallable]
        ] = None,  # ✅ Used Optional for default None
    ):
        """
        Initializes the MachineLogic instance.

        All parameters are optional and default to empty dictionaries, allowing
        a machine to be defined with only the logic it requires.

        Args:
            actions (Optional[Dict[str, ActionCallable]]): A dictionary of
                action implementations. Keys are action names (str), values are
                callable functions. Defaults to an empty dictionary if not provided.
            guards (Optional[Dict[str, GuardCallable]]): A dictionary of
                guard implementations. Keys are guard names (str), values are
                callable functions returning a boolean. Defaults to an empty
                dictionary if not provided.
            services (Optional[Dict[str, ServiceCallable]]): A dictionary of
                asynchronous service implementations. Keys are service names (str),
                values are awaitable callable functions. Defaults to an empty
                dictionary if not provided.
        """
        logger.info("Initializing MachineLogic...")
        self.actions: Dict[str, ActionCallable] = actions or {}
        self.guards: Dict[str, GuardCallable] = guards or {}
        self.services: Dict[str, ServiceCallable] = services or {}
        logger.info(
            "MachineLogic initialized with %d actions, %d guards, %d services.",
            len(self.actions),
            len(self.guards),
            len(self.services),
        )
