# examples/sync/features/persisted_snapshot/persisted_snapshot_runner.py
# -----------------------------------------------------------------------------
# 📸 get_persisted_snapshot() vs get_snapshot() -- dict vs JSON string (0.8.0)
# -----------------------------------------------------------------------------
"""Contrasts `get_persisted_snapshot()` and `get_snapshot()`, and restores.

`get_persisted_snapshot()` returns the raw envelope dict -- useful when the
caller wants to inspect or further transform it before storage (e.g. adding
it to a larger document). `get_snapshot()` is that same envelope serialised
to a JSON string, ready to write straight to disk/Redis/a queue.
`from_snapshot()` takes the JSON string back and rebuilds a running
interpreter from it.
"""

import json
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "cart",
    "initial": "shopping",
    "context": {"items": 0},
    "states": {
        "shopping": {
            "on": {"ADD": {"actions": ["add_item"]}, "CHECKOUT": "paid"}
        },
        "paid": {"type": "final"},
    },
}


def add_item(interpreter, context, event, action_def) -> None:
    """➕ Increments the item counter."""
    context["items"] += 1


def main() -> None:
    """🚀 Compare the dict envelope with its JSON form, then restore it."""
    print("\n--- 📸 Persisted Snapshot Simulation ---")
    logic = MachineLogic(actions={"add_item": add_item})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = SyncInterpreter(machine).start()
    interpreter.send("ADD")
    interpreter.send("ADD")

    persisted: Dict[str, Any] = interpreter.get_persisted_snapshot()
    logger.info(f"Persisted snapshot type: {type(persisted).__name__}")
    logger.info(f"Envelope keys: {sorted(persisted.keys())}")
    assert isinstance(persisted, dict)
    for key in ("version", "machine_id", "machine_hash", "status", "context"):
        assert key in persisted, key
    assert persisted["machine_id"] == "cart"
    assert persisted["context"]["items"] == 2

    snapshot_json = interpreter.get_snapshot()
    logger.info(f"get_snapshot() type: {type(snapshot_json).__name__}")
    assert isinstance(snapshot_json, str)
    # 🔍 It really is the same envelope, just serialised.
    assert json.loads(snapshot_json)["machine_id"] == persisted["machine_id"]

    interpreter.stop()

    restored = SyncInterpreter.from_snapshot(snapshot_json, machine).start()
    logger.info(f"Restored context: {restored.context}")
    assert restored.context["items"] == 2
    assert "cart.shopping" in restored.current_state_ids

    restored.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
