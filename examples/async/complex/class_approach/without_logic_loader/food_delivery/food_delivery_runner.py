# -------------------------------------------------------------------------------
# 🍔 Food Delivery Runner
# examples/async/complex/class_approach/without_logic_loader/food_delivery_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the asynchronous food delivery simulation
with explicit logic binding.
"""

import asyncio
import json
import logging
import os
import random
import sys
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

# -----------------------------------------------------------------------------
# 📂 Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from food_delivery_logic import FoodDeliveryLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the food delivery workflow simulation."""
    logger.info("\n--- 🍔 Async Food Delivery Simulation ---")

    path = os.path.join(os.path.dirname(__file__), "food_delivery.json")
    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = FoodDeliveryLogic()
    machine_logic = MachineLogic(
        actions={
            "set_pending_status": logic.set_pending_status,
            "log_confirmation": logic.log_confirmation,
            "set_rejection_error": logic.set_rejection_error,
            "set_timeout_error": logic.set_timeout_error,
            "update_status_to_finding_driver": logic.update_status_to_finding_driver,
            "update_status_to_preparing": logic.update_status_to_preparing,
            "update_status_to_delivering": logic.update_status_to_delivering,
            "update_status_to_delivered": logic.update_status_to_delivered,
            "log_failure_reason": logic.log_failure_reason,
        },
        services={"confirm_with_restaurant": logic.confirm_with_restaurant},
    )
    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    order_id = f"ORD-{random.randint(1000, 9999)}"
    await interpreter.send("PLACE_ORDER", order_id=order_id)
    await asyncio.sleep(2.5)

    if {"foodDelivery.order_failed"} <= interpreter.current_state_ids:
        logger.info("🚫 Order was rejected early.")
        await interpreter.stop()
        return

    logger.info("🚚 Searching for driver (3s)...")
    await asyncio.sleep(3)
    await interpreter.send("DRIVER_ASSIGNED", driver_name="Dave")

    await asyncio.sleep(2)
    await interpreter.send("ORDER_READY_FOR_PICKUP")
    await asyncio.sleep(3)
    await interpreter.send("ORDER_DELIVERED")

    await asyncio.sleep(1)
    logger.info(f"Final state: {interpreter.current_state_ids}")
    logger.info(f"Context: {interpreter.context}")

    await interpreter.stop()
    logger.info("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
