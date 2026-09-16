# examples/sync/features/strict_targets/strict_targets_runner.py
# -----------------------------------------------------------------------------
# 🎯 strict_targets -- unresolvable transition targets at build time (0.8.0)
# -----------------------------------------------------------------------------
"""Demonstrates `create_machine(..., strict_targets=...)`.

A bare, unqualified target like `"up"` written from a sibling branch used to
resolve through a last-segment fallback -- exactly the mechanism that let a
typo silently bind to an unrelated state. `strict_targets` (default `True`)
rejects any transition whose target does not resolve, at `create_machine()`
time, instead of at the first `send()` that happens to hit it. Passing
`strict_targets=False` explicitly keeps the old escape hatch alive as a
`DeprecationWarning` -- for migrating a large machine one warning at a time.
"""

import logging
import os
import sys
import warnings
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import InvalidConfigError, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 🎯 "up" is only a sibling of "moving.up", not of "controls" -- resolving
# it from "controls.left" requires the deprecated last-segment fallback.
UNRESOLVABLE_CONFIG: Dict[str, Any] = {
    "id": "panel",
    "initial": "controls",
    "states": {
        "controls": {
            "initial": "left",
            "states": {"left": {"on": {"GO": "up"}}},
        },
        "moving": {
            "initial": "idle",
            "states": {"idle": {}, "up": {}},
        },
    },
}

RESOLVABLE_CONFIG: Dict[str, Any] = {
    "id": "panel",
    "initial": "controls",
    "states": {
        "controls": {
            "initial": "left",
            "states": {"left": {"on": {"GO": "#panel.moving.up"}}},
        },
        "moving": {
            "initial": "idle",
            "states": {"idle": {}, "up": {}},
        },
    },
}


def main() -> None:
    """🚀 strict_targets rejects a typo'd target that a lenient build hides."""
    print("\n--- 🎯 strict_targets Simulation ---")

    print("\n--- strict_targets=True (default): raises at build time ---")
    try:
        create_machine(UNRESOLVABLE_CONFIG)
    except InvalidConfigError as exc:
        logger.info(f"❌ Caught as expected: {exc}")
    else:  # pragma: no cover - would mean the feature regressed
        raise AssertionError("expected InvalidConfigError")

    print("\n--- Same target spelled absolutely: builds cleanly ---")
    good_machine = create_machine(RESOLVABLE_CONFIG)
    logger.info(f"Built machine id: {good_machine.id}")
    assert good_machine.id == "panel"

    print(
        "\n--- strict_targets=False (explicit): DeprecationWarning instead ---"
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        downgraded = create_machine(UNRESOLVABLE_CONFIG, strict_targets=False)
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    logger.info(f"Warnings captured: {len(deprecation_warnings)}")
    assert len(deprecation_warnings) == 1
    assert downgraded.id == "panel"

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
