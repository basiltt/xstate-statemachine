# tests/persistence/test_locking.py
"""#260: lock strategies and `persisted()` / `apersisted()` /
`persisted_retry()` -- on every backend."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, Iterator, List

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import (
    ConflictError,
    FileStore,
    LockStrategy,
    LockTimeoutError,
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
from src.xstate_statemachine.persistence.helpers import KeyNotFoundError
from src.xstate_statemachine.persistence.locking import _DEFAULT_LOCK

STORE_FACTORIES = {
    "memory": lambda tmp: MemoryStore(),
    "file": lambda tmp: FileStore(tmp / "store"),
    "sqlite": lambda tmp: SQLiteStore(tmp / "store.db"),
}


@pytest.fixture(params=sorted(STORE_FACTORIES))
def store(request: Any, tmp_path: Any) -> Iterator[Any]:
    s = STORE_FACTORIES[request.param](tmp_path)
    yield s
    if hasattr(s, "close"):
        s.close()


CFG = {
    "id": "c",
    "initial": "s",
    "context": {"n": 0},
    "states": {
        "s": {"on": {"T": {"actions": "inc"}, "BOOM": {"actions": "boom"}}}
    },
}
ACTION_CALLS = {"inc": 0}


def _inc(i: Any, c: Any, e: Any, a: Any) -> None:
    ACTION_CALLS["inc"] += 1
    c["n"] += 1


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("action failed")


def machine():
    return create_machine(
        CFG, logic=MachineLogic(actions={"inc": _inc, "boom": _boom})
    )


class TestStrategies:
    def test_protocol_conformance(self) -> None:
        for s in (OptimisticLock(), PessimisticLock(), NoLock()):
            assert isinstance(s, LockStrategy)

    def test_default_lock_is_shared_and_stateless(self, store: Any) -> None:
        # The default argument is ONE instance; running it concurrently on
        # different keys must not leak state between callers.
        assert _DEFAULT_LOCK is not None
        m = machine()
        before = vars(_DEFAULT_LOCK).copy()

        def w(k: str) -> None:
            for _ in range(20):
                persisted_retry(store, k, m, lambda i: i.send("T"))

        ts = [threading.Thread(target=w, args=(f"k{n}",)) for n in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert vars(_DEFAULT_LOCK) == before  # no mutation
        for n in range(4):
            assert store.load(f"k{n}").version == 20

    def test_validation(self) -> None:
        with pytest.raises(ValueError):
            OptimisticLock(retries=-1)
        with pytest.raises(ValueError):
            PessimisticLock(timeout=-1)


class TestPersistedBlock:
    def test_persists_on_clean_exit(self, store: Any) -> None:
        m = machine()
        with persisted(store, "k", m) as i:
            i.send("T")
            assert i.status == "running"
        assert i.status == "stopped"  # discarded
        rec = store.load("k")
        assert rec.version == 1
        with persisted(store, "k", m) as i:
            assert i.context["n"] == 1
        assert store.load("k").version == 2

    def test_exception_in_block_writes_nothing(self, store: Any) -> None:
        m = machine()
        with persisted(store, "k", m) as i:
            i.send("T")
        before = store.load("k")
        with pytest.raises(ValueError, match="user"):
            with persisted(store, "k", m) as i:
                i.send("T")
                raise ValueError("user code failed")
        after = store.load("k")
        assert after.version == before.version
        assert after.snapshot == before.snapshot
        assert i.status == "stopped"

    def test_create_if_missing_false(self, store: Any) -> None:
        with pytest.raises(KeyNotFoundError):
            with persisted(store, "nope", machine(), create_if_missing=False):
                pass

    def test_plugins_attached_to_each_hydration(self, store: Any) -> None:
        from src.xstate_statemachine import PluginBase

        class P(PluginBase):
            def __init__(self) -> None:
                self.starts = 0

            def on_interpreter_start(self, i: Any) -> None:
                self.starts += 1

        p = P()
        m = machine()
        with persisted(store, "k", m, plugins=[p]):
            pass
        with persisted(store, "k", m, plugins=[p]):
            pass
        assert p.starts == 2

    def test_optimistic_block_raises_conflict_on_first_conflict(
        self, store: Any
    ) -> None:
        m = machine()
        with persisted(store, "k", m):
            pass
        with pytest.raises(ConflictError) as ei:
            with persisted(store, "k", m) as i:
                # A concurrent writer sneaks in while the block is open.
                persisted_retry(store, "k", m, lambda x: x.send("T"))
                i.send("T")
        assert ei.value.expected == 1 and ei.value.actual == 2
        # The block's own send was NOT persisted; the sneak's was.
        with persisted(store, "k", m, lock=NoLock()) as i:
            assert i.context["n"] == 1

    def test_nolock_last_writer_wins(self, store: Any) -> None:
        m = machine()
        with persisted(store, "k", m, lock=NoLock()):
            pass
        with persisted(store, "k", m, lock=NoLock()) as i:
            persisted_retry(store, "k", m, lambda x: x.send("T"))
            i.send("T")
        # no conflict; the block overwrote the sneak's increment
        assert store.load("k").version == 3  # create, sneak, block
        with persisted(store, "k", m, lock=NoLock()) as i:
            assert i.context["n"] == 1


class TestOptimisticRun:
    def test_retries_then_succeeds_and_counts_action_runs(
        self, store: Any
    ) -> None:
        """Forced conflicts on the first two attempts: fn (and the
        action inside it) runs 3 times for ONE logical send -- the X0.3
        guarantee the docs state."""
        m = machine()
        with persisted(store, "k", m):
            pass
        fn_calls = {"n": 0}
        ACTION_CALLS["inc"] = 0

        def fn(i: Any) -> str:
            fn_calls["n"] += 1
            if fn_calls["n"] <= 2:
                # simulate a concurrent writer between load and save
                store.save("k", store.load("k").snapshot)
            i.send("T")
            return "done"

        lock = OptimisticLock(retries=5, rng=lambda: 0.0)
        assert lock.run(store, "k", m, fn) == "done"
        assert fn_calls["n"] == 3
        assert ACTION_CALLS["inc"] == 3  # ran retries+1 times
        with persisted(store, "k", m, lock=NoLock()) as i:
            assert i.context["n"] == 1  # but only ONE increment persisted

    def test_gives_up_after_retries_with_attempts(self, store: Any) -> None:
        m = machine()
        with persisted(store, "k", m):
            pass

        def always_conflict(i: Any) -> None:
            store.save("k", store.load("k").snapshot)
            i.send("T")

        lock = OptimisticLock(retries=2, rng=lambda: 0.0)
        with pytest.raises(ConflictError) as ei:
            lock.run(store, "k", m, always_conflict)
        assert ei.value.attempts == 3  # type: ignore[attr-defined]

    def test_retries_zero_behaves_like_block(self, store: Any) -> None:
        m = machine()
        with persisted(store, "k", m):
            pass

        def conflict_once(i: Any) -> None:
            store.save("k", store.load("k").snapshot)

        with pytest.raises(ConflictError):
            OptimisticLock(retries=0).run(store, "k", m, conflict_once)


class TestPessimistic:
    def test_serialises_and_releases_on_exception(self, store: Any) -> None:
        m = machine()
        lock = PessimisticLock(timeout=5)
        order: List[str] = []
        entered, release = threading.Event(), threading.Event()

        def holder() -> None:
            with persisted(store, "k", m, lock=lock) as i:
                order.append("A-in")
                entered.set()
                release.wait(5)
                i.send("T")
                order.append("A-out")

        def waiter() -> None:
            entered.wait(5)
            with persisted(store, "k", m, lock=lock) as i:
                order.append(f"B-in n={i.context['n']}")

        ta, tb = threading.Thread(target=holder), threading.Thread(
            target=waiter
        )
        ta.start()
        tb.start()
        entered.wait(5)
        time.sleep(0.1)
        assert order == ["A-in"]
        release.set()
        ta.join(5)
        tb.join(5)
        assert order == ["A-in", "A-out", "B-in n=1"]  # B saw A's write

        # Released on exception: a follow-up acquires immediately.
        with pytest.raises(RuntimeError):
            with persisted(store, "k", m, lock=lock):
                raise RuntimeError("x")
        t0 = time.monotonic()
        with persisted(store, "k", m, lock=PessimisticLock(timeout=1)):
            pass
        assert time.monotonic() - t0 < 0.9

    def test_lock_timeout(self, store: Any) -> None:
        m = machine()
        entered, release = threading.Event(), threading.Event()

        def holder() -> None:
            with persisted(store, "k", m, lock=PessimisticLock(timeout=5)):
                entered.set()
                release.wait(5)

        t = threading.Thread(target=holder)
        t.start()
        entered.wait(5)
        try:
            with pytest.raises(LockTimeoutError):
                with persisted(
                    store, "k", m, lock=PessimisticLock(timeout=0.2)
                ):
                    pass
        finally:
            release.set()
            t.join(5)

    def test_fencing_turns_expired_lock_into_conflict(self, store: Any):
        """A store whose lock 'expired' (simulated: another writer saved
        while we held it) must yield ConflictError, never a lost update."""
        m = machine()
        with persisted(store, "k", m):
            pass
        with pytest.raises(ConflictError):
            with persisted(store, "k", m, lock=PessimisticLock()) as i:
                # Simulate an expired lock: a writer that ignored it.
                store.save("k", store.load("k").snapshot)
                i.send("T")


@pytest.mark.parametrize("lock_name", ["optimistic", "pessimistic"])
def test_sixteen_threads_no_lost_updates(store: Any, lock_name: str) -> None:
    """16 × N increments on ONE key; exact total. N is small in PRs
    (XSM_STRESS_SAVES scales it; default 8 → 128 saves)."""
    import os

    per_thread = int(os.environ.get("XSM_STRESS_SAVES", "8"))
    m = machine()
    lock = (
        OptimisticLock(retries=1_000)
        if lock_name == "optimistic"
        else PessimisticLock(timeout=60)
    )
    errors: List[BaseException] = []

    def w() -> None:
        try:
            for _ in range(per_thread):
                persisted_retry(
                    store, "k", m, lambda i: i.send("T"), lock=lock
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [threading.Thread(target=w) for _ in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(300)
    assert errors == []
    with persisted(store, "k", m, lock=NoLock()) as i:
        assert i.context["n"] == 16 * per_thread
    assert store.load("k").version == 16 * per_thread + 1


class TestAsync:
    def test_apersisted_sync_and_async_store(self, store: Any) -> None:
        async def go() -> Dict[str, Any]:
            m = machine()
            async with apersisted(store, "k", m) as i:
                await i.send("T", wait=True)
            astore = as_async(store)
            async with apersisted(astore, "k", m) as i:
                await i.send("T", wait=True)
                n_inside = i.context["n"]
            rec = await astore.load("k")
            # exception → nothing written
            with pytest.raises(ValueError):
                async with apersisted(astore, "k", m) as i:
                    await i.send("T", wait=True)
                    raise ValueError("x")
            rec2 = await astore.load("k")
            # pessimistic + conflict fencing
            async with apersisted(astore, "k", m, lock=PessimisticLock()) as i:
                await i.send("T", wait=True)
            with pytest.raises(KeyNotFoundError):
                async with apersisted(
                    astore, "zz", m, create_if_missing=False
                ):
                    pass
            return {
                "n_inside": n_inside,
                "v": rec.version,
                "v2": rec2.version,
                "final": (await astore.load("k")).version,
            }

        out = asyncio.run(go())
        assert out == {"n_inside": 2, "v": 2, "v2": 2, "final": 3}

    def test_apersisted_conflict(self, store: Any) -> None:
        async def go() -> None:
            m = machine()
            async with apersisted(store, "k", m):
                pass
            with pytest.raises(ConflictError):
                async with apersisted(store, "k", m) as i:
                    store.save("k", store.load("k").snapshot)
                    await i.send("T", wait=True)

        asyncio.run(go())
