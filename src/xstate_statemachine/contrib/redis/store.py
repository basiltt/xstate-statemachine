# src/xstate_statemachine/contrib/redis/store.py
"""`RedisStore` (sync) and `AsyncRedisStore` (redis.asyncio) -- #306."""

from __future__ import annotations

import contextlib
import secrets
import time
from typing import (
    Any,
    AsyncIterator,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

import redis

from ...exceptions import InvalidKeyError, LockTimeoutError
from ...persistence.deadline import Deadline
from ...persistence.store import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    BaseStore,
    SnapshotCodec,
    StoredSnapshot,
    validate_key,
)
from ._errors import aredis_errors_typed, redis_errors_typed, typed
from ._keys import SCHEMA_VERSION, Keys
from ._layout import (
    _DELETE,
    _FORGET,
    _PRUNE,
    _SAVE,
    _SCHEMA,
    _UNLOCK,
    DEFAULT_SOCKET_CONNECT_TIMEOUT_S,
    DEFAULT_SOCKET_TIMEOUT_S,
    _check_options,
    _check_save_call,
    _client_from_url,
    _due_rows,
    _forget_counts,
    _Layout,
    _parse_deadlines,
    _parse_snap_hash,
    _s,
    _saved_version,
    _schema_check,
    _sorted_members,
    escape_glob,
)

__all__ = [
    "AsyncRedisStore",
    "DEFAULT_SOCKET_CONNECT_TIMEOUT_S",
    "DEFAULT_SOCKET_TIMEOUT_S",
    "RedisStore",
    "escape_glob",
]


