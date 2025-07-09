# examples/sync/easy/functional_approach/with_logic_loader/light_switch/light_switch_runner.py

# -----------------------------------------------------------------------------
# 💡 Easy Example: Synchronous Light Switch (with LogicLoader)
# -----------------------------------------------------------------------------
# This script demonstrates using the `LogicLoader` with the `SyncInterpreter`.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Automatic Logic Discovery: The `create_machine` function is given a
#     string path to the `logic_modules`, and it automatically discovers and
#     binds the necessary functions.
#   - Functional Approach: The logic is defined in standalone functions in a
#     separate module (`light_switch_logic.py`).
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, SyncInterpreter

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------
def main():
    """Loads config, creates the machine with auto-discovered logic, and runs."""
    print(
        "\n--- 💡 Synchronous Light Switch Simulation (with LogicLoader) ---"
    )

    # 1. Load the machine configuration from a JSON file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "light_switch.json")
    with open(json_path, "r") as f:
        config = json.load(f)

    # 2. Create the machine instance. Instead of providing a `MachineLogic` object,
    #    we provide the path to the module where the functions are defined.
    #    The LogicLoader will automatically find and bind them.
    machine = create_machine(
        config,
        logic_modules=[
            "examples.sync.easy.functional_approach.with_logic_loader.light_switch.light_switch_logic"
        ],
    )

    # 3. Create and run the synchronous interpreter.
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    print("\n--- Turning the light ON ---")
    interpreter.send("TURN_ON")
    logging.info(f"Current State: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    print("\n--- Turning the light OFF ---")
    interpreter.send("TURN_OFF")
    logging.info(f"Current State: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
