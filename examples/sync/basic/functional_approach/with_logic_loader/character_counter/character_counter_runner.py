# examples/sync/basic/functional_approach/with_logic_loader/character_counter_runner.py
# -----------------------------------------------------------------------------
# 🔠 Character Counter Runner (Functional with LogicLoader)
# -----------------------------------------------------------------------------
"""
Main script for synchronous character counter using auto-discovered logic.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# 🛠️ Ensure project root on PYTHONPATH
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
import character_counter_logic  # noqa: E402

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
    """🚀 Execute the character counter simulation."""
    print("\n--- 🔠 Synchronous Character Counter Simulation ---")
    config_path = os.path.join(
        os.path.dirname(__file__), "character_counter.json"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[character_counter_logic])
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    time.sleep(1)  # Simulate some processing time

    print("\n--- Typing within limit ---")
    interpreter.send("TYPE", value="Hello")
    logger.info(f"Context: {interpreter.context}")

    time.sleep(2)  # Simulate some processing time

    print("\n--- Typing beyond limit (blocked) ---")
    interpreter.send("TYPE", value="Too long text here")
    logger.info(f"Context: {interpreter.context}")

    time.sleep(1)  # Simulate some processing time

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
