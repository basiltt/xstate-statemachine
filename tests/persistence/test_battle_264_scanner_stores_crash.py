# tests/persistence/test_battle_264_scanner_stores_crash.py
"""#264 battle (agent B): the stores' deadline index, scale, crash
consistency, Django ``xsm_deadlines`` and the Starlette scanner thread.

* every store round-trips ``deadlines`` exactly and clears them;
* SQLite leaves no orphan ``deadlines`` rows after ``delete``/``forget``;
* every indexed ``due_keys`` agrees with the stdlib fallback;
* ``due_keys`` scale on 100 000 records (indexed SQLite / Memory);
* kill -9 of a scanning process before / after the fire-save;
* the inbox and a timer event (what it can and cannot do);
* Django: command, 4 threads exactly-once, v1 rows under a v2 model;
* Starlette ``run_timers``: no thread leak, two apps on one store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine import (
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import (
    Deadline,
    DueTimerScanner,
    FileStore,
    MemoryStore,
    PessimisticLock,
    SQLiteStore,
    persisted,
)

pytestmark = pytest.mark.timeout(300)

ROOT = Path(__file__).resolve().parents[2]
CFG: Dict[str, Any] = {
    "id": "t",
    "initial": "w",
    "states": {"w": {"after": {"1000": "d"}}, "d": {}},
}


def _blob() -> Any:
    i = SyncInterpreter(
        create_machine(CFG), clock=SimulatedClock(wall_start=0)
    ).start()
    out = (i.get_snapshot(), i.pending_deadlines()[0])
    i.stop()
    return out


def _dl(due: float, seq: int = 1, ev: str = "after.1000.t.w") -> Deadline:
    return Deadline("t.w", seq, due, 1000, ev)


def _stores(tmp_path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "memory": MemoryStore(),
        "file": FileStore(tmp_path / "fs"),
        "sqlite": SQLiteStore(tmp_path / "s.db"),
    }
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

        out["sqlalchemy"] = SQLAlchemyStore(
            sessionmaker(create_engine(f"sqlite:///{tmp_path / 'sa.db'}"))
        )
    except ImportError:  # pragma: no cover - extra missing
        pass
    try:
        import fakeredis

        from src.xstate_statemachine.contrib.redis import RedisStore

        out["redis"] = RedisStore(fakeredis.FakeRedis(), prefix="b264")
    except ImportError:  # pragma: no cover - extra missing
        pass
    return out


# -----------------------------------------------------------------------------
# 7. deadline index parity
# -----------------------------------------------------------------------------
class TestIndexParity:
    def test_round_trip_clear_and_due_keys_agree(self, tmp_path: Path) -> None:
        blob, _ = _blob()
        weird = [
            _dl(1.000000123456789, 7, "after.1000.t.w.ünï😀"),
            _dl(1e10 + 0.25, 2**40),
        ]
        orders: Dict[str, Any] = {}
        for name, st in _stores(tmp_path).items():
            # round trip: precision, big entry_seq, unicode event type
            st.save("k-a", blob, deadlines=weird)
            got = st.load("k-a").deadlines
            assert sorted(got, key=lambda d: d.due_at_wall) == weird, name
            # 1 000 deadlines on one key
            many = [_dl(100.0 + i, i + 1) for i in range(1000)]
            st.save("k-b", blob, deadlines=many)
            assert len(st.load("k-b").deadlines) == 1000, name
            st.save("k-c", blob, deadlines=[_dl(50.0)])
            st.save("k-d", blob, deadlines=[_dl(9e9)])
            sc = DueTimerScanner(st, lambda k: None)
            orders[name] = sc.due_keys(200.0)
            # clearing
            st.save("k-b", blob, deadlines=())
            assert st.load("k-b").deadlines == (), name
            assert "k-b" not in dict(sc.due_keys(200.0)), name
        expected = [("k-a", 1.000000123456789), ("k-c", 50.0)]
        for name, rows in orders.items():
            assert rows[:2] == expected, (name, rows[:3])
            assert [k for k, _ in rows] == ["k-a", "k-c", "k-b"], name

    def test_sqlite_delete_and_forget_leave_no_orphan_rows(
        self, tmp_path: Path
    ) -> None:
        st = SQLiteStore(tmp_path / "s.db")
        blob, _ = _blob()
        for k in ("a", "b"):
            st.save(k, blob, deadlines=[_dl(1.0), _dl(2.0, 2)])
        st.delete("a")
        st.forget("b")
        n = st._conn().execute("SELECT COUNT(*) FROM deadlines").fetchone()
        assert n[0] == 0
        assert st.due_keys(1e12) == []

    def test_redis_ttl_expiry_prunes_zset_member(self) -> None:
        """Redis ``ttl_s``: the snapshot + deadline hashes expire, the
        ``deadlines`` zset member cannot. #306 battle: `due_keys` used to
        keep returning such orphans every tick (and, ``limit`` of them,
        starved live keys); it now prunes them and reports nothing. The
        scanner never fires a key whose record is gone."""
        fakeredis = pytest.importorskip("fakeredis")
        from src.xstate_statemachine.contrib.redis import RedisStore

        r = fakeredis.FakeRedis()
        st = RedisStore(r, prefix="ttl264", ttl_s=60)
        blob, dl = _blob()
        st.save("k", blob, deadlines=[dl])
        # The TTL elapses: Redis drops both hashes, not the zset member.
        r.delete(st.k.snap("k"), st.k.dl("k"))
        assert st.load("k") is None
        assert st.due_keys(10.0) == []
        assert r.zcard(st.k.deadlines) == 0
        res = DueTimerScanner(st, lambda k: create_machine(CFG)).scan(10.0)
        assert (res.woken, res.skipped_stale, res.errors) == (0, 0, [])

    def test_redis_save_is_atomic_so_index_cannot_diverge(self) -> None:
        """The hash and the zset are written by ONE Lua script: a failing
        script call writes neither (no torn index)."""
        fakeredis = pytest.importorskip("fakeredis")
        from src.xstate_statemachine.contrib.redis import RedisStore

        st = RedisStore(fakeredis.FakeRedis(), prefix="atomic264")
        blob, dl = _blob()
        st.save("k", blob, deadlines=[dl])

        def boom(*a: Any, **k: Any) -> Any:
            raise ConnectionError("network partition")

        st._save = boom  # type: ignore[assignment]
        with pytest.raises(Exception):
            st.save("k", blob, deadlines=[_dl(1e9)])
        assert st.due_keys(10.0) == [("k", dl.due_at_wall)]
        assert st.load("k").deadlines == (dl,)


# -----------------------------------------------------------------------------
# 2. scale
# -----------------------------------------------------------------------------
class TestScale:
    @pytest.mark.parametrize("kind", ["sqlite", "memory"])
    def test_100k_records_100_due_without_loading_any(
        self, tmp_path: Path, kind: str
    ) -> None:
        st = (
            SQLiteStore(tmp_path / "s.db")
            if kind == "sqlite"
            else MemoryStore()
        )
        blob, dl = _blob()
        late = _dl(1e12)
        if kind == "sqlite":
            st._conn().execute("BEGIN")
        for i in range(100_000):
            st.save(
                f"t{i:06d}", blob, deadlines=(dl if i % 1000 == 0 else late,)
            )
        if kind == "sqlite":
            st._conn().execute("COMMIT")
        loads = {"n": 0}
        real = st.load

        def load(key: str) -> Any:
            loads["n"] += 1
            return real(key)

        st.load = load  # type: ignore[method-assign]
        sc = DueTimerScanner(st, lambda k: None)
        t0 = time.perf_counter()
        due = sc.due_keys(10.0)
        took = time.perf_counter() - t0
        assert len(due) == 100 and loads["n"] == 0
        assert took < 0.5, took

    def test_file_store_fallback_is_linear_and_documented(
        self, tmp_path: Path
    ) -> None:
        """DOCUMENTED: FileStore has no index; `due_keys` loads EVERY
        record (measured ~2.4 ms/record on Windows NTFS -> ~4 min per tick
        at 100 000 records). Use SQLite/SQLAlchemy/Redis for a scanned
        store beyond a few thousand records."""
        st = FileStore(tmp_path / "fs")
        blob, dl = _blob()
        for i in range(200):
            st.save(f"t{i:03d}", blob, deadlines=(dl if i < 2 else _dl(1e12),))
        loads = {"n": 0}
        real = st.load

        def load(key: str) -> Any:
            loads["n"] += 1
            return real(key)

        st.load = load  # type: ignore[method-assign]
        sc = DueTimerScanner(st, lambda k: None, limit=1)
        assert len(sc.due_keys(10.0)) == 1
        assert loads["n"] == 200  # every record, not `limit`


# -----------------------------------------------------------------------------
# 4. crash consistency
# -----------------------------------------------------------------------------
KILL_CHILD = r"""
import json, os, sys
sys.path.insert(0, sys.argv[2])
from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import (
    DueTimerScanner, FileStore, PessimisticLock, SQLiteStore)
