# examples/sync_document_editor.py

# -----------------------------------------------------------------------------
# 📝 Moderate Example: Class-Based Document Editor
# -----------------------------------------------------------------------------
# This script demonstrates a more structured, class-based approach.
#
# Key Concepts Illustrated:
#   - Class-Based Logic: The `DocumentEditor` class encapsulates the interpreter.
#   - Logic Auto-Discovery: Uses `logic_modules` to bind methods automatically.
#   - External JSON Config: Reads the machine definition from a file.
#   - Nested States: Models a sub-state for "formatting".
#   - Sync Service: Shows `invoke` with a synchronous, failable service.
# -----------------------------------------------------------------------------

import json
import logging
import os
from typing import Dict, Any

import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.xstate_statemachine import create_machine, SyncInterpreter

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class DocumentEditor:
    """Encapsulates the logic and state for a document editor simulation."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the DocumentEditor."""
        # 🏭 Create machine using auto-discovery from a specified logic module.
        machine = create_machine(
            config,
            logic_modules=[
                "examples.sync.document_editor.document_editor_logic"
            ],  # here the logic module is specified as a string you can also import the module directly and pass it as a list
        )
        self.interpreter = SyncInterpreter(machine)

    def run(self):
        """Runs a predefined simulation of using the editor."""
        print("\n--- 📝 Synchronous Document Editor Simulation ---")
        self.interpreter.start()

        self.interpreter.send("START_EDITING", content="Hello")
        self.interpreter.send("KEY_PRESS", key=" ")
        self.interpreter.send("KEY_PRESS", key="W")
        self.interpreter.send("KEY_PRESS", key="o")

        logging.info("\n--- Toggling Format Mode ---")
        self.interpreter.send("TOGGLE_FORMAT_MODE")
        self.interpreter.send("TOGGLE_BOLD")
        self.interpreter.send("TOGGLE_FORMAT_MODE")

        self.interpreter.send("KEY_PRESS", key="r")
        self.interpreter.send("KEY_PRESS", key="l")
        self.interpreter.send("KEY_PRESS", key="d")

        logging.info("\n--- Saving the document ---")
        self.interpreter.send("SAVE")

        logging.info(f"Final Context: {self.interpreter.context}")
        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main():
    """Loads config and runs the editor simulation."""
    try:
        with open("document_editor.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error("❌ document_editor.json not found.")
        return

    editor = DocumentEditor(config)
    editor.run()


if __name__ == "__main__":
    main()
