# examples/async/features/drain_on_stop/drain_on_stop_runner.py
# -----------------------------------------------------------------------------
# 🧹 drain_pending() and stop(drain=True) -- inbox durability (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `drain_pending()` and `stop(drain=True)`.

Before 0.8.0, `stop()` discarded whatever was still queued -- fine for a UI
widget, silent data loss for a workflow with unacknowledged events in
flight. `drain_pending()` returns (and empties) the queue without
processing it, so a caller can persist what was lost. `stop(drain=True)`
instead keeps the run loop alive just long enough to process everything
still queued before shutting down -- the "finish what's in flight" choice.
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
    "id": "sink",
    "initial": "collecting",
    "context": {"processed": 0},
    "states": {"collecting": {"on": {"E": {"actions": ["count"]}}}},
}


def count(interpreter, context, event, action_def) -> None:
    """📈 Records that this event was actually processed."""
    context["processed"] += 1


async def main() -> None:
    """🚀 First discard a backlog, then drain one to completion instead."""
    print("\n--- 🧹 drain_pending() / stop(drain=True) Simulation ---")
    logic = MachineLogic(actions={"count": count})

    # 🗑️ drain_pending(): pull the backlog out WITHOUT processing it.
    machine1 = create_machine(CONFIG, logic=logic)
    interp1 = await Interpreter(machine1).start()
    for _ in range(5):
        await interp1.send("E", wait=False)
    discarded = await interp1.drain_pending()
    logger.info(f"drain_pending() pulled {len(discarded)} unprocessed events")
    assert len(discarded) == 5
    assert interp1.context["processed"] == 0
    await interp1.stop()

    # ✅ stop(drain=True): let the queued backlog finish before shutting down.
    machine2 = create_machine(CONFIG, logic=logic)
    interp2 = await Interpreter(machine2).start()
    for _ in range(5):
        await interp2.send("E", wait=False)
    await interp2.stop(drain=True, timeout=2)
    logger.info(
        f"stop(drain=True) processed {interp2.context['processed']} events"
    )
    assert interp2.context["processed"] == 5

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
