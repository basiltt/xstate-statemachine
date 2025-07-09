# examples/sync/easy/class_approach/with_logic_loader/fan_controller_runner.py

# -----------------------------------------------------------------------------
# 💨 Easy Example: Synchronous Fan Controller (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
# This script showcases the powerful combination of a class-based approach
# with the automatic discovery feature of the `LogicLoader`.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Class-Based Logic: The `FanController` class encapsulates the logic.
#   - Logic Provider: An *instance* of the `FanController` class is passed to
#     `create_machine` via the `logic_providers` argument, allowing the
#     `LogicLoader` to discover and bind its methods automatically.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
from typing import Dict, Any

# --- Path Setup ---
# sys.path.insert(
#     0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
# )
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    Event,
    ActionDefinition,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# 🏛️ FanController Class
# -----------------------------------------------------------------------------
class FanController:
    """Encapsulates the logic and state for a fan controller simulation."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the FanController."""
        # 1. Create the machine. Instead of building a `MachineLogic` object
        #    manually, we pass `self` (the instance of this class) into the
        #    `logic_providers` list. The LogicLoader will inspect this instance
        #    and bind its methods to the action names in the config.
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    # --- Actions ---
    def set_speed_low(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to set the fan speed to low."""
        ctx["speed"] = 1
        logging.info(f"💨 Fan ON. Speed set to {ctx['speed']}.")

    def set_speed_zero(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to turn the fan off by setting speed to zero."""
        ctx["speed"] = 0
        logging.info(f"🌑 Fan OFF. Speed set to {ctx['speed']}.")

    def run_simulation(self):
        """Runs a predefined simulation of using the fan controller."""
        print("\n--- 💨 Synchronous Fan Controller Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")

        print("\n--- Turning fan ON ---")
        self.interpreter.send("TURN_ON")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}")

        print("\n--- Increasing speed ---")
        self.interpreter.send("INCREASE_SPEED")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}")

        print("\n--- Increasing speed again ---")
        self.interpreter.send("INCREASE_SPEED")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}")

        print("\n--- Turning fan OFF ---")
        self.interpreter.send("TURN_OFF")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


# -----------------------------------------------------------------------------
# 🚀 Main Execution
# -----------------------------------------------------------------------------
def main():
    """Loads config and runs the fan controller simulation."""
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # json_path = os.path.join(current_dir, "fan_controller.json")
    try:
        with open("fan_controller.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(
            "❌ Configuration file not found at 'fan_controller.json'."
        )
        return

    fan_controller = FanController(config)
    fan_controller.run_simulation()


if __name__ == "__main__":
    main()
