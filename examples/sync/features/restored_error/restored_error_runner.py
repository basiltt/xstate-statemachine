# examples/sync/features/restored_error/restored_error_runner.py
# -----------------------------------------------------------------------------
# 💥 RestoredError -- error status survives a snapshot round-trip (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `actionErrorPolicy: "fail"` and `RestoredError`.

The original exception object cannot survive JSON serialisation, so a
machine restored from a snapshot taken while in `error` status needs
SOMETHING that preserves what went wrong -- otherwise `interp.error` comes
back `None` and the fact of the failure is lost entirely. `from_snapshot()`
wraps the recorded message in `RestoredError` so the caller can still see
it, even though the original exception type is gone.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    MachineLogic,
    RestoredError,
    SyncInterpreter,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "pipeline",
    "initial": "running",
    "actionErrorPolicy": "fail",
    "states": {"running": {"on": {"BOOM": {"actions": ["explode"]}}}},
}


def explode(interpreter, context, event, action_def) -> None:
    """💣 Always raises -- forces the interpreter into 'error' status."""
    raise ValueError("kaboom: the widget assembler jammed")


def main() -> None:
    """🚀 error status + message survive a snapshot/restore round-trip."""
    print("\n--- 💥 RestoredError Simulation ---")
    logic = MachineLogic(actions={"explode": explode})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = SyncInterpreter(machine).start()

    interpreter.send("BOOM")
    logger.info(f"Status after BOOM: {interpreter.status}")
    logger.info(f"Original error: {interpreter.error}")
    assert interpreter.status == "error"
    assert "explode" in str(interpreter.error)

    snapshot_json = interpreter.get_snapshot()

    restored = SyncInterpreter.from_snapshot(snapshot_json, machine)
    logger.info(f"Restored status: {restored.status}")
    logger.info(f"Restored error type: {type(restored.error).__name__}")
    logger.info(f"Restored error message: {restored.error}")
    assert restored.status == "error"
    assert isinstance(restored.error, RestoredError)
    assert "explode" in str(restored.error)

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
