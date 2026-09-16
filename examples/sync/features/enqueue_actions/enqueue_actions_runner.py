# examples/sync/features/enqueue_actions/enqueue_actions_runner.py
# -----------------------------------------------------------------------------
# 📥 enqueue_actions() -- imperatively building an action list (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `enqueue_actions()` action creator.

`enqueue_actions` subsumes both `pure` and `choose`: its callback receives
an `enqueue` helper (plus `context`, `event`, `check` and `self`) and
imperatively appends whatever actions should run, including conditionally.
This is the most flexible of the three dynamic-action creators -- reach
for `pure`/`choose` first if a simpler shape fits.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    SyncInterpreter,
    create_machine,
    enqueue_actions,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_actions(args: Dict[str, Any]) -> None:
    """🏗️ Enqueues an increment, and conditionally a doubling too."""
    enqueue = args["enqueue"]
    event = args["event"]
    enqueue.assign(lambda a: {**a["context"], "n": a["context"]["n"] + 1})
    if event.payload.get("double"):
        enqueue.assign(lambda a: {**a["context"], "n": a["context"]["n"] * 2})


CONFIG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"GO": {"actions": [enqueue_actions(build_actions)]}}}
    },
}


def main() -> None:
    """🚀 The SAME event handler produces a different action list per payload."""
    print("\n--- 📥 enqueue_actions() Simulation ---")
    interpreter = SyncInterpreter(create_machine(CONFIG)).start()

    interpreter.send("GO")  # no payload: only the increment fires
    logger.info(f"After plain GO: {interpreter.context}")
    assert interpreter.context["n"] == 1

    interpreter.send("GO", double=True)  # payload flag adds the doubling too
    logger.info(f"After GO(double=True): {interpreter.context}")
    assert interpreter.context["n"] == 4  # (1 + 1) * 2

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
