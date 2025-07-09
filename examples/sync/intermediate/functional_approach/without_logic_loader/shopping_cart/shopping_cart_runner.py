# examples/sync/intermediate/functional_approach/without_logic_loader/shopping_cart_runner.py

# -----------------------------------------------------------------------------
# 🛒 Intermediate Example: Synchronous Shopping Cart (Functional)
# -----------------------------------------------------------------------------
# This script simulates a basic e-commerce shopping cart.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Functional Approach: Logic is implemented as standalone functions.
#   - Explicit Logic Binding: A `MachineLogic` object is manually created
#     to map function names from the JSON to the Python functions.
#   - Guards for Validation: `cart_is_not_empty` prevents checking out
#     with an empty cart.
#   - Synchronous Service: `process_payment_sync` is an invoked service
#     that can succeed or fail.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# ⚙️ Machine Logic (Actions, Guards, Services)
# -----------------------------------------------------------------------------


# --- Actions ---
def add_item_to_cart(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Adds a new item to the 'items' list in the context."""
    item = e.payload.get("item")
    if item:
        ctx["items"].append(item)
        logging.info(
            f"🛒 Added '{item}'. Cart now has {len(ctx['items'])} item(s)."
        )


def clear_cart(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Clears all items from the cart."""
    ctx["items"] = []
    logging.info("🗑️ Cart has been emptied.")


# --- Guards ---
def cart_is_not_empty(ctx: Dict, e: Event) -> bool:
    """Checks if the 'items' list in the context is not empty."""
    is_not_empty = len(ctx.get("items", [])) > 0
    if not is_not_empty:
        logging.warning("🛡️ Guard Failed: Cannot check out with an empty cart.")
    return is_not_empty


# --- Services ---
def process_payment_sync(i: SyncInterpreter, ctx: Dict, e: Event) -> Dict:
    """A synchronous service that simulates processing a payment."""
    logging.info("💳 Service: Processing payment...")
    time.sleep(1)  # Simulate blocking work
    logging.info("✅ Service: Payment successful.")
    return {"confirmation": "XYZ-789"}


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------
def main():
    """Initializes and runs the shopping cart simulation."""
    print("\n--- 🛒 Synchronous Shopping Cart Simulation ---")

    # 1. Load the machine configuration from JSON.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "shopping_cart.json")
    with open(json_path, "r") as f:
        config = json.load(f)

    # 2. Manually create the MachineLogic object.
    logic = MachineLogic(
        actions={
            "add_item_to_cart": add_item_to_cart,
            "clear_cart": clear_cart,
        },
        guards={"cart_is_not_empty": cart_is_not_empty},
        services={"process_payment_sync": process_payment_sync},
    )

    # 3. Create the machine and interpreter.
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)

    # 4. Run the simulation.
    interpreter.start()
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    print("\n--- Scenario 1: Attempt to checkout while empty ---")
    interpreter.send("CHECKOUT")  # Will be blocked by guard
    logging.info(f"State is still: {interpreter.current_state_ids}\n")

    print("--- Scenario 2: Add items and checkout successfully ---")
    interpreter.send("ADD_ITEM", item="Milk")
    interpreter.send("ADD_ITEM", item="Bread")
    interpreter.send("CHECKOUT")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
