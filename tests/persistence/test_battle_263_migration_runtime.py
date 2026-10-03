# tests/persistence/test_battle_263_migration_runtime.py
"""Battle test #263 part A (2/2): migration at RUNTIME.

`persisted` / `apersisted` with a migrator under every lock strategy and
contention, `DueTimerScanner` on a stale instance, leaks, the
once-per-machine "unlabelled" warning, and a mid-flight async snapshot
migrated and resumed on the SYNC engine.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import tracemalloc
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine import base_interpreter as bi
from src.xstate_statemachine.exceptions import ConflictError
from src.xstate_statemachine.persistence import (
    DueTimerScanner,
    MachineVersionMismatchError,
    MemoryStore,
    NoLock,
    OptimisticLock,
    PessimisticLock,
    SnapshotMigrator,
    apersisted,
    persisted,
)

JOIN_S = 30.0

V1: Dict[str, Any] = {
    "id": "o",
    "version": "1.0",
    "initial": "paying",
    "states": {"paying": {"on": {"OK": "done"}}, "done": {"type": "final"}},
}
V2: Dict[str, Any] = {
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


class CountingMigrator:
    """A 1.0 -> 2.0 migrator that counts step invocations (thread-safe)."""

    def __init__(self, fail: bool = False) -> None:
        self.calls = 0
        self._lock = threading.Lock()
        self.fail = fail
        self.mig = SnapshotMigrator()
        self.mig.add("1.0", "2.0", self._step)

    def _step(self, b: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self.calls += 1
        if self.fail:
            raise RuntimeError("step bug")
        b["state_ids"] = ["o.payment.card"]
        return b


def _seed(store: MemoryStore, keys: List[str]) -> None:
    for k in keys:
        with persisted(store, k, create_machine(V1)):
            pass


# -----------------------------------------------------------------------------
# 7. persisted() / apersisted() under contention
# -----------------------------------------------------------------------------
LOCKS = {
    "optimistic0": lambda: OptimisticLock(retries=0),
    "pessimistic": lambda: PessimisticLock(timeout=JOIN_S),
    "nolock": lambda: NoLock(),
}


class TestPersistedContention:
    @pytest.mark.parametrize("lock_name", sorted(LOCKS))
    def test_sixteen_threads_one_stale_key(self, lock_name: str) -> None:
        # Arrange
        store = MemoryStore()
        _seed(store, ["k"])
        v0 = store.load("k").version
        cm = CountingMigrator()
        m2 = create_machine(V2)
        lock = LOCKS[lock_name]()
        ok: List[int] = []
        errors: List[BaseException] = []
        barrier = threading.Barrier(16, timeout=JOIN_S)

        def worker() -> None:
            barrier.wait()
            try:
                with persisted(store, "k", m2, lock=lock, migrator=cm.mig):
                    pass
                ok.append(1)
            except ConflictError:
                pass  # 📝 optimistic loser: the CALLER retries
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        # Act
        ts = [threading.Thread(target=worker) for _ in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(JOIN_S)

        # Assert
        assert not any(t.is_alive() for t in ts), "hang"
        assert errors == []
        rec = store.load("k")
        assert rec.machine_version == "2.0"
        assert 1 <= cm.calls <= 16
        assert rec.version - v0 == len(ok) >= 1
        if lock_name == "pessimistic":
            # 🏛️ Serialised: only the FIRST holder saw a 1.0 blob.
            assert cm.calls == 1 and len(ok) == 16

    @pytest.mark.parametrize("lock_name", sorted(LOCKS))
    def test_fifty_tasks_one_stale_key_async(self, lock_name: str) -> None:
        store = MemoryStore()
        _seed(store, ["k"])
        v0 = store.load("k").version
        cm = CountingMigrator()
        m2 = create_machine(V2)
        lock = LOCKS[lock_name]()

        async def one() -> bool:
            try:
                async with apersisted(
                    store, "k", m2, lock=lock, migrator=cm.mig
                ):
                    await asyncio.sleep(0)
                return True
            except ConflictError:
                return False

        async def go() -> List[bool]:
            return await asyncio.wait_for(
                asyncio.gather(*(one() for _ in range(50))), JOIN_S
            )

        ok = sum(asyncio.run(go()))
        rec = store.load("k")
        assert rec.machine_version == "2.0"
        assert 1 <= cm.calls <= 50
        assert rec.version - v0 == ok >= 1

    def test_two_hundred_stale_keys_eight_workers(self) -> None:
        store = MemoryStore()
        keys = [f"o-{n}" for n in range(200)]
        _seed(store, keys)
        cm = CountingMigrator()
        m2 = create_machine(V2)
        lock = OptimisticLock(retries=0)
        errors: List[BaseException] = []

        def worker(part: List[str]) -> None:
            for k in part:
                try:
                    with persisted(store, k, m2, lock=lock, migrator=cm.mig):
                        pass
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

        ts = [
            threading.Thread(target=worker, args=(keys[n::8],))
            for n in range(8)
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join(JOIN_S)
        assert errors == [] and cm.calls == 200
        assert {store.load(k).machine_version for k in keys} == {"2.0"}

    @pytest.mark.parametrize("lock_name", sorted(LOCKS))
    def test_raising_step_leaves_record_untouched(
        self, lock_name: str
    ) -> None:
        store = MemoryStore()
        _seed(store, ["k"])
        before = store.load("k")
        cm = CountingMigrator(fail=True)
        with pytest.raises(Exception) as ei:
            with persisted(
                store,
                "k",
                create_machine(V2),
                lock=LOCKS[lock_name](),
                migrator=cm.mig,
            ):
                pass
        assert "step bug" in str(ei.value)
        after = store.load("k")
        assert (after.machine_version, after.version) == (
            "1.0",
            before.version,
        )
        assert after.snapshot == before.snapshot


# -----------------------------------------------------------------------------
# 8. DueTimerScanner on a stale instance
# -----------------------------------------------------------------------------
T1: Dict[str, Any] = {
    "id": "t",
    "version": "1",
    "initial": "wait",
    "states": {
        "wait": {"after": {"1000": "late"}},
        "late": {},
    },
}
T2: Dict[str, Any] = {
    "id": "t",
    "version": "2",
    "initial": "pending",
    "states": {
        "pending": {"after": {"1000": "overdue"}},
        "overdue": {},
    },
}


def _rename_timer(b: Dict[str, Any]) -> Dict[str, Any]:
    b["state_ids"] = ["t.pending"]
    b["deadlines"] = [
        {**d, "state_id": "t.pending", "event_type": "after.1000.t.pending"}
        for d in b["deadlines"]
    ]
    return b


def _stale_store() -> MemoryStore:
    store = MemoryStore()
    with persisted(
        store, "t1", create_machine(T1), clock=SimulatedClock(wall_start=0)
    ):
        pass
    return store


class TestScannerStale:
    def test_no_migrator_reports_typed_error_and_keeps_deadline(
        self,
    ) -> None:
        store = _stale_store()
        sc = DueTimerScanner(store, lambda k: create_machine(T2))
        for _ in range(3):  # 📝 no hot loop: one error per pass, no wake
            res = sc.scan(now=10.0)
            assert res.woken == 0 and len(res.errors) == 1
            assert isinstance(res.errors[0][1], MachineVersionMismatchError)
        rec = store.load("t1")
        assert rec.machine_version == "1" and rec.deadlines

    def test_with_migrator_fires_and_resaves_at_new_label(self) -> None:
        store = _stale_store()
        mig = SnapshotMigrator()
        mig.add("1", "2", _rename_timer)
        sc = DueTimerScanner(store, lambda k: create_machine(T2), migrator=mig)
        res = sc.scan(now=10.0)
        assert (res.woken, res.errors) == (1, [])
        rec = store.load("t1")
        assert rec.machine_version == "2"
        assert json.loads(rec.snapshot)["state_ids"] == ["t.overdue"]
        assert sc.scan(now=20.0).woken == 0


# -----------------------------------------------------------------------------
# 10. Leaks and log volume
# -----------------------------------------------------------------------------
def _big_blob(n: int = 50) -> Dict[str, Any]:
    states = {f"s{k}": {"on": {"N": f"s{(k + 1) % n}"}} for k in range(n)}
    cfg = {"id": "b", "version": "1", "initial": "s0", "states": states}
    i = SyncInterpreter(create_machine(cfg)).start()
    try:
        return json.loads(i.get_snapshot())
    finally:
        i.stop()


class TestLeaks:
    def test_ten_thousand_three_hop_migrations_bounded(self) -> None:
        mig = SnapshotMigrator()
        for f, t in (("1", "2"), ("2", "3"), ("3", "4")):
            mig.add(f, t, lambda b: {**b, "state_ids": ["b.s1"]})
        blob = _big_blob()
        n = 10_000
        tracemalloc.start()
        try:
            for k in range(n):
                mig.migrate(blob, "4", machine_id="b")
                if k == n // 2:
                    mid = tracemalloc.take_snapshot()
            end = tracemalloc.take_snapshot()
        finally:
            tracemalloc.stop()
        growth = sum(s.size_diff for s in end.compare_to(mid, "filename"))
        assert growth < 64 * 1024, growth

    def test_pending_actor_snapshots_do_not_accumulate(self) -> None:
        raw = json.loads(
            SyncInterpreter(create_machine(V1)).start().get_snapshot()
        )
        raw["actors"] = {"k": {"src": "missing", "snapshot": dict(raw)}}
        blob = json.dumps(raw)
        sizes = {
            len(
                SyncInterpreter.from_snapshot(
                    blob, create_machine(V1)
                )._pending_actor_snapshots
            )
            for _ in range(200)
        }
        assert sizes == {1}

    def test_unlabelled_warning_is_once_per_machine(self, caplog: Any) -> None:
        bi._UNLABELLED_WARNED.clear()

        def unlabelled(cfg: Dict[str, Any]) -> str:
            i = SyncInterpreter(create_machine(cfg)).start()
            raw = json.loads(i.get_snapshot())
            i.stop()
            del raw["machine_version"]
            return json.dumps(raw)

        v1b = {**V1, "id": "o2"}
        blob, blob2 = unlabelled(V1), unlabelled(v1b)
        m, other = create_machine(V1), create_machine(v1b)
        with caplog.at_level(logging.WARNING):
            for _ in range(10_000):
                SyncInterpreter.from_snapshot(blob, m)
            SyncInterpreter.from_snapshot(blob2, other)
        hits = [
            r for r in caplog.records if "carries no machine_version" in r.msg
        ]
        assert len(hits) == 2


# -----------------------------------------------------------------------------
# 11. Mid-flight async snapshot -> migrate -> SYNC resume
# -----------------------------------------------------------------------------
A1: Dict[str, Any] = {
    "id": "x",
    "version": "1",
    "initial": "a",
    "context": {"pings": 0},
    "states": {
        "a": {"after": {"5000": "b"}, "on": {"PING": {"actions": "ping"}}},
        "b": {},
    },
}
A2: Dict[str, Any] = {
    "id": "x",
    "version": "2",
    "initial": "wait",
    "context": {"pings": 0},
    "states": {
        "wait": {
            "after": {"5000": "timedOut"},
            "on": {"PING": {"actions": "ping"}},
        },
        "timedOut": {},
    },
}


def _ping(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["pings"] += 1


def test_async_midflight_blob_migrated_resumes_on_sync_engine() -> None:
    from src.xstate_statemachine import MachineLogic

    logic = MachineLogic(actions={"ping": _ping})

    async def snap() -> str:
        clk = SimulatedClock(wall_start=100.0)
        i = await Interpreter(
            create_machine(A1, logic=logic), clock=clk
        ).start()
        i.send("PING")  # 📝 queued, not yet processed: a PENDING event
        blob = i.get_snapshot()
        await i.stop()
        return blob

    blob = asyncio.run(snap())
    raw = json.loads(blob)
    assert raw["pending_events"] and raw["deadlines"]

    def step(b: Dict[str, Any]) -> Dict[str, Any]:
        b["state_ids"] = ["x.wait"]
        b["deadlines"] = [
            {**d, "state_id": "x.wait", "event_type": "after.5000.x.wait"}
            for d in b["deadlines"]
        ]
        return b

    mig = SnapshotMigrator()
    mig.add("1", "2", step)
    clk = SimulatedClock(wall_start=102.0)
    r = SyncInterpreter.from_snapshot(
        blob,
        create_machine(A2, logic=logic),
        migrator=mig,
        clock=clk,
        restart_timers="resume",
    ).start()
    assert r.context["pings"] == 1  # the pending PING ran after migration
    clk.increment(2999)
    assert r.current_state_ids == {"x.wait"}
    clk.increment(1)
    assert r.current_state_ids == {"x.timedOut"}
    assert json.loads(r.get_snapshot())["machine_version"] == "2"
    r.stop()
