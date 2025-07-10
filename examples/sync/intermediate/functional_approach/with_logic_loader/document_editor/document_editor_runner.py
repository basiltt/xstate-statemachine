# examples/sync/intermediate/functional_approach/with_logic_loader/document_editor_runner.py
# -----------------------------------------------------------------------------
# 📝 Intermediate Example: Document Editor (Functional with LogicLoader)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous document editor state machine.

Key Concepts:
  • SyncInterpreter for blocking execution.
  • Auto-discovery of actions/services via logic_modules.
  • Nested states and synchronous service invocation.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# Ensure project root on PYTHONPATH
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
import document_editor_logic  # noqa: E402
from src.xstate_statemachine import create_machine, SyncInterpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Load configuration and run the document editor simulation."""
    print("\n--- 📝 Document Editor Simulation ---")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "document_editor.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[document_editor_logic])
    interpreter = SyncInterpreter(machine).start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    time.sleep(1)  # Simulate some initial processing delay

    print("\n--- Scenario 1: Successful save ---")
    interpreter.send("START_EDITING", content="Hello")
    interpreter.send("KEY_PRESS", key=" World")
    interpreter.send("SAVE")
    logger.info(f"Final State: {interpreter.current_state_ids}")
    logger.info(f"Final Context: {interpreter.context}\n")

    time.sleep(3)  # Simulate some processing time

    print("--- Scenario 2: Failed save ---")
    interpreter.send("START_EDITING", content="Hi")
    interpreter.send("SAVE")
    logger.info(f"State after failure: {interpreter.current_state_ids}")
    logger.info(f"Context: {interpreter.context}")

    time.sleep(2)  # Simulate some processing time

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
