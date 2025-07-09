# examples/async/complex/functional_approach/with_logic_loader/ci_cd_pipeline_runner.py
# -----------------------------------------------------------------------------
# 🚀 Complex Example: CI/CD Pipeline (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Parallel States for running tests and security scans concurrently.
#   - `onDone` on a parallel state, which fires only when all its child
#     regions have reached a final state.
#   - Multiple `invoke`d services representing pipeline stages.
#   - Functional approach with automatic logic discovery via `logic_modules`.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys
import random

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter
import ci_cd_pipeline_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- 🚀 Async CI/CD Pipeline Simulation (Functional / LogicLoader) ---"
    )

    with open("ci_cd_pipeline.json", "r") as f:
        config = json.load(f)

    # Create the machine using auto-discovery from the imported module
    machine = create_machine(config, logic_modules=[ci_cd_pipeline_logic])

    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    commit_hash = f"{random.getrandbits(128):032x}"
    await interpreter.send("NEW_COMMIT", hash=commit_hash)

    # Wait long enough for all stages to complete
    # Build (2s) + Tests (3s) + Deploy (2s) = 7s. Add buffer.
    await asyncio.sleep(8)

    logging.info("\n--- Pipeline Summary ---")
    logging.info(f"Final state: {interpreter.current_state_ids}")
    logging.info(f"Final context: {json.dumps(interpreter.context, indent=2)}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
