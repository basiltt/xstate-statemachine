# -------------------------------------------------------------------------------
# 🚦 Async Traffic Light Runner
# examples/async/basic/functional_approach/with_logic_loader/traffic_light_runner.py
# -------------------------------------------------------------------------------
"""
Runs the traffic light state machine simulation with functional logic loader.
"""

import asyncio
import json
import logging
import os
import sys

from src.xstate_statemachine import Interpreter, create_machine

# --- Ensure project root is on PYTHONPATH ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
import traffic_light_logic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Run async traffic light simulation."""
    logger.info("🚦 Starting Traffic Light simulation...")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "traffic_light.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    machine = create_machine(config, logic_modules=[traffic_light_logic])
    interpreter = await Interpreter(machine).start()

    logger.info("--- Normal cycle underway ---")
    await asyncio.sleep(5.5)

    logger.info("🚶 Pedestrian requested crossing (ignored if not green)...")
    await interpreter.send("PEDESTRIAN_WAITING")
    await asyncio.sleep(2.5)

    logger.info("🚶 Pedestrian requested crossing again...")
    await interpreter.send("PEDESTRIAN_WAITING")
    await asyncio.sleep(5.5)

    logger.info(
        "🚶 Pedestrian requested crossing on green (should interrupt)..."
    )
    await interpreter.send("PEDESTRIAN_WAITING")
    await asyncio.sleep(8)

    await interpreter.stop()
    logger.info("🏁 Simulation complete.")


if __name__ == "__main__":
    asyncio.run(main())
