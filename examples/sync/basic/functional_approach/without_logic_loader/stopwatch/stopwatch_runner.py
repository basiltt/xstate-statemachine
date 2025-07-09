# examples/sync/basic/functional_approach/without_logic_loader/stopwatch_runner.py
# -----------------------------------------------------------------------------
# ⏱️ Basic Example: Synchronous Stopwatch (Functional)
# -----------------------------------------------------------------------------
# This script simulates a basic stopwatch.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Context Management: `elapsedTime` is updated by actions.
#   - Explicit Logic Binding: A `MachineLogic` object is manually created.
#   - Functional Approach: Logic is implemented as standalone functions.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# -----------------------------------------------------------------------------
# ⚙️ Machine Logic (Actions)
# -----------------------------------------------------------------------------


def record_time_action(
    i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
) -> None:
    """Action to record the elapsed time."""
    # In a real app, this would use a more precise timer.
    ctx["elapsedTime"] = int(time.time() - ctx.get("startTime", time.time()))
    logging.info(f"⏱️ Time stopped at {ctx['elapsedTime']} seconds.")


def reset_time_action(
    i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
) -> None:
    """Action to reset the elapsed time to zero."""
    ctx["elapsedTime"] = 0
    logging.info("🔄 Timer reset.")


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------
def main():
    """Initializes and runs the stopwatch simulation."""
    print("\n--- ⏱️  Synchronous Stopwatch Simulation ---")

    # 1. Load the machine configuration from JSON.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "stopwatch.json")
    with open(json_path, "r") as f:
        config = json.load(f)

    # 2. Explicitly bind logic functions.
    logic = MachineLogic(
        actions={
            "record_time": record_time_action,
            "reset_time": reset_time_action,
        }
    )

    # 3. Create the machine and interpreter.
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)

    # 4. Run the simulation.
    interpreter.start()
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    print("\n--- Starting the stopwatch ---")
    interpreter.context["startTime"] = time.time()  # Set start time
    interpreter.send("START")
    logging.info(f"Current State: {interpreter.current_state_ids}")

    print("\n--- Waiting for 3 seconds ---")
    time.sleep(3)

    print("\n--- Stopping the stopwatch ---")
    interpreter.send("STOP")
    logging.info(f"Current State: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    print("\n--- Starting and resetting ---")
    interpreter.send("START")
    time.sleep(1)
    interpreter.send("RESET")
    logging.info(f"Current State: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
