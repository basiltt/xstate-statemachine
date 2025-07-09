# examples/async/easy/functional_approach/with_logic_loader/task_status_runner.py
# -----------------------------------------------------------------------------
# ⚙️ Easy Example: Async Task Status (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Execution with simulated delays in async actions.
#   - Automatic Logic Discovery of `async def` functions.
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
import task_status_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- ⚙️ Async Task Status Simulation (Functional / LogicLoader) ---"
    )

    with open("task_status.json", "r") as f:
        config = json.load(f)

    machine = create_machine(config, logic_modules=[task_status_logic])

    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    logging.info("Sending START event...")
    await interpreter.send("START", id="data-processing-job-456")
    await asyncio.sleep(0.8)  # Wait for async action
    logging.info(f"Current state: {interpreter.current_state_ids}")

    logging.info("Sending FINISH event...")
    await interpreter.send("FINISH")
    await asyncio.sleep(0.4)  # Wait for async action
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
