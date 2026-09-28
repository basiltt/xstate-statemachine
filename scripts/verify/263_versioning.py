"""Verification for #263 (A6 versioning). `python scripts/verify/263_versioning.py`.

Runs against the installed package. The issue's scenario with the
review-amended names: a v1 blob into the v2 machine is refused with
MachineVersionMismatchError (a SnapshotDriftError); a SnapshotMigrator
step restores it; multi-hop chains; `xsm snapshots --stale` lists stale
keys.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import SyncInterpreter, create_machine
    from xstate_statemachine.exceptions import SnapshotDriftError
    from xstate_statemachine.persistence import (
        MachineVersionMismatchError,
        NoMigrationPathError,
        SnapshotMigrator,
        SQLiteStore,
        save_interpreter,
    )

    v1 = {
        "id": "o",
        "version": "1.0",
        "initial": "paying",
        "states": {
            "paying": {"on": {"OK": "done"}},
            "done": {"type": "final"},
        },
    }
    v2 = {
        "id": "o",
        "version": "2.0",
        "initial": "payment",
        "states": {
            "payment": {
                "initial": "card",
                "states": {"card": {"on": {"OK": "#o.done"}}},
            },
            "done": {"type": "final"},
        },
    }
    v3 = {**v2, "version": "3.0", "context": {"currency": "USD"}}
    m1, m2, m3 = create_machine(v1), create_machine(v2), create_machine(v3)
    blob = SyncInterpreter(m1).start().get_snapshot()

    step("default policy refuses loudly")
    try:
        SyncInterpreter.from_snapshot(blob, m2)
        raise SystemExit("should have refused")
    except MachineVersionMismatchError as e:
        assert isinstance(e, SnapshotDriftError)
        print("  refused:", e)

    step("SnapshotMigrator step restores into the new shape")
    mig = SnapshotMigrator()

    @mig.register("1.0", "2.0")
    def up(b):  # noqa: ANN001
        b["state_ids"] = [
            "o.payment.card" if s == "o.paying" else s for s in b["state_ids"]
        ]
        b["configuration"] = ["o", "o.payment", "o.payment.card"]
        return b

    i = SyncInterpreter.from_snapshot(blob, m2, migrator=mig)
    print("  restored:", i.current_state_ids)
    assert "o.payment.card" in i.current_state_ids

    step(
        "multi-hop chain 1.0 -> 2.0 -> 3.0; missing hop is NoMigrationPathError"
    )
    try:
        mig.path("o", "1.0", "3.0")
        raise SystemExit("expected no path")
    except NoMigrationPathError as e:
        print("  before registering 2.0->3.0:", e)
    mig.add(
        "2.0",
        "3.0",
        lambda b: {
            **b,
            "context": {**b.get("context", {}), "currency": "EUR"},
        },
    )
    print("  path:", mig.path("o", "1.0", "3.0"))
    i3 = SyncInterpreter.from_snapshot(blob, m3, migrator=mig)
    assert (
        i3.current_state_ids == {"o.payment.card"}
        and i3.context["currency"] == "EUR"
    )

    step("xsm snapshots --stale")
    tmp = Path(tempfile.mkdtemp())
    store = SQLiteStore(tmp / "s.db")
    for key, m in (("old-1", m1), ("old-2", m1), ("new-1", m2)):
        x = SyncInterpreter(m).start()
        save_interpreter(store, key, x)
        x.stop()
    store.close()
    (tmp / "v2.json").write_text(json.dumps(v2), encoding="utf-8")
    url = "sqlite:///" + str(tmp / "s.db").replace("\\", "/")
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "snapshots",
            "--store",
            url,
            str(tmp / "v2.json"),
            "--stale",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    data = json.loads(out.stdout)
    print("  stale keys:", sorted(r["key"] for r in data["snapshots"]))
    assert sorted(r["key"] for r in data["snapshots"]) == ["old-1", "old-2"]

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
