# examples/async/features/stop_child/stop_child_runner.py
# -----------------------------------------------------------------------------
# 🛑 stopChild -- imperatively tearing down a spawned actor (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the ``stop_child()`` action creator.

`spawn_child()` starts an actor at will, but a long-running supervisor also
needs to retire one on purpose -- a worker that finished its batch, or a
session that timed out. Without a declarative `stopChild` the only option
was reaching into interpreter internals by hand; this action lets a normal
transition retire a named child and have it vanish from both `_actors` and
the system registry in the same step.
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
    stop_child,
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
            ],
            "on": {"RETIRE": {"actions": [stop_child("w1")]}},
        }
    },
}


async def main() -> None:
    """🚀 Spawn a worker, then retire it and confirm it is gone."""
    print("\n--- 🛑 stopChild Simulation ---")
    logic = MachineLogic(services={"worker": create_machine(WORKER_CONFIG)})
    parent = create_machine(PARENT_CONFIG, logic=logic)
    interpreter = await Interpreter(parent).start()
    await asyncio.sleep(0.02)  # let the spawned actor settle

    logger.info(f"Actors before RETIRE: {sorted(interpreter._actors)}")
    assert "parent:w1" in interpreter._actors
    assert interpreter.system.get("the-worker") is not None

    await interpreter.send("RETIRE", wait=True)

    logger.info(f"Actors after RETIRE: {sorted(interpreter._actors)}")
    assert "parent:w1" not in interpreter._actors
    assert interpreter.system.get("the-worker") is None

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
