# -------------------------------------------------------------------------------
# 🏡 Smart Home Runner
# examples/async/super_complex/class_approach/with_logic_loader/smart_home/smart_home_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the Smart Home Automation simulation.

Demonstrates:
  • Top-level parallel state regions (lighting, climate, security).
  • Actor spawning and inter-actor events.
  • Service invocation and timed transitions.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

from smart_home_logic import SmartHomeLogic  # noqa: E402
from src.xstate_statemachine import create_machine, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the Smart Home simulation."""
    logger.info("\n--- 🏡 Smart Home Simulation (Class / LogicLoader) ---")

    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "smart_home.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic_provider = SmartHomeLogic()
    machine = create_machine(config, logic_providers=[logic_provider])
    interpreter = await Interpreter(machine).start()

    logger.info(f"Initial states: {interpreter.current_state_ids}")
    logger.info(f"Spawned actors: {list(interpreter._actors.keys())}")  # noqa:

    # Scenario 1: Adjust climate
    logger.info("\n--- Scenario 1: Adjusting Climate ---")
    await interpreter.send("SET_TEMP", temp=72)

    # Scenario 2: Arm system and trigger alarm
    logger.info("\n--- Scenario 2: Arming & Motion Detection ---")
    await interpreter.send("ARM_AWAY")
    await asyncio.sleep(3.5)
    logger.info(f"States after arming: {interpreter.current_state_ids}")

    await interpreter.send("MOTION_DETECTED")
    await asyncio.sleep(1.0)
    logger.info(f"States after motion: {interpreter.current_state_ids}")

    # Scenario 3: Disarm system
    logger.info("\n--- Scenario 3: Disarming System ---")
    await interpreter.send("DISARM", code="1234")
    await asyncio.sleep(1.0)
    logger.info(f"Final states: {interpreter.current_state_ids}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
