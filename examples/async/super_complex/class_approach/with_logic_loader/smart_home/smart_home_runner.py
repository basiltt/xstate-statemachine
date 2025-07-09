# examples/async/super_complex/class_approach/with_logic_loader/smart_home_runner.py
# -----------------------------------------------------------------------------
# 🏡 Super-Complex Example: Smart Home System (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Top-Level Parallel States: `lighting`, `climate`, `security`.
#   - Actor Model: Spawning `light_bulb` actors from the `lighting` region.
#   - Inter-Actor Communication: `security` region sends events to light actors.
#   - `invoke` and `after` running in different parallel regions.
#   - Automatic Logic Discovery of all methods, including the service that
#     provides the actor machine definition.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter

# ✅ FIX: Correctly import from the sub-directory
from smart_home_logic import SmartHomeLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print("\n--- 🏡 Async Smart Home Simulation (Class / LogicLoader) ---")

    # ✅ FIX: Correctly get the path to the JSON file inside the sub-directory
    with open("smart_home.json", "r") as f:
        config = json.load(f)

    logic_provider = SmartHomeLogic()

    machine = create_machine(config, logic_providers=[logic_provider])

    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    logging.info(f"Initial states: {interpreter.current_state_ids}")
    logging.info(f"Spawned actors: {list(interpreter._actors.keys())}")

    print("\n--- Scenario 1: Adjusting climate ---")
    await interpreter.send("SET_TEMP", temp=72)
    # This will run in the background, we don't have to wait for it.

    print("\n--- Scenario 2: Arming system and detecting motion ---")
    await interpreter.send("ARM_AWAY")
    logging.info("...waiting for arming delay...")
    await asyncio.sleep(3.5)
    logging.info(f"System is now in state: {interpreter.current_state_ids}")

    await interpreter.send("MOTION_DETECTED")
    await asyncio.sleep(1.0)
    logging.info(f"System state after motion: {interpreter.current_state_ids}")

    print("\n--- Scenario 3: Disarming the system ---")
    await interpreter.send("DISARM", code="1234")
    await asyncio.sleep(1.0)
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
