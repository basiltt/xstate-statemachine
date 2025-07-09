# examples/async/easy/class_approach/with_logic_loader/light_switch_runner.py
# -----------------------------------------------------------------------------
# 💡 Easy Example: Async Light Switch (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Execution: Uses the `Interpreter` class.
#   - snake_case Naming: Action name `increment_flips` matches Python style.
#   - Automatic Logic Discovery: `logic_providers` is used to bind methods.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

from light_switch_logic import LightSwitchLogic

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter


# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print("\n--- 💡 Async Light Switch Simulation (Class / LogicLoader) ---")

    with open("light_switch.json", "r") as f:
        config = json.load(f)

    logic_provider = LightSwitchLogic()
    machine = create_machine(config, logic_providers=[logic_provider])

    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    await interpreter.send("TOGGLE")
    await asyncio.sleep(0.01)
    logging.info(f"State after TOGGLE: {interpreter.current_state_ids}")

    await interpreter.send("TOGGLE")
    await asyncio.sleep(0.01)
    logging.info(f"State after second TOGGLE: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
