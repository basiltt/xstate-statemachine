# examples/async/features/send_priority/send_priority_runner.py
# -----------------------------------------------------------------------------
# 🚨 send(priority=True) / send_priority() -- the priority lane (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `send(..., priority=True)` and its `send_priority()` alias.

Every inbox has a bound (explicit via `max_queue_size`, or the implicit
processing order otherwise). Normal `send()` appends to the back; a
priority send jumps to the FRONT of the queue, ahead of anything still
waiting -- the escape hatch for an urgent cancel/abort event that must not
sit behind a backlog of routine ones.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import Interpreter, MachineLogic, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "queue",
    "initial": "idle",
    "context": {"order": []},
    "states": {
        "idle": {
            "on": {
                "NORMAL": {"actions": ["record"]},
                "URGENT": {"actions": ["record"]},
            }
        }
    },
}


def record(interpreter, context, event, action_def) -> None:
    """📝 Appends the event type to the processing order."""
    context["order"].append(event.type)


async def main() -> None:
    """🚀 Queue two normal events, then jump one urgent event ahead."""
    print("\n--- 🚨 send(priority=True) Simulation ---")
    logic = MachineLogic(actions={"record": record})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = await Interpreter(machine).start()

    # 📥 Two ordinary sends queue in FIFO order without waiting.
    await interpreter.send("NORMAL", wait=False)
    await interpreter.send("NORMAL", wait=False)
    # 🚨 A priority send jumps the queue -- it is processed BEFORE the two
    #    normal events already waiting, even though it arrives last.
    receipt = await interpreter.send_priority("URGENT")

    await asyncio.sleep(0.05)  # let the run loop drain the whole inbox
    logger.info(f"Priority send receipt: {receipt}")
    logger.info(f"Processing order: {interpreter.context['order']}")
    assert interpreter.context["order"][0] == "URGENT"
    assert interpreter.context["order"][1:] == ["NORMAL", "NORMAL"]

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
