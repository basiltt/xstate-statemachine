# examples/sync/features/guard_error_policy/guard_error_policy_runner.py
# -----------------------------------------------------------------------------
# 🛡️ guardErrorPolicy / on_guard_error -- observable guard failures (0.8.0, #35)
# -----------------------------------------------------------------------------
"""Demonstrates the `guardErrorPolicy` config key and the `on_guard_error` hook.

Before 0.8.0 a raising guard was unconditionally treated as `False` -- a
crashing risk check and a legitimately failing one were indistinguishable
to any observer. `guardErrorPolicy` makes the fallback value explicit
(`"false"` default, `"true"`, or `"raise"` to propagate the exception), and
`on_guard_error` fires under EVERY policy so a plugin can always see the
failure, even when the transition's behaviour does not change.
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
    PluginBase,
    SyncInterpreter,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class GuardErrorInspector(PluginBase):
    """🔍 Observes every guard failure, regardless of the configured policy."""

    def __init__(self) -> None:
        self.seen: list = []

    def on_guard_error(self, interpreter, guard_name, event, error) -> None:
        self.seen.append((guard_name, str(error)))
        logger.info(f"👀 Guard '{guard_name}' failed: {error!r}")


def boom(context: Dict[str, Any], event: Any) -> bool:
    """💥 A guard that crashes instead of returning a boolean."""
    raise RuntimeError("guard blew up")


CONFIG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "guardErrorPolicy": "false",  # explicit, though it is also the default
    "states": {"a": {"on": {"GO": {"target": "b", "cond": "boom"}}}, "b": {}},
}


def main() -> None:
    """🚀 A raising guard is swallowed to `False`, but the hook still fires."""
    print("\n--- 🛡️ guardErrorPolicy Simulation ---")
    logic = MachineLogic(guards={"boom": boom})
    inspector = GuardErrorInspector()
    interpreter = SyncInterpreter(create_machine(CONFIG, logic=logic)).start()
    interpreter.use(inspector)

    interpreter.send("GO")

    logger.info(
        f"State (guard swallowed to False, so no transition): "
        f"{interpreter.current_state_ids}"
    )
    assert "m.a" in interpreter.current_state_ids
    assert len(inspector.seen) == 1
    assert inspector.seen[0][0] == "boom"

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
