# tests/persistence/test_battle_264_scanner_concurrency.py
"""#264 battle (agent B): `DueTimerScanner` exactly-once under concurrency.

* N scanner THREADS and N scanner PROCESSES racing one store, under
  `OptimisticLock`, `PessimisticLock` and `NoLock`;
* the X0.9 race built deterministically (no sleeps): a web request
  advances the key between `due_keys` and the lock; another scanner fires
  the key between the scanner's re-check and `persisted()`'s own load;
* the normal races (`ConflictError`, `LockTimeoutError`) are
  ``skipped_stale``, never ``errors``;
* ``limit`` wakes the EARLIEST deadlines and drains a backlog.

Exactly-once is asserted twice: per-key fire count from an
``on_transition`` plugin, and the record's ``version`` (1 arm-save + 1
fire-save = 2).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from src.xstate_statemachine import (
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import (
    DueTimerScanner,
    FileStore,
    MemoryStore,
    NoLock,
    OptimisticLock,
    PessimisticLock,
    SQLiteStore,
    persisted,
)

pytestmark = pytest.mark.timeout(300)

ROOT = Path(__file__).resolve().parents[2]
CFG: Dict[str, Any] = {
    "id": "r",
    "initial": "w",
    "states": {
        "w": {"after": {"5000": "d"}, "on": {"CANCEL": "c"}},
        "d": {},
        "c": {},
    },
}
SCAN_AT = 10.0  # every seeded deadline is due at wall 5.0


def _machine() -> Any:
    return create_machine(CFG)


def _seed_blob() -> Tuple[str, tuple]:
    i = SyncInterpreter(_machine(), clock=SimulatedClock(wall_start=0)).start()
    out = (i.get_snapshot(), tuple(i.pending_deadlines()))
    i.stop()
    return out


def _seed(store: Any, n: int, *, stagger: float = 0.0) -> List[str]:
    blob, dls = _seed_blob()
    keys = [f"k{i:05d}" for i in range(n)]
    for idx, k in enumerate(keys):
        d = tuple(
            type(x)(
                x.state_id,
                x.entry_seq,
                x.due_at_wall + idx * stagger,
                x.delay_ms,
                x.event_type,
            )
            for x in dls
        )
        store.save(k, blob, deadlines=d)
    return keys


class FireCounter(PluginBase):
    """Counts timer transitions per store key (thread-safe).

    ``fires`` = COMMITTED fires: buffered per thread and counted only when
    `persisted()` calls ``flush_marks`` (after the save won) -- the same
    hook the inbox and outbox use. ``attempts`` = every in-memory fire,
    including a racer whose versioned save was then refused.
    """

    def __init__(self) -> None:
        self.fires: Counter = Counter()
        self.attempts: Counter = Counter()
        self._lk = threading.Lock()
        self._buf = threading.local()

    def _pending(self) -> List[str]:
        if not hasattr(self._buf, "keys"):
            self._buf.keys = []
        return self._buf.keys  # type: ignore[no-any-return]

    def on_transition(self, i: Any, f: Any, t: Any, tr: Any) -> None:
        if str(tr.event).startswith("after."):
            self._pending().append(i.store_key)
            with self._lk:
                self.attempts[i.store_key] += 1

    def flush_marks(self) -> None:
        with self._lk:
            self.fires.update(self._pending())
        self._buf.keys = []

    def discard_marks(self) -> None:
        self._buf.keys = []


def _race(store_for: Any, lock: Any, n_threads: int, n_keys: int) -> Any:
    plugin = FireCounter()
    results: List[Any] = []
    gate = threading.Barrier(n_threads)

    def worker() -> None:
        sc = DueTimerScanner(
            store_for(), lambda k: _machine(), lock=lock, plugins=[plugin]
        )
        sc.limit = n_keys
        gate.wait(30)
        results.append(sc.scan(SCAN_AT))

    ts = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(240)
    assert not any(t.is_alive() for t in ts), "a scanner thread hung"
    return plugin, results


# -----------------------------------------------------------------------------
# 1. exactly-once, threads
# -----------------------------------------------------------------------------
class TestExactlyOnceThreads:
    @pytest.mark.parametrize("lock_name", ["optimistic", "pessimistic"])
    @pytest.mark.parametrize(
        "kind,n_keys", [("memory", 10_000), ("sqlite", 3_000), ("file", 200)]
    )
    def test_eight_scanners_fire_every_key_exactly_once(
        self, tmp_path: Path, kind: str, n_keys: int, lock_name: str
    ) -> None:
        # Arrange
        shared = MemoryStore()

        def store_for() -> Any:
            if kind == "sqlite":
                return SQLiteStore(tmp_path / "s.db", busy_timeout=60)
            if kind == "file":
                return FileStore(tmp_path / "fs")
            return shared

        keys = _seed(store_for(), n_keys)
        lock = (
            OptimisticLock()
            if lock_name == "optimistic"
            else PessimisticLock(timeout=60)
        )
        # Act
        plugin, results = _race(store_for, lock, 8, n_keys)
        # Assert
        errors = [e for r in results for e in r.errors]
        assert errors == []
        assert sum(r.woken for r in results) == n_keys
        assert set(plugin.fires.values()) == {1}
        assert len(plugin.fires) == n_keys
        check = store_for()
        assert {check.load(k).version for k in keys} == {2}
        assert all(check.load(k).deadlines == () for k in keys)
        # Every non-winning sighting of a due key is a stale skip.
        assert all(
            r.due == r.woken + r.skipped_stale + len(r.errors) for r in results
        )
        # 📝 DOCUMENTED: under OptimisticLock a racer that loses the save
        #    has already run the transition IN MEMORY (actions included);
        #    only the commit is exactly-once. Pessimistic serialises, so
        #    there attempts == commits.
        extra = sum(plugin.attempts.values()) - n_keys
        if lock_name == "pessimistic":
            assert extra == 0
        print(f"\n{kind}/{lock_name}: {extra} uncommitted in-memory fires")

    def test_nolock_double_fires_and_that_is_documented(
        self, tmp_path: Path
    ) -> None:
        """`NoLock` = "exactly one writer per key". Eight scanners are
        eight writers: double fires are EXPECTED. The count is recorded
        so the documentation's warning is grounded in a number."""
        store = MemoryStore()
        _seed(store, 2_000)
        plugin, results = _race(lambda: store, NoLock(), 8, 2_000)
        assert [e for r in results for e in r.errors] == []
        total = sum(plugin.fires.values())
        assert total >= 2_000  # never fewer than once
        print(f"\nNoLock x8 on 2000 keys: {total} fires")


