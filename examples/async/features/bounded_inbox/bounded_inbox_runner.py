# examples/async/features/bounded_inbox/bounded_inbox_runner.py
# -----------------------------------------------------------------------------
# 📬 Bounded Inbox -- max_queue_size + OverflowPolicy (0.8.0, #38)
# -----------------------------------------------------------------------------
"""Demonstrates a bounded event inbox with ``max_queue_size``.

Before 0.8.0 the inbox was unbounded: a slow consumer facing a bursty
producer just grew memory without limit. `max_queue_size` puts a ceiling
on it, and `overflow_policy` decides what a FULL inbox does to the next
`send()` -- `RAISE` (default once a bound is set; sheds load loudly with
`QueueOverflowError`), `BLOCK` (back-pressure the producer), or
`DROP_NEWEST` (discard the newest event with a warning). This script
uses the default `RAISE` policy because it is the easiest to observe
deterministically: fire more events than the bound allows, in the same
macrostep, before the run loop gets a chance to drain any of them.
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
    OverflowPolicy,
    QueueOverflowError,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "telemetry-sink",
    "initial": "collecting",
    "states": {"collecting": {"on": {"READING": "collecting"}}},
}


async def main() -> None:
    """🚀 Flood a 2-slot inbox; the 3rd send raises QueueOverflowError."""
    print("\n--- 📬 Bounded Inbox Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = Interpreter(
        machine,
        max_queue_size=2,
        overflow_policy=OverflowPolicy.RAISE,
    )
    await interpreter.start()

    # 🐢 Two readings fit the bound; a third overflows it before the run
    #    loop gets a chance to drain anything, since nothing here yields.
    await interpreter.send("READING", value=1)
    await interpreter.send("READING", value=2)
    try:
        await interpreter.send("READING", value=3)
    except QueueOverflowError as exc:
        logger.info(f"❌ Rejected as expected: {exc}")
    else:  # pragma: no cover - would mean the feature regressed
        raise AssertionError("expected QueueOverflowError")

    await asyncio.sleep(0.05)  # let the queued readings actually process
    logger.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
