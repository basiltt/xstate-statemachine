# -------------------------------------------------------------------------------
# 🚀 Async CI/CD Pipeline Runner
# examples/async/complex/functional_approach/with_logic_loader/ci_cd_pipeline_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the asynchronous CI/CD pipeline simulation
using functional logic via LogicLoader.
"""

import asyncio
import json
import logging
import os
import random
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter

# -----------------------------------------------------------------------------
# 📂 Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
import ci_cd_pipeline_logic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the CI/CD pipeline simulation."""
    logger.info("\n--- 🚀 Async CI/CD Pipeline Simulation ---")

    path = os.path.join(os.path.dirname(__file__), "ci_cd_pipeline.json")
    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[ci_cd_pipeline_logic])
    interpreter = await Interpreter(machine).start()

    commit = f"{random.getrandbits(128):032x}"
    await interpreter.send("NEW_COMMIT", hash=commit)
    # Wait for all parallel stages to complete (build 2s + tests 3s + deploy 2s)
    await asyncio.sleep(8.0)

    logger.info("--- Pipeline Summary ---")
    logger.info(f"Final state: {interpreter.current_state_ids}")
    logger.info(f"Context: {json.dumps(interpreter.context, indent=2)}")

    await interpreter.stop()
    logger.info("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
