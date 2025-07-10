# -------------------------------------------------------------------------------
# 📝 Collaborative Editor Runner
# examples/async/super_complex/functional_approach/with_logic_loader/collaborative_editor/collaborative_editor_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the Collaborative Editor simulation.

Illustrates:
  • Spawning multiple cursor actors via LogicLoader.
  • Simulated user typing and autosave.
  • Actor communication and cleanup.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

import collaborative_editor_logic  # noqa: E402
from src.xstate_statemachine import create_machine, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def simulate_user_activity(interpreter: Interpreter) -> None:
    """👥 Simulate users joining, moving, and leaving."""
    await asyncio.sleep(2)
    logger.info("👤 Alice joined")
    await interpreter.send("USER_JOINED", user_id="Alice")

    alice_actor = next(
        (
            a
            for a in interpreter._actors.values()
            if a.context.get("user_id") == "Alice"
        ),  # noqa
        None,
    )
    if alice_actor:
        await alice_actor.send(
            "UPDATE_CURSOR_POS", position={"x": 100, "y": 150}
        )

    await asyncio.sleep(2)
    logger.info("👤 Bob joined")
    await interpreter.send("USER_JOINED", user_id="Bob")

    await asyncio.sleep(2)
    logger.info("👤 Alice left")
    await interpreter.send("USER_LEFT", user_id="Alice")


async def main() -> None:
    """🚀 Execute the Collaborative Editor simulation."""
    logger.info("\n--- 📝 Collaborative Editor Simulation ---")
    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "collaborative_editor.json")
    with open(config_path, "r", encoding="utf-8") as f:  # noqa
        config: Dict[str, Any] = json.load(f)

    machine = create_machine(
        config, logic_modules=[collaborative_editor_logic]
    )
    interpreter = await Interpreter(machine).start()
    logger.info(f"Initial states: {interpreter.current_state_ids}")

    user_task = asyncio.create_task(simulate_user_activity(interpreter))

    # Simulate primary user typing
    for char in "Hello":
        await interpreter.send("KEY_PRESS", key=char)
        await asyncio.sleep(0.2)

    logger.info("...waiting for autosave...")
    await asyncio.sleep(8.0)

    await user_task
    ctx = interpreter.context.copy()
    ctx.pop("actors", None)
    logger.info(f"Final states: {interpreter.current_state_ids}")
    logger.info(f"Final context: {json.dumps(ctx, indent=2)}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
