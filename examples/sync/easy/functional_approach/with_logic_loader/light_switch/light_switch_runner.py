# examples/sync/easy/functional_approach/with_logic_loader/light_switch/light_switch_runner.py
# -----------------------------------------------------------------------------
# 💡 Easy Example: Synchronous Light Switch (LogicLoader)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous light switch demonstration using LogicLoader.

Key Concepts:
  • SyncInterpreter for blocking flow.
  • Auto-discovery: logic_modules points to the module path.
"""

import json
import logging
import sys
import os
import time

from xstate_statemachine import create_machine, SyncInterpreter

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


def main() -> None:
    """🚀 Load config, build machine, and run light switch simulation."""
    print("\n--- 💡 Light Switch Simulation (with LogicLoader) ---")

    base = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base, "light_switch.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    module_path = (
        "examples.sync.easy.functional_approach.with_logic_loader."
        "light_switch.light_switch_logic"
    )
    machine = create_machine(config, logic_modules=[module_path])
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    time.sleep(1)  # Simulate some initial delay

    print("\n--- Turning light ON ---")
    interpreter.send("TURN_ON")
    logger.info(f"State: {interpreter.current_state_ids}")
    logger.info(f"Context: {interpreter.context}")

    time.sleep(1)  # Simulate some delay for the action to complete

    print("\n--- Turning light OFF ---")
    interpreter.send("TURN_OFF")
    logger.info(f"State: {interpreter.current_state_ids}")
    logger.info(f"Context: {interpreter.context}")

    time.sleep(1)  # Simulate some delay for the action to complete

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
