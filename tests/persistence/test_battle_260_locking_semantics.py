# tests/persistence/test_battle_260_locking_semantics.py
# -----------------------------------------------------------------------------
# ⚔️ Battle test #260 part A: locking strategies + persisted() semantics
# -----------------------------------------------------------------------------
# 📝 Every claim on docs/_guide/guarantees.md about persisted() and the lock
#    strategies is an assertion target here. The deterministic fault
#    injections are the proof; the thread smoke at the bottom is the smoke.
#    Cross-PROCESS stress for File/SQLite x Optimistic/Pessimistic already
#    lives in test_battle_259_stores_crash_concurrency.py::TestProcessStress
#    and is not duplicated.
# -----------------------------------------------------------------------------
"""Battle tests for #260: after_commit, body semantics, lock strategies."""

from __future__ import annotations

import asyncio
import pathlib
import shutil
import tempfile
import threading
import time
import unittest
from typing import Any, Callable, List
from unittest import mock

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.clock import SimulatedClock
from src.xstate_statemachine.exceptions import (
    ConflictError,
    InterpreterStoppedError,
    LockTimeoutError,
    StoreError,
)
from src.xstate_statemachine.patterns.retry import RetryPolicy
from src.xstate_statemachine.persistence import (
    FileStore,
    MemoryStore,
    NoLock,
    OptimisticLock,
    PessimisticLock,
    SQLiteStore,
    apersisted,
    as_async,
    persisted,
    persisted_retry,
)
from src.xstate_statemachine.persistence import locking as locking_mod
from src.xstate_statemachine.persistence.helpers import KeyNotFoundError
from src.xstate_statemachine.persistence.locking import (
    _DEFAULT_LOCK,
    after_commit,
)
from src.xstate_statemachine.plugins import PluginBase

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUARANTEES = (ROOT / "docs" / "_guide" / "guarantees.md").read_text("utf-8")
NO_BACKOFF = RetryPolicy(base_ms=0.1, max_ms=1, jitter="full")
WATCHDOG_S = 60.0

_CFG = {
    "id": "c",
    "initial": "s",
    "context": {"n": 0},
    "states": {
        "s": {"on": {"T": {"actions": "inc"}, "F": "f"}},
        "f": {"type": "final"},
    },
}
ACTION_RUNS = {"n": 0}


def _inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ACTION_RUNS["n"] += 1
    ctx["n"] += 1


MACHINE = create_machine(_CFG, logic=MachineLogic(actions={"inc": _inc}))


def _count(store: Any, key: str) -> int:
    rec = store.load(key)
    if rec is None:
        return 0
    r = SyncInterpreter.from_snapshot(rec.snapshot, MACHINE).start()
    try:
        return int(r.context["n"])
    finally:
        r.stop()


def _threads(target: Callable[[int], None], n: int) -> List[BaseException]:
    errors: List[BaseException] = []

    def wrap(i: int) -> None:
        try:
            target(i)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [
        threading.Thread(target=wrap, args=(i,), daemon=True) for i in range(n)
    ]
    for t in ts:
        t.start()
    deadline = time.monotonic() + WATCHDOG_S
    for t in ts:
        t.join(max(0.0, deadline - time.monotonic()))
    if any(t.is_alive() for t in ts):
        raise AssertionError("threads hung past the watchdog")
    return errors


