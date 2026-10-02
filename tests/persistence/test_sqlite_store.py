# tests/persistence/test_sqlite_store.py
"""#259: `SQLiteStore` specifics -- schema table + newer-schema refusal,
`database is locked` → `LockTimeoutError`, connection per thread, file
modes, network-path warning, and the 16-thread optimistic stress test
(parametrised small here; the full 16×200 runs nightly / via the
verification script)."""

from __future__ import annotations

import os
import sqlite3
import threading
import warnings
from typing import Any, List

import pytest

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import StoreError
from src.xstate_statemachine.persistence import (
    ConflictError,
    LockTimeoutError,
    SQLiteStore,
    load_interpreter,
    save_interpreter,
)
from src.xstate_statemachine.persistence.sqlite_store import SCHEMA_VERSION

SNAP = (
    '{"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}'
)


class TestSchema:
    def test_schema_table_and_version(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        conn = sqlite3.connect(str(tmp_path / "s.db"))
        assert conn.execute("SELECT version FROM xsm_schema").fetchone() == (
            SCHEMA_VERSION,
        )
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"xsm_schema", "statecharts", "deadlines"} <= tables
        conn.close()
        store.close()

    def test_reopen_is_idempotent(self, tmp_path: Any) -> None:
        SQLiteStore(tmp_path / "s.db").save("k", SNAP)
        s2 = SQLiteStore(tmp_path / "s.db")
        assert s2.load("k").version == 1
        s2.close()

    def test_second_handle_opens_while_a_reader_holds_a_transaction(
        self, tmp_path: Any
    ) -> None:
        """Opening a second store on a file another connection is reading
        must not fail. `PRAGMA journal_mode = WAL` on an already-WAL file
        is a no-op, but issuing it needs an exclusive lock -- the Linux
        runners hit `database is locked` in the `xsm dlq` CLI tests when
        the seeding store still held a read transaction (#293). Now the
        mode is only switched when it differs, and a refused switch keeps
        the file's mode with a warning instead of failing to open."""
        path = tmp_path / "s.db"
        SQLiteStore(path).save("k", SNAP)
        reader = sqlite3.connect(str(path), isolation_level=None)
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM statecharts").fetchone()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # no warning on the fast path
                s2 = SQLiteStore(path)  # same mode: no PRAGMA write at all
                assert s2.load("k").version == 1
                s2.close()
            # A DIFFERENT mode cannot be switched under the reader's lock:
            # open anyway, warn, keep the file's mode.
            with pytest.warns(RuntimeWarning, match="could not switch"):
                s3 = SQLiteStore(path, journal_mode="DELETE", busy_timeout=0.2)
            assert s3.load("k").version == 1
            s3.close()
        finally:
            reader.execute("COMMIT")
            reader.close()

    def test_newer_schema_refused(self, tmp_path: Any) -> None:
        SQLiteStore(tmp_path / "s.db").close()
        conn = sqlite3.connect(str(tmp_path / "s.db"))
        conn.execute(
            "UPDATE xsm_schema SET version = ?", (SCHEMA_VERSION + 5,)
        )
        conn.commit()
        conn.close()
        with pytest.raises(StoreError, match="newer"):
            SQLiteStore(tmp_path / "s.db")

    def test_v1_database_upgrades_to_indexed_deadlines(
        self, tmp_path: Any
    ) -> None:
        """A database written by 0.11.0 (schema 1) has no index on
        `deadlines(key)`; opening it runs the v1 -> v2 step, the data is
        intact, and lookups by key no longer SCAN the table (#259 battle:
        save+delete was O(n) in the deadline count on CI)."""
        path = tmp_path / "s.db"
        SQLiteStore(path).save("k", SNAP)
        conn = sqlite3.connect(str(path))
        conn.execute("DROP INDEX deadlines_key")
        conn.execute("UPDATE xsm_schema SET version = 1")
        conn.commit()
        conn.close()

        store = SQLiteStore(path)
        assert store.load("k").version == 1
        assert store.health()["schema_version"] == SCHEMA_VERSION
        conn = sqlite3.connect(str(path))
        assert conn.execute("SELECT version FROM xsm_schema").fetchone() == (
            SCHEMA_VERSION,
        )
        plan = " ".join(
            str(r[3])
            for r in conn.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM deadlines WHERE key = ?",
                ("k",),
            )
        )
        assert "deadlines_key" in plan and "SCAN" not in plan, plan
        conn.close()
        store.close()

    @pytest.mark.skipif(os.name != "posix", reason="POSIX modes")
    def test_db_file_mode_0600(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        store.save("k", SNAP)
        assert (tmp_path / "s.db").stat().st_mode & 0o777 == 0o600
        # X0.5 / X0.10: the WAL sidecars too (they exist while a
        # connection is open in WAL mode; a fresh save creates them).
        for suffix in ("-wal", "-shm"):
            side = tmp_path / f"s.db{suffix}"
            if side.exists():
                assert side.stat().st_mode & 0o777 == 0o600, suffix
        store.close()

    def test_network_path_warns_and_uses_delete_journal(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            store = SQLiteStore.__new__(SQLiteStore)
            # Only exercise the constructor's path check; do not touch a UNC.
            try:
                SQLiteStore.__init__(store, r"\\server\share\x.db")
            except Exception:  # noqa: BLE001 -- the share does not exist
                pass
        assert any("network path" in str(x.message) for x in w)
        assert store.journal_mode == "DELETE"

    def test_memory_db(self) -> None:
        store = SQLiteStore(":memory:")
        assert store.save("k", SNAP) == 1
        assert store.load("k").version == 1
        with store.lock("k"):
            pass
        assert store.health()["journal_mode"] == "memory"
        store.close()

    def test_health_after_close_reopens(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        store.close()
        assert store.health()["ok"]


class TestLocking:
    def test_locked_database_maps_to_lock_timeout(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db", busy_timeout=0.2)
        store.save("k", SNAP)
        entered, release = threading.Event(), threading.Event()

        def holder() -> None:
            with store.lock("k", timeout=5):
                entered.set()
                release.wait(5)

        t = threading.Thread(target=holder)
        t.start()
        entered.wait(5)
        try:
            with pytest.raises(LockTimeoutError):
                store.save("k", SNAP)  # writer blocked by BEGIN IMMEDIATE
        finally:
            release.set()
            t.join(5)
        assert store.save("k", SNAP) == 2
        store.close()

    def test_connection_per_thread(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        # 📝 Hold the connection OBJECTS (not `id()`s -- an id is recycled
        #    once a finished thread's connection is collected) and key by
        #    a thread index (a `get_ident()` can be reused by a later
        #    thread once the earlier one has exited).
        conns: List[Any] = []
        gate = threading.Barrier(4)

        def w(n: int) -> None:
            store.save(f"k-{n}", SNAP)
            conns.append(store._conn())
            gate.wait(5)  # keep all four threads alive together

        ts = [threading.Thread(target=w, args=(n,)) for n in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert len({id(c) for c in conns}) == 4
        assert len(store.list_keys(prefix="k-")) == 4
        store.close()


CFG = {
    "id": "o",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"GO": {"target": "b", "actions": "inc"}}},
        "b": {"on": {"GO": {"target": "a", "actions": "inc"}}},
    },
}


def _inc(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] += 1


@pytest.mark.parametrize(
    "threads,per_thread",
    [
        pytest.param(
            16, int(os.environ.get("XSM_STRESS_SAVES", "8")), id="stress"
        )
    ],
)
def test_optimistic_saves_no_lost_updates(
    tmp_path: Any, threads: int, per_thread: int
) -> None:
    """16 threads × N optimistic saves on 4 keys; every thread retries on
    ConflictError with jitter; final context n == record version ==
    number of successful saves. Set XSM_STRESS_SAVES=200 for the full
    nightly size."""
    import random

    m = create_machine(CFG, logic=MachineLogic(actions={"inc": _inc}))
    store = SQLiteStore(tmp_path / "s.db")
    keys = ["k1", "k2", "k3", "k4"]
    errors: List[BaseException] = []

    def worker(n: int) -> None:
        rng = random.Random(n)
        try:
            for i in range(per_thread):
                key = keys[(n + i) % 4]
                while True:
                    interp, ver = load_interpreter(store, key, m)
                    try:
                        interp.send("GO")
                        save_interpreter(
                            store, key, interp, expected_version=ver
                        )
                        break
                    except (ConflictError, LockTimeoutError):
                        __import__("time").sleep(rng.random() * 0.005)
                    finally:
                        interp.stop()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(300)
    assert errors == []
    total = 0
    for k in keys:
        rec = store.load(k)
        r = SyncInterpreter.from_snapshot(rec.snapshot, m).start()
        assert r.context["n"] == rec.version, k
        total += rec.version
        r.stop()
    assert total == threads * per_thread
    store.close()
