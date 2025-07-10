# -------------------------------------------------------------------------------
# ⌛ Async Session Timeout Runner
# examples/async/basic/class_approach/without_logic_loader/session_timeout_runner.py
# -------------------------------------------------------------------------------
"""
Simulates user session with timeout and manual activity reset.
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
from session_timeout_logic import SessionTimeoutLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Run session timeout simulation."""
    logger.info("⌛ Starting Session Timeout simulation...")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "session_timeout.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    logic = SessionTimeoutLogic()
    machine_logic = MachineLogic(
        actions={
            "set_user": logic.set_user,
            "log_login": logic.log_login,
            "log_timeout": logic.log_timeout,
        }
    )
    machine = create_machine(config, logic=machine_logic)

    interpreter = await Interpreter(machine).start()
    logger.info(f"🔄 Initial state: {interpreter.current_state_ids}")

    await interpreter.send("LOGIN", user="Basil")
    await asyncio.sleep(0.3)
    logger.info(f"👀 State after login: {interpreter.current_state_ids}")

    # Reset timer via external event
    await asyncio.sleep(2)
    await interpreter.send("USER_ACTIVITY")
    await asyncio.sleep(0.1)
    logger.info("🔄 Timer reset; waiting for timeout...")

    await asyncio.sleep(3.5)
    logger.info(f"✅ Final state: {interpreter.current_state_ids}")
    await interpreter.stop()
    logger.info("🏁 Simulation complete.")


if __name__ == "__main__":
    asyncio.run(main())
