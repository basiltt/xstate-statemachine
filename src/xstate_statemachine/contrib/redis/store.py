# src/xstate_statemachine/contrib/redis/store.py
"""`RedisStore` (sync) and `AsyncRedisStore` (redis.asyncio) -- #306."""

from __future__ import annotations

import contextlib
import json
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

from ...exceptions import ConflictError, LockTimeoutError, StoreError
from ...persistence.deadline import Deadline, check_deadline_record
from ...persistence.store import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    BaseStore,
    SnapshotCodec,
    StoredSnapshot,
    check_save_args,
    validate_key,
)
from ._keys import SCHEMA_VERSION, Keys

__all__ = ["AsyncRedisStore", "RedisStore", "escape_glob"]

_GLOB_META = "*?[]\\"


def escape_glob(text: str) -> str:
    """Escape SCAN/KEYS glob metacharacters so *text* matches literally."""
    return "".join(f"\\{c}" if c in _GLOB_META else c for c in text)


# -----------------------------------------------------------------------------
# 📜 Lua scripts -- atomic where a WATCH window would not be
# -----------------------------------------------------------------------------
#: KEYS[1]=snap hash, KEYS[2]=keys set, KEYS[3]=dl hash, KEYS[4]=deadlines zset
#: ARGV[1]=expected_version|"" ARGV[2]=snapshot ARGV[3]=machine_version
#: ARGV[4]=updated_at ARGV[5]=key ARGV[6]=ttl_ms|"" ARGV[7..]=deadline JSON
#: (each with due_at_wall for the zset). Returns new version, or
#: {-1, actual} on conflict.
_SAVE = """
local cur = redis.call('HGET', KEYS[1], 'version')
local current = cur and tonumber(cur) or 0
if ARGV[1] ~= '' then
  local expected = tonumber(ARGV[1])
  if expected ~= current then
    if cur then return {-1, current} else return {-1, -1} end
  end
end
local nv = current + 1
redis.call('HSET', KEYS[1], 'snapshot', ARGV[2], 'version', nv,
           'machine_version', ARGV[3], 'updated_at', ARGV[4])
redis.call('SADD', KEYS[2], ARGV[5])
-- deadlines: drop this key's members, then add the new ones
local old = redis.call('HKEYS', KEYS[3])
for _, f in ipairs(old) do
  redis.call('ZREM', KEYS[4], ARGV[5] .. '|' .. f)
end
redis.call('DEL', KEYS[3])
local i = 7
while i <= #ARGV do
  local field = ARGV[i]; local due = ARGV[i+1]; local body = ARGV[i+2]
  redis.call('HSET', KEYS[3], field, body)
  redis.call('ZADD', KEYS[4], due, ARGV[5] .. '|' .. field)
  i = i + 3
end
if ARGV[6] ~= '' then
  redis.call('PEXPIRE', KEYS[1], ARGV[6])
  redis.call('PEXPIRE', KEYS[3], ARGV[6])
end
return {nv, current}
"""

#: KEYS[1]=snap KEYS[2]=keys set KEYS[3]=dl KEYS[4]=deadlines KEYS[5]=lock
#: KEYS[6]=log stream. ARGV[1]=key. Returns {snapshots, deadlines, locks,
#: log entries}. X0.5: everything the namespace holds about ONE instance
#: goes in one atomic step -- the log stream included, since it is keyed
#: by the same instance id. Inbox rows are per principal/scope, not per
#: instance, and are erased with `RedisInbox.forget(scope)`.
_FORGET = """
local snaps = redis.call('DEL', KEYS[1])
redis.call('SREM', KEYS[2], ARGV[1])
local fields = redis.call('HKEYS', KEYS[3])
for _, f in ipairs(fields) do
  redis.call('ZREM', KEYS[4], ARGV[1] .. '|' .. f)
end
redis.call('DEL', KEYS[3])
local locks = redis.call('DEL', KEYS[5])
local entries = 0
if redis.call('EXISTS', KEYS[6]) == 1 then
  entries = redis.call('XLEN', KEYS[6])
  redis.call('DEL', KEYS[6])
end
return {snaps, #fields, locks, entries}
"""

#: `delete()`: same as FORGET but leaves the lock alone (a holder may still
#: be inside a `lock()` block that deletes the record it guards).
_DELETE = """
local snaps = redis.call('DEL', KEYS[1])
redis.call('SREM', KEYS[2], ARGV[1])
local fields = redis.call('HKEYS', KEYS[3])
for _, f in ipairs(fields) do
  redis.call('ZREM', KEYS[4], ARGV[1] .. '|' .. f)
end
redis.call('DEL', KEYS[3])
return {snaps, #fields, 0}
"""

#: KEYS[1]=lock ARGV[1]=token. Compare-and-delete: only the owner releases.
_UNLOCK = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


