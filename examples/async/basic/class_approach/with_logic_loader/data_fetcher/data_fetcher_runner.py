# -------------------------------------------------------------------------------
# 📡 Async Data Fetcher Runner
# examples/async/basic/class_approach/with_logic_loader/data_fetcher_runner.py
# -------------------------------------------------------------------------------
"""
Runs the DataFetcher state machine simulation using DataFetcherLogic.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, create_machine

# --- Ensure project root is on PYTHONPATH ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from data_fetcher_logic import DataFetcherLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def patch_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """🔧 Inject retry transitions into the raw JSON config."""
    config["states"]["fetching"]["on"] = {
        "FETCH_SUCCESS": "success",
        "FETCH_FAILURE": {
            "target": "waiting_to_retry",
            "guard": "has_retries_left",
            "else": "failed",
        },
    }
    return config


async def main() -> None:
    """🚀 Entry point: start the interpreter and simulate fetch flow."""
    logger.info("📡 Starting async Data Fetcher simulation...")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "data_fetcher.json")
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    config = patch_config(raw)
    logic_provider = DataFetcherLogic()
    machine = create_machine(config, logic_providers=[logic_provider])

    interpreter = await Interpreter(machine).start()
    logger.info(f"🔄 Initial state: {interpreter.current_state_ids}")

    await interpreter.send("FETCH")
    await asyncio.sleep(4)  # Allow retries to occur

    logger.info(f"✅ Final state: {interpreter.current_state_ids}")
    logger.info(f"📝 Context: {interpreter.context}")
    await interpreter.stop()
    logger.info("🏁 Simulation complete.")


if __name__ == "__main__":
    asyncio.run(main())
