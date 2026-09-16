# examples/async/features/to_promise/to_promise_runner.py
# -----------------------------------------------------------------------------
# ⏳ to_promise() / wait_for_sync() -- awaiting completion (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `to_promise()` and its sync counterpart `wait_for_sync()`.

`to_promise(interpreter)` mirrors XState's `toPromise(actor)`: it awaits a
machine reaching a top-level final state and resolves to its `output`, or
re-raises whatever error the machine recorded. `wait_for_sync()` is the
blocking equivalent for `SyncInterpreter` -- both build on the same
predicate-polling primitive as `wait_for()`.
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
    SyncInterpreter,
    create_machine,
    to_promise,
    wait_for_sync,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "job",
    "initial": "running",
    "states": {
        "running": {"on": {"FINISH": "done"}},
        "done": {"type": "final", "output": {"result": "ok"}},
    },
}


async def run_async_part() -> None:
    """🚀 `to_promise()` resolves once the machine reaches its final state."""
    interpreter = await Interpreter(create_machine(CONFIG)).start()
    promise = asyncio.ensure_future(to_promise(interpreter, timeout=2))
    await asyncio.sleep(0.02)
    await interpreter.send("FINISH")
    output = await promise
    logger.info(f"to_promise() resolved with output: {output}")
    assert output == {"result": "ok"}
    await interpreter.stop()


def run_sync_part() -> None:
    """🚀 `wait_for_sync()` blocks until a predicate over the interpreter holds."""
    interpreter = SyncInterpreter(create_machine(CONFIG)).start()
    interpreter.send("FINISH")
    settled = wait_for_sync(
        interpreter, lambda i: i.status == "done", timeout=2
    )
    logger.info(f"wait_for_sync() settled with status: {settled.status}")
    assert settled.status == "done"
    interpreter.stop()


async def main() -> None:
    """🚀 Run both the async and sync completion-awaiting helpers."""
    print("\n--- ⏳ to_promise() / wait_for_sync() Simulation ---")
    await run_async_part()
    run_sync_part()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
