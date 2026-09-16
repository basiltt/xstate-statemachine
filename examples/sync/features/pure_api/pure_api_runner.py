# examples/sync/features/pure_api/pure_api_runner.py
# -----------------------------------------------------------------------------
# 🧪 Pure/testing API -- get_initial_snapshot / get_next_snapshot (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the pure, side-effect-free transition helpers.

`initial_transition()` / `transition()` compute what a REAL run would do
-- the resulting snapshot and the actions it would execute -- WITHOUT
starting an interpreter, spawning any actor or scheduling a timer. This is
what makes model-based testing and instant state previews affordable: no
interpreter lifecycle to manage, just plain data in, plain data out.
`get_initial_snapshot()` / `get_next_snapshot()` are the same computation
with the recorded actions discarded, for callers who only want the state.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    create_machine,
    get_initial_snapshot,
    get_next_snapshot,
    initial_transition,
    pure_transition,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"FLIP": "on"}},
        "on": {"on": {"FLIP": "off"}},
    },
}


def main() -> None:
    """🚀 Compute two steps forward without ever starting an interpreter."""
    print("\n--- 🧪 Pure Transition API Simulation ---")
    machine = create_machine(CONFIG)

    # 🧪 `initial_transition` returns BOTH the snapshot and the entry
    #    actions a real `start()` would have executed.
    snap0, entry_actions = initial_transition(machine)
    logger.info(f"Initial snapshot: {snap0}")
    logger.info(f"Entry actions recorded: {[a.type for a in entry_actions]}")
    assert snap0.matches("off")

    # 🧪 `pure_transition` steps forward purely, still returning actions.
    snap1, step_actions = pure_transition(machine, snap0, "FLIP")
    logger.info(f"After FLIP: {snap1}")
    assert snap1.matches("on")

    # 📉 The `get_*` variants are the state-only shorthand.
    plain_snap0 = get_initial_snapshot(machine)
    plain_snap1 = get_next_snapshot(machine, plain_snap0, "FLIP")
    assert plain_snap1.matches("on")
    logger.info(f"get_next_snapshot() agrees: {plain_snap1}")

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
