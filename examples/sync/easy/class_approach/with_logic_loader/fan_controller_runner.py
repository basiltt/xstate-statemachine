# examples/sync/easy/class_approach/with_logic_loader/fan_controller_runner.py
# -----------------------------------------------------------------------------
# 💨 Easy Example: Synchronous Fan Controller (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous fan controller demonstration.

Key Concepts:
  • Synchronous Execution: Uses SyncInterpreter for blocking state transitions.
  • Class-Based Logic: FanController encapsulates all actions.
  • Automatic Discovery: LogicLoader inspects the FanController instance.
"""

import sys
import json
import logging
import time
from typing import Any, Dict

from xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    Event,
    ActionDefinition,
)

# 🛡️ Windows consoles default to a legacy code page (cp1252), where the emoji
#    below raise UnicodeEncodeError and abort the example. Reconfiguring the
#    stream keeps the output readable everywhere; `errors="replace"` means a
#    terminal that still cannot render a glyph degrades instead of crashing.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class FanController:
    """Encapsulates logic and interpreter for the fan controller machine."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """🛠️ Initialize machine and SyncInterpreter.

        Args:
            config: JSON-loaded state machine configuration.
        """
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    def set_speed_low(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚙️ Action: Set fan speed to low (1)."""
        context["speed"] = 1
        logger.info(f"💨 Fan ON. Speed set to {context['speed']}.")

    def set_speed_zero(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚙️ Action: Turn the fan off (speed 0)."""
        context["speed"] = 0
        logger.info(f"🌑 Fan OFF. Speed set to {context['speed']}.")

    def run_simulation(self) -> None:
        """🚀 Execute a predefined sequence of FAN events."""
        print("\n--- 💨 Fan Controller Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")

        time.sleep(1)  # Simulate initial delay

        print("\n--- Turning fan ON ---")
        self.interpreter.send("TURN_ON")
        logger.info(f"State: {self.interpreter.current_state_ids}")
        logger.info(f"Context: {self.interpreter.context}")

        time.sleep(1)  # Simulate delay for action to complete

        print("\n--- Increasing speed ---")
        self.interpreter.send("INCREASE_SPEED")
        logger.info(f"State: {self.interpreter.current_state_ids}")
        logger.info(f"Context: {self.interpreter.context}")

        time.sleep(1)  # Simulate delay for action to complete

        print("\n--- Turning fan OFF ---")
        self.interpreter.send("TURN_OFF")
        logger.info(f"State: {self.interpreter.current_state_ids}")
        logger.info(f"Context: {self.interpreter.context}")

        time.sleep(1)  # Simulate delay for action to complete

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main() -> None:
    """🔧 Load configuration and run the fan controller simulation."""
    try:
        with open("fan_controller.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("❌ Config not found: 'fan_controller.json'")
        return

    controller = FanController(config)
    controller.run_simulation()


if __name__ == "__main__":
    main()
