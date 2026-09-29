# tests/persistence/test_store_contract.py
"""#259: the `StateStore` contract, parametrised over every backend.

Every backend must pass every test here; a contrib backend (Django,
SQLAlchemy, Redis) reuses `STORE_FACTORIES` by appending its own factory.
"""

from __future__ import annotations

import asyncio
import importlib.util
import threading
import time
from typing import Any, Callable, Dict, Iterator, List

import pytest

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import (
    ConflictError,
    Deadline,
    FileStore,
    InvalidKeyError,
    LockTimeoutError,
    MemoryStore,
    SnapshotTooLargeError,
    SQLiteStore,
    StateStore,
    StoredSnapshot,
    aload_interpreter,
    as_async,
    load_interpreter,
    save_interpreter,
)
from src.xstate_statemachine.persistence.helpers import KeyNotFoundError

# --------------------------------------------------------------------------
# factories
# --------------------------------------------------------------------------
STORE_FACTORIES: Dict[str, Callable[[Any], StateStore]] = {
    "memory": lambda tmp: MemoryStore(),
    "file": lambda tmp: FileStore(tmp / "store"),
    "sqlite": lambda tmp: SQLiteStore(tmp / "store.db"),
}


def _sqlalchemy_store(tmp: Any, **kw: Any) -> StateStore:
    """#284: `SQLAlchemyStore` on a SQLite file -- a contrib backend held
    to the SAME contract. Registered only when the extra is installed."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

    tmp.mkdir(parents=True, exist_ok=True)
    eng = create_engine(
        f"sqlite:///{tmp / 'sqla.db'}", connect_args={"timeout": 30}
    )
    return SQLAlchemyStore(sessionmaker(eng), **kw)


if importlib.util.find_spec("sqlalchemy") is not None:
    STORE_FACTORIES["sqlalchemy"] = _sqlalchemy_store


@pytest.fixture(params=sorted(STORE_FACTORIES))
def store(request: Any, tmp_path: Any) -> Iterator[StateStore]:
    s = STORE_FACTORIES[request.param](tmp_path)
    yield s
    close = getattr(s, "close", None)
    if callable(close):
        close()


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
    c["n"] = c["n"] + 1


def machine():
    return create_machine(CFG, logic=MachineLogic(actions={"inc": _inc}))


def snapshot_of(n_events: int = 0) -> str:
    i = SyncInterpreter(machine()).start()
    for _ in range(n_events):
        i.send("GO")
    blob = i.get_snapshot()
    i.stop()
    return blob


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------
class TestContract:
    def test_protocol_conformance(self, store: StateStore) -> None:
        assert isinstance(store, StateStore)
        h = store.health()
        assert h["ok"] is True and isinstance(h["backend"], str)

    def test_load_missing_is_none(self, store: StateStore) -> None:
        assert store.load("nope") is None

    def test_round_trip_and_versions(self, store: StateStore) -> None:
        blob = snapshot_of(2)
        assert store.save("k", blob, machine_version="7") == 1
        rec = store.load("k")
        assert isinstance(rec, StoredSnapshot)
        assert rec.key == "k" and rec.snapshot == blob
        assert rec.version == 1 and rec.machine_version == "7"
        assert rec.updated_at > time.time() - 60
        assert rec.deadlines == ()
        assert store.save("k", blob) == 2  # unconditional
        assert store.load("k").version == 2

    def test_expected_version_conflict(self, store: StateStore) -> None:
        blob = snapshot_of()
        assert store.save("k", blob, expected_version=0) == 1
        with pytest.raises(ConflictError) as ei:
            store.save("k", blob, expected_version=0)  # someone created it
        assert ei.value.key == "k"
        assert ei.value.expected == 0 and ei.value.actual == 1
        assert store.save("k", blob, expected_version=1) == 2
        with pytest.raises(ConflictError):
            store.save("k", blob, expected_version=1)
        assert store.load("k").version == 2  # nothing was written on conflict

    def test_conflict_on_missing_key(self, store: StateStore) -> None:
        with pytest.raises(ConflictError) as ei:
            store.save("ghost", snapshot_of(), expected_version=3)
        assert ei.value.actual is None

    def test_delete_and_forget(self, store: StateStore) -> None:
        store.save("k", snapshot_of())
        assert store.delete("k") is True
        assert store.delete("k") is False
        assert store.load("k") is None
        store.save("k", snapshot_of())
        counts = store.forget("k")
        assert counts["snapshots"] == 1
        assert store.load("k") is None
        assert store.forget("k")["snapshots"] == 0

    def test_list_keys_prefix_limit_sorted(self, store: StateStore) -> None:
        for k in ("order-3", "order-1", "user-1", "order-2"):
            store.save(k, snapshot_of())
        assert store.list_keys(prefix="order-") == [
            "order-1",
            "order-2",
            "order-3",
        ]
        assert store.list_keys(prefix="order-", limit=2) == [
            "order-1",
            "order-2",
        ]
        assert store.list_keys() == ["order-1", "order-2", "order-3", "user-1"]
        assert store.list_keys(prefix="zzz") == []

    def test_deadlines_round_trip(self, store: StateStore) -> None:
        d = Deadline("o.a", 1, 1_700_000_000.5, 5000, "after.5000.o.a")
        store.save("k", snapshot_of(), deadlines=[d])
        assert store.load("k").deadlines == (d,)
        store.save("k", snapshot_of())  # no deadlines -> cleared
        assert store.load("k").deadlines == ()

    def test_lock_is_mutually_exclusive(self, store: StateStore) -> None:
        order: List[str] = []
        entered = threading.Event()
        release = threading.Event()

        def holder() -> None:
            with store.lock("k", timeout=5):
                order.append("A-in")
                entered.set()
                release.wait(5)
                order.append("A-out")

        def waiter() -> None:
            entered.wait(5)
            with store.lock("k", timeout=5):
                order.append("B-in")

        ta, tb = threading.Thread(target=holder), threading.Thread(
            target=waiter
        )
        ta.start()
        tb.start()
        entered.wait(5)
        time.sleep(0.1)
        assert order == ["A-in"]  # B is blocked
        release.set()
        ta.join(5)
        tb.join(5)
        assert order == ["A-in", "A-out", "B-in"]

    def test_lock_timeout(self, store: StateStore) -> None:
        entered = threading.Event()
        release = threading.Event()

        def holder() -> None:
            with store.lock("k", timeout=5):
                entered.set()
                release.wait(5)

        t = threading.Thread(target=holder)
        t.start()
        entered.wait(5)
        try:
            with pytest.raises(LockTimeoutError):
                with store.lock("k", timeout=0.2):
                    pass
        finally:
            release.set()
            t.join(5)

    def test_size_cap_on_save_and_load(self, store: StateStore, tmp_path):
        small = STORE_FACTORIES[store.backend](tmp_path / "small")
        small.max_snapshot_bytes = 64
        with pytest.raises(SnapshotTooLargeError) as ei:
            small.save("k", snapshot_of())
        assert ei.value.limit == 64
        # Poisoned store: written with a big cap, read with a small one.
        store.save("k", snapshot_of())
        store.max_snapshot_bytes = 64
        with pytest.raises(SnapshotTooLargeError):
            store.load("k")

    def test_invalid_keys(self, store: StateStore) -> None:
        for bad in ("", "x" * 201, "a\x00b"):
            with pytest.raises(InvalidKeyError):
                store.save(bad, snapshot_of())
        with pytest.raises(InvalidKeyError):
            store.load("")

    def test_restore_reproduces_state_and_context(
        self, store: StateStore
    ) -> None:
        i = SyncInterpreter(machine()).start()
        i.send("GO")
        i.send("GO")
        i.send("GO")
        store.save("k", i.get_snapshot())
        i.stop()
        rec = store.load("k")
        r = SyncInterpreter.from_snapshot(rec.snapshot, machine()).start()
        assert r.current_state_ids == {"o.b"}
        assert r.context["n"] == 3
        r.stop()

    def test_codec_seam(self, store: StateStore, tmp_path) -> None:
        class Rot:
            def encode(self, s: str) -> str:
                return s[::-1]

            def decode(self, s: str) -> str:
                return s[::-1]

        if store.backend == "memory":
            enc: Any = MemoryStore(codec=Rot())
            raw = None  # no shared location to peek at
        elif store.backend == "file":
            enc = FileStore(tmp_path / "enc", codec=Rot())
            raw = FileStore(tmp_path / "enc")
        elif store.backend == "sqlalchemy":
            enc = _sqlalchemy_store(tmp_path / "enc", codec=Rot())
            raw = _sqlalchemy_store(tmp_path / "enc")
        else:
            enc = SQLiteStore(tmp_path / "enc.db", codec=Rot())
            raw = SQLiteStore(tmp_path / "enc.db")
        blob = snapshot_of(1)
        enc.save("k", blob)
        assert enc.load("k").snapshot == blob
        if raw is not None:
            # The bytes at rest are transformed: a plain store on the same
            # location reads the encoded form.
            assert raw.load("k").snapshot == blob[::-1]

    # -- helpers ----------------------------------------------------------
    def test_load_save_interpreter_round_trip(self, store: StateStore):
        m = machine()
        interp, ver = load_interpreter(store, "order-1", m)
        assert ver == 0 and interp.status == "running"
        interp.send("GO")
        assert (
            save_interpreter(store, "order-1", interp, expected_version=0) == 1
        )
        interp.stop()
        interp2, ver2 = load_interpreter(store, "order-1", m)
        assert ver2 == 1
        assert interp2.context["n"] == 1 and interp2.matches("o.b")
        interp2.stop()
        with pytest.raises(KeyNotFoundError):
            load_interpreter(store, "missing", m, create_if_missing=False)
        rec = store.load("order-1")
        assert rec.machine_version == ""  # CFG declares no version

    def test_aload_interpreter(self, store: StateStore) -> None:
        async def go() -> Any:
            m = machine()
            interp, ver = await aload_interpreter(store, "k", m)
            assert ver == 0 and interp.status == "running"
            await interp.send("GO", wait=True)
            v = save_interpreter(store, "k", interp, expected_version=0)
            await interp.stop()
            interp2, ver2 = await aload_interpreter(store, "k", m)
            n = interp2.context["n"]
            await interp2.stop()
            return v, ver2, n

        assert asyncio.run(go()) == (1, 1, 1)

    def test_as_async_wrapper(self, store: StateStore) -> None:
        async def go() -> Any:
            a = as_async(store)
            assert await a.load("k") is None
            assert await a.save("k", snapshot_of(), expected_version=0) == 1
            with pytest.raises(ConflictError):
                await a.save("k", snapshot_of(), expected_version=0)
            async with a.lock("k", timeout=2):
                assert (await a.load("k")).version == 1
            assert await a.list_keys(prefix="k") == ["k"]
            assert (await a.health())["ok"] is True
            assert await a.forget("k") is not None
            assert await a.delete("k") is False
            return True

        assert asyncio.run(go())


# --------------------------------------------------------------------------
# optimistic-locking retry loop: deterministic fault injection (primary
# proof) + a small parallel smoke test
# --------------------------------------------------------------------------
class FaultyStore:
    """Wraps a store; forces a `ConflictError` on the k-th save attempt."""

    def __init__(self, inner: StateStore, fail_on: int) -> None:
        self.inner = inner
        self.fail_on = fail_on
        self.attempts = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def save(self, key: str, snapshot: str, **kw: Any) -> int:
        self.attempts += 1
        if self.attempts == self.fail_on:
            raise ConflictError(key, kw.get("expected_version"), -1)
        return self.inner.save(key, snapshot, **kw)


def _act_once(store: Any, key: str, m: Any) -> int:
    """One create → act → persist → discard cycle with retry."""
    tries = 0
    while True:
        tries += 1
        interp, ver = load_interpreter(store, key, m)
        try:
            interp.send("GO")
            save_interpreter(store, key, interp, expected_version=ver)
            return tries
        except ConflictError:
            continue
        finally:
            interp.stop()


class TestOptimisticRetry:
    def test_fault_injected_conflict_is_retried_once(
        self, store: StateStore
    ) -> None:
        m = machine()
        faulty = FaultyStore(store, fail_on=2)
        assert _act_once(faulty, "k", m) == 1
        assert _act_once(faulty, "k", m) == 2  # 2nd save forced to conflict
        rec = store.load("k")
        assert rec.version == 2
        r = SyncInterpreter.from_snapshot(rec.snapshot, m).start()
        assert r.context["n"] == 2  # exactly two increments, none lost
        r.stop()

    def test_parallel_smoke_no_lost_updates(self, store: StateStore) -> None:
        m = machine()
        threads, per_thread, keys = 4, 10, ("k1", "k2")
        errors: List[BaseException] = []

        def worker(n: int) -> None:
            try:
                for i in range(per_thread):
                    _act_once(store, keys[(n + i) % len(keys)], m)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        ts = [
            threading.Thread(target=worker, args=(n,)) for n in range(threads)
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        assert errors == []
        total = 0
        for k in keys:
            rec = store.load(k)
            r = SyncInterpreter.from_snapshot(rec.snapshot, m).start()
            assert r.context["n"] == rec.version
            total += r.context["n"]
            r.stop()
        assert total == threads * per_thread
