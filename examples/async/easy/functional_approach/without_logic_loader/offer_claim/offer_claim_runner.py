# examples/async/easy/functional_approach/without_logic_loader/offer_claim_runner.py
# -----------------------------------------------------------------------------
# 🎉 Easy Example: Async One-Time Offer (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Execution with a simulated delay.
#   - Explicit Logic Binding of a standalone `async` function.
#   - Use of a "final" state.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

from offer_claim_logic import set_claimant

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic


# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- 🎉 Async One-Time Offer Simulation (Functional / Explicit Logic) ---"
    )

    with open("offer_claim.json", "r") as f:
        config = json.load(f)

    machine_logic = MachineLogic(actions={"set_claimant": set_claimant})

    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    logging.info("Sending CLAIM event...")
    await interpreter.send("CLAIM", user="basil")
    await asyncio.sleep(1.1)  # Wait for the long async action to complete
    logging.info(f"State after claim: {interpreter.current_state_ids}")

    logging.info("Attempting to claim again (should be ignored)...")
    await interpreter.send("CLAIM", user="another_user")
    await asyncio.sleep(0.1)  # Give it time to process (it won't do anything)
    logging.info(f"Final state is unchanged: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
