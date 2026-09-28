# tests/contrib/redis/test_redis_specific.py
"""#306: behaviours specific to the Redis backends -- mandatory prefix,
glob escaping in list_keys, lock fencing, atomic forget, schema key,
async twin under apersisted, TTL."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.exceptions import InvalidConfigError, StoreError
from src.xstate_statemachine.persistence import (
    ConflictError,
    LockTimeoutError,
    PessimisticLock,
    apersisted,
    persisted,
)

from ..conftest import requires_extra

pytestmark = requires_extra("redis")

SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}
)
CFG = {
    "id": "c",
    "initial": "s",
    "context": {"n": 0},
    "states": {"s": {"on": {"T": {"actions": "inc"}}}},
}


def _inc(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] += 1


def machine():
    return create_machine(CFG, logic=MachineLogic(actions={"inc": _inc}))


class TestPrefix:
    @pytest.mark.parametrize("bad", ["", "   ", "a b", None])
    def test_prefix_mandatory(self, r: Any, bad: Any) -> None:
        from src.xstate_statemachine.contrib.redis import (
            RedisInbox,
            RedisLog,
            RedisStore,
        )

        for cls in (RedisStore, RedisInbox, RedisLog):
            with pytest.raises(InvalidConfigError):
                cls(r, prefix=bad)  # type: ignore[arg-type]

    def test_trailing_colon_stripped_and_schema_key(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore
        from src.xstate_statemachine.contrib.redis._keys import SCHEMA_VERSION

        s = RedisStore(r, prefix=prefix + ":")
        assert s.k.p == prefix
        assert int(r.get(f"{prefix}:schema")) == SCHEMA_VERSION
        r.set(f"{prefix}:schema", SCHEMA_VERSION + 3)
        with pytest.raises(StoreError, match="newer"):
            RedisStore(r, prefix=prefix)

    def test_namespaces_isolate(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        a = RedisStore(r, prefix=prefix + "-a")
        b = RedisStore(r, prefix=prefix + "-b")
        a.save("k", SNAP)
        assert b.load("k") is None and b.list_keys() == []
        for k in r.scan_iter(match=f"{prefix}-*"):
            r.delete(k)


class TestListKeysEscaping:
    def test_glob_metacharacters_match_literally(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import (
            RedisStore,
            escape_glob,
        )

        s = RedisStore(r, prefix=prefix)
        for k in (
            "order*1",
            "order*2",
            "orderX1",
            "order?1",
            "order[1]",
            "plain",
        ):
            s.save(k, SNAP)
        assert s.list_keys(prefix="order*") == ["order*1", "order*2"]
        assert s.list_keys(prefix="order?") == ["order?1"]
        assert s.list_keys(prefix="order[") == ["order[1]"]
        assert s.list_keys() == sorted(
            ["order*1", "order*2", "orderX1", "order?1", "order[1]", "plain"]
        )
        assert escape_glob("a*b?c[d]\\e") == "a\\*b\\?c\\[d\\]\\\\e"


class TestFencing:
    def test_expired_lock_yields_conflict_not_lost_update(
        self, r: Any, prefix: str
    ) -> None:
        """Lock TTL shorter than the work: the late saver gets ConflictError
        and the first writer's data wins (X0.3)."""
        from src.xstate_statemachine.contrib.redis import RedisStore

        store = RedisStore(r, prefix=prefix, lock_ttl_ms=50)
        m = machine()
        with persisted(store, "k", m):
            pass
        with pytest.raises(ConflictError):
            with persisted(
                store, "k", m, lock=PessimisticLock(timeout=1)
            ) as slow:
                slow.send("T")
                time.sleep(0.08)  # our lock expired in Redis...
                # ...so a second worker gets in and saves first.
                with persisted(
                    store, "k", m, lock=PessimisticLock(timeout=1)
                ) as fast:
                    fast.send("T")
                    fast.send("T")
        with persisted(store, "k", m) as i:
            assert i.context["n"] == 2  # fast's write, not slow's

    def test_lock_released_only_by_owner(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        store = RedisStore(r, prefix=prefix, lock_ttl_ms=10_000)
        with store.lock("k", timeout=1):
            # A stranger's token must not release it.
            assert (
                store._unlock(keys=[store.k.lock("k")], args=["stranger"]) == 0
            )
            with pytest.raises(LockTimeoutError):
                with store.lock("k", timeout=0.1):
                    pass
        assert r.get(store.k.lock("k")) is None  # released by the owner


class TestForget:
    def test_forget_leaves_nothing_behind(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine import SimulatedClock
        from src.xstate_statemachine.contrib.redis import RedisStore

        store = RedisStore(r, prefix=prefix)
        cfg = {
            "id": "t",
            "initial": "w",
            "states": {"w": {"after": {"5000": "d"}}, "d": {}},
        }
        m = create_machine(cfg)
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        with store.lock("k"):
            assert r.get(store.k.lock("k")) is not None
            counts = store.forget("k")
        assert counts == {
            "snapshots": 1,
            "deadlines": 1,
            "locks": 1,
            "log_entries": 0,
        }
        assert [k for k in r.scan_iter(match=f"{prefix}:*k*")] == []
        assert r.zcard(store.k.deadlines) == 0
        assert store.list_keys() == []

    def test_forget_includes_the_instance_log_stream(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import RedisLog, RedisStore
        from src.xstate_statemachine.persistence import AuditPlugin

        store, log = RedisStore(r, prefix=prefix), RedisLog(r, prefix=prefix)
        m = machine()
        with persisted(store, "k", m, plugins=[AuditPlugin(log)]) as i:
            i.send("T")
            i.send("T")
        assert len(log.read("k")) == 2
        counts = store.forget("k")
        assert counts["log_entries"] == 2
        assert log.read("k") == []
        leftovers = [
            k.decode() if isinstance(k, bytes) else k
            for k in r.scan_iter(match=f"{prefix}:*")
        ]
        assert all(not k.endswith(":k") for k in leftovers), leftovers

    def test_delete_keeps_lock(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        store = RedisStore(r, prefix=prefix)
        store.save("k", SNAP)
        with store.lock("k"):
            assert store.delete("k") is True
            assert r.get(store.k.lock("k")) is not None  # still ours
        assert store.delete("k") is False


class TestTTL:
    def test_snapshot_ttl_expires_idle_instances(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        store = RedisStore(r, prefix=prefix, ttl_s=0.05)
        store.save("k", SNAP)
        assert r.pttl(store.k.snap("k")) > 0
        time.sleep(0.1)
        assert store.load("k") is None


class TestAsyncTwin:
    def test_async_store_under_apersisted(
        self, r: Any, ar: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import (
            AsyncRedisStore,
            RedisStore,
        )

        sync_store = RedisStore(r, prefix=prefix)
        m = machine()

        async def go() -> Any:
            astore = AsyncRedisStore(ar, prefix=prefix)
            assert (await astore.health())["ok"]
            async with apersisted(astore, "k", m) as i:
                await i.send("T", wait=True)
            async with apersisted(astore, "k", m, lock=PessimisticLock()) as i:
                await i.send("T", wait=True)
            with pytest.raises(ConflictError):
                async with apersisted(astore, "k", m) as i:
                    sync_store.save(
                        "k", sync_store.load("k").snapshot
                    )  # sneak
                    await i.send("T", wait=True)
            rec = await astore.load("k")
            keys = await astore.list_keys(prefix="k")
            async with astore.lock("k", timeout=1):
                pass
            assert await astore.forget("k") == {
                "snapshots": 1,
                "deadlines": 0,
                "locks": 0,
                "log_entries": 0,
            }
            return rec.version, keys

        version, keys = asyncio.run(go())
        assert version == 3 and keys == ["k"]
        # the sync view saw the same data
        assert sync_store.load("k") is None