# -----------------------------------------------------------------------------
# 1b. exactly-once, processes
# -----------------------------------------------------------------------------
PROC_CHILD = r"""
import json, sys
sys.path.insert(0, sys.argv[2])
from src.xstate_statemachine import PluginBase, create_machine
from src.xstate_statemachine.persistence import (
    DueTimerScanner, FileStore, OptimisticLock, PessimisticLock, SQLiteStore)
a = json.loads(sys.argv[1])
store = (SQLiteStore(a["path"], busy_timeout=60) if a["kind"] == "sqlite"
         else FileStore(a["path"]))
fired, buf = [], []
class P(PluginBase):
    def on_transition(self, i, f, t, tr):
        if str(tr.event).startswith("after."):
            buf.append(i.store_key)
    def flush_marks(self):
        fired.extend(buf); buf.clear()
    def discard_marks(self):
        buf.clear()
lock = OptimisticLock() if a["lock"] == "opt" else PessimisticLock(timeout=60)
sc = DueTimerScanner(store, lambda k: create_machine(a["cfg"]), lock=lock,
                     plugins=[P()], limit=a["n"])
r = sc.scan(10.0)
print(json.dumps({"fired": fired, "woken": r.woken,
                  "stale": r.skipped_stale, "errors": [k for k, _ in r.errors]}))
"""


