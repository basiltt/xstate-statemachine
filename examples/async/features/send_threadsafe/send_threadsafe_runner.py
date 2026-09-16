# examples/async/features/send_threadsafe/send_threadsafe_runner.py
# -----------------------------------------------------------------------------
# 🧵 Interpreter.send_threadsafe() -- cross-thread event delivery (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `Interpreter.send_threadsafe()`.

`send()` is a coroutine: calling it from a plain background thread with no
event loop of its own raises `WrongThreadError`. `send_threadsafe()` is the
dedicated bridge -- it schedules the event onto the interpreter's own loop
from any thread and hands back a `concurrent.futures.Future` the calling
thread can block on.
"""

import asyncio
import logging
import os
import sys
import threading
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
    "id": "m",
    "initial": "waiting",
    "states": {"waiting": {"on": {"PING": {"actions": ["log_ping"]}}}},
}


def log_ping(interpreter, context, event, action_def) -> None:
    """📣 Proves the event actually reached the interpreter's own loop."""
    logger.info("PING handled on the interpreter's event loop")


async def main() -> None:
    """🚀 A worker thread sends an event across into the running interpreter."""
    print("\n--- 🧵 send_threadsafe() Simulation ---")
    logic = MachineLogic(actions={"log_ping": log_ping})
    interpreter = await Interpreter(
        create_machine(CONFIG, logic=logic)
    ).start()

    result: Dict[str, Any] = {}

    def from_worker_thread() -> None:
        """🧵 Runs with NO asyncio event loop of its own."""
        try:
            future = interpreter.send_threadsafe("PING")
            future.result(timeout=2)  # blocks until the event is QUEUED
            result["queued"] = True
        except Exception as exc:  # pragma: no cover - diagnostic aid
            result["error"] = exc

    worker = threading.Thread(target=from_worker_thread)
    worker.start()
    # ⏳ Wait for the thread WITHOUT blocking this loop -- `Thread.join()`
    #    would starve the very loop `send_threadsafe()` needs to run on.
    await asyncio.get_event_loop().run_in_executor(None, worker.join, 2)

    logger.info(f"Cross-thread send result: {result}")
    assert result.get("queued") is True
    await asyncio.sleep(0.05)  # let the run loop process the queued PING

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
