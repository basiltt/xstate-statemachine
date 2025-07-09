# examples/async/super_complex/functional_approach/with_logic_loader/collaborative_editor_runner.py
# -----------------------------------------------------------------------------
# 📝 Super-Complex Example: Collaborative Editor (Functional / LogicLoader)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Three top-level parallel states managing different concerns.
#   - Spawning actors for each collaborator that joins.
#   - A debounced auto-save mechanism using `after`.
#   - Communication between states (typing triggers saving).
#   - Functional approach with automatic logic discovery.
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
import collaborative_editor_logic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def simulate_user_activity(interpreter: Interpreter):
    """A background task to simulate users joining, leaving, and moving cursors."""
    await asyncio.sleep(2)
    logging.info("\n--- User 'Alice' joins the session ---")
    await interpreter.send("USER_JOINED", user_id="Alice")

    await asyncio.sleep(1)
    # ✅ FIX: Find the actor robustly by checking its context.
    alice_actor = next(
        (
            actor
            for actor in interpreter._actors.values()
            if actor.context.get("user_id") == "Alice"
        ),
        None,
    )

    if alice_actor:
        await alice_actor.send(
            "UPDATE_CURSOR_POS", position={"x": 100, "y": 150}
        )
    else:
        logging.error("Runner could not find Alice's actor to move cursor.")

    await asyncio.sleep(2)
    logging.info("\n--- User 'Bob' joins the session ---")
    await interpreter.send("USER_JOINED", user_id="Bob")

    await asyncio.sleep(2)
    logging.info("\n--- User 'Alice' leaves the session ---")
    await interpreter.send("USER_LEFT", user_id="Alice")


async def main():
    print(
        "\n--- 📝 Async Collaborative Editor Simulation (Functional / LogicLoader) ---"
    )

    with open("collaborative_editor.json", "r") as f:
        config = json.load(f)

    # The LogicLoader will now correctly find `collaborator_cursor` as a required service.
    machine = create_machine(
        config, logic_modules=[collaborative_editor_logic]
    )
    interpreter = await Interpreter(machine).start()

    logging.info(f"Initial states: {interpreter.current_state_ids}")

    user_activity_task = asyncio.create_task(
        simulate_user_activity(interpreter)
    )

    # ... (rest of the simulation is the same) ...
    await asyncio.sleep(1)
    logging.info("\n--- Primary user starts typing ---")
    await interpreter.send("KEY_PRESS", key="H")
    await asyncio.sleep(0.2)
    await interpreter.send("KEY_PRESS", key="e")
    await asyncio.sleep(0.2)
    await interpreter.send("KEY_PRESS", key="l")
    await asyncio.sleep(0.2)
    await interpreter.send("KEY_PRESS", key="l")
    await asyncio.sleep(0.2)
    await interpreter.send("KEY_PRESS", key="o")

    logging.info("...user pauses typing, waiting for auto-save...")
    await asyncio.sleep(8)

    await user_activity_task

    logging.info("\n--- Editor Summary ---")
    logging.info(f"Final state: {interpreter.current_state_ids}")
    serializable_context = interpreter.context.copy()
    serializable_context.pop(
        "actors", None
    )  # Remove actors if they were added
    logging.info(
        f"Final context: {json.dumps(serializable_context, indent=2)}"
    )

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
