# examples/async/features/wait_done/wait_done_runner.py
# -----------------------------------------------------------------------------
# 🏁 wait_done() -- awaiting completion instead of polling status (0.8.0, #43)
# -----------------------------------------------------------------------------
"""Demonstrates `interpreter.wait_done()`.

Before this future existed, a parent that wanted to know when a machine
reached a final state had to poll `interpreter.status` on a timer -- wasted
wake-ups for something the interpreter already knows the instant it happens.
`wait_done()` returns a future resolved from the terminal-status transition
itself, so the caller just awaits it.
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
    "id": "job",
    "initial": "running",
    "states": {
        "running": {"on": {"FINISH": "done"}},
        "done": {"type": "final"},
    },
}


async def main() -> None:
    """🚀 Await completion instead of racing the run loop with a sleep."""
    print("\n--- 🏁 wait_done() Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = await Interpreter(machine).start()

    waiter = asyncio.ensure_future(interpreter.wait_done())
    await interpreter.send("FINISH", wait=False)

    status = await waiter
    logger.info(f"wait_done() resolved with status: {status!r}")
    assert status == "done"
    assert interpreter.status == "done"

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
