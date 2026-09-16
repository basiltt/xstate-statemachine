# examples/sync/features/active_state_ids_and_value/active_state_ids_and_value_runner.py
# -----------------------------------------------------------------------------
# 🌲 current_state_ids vs. value vs. matches() -- three views of one config
# -----------------------------------------------------------------------------
"""Contrasts `current_state_ids`, `active_state_ids`, `value`, and `matches()`.

`current_state_ids` is a flat set of fully-qualified leaf ids -- exact and
unambiguous, but not shaped like the machine. `active_state_ids` is a plain
alias of it. `value` is the hierarchical form XState's `state.value`
returns (a string for an atomic leaf, a dict for nested regions). `matches()`
accepts either a partial id string or a partial `value`-shaped dict, and
answers whether that shape is currently active -- the ergonomic way most
guard/UI code actually wants to ask the question.
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
    "id": "checkout",
    "initial": "cart",
    "states": {
        "cart": {"on": {"NEXT": "payment"}},
        "payment": {
            "initial": "entering",
            "states": {
                "entering": {"on": {"SUBMIT": "processing"}},
                "processing": {},
            },
        },
    },
}


def main() -> None:
    """🚀 Same configuration, four different lenses onto it."""
    print("\n--- 🌲 State Views Simulation ---")
    machine = create_machine(CONFIG)
    interpreter = SyncInterpreter(machine).start()

    interpreter.send("NEXT")
    interpreter.send("SUBMIT")

    logger.info(f"current_state_ids: {interpreter.current_state_ids}")
    logger.info(f"active_state_ids:  {interpreter.active_state_ids}")
    assert interpreter.current_state_ids == interpreter.active_state_ids
    assert interpreter.current_state_ids == {"checkout.payment.processing"}

    logger.info(f"value: {interpreter.value}")
    assert interpreter.value == {"payment": "processing"}

    logger.info(
        f"matches('payment.processing'): "
        f"{interpreter.matches('payment.processing')}"
    )
    logger.info(
        f"matches({{'payment': 'processing'}}): "
        f"{interpreter.matches({'payment': 'processing'})}"
    )
    logger.info(f"matches('cart'): {interpreter.matches('cart')}")
    assert interpreter.matches("payment.processing") is True
    assert interpreter.matches({"payment": "processing"}) is True
    assert interpreter.matches("cart") is False

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
