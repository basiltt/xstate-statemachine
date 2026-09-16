# examples/async/features/escalate/escalate_runner.py
# -----------------------------------------------------------------------------
# 🔥 escalate() -- actor-error propagation (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `escalate()` action creator.

A child actor cannot simply raise a Python exception to signal a business
failure to its parent -- the two run as independent state machines. `escalate`
is the declarative bridge: it sends an `xstate.error.actor.<child-id>` event
to the parent, which the parent handles with an ordinary `on` transition,
exactly like it would `onError` for an invoked service.
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
    escalate,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHILD_CONFIG: Dict[str, Any] = {
    "id": "worker",
    "initial": "working",
    "states": {
        "working": {
            "on": {"FAIL": {"actions": [escalate("boom: worker choked")]}}
        }
    },
}

PARENT_CONFIG: Dict[str, Any] = {
    "id": "supervisor",
    "initial": "running",
    "states": {
        "running": {
            "entry": [
                {"type": "spawnChild", "params": {"src": "worker", "id": "w1"}}
            ],
            "on": {
                "TRIGGER": {
                    "actions": [
                        {
                            "type": "sendTo",
                            "params": {"to": "w1", "event": "FAIL"},
                        }
                    ]
                },
                "xstate.error.actor.supervisor:w1": "failed",
            },
        },
        "failed": {},
    },
}


async def main() -> None:
    """🚀 A child escalates a failure; the parent's own `on` catches it."""
    print("\n--- 🔥 escalate() Simulation ---")
    logic = MachineLogic(services={"worker": create_machine(CHILD_CONFIG)})
    machine = create_machine(PARENT_CONFIG, logic=logic)
    interpreter = await Interpreter(machine).start()
    await asyncio.sleep(0.02)  # let the spawned child settle

    await interpreter.send("TRIGGER")
    await asyncio.sleep(0.05)  # let the escalation event be delivered

    logger.info(f"State: {interpreter.current_state_ids}")
    assert "supervisor.failed" in interpreter.current_state_ids

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
