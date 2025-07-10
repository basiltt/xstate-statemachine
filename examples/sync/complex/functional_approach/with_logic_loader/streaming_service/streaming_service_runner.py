# -----------------------------------------------------------------------------
# 🎬 Streaming Service Runner
# examples/async/complex/functional_approach/with_logic_loader/streaming_service/streaming_service_runner.py
# -----------------------------------------------------------------------------
"""
Runs the async streaming service simulation:

  • SELECT_CONTENT → load_manifest_service → store_manifest
  • PLAY with guard can_play_hd → buffer_video_service → log_playback_started
  • onError → set_error
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter

# Ensure project root on path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
import streaming_service_logic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def wait_for_state(
    interpreter: Interpreter, state_id: str, timeout: float = 6.0
) -> bool:
    """⏳ Poll until the interpreter enters state_id or timeout."""
    start = asyncio.get_event_loop().time()
    while True:
        if state_id in interpreter.current_state_ids:
            logger.info(f"--> Reached '{state_id}'")
            return True
        if asyncio.get_event_loop().time() - start > timeout:
            logger.error(f"--> Timed out waiting for '{state_id}'.")
            return False
        await asyncio.sleep(0.1)


async def main() -> None:
    """🚀 Execute Streaming Service scenarios."""
    print("\n--- 🎬 Async Streaming Service Simulation ---")
    config_path = "streaming_service.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(config, logic_modules=[streaming_service_logic])
    # Scenario 1: HD playback
    print("\n--- Scenario 1: High-speed connection (HD) ---")
    interp1 = await Interpreter(machine).start()
    await interp1.send("SELECT_CONTENT", content_id="movie_123")
    if await wait_for_state(interp1, "streamingService.ready"):
        await interp1.send("PLAY", network_speed_mbps=10)
        await wait_for_state(interp1, "streamingService.playing")
        logger.info(f"Context: {interp1.context}")
    await interp1.stop()

    # Scenario 2: SD fallback
    print("\n--- Scenario 2: Low-speed connection (SD) ---")
    interp2 = await Interpreter(machine).start()
    await interp2.send("SELECT_CONTENT", content_id="movie_123")
    if await wait_for_state(interp2, "streamingService.ready"):
        await interp2.send("PLAY", network_speed_mbps=2)
        await wait_for_state(interp2, "streamingService.playing")
        logger.info(f"Context: {interp2.context}")
    await interp2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
