# examples/sync/intermediate/class_approach/with_logic_loader/thermostat_runner.py

# -----------------------------------------------------------------------------
# 🌡️ Intermediate Example: Thermostat (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a simple thermostat.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Class-Based Logic: The `Thermostat` class encapsulates all logic.
#   - Automatic Logic Discovery: An instance of the `Thermostat` class is
#     passed to `create_machine` via `logic_providers`. The `LogicLoader`
#     inspects this object and automatically binds its methods.
#   - Guards: Multiple guards (`is_below_target`, `is_above_target`) are
#     used to make decisions based on the context.
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
    Event,
    ActionDefinition,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# 🏛️ Thermostat Class
# -----------------------------------------------------------------------------
class Thermostat:
    """Encapsulates the logic and interpreter for a thermostat."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the Thermostat."""
        # 1. Create the machine, passing `self` to `logic_providers` for auto-discovery.
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    # --- Actions ---
    def set_target_temperature(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["target_temp"] = e.payload.get("temperature")
        logging.info(
            f"🌡️  New target temperature set to: {ctx['target_temp']}°F"
        )

    def start_heating(self, i, ctx, e, a):
        logging.info("🔥 Heating started...")

    def start_cooling(self, i, ctx, e, a):
        logging.info("❄️  Cooling started...")

    def update_current_temp(self, i, ctx, e, a):
        ctx["current_temp"] = e.payload.get("temperature")
        logging.info(f"🌡️  Current temperature is now: {ctx['current_temp']}°F")

    # --- Guards ---
    def is_below_target(self, ctx: Dict, e: Event) -> bool:
        return ctx["current_temp"] < ctx["target_temp"]

    def is_above_target(self, ctx: Dict, e: Event) -> bool:
        return ctx["current_temp"] > ctx["target_temp"]

    def is_at_target(self, ctx: Dict, e: Event) -> bool:
        return ctx["current_temp"] == ctx["target_temp"]

    def run_simulation(self):
        """Runs a predefined simulation of the thermostat."""
        print("\n--- 🌡️  Synchronous Thermostat Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")
        logging.info(f"Initial Context: {self.interpreter.context}")

        print("\n--- Scenario 1: Setting a higher temperature ---")
        self.interpreter.send("SET_TARGET", temperature=75)
        self.interpreter.send("CHECK_TEMP")  # Enters 'heating'
        logging.info(f"State: {self.interpreter.current_state_ids}")

        self.interpreter.send("TEMPERATURE_RISE", temperature=72)
        self.interpreter.send("CHECK_TEMP")  # Still heating
        logging.info(f"State: {self.interpreter.current_state_ids}")

        self.interpreter.send("TEMPERATURE_RISE", temperature=75)
        self.interpreter.send("CHECK_TEMP")  # Reaches target, becomes idle
        logging.info(f"State: {self.interpreter.current_state_ids}")

        print("\n--- Scenario 2: Setting a lower temperature ---")
        self.interpreter.send("SET_TARGET", temperature=68)
        self.interpreter.send("CHECK_TEMP")  # Enters 'cooling'
        logging.info(f"State: {self.interpreter.current_state_ids}")

        self.interpreter.send("TEMPERATURE_DROP", temperature=70)
        self.interpreter.send("CHECK_TEMP")  # Still cooling
        logging.info(f"State: {self.interpreter.current_state_ids}")

        self.interpreter.send("TEMPERATURE_DROP", temperature=68)
        self.interpreter.send("CHECK_TEMP")  # Reaches target, becomes idle
        logging.info(f"State: {self.interpreter.current_state_ids}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


# -----------------------------------------------------------------------------
# 🚀 Main Execution
# -----------------------------------------------------------------------------
def main():
    """Loads config and runs the thermostat simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "thermostat.json")
    try:
        with open(json_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"❌ Configuration file not found at '{json_path}'")
        return

    thermostat = Thermostat(config)
    thermostat.run_simulation()


if __name__ == "__main__":
    main()
