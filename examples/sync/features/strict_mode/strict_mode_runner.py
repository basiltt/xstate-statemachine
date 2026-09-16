# examples/sync/features/strict_mode/strict_mode_runner.py
# -----------------------------------------------------------------------------
# 🚨 Strict Mode -- undeclared events raise at the call site (0.8.0, #51)
# -----------------------------------------------------------------------------
"""Demonstrates ``strict=True`` on the interpreter constructor.

By default, sending an event type the machine never declares in any `on`
block is a silent no-op -- a typo like `"SUMBIT"` for `"SUBMIT"` just does
nothing, and nobody notices until a user reports a stuck button. With
`strict=True` the SAME send raises `UnknownEventError` immediately, at
the call site, so the typo is a test failure instead of a support ticket.
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
    UnknownEventError,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "form",
    "initial": "editing",
    "states": {
        "editing": {"on": {"SUBMIT": "submitted"}},
        "submitted": {"type": "final"},
    },
}


def main() -> None:
    """🚀 The same typo behaves differently with strict on vs. off."""
    print("\n--- 🚨 Strict Mode Simulation ---")

    print("\n--- strict=False (default): typo is silently ignored ---")
    lenient = create_machine(CONFIG)
    interpreter = SyncInterpreter(lenient, strict=False).start()
    interpreter.send("SUMBIT")  # 🤫 typo -- no matching `on` entry anywhere
    logger.info(f"State (unchanged): {interpreter.current_state_ids}")
    assert "form.editing" in interpreter.current_state_ids
    interpreter.stop()

    print("\n--- strict=True: same typo raises at the call site ---")
    strict_machine = create_machine(CONFIG)
    interpreter = SyncInterpreter(strict_machine, strict=True).start()
    try:
        interpreter.send("SUMBIT")
    except UnknownEventError as exc:
        logger.info(f"❌ Caught as expected: {exc}")
    else:  # pragma: no cover - would mean the feature regressed
        raise AssertionError("expected UnknownEventError")
    interpreter.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
