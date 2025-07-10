# -------------------------------------------------------------------------------
# 🔐 Async 2FA Runner
# examples/async/complex/class_approach/with_logic_loader/two_factor_auth/two_factor_auth_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the asynchronous two-factor authentication simulation
using :class:`TwoFactorAuthLogic` via LogicLoader.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter

# -----------------------------------------------------------------------------
# 📂 Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from two_factor_auth_logic import TwoFactorAuthLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute two-factor authentication scenarios."""
    logger.info("\n--- 🔐 Async 2FA Simulation (Class / LogicLoader) ---")

    # Load state machine configuration
    path = os.path.join(os.path.dirname(__file__), "two_factor_auth.json")
    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    # Instantiate logic provider and create machine
    logic = TwoFactorAuthLogic()
    machine = create_machine(config, logic_providers=[logic])

    # --- Scenario 1: Successful Authentication ---
    logger.info("\n--- Scenario 1: Successful Authentication ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("START_2FA")
    await asyncio.sleep(2.5)

    correct_code = interpreter1.context.get("generated_code")
    logger.info(f"Runner: Submitting correct code '{correct_code}'")
    await interpreter1.send("SUBMIT_CODE", code=correct_code)
    await asyncio.sleep(1.0)
    logger.info(f"Final state: {interpreter1.current_state_ids}")
    await interpreter1.stop()

    # --- Scenario 2: Incorrect then Correct Code ---
    logger.info("\n--- Scenario 2: Incorrect then Correct Code ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("START_2FA")
    await asyncio.sleep(2.5)

    generated = interpreter2.context.get("generated_code")
    logger.info(
        f"Runner: Generated code is '{generated}', sending wrong first."
    )
    await interpreter2.send("SUBMIT_CODE", code="000000")
    await asyncio.sleep(0.5)
    logger.info(f"State after wrong code: {interpreter2.current_state_ids}")

    logger.info("Runner: Now submitting correct code.")
    await interpreter2.send("SUBMIT_CODE", code=generated)
    await asyncio.sleep(1.0)
    logger.info(f"Final state: {interpreter2.current_state_ids}")
    await interpreter2.stop()

    logger.info("\n--- ✅ All Scenarios Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
