# -------------------------------------------------------------------------------
# ⚙️ Async Task Status Runner
# examples/async/easy/functional_approach/with_logic_loader/task_status/task_status_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async task status simulation using LogicLoader.

Demonstrates:
  • Async def actions auto-discovered.
  • START and FINISH events modifying context.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

# --- Ensure project root on PYTHONPATH ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)

from src.xstate_statemachine import create_machine, Interpreter
import task_status_logic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the task status state machine."""
    logger.info("\n--- ⚙️ Async Task Status Simulation ---")

    config_path = os.path.join(os.path.dirname(__file__), "task_status.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[task_status_logic])
    interpreter = await Interpreter(machine).start()
    logger.info(f"Initial state: {interpreter.current_state_ids}")

    logger.info("➡️ Sending START event...")
    await interpreter.send("START", id="job-456")
    await asyncio.sleep(0.8)
    logger.info(f"State after START: {interpreter.current_state_ids}")

    logger.info("➡️ Sending FINISH event...")
    await interpreter.send("FINISH")
    await asyncio.sleep(0.4)
    logger.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
