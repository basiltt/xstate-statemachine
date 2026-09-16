# examples/sync/features/pure_action/pure_action_runner.py
# -----------------------------------------------------------------------------
# 🧼 pure() -- computing an action list from context (0.8.0, XState v4 parity)
# -----------------------------------------------------------------------------
"""Demonstrates the `pure` action creator.

A static `actions` list can only name actions that always fire together.
`pure(fn)` instead calls `fn(context, event)` at transition time and runs
whatever it returns -- a single action, a list, or nothing -- so the
decision of WHICH actions to run can depend on data the config never sees.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine
from xstate_statemachine.actions import log, pure

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def choose_bonus_actions(args: Dict[str, Any]) -> Any:
    """🧮 Computes the action list dynamically from live context."""
    if args["context"]["score"] >= 100:
        return [log("jackpot!"), {"type": "record_bonus"}]
    return {"type": "record_bonus"}


CONFIG: Dict[str, Any] = {
    "id": "arcade",
    "initial": "playing",
    "context": {"score": 0, "bonuses": 0},
    "states": {
        "playing": {
            "on": {
                "SCORE": {
                    "actions": [
                        {"type": "add_points"},
                        pure(choose_bonus_actions),
                    ]
                }
            }
        }
    },
}


def add_points(interpreter, context, event, action_def) -> None:
    """➕ Adds the scored points to the running total."""
    context["score"] += event.payload.get("points", 0)


def record_bonus(interpreter, context, event, action_def) -> None:
    """🎁 Records that a bonus action fired."""
    context["bonuses"] += 1


def main() -> None:
    """🚀 pure() computes a different action list once score crosses 100."""
    print("\n--- 🧼 pure() Simulation ---")
    logic = MachineLogic(
        actions={"add_points": add_points, "record_bonus": record_bonus}
    )
    machine = create_machine(CONFIG, logic=logic)
    interpreter = SyncInterpreter(machine).start()

    interpreter.send("SCORE", points=40)
    logger.info(f"After first score: {interpreter.context}")
    assert interpreter.context["bonuses"] == 1

    interpreter.send("SCORE", points=90)  # crosses the 100-point threshold
    logger.info(f"After jackpot score: {interpreter.context}")
    assert interpreter.context["score"] == 130
    assert interpreter.context["bonuses"] == 2

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
