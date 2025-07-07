import asyncio
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
from xstate_statemachine.events import Event
from xstate_statemachine.exceptions import ImplementationMissingError

# Import MachineNode for runtime usage, specifically for the type hint in services
from xstate_statemachine.models import MachineNode  # ADDED THIS LINE

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xstate_statemachine.interpreter import Interpreter
    from xstate_statemachine.models import (
        ActionDefinition,
    )


TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

ActionCallable = Callable[
    [
        "Interpreter",
        TContext,
        Event,
        "ActionDefinition",
    ],
    Union[None, Awaitable[None]],
]
GuardCallable = Callable[[TContext, Event], bool]
ServiceCallable = Callable[["Interpreter", TContext, Event], Awaitable[Any]]


class MachineLogic(Generic[TContext, TEvent]):
    """
    A container for the implementation logic of a state machine.
    """

    def __init__(
        self,
        actions: Optional[Dict[str, ActionCallable]] = None,
        guards: Optional[Dict[str, GuardCallable]] = None,
        services: Optional[
            Dict[
                str, Union[ServiceCallable, MachineNode]
            ]  # Use Union here, not `|` for older Python versions if needed.
        ] = None,
    ):
        logger.info("Initializing MachineLogic...")
        self.actions: Dict[str, ActionCallable] = actions or {}
        self.guards: Dict[str, GuardCallable] = guards or {}
        self.services: Dict[str, Union[ServiceCallable, MachineNode]] = (
            services or {}
        )  # Use Union here
        logger.info(
            "MachineLogic initialized with %d actions, %d guards, %d services.",
            len(self.actions),
            len(self.guards),
            len(self.services),
        )


# --- Actions (rest of your actions code) ---
def set_espresso(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    context["selectedDrink"] = "Espresso"
    print(f"DEBUG (Action): Selected: {context['selectedDrink']}")


def set_latte(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    context["selectedDrink"] = "Latte"
    print(f"DEBUG (Action): Selected: {context['selectedDrink']}")


def log_selection(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    print(
        f"--- Customer selected {context['selectedDrink']}. Ready to brew! ---"
    )


def start_brewing(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    print(f"--- Brewing {context['selectedDrink']}... Please wait. ---")


def increment_coffee_count(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    context["coffeeCount"] += 1
    print(f"DEBUG (Action): Total coffees made: {context['coffeeCount']}")


def decrement_water(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    """Action: Decrements water level after brewing."""
    if context["waterLevel"] > 10:  # Assuming 10 units of water per coffee
        context["waterLevel"] -= 10
    else:
        context["waterLevel"] = 0
    print(f"DEBUG (Action): Water level is now: {context['waterLevel']}%")


def serve_drink(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    print(f"--- Your {context['selectedDrink']} is ready! Enjoy! ---")


def start_cleaning(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    print("--- Cleaning machine... This will take a moment. ---")


def set_water_to_full(
    interpreter: "Interpreter",
    context: TContext,
    event: Event,
    action_def: "ActionDefinition",
):
    """Action: Sets water level back to full after refilling service completes."""
    context["waterLevel"] = 100
    print(
        f"DEBUG (Action): Water tank is now FULL ({context['waterLevel']}%)."
    )


# --- Guards (rest of your guards code) ---
def can_brew(context: TContext, event: Event) -> bool:
    is_selected = context["selectedDrink"] is not None
    has_water = context["waterLevel"] > 0
    if not is_selected:
        print("ALERT (Guard): Please select a drink first!")
    if not has_water:
        print("ALERT (Guard): Not enough water! Please refill.")
    return is_selected and has_water


def can_clean(context: TContext, event: Event) -> bool:
    needs_cleaning = context["coffeeCount"] >= 3
    if not needs_cleaning:
        print(
            f"ALERT (Guard): Only {context['coffeeCount']} coffees made. No need to clean yet."
        )
    else:
        print(
            f"DEBUG (Guard): {context['coffeeCount']} coffees made. Cleaning recommended."
        )
    return needs_cleaning


# --- Services (rest of your services code) ---
async def refill_water_service(
    interpreter: "Interpreter", context: TContext, event: Event
) -> str:
    """Service: Simulates asynchronously refilling the water tank."""
    print("--- Refilling water tank... This will take 4 seconds. ---")
    await asyncio.sleep(4)
    print("--- Water refilled! ---")
    return "Water refilled successfully"


# Create the MachineLogic instance
coffee_machine_logic = MachineLogic(
    actions={
        "setEspresso": set_espresso,
        "setLatte": set_latte,
        "logSelection": log_selection,
        "startBrewing": start_brewing,
        "incrementCoffeeCount": increment_coffee_count,
        "decrementWater": decrement_water,
        "serveDrink": serve_drink,
        "startCleaning": start_cleaning,
        "setWaterToFull": set_water_to_full,
    },
    guards={"canBrew": can_brew, "canClean": can_clean},
    services={"refillWaterService": refill_water_service},
)
