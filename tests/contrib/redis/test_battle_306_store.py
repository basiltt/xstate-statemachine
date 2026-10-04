# tests/contrib/redis/test_battle_306_store.py
"""#306 battle (adversary A): `RedisStore` / `AsyncRedisStore` defects.

Every test runs on fakeredis by default and on a live server with
``XSM_REDIS_URL`` (see conftest). Each one failed before its fix.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
import threading
import time
from typing import Any, List

import pytest

from src.xstate_statemachine.exceptions import (
    InvalidKeyError,
    SnapshotCorruptError,
    SnapshotTooLargeError,
    StoreError,
    StoreUnavailableError,
)
from src.xstate_statemachine.persistence import ConflictError
from src.xstate_statemachine.persistence.deadline import Deadline

from ..conftest import requires_extra
from .conftest import _aclient

pytestmark = requires_extra("redis")

SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}
)


def _dl(due: float, state: str = "m.a", seq: int = 1) -> Deadline:
    return Deadline(state, seq, due, 1000, f"after.1000.{state}")


def _store(r: Any, prefix: str, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.redis import RedisStore

    return RedisStore(r, prefix=prefix, **kw)


def _astore(r: Any, prefix: str, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.redis import AsyncRedisStore

    # 📝 3.9: an asyncio client built with no running loop calls
    #    `get_event_loop()`, which raises once an earlier test unset it.
    #    Give it a fresh loop for construction; the store itself is
    #    loop-agnostic until its first awaited call.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    return AsyncRedisStore(_aclient(r), prefix=prefix, **kw)


async def _close(a: Any) -> None:
    close = getattr(a.r, "aclose", None) or a.r.close
    await close()


# -----------------------------------------------------------------------------
# 3. keys containing the old member separator
# -----------------------------------------------------------------------------
class TestPipeInKey:
    @pytest.mark.parametrize("key", ["a|b", "a|", "|", "x|m.a|1"])
    def test_due_keys_returns_the_real_key(
        self, r: Any, prefix: str, key: str
    ) -> None:
        """Layout 1 split the zset member on the first `|`: "a|b" woke
        "a" (a different instance, or nobody) and "a|b" never woke."""
        s = _store(r, prefix)
        s.save(key, SNAP, deadlines=[_dl(1.0)])
        assert s.due_keys(10.0) == [(key, 1.0)]

    def test_resave_and_forget_clean_the_index(
        self, r: Any, prefix: str
    ) -> None:
        s = _store(r, prefix)
        s.save("a|b", SNAP, deadlines=[_dl(1.0), _dl(2.0, "m.b")])
        s.save("a|b", SNAP, deadlines=[_dl(3.0)])
        assert r.zcard(s.k.deadlines) == 1
        assert s.forget("a|b")["deadlines"] == 1
        assert r.zcard(s.k.deadlines) == 0

    def test_layout1_members_still_read_and_cleaned(
        self, r: Any, prefix: str
    ) -> None:
        """A namespace written by 0.11.0 (schema 1) keeps working: its
        `key|field` members are parsed and removed by the next save."""
        s = _store(r, prefix)
        field = "m.a|1|after.1000.m.a"
        r.hset(s.k.snap("old"), mapping={"snapshot": SNAP, "version": 1})
        r.hset(s.k.dl("old"), field, json.dumps(_dl(1.0).to_dict()))
        r.zadd(s.k.deadlines, {f"old|{field}": 1.0})
        assert s.due_keys(10.0) == [("old", 1.0)]
        assert len(s.load("old").deadlines) == 1
        s.save("old", SNAP, deadlines=[])
        assert r.zcard(s.k.deadlines) == 0

    def test_unicode_and_long_keys_roundtrip(
        self, r: Any, prefix: str
    ) -> None:
        s = _store(r, prefix)
        for key in ["ключ|‏×", "k" * 200, "a*b?[c]"]:
            s.save(key, SNAP, deadlines=[_dl(1.0)])
            assert s.load(key) is not None
        assert {k for k, _ in s.due_keys(10.0)} == {
            "ключ|‏×",
            "k" * 200,
            "a*b?[c]",
        }
        assert s.list_keys(prefix="a*") == ["a*b?[c]"]

    @pytest.mark.parametrize("bad", ["", "a\x00b", "k" * 10_000, "\ud800"])
    def test_bad_keys_refused_both_engines(
        self, r: Any, prefix: str, bad: str
    ) -> None:
        s = _store(r, prefix)
        a = _astore(r, prefix)
        with pytest.raises(InvalidKeyError):
            s.save(bad, SNAP)

        async def go() -> None:
            try:
                with pytest.raises(InvalidKeyError):
                    await a.save(bad, SNAP)
                with pytest.raises(InvalidKeyError):
                    await a.load(bad)
            finally:
                await _close(a)

        asyncio.run(go())


# -----------------------------------------------------------------------------
# 2. ttl_s orphans in the deadline index
# -----------------------------------------------------------------------------
class TestTtlOrphans:
    def test_expired_snapshots_do_not_starve_live_keys(
        self, r: Any, prefix: str
    ) -> None:
        """Expired records left their zset members behind; at `limit` of
        them `due_keys` returned only dead keys, forever."""
        s = _store(r, prefix, ttl_s=0.05)
        for i in range(5):
            s.save(f"old{i}", SNAP, deadlines=[_dl(1.0)])
        time.sleep(0.2)
        live = _store(r, prefix)
        live.save("live", SNAP, deadlines=[_dl(2.0)])
        assert live.due_keys(10.0, limit=3) == [("live", 2.0)]
        assert r.zcard(s.k.deadlines) == 1  # orphans pruned

    def test_async_due_keys_prunes_too(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix, ttl_s=0.05)
        s.save("dead", SNAP, deadlines=[_dl(1.0)])
        time.sleep(0.2)
        s.save("x|y", SNAP, deadlines=[_dl(2.0)])
        a = _astore(r, prefix)

        async def go() -> List[Any]:
            try:
                return await a.due_keys(10.0, limit=1)
            finally:
                await _close(a)

        assert asyncio.run(go()) == [("x|y", 2.0)]

    def test_prune_never_drops_a_recreated_record(
        self, r: Any, prefix: str
    ) -> None:
        """The EXISTS check and the ZREM are one script: a record that
        exists when pruning runs keeps its member."""
        s = _store(r, prefix)
        s.save("k", SNAP, deadlines=[_dl(1.0)])
        member = r.zrange(s.k.deadlines, 0, -1)[0]
        assert s._prune_orphans([member]) == []
        assert r.zcard(s.k.deadlines) == 1


# -----------------------------------------------------------------------------
# 4. schema marker
# -----------------------------------------------------------------------------
class TestSchema:
    @pytest.mark.parametrize("marker", ["abc", "1.5", "", "\xff"])
    def test_unreadable_marker_is_store_error(
        self, r: Any, prefix: str, marker: str
    ) -> None:
        r.set(f"{prefix}:schema", marker.encode("latin-1"))
        with pytest.raises(StoreError, match="schema"):
            _store(r, prefix)

    def test_older_marker_is_upgraded_newer_refused(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis._keys import SCHEMA_VERSION

        r.set(f"{prefix}:schema", 1)
        _store(r, prefix)
        assert int(r.get(f"{prefix}:schema")) == SCHEMA_VERSION
        r.set(f"{prefix}:schema", SCHEMA_VERSION + 1)
        with pytest.raises(StoreError, match="newer"):
            _store(r, prefix)

    def test_async_store_checks_the_marker(self, r: Any, prefix: str) -> None:
        """The async store never read the marker and wrote into a
        namespace a newer layout owned."""
        r.set(f"{prefix}:schema", 99)
        a = _astore(r, prefix)

        async def go() -> None:
            try:
                with pytest.raises(StoreError, match="newer"):
                    await a.save("k", SNAP)
                with pytest.raises(StoreError, match="newer"):
                    await a.list_keys()
            finally:
                await _close(a)

        asyncio.run(go())
        assert not r.exists(f"{prefix}:snap:k")

    def test_racing_constructors_agree(self, r: Any, prefix: str) -> None:
        errors: List[BaseException] = []
        gate = threading.Barrier(16)

        def build() -> None:
            gate.wait()
            try:
                _store(r, prefix)
            except BaseException as exc:  # pragma: no cover - asserted
                errors.append(exc)

        threads = [threading.Thread(target=build) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        assert errors == []


# -----------------------------------------------------------------------------
# 5. damaged records / size
# -----------------------------------------------------------------------------
class TestDamagedRecords:
    @pytest.mark.parametrize(
        "row",
        [{"version": "1"}, {"snapshot": "{}", "version": "x"}],
    )
    def test_damaged_hash_is_snapshot_corrupt(
        self, r: Any, prefix: str, row: Any
    ) -> None:
        s = _store(r, prefix)
        r.hset(s.k.snap("bad"), mapping=row)
        with pytest.raises(SnapshotCorruptError):
            s.load("bad")
        a = _astore(r, prefix)

        async def go() -> None:
            try:
                with pytest.raises(SnapshotCorruptError):
                    await a.load("bad")
            finally:
                await _close(a)

        asyncio.run(go())

    def test_poisoned_oversize_refused_on_load_both(
        self, r: Any, prefix: str
    ) -> None:
        s = _store(r, prefix, max_snapshot_bytes=100)
        r.hset(s.k.snap("big"), mapping={"snapshot": "é" * 60, "version": 1})
        with pytest.raises(SnapshotTooLargeError):
            s.load("big")  # 120 bytes, 60 chars
        a = _astore(r, prefix, max_snapshot_bytes=100)

        async def go() -> None:
            try:
                with pytest.raises(SnapshotTooLargeError):
                    await a.load("big")
            finally:
                await _close(a)

        asyncio.run(go())

    def test_exact_limit_accepted(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix, max_snapshot_bytes=len(SNAP))
        s.save("k", SNAP)
        assert s.load("k").snapshot == SNAP


# -----------------------------------------------------------------------------
# 9. async drift
# -----------------------------------------------------------------------------
class _BadCodec:
    def encode(self, s: str) -> str:
        raise RuntimeError("kms down")

    def decode(self, s: str) -> str:
        raise RuntimeError("kms down")


class TestAsyncParity:
    def test_async_save_policy_matches_sync(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix)
        a = _astore(r, prefix)
        with pytest.raises(TypeError):
            s.save("k", 5)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            s.save("k", SNAP, expected_version=-1)

        async def go() -> None:
            try:
                with pytest.raises(TypeError):
                    await a.save("k", 5)
                with pytest.raises(ValueError):
                    await a.save("k", SNAP, expected_version=-1)
                with pytest.raises(ValueError):
                    await a.list_keys(limit=-1)
                assert await a.list_keys(limit=0) == []
                with pytest.raises(ValueError):
                    a.lock("k", timeout=-1)
            finally:
                await _close(a)

        asyncio.run(go())

    def test_async_codec_failures_are_typed(self, r: Any, prefix: str) -> None:
        _store(r, prefix).save("k", SNAP)
        a = _astore(r, prefix, codec=_BadCodec())

        async def go() -> None:
            try:
                with pytest.raises(StoreError, match="encode"):
                    await a.save("k2", SNAP)
                with pytest.raises(SnapshotCorruptError):
                    await a.load("k")
            finally:
                await _close(a)

        asyncio.run(go())

    def test_async_list_keys_hides_planted_bad_keys(
        self, r: Any, prefix: str
    ) -> None:
        s = _store(r, prefix)
        s.save("ok", SNAP)
        r.sadd(s.k.keys, "", "a\x00b")
        a = _astore(r, prefix)

        async def go() -> List[str]:
            try:
                return await a.list_keys()
            finally:
                await _close(a)

        assert asyncio.run(go()) == ["ok"] == s.list_keys()


# -----------------------------------------------------------------------------
# options validated at construction
# -----------------------------------------------------------------------------
class TestOptions:
    @pytest.mark.parametrize(
        "kw", [{"lock_ttl_ms": 0}, {"ttl_s": 0.0001}, {"ttl_s": -1}]
    )
    def test_degenerate_ttls_refused(
        self, r: Any, prefix: str, kw: Any
    ) -> None:
        """`lock_ttl_ms=0` was a raw ResponseError on first lock; a tiny or
        negative `ttl_s` made every save vanish immediately."""
        with pytest.raises(ValueError):
            _store(r, prefix, **kw)
        with pytest.raises(ValueError):
            _astore(r, prefix, **kw)


# -----------------------------------------------------------------------------
# 6. outage while TAKING the lock / 8. bounded hang
# -----------------------------------------------------------------------------
class _DownOnSet:
    def __init__(self, real: Any) -> None:
        self._real = real

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)

    def set(self, *a: Any, **kw: Any) -> Any:
        import redis

        raise redis.ConnectionError("failover")


class TestOutage:
    def test_lock_acquire_outage_is_typed(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine.persistence import (
            PessimisticLock,
            persisted,
        )

        from .test_redis_specific import machine

        s = _store(_DownOnSet(r), prefix)
        with pytest.raises(StoreUnavailableError):
            with s.lock("k", timeout=0):
                pass  # pragma: no cover
        with pytest.raises(StoreUnavailableError):
            with persisted(s, "k", machine(), lock=PessimisticLock()):
                pass  # pragma: no cover

    def test_async_lock_acquire_outage_is_typed(
        self, r: Any, prefix: str
    ) -> None:
        a = _astore(r, prefix)

        async def boom(*_a: Any, **_k: Any) -> Any:
            import redis

            raise redis.ConnectionError("failover")

        async def go() -> None:
            a.r.set = boom
            try:
                with pytest.raises(StoreUnavailableError):
                    async with a.lock("k", timeout=0):
                        pass  # pragma: no cover
            finally:
                await _close(a)

        asyncio.run(go())

    def test_release_failure_does_not_mask_body_error(
        self, r: Any, prefix: str
    ) -> None:
        import redis

        s = _store(r, prefix)

        def broken_unlock(**_kw: Any) -> Any:
            raise redis.ConnectionError("gone")

        s._unlock = broken_unlock
        with pytest.raises(StoreUnavailableError, match="body"):
            with s.lock("k", timeout=0):
                raise StoreUnavailableError("body")

    def test_health_never_raises(self, r: Any, prefix: str) -> None:
        s = _store(r, prefix)

        class Weird:
            def ping(self) -> Any:
                raise OSError("not a RedisError")

        s.r = Weird()
        assert s.health()["ok"] is False

    def test_url_client_has_bounded_timeouts(self) -> None:
        """A server that accepts TCP but never answers must not hang the
        constructor forever: URL-built clients get a socket timeout."""
        from src.xstate_statemachine.contrib.redis import (
            DEFAULT_SOCKET_TIMEOUT_S,
            RedisStore,
        )

        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        held: List[Any] = []

        def accept_forever() -> None:
            with contextlib.suppress(OSError):  # closed at teardown
                while True:
                    held.append(srv.accept())

        threading.Thread(target=accept_forever, daemon=True).start()
        url = f"redis://127.0.0.1:{srv.getsockname()[1]}/0"
        t0 = time.monotonic()
        try:
            with pytest.raises(StoreUnavailableError):
                RedisStore(url + "?socket_timeout=0.3", prefix="p")
            assert time.monotonic() - t0 < DEFAULT_SOCKET_TIMEOUT_S
        finally:
            srv.close()

    def test_url_client_gets_default_timeouts(self) -> None:
        from src.xstate_statemachine.contrib.redis import (
            DEFAULT_SOCKET_CONNECT_TIMEOUT_S,
            DEFAULT_SOCKET_TIMEOUT_S,
        )
        from src.xstate_statemachine.contrib.redis._layout import (
            _client_from_url,
        )

        import redis

        kw = _client_from_url(
            redis.Redis, "redis://localhost:1/0"
        ).connection_pool.connection_kwargs
        assert kw["socket_timeout"] == DEFAULT_SOCKET_TIMEOUT_S
        assert kw["socket_connect_timeout"] == DEFAULT_SOCKET_CONNECT_TIMEOUT_S
        kw = _client_from_url(
            redis.Redis, "redis://localhost:1/0?socket_timeout=30"
        ).connection_pool.connection_kwargs
        assert kw["socket_timeout"] == 30


# -----------------------------------------------------------------------------
# 1. fencing: a THIRD writer after two expired locks
# -----------------------------------------------------------------------------
class TestFencing:
    def test_third_writer_after_two_expiries(
        self, r: Any, prefix: str
    ) -> None:
        s = _store(r, prefix, lock_ttl_ms=30)
        v0 = s.save("k", SNAP)
        outcomes: List[str] = []
        for _ in range(2):
            with s.lock("k", timeout=1):
                time.sleep(0.06)  # lock expired; we are still "inside"
                with s.lock("k", timeout=1):  # a third writer gets in
                    s.save("k", SNAP, expected_version=s.load("k").version)
                try:
                    s.save("k", SNAP, expected_version=v0)
                    outcomes.append("lost-update")
                except ConflictError:
                    outcomes.append("conflict")
        assert outcomes == ["conflict", "conflict"]
        assert s.load("k").version == v0 + 2
