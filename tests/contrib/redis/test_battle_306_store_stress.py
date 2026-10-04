# tests/contrib/redis/test_battle_306_store_stress.py
"""#306 battle (adversary A): concurrency, script reload, client flavours
and leak checks for `RedisStore`. fakeredis by default; live server with
``XSM_REDIS_URL``."""

from __future__ import annotations

import asyncio
import json
import os
import random
import threading
import tracemalloc
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine.persistence import (
    ConflictError,
    PessimisticLock,
    as_async,
    persisted,
)
from src.xstate_statemachine.persistence.deadline import Deadline

from ..conftest import requires_extra
from .test_redis_specific import machine

pytestmark = requires_extra("redis")

LIVE = os.environ.get("XSM_REDIS_URL")
SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}
)


def _store(r: Any, prefix: str, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.redis import RedisStore

    return RedisStore(r, prefix=prefix, **kw)


def _dl(key: str, due: float) -> Deadline:
    return Deadline("m.a", 1, due, 1000, "after.1000.m.a")


class TestAtomicSave:
    def test_64_optimistic_savers_on_one_key(
        self, r: Any, prefix: str
    ) -> None:
        """Every version is won by exactly one saver; the index always
        mirrors the winning record (one member, its due time)."""
        s = _store(r, prefix)
        s.save("k", SNAP)
        gate = threading.Barrier(64)
        wins: List[int] = []
        lock = threading.Lock()

        def saver(n: int) -> None:
            gate.wait()
            for _ in range(5):
                v = s.load("k").version
                try:
                    nv = s.save(
                        "k",
                        SNAP,
                        expected_version=v,
                        deadlines=[_dl("k", float(n))],
                    )
                except ConflictError:
                    continue
                with lock:
                    wins.append(nv)

        ts = [threading.Thread(target=saver, args=(i,)) for i in range(64)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert sorted(wins) == list(range(2, 2 + len(wins)))  # no dupes
        rec = s.load("k")
        assert rec.version == 1 + len(wins)
        assert r.zcard(s.k.deadlines) == 1
        assert s.due_keys(1e9) == [("k", rec.deadlines[0].due_at_wall)]

    def test_1000_keys_index_consistent(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix)
        rng = random.Random(306)
        keys = [f"o|{i}" for i in range(1000)]

        def worker(chunk: List[str]) -> None:
            for k in chunk:
                s.save(k, SNAP, deadlines=[_dl(k, rng.uniform(0, 10))])
                if rng.random() < 0.3:
                    s.delete(k)

        ts = [
            threading.Thread(target=worker, args=(keys[i::8],))
            for i in range(8)
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        live = set(s.list_keys(limit=10_000))
        due = {k for k, _ in s.due_keys(1e9, limit=10_000)}
        assert due == live
        assert r.zcard(s.k.deadlines) == len(live)

    def test_delete_and_forget_race_save(self, r: Any, prefix: str) -> None:
        """No interleaving leaves an index member without its record."""
        s = _store(r, prefix)
        stop = threading.Event()

        def saver() -> None:
            while not stop.is_set():
                s.save("k", SNAP, deadlines=[_dl("k", 1.0)])

        def eraser() -> None:
            for i in range(300):
                (s.delete if i % 2 else s.forget)("k")

        t = threading.Thread(target=saver)
        t.start()
        eraser()
        stop.set()
        t.join(30)
        rec = s.load("k")
        assert r.zcard(s.k.deadlines) == (1 if rec else 0)
        if rec is None:
            with pytest.raises(ConflictError) as ei:
                s.save("k", SNAP, expected_version=3)
            assert ei.value.actual is None  # the `actual == -1` path


class TestFencedPersisted:
    def test_seeded_pessimistic_stress_no_lost_update(
        self, r: Any, prefix: str
    ) -> None:
        """8 workers, lock TTL shorter than some of the work: every
        increment either lands or raises ConflictError -- never lost."""
        s = _store(r, prefix, lock_ttl_ms=20)
        m = machine()
        with persisted(s, "k", m):
            pass
        landed: List[int] = []
        lk = threading.Lock()

        def worker(seed: int) -> None:
            rng = random.Random(seed)
            for _ in range(15):
                try:
                    with persisted(
                        s, "k", m, lock=PessimisticLock(timeout=5)
                    ) as i:
                        i.send("T")
                        if rng.random() < 0.2:
                            threading.Event().wait(0.03)  # outlive the lock
                except ConflictError:
                    continue
                with lk:
                    landed.append(1)

        ts = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        with persisted(s, "k", m) as i:
            assert i.context["n"] == len(landed)


class TestClientFlavours:
    def test_script_flush_mid_run(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix)
        s.save("k", SNAP)
        r.script_flush()  # NOSCRIPT on next EVALSHA -> redis-py reloads
        assert s.save("k", SNAP, expected_version=1) == 2
        with s.lock("k", timeout=0):
            r.script_flush()
        assert r.get(s.k.lock("k")) is None  # unlock reloaded too
        assert s.forget("k")["snapshots"] == 1

    @pytest.mark.parametrize("protocol", [2, 3])
    def test_decode_responses_and_resp3(
        self, r: Any, prefix: str, protocol: int
    ) -> None:
        if LIVE:
            import redis

            client = redis.Redis.from_url(
                LIVE, decode_responses=True, protocol=protocol
            )
        else:
            import fakeredis

            client = fakeredis.FakeRedis(
                server=r.connection_pool.connection_kwargs["server"],
                decode_responses=True,
                protocol=protocol,
            )
        s = _store(client, prefix)
        s.save("a|b", SNAP, deadlines=[_dl("a|b", 1.0)])
        rec = s.load("a|b")
        assert rec.snapshot == SNAP and rec.version == 1
        assert len(rec.deadlines) == 1
        assert s.due_keys(10.0) == [("a|b", 1.0)]
        assert s.list_keys() == ["a|b"]
        assert s.health()["ok"] is True
        client.close()


def _pool_size(client: Any) -> int:
    return len(getattr(client.connection_pool, "_available_connections", []))


class TestLeaks:
    def test_persisted_cycles_flat(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix)
        m = machine()
        n = 2000 if LIVE else 1000
        threads0 = threading.active_count()

        def cycles(count: int) -> None:
            for i in range(count):
                with persisted(
                    s, f"k{i % 50}", m, lock=PessimisticLock()
                ) as it:
                    it.send("T")

        cycles(n // 2)
        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()
        pool1 = _pool_size(r)
        cycles(n // 2)
        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(
            st.size_diff for st in snap2.compare_to(snap1, "filename")
        )
        assert growth < 2_000_000, growth
        assert _pool_size(r) <= max(pool1, 1)
        assert threading.active_count() <= threads0

    @pytest.mark.skipif(not LIVE, reason="real redis.asyncio connections")
    def test_async_store_asyncio_run_per_cycle(self, prefix: str) -> None:
        from src.xstate_statemachine.contrib.redis import AsyncRedisStore

        async def cycle(i: int) -> None:
            a = AsyncRedisStore(LIVE, prefix=prefix)
            try:
                await a.save(f"k{i}", SNAP)
                async with a.lock(f"k{i}", timeout=1):
                    assert (await a.load(f"k{i}")).version >= 1
            finally:
                await a.r.aclose()

        import redis

        probe = redis.Redis.from_url(LIVE)
        before = probe.info("clients")["connected_clients"]
        for i in range(200):
            asyncio.run(cycle(i))
        after = probe.info("clients")["connected_clients"]
        probe.close()
        assert after <= before + 2

    def test_as_async_executor_threads_flat(self, r: Any, prefix: str) -> None:
        a = as_async(_store(r, prefix))
        threads0 = threading.active_count()

        async def go() -> Dict[str, int]:
            for i in range(300):
                await a.save(f"k{i % 10}", SNAP)
                await a.load(f"k{i % 10}")
            return {"t": threading.active_count()}

        for _ in range(5):
            asyncio.run(go())
        assert threading.active_count() <= threads0 + 1
