# examples/async/complex/class_approach/without_logic_loader/food_delivery_runner.py
# -----------------------------------------------------------------------------
# 🍔 Complex Example: Food Delivery Tracker (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - A sequential, multi-step async process.
#   - `invoke` to simulate an API call to a restaurant.
#   - `after` to simulate a timeout for finding a driver.
#   - Explicit Logic Binding of async and sync methods from a class.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys
import random

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from food_delivery_logic import FoodDeliveryLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- 🍔 Async Food Delivery Simulation (Class / Explicit Logic) ---"
    )

    with open("food_delivery.json", "r") as f:
        config = json.load(f)

    logic_provider = FoodDeliveryLogic()

    # Manually create the MachineLogic object
    machine_logic = MachineLogic(
        actions={
            "set_pending_status": logic_provider.set_pending_status,
            "log_confirmation": logic_provider.log_confirmation,
            "set_rejection_error": logic_provider.set_rejection_error,
            "set_timeout_error": logic_provider.set_timeout_error,
            "update_status_to_finding_driver": logic_provider.update_status_to_finding_driver,
            "update_status_to_preparing": logic_provider.update_status_to_preparing,
            "update_status_to_delivering": logic_provider.update_status_to_delivering,
            "update_status_to_delivered": logic_provider.update_status_to_delivered,
            "log_failure_reason": logic_provider.log_failure_reason,
        },
        services={
            "confirm_with_restaurant": logic_provider.confirm_with_restaurant,
        },
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    order_id = f"ORD-{random.randint(1000, 9999)}"
    await interpreter.send("PLACE_ORDER", order_id=order_id)

    # Wait for restaurant confirmation
    await asyncio.sleep(2.5)

    # Check if the order failed at the confirmation step
    if interpreter.current_state_ids == {"foodDelivery.order_failed"}:
        logging.info(
            "Simulation ended early because restaurant rejected the order."
        )
        await interpreter.stop()
        return

    # Simulate finding a driver
    logging.info("...simulating a 3-second driver search...")
    await asyncio.sleep(3)
    await interpreter.send("DRIVER_ASSIGNED", driver_name="Dave")

    # Simulate food prep and delivery
    await asyncio.sleep(2)
    await interpreter.send("ORDER_READY_FOR_PICKUP")
    await asyncio.sleep(3)
    await interpreter.send("ORDER_DELIVERED")

    await asyncio.sleep(1)
    logging.info(f"Final state: {interpreter.current_state_ids}")
    logging.info(f"Final context: {interpreter.context}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
