# -------------------------------------------------------------------------------
# 🔐 Async Auth Flow Runner
# examples/async/intermediate/functional_approach/with_logic_loader/auth_flow/auth_flow_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async authentication flow simulation using LogicLoader.

Illustrates:
  • Async service invocation (`invoke`).
  • `onDone` / `onError` transitions.
  • Passing credentials via event payload.
  • Auto-discovery of standalone functions.
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
import auth_flow_logic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the Auth Flow state machine simulation."""
    logger.info("\n--- 🔐 Async Auth Flow Simulation ---")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "auth_flow.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[auth_flow_logic])
    interpreter = await Interpreter(machine).start()

    # Scenario 1: Failed Login
    logger.info("\n--- Scenario 1: Failed Login ---")
    await interpreter.send(
        "LOGIN", username="admin", password="wrong_password"
    )
    await asyncio.sleep(1.5)
    logger.info(f"State: {interpreter.current_state_ids}")

    # Scenario 2: Successful Login
    logger.info("\n--- Scenario 2: Successful Login ---")
    await interpreter.send("LOGIN", username="admin", password="password123")
    await asyncio.sleep(1.5)
    logger.info(f"State: {interpreter.current_state_ids}")

    await interpreter.stop()
    logger.info("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
