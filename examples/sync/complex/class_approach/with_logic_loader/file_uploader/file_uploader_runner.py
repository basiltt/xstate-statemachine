# -----------------------------------------------------------------------------
# 📂 File Uploader Runner
# examples/sync/complex/class_approach/with_logic_loader/file_uploader/file_uploader_runner.py
# -----------------------------------------------------------------------------
"""
Simulates the synchronous file upload workflow:

  • SELECT_FILE → UPLOAD (invoke upload_file_sync)
  • onDone → process_file_sync
  • onDone → log_complete
  • onError transitions on failure
  • Guards prevent invalid actions
"""

import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, SyncInterpreter

# Ensure project root on path
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../../..")
    ),
)
from examples.sync.complex.class_approach.with_logic_loader.file_uploader.file_uploader_logic import (  # noqa: E501
    FileUploaderLogic,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """🚀 Execute File Uploader scenarios."""
    print("\n--- 📂 Synchronous File Uploader Simulation ---")
    config_path = "file_uploader.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = FileUploaderLogic()
    machine = create_machine(config, logic_providers=[logic])
    interpreter = SyncInterpreter(machine)
    interpreter.start()

    # Scenario 1: Successful upload
    print("\n--- Scenario 1: Successful Upload ---")
    interpreter.send("SELECT_FILE", file="document.pdf")
    interpreter.send("UPLOAD")
    logger.info(f"Final State: {interpreter.current_state_ids}")

    # Scenario 2: Upload failure
    print("\n--- Scenario 2: Network Failure During Upload ---")
    interpreter.send("NEW_UPLOAD")
    interpreter.send("SELECT_FILE", file="report_fail.docx")
    interpreter.send("UPLOAD")
    logger.info(f"State after failure: {interpreter.current_state_ids}")

    # Scenario 3: Processing failure
    print("\n--- Scenario 3: Invalid File Format During Processing ---")
    interpreter.send("CANCEL")
    interpreter.send("SELECT_FILE", file="image_invalid.jpg")
    interpreter.send("UPLOAD")
    logger.info(f"State after failure: {interpreter.current_state_ids}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
