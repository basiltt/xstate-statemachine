# -------------------------------------------------------------------------------
# 🎬 Async Video Transcoder Runner
# examples/async/intermediate/functional_approach/without_logic_loader/video_transcoder_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async Video Transcoder simulation with explicit logic binding.

Illustrates:
  • Async actions sending events back.
  • Async service invocation (`invoke`).
  • Explicit MachineLogic for standalone functions.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

# -----------------------------------------------------------------------------
# 🛠️ Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from video_transcoder_logic import (
    upload_video_file,
    set_transcoding_status,
    set_error,
    transcode_video_service,
)  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_simulation(
    config: Dict[str, Any],
    logic: MachineLogic,
    payload: Dict[str, Any],
) -> None:
    """🔧 Run one video transcoding scenario."""
    interpreter = await Interpreter(
        create_machine(config, logic=logic)
    ).start()
    await interpreter.send("SELECT_FILE", **payload)
    await asyncio.sleep(5.5)
    logger.info(f"🔄 State: {interpreter.current_state_ids}")
    logger.info(f"📝 Context: {interpreter.context}")
    await interpreter.stop()


async def main() -> None:
    """🚀 Execute the Video Transcoder state machine simulation."""
    logger.info("\n--- 🎬 Async Video Transcoder Simulation ---")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "video_transcoder.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = MachineLogic(
        actions={
            "upload_video_file": upload_video_file,
            "set_transcoding_status": set_transcoding_status,
            "set_error": set_error,
        },
        services={"transcode_video_service": transcode_video_service},
    )

    # Scenario 1: Success
    logger.info("\n--- Scenario 1: Upload & Transcode Success ---")
    await run_simulation(config, logic, {"file_name": "family_vacation.mp4"})

    # Scenario 2: Transcode Failure
    logger.info("\n--- Scenario 2: Transcode Failure ---")
    await run_simulation(
        config, logic, {"file_name": "archive_unsupported.mov"}
    )

    logger.info("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
