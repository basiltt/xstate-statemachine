# examples/async/features/wait_for_receipt/send_wait_runner.py
# -----------------------------------------------------------------------------
# 🧾 send(wait=True) -- await the macrostep, get a Receipt (0.8.0, #39)
# -----------------------------------------------------------------------------
"""Demonstrates ``send(wait=True)``.

By default `send()` resolves as soon as the event is queued, not once it
has actually been processed -- correct for fire-and-forget, but useless
if the caller needs to know whether the transition happened, what state
resulted, or whether an action inside it failed. `wait=True` instead
returns a `Receipt` once the full macrostep has run to completion.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import Interpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "order",
    "initial": "placed",
    "states": {
        "placed": {"on": {"SHIP": "shipped"}},
        "shipped": {"type": "final"},
    },
}


async def main() -> None:
    """🚀 Await the receipt instead of racing the run loop with a sleep."""
    print("\n--- 🧾 send(wait=True) Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = await Interpreter(machine).start()

    receipt = await interpreter.send("SHIP", wait=True)
    logger.info(
        f"Receipt: changed={receipt.changed} "
        f"state_ids={sorted(receipt.state_ids)} error={receipt.error}"
    )
    assert receipt.changed is True
    assert receipt.error is None
    assert "order.shipped" in receipt.state_ids

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
