# examples/sync/features/snapshot_drift/snapshot_drift_runner.py
# -----------------------------------------------------------------------------
# 🧬 SnapshotDriftError / verify_machine_hash -- the snapshot envelope (0.8.0, #45)
# -----------------------------------------------------------------------------
"""Demonstrates the snapshot envelope's structural-drift guard.

Every persisted snapshot carries a `machine_hash` -- a fingerprint of the
machine's structure at the moment it was taken. `from_snapshot()` checks it
by default: if the machine definition has since changed shape, restoring
would silently resolve state ids against a DIFFERENT machine, which is how
`StateNotFoundError` surprises show up in production. `SnapshotDriftError`
makes that mismatch loud instead, and `verify_machine_hash=False` is the
explicit opt-out once the caller has migrated the payload by hand.
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
    SnapshotDriftError,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG_V1: Dict[str, Any] = {"id": "m", "initial": "a", "states": {"a": {}}}
# 🔀 Same id, but a new state was added -- a structural change.
CONFIG_V2: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


def main() -> None:
    """🚀 Take a snapshot on v1, then try (and opt out of) restoring on v2."""
    print("\n--- 🧬 Snapshot Drift Simulation ---")
    machine_v1 = create_machine(CONFIG_V1)
    snapshot = SyncInterpreter(machine_v1).start().get_snapshot()

    machine_v2 = create_machine(CONFIG_V2)
    try:
        SyncInterpreter.from_snapshot(snapshot, machine_v2)
    except SnapshotDriftError as exc:
        logger.info(f"❌ Drift detected as expected: {exc}")
    else:  # pragma: no cover - would mean the feature regressed
        raise AssertionError("expected SnapshotDriftError")

    # ✅ Opt out once the structural change is known to be compatible.
    restored = SyncInterpreter.from_snapshot(
        snapshot, machine_v2, verify_machine_hash=False
    )
    logger.info(f"Restored despite drift: {restored.current_state_ids}")
    assert "m.a" in restored.current_state_ids
    restored.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
