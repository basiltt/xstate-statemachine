# examples/sync/features/choose/choose_runner.py
# -----------------------------------------------------------------------------
# 🔀 choose() -- the first matching branch runs (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates the `choose()` action creator.

`choose` picks the FIRST branch whose `guard` passes (or which has no
guard at all) and runs that branch's actions -- an inline if/elif for
action lists, without a second guarded transition just to vary behaviour.
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
    SyncInterpreter,
    assign,
    choose,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"vip": False, "label": ""},
    "states": {
        "a": {
            "on": {
                "GO": {
                    "actions": [
                        choose(
                            [
                                {
                                    "guard": "isVip",
                                    "actions": [
                                        assign(
                                            lambda a: {
                                                **a["context"],
                                                "label": "vip path",
                                            }
                                        )
                                    ],
                                },
                                {
                                    "actions": [
                                        assign(
                                            lambda a: {
                                                **a["context"],
                                                "label": "default path",
                                            }
                                        )
                                    ]
                                },
                            ]
                        )
                    ]
                }
            }
        }
    },
}


def main() -> None:
    """🚀 The SAME `GO` event resolves to a different branch per context."""
    print("\n--- 🔀 choose() Simulation ---")
    logic = MachineLogic(
        guards={"isVip": lambda context, event: context["vip"]}
    )

    regular = SyncInterpreter(create_machine(CONFIG, logic=logic)).start()
    regular.send("GO")
    logger.info(f"Regular customer: {regular.context['label']}")
    assert regular.context["label"] == "default path"
    regular.stop()

    vip_machine = create_machine(CONFIG, logic=logic)
    vip = SyncInterpreter(vip_machine).start()
    vip.context["vip"] = True
    vip.send("GO")
    logger.info(f"VIP customer: {vip.context['label']}")
    assert vip.context["label"] == "vip path"
    vip.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
