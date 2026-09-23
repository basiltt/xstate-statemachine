# examples/sync/features/strict_config/strict_config_runner.py
# -----------------------------------------------------------------------------
# 🗝️ Strict config -- a misspelled key is named, at every level (0.9.0, #216/#220)
# -----------------------------------------------------------------------------
"""Demonstrates unknown-key validation on ``create_machine``.

The parser reads a fixed set of keys at each level of the config (root,
state, transition, invoke) and ignores the rest. Before 0.9.0 that made a
one-character typo the quietest bug in the library: ``"entyr"`` was an
entry action that never ran, ``"onn"`` a transition that did not exist,
``"actionErrorPolicyy"`` a safety policy that silently reverted to its
permissive default -- and the machine built clean.

Now every unknown key at every level is reported with its PATH and the
closest known key. By default that is a WARNING and the build proceeds;
``strict_config=True`` (or ``"strictConfig": true`` in the config) refuses
with ``InvalidConfigError`` instead. Keys under ``meta`` or prefixed
``x-`` are the sanctioned homes for custom metadata and are never
reported.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import InvalidConfigError, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 🐛 Two typos, one level down from the root -- exactly where #216's
#    root-only check could not see them.
TYPO_CONFIG: Dict[str, Any] = {
    "id": "form",
    "initial": "editing",
    "states": {
        "editing": {
            "entyr": ["greet"],  # should be "entry"
            "onn": {"SUBMIT": "submitted"},  # should be "on"
        },
        "submitted": {"type": "final"},
    },
}

# ✅ Custom metadata has a home that strict mode never touches.
CLEAN_CONFIG: Dict[str, Any] = {
    "id": "form",
    "initial": "editing",
    "x-owner": "checkout-team",
    "states": {
        "editing": {
            "meta": {"ui": "form"},
            "on": {"SUBMIT": "submitted"},
        },
        "submitted": {"type": "final"},
    },
}


def main() -> None:
    """🚀 Default warns with a hint; strict refuses; metadata is allowed."""
    print("\n--- 🗝️ Strict Config Simulation ---")

    print("\n--- default: the typos are WARNED with 'did you mean' + path ---")
    machine = create_machine(TYPO_CONFIG)  # look at the WARNING line above
    # The machine BUILT, with both typo'd keys ignored: no entry action, and
    # no transition -- the failure mode the warning exists to expose.
    assert not machine.states["editing"].entry
    assert not machine.states["editing"].on
    logger.info("Built anyway; 'editing' has no entry action and no 'on'.")

    print("\n--- strict_config=True: the same typos are REFUSED ---")
    try:
        create_machine(TYPO_CONFIG, strict_config=True)
    except InvalidConfigError as exc:
        logger.info(f"❌ Caught as expected: {exc}")
        assert "form.editing" in str(exc)  # the path
        assert "did you mean 'entry'" in str(exc)  # the hint
    else:  # pragma: no cover - would mean the feature regressed
        raise AssertionError("expected InvalidConfigError")

    print("\n--- strict_config=True: 'x-' keys and 'meta' are always fine ---")
    clean = create_machine(CLEAN_CONFIG, strict_config=True)
    logger.info(f"✅ '{clean.id}' built clean under strict_config.")

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
