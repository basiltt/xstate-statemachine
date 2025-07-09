# examples/async/complex/class_approach/with_logic_loader/two_factor_auth_runner.py
# -----------------------------------------------------------------------------
# 🔐 Complex Example: Async 2FA System (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Parallel States for concurrent activities (code delivery, code entry).
#   - `invoke` for an async service in one parallel region.
#   - `after` for a timeout in the other parallel region.
#   - Communication between parallel states via events.
#   - Guards for validating user input.
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
from two_factor_auth_logic import TwoFactorAuthLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print("\n--- 🔐 Async 2FA Simulation (Class / LogicLoader) ---")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(
        current_dir, "two_factor_auth", "two_factor_auth.json"
    )
    with open(json_path, "r") as f:
        config = json.load(f)

    logic_provider = TwoFactorAuthLogic()
    machine = create_machine(config, logic_providers=[logic_provider])

    # --- Scenario 1: Successful Authentication ---
    print("\n--- Scenario 1: Successful Authentication ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("START_2FA")
    await asyncio.sleep(2.5)  # Wait for code delivery

    # Get the code from the context of the *currently running* interpreter
    correct_code = interpreter1.context.get("generated_code")
    logging.info(
        f"Runner: Retrieved generated code '{correct_code}' to submit."
    )

    await interpreter1.send("SUBMIT_CODE", code=correct_code)
    await asyncio.sleep(1.0)  # Wait for validation

    logging.info(
        f"Final state for Scenario 1: {interpreter1.current_state_ids}"
    )
    await interpreter1.stop()

    # --- Scenario 2: Incorrect Code, then Correct ---
    print("\n--- Scenario 2: Incorrect Code, then Correct ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("START_2FA")
    await asyncio.sleep(2.5)  # Wait for code delivery

    correct_code_2 = interpreter2.context.get("generated_code")
    logging.info(
        f"Runner: Retrieved generated code '{correct_code_2}'. Submitting wrong code first."
    )

    await interpreter2.send("SUBMIT_CODE", code="000000")  # Submit wrong code
    await asyncio.sleep(0.5)
    logging.info(f"State after wrong code: {interpreter2.current_state_ids}")

    logging.info("Runner: Submitting correct code now.")
    await interpreter2.send(
        "SUBMIT_CODE", code=correct_code_2
    )  # Submit correct code
    await asyncio.sleep(1.0)

    logging.info(
        f"Final state for Scenario 2: {interpreter2.current_state_ids}"
    )
    await interpreter2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