class TestExactlyOnceProcesses:
    @pytest.mark.parametrize("lock", ["opt", "pess"])
    @pytest.mark.parametrize("kind,n", [("sqlite", 1_000), ("file", 100)])
    def test_four_processes(
        self, tmp_path: Path, kind: str, n: int, lock: str
    ) -> None:
        path = str(tmp_path / ("s.db" if kind == "sqlite" else "fs"))
        store = SQLiteStore(path) if kind == "sqlite" else FileStore(path)
        keys = _seed(store, n)
        args = json.dumps(
            {"path": path, "kind": kind, "lock": lock, "cfg": CFG, "n": n}
        )
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", PROC_CHILD, args, str(ROOT)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for _ in range(4)
        ]
        outs = []
        for p in procs:
            out, err = p.communicate(timeout=240)
            assert p.returncode == 0, err.decode(errors="replace")[-2000:]
            outs.append(json.loads(out.decode().strip().splitlines()[-1]))
        fired = Counter(k for o in outs for k in o["fired"])
        assert [k for o in outs for k in o["errors"]] == []
        assert set(fired) == set(keys) and set(fired.values()) == {1}
        assert {store.load(k).version for k in keys} == {2}


# -----------------------------------------------------------------------------
# 1c. the X0.9 races, deterministic
# -----------------------------------------------------------------------------
class TestDeterministicRaces:
    @pytest.mark.parametrize("engine", ["sync", "async"])
    def test_restart_false_exit_leaves_no_orphan_deadline(
        self, engine: str
    ) -> None:
        """BUG fixed (`_forget_deadlines`): `restart_timers=False` PARKS the
        restored deadline; exiting its state dropped the armed timer but
        not the parked record, so the save carried an orphan and every
        scanner tick on that key raised `StateNotFoundError`. Both engines
        exit through the same `_forget_deadlines`."""
        store = MemoryStore()
        _seed(store, 1)
        m = _machine()
        if engine == "sync":
            with persisted(store, "k00000", m, restart_timers=False) as i:
                i.send("CANCEL")
        else:
            import asyncio

            from src.xstate_statemachine.persistence import apersisted

            async def go() -> None:
                async with apersisted(
                    store, "k00000", m, restart_timers=False
                ) as i:
                    await i.send("CANCEL", wait=True)

            asyncio.run(go())
        rec = store.load("k00000")
        assert rec.deadlines == () and '"r.c"' in rec.snapshot
        # and the scanner has nothing to trip over
        sc = DueTimerScanner(store, lambda k: m)
        r = sc.scan(SCAN_AT)
        assert (r.due, r.woken, r.errors) == (0, 0, [])

    def test_web_request_advances_key_between_scan_and_lock(
        self, tmp_path: Path
    ) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        _seed(store, 1)
        m = _machine()

        class Racy(DueTimerScanner):
            def due_keys(self, now: Any = None) -> Any:
                keys = super().due_keys(now)
                # A web request cancels between our index read and our lock.
                with persisted(
                    store, "k00000", m, clock=SimulatedClock(wall_start=1)
                ) as i:
                    i.send("CANCEL")
                return keys

        plugin = FireCounter()
        sc = Racy(store, lambda k: m, plugins=[plugin])
        r = sc.scan(SCAN_AT)
        assert (r.due, r.woken, r.skipped_stale, r.errors) == (1, 0, 1, [])
        assert plugin.fires == Counter()
        rec = store.load("k00000")
        assert rec.deadlines == () and '"r.c"' in rec.snapshot

    @pytest.mark.parametrize("kind", ["memory", "sqlite", "file"])
    def test_other_scanner_fires_between_recheck_and_persisted_load(
        self, tmp_path: Path, kind: str
    ) -> None:
        """BUG fixed: under OptimisticLock the key could be fired by
        another scanner AFTER our re-check but BEFORE `persisted()`'s own
        load; we then loaded a record with nothing due, saved a no-op v+1
        and counted it as ``woken`` (10 006 woken for 10 000 keys)."""
        inner = {
            "memory": lambda: MemoryStore(),
            "sqlite": lambda: SQLiteStore(tmp_path / "s.db"),
            "file": lambda: FileStore(tmp_path / "fs"),
        }[kind]()
        _seed(inner, 1)
        m = _machine()
        loads = {"n": 0}
        real_load = inner.load

        def load(key: str) -> Any:
            loads["n"] += 1
            if loads["n"] == 2:  # the re-check is #1; persisted() is #2
                other = DueTimerScanner(inner, lambda k: m)
                inner.load = real_load  # type: ignore[method-assign]
                assert other.scan(SCAN_AT).woken == 1
            return real_load(key)

        inner.load = load  # type: ignore[method-assign]
        sc = DueTimerScanner(inner, lambda k: m)
        sc.store.load = load  # type: ignore[method-assign]
        r = sc.scan(SCAN_AT)
        assert (r.woken, r.skipped_stale, r.errors) == (0, 1, [])
        assert real_load("k00000").version == 2  # not 3: no no-op save

    def test_conflict_on_save_is_stale_not_error(self) -> None:
        store = MemoryStore()
        _seed(store, 1)
        m = _machine()
        real_save = store.save

        def save(key: str, *a: Any, **k: Any) -> Any:
            # Another writer commits first: our versioned save conflicts.
            store.save = real_save  # type: ignore[method-assign]
            real_save(key, store.load(key).snapshot, deadlines=())
            return real_save(key, *a, **k)

        store.save = save  # type: ignore[method-assign]
        r = DueTimerScanner(store, lambda k: m).scan(SCAN_AT)
        assert (r.woken, r.skipped_stale, r.errors) == (0, 1, [])

    @pytest.mark.parametrize("kind", ["memory", "file"])
    def test_locked_key_is_stale_not_error_and_not_a_self_deadlock(
        self, tmp_path: Path, kind: str
    ) -> None:
        """Two BUGs fixed: (1) `PessimisticLock` on a store with a
        non-re-entrant lock (Memory, File) timed out on ITSELF for every
        key -- the scanner held the lock and `persisted()` re-took it;
        (2) a key another holder has locked was an ``errors`` entry every
        tick. Now: woken normally / skipped_stale."""
        store = (
            MemoryStore() if kind == "memory" else FileStore(tmp_path / "f")
        )
        _seed(store, 2)
        m = _machine()
        sc = DueTimerScanner(
            store, lambda k: m, lock=PessimisticLock(timeout=0.2)
        )
        held, release = threading.Event(), threading.Event()

        def holder() -> None:
            with store.lock("k00000", timeout=5):
                held.set()
                release.wait(10)

        t = threading.Thread(target=holder)
        t.start()
        held.wait(5)
        try:
            r = sc.scan(SCAN_AT)
        finally:
            release.set()
            t.join(10)
        assert (r.woken, r.skipped_stale, r.errors) == (1, 1, [])
        assert sc.scan(SCAN_AT).woken == 1  # next tick picks it up


