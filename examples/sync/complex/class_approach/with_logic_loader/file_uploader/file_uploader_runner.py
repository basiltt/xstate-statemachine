# examples/sync/complex/class_approach/with_logic_loader/file_uploader_runner.py
# -----------------------------------------------------------------------------
# 📂 Complex Example: File Uploader (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a file upload process with multiple steps.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Class-Based Logic: `FileUploaderLogic` class encapsulates all logic.
#   - Automatic Logic Discovery: `logic_providers` is used to bind methods.
#   - Sync Services (`invoke`): Simulates blocking upload and processing steps.
#   - Error Handling (`onError`): Catches exceptions from services.
#   - Guards: `is_file_selected` prevents actions on invalid states.
# -----------------------------------------------------------------------------
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../../..")
    ),
)
from src.xstate_statemachine import create_machine, SyncInterpreter
from examples.sync.complex.class_approach.with_logic_loader.file_uploader.file_uploader_logic import (
    FileUploaderLogic,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main():
    print("\n--- 📂 Synchronous File Uploader Simulation ---")
    with open("file_uploader.json", "r") as f:
        config = json.load(f)

    # Instantiate the logic provider
    uploader_logic = FileUploaderLogic()

    # Create the machine, passing the instance for auto-discovery
    machine = create_machine(config, logic_providers=[uploader_logic])
    interpreter = SyncInterpreter(machine)
    interpreter.start()

    # --- Scenario 1: Successful Upload ---
    print("\n--- Scenario 1: Successful Upload ---")
    interpreter.send("SELECT_FILE", file="document.pdf")
    interpreter.send("UPLOAD")
    logging.info(f"Final State: {interpreter.current_state_ids}")

    # --- Scenario 2: Upload Fails ---
    print("\n--- Scenario 2: Network Failure During Upload ---")
    interpreter.send("NEW_UPLOAD")
    interpreter.send("SELECT_FILE", file="report_fail.docx")
    interpreter.send("UPLOAD")
    logging.info(f"State after failure: {interpreter.current_state_ids}")

    # --- Scenario 3: Processing Fails ---
    print("\n--- Scenario 3: Invalid File Format During Processing ---")
    interpreter.send("CANCEL")
    interpreter.send("SELECT_FILE", file="image_invalid.jpg")
    interpreter.send("UPLOAD")
    logging.info(f"State after failure: {interpreter.current_state_ids}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
