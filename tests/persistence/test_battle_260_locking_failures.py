# tests/persistence/test_battle_260_locking_failures.py
"""#260 battle part B: failure injection at every site inside `persisted()` /
`apersisted()`, the `load_interpreter` / migrator / `from_snapshot` kwarg
contracts, `persisted_retry`, leaks and bounds.

unittest only (no pytest-asyncio): `asyncio.run` / `IsolatedAsyncioTestCase`.
"""

from __future__ import annotations

import asyncio
import gc
import json
import shutil
import tempfile
import sys
import threading
import time
import tracemalloc
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

from src.xstate_statemachine import (
    MachineLogic,
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    ConflictError,
    LockTimeoutError,
    SnapshotCorruptError,
    SnapshotDriftError,
    SnapshotTooLargeError,
    StoreError,
)
from src.xstate_statemachine.patterns.retry import RetryPolicy
from src.xstate_statemachine.persistence import (
    FileStore,
    MachineVersionMismatchError,
    MemoryStore,
    NoLock,
    OptimisticLock,
    PessimisticLock,
    SnapshotMigrator,
    SQLiteStore,
    apersisted,
    persisted,
    persisted_retry,
)
from src.xstate_statemachine.persistence.helpers import (
    KeyNotFoundError,
    load_interpreter,
)
from src.xstate_statemachine.persistence.locking import after_commit

LIB = "xstate_statemachine"


def _inc(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] = c.get("n", 0) + 1


def _machine(version: Optional[str] = None, mid: str = "c") -> Any:
    cfg: Dict[str, Any] = {
        "id": mid,
        "initial": "s",
        "context": {"n": 0},
        "states": {"s": {"on": {"T": {"actions": "inc"}}}},
    }
    if version:
        cfg["version"] = version
    return create_machine(cfg, logic=MachineLogic(actions={"inc": _inc}))


class _FaultyLock:
    def __init__(self, owner: "FaultyStore", inner: Any) -> None:
        self.owner = owner
        self.inner = inner

    def __enter__(self) -> None:
        self.owner.log.append("lock.enter")
        exc = self.owner.fail_next.pop("lock.__enter__", None)
        if exc is not None:
            raise exc("injected lock.__enter__")
        self.inner.__enter__()

    def __exit__(self, *exc_info: Any) -> None:
        self.owner.log.append("lock.exit")
        try:
            self.inner.__exit__(*exc_info)  # really release first
        finally:
            exc = self.owner.fail_next.pop("lock.__exit__", None)
            if exc is not None:
                raise exc("injected lock.__exit__")


