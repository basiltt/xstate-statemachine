# examples/async/features/forward_to/forward_to_runner.py
# -----------------------------------------------------------------------------
# 📮 forward_to() -- relaying the current event onward (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `forward_to()` action creator.

`forward_to(target)` relays the EVENT THAT TRIGGERED the current transition
straight to another actor, unchanged -- a one-line proxy, instead of
manually re-building the event with `send_to()`.
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
    forward_to,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHILD_CONFIG: Dict[str, Any] = {
    "id": "child",
    "initial": "idle",
    "context": {"pings": 0},
    "states": {"idle": {"on": {"PING": {"actions": ["count_ping"]}}}},
}

PARENT_CONFIG: Dict[str, Any] = {
    "id": "parent",
    "initial": "run",
    "states": {
        "run": {
            "entry": [
                {
                    "type": "spawnChild",
                    "params": {
                        "src": "child",
                        "id": "c1",
                        "systemId": "the-child",
                    },
                }
            ],
            "on": {"PING": {"actions": [forward_to("c1")]}},
        }
    },
}


def count_ping(interpreter, context, event, action_def) -> None:
    """📈 Proves the forwarded event reached the child."""
    context["pings"] += 1


async def main() -> None:
    """🚀 The parent receives PING and forwards it, unopened, to its child."""
    print("\n--- 📮 forward_to() Simulation ---")
    logic = MachineLogic(
        services={
            "child": create_machine(
                CHILD_CONFIG,
                logic=MachineLogic(actions={"count_ping": count_ping}),
            )
        }
    )
    parent = create_machine(PARENT_CONFIG, logic=logic)
    interpreter = await Interpreter(parent).start()
    await asyncio.sleep(0.02)

    await interpreter.send("PING")
    await asyncio.sleep(0.05)

    child = interpreter.system.get("the-child")
    assert child is not None
    logger.info(f"Child context after forwarding: {child.context}")
    assert child.context["pings"] == 1

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