a = json.loads(sys.argv[1])
store = SQLiteStore(a["path"]) if a["kind"] == "sqlite" else FileStore(a["path"])
def effect(i, c, e, ac):
    with open(a["effects"], "a") as fh:
        fh.write("fired\n")
m = create_machine(a["cfg"], logic=MachineLogic(actions={"effect": effect}))
real = store.save
def save(*args, **kw):
    if a["point"] == "before_save":
        os._exit(9)
    real(*args, **kw)
    os._exit(9)  # after_save: before the lock is released
store.save = save
DueTimerScanner(store, lambda k: m, lock=PessimisticLock(timeout=5)).scan(10.0)
sys.exit(3)
"""

CRASH_CFG = {
    "id": "t",
    "initial": "w",
    "states": {
        "w": {"after": {"1000": {"target": "d", "actions": "effect"}}},
        "d": {},
    },
}


class TestKill9:
    @pytest.mark.parametrize("point", ["before_save", "after_save"])
    @pytest.mark.parametrize("kind", ["sqlite", "file"])
    def test_kill_during_wake(
        self, tmp_path: Path, kind: str, point: str
    ) -> None:
        from src.xstate_statemachine import MachineLogic

        path = str(tmp_path / ("s.db" if kind == "sqlite" else "fs"))
        effects = tmp_path / "effects.txt"
        effects.write_text("")
        store = (
            SQLiteStore(path)
            if kind == "sqlite"
            else FileStore(path, stale_lock_after=0.5)
        )
        logic = MachineLogic(
            actions={
                "effect": lambda i, c, e, a: effects.open("a").write("fired\n")
            }
        )
        m = create_machine(CRASH_CFG, logic=logic)
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        args = json.dumps(
            {
                "path": path,
                "kind": kind,
                "point": point,
                "cfg": CRASH_CFG,
                "effects": str(effects),
            }
        )
        p = subprocess.run(
            [sys.executable, "-c", KILL_CHILD, args, str(ROOT)],
            cwd=str(ROOT),
            capture_output=True,
            timeout=120,
        )
        assert p.returncode == 9, p.stderr.decode(errors="replace")[-2000:]
        if kind == "file":
            time.sleep(0.6)  # the dead holder's lock file goes stale
        # never torn: the record loads and is either v1 (armed) or v2 (fired)
        rec = (SQLiteStore(path) if kind == "sqlite" else store).load("k")
        assert rec is not None and rec.version in (1, 2)
        res = DueTimerScanner(
            SQLiteStore(path) if kind == "sqlite" else store,
            lambda k: m,
            lock=PessimisticLock(timeout=5),
        ).scan(10.0)
        assert res.errors == []
        final = (SQLiteStore(path) if kind == "sqlite" else store).load("k")
        assert final.version == 2 and final.deadlines == ()
        side_effects = effects.read_text().count("fired")
        committed_by_child = rec.version == 2
        # 📝 SQLite + Pessimistic: the save joins the lock's BEGIN
        #    IMMEDIATE, so a kill AFTER the save but BEFORE release rolls
        #    it back -- (b) behaves like (a): re-fired by the parent.
        #    FileStore: the atomic rename is durable at once, so (b) is
        #    committed and the parent has nothing to do.
        assert committed_by_child == (kind == "file" and point == "after_save")
        assert res.woken == (0 if committed_by_child else 1)
        # at-least-once: the action ran in the child AND (unless the
        # child's save survived) again in the parent.
        assert side_effects == (1 if committed_by_child else 2)

    def test_inbox_cannot_dedupe_a_timer_event(self) -> None:
        """DOCUMENTED: `IdempotencyPlugin`'s default key reads
        ``payload["idempotency_key"]`` / ``payload["id"]``; an ``after``
        event has no payload, so the key is ``None`` and the event is NOT
        deduplicated. Pairing the scanner with the inbox protects the
        events YOUR timer action sends onwards (give them a key derived
        from ``(store_key, entry_seq)``), not the re-fire itself; the
        re-fire window is closed only by making the transition
        idempotent or by `PessimisticLock` on a transactional store."""
        from src.xstate_statemachine.events import Event
        from src.xstate_statemachine.persistence import (
            IdempotencyPlugin,
            MemoryInbox,
        )
        from src.xstate_statemachine.persistence.idempotency import (
            default_key,
        )

        # Arrange: the key the plugin derives for a timer event
        assert default_key(Event("after.1000.t.w", {})) is None
        inbox = MemoryInbox()
        store = MemoryStore()
        m = create_machine(CFG)
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        claims: List[Any] = []
        real_claim = inbox.claim
        inbox.claim = lambda *a, **k: (  # type: ignore[method-assign]
            claims.append(a) or real_claim(*a, **k)
        )
        plug = IdempotencyPlugin(inbox, principal=lambda e: "system")
        # Act: a wake with the inbox attached
        r = DueTimerScanner(store, lambda k: m, plugins=[plug]).scan(10.0)
        # Assert: it fires, and nothing was claimed for the timer event
        assert r.woken == 1 and r.errors == []
        assert claims == []


# -----------------------------------------------------------------------------
# 5. disk full during the fire-save
# -----------------------------------------------------------------------------
def test_disk_full_on_fire_save_keeps_old_record_and_retries(
    tmp_path: Path,
) -> None:
    import errno

    st = FileStore(tmp_path / "fs")
    m = create_machine(CFG)
    with persisted(st, "k", m, clock=SimulatedClock(wall_start=0)):
        pass
    real = st._write_atomic

    def full(*a: Any, **k: Any) -> Any:
        raise OSError(errno.ENOSPC, "No space left on device")

    st._write_atomic = full  # type: ignore[method-assign]
    r = DueTimerScanner(st, lambda k: m).scan(10.0)
    assert r.woken == 0 and [k for k, _ in r.errors] == ["k"]
    rec = st.load("k")
    assert rec.version == 1 and len(rec.deadlines) == 1
    st._write_atomic = real  # type: ignore[method-assign]
    assert DueTimerScanner(st, lambda k: m).run_once(now=10.0) == 1


# -----------------------------------------------------------------------------
# 9. Starlette registry run_timers
# -----------------------------------------------------------------------------
class TestStarletteScanner:
    def _reg(self, store: Any, now: Any) -> Any:
        pytest.importorskip("starlette")
        from src.xstate_statemachine.contrib.starlette import (
            StatechartRegistry,
            allow_all,
        )

        reg = StatechartRegistry(
            store, run_timers=True, scanner_interval_s=0.02, scanner_now=now
        )
        reg.register("t", create_machine(CFG), authorize=allow_all)
        return reg

    def test_fifty_start_stops_leak_no_thread(self) -> None:
        pytest.importorskip("starlette")
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        store = MemoryStore()
        before = None
        for n in range(50):
            reg = self._reg(store, time.time)
            app = Starlette(lifespan=reg.lifespan)
            t0 = time.monotonic()
            with TestClient(app):
                assert reg.scanner is not None
            assert time.monotonic() - t0 < 5
            assert reg.scanner is None
            if n == 4:
                before = threading.active_count()
        assert threading.active_count() <= (before or 0)
        assert not any(
            t.name == "xsm-timer-scanner" for t in threading.enumerate()
        )

    def test_two_apps_one_store_fire_exactly_once(
        self, tmp_path: Path
    ) -> None:
        """Two "schedulers" on one store (the docs say run exactly one):
        the version fence still commits each timer exactly once -- so
        "exactly one scheduler" is an operational recommendation (less
        wasted work), not a correctness requirement."""
        pytest.importorskip("starlette")
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        path = tmp_path / "s.db"
        seed = SQLiteStore(path)
        blob, dl = _blob()
        for i in range(200):
            seed.save(f"t.{i}", blob, deadlines=[dl])
        later = lambda: time.time() + 3600  # noqa: E731
        regs = [self._reg(SQLiteStore(path), later) for _ in range(2)]
        apps = [Starlette(lifespan=r.lifespan) for r in regs]
        with TestClient(apps[0]), TestClient(apps[1]):
            end = time.monotonic() + 30
            while time.monotonic() < end:
                if all(not seed.load(f"t.{i}").deadlines for i in range(200)):
                    break
                time.sleep(0.05)
            scanners = [r.scanner for r in regs]
        assert {seed.load(f"t.{i}").version for i in range(200)} == {2}
        for s in scanners:
            assert s.last_result.errors == []


# -----------------------------------------------------------------------------
# 11. stress (opt-in)
# -----------------------------------------------------------------------------
@pytest.mark.stress
@pytest.mark.skipif(not os.environ.get("XSM_STRESS"), reason="XSM_STRESS=1")
@pytest.mark.timeout(600)
def test_stress_1000_instances_one_second_timers_60s(tmp_path: Path) -> None:
    import psutil

    st = SQLiteStore(tmp_path / "s.db")
    m = create_machine(
        {
            "id": "s",
            "initial": "a",
            "states": {
                "a": {"after": {"1000": "b"}},
                "b": {"after": {"1000": "a"}},
            },
        }
    )
    for i in range(1000):
        with persisted(st, f"s{i}", m):
            pass
    lags: List[float] = []
    sc = DueTimerScanner(st, lambda k: m, limit=10_000)
    real_scan = sc.scan

    def scan(now: Any = None) -> Any:
        r = real_scan(now)
        assert r.errors == [], r.errors[:3]
        if r.woken:
            lags.append(r.max_lag_s)
        return r

    sc.scan = scan  # type: ignore[method-assign]
    t = threading.Thread(target=sc.run_forever, args=(0.1,), daemon=True)
    t.start()
    time.sleep(60)
    sc.stop()
    t.join(5)
    versions = [st.load(f"s{i}").version for i in range(1000)]
    lags.sort()
    p99 = lags[int(len(lags) * 0.99)] if lags else 0.0
    rss = psutil.Process().memory_info().rss / 2**20
    print(
        f"\nfires={sum(versions) - 1000} p99_lag={p99:.3f}s rss={rss:.0f}MiB"
    )
    assert min(versions) >= 30  # ~1 fire/s/instance at least half the time
