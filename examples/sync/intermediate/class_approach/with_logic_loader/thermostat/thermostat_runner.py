# examples/sync/intermediate/class_approach/with_logic_loader/thermostat_runner.py
# -----------------------------------------------------------------------------
# 🌡️ Intermediate Example: Thermostat (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous thermostat state machine.

Key Concepts:
  • SyncInterpreter for blocking execution.
  • Class-based logic auto-discovered via logic_providers.
  • Guards determine heating/cooling behavior.
"""

import json
import logging
import os
import time
from typing import Any, Dict

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    Event,
    ActionDefinition,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class Thermostat:
    """Encapsulates logic and interpreter for a thermostat state machine."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the Thermostat with its machine configuration.

        Args:
            config: The JSON-loaded state machine configuration.
        """
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    def set_target_temperature(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🌡️ Action: Set the desired target temperature in context.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable context dictionary.
            event: Event carrying payload {'temperature': int}.
            action_def: Metadata for this action.
        """
        target = event.payload.get("temperature")
        context["target_temp"] = target
        logger.info(f"🌡️ New target temperature set to {target}°F.")

    def start_heating(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔥 Action: Log that heating has started."""
        logger.info("🔥 Heating started...")

    def start_cooling(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❄️ Action: Log that cooling has started."""
        logger.info("❄️ Cooling started...")

    def update_current_temp(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🌡️ Action: Update current temperature in context.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable context dictionary.
            event: Event carrying payload {'temperature': int}.
            action_def: Metadata for this action.
        """
        current = event.payload.get("temperature")
        context["current_temp"] = current
        logger.info(f"🌡️ Current temperature is now {current}°F.")

    def is_below_target(  # noqa
        self,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> bool:
        """🛡️ Guard: Check if the current temp is below target.

        Args:
            context: Mutable context dictionary.
            event: The triggering Event.

        Returns:
            True if current_temp < target_temp, False otherwise.
        """
        return context.get("current_temp", 0) < context.get("target_temp", 0)

    def is_above_target(  # noqa
        self,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> bool:
        """🛡️ Guard: Check if the current temp is above target.

        Args:
            context: Mutable context dictionary.
            event: The triggering Event.

        Returns:
            True if current_temp > target_temp, False otherwise.
        """
        return context.get("current_temp", 0) > context.get("target_temp", 0)

    def is_at_target(  # noqa
        self,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> bool:
        """🛡️ Guard: Check if current temp matches target.

        Args:
            context: Mutable context dictionary.
            event: The triggering Event.

        Returns:
            True if current_temp == target_temp, False otherwise.
        """
        return context.get("current_temp") == context.get("target_temp")

    def run_simulation(self) -> None:
        """🚀 Execute a predefined thermostat simulation."""
        print("\n--- 🌡️ Thermostat Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")
        logger.info(f"Initial Context: {self.interpreter.context}")

        time.sleep(1)

        print("\n--- Scenario 1: Raise target temperature ---")
        self.interpreter.send("SET_TARGET", temperature=75)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)

        self.interpreter.send("TEMPERATURE_RISE", temperature=72)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(1)

        self.interpreter.send("TEMPERATURE_RISE", temperature=75)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)

        print("\n--- Scenario 2: Lower target temperature ---")
        self.interpreter.send("SET_TARGET", temperature=68)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(1)

        self.interpreter.send("TEMPERATURE_DROP", temperature=70)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)

        self.interpreter.send("TEMPERATURE_DROP", temperature=68)
        self.interpreter.send("CHECK_TEMP")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main() -> None:
    """Load configuration and run the thermostat simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "thermostat.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Config not found: '{config_path}'")
        return

    thermostat = Thermostat(config)
    thermostat.run_simulation()


if __name__ == "__main__":
    main()