def _dl_field(d: Deadline) -> str:
    return f"{d.state_id}|{d.entry_seq}|{d.event_type}"


def _dl_args(deadlines: Sequence[Deadline]) -> List[str]:
    out: List[str] = []
    for d in deadlines:
        out.extend(
            [_dl_field(d), repr(float(d.due_at_wall)), json.dumps(d.to_dict())]
        )
    return out


def _parse_deadlines(rows: Dict[Any, Any]) -> List[Deadline]:
    out: List[Deadline] = []
    for raw in rows.values():
        try:
            rec = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if check_deadline_record(rec) is None:
            out.append(Deadline.from_dict(rec))
    out.sort(key=lambda d: (d.due_at_wall, d.state_id))
    return out


def _s(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


class RedisStore(BaseStore):
    """`StateStore` on Redis (sync client).

    Args:
        client_or_url: A ``redis.Redis`` client or a URL
            (``redis://host:6379/0``). The client is used as given --
            ``decode_responses`` may be on or off.
        prefix: **Mandatory** key namespace (X0.15), e.g. ``"myapp"``.
        codec: Optional `SnapshotCodec` (encryption / compression at rest).
        max_snapshot_bytes: Size cap on save and load (1 MiB default).
        ttl_s: Optional expiry for snapshot hashes (idle instances vanish).
        lock_ttl_ms: How long a `lock()` may be held before Redis expires
            it -- the reason `persisted()` also fences with the version.

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
        self.k = Keys(prefix)
        self.r: Any = (
            redis.Redis.from_url(client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self.ttl_s = ttl_s
        self.lock_ttl_ms = int(lock_ttl_ms)
        self._save = self.r.register_script(_SAVE)
        self._delete = self.r.register_script(_DELETE)
        self._forget = self.r.register_script(_FORGET)
        self._unlock = self.r.register_script(_UNLOCK)
        self._ensure_schema()

    # -- schema (X0.10) -----------------------------------------------------------
    def _ensure_schema(self) -> None:
        cur = self.r.get(self.k.schema)
        if cur is None:
            self.r.set(self.k.schema, SCHEMA_VERSION, nx=True)
            return
        found = int(_s(cur))
        if found > SCHEMA_VERSION:
            raise StoreError(
                f"Redis namespace '{self.k.p}' has schema version {found}, "
                f"newer than this library supports ({SCHEMA_VERSION})."
            )

    # -- primitives ---------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        h = self.r.hgetall(self.k.snap(key))
        if not h:
            return None
        h = {_s(a): b for a, b in h.items()}
        deadlines = _parse_deadlines(self.r.hgetall(self.k.dl(key)))
        return (
            _s(h["snapshot"]),
            int(_s(h["version"])),
            _s(h.get("machine_version", "")),
            float(_s(h.get("updated_at", 0.0))),
            deadlines,
        )

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        res = self._save(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
            ],
            args=[
                "" if expected_version is None else str(expected_version),
                data,
                machine_version,
                repr(time.time()),
                key,
                "" if self.ttl_s is None else str(int(self.ttl_s * 1000)),
                *_dl_args(deadlines),
            ],
        )
        new_version, actual = int(res[0]), int(res[1])
        if new_version == -1:
            raise ConflictError(
                key, expected_version, None if actual == -1 else actual
            )
        return new_version

    def _delete_raw(self, key: str) -> bool:
        res = self._delete(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
            ],
            args=[key],
        )
        return int(res[0]) > 0

    def _forget_raw(self, key: str) -> Dict[str, int]:
        res = self._forget(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
                self.k.lock(key),
                self.k.log(key),
            ],
            args=[key],
        )
        return {
            "snapshots": int(res[0]),
            "deadlines": int(res[1]),
            "locks": int(res[2]),
            "log_entries": int(res[3]),
        }

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        # 📝 The keys SET is the index; SCAN over it with an escaped pattern
        #    so a user prefix containing `*?[` matches literally (X0.15).
        pattern = escape_glob(prefix) + "*"
        found: List[str] = []
        for member in self.r.sscan_iter(self.k.keys, match=pattern, count=500):
            found.append(_s(member))
        found.sort()
        return found[:limit]

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._redis_lock(key, timeout)

    @contextlib.contextmanager
    def _redis_lock(self, key: str, timeout: float) -> Iterator[None]:
        token = secrets.token_hex(16)
        name = self.k.lock(key)
        deadline = time.monotonic() + timeout
        while True:
            if self.r.set(name, token, nx=True, px=self.lock_ttl_ms):
                break
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            time.sleep(0.01)
        try:
            yield
        finally:
            with contextlib.suppress(redis.RedisError):
                self._unlock(keys=[name], args=[token])

    def health(self) -> Dict[str, Any]:
        try:
            ok = bool(self.r.ping())
            return {
                "ok": ok,
                "backend": self.backend,
                "prefix": self.k.p,
                "keys": int(self.r.scard(self.k.keys)),
                "schema_version": SCHEMA_VERSION,
            }
        except redis.RedisError as exc:
            return {"ok": False, "backend": self.backend, "error": str(exc)}

    # -- scanner support -------------------------------------------------------------
    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, due_at)`` for deadlines with ``due_at <= until_wall``,
        soonest first -- read from the zset index, not by loading every
        record. `DueTimerScanner` uses it when present."""
        rows = self.r.zrangebyscore(
            self.k.deadlines,
            "-inf",
            until_wall,
            start=0,
            num=limit,
            withscores=True,
        )
        seen: Dict[str, float] = {}
        for member, score in rows:
            key = _s(member).split("|", 1)[0]
            seen.setdefault(key, float(score))
        return sorted(seen.items(), key=lambda kv: kv[1])


class AsyncRedisStore:
    """`AsyncStateStore` on ``redis.asyncio`` -- the same layout and Lua
    scripts as `RedisStore`, so both may point at one namespace."""

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

        self.k = Keys(prefix)
        self.r: Any = (
            aredis.Redis.from_url(client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self._policy = BaseStore(
            codec=codec, max_snapshot_bytes=max_snapshot_bytes
        )
        self.ttl_s = ttl_s
        self.lock_ttl_ms = int(lock_ttl_ms)
        self._save = self.r.register_script(_SAVE)
        self._delete = self.r.register_script(_DELETE)
        self._forget = self.r.register_script(_FORGET)
        self._unlock = self.r.register_script(_UNLOCK)

    async def load(self, key: str) -> Optional[StoredSnapshot]:
        validate_key(key)
        h = await self.r.hgetall(self.k.snap(key))
        if not h:
            return None
        h = {_s(a): b for a, b in h.items()}
        data = _s(h["snapshot"])
        self._policy._check_size(key, data)
        deadlines = _parse_deadlines(await self.r.hgetall(self.k.dl(key)))
        return StoredSnapshot(
            key=key,
            snapshot=self._policy.codec.decode(data),
            version=int(_s(h["version"])),
            machine_version=_s(h.get("machine_version", "")),
            updated_at=float(_s(h.get("updated_at", 0.0))),
            deadlines=tuple(deadlines),
        )

    async def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        validate_key(key)
        # 📝 #263 battle: the sync stores ran these checks; async did not.
        expected_version, machine_version, deadlines = check_save_args(
            expected_version, machine_version, deadlines
        )
        data = self._policy.codec.encode(snapshot)
        self._policy._check_size(key, data)
        res = await self._save(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
            ],
            args=[
                "" if expected_version is None else str(expected_version),
                data,
                machine_version or "",
                repr(time.time()),
                key,
                "" if self.ttl_s is None else str(int(self.ttl_s * 1000)),
                *_dl_args(tuple(deadlines)),
            ],
        )
        new_version, actual = int(res[0]), int(res[1])
        if new_version == -1:
            raise ConflictError(
                key, expected_version, None if actual == -1 else actual
            )
        return new_version

    async def delete(self, key: str) -> bool:
        validate_key(key)
        res = await self._delete(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
            ],
            args=[key],
        )
        return int(res[0]) > 0

    async def forget(self, key: str) -> Dict[str, int]:
        validate_key(key)
        res = await self._forget(
            keys=[
                self.k.snap(key),
                self.k.keys,
                self.k.dl(key),
                self.k.deadlines,
                self.k.lock(key),
                self.k.log(key),
            ],
            args=[key],
        )
        return {
            "snapshots": int(res[0]),
            "deadlines": int(res[1]),
            "locks": int(res[2]),
            "log_entries": int(res[3]),
        }

    async def list_keys(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[str]:
        pattern = escape_glob(prefix) + "*"
        found: List[str] = []
        async for member in self.r.sscan_iter(
            self.k.keys, match=pattern, count=500
        ):
            found.append(_s(member))
        found.sort()
        return found[:limit]

    def lock(self, key: str, *, timeout: float = 10.0) -> Any:
        return self._alock(key, timeout)

    @contextlib.asynccontextmanager
    async def _alock(self, key: str, timeout: float) -> AsyncIterator[None]:
        import asyncio

        validate_key(key)
        token = secrets.token_hex(16)
        name = self.k.lock(key)
        deadline = time.monotonic() + timeout
        while True:
            if await self.r.set(name, token, nx=True, px=self.lock_ttl_ms):
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
        try:
            ok = bool(await self.r.ping())
            return {"ok": ok, "backend": self.backend, "prefix": self.k.p}
        except redis.RedisError as exc:
            return {"ok": False, "backend": self.backend, "error": str(exc)}
