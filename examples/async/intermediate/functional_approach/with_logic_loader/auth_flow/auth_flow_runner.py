# examples/async/intermediate/functional_approach/with_logic_loader/auth_flow_runner.py
# -----------------------------------------------------------------------------
# 🔐 Intermediate Example: Async Auth Flow (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Services (`invoke`) for authentication.
#   - `onDone`/`onError` to handle login success and failure.
#   - Passing credentials via event payload to the service.
#   - Automatic Logic Discovery of standalone `async` and `sync` functions.
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
import auth_flow_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print("\n--- 🔐 Async Auth Flow Simulation (Functional / LogicLoader) ---")

    with open("auth_flow.json", "r") as f:
        config = json.load(f)

    machine = create_machine(config, logic_modules=[auth_flow_logic])
    interpreter = await Interpreter(machine).start()

    # --- Scenario 1: Failed Login ---
    print("\n--- Scenario 1: Failed Login ---")
    await interpreter.send(
        "LOGIN", username="admin", password="wrong_password"
    )
    await asyncio.sleep(1.5)
    logging.info(f"Current state: {interpreter.current_state_ids}")

    # --- Scenario 2: Successful Login ---
    print("\n--- Scenario 2: Successful Login ---")
    await interpreter.send("LOGIN", username="admin", password="password123")
    await asyncio.sleep(1.5)
    logging.info(f"Current state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
