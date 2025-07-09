# examples/sync/super_complex/class_approach/with_logic_loader/ecommerce_fulfillment_runner.py
# -----------------------------------------------------------------------------
# 🛒 Super-Complex Example: E-Commerce Fulfillment (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a complete e-commerce order fulfillment lifecycle.
#
# Key Concepts Illustrated:
#   - Top-Level Parallel States: `orderFlow`, `inventorySync`, and
#     `customerSupport` run concurrently.
#   - Hierarchical States: `shipping` is a parallel state within `orderFlow`.
#   - `onDone` bubbling: Final states in children trigger `onDone` in parents.
#   - Automatic Logic Discovery via `logic_providers`.
#   - Parameterized actions and synchronous `invoke` services.
# -----------------------------------------------------------------------------
import json
import logging
import os
import sys
import random
import time

from examples.sync.super_complex.functional_approach.with_logic_loader.ecommerce_fulfillment_logic import (
    ECommerceFulfillmentLogic,
)

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../../..")
    ),
)
from src.xstate_statemachine import create_machine, SyncInterpreter


# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main():
    print("\n--- 🛒 Synchronous E-Commerce Fulfillment Simulation ---")

    # --- Setup ---
    with open("ecommerce_fulfillment.json", "r") as f:
        config = json.load(f)

    # Instantiate the logic provider
    fulfillment_logic = ECommerceFulfillmentLogic()

    # Create the machine, passing the instance for auto-discovery
    machine = create_machine(config, logic_providers=[fulfillment_logic])
    interpreter = SyncInterpreter(machine)

    # --- Simulation ---
    interpreter.start()
    interpreter.context.update(
        {
            "orderId": f"ord_{random.randint(100, 999)}",
            "cart": ["item-a", "item-b"],
        }
    )
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    # --- Scenario 1: Successful Order ---
    print("\n--- Scenario 1: Successful Order ---")
    interpreter.send("CHECKOUT")
    interpreter.send("SUBMIT_PAYMENT", card_number="valid_card")
    interpreter.send("RESERVE_SUCCESS")
    interpreter.send("PACKING_DONE")
    # At this point, shipping invoke starts automatically
    time.sleep(1.5)  # Allow arrangeShipment service to complete
    interpreter.send("SHIP")
    interpreter.send("DELIVERED")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}")

    # --- Scenario 2: Payment Fails then Cancels ---
    print("\n--- Scenario 2: Payment Fails & Order is Cancelled ---")
    # Re-create interpreter for a clean run
    interpreter = SyncInterpreter(machine).start()
    interpreter.context.update(
        {"orderId": f"ord_{random.randint(100, 999)}", "cart": ["item-c"]}
    )
    interpreter.send("CHECKOUT")
    interpreter.send(
        "SUBMIT_PAYMENT", card_number="fail_card"
    )  # This will fail
    logging.info(
        f"State after failed payment: {interpreter.current_state_ids}"
    )
    interpreter.send("CANCEL_ORDER")
    logging.info(f"Final State: {interpreter.current_state_ids}")

    # --- Scenario 3: Interact with other parallel states ---
    print("\n--- Scenario 3: Interact with Support and Inventory ---")
    interpreter.send("ITEM_CHANGED")  # inventorySync region
    interpreter.send("OPEN_TICKET")  # customerSupport region
    logging.info(
        f"State after parallel events: {interpreter.current_state_ids}"
    )

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