# -----------------------------------------------------------------------------
# 2b. limit= wakes the EARLIEST, and a backlog drains
# -----------------------------------------------------------------------------
class TestLimitIsBatching:
    @pytest.mark.parametrize("kind", ["memory", "sqlite", "file"])
    def test_backlog_drains_earliest_first(
        self, tmp_path: Path, kind: str
    ) -> None:
        """BUG fixed (coordinator repro): limit capped the keys SCANNED in
        KEY order; 30 due keys with limit=10 woke 10 and then 0 forever.
        Keys are seeded so key order is the REVERSE of deadline order."""
        store = {
            "memory": lambda: MemoryStore(),
            "sqlite": lambda: SQLiteStore(tmp_path / "s.db"),
            "file": lambda: FileStore(tmp_path / "fs"),
        }[kind]()
        n = 30
        keys = _seed(store, n, stagger=-1.0)  # k00029 is the earliest
        m = _machine()
        sc = DueTimerScanner(store, lambda k: m, limit=10)
        order: List[str] = []
        for _ in range(3):
            woke = [k for k, _ in sc.due_keys(SCAN_AT)]
            r = sc.scan(SCAN_AT)
            assert (r.woken, r.errors) == (10, [])
            order.extend(woke)
        assert order == list(reversed(keys))
        assert sc.scan(SCAN_AT).woken == 0
        assert sc.due_keys(SCAN_AT) == []

    def test_prefix_is_not_starved_by_other_prefixes(self) -> None:
        store = MemoryStore()
        blob, dls = _seed_blob()
        for i in range(50):
            store.save(f"a-{i}", blob, deadlines=dls)
        store.save("b-1", blob, deadlines=dls)
        sc = DueTimerScanner(store, lambda k: _machine(), prefix="b-", limit=5)
        assert sc.run_once(now=SCAN_AT) == 1

    def test_bad_construction_fails_loudly(self) -> None:
        with pytest.raises(ValueError):
            DueTimerScanner(MemoryStore(), _machine, skew_tolerance_s=-1)
        with pytest.raises(ValueError):
            DueTimerScanner(MemoryStore(), _machine, limit=0)


