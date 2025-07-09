# examples/sync/intermediate/functional_approach/with_logic_loader/document_editor_runner.py

# -----------------------------------------------------------------------------
# 📝 Intermediate Example: Document Editor (Functional with LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a simple document editor with nested states.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Automatic Logic Discovery: `logic_modules` is used to discover all
#     the standalone functions in `document_editor_logic.py`.
#   - Functional Approach: Logic is defined as standalone functions.
#   - Nested States: Models `typing` and `formatting` within an `editing` state.
#   - Sync Service with Error Handling: The `invoke` of `save_document` can
#     succeed (`onDone`) or fail (`onError`).
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys

from examples.sync.intermediate.functional_approach.with_logic_loader.document_editor import (
    document_editor_logic,
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
    """Loads config and runs the document editor simulation."""
    print("\n--- 📝 Synchronous Document Editor Simulation ---")

    # 1. Load the machine configuration from JSON.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "document_editor.json")
    with open(json_path, "r") as f:
        config = json.load(f)

    # 2. Create the machine using `logic_modules` for auto-discovery.
    machine = create_machine(
        config,
        logic_modules=[document_editor_logic],
    )

    # 3. Create and start the synchronous interpreter.
    interpreter = SyncInterpreter(machine).start()
    logging.info(f"Initial State: {interpreter.current_state_ids}")

    # --- Scenario 1: Successful edit and save ---
    print("\n--- Scenario 1: Successful Save ---")
    interpreter.send("START_EDITING", content="Hello")
    interpreter.send("KEY_PRESS", key=" World")
    interpreter.send("SAVE")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}\n")

    # --- Scenario 2: Edit and fail to save (content too short) ---
    print("--- Scenario 2: Failed Save ---")
    interpreter.send("START_EDITING", content="Hi")
    interpreter.send("SAVE")  # Will fail because len < 5
    logging.info(f"State after failed save: {interpreter.current_state_ids}")
    logging.info(f"Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
