# examples/sync/features/action_error_policy/action_error_policy_runner.py
# -----------------------------------------------------------------------------
# 🛡️ Action Error Policy (0.8.0, #26-#60)
# -----------------------------------------------------------------------------
"""Demonstrates the ``actionErrorPolicy`` config key.

Before 0.8.0 a raising action still let its transition commit -- a
defensible default for a UI widget, and a money-losing one for an order
lifecycle. `actionErrorPolicy` is the opt-in per-machine choice between
the two:

  * ``"continue"`` (0.7.x behaviour, still the default): log the error,
    keep the transition.
  * ``"fail"``: the whole transition is rolled back and a
    `TransitionFailedError` is raised out of `send()`.

This script runs the SAME machine and the SAME raising action once under
each policy so the difference is visible side by side.
"""

import logging
import os
import sys
from typing import Any, Dict

# 🛠️ Ensure the installed (or repo-root) package is importable either way.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    ActionDefinition,
    Event,
    MachineLogic,
    SyncInterpreter,
    TransitionFailedError,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def charge_card_action(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """💥 Simulates a payment gateway timing out mid-transition."""
    context["attempted"] = True
    raise RuntimeError("payment gateway timeout")


def build_config(action_error_policy: str) -> Dict[str, Any]:
    """🏗️ Same machine shape, only the policy key differs."""
    return {
        "id": f"checkout-{action_error_policy}",
        "initial": "cart",
        "actionErrorPolicy": action_error_policy,
        "context": {"attempted": False},
        "states": {
            "cart": {"on": {"CHECKOUT": "paid"}},
            "paid": {"entry": "charge_card"},
        },
    }


def run_continue_policy() -> None:
    """✅ Default: the action's failure is logged but PAID is reached."""
    print("\n--- actionErrorPolicy='continue' (0.7.x default) ---")
    logic = MachineLogic(actions={"charge_card": charge_card_action})
    machine = create_machine(build_config("continue"), logic=logic)
    interpreter = SyncInterpreter(machine).start()

    interpreter.send("CHECKOUT")
    logger.info(f"State: {interpreter.current_state_ids}")
    logger.info(f"Context: {interpreter.context}")
    assert "checkout-continue.paid" in interpreter.current_state_ids
    interpreter.stop()


def run_fail_policy() -> None:
    """🚫 Opt-in strict: the transition is rolled back, send() raises."""
    print("\n--- actionErrorPolicy='fail' (opt-in strict) ---")
    logic = MachineLogic(actions={"charge_card": charge_card_action})
    machine = create_machine(build_config("fail"), logic=logic)
    interpreter = SyncInterpreter(machine).start()

    try:
        interpreter.send("CHECKOUT")
    except TransitionFailedError as exc:
        logger.info(f"❌ Transition rolled back as expected: {exc}")
    # 🛑 "fail" STOPS the machine (0.9.0, #145): the configuration is cleared,
    #    status is "stopped", and the reason is retained on `.error`.
    logger.info(f"Status: {interpreter.status}; error: {interpreter.error}")
    assert interpreter.status == "stopped"
    assert interpreter.current_state_ids == set()
    assert isinstance(interpreter.error, TransitionFailedError)


def main() -> None:
    """🚀 Run both policies back to back."""
    print("\n--- 🛡️ Action Error Policy Simulation ---")
    run_continue_policy()
    run_fail_policy()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