# -----------------------------------------------------------------------------
# 3. lag metric, skew, injected clocks
# -----------------------------------------------------------------------------
class TestLagAndSkew:
    def test_max_lag_with_mixed_lateness(self) -> None:
        store = MemoryStore()
        _seed(store, 3, stagger=2.0)  # due 5, 7, 9
        r = DueTimerScanner(store, lambda k: _machine()).scan(SCAN_AT)
        assert r.woken == 3 and r.max_lag_s == pytest.approx(5.0)

    def test_skew_window(self) -> None:
        for tol, woken in ((1.0, 1), (0.0, 0)):
            store = MemoryStore()
            _seed(store, 1)
            sc = DueTimerScanner(
                store, lambda k: _machine(), skew_tolerance_s=tol
            )
            assert sc.run_once(now=4.5) == woken, tol

    def test_simulated_clock_wall_now_end_to_end(self) -> None:
        store = MemoryStore()
        _seed(store, 1)
        clk = SimulatedClock(wall_start=4.0)
        sc = DueTimerScanner(store, lambda k: _machine(), now=clk.wall_now)
        assert sc.run_once() == 0
        clk.increment(1000)  # wall 5.0
        assert sc.run_once() == 1

    def test_unfired_deadlines_keep_their_original_due_at(self) -> None:
        """`_WallClock` pins wall_now to the scan instant; the deadline that
        did NOT mature must be saved with its ORIGINAL due_at_wall, not
        re-anchored to the scan instant."""
        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "a": {
                    "initial": "w",
                    "states": {"w": {"after": {"1000": "d"}}, "d": {}},
                },
                "b": {
                    "initial": "w",
                    "states": {"w": {"after": {"900000": "d"}}, "d": {}},
                },
            },
        }
        m = create_machine(cfg)
        store = MemoryStore()
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=100.0)):
            pass
        r = DueTimerScanner(store, lambda k: m).scan(150.0)
        assert r.woken == 1
        (left,) = store.load("k").deadlines
        assert left.due_at_wall == pytest.approx(1000.0)
        assert left.delay_ms == 900000