class FaultyStore:
    """Wraps a store; `save` raises *exc_factory()* on the listed attempts
    (1-based). Everything else is delegated."""

    def __init__(self, inner: Any, fail_on=(), exc_factory=None) -> None:
        self.inner = inner
        self.fail_on = set(fail_on)
        self.attempts = 0
        self.exc_factory = exc_factory or (
            lambda key, kw: ConflictError(key, kw.get("expected_version"), -1)
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def save(self, key: str, snapshot: str, **kw: Any) -> int:
        self.attempts += 1
        if self.attempts in self.fail_on:
            raise self.exc_factory(key, kw)
        return self.inner.save(key, snapshot, **kw)


class Marker:
    """A post-save marker plugin (the `IdempotencyPlugin` / `OutboxPlugin`
    shape): buffered marks, flushed after the save, discarded on failure."""

    def __init__(self, log: List[str], store: Any, key: str, fail=False):
        self.log, self.store, self.key = log, store, key
        self.fail = fail
        self.buffer_marks = False
        self.flush_priority = 0

    def flush_marks(self) -> None:
        rec = self.store.load(self.key)
        self.log.append(f"mark@v{rec.version if rec else 0}")
        if self.fail:
            raise StoreError("inbox down")

    def discard_marks(self) -> None:
        self.log.append("discard")


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        ACTION_RUNS["n"] = 0

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stores(self) -> List[Any]:
        return [
            MemoryStore(),
            FileStore(self.tmp / f"fs{id(self)}{time.monotonic_ns()}"),
            SQLiteStore(self.tmp / f"s{time.monotonic_ns()}.db"),
        ]


# =============================================================================
# ✅ after_commit
# =============================================================================
class TestAfterCommit(_Tmp):
    def test_runs_after_save_once_in_order(self) -> None:
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                seen: List[Any] = []

                def cb(tag: str) -> Callable[[], None]:
                    return lambda: seen.append((tag, store.load("k").version))

                with persisted(store, "k", MACHINE) as i:
                    i.send("T")
                    after_commit(cb("a"))
                    after_commit(cb("b"))
                    self.assertEqual(seen, [])
                self.assertEqual(seen, [("a", 1), ("b", 1)])

    def test_not_run_on_conflict_storeerror_or_body_error(self) -> None:
        cases = [
            ("conflict", lambda k, kw: ConflictError(k, 0, -1), ConflictError),
            ("store", lambda k, kw: StoreError("disk"), StoreError),
        ]
        for name, factory, exc in cases:
            with self.subTest(name):
                ran: List[int] = []
                store = FaultyStore(MemoryStore(), {1}, factory)
                with self.assertRaises(exc):
                    with persisted(store, "k", MACHINE) as i:
                        i.send("T")
                        after_commit(lambda: ran.append(1))
                self.assertEqual(ran, [])
        ran2: List[int] = []
        with self.assertRaises(RuntimeError):
            with persisted(MemoryStore(), "k", MACHINE):
                after_commit(lambda: ran2.append(1))
                raise RuntimeError("body")
        self.assertEqual(ran2, [])

    def test_raising_callback_save_durable_rest_run_first_reraised(self):
        store = MemoryStore()
        log: List[str] = []

        def boom(tag: str) -> Callable[[], None]:
            def f() -> None:
                log.append(tag)
                raise RuntimeError(tag)

            return f

        with self.assertRaises(RuntimeError) as cm:
            with persisted(store, "k", MACHINE) as i:
                i.send("T")
                after_commit(boom("b1"))
                after_commit(boom("b2"))
                after_commit(lambda: log.append("c"))
        self.assertEqual(str(cm.exception), "b1")  # first error re-raised
        self.assertEqual(log, ["b1", "b2", "c"])  # every callback ran
        self.assertEqual(_count(store, "k"), 1)  # save already durable
        self.assertEqual(store.load("k").version, 1)

    def test_outside_block_runs_immediately(self) -> None:
        ran: List[int] = []
        after_commit(lambda: ran.append(1))
        self.assertEqual(ran, [1])

    def test_nested_different_key_runs_its_own_callbacks_at_its_exit(
        self,
    ) -> None:
        # 🐛 Review M2 (fixed): a nested block on ANOTHER key deferred its
        #    callbacks to the outermost commit -- its save was already
        #    durable, so a committed state change could end with no
        #    published event. A different key is its own commit.
        store = MemoryStore()
        log: List[str] = []
        with persisted(store, "outer", MACHINE):
            with persisted(store, "inner", MACHINE) as j:
                j.send("T")
                after_commit(lambda: log.append("inner-cb"))
            self.assertEqual(_count(store, "inner"), 1)
            self.assertEqual(log, ["inner-cb"])  # ran at the INNER exit
            log.append("inner-exited")
            after_commit(lambda: log.append("outer-cb"))
        self.assertEqual(log, ["inner-cb", "inner-exited", "outer-cb"])

    def test_nested_different_key_callbacks_survive_outer_failure(
        self,
    ) -> None:
        # 🐛 Review M2 (fixed): the inner save committed, so its callback
        #    MUST have run even though the outer block then failed.
        store = MemoryStore()
        log: List[str] = []
        with self.assertRaises(RuntimeError):
            with persisted(store, "outer", MACHINE):
                with persisted(store, "inner", MACHINE):
                    after_commit(lambda: log.append("inner-cb"))
                after_commit(lambda: log.append("outer-cb"))
                raise RuntimeError("outer")
        self.assertEqual(log, ["inner-cb"])  # inner ran, outer dropped
        self.assertEqual(store.load("inner").version, 1)
        self.assertIsNone(store.load("outer"))

    def test_nested_same_key_shares_the_outer_commit(self) -> None:
        # 📝 The deferral IS right when the nested scope is the SAME key:
        #    a `lock.run` re-entering its own key is one commit, so its
        #    callbacks wait for that commit. Model it with the scope
        #    primitive directly -- a real nested write to the same key
        #    under OptimisticLock would (correctly) conflict.
        from src.xstate_statemachine.persistence.locking import (
            _commit_scope,
        )

        log: List[str] = []
        with _commit_scope(key="k"):
            after_commit(lambda: log.append("outer-cb"))
            with _commit_scope(key="k"):
                after_commit(lambda: log.append("inner-cb"))
            self.assertEqual(log, [])  # same key: deferred to the outer
            with _commit_scope(key="other"):
                after_commit(lambda: log.append("other-cb"))
            self.assertEqual(log, ["other-cb"])  # other key: its own
        self.assertEqual(log, ["other-cb", "outer-cb", "inner-cb"])

    def test_sync_block_refuses_coroutine_callback(self) -> None:
        async def co() -> None:  # pragma: no cover - never awaited
            pass

        store = MemoryStore()
        with self.assertRaises(TypeError):
            with persisted(store, "k", MACHINE):
                after_commit(co)
        self.assertEqual(store.load("k").version, 1)

    def test_threads_no_crosstalk(self) -> None:
        store = MemoryStore()
        barrier = threading.Barrier(2, timeout=10)
        got: dict = {}

        def work(n: int) -> None:
            mine: List[Any] = []
            with persisted(store, f"k{n}", MACHINE):
                after_commit(lambda: mine.append(threading.get_ident()))
                barrier.wait()  # both inside a block at once
            barrier.wait()
            got[n] = (mine, threading.get_ident())

        self.assertEqual(_threads(work, 2), [])
        for n in (0, 1):
            mine, ident = got[n]
            self.assertEqual(mine, [ident])

    def test_async_tasks_no_crosstalk_and_coroutine_awaited(self) -> None:
        store = MemoryStore()
        log: List[str] = []

        async def task(n: int, gate: asyncio.Event) -> None:
            async def co() -> None:
                await asyncio.sleep(0)
                log.append(f"co{n}")

            async with apersisted(store, f"k{n}", MACHINE):
                after_commit(lambda: log.append(f"cb{n}"))
                after_commit(co)
                await gate.wait()
                if n == 1:
                    raise RuntimeError("task 1 fails")

        async def main() -> List[Any]:
            gate = asyncio.Event()
            ts = [asyncio.ensure_future(task(n, gate)) for n in (0, 1)]
            await asyncio.sleep(0.05)
            gate.set()
            return await asyncio.gather(*ts, return_exceptions=True)

        res = asyncio.run(main())
        self.assertIsNone(res[0])
        self.assertIsInstance(res[1], RuntimeError)
        self.assertEqual(log, ["cb0", "co0"])
        self.assertIsNone(store.load("k1"))


# =============================================================================
# 🧾 Marker ordering: claim → save → mark
# =============================================================================
class TestMarks(_Tmp):
    def test_mark_after_save(self) -> None:
        store = MemoryStore()
        log: List[str] = []
        m = Marker(log, store, "k")
        with persisted(store, "k", MACHINE, plugins=[m]) as i:
            self.assertTrue(m.buffer_marks)  # buffered inside the block
            i.send("T")
        self.assertEqual(log, ["mark@v1"])  # mark saw the saved record
        self.assertFalse(m.buffer_marks)  # restored on exit

    def test_failed_save_writes_no_mark(self) -> None:
        for exc in (StoreError, ConflictError):
            with self.subTest(exc.__name__):
                inner = MemoryStore()
                log: List[str] = []
                store = FaultyStore(
                    inner,
                    {1},
                    lambda k, kw, e=exc: (
                        e("x") if e is StoreError else e(k, 0, -1)
                    ),
                )
                with self.assertRaises(exc):
                    with persisted(
                        store, "k", MACHINE, plugins=[Marker(log, inner, "k")]
                    ) as i:
                        i.send("T")
                self.assertEqual(log, ["discard"])
                self.assertIsNone(inner.load("k"))

    def test_failed_mark_snapshot_saved_error_propagates(self) -> None:
        store = MemoryStore()
        log: List[str] = []
        ran: List[int] = []
        with self.assertRaises(StoreError):
            with persisted(
                store, "k", MACHINE, plugins=[Marker(log, store, "k", True)]
            ) as i:
                i.send("T")
                after_commit(lambda: ran.append(1))
        # 📝 guarantees.md "between save and mark": the snapshot is durable
        self.assertEqual(_count(store, "k"), 1)
        self.assertEqual(log, ["mark@v1"])
        self.assertEqual(ran, [])  # the block did not exit cleanly

    def test_failing_marker_does_not_stop_later_marker(self) -> None:
        store = MemoryStore()
        log: List[str] = []
        a = Marker(log, store, "k", fail=True)
        b = Marker(log, store, "k")
        b.flush_priority = 1
        with self.assertRaises(StoreError):
            with persisted(store, "k", MACHINE, plugins=[b, a]):
                pass
        self.assertEqual(log, ["mark@v1", "mark@v1"])

    def test_body_error_discards_marks(self) -> None:
        store = MemoryStore()
        log: List[str] = []
        with self.assertRaises(RuntimeError):
            with persisted(
                store, "k", MACHINE, plugins=[Marker(log, store, "k")]
            ):
                raise RuntimeError
        self.assertEqual(log, ["discard"])


# =============================================================================
# 📦 Body semantics
# =============================================================================
class TestBody(_Tmp):
    def test_body_error_writes_nothing(self) -> None:
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                with persisted(store, "k", MACHINE) as i:
                    i.send("T")
                before = store.load("k")
                with self.assertRaises(RuntimeError):
                    with persisted(store, "k", MACHINE) as i:
                        i.send("T")
                        i.send("F")  # even reaching final
                        raise RuntimeError("body")
                after = store.load("k")
                self.assertEqual(after.version, before.version)
                self.assertEqual(after.snapshot, before.snapshot)
                self.assertNotEqual(i.status, "running")  # discarded

    def test_final_inside_body_is_saved_and_then_refused(self) -> None:
        store = MemoryStore()
        with persisted(store, "k", MACHINE) as i:
            i.send("F")
            self.assertEqual(i.status, "done")
        rec = store.load("k")
        self.assertEqual(rec.version, 1)
        self.assertIn('"done"', rec.snapshot)
        with persisted(store, "k", MACHINE) as i:
            self.assertEqual(i.status, "done")  # not recreated
            r = i.send("T", wait=True)
            self.assertIsInstance(r.error, InterpreterStoppedError)
            self.assertFalse(r.changed)
        self.assertEqual(_count(store, "k"), 0)
        with persisted(store, "k", MACHINE) as i:
            self.assertEqual(i.status, "done")  # store not corrupted

    def test_noop_body_still_saves_and_bumps_version(self) -> None:
        # 📝 Documented: "persists on clean exit". A no-op block IS a save
        # (it creates the record in persistence.md's own example). Pinned
        # so a "skip unchanged" optimisation is a deliberate change.
        store = MemoryStore()
        with persisted(store, "k", MACHINE):
            pass
        self.assertEqual(store.load("k").version, 1)
        with persisted(store, "k", MACHINE):
            pass
        self.assertEqual(store.load("k").version, 2)

    def test_noop_reader_conflicts_with_concurrent_writer(self) -> None:
        # The consequence: a read-only block under OptimisticLock raises
        # ConflictError when a writer committed meanwhile.
        store = MemoryStore()
        with persisted(store, "k", MACHINE):
            pass
        with self.assertRaises(ConflictError):
            with persisted(store, "k", MACHINE) as reader:
                persisted_retry(store, "k", MACHINE, lambda i: i.send("T"))
                self.assertEqual(reader.context["n"], 0)
        self.assertEqual(_count(store, "k"), 1)

    def test_create_if_missing(self) -> None:
        store = MemoryStore()
        entered: List[int] = []
        with self.assertRaises(KeyNotFoundError):
            with persisted(store, "k", MACHINE, create_if_missing=False):
                entered.append(1)  # pragma: no cover
        self.assertEqual(entered, [])
        self.assertIsNone(store.load("k"))
        with persisted(store, "k", MACHINE, create_if_missing=True):
            pass
        self.assertEqual(store.load("k").version, 1)

    def test_interpreter_started_keyed_clocked_plugins_started(self) -> None:
        store = MemoryStore()
        started: List[str] = []

        class P(PluginBase):
            def on_interpreter_start(self, interp: Any) -> None:
                started.append(interp.store_key)

        clock = SimulatedClock(wall_start=1_000_000.0)
        for _ in range(2):  # create, then hydrate
            with persisted(
                store, "k", MACHINE, clock=clock, plugins=[P()]
            ) as i:
                self.assertEqual(i.status, "running")
                self.assertEqual(i.store_key, "k")
                self.assertEqual(i.wall_now(), 1_000_000.0)
        self.assertEqual(started, ["k", "k"])

    def test_default_lock_shared_stateless_under_threads(self) -> None:
        store = MemoryStore()
        before = dict(vars(_DEFAULT_LOCK))

        def work(n: int) -> None:
            for _ in range(125):
                with persisted(store, f"k{n}", MACHINE) as i:
                    i.send("T")

        self.assertEqual(_threads(work, 8), [])
        for n in range(8):
            self.assertEqual(_count(store, f"k{n}"), 125)
        self.assertEqual(vars(_DEFAULT_LOCK), before)
        self.assertEqual(
            set(vars(_DEFAULT_LOCK)), {"retries", "backoff", "_rng"}
        )

    def test_bad_lock_argument_is_valueerror_naming_options(self) -> None:
        store = MemoryStore()
        for bad in ("none", "optimistic", 5, object()):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as cm:
                    with persisted(store, "k", MACHINE, lock=bad):
                        pass  # pragma: no cover
                for name in ("OptimisticLock", "PessimisticLock", "NoLock"):
                    self.assertIn(name, str(cm.exception))
                with self.assertRaises(ValueError):
                    persisted_retry(store, "k", MACHINE, id, lock=bad)
        self.assertIsNone(store.load("k"))

    def test_interpreter_cls_not_accepted(self) -> None:
        from src.xstate_statemachine import Interpreter

        with self.assertRaises(TypeError):
            with persisted(
                MemoryStore(), "k", MACHINE, interpreter_cls=Interpreter
            ):
                pass  # pragma: no cover


# =============================================================================
# 🔁 Optimistic
# =============================================================================
class TestOptimistic(_Tmp):
    def test_block_raises_on_first_conflict(self) -> None:
        store = FaultyStore(MemoryStore(), {1})
        with self.assertRaises(ConflictError):
            with persisted(store, "k", MACHINE) as i:
                i.send("T")
        self.assertEqual(store.attempts, 1)

    def test_run_calls_fn_k_plus_one_and_actions_match(self) -> None:
        for k in (1, 2, 3):
            with self.subTest(k=k):
                ACTION_RUNS["n"] = 0
                store = FaultyStore(MemoryStore(), set(range(1, k + 1)))
                calls = {"n": 0}

                def fn(i: Any) -> str:
                    calls["n"] += 1
                    i.send("T")
                    return "ok"

                lock = OptimisticLock(retries=k, backoff=NO_BACKOFF)
                self.assertEqual(lock.run(store, "k", MACHINE, fn), "ok")
                self.assertEqual(calls["n"], k + 1)
                # ⚠️ the amendment: actions ran once per attempt
                self.assertEqual(ACTION_RUNS["n"], k + 1)
                self.assertEqual(_count(store.inner, "k"), 1)
        self.assertIn("retries + 1", GUARANTEES)

    def test_retries_zero_and_exhaustion_attempts(self) -> None:
        for retries in (0, 1, 4):
            with self.subTest(retries=retries):
                store = FaultyStore(MemoryStore(), set(range(1, 100)))
                lock = OptimisticLock(retries=retries, backoff=NO_BACKOFF)
                with self.assertRaises(ConflictError) as cm:
                    lock.run(store, "k", MACHINE, lambda i: i.send("T"))
                self.assertEqual(cm.exception.attempts, retries + 1)
                self.assertEqual(store.attempts, retries + 1)
                self.assertIsNone(store.inner.load("k"))

    def test_backoff_sleeps_within_policy_bounds(self) -> None:
        policy = RetryPolicy(base_ms=10, factor=2, max_ms=30, jitter="full")
        for r in (0.0, 0.5, 0.999):
            with self.subTest(rng=r):
                sleeps: List[float] = []
                lock = OptimisticLock(retries=4, backoff=policy, rng=lambda: r)
                store = FaultyStore(MemoryStore(), {1, 2, 3, 4})
                with mock.patch.object(
                    locking_mod.time, "sleep", sleeps.append
                ):
                    lock.run(store, "k", MACHINE, lambda i: i.send("T"))
                caps = [0.010, 0.020, 0.030, 0.030]
                self.assertEqual(len(sleeps), 4)
                for s, cap in zip(sleeps, caps):
                    self.assertAlmostEqual(s, r * cap, places=9)
                    self.assertLessEqual(s, cap)

    def test_persisted_retry_return_and_foreign_exception(self) -> None:
        store = FaultyStore(MemoryStore(), {1})
        lock = OptimisticLock(retries=2, backoff=NO_BACKOFF)
        calls = {"n": 0}

        def fn(i: Any) -> dict:
            calls["n"] += 1
            i.send("T")
            return {"v": calls["n"]}

        self.assertEqual(
            persisted_retry(store, "k", MACHINE, fn, lock=lock), {"v": 2}
        )
        calls["n"] = 0

        def bad(i: Any) -> None:
            calls["n"] += 1
            i.send("T")
            raise KeyError("domain")

        with self.assertRaises(KeyError):
            persisted_retry(store, "k", MACHINE, bad, lock=lock)
        self.assertEqual(calls["n"], 1)  # not retried
        self.assertEqual(_count(store.inner, "k"), 1)  # nothing written

    def test_run_after_commit_only_for_winning_attempt(self) -> None:
        store = FaultyStore(MemoryStore(), {1, 2})
        ran: List[int] = []
        lock = OptimisticLock(retries=3, backoff=NO_BACKOFF)
        n = {"a": 0}

        def fn(i: Any) -> None:
            n["a"] += 1
            after_commit(lambda a=n["a"]: ran.append(a))

        lock.run(store, "k", MACHINE, fn)
        self.assertEqual(ran, [3])


# =============================================================================
# 🔒 Pessimistic
# =============================================================================
class TestPessimistic(_Tmp):
    def test_lock_timeout_at_bound(self) -> None:
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                held, release = threading.Event(), threading.Event()

                def holder() -> None:
                    with store.lock("k", timeout=5):
                        held.set()
                        release.wait(10)

                t = threading.Thread(target=holder, daemon=True)
                t.start()
                self.assertTrue(held.wait(5))
                t0 = time.monotonic()
                try:
                    with self.assertRaises(LockTimeoutError):
                        with persisted(
                            store,
                            "k",
                            MACHINE,
                            lock=PessimisticLock(timeout=0.5),
                        ):
                            pass  # pragma: no cover
                    took = time.monotonic() - t0
                finally:
                    release.set()
                    t.join(10)
                self.assertGreaterEqual(took, 0.4)
                # 📝 The lower bound is the guarantee ("never early"). The
                #    upper bound only guards against a wait that ignores
                #    `timeout` altogether (the #259 spin bug): SQLite's
                #    busy handler polls in coarse steps and a loaded macOS
                #    runner read 1.63 s for a 0.5 s timeout. Allow 3x.
                self.assertLessEqual(took, 0.5 * 3 + 0.5)

    def test_fencing_expired_lock_is_conflict_not_lost_update(self) -> None:
        store = MemoryStore()
        lock = PessimisticLock(timeout=5)
        with persisted(store, "k", MACHINE, lock=lock) as i:
            i.send("T")
        with self.assertRaises(ConflictError):
            with persisted(store, "k", MACHINE, lock=lock) as i:
                i.send("T")
                # "the lock expired": another writer bypasses it
                other = SyncInterpreter.from_snapshot(
                    store.load("k").snapshot, MACHINE
                ).start()
                other.send("T")
                other.send("T")
                store.save("k", other.get_snapshot(), expected_version=None)
                other.stop()
        self.assertEqual(_count(store, "k"), 3)  # the other writer's data

    def test_body_error_releases_lock(self) -> None:
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                with self.assertRaises(RuntimeError):
                    with persisted(
                        store, "k", MACHINE, lock=PessimisticLock()
                    ):
                        raise RuntimeError
                ok = threading.Event()

                def nxt(_n: int) -> None:
                    with persisted(
                        store, "k", MACHINE, lock=PessimisticLock(timeout=0)
                    ):
                        ok.set()

                self.assertEqual(_threads(nxt, 1), [])
                self.assertTrue(ok.is_set())

    def test_lock_released_before_after_commit(self) -> None:
        store = MemoryStore()
        result: List[bool] = []

        def probe() -> None:
            def other() -> None:
                try:
                    with store.lock("k", timeout=0):
                        result.append(True)
                except LockTimeoutError:
                    result.append(False)

            _threads(lambda _n: other(), 1)

        with persisted(store, "k", MACHINE, lock=PessimisticLock()):
            after_commit(probe)
        self.assertEqual(result, [True])


# =============================================================================
# 🚫 NoLock
# =============================================================================
class TestNoLock(_Tmp):
    def test_documented_lost_update_happens(self) -> None:
        for store in self.stores():
            with self.subTest(store=type(store).__name__):
                with persisted(store, "k", MACHINE, lock=NoLock()):
                    pass
                with persisted(store, "k", MACHINE, lock=NoLock()) as a:
                    with persisted(store, "k", MACHINE, lock=NoLock()) as b:
                        b.send("T")
                    a.send("T")
                # two increments committed, one survives: last writer wins
                self.assertEqual(_count(store, "k"), 1)
                self.assertEqual(store.load("k").version, 3)
        self.assertIn(
            "NoLock", (ROOT / "docs/_guide/persistence.md").read_text("utf-8")
        )


# =============================================================================
# ⚡ apersisted
# =============================================================================
class TestAsync(_Tmp):
    def _both(self, inner: Any) -> List[Any]:
        return [inner, as_async(inner)]

    def test_semantics_match_with_sync_and_async_store(self) -> None:
        for base in self.stores():
            for store in self._both(base):
                with self.subTest(
                    base=type(base).__name__, s=type(store).__name__
                ):
                    key = f"k{id(store)}"

                    async def main() -> None:
                        async with apersisted(
                            base if store is base else store, key, MACHINE
                        ) as i:
                            await i.send("T")
                        with self.assertRaises(RuntimeError):
                            async with apersisted(store, key, MACHINE) as i:
                                await i.send("T")
                                raise RuntimeError
                        with self.assertRaises(KeyNotFoundError):
                            async with apersisted(
                                store,
                                key + "x",
                                MACHINE,
                                create_if_missing=False,
                            ):
                                pass  # pragma: no cover
                        async with apersisted(
                            store,
                            key,
                            MACHINE,
                            lock=PessimisticLock(timeout=5),
                        ) as i:
                            await i.send("T")
                        with self.assertRaises(ValueError):
                            async with apersisted(
                                store, key, MACHINE, lock="none"
                            ):
                                pass  # pragma: no cover

                    asyncio.run(main())
                    self.assertEqual(_count(base, key), 2)
                    self.assertEqual(base.load(key).version, 2)
                    if store is not base:
                        store.close()

    def test_async_conflict_and_failed_save_skip_callbacks(self) -> None:
        inner = MemoryStore()
        store = FaultyStore(inner, {1})
        ran: List[int] = []

        async def main() -> None:
            with self.assertRaises(ConflictError):
                async with apersisted(store, "k", MACHINE) as i:
                    await i.send("T")
                    after_commit(lambda: ran.append(1))

        asyncio.run(main())
        self.assertEqual(ran, [])
        self.assertIsNone(inner.load("k"))


# =============================================================================
# 🔥 Smoke: 16 threads x 50 on ONE key, per strategy x store
# =============================================================================
class TestThreadSmoke(_Tmp):
    THREADS, EACH = 16, 50

    def test_counts(self) -> None:
        total = self.THREADS * self.EACH
        for store in self.stores():
            for lock in (
                OptimisticLock(retries=100_000, backoff=NO_BACKOFF),
                PessimisticLock(timeout=60),
                NoLock(),
            ):
                key = type(lock).__name__
                with self.subTest(store=type(store).__name__, lock=key):
                    # 📝 Per-CALL outcomes. A thread that hits one
                    #    LockTimeoutError must keep going, or the thread's
                    #    REMAINING calls are silently lost and `total -
                    #    len(errs)` undercounts (Windows 3.9 CI: 1 error,
                    #    756 of 800 counted -- the error cost that thread
                    #    its other 44 calls, #263 battle).
                    attempted = [0]
                    ok = [0]
                    errs: List[BaseException] = []
                    lk = threading.Lock()

                    def work(_n: int) -> None:
                        for _ in range(self.EACH):
                            with lk:
                                attempted[0] += 1
                            try:
                                lock.run(
                                    store, key, MACHINE, lambda i: i.send("T")
                                )
                            except LockTimeoutError as exc:
                                with lk:
                                    errs.append(exc)
                            else:
                                with lk:
                                    ok[0] += 1

                    self.assertEqual(_threads(work, self.THREADS), [])
                    self.assertEqual(attempted[0], total)
                    n = _count(store, key)
                    if isinstance(lock, NoLock):
                        # documented hazard: no errors, possibly fewer
                        self.assertEqual(errs, [])
                        self.assertLessEqual(n, total)
                        self.assertGreaterEqual(n, 1)
                        continue
                    if isinstance(store, FileStore) and isinstance(
                        lock, OptimisticLock
                    ):
                        # 📝 FileStore's per-save critical section waits a
                        #    FIXED 10 s for the OS lock. 16 threads each
                        #    polling `msvcrt.locking` every 10 ms through
                        #    800 fsync'd saves starved one past that on
                        #    the Windows 3.9 runner (3 of 800 calls). The
                        #    starved calls raised LockTimeoutError -- loud,
                        #    never a lost update -- and every call that
                        #    returned was counted exactly once. Assert
                        #    THAT; the exact-800 claim is proved on Memory
                        #    and SQLite and on FileStore under Pessimistic.
                        self.assertEqual(n, ok[0])
                        self.assertEqual(ok[0] + len(errs), total)
                        continue
                    self.assertEqual(errs, [])
                    self.assertEqual(n, total)
                    self.assertEqual(store.load(key).version, total)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
