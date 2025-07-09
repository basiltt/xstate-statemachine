# examples/async/intermediate/class_approach/with_logic_loader/api_fetcher_runner.py
# -----------------------------------------------------------------------------
# 📞 Intermediate Example: Async API Fetcher (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Services (`invoke`): Calling an `async` function that
#     simulates a network request.
#   - Passing data to a service via `context`.
#   - `onDone` and `onError` handlers for processing service results.
#   - Automatic Logic Discovery of a class instance's methods.
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
from api_fetcher_logic import ApiFetcherLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print("\n--- 📞 Async API Fetcher Simulation (Class / LogicLoader) ---")

    with open("api_fetcher.json", "r") as f:
        config = json.load(f)

    logic_provider = ApiFetcherLogic()
    machine = create_machine(config, logic_providers=[logic_provider])
    interpreter = await Interpreter(machine).start()

    # --- Scenario 1: Successful fetch ---
    print("\n--- Scenario 1: Successful Fetch ---")
    await interpreter.send("FETCH", id="user123")
    await asyncio.sleep(2)  # Wait for invoke to complete
    logging.info(f"Current state: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    # --- Scenario 2: Failed fetch ---
    print("\n--- Scenario 2: Failed Fetch ---")
    await interpreter.send("FETCH", id="user999")
    await asyncio.sleep(2)  # Wait for invoke to complete
    logging.info(f"Current state: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
