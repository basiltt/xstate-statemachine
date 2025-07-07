# examples/with_logic_loader/coffee_machine/class_approach/coffee_machine_class_logic.py
import asyncio

# -----------------------------------------------------------------------------
# ☕ Coffee Machine Logic (Class-Based)
# -----------------------------------------------------------------------------
# This module defines the core logic for a coffee machine state machine using
# a class-based approach.
#
# Key Concepts Illustrated:
#   - Encapsulation: The `CoffeeMachine` class holds the state machine's
#     interpreter, context, and all related logic (actions, guards, services).
#   - Explicit Logic Binding: This example manually creates a `MachineLogic`
#     object, mapping string names from the JSON config to the class's methods.
# -----------------------------------------------------------------------------

import logging
import sys
import os
from typing import Any, Dict

# -----------------------------------------------------------------------------
# 🐍 Path Setup
# -----------------------------------------------------------------------------
# A simple way to handle paths so the library can be found.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

from src.xstate_statemachine import (
    ActionDefinition,
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🏛️ CoffeeMachine Class
# -----------------------------------------------------------------------------
# This class encapsulates all logic and state for a coffee machine simulation.
# It showcases how to manually bind state machine logic to class methods,
# providing a structured, object-oriented way to manage behavior.
# -----------------------------------------------------------------------------


class CoffeeMachine:
    """Encapsulates the logic and interpreter for a coffee machine.

    This class serves as a single, cohesive unit for the coffee machine's
    functionality. It initializes the state machine interpreter and provides
    all the necessary action, guard, and service implementations as instance
    methods.

    Attributes:
        interpreter (Interpreter): The state machine interpreter instance that
            runs the coffee machine logic.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initializes the CoffeeMachine instance.

        This constructor performs all necessary setup:
        1.  Manually creates a `MachineLogic` object that maps action, guard,
            and service names from the config to this class's methods.
        2.  Creates the state machine node using the provided config and logic.
        3.  Creates and configures the `Interpreter` to run the machine.

        Args:
            config (Dict[str, Any]): The state machine configuration dictionary,
                typically loaded from a JSON file.
        """
        logging.info("🤖 Initializing CoffeeMachine instance...")

        # 🧠 Manually create the MachineLogic instance. This is the core of the
        # class-based approach, providing explicit binding of config names
        # to the corresponding methods of this class instance.
        machine_logic = MachineLogic(
            actions={
                "setEspresso": self.set_espresso,
                "setLatte": self.set_latte,
                "logSelection": self.log_selection,
                "startBrewing": self.start_brewing,
                "incrementCoffeeCount": self.increment_coffee_count,
                "decrementWater": self.decrement_water,
                "serveDrink": self.serve_drink,
                "startCleaning": self.start_cleaning,
                "setWaterToFull": self.set_water_to_full,
            },
            guards={"canBrew": self.can_brew, "canClean": self.can_clean},
            services={"refillWaterService": self.refill_water_service},
        )

        # 🏭 Create the machine node, injecting the configuration and the
        #    explicitly defined logic. This decouples the machine's structure
        #    from its implementation.
        machine_node = create_machine(config, logic=machine_logic)

        # 🚀 Create the interpreter and attach a logging inspector for observability.
        self.interpreter = Interpreter(machine_node)
        self.interpreter.use(LoggingInspector())
        logging.info("✅ CoffeeMachine initialized successfully.")

    # -------------------------------------------------------------------------
    # 🎬 Actions
    # -------------------------------------------------------------------------

    async def set_espresso(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to set the selected drink to Espresso."""
        ctx["selectedDrink"] = "Espresso"
        logging.info("Action: ☕ Selected: %s", ctx["selectedDrink"])

    async def set_latte(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to set the selected drink to Latte."""
        ctx["selectedDrink"] = "Latte"
        logging.info("Action: ☕ Selected: %s", ctx["selectedDrink"])

    async def log_selection(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to log a message confirming the drink selection."""
        logging.info(
            "--- ✅ Customer selected %s. Ready to brew! ---",
            ctx["selectedDrink"],
        )

    async def start_brewing(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to log the start of the brewing process."""
        logging.info(
            "--- ⏳ Brewing %s... Please wait. ---", ctx["selectedDrink"]
        )

    async def increment_coffee_count(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to increment the total number of coffees made."""
        ctx["coffeeCount"] += 1
        logging.info("Action: 📈 Total coffees made: %d", ctx["coffeeCount"])

    async def decrement_water(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to decrease the water level after brewing."""
        ctx["waterLevel"] = max(0, ctx["waterLevel"] - 10)
        logging.info("Action: 💧 Water level is now: %d%%", ctx["waterLevel"])

    async def serve_drink(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to log that the drink is ready to be served."""
        logging.info(
            "--- 🎉 Your %s is ready! Enjoy! ---", ctx["selectedDrink"]
        )

    async def start_cleaning(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to log the start of the cleaning cycle."""
        logging.info("--- 🧼 Cleaning machine... This will take a moment. ---")

    async def set_water_to_full(
        self,
        i: Interpreter,
        ctx: Dict[str, Any],
        e: Event,
        ad: ActionDefinition,
    ) -> None:
        """Action to set the water level to 100% after refilling."""
        ctx["waterLevel"] = 100
        logging.info(
            "Action: 💧 Water tank is now FULL (%d%%).", ctx["waterLevel"]
        )

    # -------------------------------------------------------------------------
    # 🛡️ Guards
    # -------------------------------------------------------------------------

    def can_brew(self, ctx: Dict[str, Any], e: Event) -> bool:
        """Guard to check if the machine has enough water and a drink is selected."""
        is_selected = ctx.get("selectedDrink") is not None
        has_water = ctx.get("waterLevel", 0) > 0

        # 🧐 Log the reason if the guard fails.
        if not has_water:
            logging.warning("Guard: ❌ Not enough water! Please refill.")
        return is_selected and has_water

    def can_clean(self, ctx: Dict[str, Any], e: Event) -> bool:
        """Guard to check if the machine has made enough coffees to require cleaning."""
        needs_cleaning = ctx.get("coffeeCount", 0) >= 3

        # 🧐 Log the reason if the guard fails.
        if not needs_cleaning:
            logging.warning(
                "Guard: ℹ️ Only %d coffees made. No need to clean yet.",
                ctx["coffeeCount"],
            )
        return needs_cleaning

    # -------------------------------------------------------------------------
    # ⚙️ Services
    # -------------------------------------------------------------------------

    async def refill_water_service(
        self, i: Interpreter, ctx: Dict[str, Any], e: Event
    ) -> str:
        """Service to simulate refilling the water tank asynchronously."""
        logging.info(
            "Service: 💧 Refilling water tank... This will take 4 seconds."
        )
        await asyncio.sleep(4)
        logging.info("Service: ✅ Water refilled!")
        return "Water refilled successfully"
