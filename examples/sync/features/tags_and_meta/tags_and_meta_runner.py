# examples/sync/features/tags_and_meta/tags_and_meta_runner.py
# -----------------------------------------------------------------------------
# 🏷️ tags & meta -- attaching data to states without context (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates state `tags` and `meta`, plus `has_tag()`/`get_meta()`.

Tags classify what KIND of state is active (e.g. "loading", "error") for
UI code that shouldn't need to know every concrete state name. `meta` is
free-form data attached to a state (e.g. a help URL) that has nothing to do
with the machine's own decision-making, just downstream consumers.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "fetch",
    "initial": "idle",
    "states": {
        "idle": {"tags": ["ready"], "on": {"FETCH": "loading"}},
        "loading": {
            "tags": ["busy"],
            "meta": {"spinner": True},
            "on": {"OK": "success", "FAIL": "failure"},
        },
        "success": {"tags": ["done"]},
        "failure": {
            "tags": ["done", "error"],
            "meta": {"helpUrl": "https://example.com/help"},
        },
    },
}


def main() -> None:
    """🚀 Tags classify the active state; meta carries data for the UI."""
    print("\n--- 🏷️ tags & meta Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = SyncInterpreter(machine).start()

    logger.info(f"idle tags: {interpreter.tags}")
    assert interpreter.tags == {"ready"}
    assert interpreter.has_tag("ready") is True
    assert interpreter.has_tag("busy") is False

    interpreter.send("FETCH")
    logger.info(
        f"loading tags: {interpreter.tags}, meta: {interpreter.get_meta()}"
    )
    assert interpreter.has_tag("busy") is True
    assert interpreter.get_meta()["fetch.loading"]["spinner"] is True

    interpreter.send("FAIL")
    logger.info(
        f"failure tags: {interpreter.tags}, meta: {interpreter.get_meta()}"
    )
    assert interpreter.tags == {"done", "error"}
    assert (
        interpreter.get_meta()["fetch.failure"]["helpUrl"]
        == "https://example.com/help"
    )

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