# -----------------------------------------------------------------------------
# 5/6. failure injection + bounded waits
# -----------------------------------------------------------------------------
class TestFailures:
    def test_machine_for_key_failures_are_per_key(self) -> None:
        store = MemoryStore()
        _seed(store, 3)
        other = create_machine({**CFG, "id": "other"})

        def pick(key: str) -> Any:
            if key == "k00000":
                raise RuntimeError("no chart")
            if key == "k00001":
                return other  # wrong chart id
            return _machine()

        sc = DueTimerScanner(store, pick)
        r = sc.scan(SCAN_AT)
        assert r.woken == 1
        assert sorted(k for k, _ in r.errors) == ["k00000", "k00001"]
        # 📝 No poison/back-off: the bad keys stay due and are retried
        #    (and reported) every tick. Documented runbook: alert on a
        #    key that appears in `errors` on consecutive ticks; fix the
        #    chart mapping or `forget()` the key.
        r2 = sc.scan(SCAN_AT)
        assert (r2.woken, len(r2.errors)) == (0, 2)

    def test_load_raising_store_error_mid_scan(self) -> None:
        from src.xstate_statemachine.exceptions import StoreError

        store = MemoryStore()
        _seed(store, 3)
        real = store.load

        def load(key: str) -> Any:
            if key == "k00001":
                raise StoreError("disk went away")
            return real(key)

        store.load = load  # type: ignore[method-assign]
        r = DueTimerScanner(store, lambda k: _machine()).scan(SCAN_AT)
        assert r.woken == 2 and [k for k, _ in r.errors] == ["k00001"]

    def test_run_forever_survives_a_scan_that_always_raises(self) -> None:
        import logging
        import time

        sc = DueTimerScanner(MemoryStore(), lambda k: _machine())
        calls = {"n": 0}

        def boom(now: Any = None) -> Any:
            calls["n"] += 1
            raise RuntimeError("scan broke")

        sc.scan = boom  # type: ignore[method-assign]
        logging.getLogger("xstate_statemachine").disabled = True
        try:
            t = threading.Thread(target=sc.run_forever, args=(0.05,))
            t.start()
            deadline = time.monotonic() + 5
            while calls["n"] < 3 and time.monotonic() < deadline:
                time.sleep(0.01)
            t0 = time.monotonic()
            sc.stop()
            t.join(2)
        finally:
            logging.getLogger("xstate_statemachine").disabled = False
        assert not t.is_alive() and calls["n"] >= 3
        assert time.monotonic() - t0 <= 0.05 + 0.5

    def test_lock_that_never_returns_is_bounded(self) -> None:
        """A store whose lock never frees: `PessimisticLock(timeout=)` is
        honoured, the key is skipped (not an error), next key proceeds."""
        import time

        store = MemoryStore()
        _seed(store, 2)
        held = threading.Event()
        cm = store.lock("k00000", timeout=1)  # keep a ref: GC would release

        def hold() -> None:
            cm.__enter__()
            held.set()
            threading.Event().wait(60)

        threading.Thread(target=hold, daemon=True).start()  # never releases
        assert held.wait(5)
        sc = DueTimerScanner(
            store, lambda k: _machine(), lock=PessimisticLock(timeout=0.3)
        )
        t0 = time.monotonic()
        r = sc.scan(SCAN_AT)
        assert time.monotonic() - t0 < 2.0
        assert (r.woken, r.skipped_stale, r.errors) == (1, 1, [])

    def test_env_marker(self) -> None:
        assert os.environ.get("XSM_NEVER_SET_264") is None


def test_create_machine_from_one_config_in_eight_threads() -> None:
    """BUG fixed (models.py): the #136 aliased-cycle guard used ONE
    module-level set for all threads, so a scanner pool whose
    ``machine_for_key`` builds from a shared config raised a false
    `InvalidConfigError` (1 035 of 2 400 builds)."""
    errors: List[BaseException] = []

    def go() -> None:
        for _ in range(200):
            try:
                create_machine(CFG)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

    ts = [threading.Thread(target=go) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert errors == []
