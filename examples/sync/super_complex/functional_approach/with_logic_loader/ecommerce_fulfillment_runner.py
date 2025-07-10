# examples/sync/super_complex/class_approach/with_logic_loader/ecommerce_fulfillment_runner.py
# -------------------------------------------------------------------------------
# 🛒 E-Commerce Fulfillment Runner
# -------------------------------------------------------------------------------
"""
Runner for the E-Commerce Fulfillment simulation,
now wired to snake_case actions and guards in the JSON.
"""

import json
import logging
import random
import time
from typing import Any, Dict

from ecommerce_fulfillment_logic import ECommerceFulfillmentLogic  # noqa: E402
from src.xstate_statemachine import create_machine, SyncInterpreter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    """🚀 Execute the fulfillment simulation scenarios."""
    print("\n--- 🛒 E-Commerce Fulfillment Simulation ---")
    config_path = "ecommerce_fulfillment.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = ECommerceFulfillmentLogic()
    machine = create_machine(config, logic_providers=[logic])
    interp = SyncInterpreter(machine)
    interp.start()

    # prepare a draft order
    interp.context.update(
        {
            "orderId": f"ord_{random.randint(100, 999)}",
            "cart": ["item-a", "item-b"],
        }
    )
    logger.info("Initial State: %s", interp.current_state_ids)

    # Scenario 1: Successful order
    print("\n--- Scenario 1: Successful Order ---")
    interp.send("CHECKOUT")
    time.sleep(1)  # simulate some processing time
    interp.send("SUBMIT_PAYMENT", card_number="valid_card")
    time.sleep(2)  # simulate payment processing
    # simulate inventory reserve + packing + shipping
    interp.send("RESERVE_SUCCESS")
    time.sleep(1)
    interp.send("PACKING_DONE")
    time.sleep(1.5)
    interp.send("SHIP")
    time.sleep(1)
    interp.send("DELIVERED")
    logger.info("Final State: %s", interp.current_state_ids)
    logger.info("Final Context: %s", interp.context)
    time.sleep(1)

    # Scenario 2: Payment fails & cancellation
    print("\n--- Scenario 2: Payment Fails & Cancel ---")
    interp = SyncInterpreter(machine)
    interp.start()
    interp.context.update(
        {"orderId": f"ord_{random.randint(100, 999)}", "cart": ["item-c"]}
    )
    interp.send("CHECKOUT")
    time.sleep(1)  # simulate some processing time
    interp.send("SUBMIT_PAYMENT", card_number="fail_card")
    time.sleep(2)  # simulate payment processing
    logger.info("State after failure: %s", interp.current_state_ids)

    interp.send("CANCEL_ORDER")
    time.sleep(2)  # simulate cancellation processing
    logger.info("Final State: %s", interp.current_state_ids)

    # Scenario 3: Parallel region interaction
    print("\n--- Scenario 3: Parallel Events ---")
    interp.send("ITEM_CHANGED")
    time.sleep(1)  # simulate item change processing
    interp.send("OPEN_TICKET")
    logger.info("State after parallel: %s", interp.current_state_ids)
    time.sleep(1)

    interp.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
