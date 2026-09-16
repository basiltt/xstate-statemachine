# examples/sync/features/spawn_blocking_timeout/spawn_blocking_timeout_runner.py
# -----------------------------------------------------------------------------
# ⏱️ spawnBlockingTimeout -- bounding a blocking spawn (0.8.0, #41)
# -----------------------------------------------------------------------------
"""Demonstrates the `spawnBlockingTimeout` config key.

`spawn_blocking_<key>` runs a child to completion INLINE before the
parent's next action -- useful when a step genuinely cannot proceed until
its child is done. But a child that never reaches a terminal state would
hang the parent forever. `spawnBlockingTimeout` (milliseconds) bounds that
wait: past the deadline, the parent logs a warning and continues rather
than blocking indefinitely.
"""

import logging
import os
import sys
import time
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 🐢 This child has an `after` timer far longer than the parent's bound, so
#    it is still "in flight" (not idle) when the blocking wait gives up.
CHILD_CONFIG: Dict[str, Any] = {
    "id": "child",
    "initial": "work",
    "states": {"work": {"after": {5000: "done"}}, "done": {"type": "final"}},
}

PARENT_CONFIG: Dict[str, Any] = {
    "id": "parent",
    "initial": "run",
    "spawnBlockingTimeout": 200,  # 200ms, far shorter than the child's 5s timer
    "states": {
        "run": {"entry": ["spawn_blocking_childSvc"], "on": {"GO": "b"}},
        "b": {},
    },
}


def main() -> None:
    """🚀 The bound (200ms) elapses long before the child (5s) ever would."""
    print("\n--- ⏱️ spawnBlockingTimeout Simulation ---")
    logic = MachineLogic(
        services={"childSvc": lambda i, c, e: create_machine(CHILD_CONFIG)}
    )
    machine = create_machine(PARENT_CONFIG, logic=logic)

    start = time.monotonic()
    interpreter = SyncInterpreter(machine).start()
    elapsed = time.monotonic() - start

    logger.info(f"start() returned after {elapsed:.2f}s (bound was 0.2s)")
    logger.info(f"Parent state: {interpreter.current_state_ids}")
    # ✅ The parent proceeded despite the child never finishing.
    assert elapsed < 2.0
    assert interpreter.status == "running"

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
