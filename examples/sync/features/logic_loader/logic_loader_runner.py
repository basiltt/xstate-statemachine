# examples/sync/features/logic_loader/logic_loader_runner.py
# -----------------------------------------------------------------------------
# 🧩 logic_modules + logic_providers -- auto-discovering implementations
# -----------------------------------------------------------------------------
"""Demonstrates `create_machine(config, logic_modules=[...], logic_providers=[...])`.

Wiring every action/guard by hand into a `MachineLogic(...)` dict gets
tedious once a machine has dozens of them. `logic_modules` scans a plain
module for same-named functions instead; `logic_providers` does the same
for methods on a class instance, and -- because providers are scanned
AFTER modules -- a provider's method silently wins over a module function
of the same name, letting a caller override one piece of behaviour (e.g. a
test double) without touching the rest.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import SyncInterpreter, create_machine

sys.path.insert(0, os.path.dirname(__file__))
import logic_loader_logic  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "submission",
    "initial": "idle",
    "context": {"source": None},
    "states": {
        "idle": {
            "on": {
                "SUBMIT": {
                    "target": "accepted",
                    "guard": "guard_is_valid",
                    "actions": ["record_from_module"],
                }
            }
        },
        "accepted": {"type": "final"},
    },
}


class OverrideProvider:
    """🏛️ A class instance whose method overrides the module's version."""

    def record_from_module(
        self, interpreter, context, event, action_def
    ) -> None:
        """📝 Records that the PROVIDER implementation ran instead."""
        context["source"] = "provider"


def main() -> None:
    """🚀 A module supplies logic by name; a provider overrides one action."""
    print("\n--- 🧩 logic_modules / logic_providers Simulation ---")

    print("\n--- logic_modules only: module implementation wins ---")
    machine = create_machine(CONFIG, logic_modules=[logic_loader_logic])
    interpreter = SyncInterpreter(machine).start()
    interpreter.send("SUBMIT", amount=10)
    logger.info(
        f"Source after module-only run: {interpreter.context['source']}"
    )
    assert interpreter.context["source"] == "module"
    interpreter.stop()

    print("\n--- logic_modules + logic_providers: provider wins ---")
    provider = OverrideProvider()
    machine = create_machine(
        CONFIG,
        logic_modules=[logic_loader_logic],
        logic_providers=[provider],
    )
    interpreter = SyncInterpreter(machine).start()
    interpreter.send("SUBMIT", amount=10)
    logger.info(
        f"Source after provider override run: {interpreter.context['source']}"
    )
    assert interpreter.context["source"] == "provider"
    interpreter.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
