# examples/async/features/send_parent/send_parent_runner.py
# -----------------------------------------------------------------------------
# 📨 send_parent() -- child-to-parent actor messaging (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `send_parent()` action creator.

A spawned child cannot address its parent by id -- it does not know one was
assigned. `send_parent()` is the dedicated shortcut: it delivers an event
straight to whichever actor spawned this one, the core primitive behind
child-to-parent notifications in the actor model.
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
    send_parent,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHILD_CONFIG: Dict[str, Any] = {
    "id": "child",
    "initial": "work",
    "states": {
        "work": {"on": {"DONE_WORK": {"actions": [send_parent("CHILD_DONE")]}}}
    },
}

PARENT_CONFIG: Dict[str, Any] = {
    "id": "parent",
    "initial": "run",
    "states": {
        "run": {
            "entry": [
                {"type": "spawnChild", "params": {"src": "child", "id": "c1"}}
            ],
            "on": {
                "RELAY": {
                    "actions": [
                        {
                            "type": "sendTo",
                            "params": {"to": "c1", "event": "DONE_WORK"},
                        }
                    ]
                },
                "CHILD_DONE": "done",
            },
        },
        "done": {},
    },
}


async def main() -> None:
    """🚀 The child sends an event upward; the parent transitions on it."""
    print("\n--- 📨 send_parent() Simulation ---")
    logic = MachineLogic(services={"child": create_machine(CHILD_CONFIG)})
    parent = create_machine(PARENT_CONFIG, logic=logic)
    interpreter = await Interpreter(parent).start()
    await asyncio.sleep(0.02)

    await interpreter.send("RELAY")
    await asyncio.sleep(0.05)

    logger.info(f"State: {interpreter.current_state_ids}")
    assert "parent.done" in interpreter.current_state_ids

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
