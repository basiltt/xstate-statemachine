# examples/sync/features/simulated_clock/simulated_clock_test_demo.py
# -----------------------------------------------------------------------------
# ⏰ SimulatedClock -- deterministic virtual time for tests (0.8.0, #49)
# -----------------------------------------------------------------------------
"""Demonstrates ``SimulatedClock`` driving an `after` timer with no sleeps.

Testing a timeout used to mean an actual `time.sleep()` in the test
suite -- slow, and flaky under load. `SimulatedClock` makes time a value
the test controls: `increment()` jumps virtual `now()` forward and fires
every timer that became due, in order, synchronously. This file is named
`*_test_demo.py` rather than `*_runner.py` because its entire point is
the pattern a real `unittest`/`pytest` test would use; `main()` exercises
it exactly as a test body would with `assert` instead of `self.assertEqual`.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import SimulatedClock, SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "session",
    "initial": "active",
    "states": {
        "active": {"after": {"30000": "timed_out"}},
        "timed_out": {"type": "final"},
    },
}


def main() -> None:
    """🚀 Advance virtual time instead of sleeping 30 real seconds."""
    print("\n--- ⏰ SimulatedClock Simulation ---")

    clock = SimulatedClock()
    machine = create_machine(CONFIG)
    interpreter = SyncInterpreter(machine, clock=clock).start()
    logger.info(f"t=0: state={interpreter.current_state_ids}")
    assert "session.active" in interpreter.current_state_ids

    # ⏸️ Not due yet -- 29s of virtual time, timer stays armed.
    clock.increment(29_000)
    logger.info(f"t=29s: state={interpreter.current_state_ids}")
    assert "session.active" in interpreter.current_state_ids

    # ⏰ Crossing the 30s mark fires the `after` synchronously.
    clock.increment(1_000)
    logger.info(f"t=30s: state={interpreter.current_state_ids}")
    assert "session.timed_out" in interpreter.current_state_ids

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
