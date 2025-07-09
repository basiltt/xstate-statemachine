# examples/async/intermediate/functional_approach/without_logic_loader/video_transcoder_runner.py
# -----------------------------------------------------------------------------
# 🎬 Intermediate Example: Video Transcoder (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous actions that send events back to the machine.
#   - Asynchronous services (`invoke`) to model a multi-stage process.
#   - Explicit logic binding for standalone `async` functions.
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
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from video_transcoder_logic import (
    upload_video_file,
    set_transcoding_status,
    set_error,
    transcode_video_service,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def run_simulation(config, logic, payload):
    """Helper to run a single simulation instance."""
    interpreter = await Interpreter(
        create_machine(config, logic=logic)
    ).start()
    await interpreter.send("SELECT_FILE", **payload)
    # Wait long enough for both upload action and transcode service
    await asyncio.sleep(5.5)
    logging.info(f"Final state: {interpreter.current_state_ids}")
    logging.info(f"Final context: {interpreter.context}")
    await interpreter.stop()


async def main():
    print(
        "\n--- 🎬 Async Video Transcoder Simulation (Functional / Explicit Logic) ---"
    )

    with open("video_transcoder.json", "r") as f:
        config = json.load(f)

    # Manually bind the standalone functions to a MachineLogic object
    machine_logic = MachineLogic(
        actions={
            "upload_video_file": upload_video_file,
            "set_transcoding_status": set_transcoding_status,
            "set_error": set_error,
        },
        services={"transcode_video_service": transcode_video_service},
    )

    # --- Scenario 1: Successful transcode ---
    print("\n--- Scenario 1: Successful Upload and Transcode ---")
    await run_simulation(
        config, machine_logic, {"file_name": "family_vacation.mp4"}
    )

    # --- Scenario 2: Transcoding fails ---
    print("\n--- Scenario 2: Upload Succeeds but Transcoding Fails ---")
    await run_simulation(
        config, machine_logic, {"file_name": "archive_unsupported.mov"}
    )

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
