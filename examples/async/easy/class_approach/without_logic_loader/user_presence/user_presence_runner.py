# -------------------------------------------------------------------------------
# 🟢 Async User Presence Runner
# examples/async/easy/class_approach/without_logic_loader/user_presence/user_presence_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async user presence simulation with explicit logic binding.

Demonstrates:
  • Async action methods.
  • Explicit MachineLogic binding.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

# --- Ensure project root on PYTHONPATH ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)

from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from user_presence_logic import UserPresenceLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the user presence state machine."""
    logger.info("\n--- 🟢 Async User Presence Simulation ---")

    config_path = os.path.join(os.path.dirname(__file__), "user_presence.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = UserPresenceLogic()
    machine_logic = MachineLogic(
        actions={"update_last_seen": logic.update_last_seen}
    )
    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()
    logger.info(f"Initial state: {interpreter.current_state_ids}")

    logger.info("➡️ Sending CONNECT event...")
    await interpreter.send("CONNECT", user_id="user-123")
    await asyncio.sleep(3)
    logger.info(f"State after CONNECT: {interpreter.current_state_ids}")

    logger.info("➡️ Sending DISCONNECT event...")
    await interpreter.send("DISCONNECT")
    await asyncio.sleep(2)
    logger.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
