# examples/async/complex/functional_approach/with_logic_loader/streaming_service_runner.py
# -----------------------------------------------------------------------------
# 🎬 Complex Example: Streaming Service (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - A sequence of two `invoke` calls (load manifest, then buffer).
#   - Guards to make a conditional transition (choosing video quality).
#   - Functional approach with automatic logic discovery via `logic_modules`.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter
import streaming_service_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def wait_for_state(
    interpreter: Interpreter, state_id: str, timeout: float = 6.0
) -> bool:
    start_time = asyncio.get_event_loop().time()
    while True:
        if state_id in interpreter.current_state_ids:
            logging.info(f"--> Reached expected state '{state_id}'")
            return True
        if asyncio.get_event_loop().time() - start_time > timeout:
            logging.error(
                f"--> Timed out waiting for state '{state_id}'. Current state: {interpreter.current_state_ids}"
            )
            return False
        await asyncio.sleep(0.1)


async def main():
    print(
        "\n--- 🎬 Async Streaming Service Simulation (Functional / LogicLoader) ---"
    )

    with open("streaming_service.json", "r") as f:
        config = json.load(f)

    machine = create_machine(config, logic_modules=[streaming_service_logic])

    # --- Scenario 1: High-speed connection, plays in HD ---
    print("\n--- Scenario 1: High-speed connection (HD) ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("SELECT_CONTENT", content_id="movie_123")

    if await wait_for_state(interpreter1, "streamingService.ready"):
        await interpreter1.send("PLAY", network_speed_mbps=10)  # High speed
        await wait_for_state(interpreter1, "streamingService.playing")
        logging.info(f"Final context for Scenario 1: {interpreter1.context}")

    await interpreter1.stop()

    # --- Scenario 2: Low-speed connection, falls back to SD ---
    print("\n--- Scenario 2: Low-speed connection (SD) ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("SELECT_CONTENT", content_id="movie_123")

    if await wait_for_state(interpreter2, "streamingService.ready"):
        await interpreter2.send("PLAY", network_speed_mbps=2)  # Low speed
        await wait_for_state(interpreter2, "streamingService.playing")
        logging.info(f"Final context for Scenario 2: {interpreter2.context}")

    await interpreter2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
