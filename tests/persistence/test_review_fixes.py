# tests/persistence/test_review_fixes.py
"""Regression tests for the 0.12.0 persistence code-quality review.

One test (or small group) per finding id (P-xx); each failed before its fix.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    InvalidConfigError,
    NotSupportedError,
    SnapshotCorruptError,
    SnapshotDriftError,
    StoreError,
    StoreUnavailableError,
)
from src.xstate_statemachine.persistence import (
    FileStore,
    IdempotencyPlugin,
    MemoryInbox,
    MemoryStore,
    OptimisticLock,
    SQLiteInbox,
    SQLiteStore,
    apersisted,
    persisted,
)
from src.xstate_statemachine.persistence.deadline import Deadline
from src.xstate_statemachine.persistence.helpers import load_interpreter
from src.xstate_statemachine.persistence.idempotency import (
    default_key,
    fingerprint,
)
from src.xstate_statemachine.persistence.snapshot import (
    check_identity,
    check_version,
    upcast,
)
from src.xstate_statemachine.persistence.timers import DueTimerScanner

CFG = {
    "id": "wallet",
    "initial": "open",
    "context": {"credits": 0},
    "states": {
        "open": {"on": {"CREDIT": {"actions": "add"}}},
    },
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["credits"] += (e.payload or {}).get("amount", 1)


def machine() -> Any:
    return create_machine(CFG, logic=MachineLogic(actions={"add": _add}))


# -- P-04 ------------------------------------------------------------------
def test_p04_remaining_ms_never_overflows() -> None:
    d = Deadline("a", 1, 1e306, 1, "after.1.a")
    assert d.remaining_ms(0.0) == 10**15
    assert Deadline("a", 1, -1e306, 1, "e").remaining_ms(0.0) == 0


# -- P-05 / P-42 / P-20 ----------------------------------------------------
@pytest.mark.parametrize(
    "snap", [{"pending_events": 5}, {"deferred": 7}, {"pending_events": True}]
)
def test_p05_upcast_tolerates_non_list_lanes(snap: Dict[str, Any]) -> None:
    upcast(snap, 2)  # must not raise; check_shape reports it later


def test_p05_from_snapshot_reports_corrupt_not_typeerror() -> None:
    m = machine()
    interp = SyncInterpreter(m).start()
    snap = json.loads(interp.get_snapshot())
    snap["version"] = 2
    snap["pending_events"] = 5
    with pytest.raises(SnapshotCorruptError):
        SyncInterpreter.from_snapshot(
            json.dumps(snap), m, verify_machine_hash=False
        )


def test_p42_fractional_version_is_corrupt() -> None:
    with pytest.raises(SnapshotCorruptError):
        check_version({"version": 1.9})
    assert check_version({"version": 3.0}) == 3
    assert check_version({"version": "3"}) == 3


def test_p20_expected_hash_wins_over_verify_false() -> None:
    m = machine()
    snap = {"machine_id": "wallet", "machine_hash": "deadbeef"}
    with pytest.raises(SnapshotDriftError):
        check_identity(
            snap, m, verify_hash=False, version=4, expected_hash="cafebabe"
        )
    # no expected hash + verify off: still unchecked
    check_identity(snap, m, verify_hash=False, version=4)


# -- P-16 ------------------------------------------------------------------
def test_p16_unknown_restore_kwarg_fails_on_fresh_key_too() -> None:
    with pytest.raises(TypeError, match="expected_machine_hsh"):
        load_interpreter(
            MemoryStore(), "k", machine(), expected_machine_hsh="x"
        )


def test_p16_expected_hash_checked_for_new_key() -> None:
    with pytest.raises(SnapshotDriftError):
        load_interpreter(
            MemoryStore(), "k", machine(), expected_machine_hash="nope"
        )
    interp, version = load_interpreter(
        MemoryStore(),
        "k",
        machine(),
        expected_machine_hash=machine().structure_hash,
    )
    assert version == 0
    interp.stop()


# -- P-14 ------------------------------------------------------------------
class _Marker:
    flush_priority = 0

    def __init__(self) -> None:
        self.flushed = 0
        self.discarded = 0

    def flush_marks(self) -> int:
        self.flushed += 1
        return 1

    def discard_marks(self) -> int:
        self.discarded += 1
        return 0


def test_p14_generator_of_plugins_is_not_exhausted() -> None:
    marker = _Marker()
    store = MemoryStore()
    with persisted(store, "k", machine(), plugins=(p for p in [marker])) as o:
        o.send("CREDIT", amount=2)
    assert marker.flushed == 1


# -- P-02 ------------------------------------------------------------------
def test_p02_apersisted_refuses_custom_strategy() -> None:
    class Custom:
        def run(self, *a: Any, **k: Any) -> Any:  # pragma: no cover
            raise AssertionError

        def acquire(self, store: Any, key: str) -> Any:  # pragma: no cover
            raise AssertionError

        def fence(self, version: int) -> int:  # pragma: no cover
            return version

    async def go() -> None:
        async with apersisted(MemoryStore(), "k", machine(), lock=Custom()):
            pass  # pragma: no cover

    with pytest.raises(NotSupportedError):
        asyncio.run(go())


def test_p02_builtin_strategies_still_work() -> None:
    async def go() -> None:
        async with apersisted(
            MemoryStore(), "k", machine(), lock=OptimisticLock()
        ) as o:
            await o.send("CREDIT")

    asyncio.run(go())


# -- P-03 / P-22 / P-23 ------------------------------------------------------
def _plugin(**kw: Any) -> IdempotencyPlugin:
    kw.setdefault("principal", lambda e: "alice")
    return IdempotencyPlugin(MemoryInbox(), **kw)


def _send_keyed(plugin: IdempotencyPlugin, payload: Any) -> Any:
    interp = SyncInterpreter(machine()).use(plugin).start()
    return interp, interp.send("CREDIT", wait=True, **payload)


def test_p03_raising_principal_refuses_instead_of_admitting() -> None:
    plugin = _plugin(principal=lambda e: e.payload["user"])  # KeyError
    interp, receipt = _send_keyed(plugin, {"id": "k1"})
    assert interp.context["credits"] == 0
    assert receipt.duplicate is True and receipt.error is not None


def test_p03_raising_key_fn_refuses() -> None:
    def bad_key(event: Any) -> str:
        raise RuntimeError("nope")

    plugin = _plugin(key=bad_key)
    interp, receipt = _send_keyed(plugin, {"amount": 1})
    assert interp.context["credits"] == 0
    assert receipt.error is not None


def test_p03_raising_instance_key_refuses() -> None:
    def bad(interp: Any) -> str:
        raise AttributeError("x")

    plugin = _plugin(instance_key=bad)
    interp, receipt = _send_keyed(plugin, {"id": "k1"})
    assert interp.context["credits"] == 0
    assert receipt.error is not None


def test_p22_address_repr_payload_is_refused_not_fingerprinted() -> None:
    class Foo:
        pass

    ev = type("E", (), {"type": "X", "payload": {"obj": Foo()}})()
    with pytest.raises(TypeError):
        fingerprint(ev)
    # stable text forms are still fine
    from decimal import Decimal

    ev2 = type("E", (), {"type": "X", "payload": {"n": Decimal("1.5")}})()
    assert fingerprint(ev2) == fingerprint(ev2)


def test_p22_default_key_ignores_non_dict_payload() -> None:
    ev = type("E", (), {"type": "X", "payload": [1, 2]})()
    assert default_key(ev) is None


def test_p23_flush_marks_attempts_every_mark() -> None:
    from src.xstate_statemachine.persistence.idempotency import (
        _session_token,
    )

    plugin = _plugin()
    marks: List[str] = []
    real = plugin._mark

    def flaky(scope: str, key: str, fp: str, payload: Any) -> None:
        marks.append(key)
        if key == "a":
            raise StoreError("inbox down")
        real(scope, key, fp, payload)

    plugin._mark = flaky  # type: ignore[method-assign]
    with plugin._lock:
        plugin._buffered[_session_token()] = [
            ("s", "a", "f", None),
            ("s", "b", "f", None),
        ]
    with pytest.raises(StoreError):
        plugin.flush_marks()
    assert marks == ["a", "b"]


# -- P-01 ------------------------------------------------------------------
def test_p01_sqlite_load_is_a_single_snapshot(tmp_path: Any) -> None:
    store = SQLiteStore(tmp_path / "s.db")
    snap = SyncInterpreter(machine()).start().get_snapshot()

    def dl(n: int) -> Any:
        return (Deadline(f"s{n}", n, 1000.0 + n, 1, "after.1.x"),)

    store.save("k", snap, deadlines=dl(1))
    stop = threading.Event()
    errors: List[str] = []

    def writer() -> None:
        w = SQLiteStore(tmp_path / "s.db")
        n = 2
        while not stop.is_set():
            w.save("k", snap, deadlines=dl(n))
            n += 1
        w.close()

    def reader() -> None:
        r = SQLiteStore(tmp_path / "s.db")
        for _ in range(300):
            rec = r.load("k")
            assert rec is not None
            # version v always carries deadline entry_seq v
            if rec.deadlines[0].entry_seq != rec.version:
                errors.append(f"{rec.version} vs {rec.deadlines[0].entry_seq}")
        r.close()

    t = threading.Thread(target=writer)
    t.start()
    try:
        reader()
    finally:
        stop.set()
        t.join()
    assert errors == []


def test_p01_load_reads_record_and_deadlines_in_one_statement(
    tmp_path: Any,
) -> None:
    store = SQLiteStore(tmp_path / "s.db")
    store.save(
        "k",
        SyncInterpreter(machine()).start().get_snapshot(),
        deadlines=(Deadline("s", 1, 1000.0, 1, "after.1.s"),),
    )
    seen: List[str] = []
    store._conn().set_trace_callback(seen.append)
    rec = store.load("k")
    store._conn().set_trace_callback(None)
    assert rec is not None and len(rec.deadlines) == 1
    assert (
        len([x for x in seen if x.lstrip().upper().startswith("SELECT")]) == 1
    )


# -- P-11 / P-12 -------------------------------------------------------------
@pytest.mark.parametrize("mode", ["OFF", "WAL; DROP TABLE x", "memory"])
def test_p11_bad_journal_mode_is_rejected(mode: str) -> None:
    with pytest.raises(ValueError, match="journal_mode"):
        SQLiteStore(":memory:", journal_mode=mode)


@pytest.mark.parametrize("bt", [-1.0, float("nan"), float("inf")])
def test_p11_bad_busy_timeout_is_rejected(bt: float) -> None:
    with pytest.raises(ValueError, match="busy_timeout"):
        SQLiteStore(":memory:", busy_timeout=bt)


def test_p12_unusable_parent_is_a_store_error(tmp_path: Any) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(StoreError):
        SQLiteStore(blocker / "sub" / "s.db")


def test_p12_close_closes_every_threads_connection(tmp_path: Any) -> None:
    store = SQLiteStore(tmp_path / "s.db")
    conns: List[sqlite3.Connection] = []
    ready, release = threading.Event(), threading.Event()

    def worker() -> None:
        store.load("k")
        conns.append(store._local.conn)
        ready.set()
        release.wait(5)

    t = threading.Thread(target=worker)
    t.start()
    ready.wait(5)
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        conns[0].execute("SELECT 1")
    release.set()
    t.join()
    assert store.load("k") is None  # lazily re-opens, as before


# -- P-13 --------------------------------------------------------------------
def test_p13_sqlite_inbox_errors_are_typed(tmp_path: Any) -> None:
    inbox = SQLiteInbox(tmp_path / "i.db")
    conn = inbox._conn()
    conn.execute("DROP TABLE inbox")
    with pytest.raises(StoreError):
        inbox.get("s", "k")
    with pytest.raises(StoreError):
        inbox.claim("s", "k", "fp", ttl_s=None)
    inbox.close()


# -- P-06 / P-07 / P-08 / P-10 ----------------------------------------------
def test_p06_mkstemp_failure_is_a_store_error(
    tmp_path: Any, monkeypatch: Any
) -> None:
    store = FileStore(tmp_path / "d")
    import tempfile

    def boom(*a: Any, **k: Any) -> Any:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(tempfile, "mkstemp", boom)
    with pytest.raises(StoreError):
        store.save("k", "{}")


def test_p06_delete_oserror_is_a_store_error(
    tmp_path: Any, monkeypatch: Any
) -> None:
    store = FileStore(tmp_path / "d")
    store.save("k", "{}")

    def boom(*a: Any, **k: Any) -> Any:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(os, "unlink", boom)
    with pytest.raises(StoreError):
        store.delete("k")


def test_p06_list_keys_on_vanished_directory(tmp_path: Any) -> None:
    store = FileStore(tmp_path / "d")
    os.rmdir(tmp_path / "d")
    with pytest.raises(StoreUnavailableError):
        store.list_keys()


def test_p07_delete_waits_for_the_key_lock(tmp_path: Any) -> None:
    store = FileStore(tmp_path / "d")
    store.save("k", "{}")
    started, done = threading.Event(), threading.Event()

    def deleter() -> None:
        started.set()
        store.delete("k")
        done.set()

    with store.lock("k", timeout=5):
        t = threading.Thread(target=deleter)
        t.start()
        started.wait(5)
        assert not done.wait(0.3)  # blocked behind our lock
    t.join(5)
    assert done.is_set()
    assert store.load("k") is None


def test_p08_list_keys_skips_names_load_would_reject(tmp_path: Any) -> None:
    store = FileStore(tmp_path / "d")
    store.save("good", "{}")
    d = tmp_path / "d"
    (d / "%2f.xsm.json").write_text("{}")
    (d / "Order.xsm.json").write_text("{}")
    assert store.list_keys() == ["good"]
    assert [k for k, _ in store.list_versions()] == ["good"]


def test_p10_directory_is_fsynced_after_replace(
    tmp_path: Any, monkeypatch: Any
) -> None:
    if os.name != "posix":
        pytest.skip("directory fsync is POSIX-only")
    store = FileStore(tmp_path / "d")
    synced: List[int] = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (synced.append(fd), real(fd)))
    store.save("k", "{}")
    assert len(synced) == 2  # the file, then the directory


# -- P-09 ------------------------------------------------------------------
def test_p09_forget_keeps_a_held_lock() -> None:
    m = MemoryStore()
    with m.lock("k"):
        m.forget("k")
        with pytest.raises(StoreError):
            with m.lock("k", timeout=0.1):
                pass  # pragma: no cover


# -- P-15 ------------------------------------------------------------------
def test_p15_scanner_last_result_and_lock_validation() -> None:
    scanner = DueTimerScanner(MemoryStore(), lambda k: machine())
    assert scanner.last_result is None
    with pytest.raises(ValueError):
        DueTimerScanner(
            MemoryStore(), lambda k: machine(), lock=OptimisticLock
        )
    with pytest.raises(ValueError):
        scanner.run_forever(0)


# -- P-19 ------------------------------------------------------------------
def test_p19_dropped_event_is_forgotten_by_the_log_plugin() -> None:
    from src.xstate_statemachine.persistence.log import (
        MemoryLog,
        TransitionLogPlugin,
    )

    plugin = TransitionLogPlugin(MemoryLog())
    interp = SyncInterpreter(machine()).use(plugin).start()
    interp.stop()
    interp.send("CREDIT")  # dropped: not running
    assert not any(plugin._external.values())


# -- P-21 ------------------------------------------------------------------
def test_p21_adopt_refuses_non_json_context() -> None:
    from decimal import Decimal

    from src.xstate_statemachine.persistence.adopt import from_state_ids

    with pytest.raises(InvalidConfigError):
        from_state_ids(
            machine(), ["wallet.open"], context={"credits": Decimal("1.5")}
        )


# -- P-40 ------------------------------------------------------------------
@pytest.mark.parametrize("kind", ["memory", "file", "sqlite"])
def test_p40_list_versions_rejects_negative_limit(
    kind: str, tmp_path: Any
) -> None:
    store: Any = {
        "memory": lambda: MemoryStore(),
        "file": lambda: FileStore(tmp_path / "d"),
        "sqlite": lambda: SQLiteStore(tmp_path / "s.db"),
    }[kind]()
    with pytest.raises(ValueError):
        store.list_versions(limit=-1)
