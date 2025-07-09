# examples/async/basic/functional_approach/without_logic_loader/stopwatch_runner.py
# -----------------------------------------------------------------------------
# ⏱️ Basic Example: Async Stopwatch (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Top-level transitions (`on: { "RESET": ... }`) that are available from any state.
#   - Parameterized actions for reusable logic.
#   - Explicit Logic Binding of `async` and `sync` functions.
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
from stopwatch_logic import log_status, record_lap, reset_timer

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- ⏱️  Async Stopwatch Simulation (Functional / Explicit Logic) ---"
    )

    with open("stopwatch.json", "r") as f:
        config = json.load(f)

    machine_logic = MachineLogic(
        actions={
            "log_status": log_status,
            "record_lap": record_lap,
            "reset_timer": reset_timer,
        }
    )

    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()

    await asyncio.sleep(0.2)
    await interpreter.send("START")

    await asyncio.sleep(0.2)
    await interpreter.send("LAP")

    await asyncio.sleep(0.2)
    await interpreter.send("STOP")

    await asyncio.sleep(0.2)
    await interpreter.send("RESET")

    await asyncio.sleep(0.3)
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
