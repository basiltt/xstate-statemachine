# -------------------------------------------------------------------------------
# 📞 Async API Fetcher Runner
# examples/async/intermediate/class_approach/with_logic_loader/api_fetcher/api_fetcher_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async API Fetcher simulation using LogicLoader.

Illustrates:
  • Async service invocation (`invoke`).
  • `onDone` / `onError` transitions.
  • Automatic discovery of class-based actions and service.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter

# -----------------------------------------------------------------------------
# 🛠️ Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from api_fetcher_logic import ApiFetcherLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the API Fetcher state machine simulation."""
    logger.info(
        "\n--- 📞 Async API Fetcher Simulation (Class / LogicLoader) ---"
    )

    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "api_fetcher.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = ApiFetcherLogic()
    machine = create_machine(config, logic_providers=[logic])
    interpreter = await Interpreter(machine).start()

    # --- Scenario 1: Successful Fetch ---
    logger.info("\n--- Scenario 1: Successful Fetch ---")
    await interpreter.send("FETCH", id="user123")
    await asyncio.sleep(2.0)
    logger.info(f"✅ State: {interpreter.current_state_ids}")
    logger.info(f"📝 Context: {interpreter.context}")

    # --- Scenario 2: Failed Fetch ---
    logger.info("\n--- Scenario 2: Failed Fetch ---")
    await interpreter.send("FETCH", id="user999")
    await asyncio.sleep(2.0)
    logger.info(f"✅ State: {interpreter.current_state_ids}")
    logger.info(f"📝 Context: {interpreter.context}")

    await interpreter.stop()
    logger.info("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
