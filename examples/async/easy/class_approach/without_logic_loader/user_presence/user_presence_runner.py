# examples/async/easy/class_approach/without_logic_loader/user_presence_runner.py
# -----------------------------------------------------------------------------
# 🟢 Easy Example: Async User Presence (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Execution with simulated delays in actions.
#   - Explicit Logic Binding of an `async` method.
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
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from user_presence_logic import UserPresenceLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- 🟢 Async User Presence Simulation (Class / Explicit Logic) ---"
    )

    with open("user_presence.json", "r") as f:
        config = json.load(f)

    logic_provider = UserPresenceLogic()
    machine_logic = MachineLogic(
        actions={"update_last_seen": logic_provider.update_last_seen}
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    logging.info("Sending CONNECT event...")
    await interpreter.send("CONNECT", user_id="user-123")
    await asyncio.sleep(0.6)  # Wait for the async action to complete
    logging.info(f"Current state: {interpreter.current_state_ids}")

    logging.info("Sending DISCONNECT event...")
    await interpreter.send("DISCONNECT")
    await asyncio.sleep(0.6)  # Wait for the async action to complete
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