class FaultyStore:
    """Delegates to a real store; ``fail_next[op] = ExcClass`` raises once."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.fail_next: Dict[str, Any] = {}
        self.log: List[str] = []

    def _maybe(self, op: str) -> None:
        self.log.append(op)
        exc = self.fail_next.pop(op, None)
        if exc is not None:
            if exc is ConflictError:
                raise ConflictError("k", 1, 2)
            if exc is SnapshotTooLargeError:
                raise SnapshotTooLargeError("k", 10, 5)
            raise exc("injected " + op)

    def load(self, key: str) -> Any:
        self._maybe("load")
        return self.inner.load(key)

    def save(self, key: str, snapshot: str, **kw: Any) -> int:
        self._maybe("save")
        return self.inner.save(key, snapshot, **kw)

    def delete(self, key: str) -> bool:
        self._maybe("delete")
        return self.inner.delete(key)

    def lock(self, key: str, *, timeout: float = 10.0) -> Any:
        return _FaultyLock(self, self.inner.lock(key, timeout=timeout))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._open: List[Any] = []

    def make(self, kind: str) -> Any:
        if kind == "memory":
            s: Any = MemoryStore()
        elif kind == "file":
            s = FileStore(self.tmp / ("f%d" % len(self._open)))
        else:
            s = SQLiteStore(self.tmp / ("s%d.db" % len(self._open)))
        self._open.append(s)
        self.addCleanup(lambda: hasattr(s, "close") and s.close())
        return s

    def seed(self, store: Any, key: str = "k", n: int = 1) -> None:
        with persisted(store, key, _machine()) as i:
            for _ in range(n):
                i.send("T")

    def assert_free(self, store: Any, key: str = "k") -> None:
        """No lock leaked: a pessimistic block acquires at once."""
        t0 = time.monotonic()
        with persisted(
            store, key, _machine(), lock=PessimisticLock(timeout=1)
        ):
            pass
        self.assertLess(time.monotonic() - t0, 1.0)

    def ver(self, store: Any, key: str = "k") -> Optional[int]:
        r = store.load(key)
        return None if r is None else r.version


KINDS = ("memory", "file", "sqlite")
LOCKS = (
    ("optimistic", lambda: OptimisticLock()),
    ("pessimistic", lambda: PessimisticLock(timeout=1)),
    ("none", lambda: NoLock()),
)


# =============================================================================
# load failures
# =============================================================================
class TestLoadFailures(_Base):
    def test_load_errors_propagate_typed_body_never_runs(self) -> None:
        for kind in KINDS:
            for exc in (
                StoreError,
                SnapshotCorruptError,
                SnapshotTooLargeError,
                OSError,
            ):
                for lname, mk in LOCKS:
                    with self.subTest(kind=kind, exc=exc.__name__, lock=lname):
                        fs = FaultyStore(self.make(kind))
                        self.seed(fs)
                        before = self.ver(fs)
                        fs.fail_next["load"] = exc
                        ran: List[int] = []
                        with self.assertRaises(exc):
                            with persisted(fs, "k", _machine(), lock=mk()):
                                ran.append(1)
                        self.assertEqual(ran, [])
                        self.assertEqual(self.ver(fs), before)  # no write
                        self.assert_free(fs)

    def test_load_error_not_wrapped_twice(self) -> None:
        fs = FaultyStore(MemoryStore())
        fs.fail_next["load"] = StoreError
        with self.assertRaises(StoreError) as cm:
            with persisted(fs, "k", _machine()):
                pass
        self.assertIsNone(cm.exception.__cause__)
        self.assertEqual(str(cm.exception), "injected load")

    def test_wrong_machine_id_is_drift_before_body(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                st = self.make(kind)
                self.seed(st)
                ran: List[int] = []
                with self.assertRaises(SnapshotDriftError):
                    with persisted(st, "k", _machine(mid="other")):
                        ran.append(1)
                self.assertEqual(ran, [])
                self.assertEqual(self.ver(st), 1)
                self.assert_free(st)

    def test_changed_structure_is_drift_unless_hash_check_off(self) -> None:
        st = MemoryStore()
        self.seed(st)
        changed = create_machine(
            {
                "id": "c",
                "initial": "s",
                "context": {"n": 0},
                "states": {
                    "s": {"on": {"T": {"actions": "inc"}, "U": "t"}},
                    "t": {},
                },
            },
            logic=MachineLogic(actions={"inc": _inc}),
        )
        with self.assertRaises(SnapshotDriftError):
            with persisted(st, "k", changed):
                self.fail("body ran")
        with persisted(st, "k", changed, verify_machine_hash=False) as i:
            self.assertEqual(i.context["n"], 1)
            i.send("T")
        self.assertEqual(self.ver(st), 2)

    def test_every_strategy_run_forwards_the_hash_arguments(self) -> None:
        # 🐛 Review H1 (fixed): OptimisticLock.run -- the DEFAULT -- accepted
        #    verify_machine_hash / expected_machine_hash and silently
        #    dropped them, so `persisted_retry(..., verify_machine_hash=
        #    False)` still raised SnapshotDriftError. Every strategy, and
        #    the default (lock=None), must forward both.
        changed = create_machine(
            {
                "id": "c",
                "initial": "s",
                "context": {"n": 0},
                "states": {
                    "s": {"on": {"T": {"actions": "inc"}, "U": "t"}},
                    "t": {},
                },
            },
            logic=MachineLogic(actions={"inc": _inc}),
        )
        for lock in (None, OptimisticLock(), PessimisticLock(), NoLock()):
            with self.subTest(lock=type(lock).__name__):
                st = MemoryStore()
                self.seed(st)
                with self.assertRaises(SnapshotDriftError):
                    persisted_retry(
                        st, "k", changed, lambda i: i.send("T"), lock=lock
                    )
                persisted_retry(
                    st,
                    "k",
                    changed,
                    lambda i: i.send("T"),
                    lock=lock,
                    verify_machine_hash=False,
                )
                self.assertEqual(self.ver(st), 2)
                # expected_machine_hash: a wrong pin is refused, the right
                # one (the CHANGED machine's) accepted
                from src.xstate_statemachine.persistence.snapshot import (
                    structure_hash,
                )

                with self.assertRaises(SnapshotDriftError):
                    persisted_retry(
                        st,
                        "k",
                        changed,
                        lambda i: None,
                        lock=lock,
                        verify_machine_hash=False,
                        expected_machine_hash="not-the-hash",
                    )
                persisted_retry(
                    st,
                    "k",
                    changed,
                    lambda i: None,
                    lock=lock,
                    verify_machine_hash=False,
                    expected_machine_hash=structure_hash(changed),
                )

    def test_unknown_kwarg_is_typeerror_at_call(self) -> None:
        st = MemoryStore()
        with self.assertRaises(TypeError):
            persisted(st, "k", _machine(), bogus=1)  # at the call, not deep
        with self.assertRaises(TypeError):
            apersisted(st, "k", _machine(), bogus=1)
        with self.assertRaises(TypeError):
            OptimisticLock().run(st, "k", _machine(), lambda i: 0, bogus=1)

    def test_restore_kwargs_reach_from_snapshot(self) -> None:
        st = MemoryStore()
        m = _machine("1")
        self.seed(st)
        real = SyncInterpreter.from_snapshot
        with mock.patch.object(
            SyncInterpreter, "from_snapshot", wraps=real
        ) as spy:
            mig = SnapshotMigrator()
            with persisted(
                st,
                "k",
                m,
                restart_timers="restart",
                verify_machine_hash=False,
                expected_machine_hash=m.structure_hash,
                on_version_mismatch="warn",
                migrator=mig,
            ):
                pass
        kw = spy.call_args.kwargs
        self.assertEqual(kw["restart_timers"], "restart")
        self.assertIs(kw["verify_machine_hash"], False)
        self.assertEqual(kw["expected_machine_hash"], m.structure_hash)
        self.assertEqual(kw["on_version_mismatch"], "warn")
        self.assertIs(kw["migrator"], mig)

    def test_expected_machine_hash_enforced(self) -> None:
        st = MemoryStore()
        self.seed(st)
        with self.assertRaises(SnapshotDriftError):
            with persisted(
                st, "k", _machine(), expected_machine_hash="deadbeef"
            ):
                self.fail("body ran")
        with persisted(
            st,
            "k",
            _machine(),
            expected_machine_hash=_machine().structure_hash,
        ):
            pass


# =============================================================================
# save / lock failures
# =============================================================================
class TestSaveAndLockFailures(_Base):
    def test_save_failure_keeps_body_effects_but_commits_nothing(self) -> None:
        for kind in KINDS:
            for exc in (ConflictError, StoreError, OSError):
                for lname, mk in LOCKS:
                    with self.subTest(kind=kind, exc=exc.__name__, lock=lname):
                        fs = FaultyStore(self.make(kind))
                        self.seed(fs)
                        before = self.ver(fs)
                        effects: List[int] = []
                        committed: List[int] = []
                        fs.fail_next["save"] = exc
                        with self.assertRaises(exc) as cm:
                            with persisted(
                                fs, "k", _machine(), lock=mk()
                            ) as i:
                                after_commit(lambda: committed.append(1))
                                i.send("T")
                                effects.append(i.context["n"])
                        self.assertEqual(effects, [2])  # body DID run
                        self.assertEqual(committed, [])  # after_commit dropped
                        self.assertEqual(self.ver(fs), before)
                        self.assertEqual(
                            json.loads(fs.load("k").snapshot)["context"]["n"],
                            1,
                        )
                        self.assertIsNone(cm.exception.__cause__)
                        self.assert_free(fs)

    def test_lock_enter_timeout_body_never_runs(self) -> None:
        fs = FaultyStore(MemoryStore())
        self.seed(fs)
        fs.fail_next["lock.__enter__"] = LockTimeoutError
        # LockTimeoutError takes (key, timeout); build via a factory
        fs.fail_next["lock.__enter__"] = lambda msg: LockTimeoutError("k", 1.0)
        ran: List[int] = []
        with self.assertRaises(LockTimeoutError):
            with persisted(fs, "k", _machine(), lock=PessimisticLock()):
                ran.append(1)
        self.assertEqual(ran, [])
        self.assertEqual(self.ver(fs), 1)
        self.assert_free(fs)

    def test_save_happens_inside_lock_then_unlock(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                fs = FaultyStore(self.make(kind))
                self.seed(fs)
                fs.log.clear()
                with persisted(
                    fs, "k", _machine(), lock=PessimisticLock()
                ) as i:
                    i.send("T")
                ops = [
                    o
                    for o in fs.log
                    if o in ("lock.enter", "save", "lock.exit")
                ]
                self.assertEqual(ops, ["lock.enter", "save", "lock.exit"])
                self.assertLess(fs.log.index("load"), fs.log.index("save"))

    def test_lock_exit_failure_after_save_propagates_and_lock_free(
        self,
    ) -> None:
        fs = FaultyStore(MemoryStore())
        self.seed(fs)
        fs.fail_next["lock.__exit__"] = OSError
        with self.assertRaises(OSError):
            with persisted(fs, "k", _machine(), lock=PessimisticLock()) as i:
                i.send("T")
        # the save was committed BEFORE unlock (no lost-update window)
        self.assertEqual(self.ver(fs), 2)
        self.assert_free(fs)

    def test_body_baseexception_releases_lock_writes_nothing(self) -> None:
        for kind in KINDS:
            for exc in (KeyboardInterrupt, asyncio.CancelledError, SystemExit):
                for lname, mk in LOCKS:
                    with self.subTest(kind=kind, exc=exc.__name__, lock=lname):
                        fs = FaultyStore(self.make(kind))
                        self.seed(fs)
                        fs.log.clear()
                        committed: List[int] = []
                        with self.assertRaises(exc):
                            with persisted(
                                fs, "k", _machine(), lock=mk()
                            ) as i:
                                after_commit(lambda: committed.append(1))
                                i.send("T")
                                raise exc()
                        self.assertEqual(committed, [])
                        self.assertEqual(self.ver(fs), 1)
                        self.assertNotIn("save", fs.log)
                        self.assert_free(fs)

    def test_start_failure_is_typed_and_lock_released(self) -> None:
        def boom(i: Any, c: Any, e: Any, a: Any) -> None:
            raise RuntimeError("boom")

        m = create_machine(
            {
                "id": "f",
                "initial": "s",
                "actionErrorPolicy": "fail",
                "states": {"s": {"entry": "boom"}},
            },
            logic=MachineLogic(actions={"boom": boom}),
        )
        st = MemoryStore()
        # 📝 contract: `fail` policy STOPS the machine; `start()` itself does
        # not raise, so the body sees a stopped interpreter (documented) and
        # the stopped state is what is persisted.
        with persisted(st, "f", m, lock=PessimisticLock(timeout=1)) as i:
            self.assertEqual(i.status, "stopped")
        self.assertEqual(
            json.loads(st.load("f").snapshot)["status"], "stopped"
        )
        # and the NEXT block fails typed, never wedged, lock free
        from src.xstate_statemachine.exceptions import InvalidConfigError

        with self.assertRaises(InvalidConfigError):
            with persisted(st, "f", m, lock=PessimisticLock(timeout=1)):
                self.fail("body ran")
        with (
            persisted(st, "f", m, lock=PessimisticLock(timeout=1))
            if False
            else (
                persisted(st, "g", _machine(), lock=PessimisticLock(timeout=1))
            )
        ):
            pass

    def test_raising_plugin_is_contained_body_runs(self) -> None:
        class P(PluginBase):  # type: ignore[type-arg]
            def on_interpreter_start(self, interpreter: Any) -> None:
                raise RuntimeError("plug")

        st = MemoryStore()
        with persisted(st, "k", _machine(), plugins=[P()]) as i:
            self.assertEqual(i.status, "running")
            i.send("T")
        self.assertEqual(self.ver(st), 1)

    def test_runaway_start_is_typed_nothing_written_clock_clean(self) -> None:
        loop = create_machine(
            {
                "id": "r",
                "initial": "a",
                "states": {"a": {"always": "b"}, "b": {"always": "a"}},
            }
        )
        st = MemoryStore()
        cl = SimulatedClock()
        try:
            with persisted(st, "k", loop, clock=cl) as i:
                self.assertEqual(i.status, "running")
        except Exception as exc:  # typed engine error, not a hang
            from src.xstate_statemachine.exceptions import XStateMachineError

            self.assertIsInstance(exc, XStateMachineError)
        self.assertEqual(cl.pending, 0)


# =============================================================================
# load_interpreter / create_if_missing / migrator
# =============================================================================
V1 = {
    "id": "o",
    "version": "1",
    "initial": "a",
    "context": {"n": 0},
    "states": {"a": {"on": {"X": {}}}},
}


class TestLoadInterpreterAndMigrator(_Base):
    def test_load_interpreter_returns_started(self) -> None:
        st = MemoryStore()
        self.seed(st)
        i, v = load_interpreter(st, "k", _machine())
        self.assertEqual((i.status, v, i.store_key), ("running", 1, "k"))
        self.assertEqual(i.context["n"], 1)
        i.stop()

    def test_missing_key_without_create_names_key(self) -> None:
        st = MemoryStore()
        with self.assertRaises(KeyNotFoundError) as cm:
            load_interpreter(
                st, "nope-key", _machine(), create_if_missing=False
            )
        self.assertIn("nope-key", str(cm.exception))
        self.assertEqual(cm.exception.key, "nope-key")
        with self.assertRaises(StoreError):
            load_interpreter(
                st, "nope-key", _machine(), create_if_missing=False
            )
        with self.assertRaises(KeyNotFoundError):
            with persisted(
                st, "nope-key", _machine(), create_if_missing=False
            ):
                self.fail("body ran")

    def test_create_if_missing_starts_fresh_not_saved_until_caller_saves(
        self,
    ) -> None:
        st = MemoryStore()
        i, v = load_interpreter(st, "new", _machine())
        self.assertEqual((i.status, v, i.store_key), ("running", 0, "new"))
        self.assertIsNone(st.load("new"))  # documented: NOT saved implicitly
        i.stop()
        # persisted() creates + saves on clean exit
        with persisted(st, "new2", _machine()):
            self.assertIsNone(st.load("new2"))
        self.assertEqual(self.ver(st, "new2"), 1)

    def test_migrator_applies_once_and_saves_new_version(self) -> None:
        st = MemoryStore()
        with persisted(st, "o", create_machine(V1)):
            pass
        calls: List[int] = []
        mig = SnapshotMigrator()

        def up(b: Dict[str, Any]) -> Dict[str, Any]:
            calls.append(1)
            b["context"]["n"] = 5
            return b

        mig.add("1", "2", up)
        m2 = create_machine(dict(V1, version="2"))
        with persisted(st, "o", m2, migrator=mig) as i:
            self.assertEqual(i.context["n"], 5)
        self.assertEqual(calls, [1])
        rec = st.load("o")
        self.assertEqual(rec.machine_version, "2")
        self.assertEqual(json.loads(rec.snapshot)["context"]["n"], 5)
        with persisted(st, "o", m2, migrator=mig):  # already v2: no re-run
            pass
        self.assertEqual(calls, [1])

    def test_unregistered_step_is_version_mismatch(self) -> None:
        st = MemoryStore()
        with persisted(st, "o", create_machine(V1)):
            pass
        mig = SnapshotMigrator()
        mig.add("2", "3", lambda b: b)
        for kw in ({}, {"migrator": mig}, {"on_version_mismatch": "error"}):
            with self.subTest(kw=kw):
                with self.assertRaises(MachineVersionMismatchError):
                    with persisted(
                        st, "o", create_machine(dict(V1, version="3")), **kw
                    ):
                        self.fail("body ran")
        self.assertEqual(self.ver(st, "o"), 1)
        self.assert_free(st, "k")
        # documented escape hatch: warn restores as-is
        with persisted(
            st,
            "o",
            create_machine(dict(V1, version="3")),
            on_version_mismatch="warn",
        ):
            pass

    def test_raising_migrator_step_is_typed_nothing_written(self) -> None:
        st = FaultyStore(MemoryStore())
        with persisted(st, "o", create_machine(V1)):
            pass
        mig = SnapshotMigrator()

        def bad(b: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError("step blew up")

        mig.add("1", "2", bad)
        st.log.clear()
        with self.assertRaises(Exception) as cm:
            with persisted(
                st,
                "o",
                create_machine(dict(V1, version="2")),
                migrator=mig,
                lock=PessimisticLock(timeout=1),
            ):
                self.fail("body ran")
        self.assertIn("step blew up", str(cm.exception))
        self.assertNotIn("save", st.log)
        self.assertEqual(self.ver(st, "o"), 1)
        self.assertEqual(st.load("o").machine_version, "1")


# =============================================================================
# persisted_retry / lock.run / constructors
# =============================================================================
class TestRetryContracts(_Base):
    def test_run_conflict_from_body_is_retried_then_attempts_recorded(
        self,
    ) -> None:
        st = MemoryStore()
        calls: List[int] = []

        def fn(i: Any) -> str:
            calls.append(1)
            if len(calls) < 3:
                raise ConflictError("k", 1, 2)  # raised by the BODY
            return "ok"

        lk = OptimisticLock(retries=5, rng=lambda: 0.0)
        self.assertEqual(
            persisted_retry(st, "k", _machine(), fn, lock=lk), "ok"
        )
        self.assertEqual(len(calls), 3)  # documented: retried like a save's

    def test_run_conflict_exhausts_bounded(self) -> None:
        st = MemoryStore()
        calls: List[int] = []

        def fn(i: Any) -> None:
            calls.append(1)
            raise ConflictError("k", 1, 2)

        lk = OptimisticLock(retries=3, rng=lambda: 0.0)
        with self.assertRaises(ConflictError) as cm:
            persisted_retry(st, "k", _machine(), fn, lock=lk)
        self.assertEqual(len(calls), 4)
        self.assertEqual(cm.exception.attempts, 4)  # type: ignore[attr-defined]
        self.assertIsNone(st.load("k"))

    def test_block_conflict_from_body_propagates_no_retry(self) -> None:
        st = MemoryStore()
        calls: List[int] = []
        with self.assertRaises(ConflictError):
            with persisted(st, "k", _machine()):
                calls.append(1)
                raise ConflictError("k", 1, 2)
        self.assertEqual(calls, [1])

    def test_non_conflict_not_retried_value_and_args_passthrough(self) -> None:
        st = MemoryStore()
        calls: List[int] = []

        def bad(i: Any) -> None:
            calls.append(1)
            raise ValueError("nope")

        with self.assertRaises(ValueError):
            persisted_retry(st, "k", _machine(), bad)
        self.assertEqual(calls, [1])
        self.assertIsNone(st.load("k"))

        def good(i: Any) -> int:
            i.send("T")
            return i.context["n"]

        self.assertEqual(persisted_retry(st, "k", _machine(), good), 1)
        self.assertEqual(
            persisted_retry(
                st,
                "k",
                _machine(),
                good,
                lock=NoLock(),
                clock=SimulatedClock(),
            ),
            2,
        )

    def test_pessimistic_and_nolock_run_do_not_retry_conflict(self) -> None:
        for lk in (PessimisticLock(timeout=1), NoLock()):
            calls: List[int] = []

            def fn(i: Any) -> None:
                calls.append(1)
                raise ConflictError("k", 1, 2)

            with self.subTest(lock=type(lk).__name__):
                with self.assertRaises(ConflictError):
                    persisted_retry(
                        MemoryStore(), "k", _machine(), fn, lock=lk
                    )
                self.assertEqual(calls, [1])

    def test_constructor_validation(self) -> None:
        with self.assertRaises(ValueError):
            OptimisticLock(retries=-1)
        for bad in ("3", 1.5, None, True):
            with self.subTest(retries=bad):
                with self.assertRaises(TypeError):
                    OptimisticLock(retries=bad)  # type: ignore[arg-type]
        for bad_b in (3, "fast", lambda n: 0):
            with self.subTest(backoff=bad_b):
                with self.assertRaises(TypeError):
                    OptimisticLock(backoff=bad_b)  # type: ignore[arg-type]
        OptimisticLock(retries=0, backoff=RetryPolicy(max_attempts=2))
        with self.assertRaises(ValueError):
            PessimisticLock(timeout=-1)

    def test_retry_wrapper_is_not_a_decorator_but_fn_name_irrelevant(
        self,
    ) -> None:
        # `persisted_retry` is a CALL, not a decorator: it must not mutate
        # or wrap `fn`.
        def fn(i: Any) -> int:
            """doc"""
            return 1

        persisted_retry(MemoryStore(), "k", _machine(), fn)
        self.assertEqual((fn.__name__, fn.__doc__), ("fn", "doc"))


# =============================================================================
# bounds: every wait in locking.py is bounded
# =============================================================================
class TestBounds(_Base):
    """locking.py waits (grep: `time.sleep` in `OptimisticLock._sleep`,
    `store.lock(timeout=...)` in `PessimisticLock.acquire`/`apersisted`;
    there is no bare acquire/wait/join):

    1. `_sleep`           -> bounded by RetryPolicy.max_ms and `retries`.
    2. pessimistic lock   -> bounded by `timeout` (LockTimeoutError).
    3. apersisted lock    -> bounded by `timeout` through the adapter.
    """

    def test_optimistic_retry_loop_terminates_and_sleeps_bounded(self) -> None:
        pol = RetryPolicy(
            max_attempts=3, base_ms=1.0, factor=2.0, max_ms=5.0, jitter="none"
        )
        lk = OptimisticLock(retries=4, backoff=pol)
        slept: List[float] = []
        with mock.patch("time.sleep", side_effect=slept.append):
            with self.assertRaises(ConflictError):
                persisted_retry(
                    MemoryStore(),
                    "k",
                    _machine(),
                    lambda i: (_ for _ in ()).throw(ConflictError("k", 1, 2)),
                    lock=lk,
                )
        self.assertEqual(len(slept), 4)
        self.assertTrue(all(s <= 0.005 + 1e-9 for s in slept))

    def test_pessimistic_wait_is_bounded_by_timeout(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                st = self.make(kind)
                self.seed(st)
                holder_in = threading.Event()
                release = threading.Event()

                def hold() -> None:
                    with st.lock("k", timeout=5):
                        holder_in.set()
                        release.wait(10)

                t = threading.Thread(target=hold, daemon=True)
                t.start()
                self.assertTrue(holder_in.wait(5))
                t0 = time.monotonic()
                try:
                    with self.assertRaises(LockTimeoutError):
                        with persisted(
                            st,
                            "k",
                            _machine(),
                            lock=PessimisticLock(timeout=0.2),
                        ):
                            self.fail("body ran")
                    self.assertLess(time.monotonic() - t0, 3.0)
                finally:
                    release.set()
                    t.join(5)
                self.assertFalse(t.is_alive())
                self.assertEqual(self.ver(st), 1)

    def test_apersisted_pessimistic_wait_is_bounded(self) -> None:
        st = MemoryStore()
        self.seed(st)

        async def main() -> float:
            with st.lock("k", timeout=5):  # held by this thread's sync call
                t0 = time.monotonic()
                with self.assertRaises(LockTimeoutError):
                    async with apersisted(
                        st, "k", _machine(), lock=PessimisticLock(timeout=0.2)
                    ):
                        self.fail("body ran")
                return time.monotonic() - t0

        # MemoryStore lock is non-reentrant across threads: adapter thread
        # must time out.
        self.assertLess(asyncio.run(main()), 3.0)


# =============================================================================
# async failure paths
# =============================================================================
class TestAsyncFailures(unittest.IsolatedAsyncioTestCase):
    async def test_load_error_and_save_error_async(self) -> None:
        for exc in (StoreError, OSError, ConflictError):
            fs = FaultyStore(MemoryStore())
            with persisted(fs, "k", _machine()) as i:
                i.send("T")
            fs.fail_next["load"] = exc
            ran: List[int] = []
            with self.assertRaises(exc):
                async with apersisted(fs, "k", _machine()):
                    ran.append(1)
            self.assertEqual(ran, [])
            fs.fail_next["save"] = exc
            with self.assertRaises(exc):
                async with apersisted(
                    fs, "k", _machine(), lock=PessimisticLock(timeout=1)
                ) as i:
                    await i.send("T", wait=True)
                    ran.append(2)
            self.assertEqual(ran, [2])
            self.assertEqual(fs.load("k").version, 1)
            async with apersisted(
                fs, "k", _machine(), lock=PessimisticLock(timeout=1)
            ):
                pass  # lock free

    async def test_cancel_and_keyboardinterrupt_in_body(self) -> None:
        fs = FaultyStore(MemoryStore())
        with persisted(fs, "k", _machine()):
            pass
        for exc in (asyncio.CancelledError, KeyboardInterrupt):
            with self.assertRaises(exc):
                async with apersisted(
                    fs, "k", _machine(), lock=PessimisticLock(timeout=1)
                ) as i:
                    await i.send("T", wait=True)
                    raise exc()
            self.assertEqual(fs.load("k").version, 1)
        async with apersisted(
            fs, "k", _machine(), lock=PessimisticLock(timeout=1)
        ):
            pass

    async def test_async_drift_before_body(self) -> None:
        st = MemoryStore()
        with persisted(st, "k", _machine()):
            pass
        with self.assertRaises(SnapshotDriftError):
            async with apersisted(st, "k", _machine(mid="zz")):
                self.fail("body ran")
        changed = create_machine(
            {
                "id": "c",
                "initial": "s",
                "context": {"n": 0},
                "states": {
                    "s": {"on": {"T": {"actions": "inc"}, "U": "t"}},
                    "t": {},
                },
            },
            logic=MachineLogic(actions={"inc": _inc}),
        )
        with self.assertRaises(SnapshotDriftError):
            async with apersisted(st, "k", changed):
                self.fail("body ran")
        async with apersisted(
            st, "k", changed, verify_machine_hash=False
        ) as i:
            self.assertEqual(i.context["n"], 0)

    async def test_adapter_for_sync_store_closed_after_failures(self) -> None:
        st = MemoryStore()
        # 📝 `_owned_adapter` closes the adapter via the loop's DEFAULT
        #    executor (review M1: a sync `shutdown(wait=True)` stalled the
        #    loop). That executor keeps one idle thread for the loop's
        #    life -- asyncio's, not ours. Warm it before the baseline so
        #    the assertion measures adapter threads only.
        await asyncio.get_running_loop().run_in_executor(None, lambda: None)
        base = threading.active_count()
        for n in range(30):
            try:
                async with apersisted(st, "k%d" % n, _machine()) as i:
                    await i.send("T", wait=True)
                    if n % 2:
                        raise RuntimeError("x")
            except RuntimeError:
                pass
        gc.collect()
        self.assertLessEqual(threading.active_count(), base)


# =============================================================================
# leaks
# =============================================================================
def _lib_bytes(snap: "tracemalloc.Snapshot") -> int:
    return sum(
        s.size
        for s in snap.statistics("filename")
        if LIB in s.traceback[0].filename
    )


def _leak_ceiling() -> int:
    """📏 Bytes of library-attributed growth allowed between the N/2 and N
    readings. Under `pytest --cov` on CPython <= 3.13 the C tracer's own
    per-line bookkeeping is attributed to the *library frame executing*,
    so the reading drifts with how much library code the previous ~6 000
    tests exercised (the #305 lesson; the full coverage job read 3.35 MB
    here with every byte reading 0 in isolation and on 3.14). A real leak
    is per-cycle and LINEAR: 10 000 cycles x even 1 KB = 10 MB. Strict
    without a tracer; "far below a real leak" with one."""
    tracer = sys.gettrace() is not None or (
        hasattr(sys, "monitoring")
        and sys.monitoring.get_tool(sys.monitoring.COVERAGE_ID) is not None
    )
    return 6_000_000 if tracer else 256 * 1024


def _cycle_store(store: Any, key: str, n: int) -> None:
    m = _machine()
    for _ in range(n):
        with persisted(store, key, m) as i:
            i.send("T")
            i.send("T")
            i.send("T")


class TestLeaks(_Base):
    @staticmethod
    def _settled_thread_count() -> int:
        """Thread count after giving threads from EARLIER tests a moment to
        exit. In the full suite this class can run right after a file whose
        daemon workers (SQLite pool, timer threads) are still winding down;
        counting them as "ours" failed the memory subtest once on the
        coverage job while every byte reading was 0."""
        deadline = time.monotonic() + 2.0
        last = threading.active_count()
        while time.monotonic() < deadline:
            time.sleep(0.05)
            now = threading.active_count()
            if now >= last:
                return now
            last = now
        return last

    def _measure(self, store: Any, n: int) -> Dict[str, Any]:
        _cycle_store(store, "warm", 50)
        gc.collect()
        tasks0 = self._settled_thread_count()
        tracemalloc.start()
        try:
            _cycle_store(store, "leak", n // 2)
            gc.collect()
            a = _lib_bytes(tracemalloc.take_snapshot())
            _cycle_store(store, "leak", n - n // 2)
            gc.collect()
            b = _lib_bytes(tracemalloc.take_snapshot())
        finally:
            tracemalloc.stop()
        return {
            "half": a,
            "full": b,
            "threads": self._settled_thread_count() - tasks0,
        }

    def test_sync_cycles_do_not_leak(self) -> None:
        counts = {"memory": 10000, "file": 300, "sqlite": 3000}
        for kind in KINDS:
            with self.subTest(kind=kind):
                r = self._measure(self.make(kind), counts[kind])
                print(
                    "LEAK %s n=%d half=%d full=%d threads=+%d"
                    % (kind, counts[kind], r["half"], r["full"], r["threads"])
                )
                # second half must not grow the library's footprint
                self.assertLess(r["full"] - r["half"], _leak_ceiling())
                # no thread created by the cycles survives them (a thread
                # from an earlier test EXITING meanwhile is not a leak)
                self.assertLessEqual(r["threads"], 0)

    def test_async_cycles_do_not_leak_tasks_or_threads(self) -> None:
        async def main() -> Dict[str, Any]:
            st = MemoryStore()
            m = _machine()

            async def run(n: int) -> None:
                for _ in range(n):
                    async with apersisted(st, "a", m) as i:
                        for _ in range(3):
                            await i.send("T", wait=True)

            await run(20)
            # warm the loop's default executor (adapter close goes through
            # it; its one idle thread is asyncio's for the loop's life)
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: None
            )
            gc.collect()
            t0 = threading.active_count()
            tasks0 = len(asyncio.all_tasks())
            tracemalloc.start()
            try:
                await run(1000)
                gc.collect()
                a = _lib_bytes(tracemalloc.take_snapshot())
                await run(1000)
                gc.collect()
                b = _lib_bytes(tracemalloc.take_snapshot())
            finally:
                tracemalloc.stop()
            return {
                "half": a,
                "full": b,
                "threads": threading.active_count() - t0,
                "tasks": len(asyncio.all_tasks()) - tasks0,
            }

        r = asyncio.run(main())
        print(
            "LEAK async n=2000 half=%(half)d full=%(full)d "
            "threads=+%(threads)d tasks=+%(tasks)d" % r
        )
        self.assertLess(r["full"] - r["half"], _leak_ceiling())
        self.assertEqual(r["threads"], 0)
        self.assertEqual(r["tasks"], 0)

    def test_async_sync_store_adapters_do_not_grow_threads(self) -> None:
        async def main() -> int:
            st = MemoryStore()
            # warm the loop's default executor (see the sibling test above)
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: None
            )
            base = threading.active_count()
            for _ in range(1000):
                async with apersisted(st, "a", _machine()):
                    pass
            gc.collect()
            return threading.active_count() - base

        self.assertLessEqual(asyncio.run(main()), 0)

    def test_closing_the_owned_adapter_does_not_block_the_loop(self) -> None:
        # 🐛 Review M1 (fixed): `astore.close()` is a blocking executor
        #    join; called synchronously from the async `finally` it stalled
        #    the loop while a slow store call finished. A heartbeat task
        #    must keep ticking during the exit.
        class Slow(MemoryStore):
            def save(self, *a: Any, **kw: Any) -> int:
                time.sleep(0.4)
                return super().save(*a, **kw)

        async def main() -> int:
            ticks = 0
            stop = asyncio.Event()

            async def heartbeat() -> None:
                nonlocal ticks
                while not stop.is_set():
                    ticks += 1
                    await asyncio.sleep(0.02)

            hb = asyncio.create_task(heartbeat())
            st = Slow()
            async with apersisted(st, "k", _machine()) as i:
                await i.send("T", wait=True)
            stop.set()
            await hb
            return ticks

        # the exit (save ~0.4 s + close) must have let the heartbeat run
        # many times; a blocked loop would yield ~1-2 ticks
        self.assertGreater(asyncio.run(main()), 8)


# =============================================================================
# durable deadline with a SimulatedClock
# =============================================================================
class TestDeadlinePersistence(_Base):
    def test_after_timer_persisted_not_fired_on_exit(self) -> None:
        m = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {"a": {"after": {"1000": "b"}}, "b": {}},
            }
        )
        for kind in KINDS:
            with self.subTest(kind=kind):
                st = self.make(kind)
                cl = SimulatedClock()
                with persisted(st, "t", m, clock=cl):
                    self.assertEqual(cl.pending, 1)
                rec = st.load("t")
                self.assertEqual(len(rec.deadlines), 1)
                self.assertEqual(rec.deadlines[0].delay_ms, 1000)
                self.assertEqual(
                    json.loads(rec.snapshot)["state_ids"], ["t.a"]
                )
                self.assertEqual(cl.pending, 0)  # stopped, timer cancelled
                cl.increment(5000)  # nothing fires after exit
                self.assertEqual(
                    json.loads(st.load("t").snapshot)["state_ids"], ["t.a"]
                )
                self.assertEqual(self.ver(st, "t"), 1)

    def test_async_deadline_persisted(self) -> None:
        m = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {"a": {"after": {"1000": "b"}}, "b": {}},
            }
        )

        async def main() -> None:
            st = MemoryStore()
            cl = SimulatedClock()
            async with apersisted(st, "t", m, clock=cl):
                pass
            self.assertEqual(len(st.load("t").deadlines), 1)
            self.assertEqual(cl.pending, 0)

        asyncio.run(main())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