class RedisStore(BaseStore):
    """`StateStore` on Redis (sync client).

    Args:
        client_or_url: A ``redis.Redis`` client or a URL
            (``redis://host:6379/0``). A client is used as given --
            ``decode_responses`` may be on or off. A URL gets bounded
            socket timeouts (`DEFAULT_SOCKET_TIMEOUT_S`); override them in
            the query string (``?socket_timeout=30``) or pass a client.
        prefix: **Mandatory** key namespace (X0.15), e.g. ``"myapp"``.
        codec: Optional `SnapshotCodec` (encryption / compression at rest).
        max_snapshot_bytes: Size cap on save and load (1 MiB default).
        ttl_s: Optional expiry for snapshot hashes (idle instances vanish).
            At least one millisecond.
        lock_ttl_ms: How long a `lock()` may be held before Redis expires
            it -- the reason `persisted()` also fences with the version.

    Raises:
        StoreError: The namespace's schema marker is newer than this
            library, or unreadable. `StoreUnavailableError` when Redis
            cannot be reached at construction.
        ValueError: ``ttl_s`` / ``lock_ttl_ms`` below one millisecond.

    Good for: several hosts sharing one state. Not for: a Redis you do not
    persist (AOF/RDB) if you need durability across a Redis restart.
    """

    backend = "redis"

    def __init__(
        self,
        client_or_url: Any,
        *,
        prefix: str,
        codec: Optional[SnapshotCodec] = None,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        ttl_s: Optional[float] = None,
        lock_ttl_ms: int = 30_000,
    ) -> None:
        super().__init__(codec=codec, max_snapshot_bytes=max_snapshot_bytes)
        _check_options(ttl_s, lock_ttl_ms)
        self.k = Keys(prefix)
        self.r: Any = (
            _client_from_url(redis.Redis, client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self.ttl_s = ttl_s
        self.lock_ttl_ms = int(lock_ttl_ms)
        self._layout = _Layout(self.k, ttl_s)
        self._save = self.r.register_script(_SAVE)
        self._delete = self.r.register_script(_DELETE)
        self._forget = self.r.register_script(_FORGET)
        self._unlock = self.r.register_script(_UNLOCK)
        self._prune = self.r.register_script(_PRUNE)
        self._schema = self.r.register_script(_SCHEMA)
        self._ensure_schema()

    # -- schema (X0.10) -----------------------------------------------------------
    @redis_errors_typed
    def _ensure_schema(self) -> None:
        if _schema_check(self.k.p, self.r.get(self.k.schema)):
            marker = self._schema(keys=[self.k.schema], args=[SCHEMA_VERSION])
            _schema_check(self.k.p, marker)

    # -- primitives ---------------------------------------------------------------
    @redis_errors_typed
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        h = self.r.hgetall(self.k.snap(key))
        if not h:
            return None
        data, version, mv, updated_at = _parse_snap_hash(key, h)
        deadlines = _parse_deadlines(self.r.hgetall(self.k.dl(key)))
        return data, version, mv, updated_at, deadlines

    @redis_errors_typed
    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        res = self._save(
            keys=self._layout.save_keys(key),
            args=self._layout.save_args(
                key, data, expected_version, machine_version, deadlines
            ),
        )
        return _saved_version(res, key, expected_version)

    @redis_errors_typed
    def _delete_raw(self, key: str) -> bool:
        res = self._delete(keys=self._layout.save_keys(key), args=[key])
        return int(res[0]) > 0

    @redis_errors_typed
    def _forget_raw(self, key: str) -> Dict[str, int]:
        res = self._forget(keys=self._layout.forget_keys(key), args=[key])
        return _forget_counts(res)

    @redis_errors_typed
    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        # 📝 The keys SET is the index; SCAN over it with an escaped pattern
        #    so a user prefix containing `*?[` matches literally (X0.15).
        pattern = escape_glob(prefix) + "*"
        members = list(
            self.r.sscan_iter(self.k.keys, match=pattern, count=500)
        )
        return _sorted_members(members, limit)

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._redis_lock(key, timeout)

    @contextlib.contextmanager
    def _redis_lock(self, key: str, timeout: float) -> Iterator[None]:
        token = secrets.token_hex(16)
        name = self.k.lock(key)
        deadline = time.monotonic() + timeout
        while True:
            # 🐛 #306 battle: an outage while TAKING the lock escaped as a
            #    raw `redis.ConnectionError` (a 500 where it is a 503).
            try:
                got = self.r.set(name, token, nx=True, px=self.lock_ttl_ms)
            except redis.RedisError as exc:
                raise typed(exc, type(self).__name__) from exc
            if got:
                break
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            time.sleep(0.01)
        try:
            yield
        finally:
            # 📝 A failed RELEASE is suppressed on purpose: the lock then
            #    expires after `lock_ttl_ms`, and whatever the body raised
            #    or returned is what the caller must see.
            with contextlib.suppress(redis.RedisError):
                self._unlock(keys=[name], args=[token])

    def health(self) -> Dict[str, Any]:
        """Liveness probe; never raises (a down Redis is ``ok: False``)."""
        try:
            ok = bool(self.r.ping())
            return {
                "ok": ok,
                "backend": self.backend,
                "prefix": self.k.p,
                "keys": int(self.r.scard(self.k.keys)),
                "schema_version": SCHEMA_VERSION,
            }
        except Exception as exc:  # a probe reports, it does not raise
            # 📝 class name only: `str(exc)` carries host:port (X0.7).
            return {
                "ok": False,
                "backend": self.backend,
                "error": type(exc).__name__,
            }

    # -- scanner support -------------------------------------------------------------
    @redis_errors_typed
    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, due_at)`` for deadlines with ``due_at <= until_wall``,
        soonest first -- read from the zset index, not by loading every
        record. `DueTimerScanner` uses it when present.

        🐛 #306 battle: with ``ttl_s`` the snapshot hash expires but its
        zset members cannot (Redis expires keys, not members). Those
        orphans sorted first forever and, ``limit`` of them, starved every
        live due key. Orphans met here are pruned atomically (`_PRUNE`)
        and not reported; the read repeats while it pruned a full page.
        """
        while True:
            rows = self.r.zrangebyscore(
                self.k.deadlines,
                "-inf",
                until_wall,
                start=0,
                num=limit,
                withscores=True,
            )
            gone = self._prune_orphans([m for m, _ in rows])
            if not gone or len(rows) < limit:
                return _due_rows(rows, gone)

    def _prune_orphans(self, members: List[Any]) -> List[Any]:
        if not members:
            return []
        return list(
            self._prune(
                keys=[self.k.deadlines],
                args=self._layout.prune_args(members),
            )
        )


class AsyncRedisStore:
    """`AsyncStateStore` on ``redis.asyncio`` -- the same layout, Lua
    scripts and argument policy as `RedisStore`, so both may point at one
    namespace. Constructor arguments are those of `RedisStore`; the schema
    marker is checked on the first call (a constructor cannot await)."""

    backend = "redis"

    def __init__(
        self,
        client_or_url: Any,
        *,
        prefix: str,
        codec: Optional[SnapshotCodec] = None,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        ttl_s: Optional[float] = None,
        lock_ttl_ms: int = 30_000,
    ) -> None:
        import redis.asyncio as aredis

        _check_options(ttl_s, lock_ttl_ms)
        self.k = Keys(prefix)
        self.r: Any = (
            _client_from_url(aredis.Redis, client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self._policy = BaseStore(
            codec=codec, max_snapshot_bytes=max_snapshot_bytes
        )
        self.ttl_s = ttl_s
        self.lock_ttl_ms = int(lock_ttl_ms)
        self._layout = _Layout(self.k, ttl_s)
        self._schema_ok = False
        self._save = self.r.register_script(_SAVE)
        self._delete = self.r.register_script(_DELETE)
        self._forget = self.r.register_script(_FORGET)
        self._unlock = self.r.register_script(_UNLOCK)
        self._prune = self.r.register_script(_PRUNE)
        self._schema = self.r.register_script(_SCHEMA)

    async def _ensure_schema(self) -> None:
        # 🐛 #306 battle: the async store never looked at the schema
        #    marker -- it wrote into a namespace a NEWER layout owned.
        if self._schema_ok:
            return
        if _schema_check(self.k.p, await self.r.get(self.k.schema)):
            marker = await self._schema(
                keys=[self.k.schema], args=[SCHEMA_VERSION]
            )
            _schema_check(self.k.p, marker)
        self._schema_ok = True

    @aredis_errors_typed
    async def load(self, key: str) -> Optional[StoredSnapshot]:
        validate_key(key)
        await self._ensure_schema()
        h = await self.r.hgetall(self.k.snap(key))
        if not h:
            return None
        data, version, mv, updated_at = _parse_snap_hash(key, h)
        self._policy._check_size(key, data)
        deadlines = _parse_deadlines(await self.r.hgetall(self.k.dl(key)))
        return StoredSnapshot(
            key=key,
            snapshot=self._policy._decode(key, data),
            version=version,
            machine_version=mv,
            updated_at=updated_at,
            deadlines=tuple(deadlines),
        )

    @aredis_errors_typed
    async def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        data, expected_version, machine_version, dls = _check_save_call(
            self._policy,
            key,
            snapshot,
            expected_version,
            machine_version,
            deadlines,
        )
        await self._ensure_schema()
        res = await self._save(
            keys=self._layout.save_keys(key),
            args=self._layout.save_args(
                key, data, expected_version, machine_version, dls
            ),
        )
        return _saved_version(res, key, expected_version)

    @aredis_errors_typed
    async def delete(self, key: str) -> bool:
        validate_key(key)
        await self._ensure_schema()
        res = await self._delete(keys=self._layout.save_keys(key), args=[key])
        return int(res[0]) > 0

    @aredis_errors_typed
    async def forget(self, key: str) -> Dict[str, int]:
        validate_key(key)
        await self._ensure_schema()
        res = await self._forget(
            keys=self._layout.forget_keys(key), args=[key]
        )
        return _forget_counts(res)

    @aredis_errors_typed
    async def list_keys(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[str]:
        # 📝 Same policy as `BaseStore.list_keys`: negative limit refused,
        #    and a planted key `load()` would reject is never advertised.
        if limit < 0:
            raise ValueError("limit must be >= 0")
        if limit == 0:
            return []
        await self._ensure_schema()
        pattern = escape_glob(prefix) + "*"
        members = [
            m
            async for m in self.r.sscan_iter(
                self.k.keys, match=pattern, count=500
            )
        ]
        out: List[str] = []
        for k in _sorted_members(members, len(members)):
            try:
                validate_key(k)
            except InvalidKeyError:
                continue
            out.append(k)
        return out[:limit]

    def lock(self, key: str, *, timeout: float = 10.0) -> Any:
        validate_key(key)
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        return self._alock(key, timeout)

    @contextlib.asynccontextmanager
    async def _alock(self, key: str, timeout: float) -> AsyncIterator[None]:
        import asyncio

        token = secrets.token_hex(16)
        name = self.k.lock(key)
        deadline = time.monotonic() + timeout
        while True:
            try:
                got = await self.r.set(
                    name, token, nx=True, px=self.lock_ttl_ms
                )
            except redis.RedisError as exc:
                raise typed(exc, type(self).__name__) from exc
            if got:
                break
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            await asyncio.sleep(0.01)
        try:
            yield
        finally:
            with contextlib.suppress(redis.RedisError):
                await self._unlock(keys=[name], args=[token])

    async def health(self) -> Dict[str, Any]:
        """Liveness probe; never raises (a down Redis is ``ok: False``)."""
        try:
            ok = bool(await self.r.ping())
            return {
                "ok": ok,
                "backend": self.backend,
                "prefix": self.k.p,
                "keys": int(await self.r.scard(self.k.keys)),
                "schema_version": SCHEMA_VERSION,
            }
        except Exception as exc:  # a probe reports, it does not raise
            # 📝 class name only: `str(exc)` carries host:port (X0.7).
            return {
                "ok": False,
                "backend": self.backend,
                "error": type(exc).__name__,
            }

    async def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """Async twin of `RedisStore.due_keys` (orphans pruned)."""
        try:
            await self._ensure_schema()  # reviewer M1: parity with sync
            while True:
                rows = await self.r.zrangebyscore(
                    self.k.deadlines,
                    "-inf",
                    until_wall,
                    start=0,
                    num=limit,
                    withscores=True,
                )
                members = [m for m, _ in rows]
                gone: List[Any] = []
                if members:
                    gone = list(
                        await self._prune(
                            keys=[self.k.deadlines],
                            args=self._layout.prune_args(members),
                        )
                    )
                if not gone or len(rows) < limit:
                    return _due_rows(rows, gone)
        except redis.RedisError as exc:
            raise typed(exc, type(self).__name__) from exc
