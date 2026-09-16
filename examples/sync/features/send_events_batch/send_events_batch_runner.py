# examples/sync/features/send_events_batch/send_events_batch_runner.py
# -----------------------------------------------------------------------------
# 📬 send_events() -- one call, a mixed batch of event spellings (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `interpreter.send_events([...])` with mixed event forms.

Feeding a machine several events in a row by calling `send()` in a loop
works, but forces the caller to normalise a heterogeneous batch (event
type strings from one source, payload dicts from another, `Event` objects
already built for retry) before it can do that. `send_events()` accepts
all three spellings in the same list and processes them, in order, in one
call.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    Event,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "till",
    "initial": "open",
    "context": {"log": []},
    "states": {
        "open": {
            "on": {
                "RING": {"actions": ["record"]},
                "REFUND": {"actions": ["record"]},
                "VOID": {"actions": ["record"]},
            }
        }
    },
}


def record(interpreter, context, event, action_def) -> None:
    """📝 Records the event type and payload for inspection."""
    context["log"].append((event.type, dict(event.payload)))


def main() -> None:
    """🚀 A single send_events() call processes three different spellings."""
    print("\n--- 📬 send_events() Batch Simulation ---")
    logic = MachineLogic(actions={"record": record})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = SyncInterpreter(machine).start()

    batch = [
        "RING",  # 🔤 bare string, no payload
        {"type": "REFUND", "amount": 5},  # 📦 dict with inline payload keys
        Event(type="VOID", payload={"reason": "misring"}),  # 🎯 Event object
    ]
    interpreter.send_events(batch)

    logger.info(f"Processing log: {interpreter.context['log']}")
    assert interpreter.context["log"] == [
        ("RING", {}),
        ("REFUND", {"amount": 5}),
        ("VOID", {"reason": "misring"}),
    ]

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
