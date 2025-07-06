# src/xstate_machine/machine_logic.py
from __future__ import annotations
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Union,
    TypeVar,
    Generic,
    TYPE_CHECKING,
)
from .events import Event

if TYPE_CHECKING:
    from .interpreter import Interpreter

    # ✨ FIX: Import ActionDefinition for use in the type hint.
    from .models import ActionDefinition

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

# ✨ FIX: Add `ActionDefinition` as the fourth argument to the ActionCallable.
ActionCallable = Callable[
    ["Interpreter", TContext, TEvent, "ActionDefinition"],
    Union[None, Awaitable[None]],
]
GuardCallable = Callable[[TContext, TEvent], bool]
ServiceCallable = Callable[["Interpreter", TContext, TEvent], Awaitable[Any]]


class MachineLogic(Generic[TContext, TEvent]):
    """
    A container for the implementation logic of a state machine.
    """

    def __init__(
        self,
        actions: Dict[
            str, ActionCallable["Interpreter", TContext, TEvent]
        ] = None,
        guards: Dict[str, GuardCallable[TContext, TEvent]] = None,
        services: Dict[
            str, ServiceCallable["Interpreter", TContext, TEvent]
        ] = None,
    ):
        self.actions = actions or {}
        self.guards = guards or {}
        self.services = services or {}
