# examples/sync/easy/class_approach/without_logic_loader/toggle_switch/toggle_switch_runner.py

# -----------------------------------------------------------------------------
# 💡 Easy Example: Synchronous Toggle Switch (Class-Based)
# -----------------------------------------------------------------------------
# This script demonstrates a simple class-based approach with the SyncInterpreter.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter` for a blocking workflow.
#   - Class-Based Logic: The `ToggleSwitch` class encapsulates the interpreter
#     and its logic.
#   - Explicit Logic Binding: A `MachineLogic` object is manually created,
#     mapping logic names from the JSON config to the class's instance methods.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
from typing import Dict, Any

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
# 🏛️ ToggleSwitch Class
# -----------------------------------------------------------------------------
class ToggleSwitch:
    """Encapsulates the logic and interpreter for a simple toggle switch."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the ToggleSwitch."""
        # 1. Manually create the MachineLogic object, binding action names
        #    to the methods of this class instance.
        machine_logic = MachineLogic(
            actions={"increment_toggles": self.increment_toggles_action}
        )

        # 2. Create the machine node and the synchronous interpreter.
        machine = create_machine(config, logic=machine_logic)
        self.interpreter = SyncInterpreter(machine)

    def increment_toggles_action(
        self, i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ) -> None:
        """Action to increment the toggle count in the context."""
        ctx["toggleCount"] += 1
        logging.info(f"🔄 Toggle count is now: {ctx['toggleCount']}")

    def run_simulation(self):
        """Runs a predefined simulation of using the toggle switch."""
        print("\n--- 💡 Synchronous Toggle Switch Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial state: {self.interpreter.current_state_ids}")

        print("\n--- Toggling ON ---")
        self.interpreter.send("TOGGLE")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")

        print("\n--- Toggling OFF ---")
        self.interpreter.send("TOGGLE")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")

        print("\n--- Toggling ON again ---")
        self.interpreter.send("TOGGLE")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")

        logging.info(f"Final Context: {self.interpreter.context}")
        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


# -----------------------------------------------------------------------------
# 🚀 Main Execution
# -----------------------------------------------------------------------------
def main():
    """Loads config and runs the toggle switch simulation."""
    try:
        with open("toggle_switch.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(
            "❌ Configuration file not found at 'toggle_switch.json'."
        )
        return

    toggle_switch = ToggleSwitch(config)
    toggle_switch.run_simulation()


if __name__ == "__main__":
    main()
