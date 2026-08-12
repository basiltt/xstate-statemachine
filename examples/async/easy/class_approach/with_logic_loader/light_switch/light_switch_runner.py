# -------------------------------------------------------------------------------
# 💡 Async Light Switch Runner
# examples/async/easy/class_approach/with_logic_loader/light_switch/light_switch_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async light switch simulation using LogicLoader.

Demonstrates:
  • Automatic binding of class-based actions.
  • Simple TOGGLE events driving state transitions.
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

from xstate_statemachine import create_machine, Interpreter
from light_switch_logic import LightSwitchLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚦 Execute the light switch state machine."""
    logger.info("\n--- 💡 Async Light Switch Simulation ---")

    # Load machine definition
    config_path = os.path.join(os.path.dirname(__file__), "light_switch.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    # Create machine with logic provider
    logic = LightSwitchLogic()
    machine = create_machine(config, logic_providers=[logic])

    # Start interpreter
    interpreter = await Interpreter(machine).start()
    logger.info(f"Initial state: {interpreter.current_state_ids}")

    # Toggle twice
    await interpreter.send("TOGGLE")
    await asyncio.sleep(0.01)
    logger.info(f"State after TOGGLE: {interpreter.current_state_ids}")

    await asyncio.sleep(1)  # Simulate some delay before next toggle

    await interpreter.send("TOGGLE")
    await asyncio.sleep(0.01)
    logger.info(f"State after second TOGGLE: {interpreter.current_state_ids}")

    await asyncio.sleep(1)  # Simulate some delay before next toggle

    # Stop interpreter
    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
