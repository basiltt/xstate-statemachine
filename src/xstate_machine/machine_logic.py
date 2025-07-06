# src/xstate_python/machine_logic.py
from typing import Any, Awaitable, Callable, Dict, Union
from .events import Event

# -----------------------------------------------------------------------------
# 🧠 Machine Logic
# -----------------------------------------------------------------------------
# This class acts as a container for the concrete implementations of a state
# machine's behaviors, applying the Strategy pattern.
# -----------------------------------------------------------------------------

# Define common types for context and callables
Context = Dict[str, Any]
ActionCallable = Callable[[Context, Event], Union[None, Awaitable[None]]]
GuardCallable = Callable[[Context, Event], bool]
ServiceCallable = Callable[[Context, Event], Awaitable[Any]]


class MachineLogic:
    """
    A container for the implementation logic of a state machine.

    This class decouples the state machine's definition (JSON) from its
    concrete implementation (Python functions), allowing for clean architecture.

    Attributes:
        actions (Dict): Maps string names to Python functions for side-effects.
        guards (Dict): Maps string names to Python functions for transition conditions.
        services (Dict): Maps string names to async Python functions for invoked tasks.
    """

    def __init__(
        self,
        actions: Dict[str, ActionCallable] = None,
        guards: Dict[str, GuardCallable] = None,
        services: Dict[str, ServiceCallable] = None,
    ):
        """
        Initializes the MachineLogic container.

        Args:
            actions: A dictionary mapping action names to callable functions.
            guards: A dictionary mapping guard names to callable functions.
            services: A dictionary mapping service names to awaitable functions.
        """
        self.actions = actions or {}
        self.guards = guards or {}
        self.services = services or {}
