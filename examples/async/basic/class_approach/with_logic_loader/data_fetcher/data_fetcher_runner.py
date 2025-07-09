# examples/async/basic/class_approach/with_logic_loader/data_fetcher_runner.py
# -----------------------------------------------------------------------------
# 📡 Basic Example: Async Data Fetcher (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Actions with simulated I/O.
#   - Guards (`has_retries_left`) controlling flow.
#   - Delayed Transitions (`after`) for implementing a retry delay.
#   - Automatic Logic Discovery (`logic_providers`).
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

from data_fetcher_logic import DataFetcherLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# A temporary patch to the JSON to add the transitions that were missing.
# In a real scenario, you'd edit the JSON file directly.
def patch_config(config):
    config["states"]["fetching"]["on"] = {
        "FETCH_SUCCESS": "success",
        "FETCH_FAILURE": {
            "target": "waiting_to_retry",
            "guard": "has_retries_left",
            "else": "failed",
        },
    }
    return config


async def main():
    print("\n--- 📡 Async Data Fetcher Simulation (Class / LogicLoader) ---")

    with open("data_fetcher.json", "r") as f:
        config = json.load(f)

    # Apply the patch to the configuration
    patched_config = patch_config(config)

    logic_provider = DataFetcherLogic()
    machine = create_machine(patched_config, logic_providers=[logic_provider])

    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    logging.info(
        "\n--- Triggering fetch, will run until success or failure ---"
    )
    await interpreter.send("FETCH")

    # Keep the script alive to observe the `after` transition
    try:
        # Wait long enough for multiple retries
        await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    finally:
        logging.info(f"Final state: {interpreter.current_state_ids}")
        logging.info(f"Final context: {interpreter.context}")
        await interpreter.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
