# examples/sync/easy/class_approach/without_logic_loader/toggle_switch_runner.py
# -----------------------------------------------------------------------------
# 💡 Easy Example: Synchronous Toggle Switch (Explicit Logic Binding)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous toggle switch demonstration.

Key Concepts:
  • Synchronous Execution: Uses SyncInterpreter.
  • Explicit Logic: MachineLogic maps names to ToggleSwitch methods.
"""

import sys
import json
import logging
import time
from typing import Any, Dict

from xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
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


class ToggleSwitch:
    """Encapsulates logic and interpreter for a simple toggle switch."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """🛠️ Initialize machine with explicit MachineLogic and SyncInterpreter."""
        logic = MachineLogic(
            actions={"increment_toggles": self.increment_toggles}
        )
        machine = create_machine(config, logic=logic)
        self.interpreter = SyncInterpreter(machine)

    def increment_toggles(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚙️ Action: Increment toggle count in context."""
        context["toggleCount"] = context.get("toggleCount", 0) + 1
        logger.info(f"🔄 Toggle count is now {context['toggleCount']}.")

    def run_simulation(self) -> None:
        """🚀 Execute a predefined sequence of TOGGLE events."""
        print("\n--- 💡 Toggle Switch Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")

        time.sleep(1)  # Initial delay before first toggle

        for _ in range(3):
            print("\n--- Toggling ---")
            self.interpreter.send("TOGGLE")
            logger.info(f"State: {self.interpreter.current_state_ids}")
            logger.info(f"Context: {self.interpreter.context}")

            time.sleep(2)  # Simulate a delay for each toggle action

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main() -> None:
    """🔧 Load config and run toggle switch simulation."""
    try:
        with open("toggle_switch.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("❌ Config not found: 'toggle_switch.json'")
        return

    switch = ToggleSwitch(config)
    switch.run_simulation()


if __name__ == "__main__":
    main()
