# examples/with_logic_loader/coffee_machine/functional_approach/coffee_machine_logic.py

# -----------------------------------------------------------------------------
# ☕ Coffee Machine Logic (Functional Approach)
# -----------------------------------------------------------------------------
# This module provides a "functional" implementation of the logic for a coffee
# machine state machine. Each action, guard, and service is a standalone
# function designed to be dynamically discovered by the `LogicLoader`.
#
# This approach promotes a clean separation of concerns, where the machine's
# behavior (the "how") is defined here, entirely separate from the machine's
# structure (the "what," defined in the JSON configuration).
# -----------------------------------------------------------------------------

import asyncio
import logging
from typing import Any, Dict

# -----------------------------------------------------------------------------
# 📚 Type Hint Imports
# -----------------------------------------------------------------------------
# These imports are used for type hinting the function signatures, providing
# excellent IDE support and code clarity.
from src.xstate_statemachine.events import Event
from src.xstate_statemachine.interpreter import Interpreter
from src.xstate_statemachine.models import ActionDefinition

# -----------------------------------------------------------------------------
# 🎬 Actions
# -----------------------------------------------------------------------------
# Actions are "fire-and-forget" operations that modify the machine's context
# or perform side effects (like logging). They do not return a value.
# -----------------------------------------------------------------------------


async def set_espresso(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Sets the selected drink to Espresso in the machine's context.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    context["selectedDrink"] = "Espresso"
    logging.info("Action: ☕ Selected: %s", context["selectedDrink"])


async def set_latte(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Sets the selected drink to Latte in the machine's context.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    context["selectedDrink"] = "Latte"
    logging.info("Action: ☕ Selected: %s", context["selectedDrink"])


async def log_selection(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Logs a confirmation message after a drink has been selected.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    logging.info(
        "--- ✅ Customer selected %s. Ready to brew! ---",
        context["selectedDrink"],
    )


async def start_brewing(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Logs a message indicating the start of the brewing process.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    logging.info(
        "--- ⏳ Brewing %s... Please wait. ---", context["selectedDrink"]
    )


async def increment_coffee_count(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Increments the total number of coffees made.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    context["coffeeCount"] += 1
    logging.info("Action: 📈 Total coffees made: %d", context["coffeeCount"])


async def decrement_water(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Decreases the water level after brewing, ensuring it doesn't go below zero.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    # 💧 Safely decrement water level.
    context["waterLevel"] = max(0, context["waterLevel"] - 10)
    logging.info("Action: 💧 Water level is now: %d%%", context["waterLevel"])


async def serve_drink(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Logs a message that the drink is ready.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    logging.info(
        "--- 🎉 Your %s is ready! Enjoy! ---", context["selectedDrink"]
    )


async def start_cleaning(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Logs the start of the cleaning cycle.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    logging.info("--- 🧼 Cleaning machine... This will take a moment. ---")


async def set_water_to_full(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Sets the water level context variable to 100.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context (state) of the machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of this action.
    """
    context["waterLevel"] = 100
    logging.info(
        "Action: 💧 Water tank is now FULL (%d%%).", context["waterLevel"]
    )


# -----------------------------------------------------------------------------
# 🛡️ Guards
# -----------------------------------------------------------------------------
# Guards are synchronous functions that return a boolean value. They act as
# conditional checks to determine if a transition should be taken.
# -----------------------------------------------------------------------------


def can_brew(context: Dict[str, Any], event: Event) -> bool:
    """Checks if a drink is selected and there is enough water to brew.

    Args:
        context (Dict[str, Any]): The current context of the machine.
        event (Event): The event that triggered this guard check.

    Returns:
        bool: `True` if the machine can brew, `False` otherwise.
    """
    is_selected = context.get("selectedDrink") is not None
    has_water = context.get("waterLevel", 0) > 0

    # 🧐 Log the reason for failure to aid in debugging.
    if not is_selected:
        logging.warning("Guard: ❌ No drink selected!")
    if not has_water:
        logging.warning("Guard: ❌ Not enough water! Please refill.")

    return is_selected and has_water


def can_clean(context: Dict[str, Any], event: Event) -> bool:
    """Checks if the machine has made enough coffees to require cleaning.

    Args:
        context (Dict[str, Any]): The current context of the machine.
        event (Event): The event that triggered this guard check.

    Returns:
        bool: `True` if the machine needs cleaning, `False` otherwise.
    """
    needs_cleaning = context.get("coffeeCount", 0) >= 3

    # 🧐 Provide informative logging for both success and failure cases.
    if needs_cleaning:
        logging.info(
            "Guard: ✅ %d coffees made. Cleaning is allowed.",
            context["coffeeCount"],
        )
    else:
        logging.warning(
            "Guard: ℹ️ Only %d coffees made. No need to clean yet.",
            context["coffeeCount"],
        )

    return needs_cleaning


# -----------------------------------------------------------------------------
# ⚙️ Services
# -----------------------------------------------------------------------------
# Services are functions that represent long-running or asynchronous processes.
# They can return data to the parent machine upon completion.
# -----------------------------------------------------------------------------


async def refill_water_service(
    interpreter: Interpreter, context: Dict[str, Any], event: Event
) -> str:
    """Simulates an asynchronous process of refilling the water tank.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the machine.
        event (Event): The event that invoked this service.

    Returns:
        str: A message indicating the result of the operation. This value
             will be placed in the `onDone` event sent back to the machine.
    """
    logging.info(
        "Service: 💧 Refilling water tank... This will take 4 seconds."
    )
    # ⏳ Simulate a time-consuming I/O operation.
    await asyncio.sleep(4)
    logging.info("Service: ✅ Water refilled!")
    return "Water refilled successfully"
