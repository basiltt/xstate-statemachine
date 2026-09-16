# examples/async/features/spawn_child/spawn_child_runner.py
# -----------------------------------------------------------------------------
# 🐣 spawn_child() -- dynamic actor spawning (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `spawn_child()` action creator.

Declaring `invoke` in the config spawns a service the moment its state is
entered. `spawn_child()` is the imperative counterpart: any action list can
spawn a new actor at will, register it under an explicit id, and address it
later through `interpreter.system`.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    create_machine,
    spawn_child,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WORKER_CONFIG: Dict[str, Any] = {
    "id": "worker",
    "initial": "idle",
    "states": {"idle": {}},
}

PARENT_CONFIG: Dict[str, Any] = {
    "id": "parent",
    "initial": "run",
    "states": {
        "run": {
            "entry": [
                spawn_child("worker", actor_id="w1", system_id="the-worker")
            ]
        }
    },
}


async def main() -> None:
    """🚀 An entry action spawns a worker, findable via the system registry."""
    print("\n--- 🐣 spawn_child() Simulation ---")
    logic = MachineLogic(services={"worker": create_machine(WORKER_CONFIG)})
    parent = create_machine(PARENT_CONFIG, logic=logic)
    interpreter = await Interpreter(parent).start()
    await asyncio.sleep(0.02)  # let the spawned actor settle

    worker = interpreter.system.get("the-worker")
    logger.info(
        f"Spawned worker found via system registry: {worker is not None}"
    )
    assert worker is not None
    logger.info(f"Worker state: {worker.current_state_ids}")
    assert "worker.idle" in worker.current_state_ids

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
