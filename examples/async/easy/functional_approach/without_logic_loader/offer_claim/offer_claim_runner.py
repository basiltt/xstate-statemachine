# -------------------------------------------------------------------------------
# 🎉 Async Offer Claim Runner
# examples/async/easy/functional_approach/without_logic_loader/offer_claim/offer_claim_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async one-time offer claim simulation with explicit logic.

Demonstrates:
  • A final state after CLAIM.
  • Ignoring repeated CLAIM events.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from offer_claim_logic import set_claimant

# -----------------------------------------------------------------------------
# 📂 Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the one-time offer claim state machine."""
    logger.info("\n--- 🎉 Async Offer Claim Simulation ---")

    config_path = os.path.join(os.path.dirname(__file__), "offer_claim.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine_logic = MachineLogic(actions={"set_claimant": set_claimant})
    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()
    logger.info(f"Initial state: {interpreter.current_state_ids}")

    await asyncio.sleep(1)

    # First claim attempt
    logger.info("➡️ Sending CLAIM event...")
    await interpreter.send("CLAIM", user="basil")
    await asyncio.sleep(1.1)
    logger.info(f"State after first CLAIM: {interpreter.current_state_ids}")

    # Second claim should be ignored
    logger.info("➡️ Sending CLAIM event again...")
    await interpreter.send("CLAIM", user="another_user")
    await asyncio.sleep(2)
    logger.info(f"Final state (unchanged): {interpreter.current_state_ids}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
