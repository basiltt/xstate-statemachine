# examples/sync/features/subscribe/subscribe_runner.py
# -----------------------------------------------------------------------------
# 🔔 subscribe() -- a listener for every settled transition (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `interpreter.subscribe()`.

Mirrors XState's `actor.subscribe()`: register a listener that fires after
every settled macrostep, and get back an unsubscribe callable. Without this,
observing the interpreter meant wrapping every `send()` call site by hand --
easy to forget at exactly the call site that introduces the bug.
"""

import logging
import os
import sys
from typing import Any, Dict, List

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "light",
    "initial": "red",
    "states": {
        "red": {"on": {"NEXT": "green"}},
        "green": {"on": {"NEXT": "yellow"}},
        "yellow": {"on": {"NEXT": "red"}},
    },
}


def main() -> None:
    """🚀 A subscriber observes transitions until it unsubscribes."""
    print("\n--- 🔔 subscribe() Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = SyncInterpreter(machine).start()

    observed: List[str] = []

    def listener(interp: SyncInterpreter) -> None:
        """👂 Records the interpreter's state each time it settles."""
        observed.append(next(iter(interp.current_state_ids)))

    unsubscribe = interpreter.subscribe(listener)

    interpreter.send("NEXT")  # red -> green
    interpreter.send("NEXT")  # green -> yellow
    logger.info(f"Observed while subscribed: {observed}")
    assert observed == ["light.green", "light.yellow"]

    unsubscribe()
    interpreter.send("NEXT")  # yellow -> red, but nobody is listening
    logger.info(f"Observed after unsubscribe: {observed}")
    assert observed == ["light.green", "light.yellow"]  # unchanged
    assert "light.red" in interpreter.current_state_ids

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
