# examples/sync/basic/functional_approach/with_logic_loader/character_counter_runner.py

# -----------------------------------------------------------------------------
# 🔠 Basic Example: Synchronous Character Counter (Functional with LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a character counter that uses guards to manage a limit.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Automatic Logic Discovery: The `create_machine` function uses `logic_modules`
#     to auto-discover and bind the necessary functions from a separate module.
#   - Functional Approach: Logic is defined as standalone functions.
#   - Guards: `is_under_limit` prevents the action from firing if the
#     new text is too long.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys

from examples.sync.basic.functional_approach.with_logic_loader.character_counter import (
    character_counter_logic,
)

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
    print("\n--- 🔠 Synchronous Character Counter Simulation ---")

    # 1. Load the machine configuration.
    with open("character_counter.json", "r") as f:
        config = json.load(f)

    # 2. Create the machine using `logic_modules` for auto-discovery.
    machine = create_machine(
        config,
        logic_modules=[character_counter_logic],
    )

    # 3. Create and run the synchronous interpreter.
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    print("\n--- Typing within the limit ---")
    interpreter.send("TYPE", value="Hello")
    logging.info(f"Context: {interpreter.context}")

    print("\n--- Attempting to type beyond the limit (should be blocked) ---")
    interpreter.send("TYPE", value="This text is definitely too long")
    logging.info("State remains unchanged because guard failed.")
    logging.info(f"Context: {interpreter.context}")

    print("\n--- Reaching the limit exactly ---")
    interpreter.send("TYPE", value="This is 15 ch.")
    logging.info(f"Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
