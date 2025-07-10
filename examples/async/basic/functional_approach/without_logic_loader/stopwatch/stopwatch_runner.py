# -------------------------------------------------------------------------------
# ⏱️ Async Stopwatch Runner
# examples/async/basic/functional_approach/without_logic_loader/stopwatch_runner.py
# -------------------------------------------------------------------------------
"""
Runs the async stopwatch state machine with explicit logic binding.
"""

import asyncio
import json
import logging
import os
import sys

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

# --- Ensure project root is on PYTHONPATH ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from stopwatch_logic import log_status, record_lap, reset_timer  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Run async stopwatch simulation."""
    logger.info("⏱️ Starting Stopwatch simulation...")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "stopwatch.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    machine_logic = MachineLogic(
        actions={
            "log_status": log_status,
            "record_lap": record_lap,
            "reset_timer": reset_timer,
        }
    )
    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()
    await asyncio.sleep(0.2)

    logger.info("▶️ Sending START event...")
    await interpreter.send("START")
    await asyncio.sleep(2)

    logger.info("🏁 Sending LAP event...")
    await interpreter.send("LAP")
    await asyncio.sleep(2)

    logger.info("⏹️ Sending STOP event...")
    await interpreter.send("STOP")
    await asyncio.sleep(2)

    logger.info("🔄 Sending RESET event...")
    await interpreter.send("RESET")
    await asyncio.sleep(3)

    logger.info(f"✅ Final state: {interpreter.current_state_ids}")
    await interpreter.stop()
    logger.info("🏁 Simulation complete.")


if __name__ == "__main__":
    asyncio.run(main())
