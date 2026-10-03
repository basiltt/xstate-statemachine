# tests/persistence/test_versioning.py
"""#263: `machine_version` label check on restore, `SnapshotMigrator`
(chaining, scoping, missing path), policies, child actors, `persisted()`
pass-through, and the `xsm snapshots --stale` command."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    SnapshotDriftError,
    SnapshotVersionError,
    StateNotFoundError,
)
from src.xstate_statemachine.persistence import (
    MachineVersionMismatchError,
    MemoryStore,
    NoMigrationPathError,
    SnapshotMigrator,
    SQLiteStore,
    persisted,
    save_interpreter,
)

ROOT = Path(__file__).resolve().parents[2]

V1 = {
    "id": "o",
    "version": "1.0",
    "initial": "paying",
    "states": {"paying": {"on": {"OK": "done"}}, "done": {"type": "final"}},
}
V2 = {
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
V3 = {**V2, "version": "3.0", "context": {"currency": "USD"}}


def up_1_2(b: Dict[str, Any]) -> Dict[str, Any]:
    b["state_ids"] = [
        "o.payment.card" if s == "o.paying" else s for s in b["state_ids"]
    ]
    b["configuration"] = ["o", "o.payment", "o.payment.card"]
    return b


def up_2_3(b: Dict[str, Any]) -> Dict[str, Any]:
    b.setdefault("context", {}).setdefault("currency", "EUR")
    return b


def blob_v1() -> str:
    i = SyncInterpreter(create_machine(V1)).start()
    s = i.get_snapshot()
    i.stop()
    return s


class TestMismatchPolicy:
    def test_default_is_error_and_is_drift_error(self) -> None:
        with pytest.raises(MachineVersionMismatchError) as ei:
            SyncInterpreter.from_snapshot(blob_v1(), create_machine(V2))
        e = ei.value
        assert isinstance(e, SnapshotDriftError)
        assert not isinstance(e, SnapshotVersionError)  # layout vs label
        assert (e.machine_id, e.expected, e.found) == ("o", "2.0", "1.0")
        assert "'1.0'" in str(e) and "'2.0'" in str(e) and "'o'" in str(e)

    def test_same_version_passes(self) -> None:
        i = SyncInterpreter.from_snapshot(blob_v1(), create_machine(V1))
        assert i.current_state_ids == {"o.paying"}

    def test_warn_policy_restores_as_is(self, caplog: Any) -> None:
        # Same structure, only the label changed: warn is legitimate.
        v1b = {**V1, "version": "1.1"}
        i = SyncInterpreter.from_snapshot(
            blob_v1(), create_machine(v1b), on_version_mismatch="warn"
        )
        assert i.current_state_ids == {"o.paying"}
        assert any(
            "on_version_mismatch='warn'" in r.message for r in caplog.records
        )

    def test_warn_does_not_bypass_structure_hash(self) -> None:
        # Label mismatch waved through, but V2's structure differs -> drift.
        with pytest.raises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V2), on_version_mismatch="warn"
            )

    def test_invalid_policy(self) -> None:
        with pytest.raises(ValueError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V1), on_version_mismatch="yolo"
            )

    def test_unlabelled_blob_restores_with_warning(self, caplog: Any) -> None:
        from src.xstate_statemachine import base_interpreter as bi

        bi._UNLABELLED_WARNED.clear()  # #263 battle: once per process
        raw = json.loads(blob_v1())
        del raw["machine_version"]  # a 0.10.x writer
        i = SyncInterpreter.from_snapshot(json.dumps(raw), create_machine(V1))
        assert i.current_state_ids == {"o.paying"}
        assert any(
            "carries no machine_version" in r.message for r in caplog.records
        )

    def test_unversioned_chart_never_mismatches(self) -> None:
        cfg = {k: v for k, v in V1.items() if k != "version"}
        m = create_machine(cfg)
        blob = SyncInterpreter(m).start().get_snapshot()
        raw = json.loads(blob)
        raw["machine_version"] = "whatever"
        SyncInterpreter.from_snapshot(json.dumps(raw), m)  # no raise

    def test_error_policy_ignores_provided_migrator(self) -> None:
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)
        with pytest.raises(MachineVersionMismatchError):
            SyncInterpreter.from_snapshot(
                blob_v1(),
                create_machine(V2),
                migrator=mig,
                on_version_mismatch="error",
            )


class TestMigrator:
    def test_single_hop_restores_into_new_shape(self) -> None:
        mig = SnapshotMigrator()
        mig.register("1.0", "2.0")(up_1_2)
        i = SyncInterpreter.from_snapshot(
            blob_v1(), create_machine(V2), migrator=mig
        )
        assert i.current_state_ids == {"o.payment.card"}
        i.start()
        i.send("OK")
        assert i.current_state_ids == {"o.done"}
        # re-persisted at the new version with the NEW hash
        blob = json.loads(i.get_snapshot())
        assert blob["machine_version"] == "2.0"
        assert blob["machine_hash"] == create_machine(V2).structure_hash

    def test_multi_hop_chains_shortest_path(self) -> None:
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)
        mig.add("2.0", "3.0", up_2_3)
        assert mig.path("o", "1.0", "3.0") == [("1.0", "2.0"), ("2.0", "3.0")]
        i = SyncInterpreter.from_snapshot(
            blob_v1(), create_machine(V3), migrator=mig
        )
        assert i.current_state_ids == {"o.payment.card"}
        assert (
            i.context["currency"] == "EUR"
        )  # step ran; machine default did not win

    def test_missing_hop_is_no_path_error(self) -> None:
        mig = SnapshotMigrator()
        mig.add("2.0", "3.0", up_2_3)
        with pytest.raises(NoMigrationPathError) as ei:
            mig.path("o", "1.0", "3.0")
        assert (ei.value.found, ei.value.target) == ("1.0", "3.0")
        assert not mig.can_migrate("o", "1.0", "3.0")
        # from_snapshot with an unusable migrator: the mismatch error
        with pytest.raises(MachineVersionMismatchError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V3), migrator=mig
            )

    def test_migrate_returns_copy_and_drops_hash(self) -> None:
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)
        raw = json.loads(blob_v1())
        out = mig.migrate(raw, "2.0")
        assert out is not raw and raw["state_ids"] == ["o.paying"]
        assert out["machine_version"] == "2.0" and "machine_hash" not in out
        assert mig.migrate(raw, "1.0") == raw  # no hops: equal copy

    def test_scoped_steps_win_over_unscoped(self) -> None:
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", lambda b: {**b, "tag": "generic"})
        mig.add("1.0", "2.0", lambda b: {**b, "tag": "for-o"}, machine_id="o")
        assert (
            mig.migrate({"machine_version": "1.0"}, "2.0", machine_id="o")[
                "tag"
            ]
            == "for-o"
        )
        assert (
            mig.migrate({"machine_version": "1.0"}, "2.0", machine_id="x")[
                "tag"
            ]
            == "generic"
        )

    def test_step_validation(self) -> None:
        mig = SnapshotMigrator()
        with pytest.raises(ValueError):
            mig.register("1.0", "1.0")
        mig.add("1.0", "2.0", lambda b: "not a dict")  # type: ignore[arg-type,return-value]
        with pytest.raises(TypeError):
            mig.migrate({"machine_version": "1.0"}, "2.0")

    def test_migrated_blob_is_validated_against_new_machine(self) -> None:
        # A migration that names a state the new machine lacks is refused
        # (X0.4), never silently accepted.
        mig = SnapshotMigrator()
        mig.add(
            "1.0",
            "2.0",
            lambda b: {
                **b,
                "state_ids": ["o.ghost"],
                "configuration": ["o", "o.ghost"],
            },
        )
        with pytest.raises(StateNotFoundError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V2), migrator=mig
            )

    def test_strict_still_applies_to_restored_events(self) -> None:
        # A pending user event the new (strict) machine does not declare is
        # refused on restore, migration or not.
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)
        raw = json.loads(blob_v1())
        raw["pending_events"] = [
            {"kind": "event", "type": "BOGUS", "payload": {}}
        ]
        m2 = create_machine({**V2, "strict": True})
        i = SyncInterpreter.from_snapshot(json.dumps(raw), m2, migrator=mig)
        i.start()
        assert i.last_error is not None
        assert i.current_state_ids == {"o.payment.card"}

    def test_async_engine_parity(self) -> None:
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)

        async def go() -> Any:
            with pytest.raises(MachineVersionMismatchError):
                Interpreter.from_snapshot(blob_v1(), create_machine(V2))
            i = Interpreter.from_snapshot(
                blob_v1(), create_machine(V2), migrator=mig
            )
            await i.start()
            ids = set(i.current_state_ids)
            await i.stop()
            return ids

        assert asyncio.run(go()) == {"o.payment.card"}


class TestChildActors:
    def test_child_blob_follows_same_policy(self) -> None:
        kid_v1 = {
            "id": "kid",
            "version": "1",
            "initial": "x",
            "states": {"x": {"on": {"GO": "y"}}, "y": {}},
        }
        kid_v2 = {
            "id": "kid",
            "version": "2",
            "initial": "start",
            "states": {"start": {"on": {"GO": "end"}}, "end": {}},
        }
        parent = {
            "id": "p",
            "version": "1",
            "initial": "a",
            "states": {"a": {"entry": "spawn_kid"}},
        }
        m1 = create_machine(
            parent,
            logic=MachineLogic(services={"kid": create_machine(kid_v1)}),
        )
        i = SyncInterpreter(m1).start()
        blob = i.get_snapshot()
        i.stop()
        m2 = create_machine(
            parent,
            logic=MachineLogic(services={"kid": create_machine(kid_v2)}),
        )
        with pytest.raises(MachineVersionMismatchError) as ei:
            SyncInterpreter.from_snapshot(blob, m2)
        assert ei.value.machine_id == "kid"
        mig = SnapshotMigrator()
        mig.add(
            "1",
            "2",
            lambda b: {
                **b,
                "state_ids": ["kid.start"],
                "configuration": ["kid", "kid.start"],
            },
            machine_id="kid",
        )
        r = SyncInterpreter.from_snapshot(blob, m2, migrator=mig)
        (child,) = r._actors.values()
        assert child.current_state_ids == {"kid.start"}


class TestPersistedIntegration:
    def test_persisted_passes_migrator_through(self) -> None:
        store = MemoryStore()
        with persisted(store, "o-1", create_machine(V1)):
            pass
        with pytest.raises(MachineVersionMismatchError):
            with persisted(store, "o-1", create_machine(V2)):
                pass
        mig = SnapshotMigrator()
        mig.add("1.0", "2.0", up_1_2)
        with persisted(store, "o-1", create_machine(V2), migrator=mig) as i:
            assert i.current_state_ids == {"o.payment.card"}
        rec = store.load("o-1")
        assert rec.machine_version == "2.0"  # re-saved at the new label
        # a second load needs no migration any more
        with persisted(store, "o-1", create_machine(V2)) as i:
            assert i.current_state_ids == {"o.payment.card"}


class TestSnapshotsCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "snapshots", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
            env={
                **os.environ,
                "PYTHONPATH": str(ROOT / "src"),
                "PYTHONIOENCODING": "utf-8",
            },
        )

    def test_lists_and_finds_stale(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        for key, cfg in (("old-1", V1), ("old-2", V1), ("new-1", V2)):
            i = SyncInterpreter(create_machine(cfg)).start()
            save_interpreter(store, key, i)
            i.stop()
        store.close()
        (tmp_path / "v2.json").write_text(json.dumps(V2), encoding="utf-8")
        url = "sqlite:///" + str(tmp_path / "s.db").replace("\\", "/")

        out = self._run("--store", url, "--json")
        assert out.returncode == 0, out.stderr
        data = json.loads(out.stdout)
        assert data["count"] == 3 and data["machine_version"] is None

        out = self._run(
            "--store", url, str(tmp_path / "v2.json"), "--stale", "--json"
        )
        assert out.returncode == 0, out.stderr
        data = json.loads(out.stdout)
        assert data["machine_version"] == "2.0" and data["stale_only"]
        assert sorted(r["key"] for r in data["snapshots"]) == [
            "old-1",
            "old-2",
        ]
        assert all(r["machine_version"] == "1.0" for r in data["snapshots"])

        out = self._run("--store", url, str(tmp_path / "v2.json"), "--stale")
        assert "old-1" in out.stdout and "new-1" not in out.stdout
        assert "stale snapshots (2)" in out.stdout

        out = self._run("--store", url, "--stale")
        assert out.returncode != 0 and "needs the machine JSON" in out.stderr

    def test_file_store_url_and_empty(self, tmp_path: Any) -> None:
        url = "file:///" + str(tmp_path / "fs").replace("\\", "/")
        out = self._run("--store", url)
        assert out.returncode == 0 and "store is empty" in out.stdout
        out = self._run("--store", "redis://x")
        assert out.returncode != 0 and "unsupported store URL" in out.stderr
