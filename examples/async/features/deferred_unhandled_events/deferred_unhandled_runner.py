# examples/async/features/deferred_unhandled_events/deferred_unhandled_runner.py
# -----------------------------------------------------------------------------
# 📨 onUnhandled: "defer" (0.8.0, #26-#60)
# -----------------------------------------------------------------------------
"""Demonstrates the ``onUnhandled`` config key set to ``"defer"``.

By default (`"ignore"`, the 0.7.x behaviour) an event with no matching
transition in the current state just vanishes. `"defer"` instead holds
it, and replays it automatically the next time the machine successfully
transitions -- useful for a UI that lets a user tap "next" before a
loading spinner clears: the tap is not lost, it fires again once the
machine is ready to handle it.
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
    "id": "loading-gate",
    "initial": "loading",
    "onUnhandled": "defer",
    "states": {
        "loading": {"on": {"LOADED": "ready"}},
        "ready": {"on": {"NEXT": "done"}},
        "done": {"type": "final"},
    },
}


async def main() -> None:
    """🚀 Send NEXT while still loading; it fires once LOADED lands."""
    print("\n--- 📨 Deferred Unhandled Events Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = await Interpreter(machine).start()

    logger.info(f"Initial state: {interpreter.current_state_ids}")

    # 🖱️ The user taps "next" too early -- 'loading' has no NEXT handler.
    # 📬 Unlike SyncInterpreter, the async engine only QUEUES the event
    #    here; it is processed by the run loop, so wait=True is used to
    #    observe the deferral only after its macrostep actually ran.
    await interpreter.send("NEXT", wait=True)
    logger.info(
        f"After early NEXT: state={interpreter.current_state_ids} "
        f"deferred={interpreter.deferred_count}"
    )
    assert interpreter.deferred_count == 1

    # ⏳ The load finishes; the deferred NEXT replays automatically.
    await interpreter.send("LOADED", wait=True)
    logger.info(
        f"After LOADED: state={interpreter.current_state_ids} "
        f"deferred={interpreter.deferred_count}"
    )
    assert "loading-gate.done" in interpreter.current_state_ids
    assert interpreter.deferred_count == 0

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
