# examples/async/basic/class_approach/without_logic_loader/session_timeout_runner.py
# -----------------------------------------------------------------------------
# ⌛ Basic Example: Async Session Timeout (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Delayed Transitions (`after`) to create a timeout.
#   - External self-transition (`"internal": false`) to reset the timer by
#     exiting and re-entering the `logged_in` state.
#   - Explicit Logic Binding.
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
from session_timeout_logic import SessionTimeoutLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- ⌛ Async Session Timeout Simulation (Class / Explicit Logic) ---"
    )

    with open("session_timeout.json", "r") as f:
        config = json.load(f)

    logic_provider = SessionTimeoutLogic()
    machine_logic = MachineLogic(
        actions={
            "set_user": logic_provider.set_user,
            "log_login": logic_provider.log_login,
            "log_timeout": logic_provider.log_timeout,
        }
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    await interpreter.send("LOGIN", user="Basil")
    await asyncio.sleep(0.3)
    logging.info(f"Current state: {interpreter.current_state_ids}")

    logging.info(
        "\n--- Waiting for 2 seconds, then sending activity to reset timer ---"
    )
    await asyncio.sleep(2)
    await interpreter.send("USER_ACTIVITY")
    await asyncio.sleep(0.1)
    logging.info("Timer reset. Waiting for another 3 seconds for timeout...")

    await asyncio.sleep(3.5)
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
