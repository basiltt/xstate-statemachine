# examples/sync/features/raise_internal_queue/raise_internal_queue_runner.py
# -----------------------------------------------------------------------------
# 🙋 raise_() -- self-sent events beat the next external send (0.8.0, #36)
# -----------------------------------------------------------------------------
"""Demonstrates that a `raise`-d event is a microstep, not a new macrostep.

Before #36, an action calling `raise_()` queued its event on the SAME inbox
as external `send()` calls, so an external event arriving right after could
overtake it -- the raised event was supposed to be internal and immediate,
but processing order said otherwise. This regression proof records the
processing order and asserts the raised event is always handled before any
externally-sent event queued afterwards.
"""

import logging
import os
import sys
from typing import Any, Dict, List

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine
from xstate_statemachine.actions import raise_

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "queue",
    "initial": "idle",
    "context": {"order": []},
    "states": {
        "idle": {
            "on": {
                "START": {
                    "actions": [
                        {"type": "record", "params": {"label": "START"}},
                        raise_("INTERNAL"),
                    ]
                },
                "INTERNAL": {
                    "actions": [
                        {"type": "record", "params": {"label": "INTERNAL"}}
                    ]
                },
                "EXTERNAL": {
                    "actions": [
                        {"type": "record", "params": {"label": "EXTERNAL"}}
                    ]
                },
            }
        }
    },
}


def record(interpreter, context, event, action_def) -> None:
    """📝 Appends the action's label to the processing order."""
    context["order"].append(action_def.params["label"])


def main() -> None:
    """🚀 The raised INTERNAL event is processed before EXTERNAL, always."""
    print("\n--- 🙋 raise_() Microstep Ordering Simulation ---")
    logic = MachineLogic(actions={"record": record})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = SyncInterpreter(machine).start()

    # 📥 START raises INTERNAL as part of its own microstep; the send()
    #    calls below are two SEPARATE macrosteps, so ordering here would be
    #    trivially guaranteed either way. The real proof is that a single
    #    `send_events` call containing both an event that raises AND a
    #    trailing external event still processes the raise first.
    interpreter.send_events(["START", "EXTERNAL"])

    order: List[str] = interpreter.context["order"]
    logger.info(f"Processing order: {order}")
    assert order == ["START", "INTERNAL", "EXTERNAL"], order

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
