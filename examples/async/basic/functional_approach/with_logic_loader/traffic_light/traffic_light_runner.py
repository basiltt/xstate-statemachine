# examples/async/basic/functional_approach/with_logic_loader/traffic_light_runner.py
# -----------------------------------------------------------------------------
# 🚦 Basic Example: Async Traffic Light (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Delayed Transitions (`after`) for normal light cycles.
#   - Guards to check conditions before an event-based transition.
#   - Parameterized Actions: `log_light_change` receives its color from the
#     machine definition, making it reusable.
#   - Automatic Logic Discovery of `async def` and `def` functions.
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

import traffic_light_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


async def main():
    print(
        "\n--- 🚦 Async Traffic Light Simulation (Functional / LogicLoader) ---"
    )

    with open("traffic_light.json", "r") as f:
        config = json.load(f)

    machine = create_machine(config, logic_modules=[traffic_light_logic])
    interpreter = await Interpreter(machine).start()

    logging.info("--- Normal cycle running... ---")
    await asyncio.sleep(5.5)  # Let it transition from green to yellow

    logging.info(
        "\n--- Pedestrian button pressed, interrupting the yellow->red cycle ---"
    )
    await interpreter.send(
        "PEDESTRIAN_WAITING"
    )  # This will be ignored as the light is not green
    await asyncio.sleep(2.5)  # Let it transition from yellow to red

    logging.info(
        "\n--- Pedestrian button pressed while light is red (ignored) ---"
    )
    await interpreter.send("PEDESTRIAN_WAITING")  # Ignored
    await asyncio.sleep(5.5)  # Let it transition from red to green

    logging.info(
        "\n--- Pedestrian button pressed while light is green (will interrupt) ---"
    )
    await interpreter.send(
        "PEDESTRIAN_WAITING"
    )  # This should trigger the transition to yellow early

    await asyncio.sleep(8)  # Observe the rest of the interrupted cycle

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
