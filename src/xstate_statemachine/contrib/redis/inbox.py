# src/xstate_statemachine/contrib/redis/inbox.py
"""`RedisInbox` -- the idempotency inbox (#261) on Redis (#306)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import redis

from ...persistence.idempotency import InboxEntry
from ._errors import redis_errors_typed
from ._keys import Keys

__all__ = ["RedisInbox"]

#: KEYS[1]=inbox hash KEYS[2]=exp zset
#: ARGV[1]=key ARGV[2]=fp ARGV[3]=expires_at|"" ARGV[4]=now ARGV[5]=scope
#: Claim: succeed iff absent or expired. Returns 1 / 0.
_CLAIM = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if raw then
  local e = cjson.decode(raw)
  if e.expires_at == cjson.null or e.expires_at == nil or tonumber(e.expires_at) > tonumber(ARGV[4]) then
    return 0
  end
end
local entry = {fingerprint = ARGV[2], receipt_json = cjson.null}
if ARGV[3] ~= '' then entry.expires_at = tonumber(ARGV[3]) else entry.expires_at = cjson.null end
redis.call('HSET', KEYS[1], ARGV[1], cjson.encode(entry))
if ARGV[3] ~= '' then
  redis.call('ZADD', KEYS[2], ARGV[3], ARGV[5] .. '|' .. ARGV[1])
else
  redis.call('ZREM', KEYS[2], ARGV[5] .. '|' .. ARGV[1])
end
return 1
"""

#: KEYS[1]=inbox hash KEYS[2]=exp zset ARGV[1]=key ARGV[2]=receipt ARGV[3]=expires_at|"" ARGV[4]=scope
_MARK = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
local fp = ''
if raw then fp = cjson.decode(raw).fingerprint end
local entry = {fingerprint = fp, receipt_json = ARGV[2]}
if ARGV[3] ~= '' then entry.expires_at = tonumber(ARGV[3]) else entry.expires_at = cjson.null end
redis.call('HSET', KEYS[1], ARGV[1], cjson.encode(entry))
if ARGV[3] ~= '' then
  redis.call('ZADD', KEYS[2], ARGV[3], ARGV[4] .. '|' .. ARGV[1])
end
return 1
"""

#: KEYS[1]=inbox hash KEYS[2]=exp zset ARGV[1]=key ARGV[2]=scope. Drop only if in flight.
_RELEASE = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if raw then
  local e = cjson.decode(raw)
  if e.receipt_json == cjson.null or e.receipt_json == nil then
    redis.call('HDEL', KEYS[1], ARGV[1])
    redis.call('ZREM', KEYS[2], ARGV[2] .. '|' .. ARGV[1])
    return 1
  end
end
return 0
"""

#: KEYS[1]=exp zset ARGV[1]=now ARGV[2]=prefix. Purge expired members and their hash fields.
_PURGE = """
local members = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
local n = 0
for _, m in ipairs(members) do
  local sep = string.find(m, '|', 1, true)
  local scope = string.sub(m, 1, sep - 1)
  local key = string.sub(m, sep + 1)
  n = n + redis.call('HDEL', ARGV[2] .. ':inbox:' .. scope, key)
  redis.call('ZREM', KEYS[1], m)
end
return n
"""


def _s(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


class RedisInbox:
    """`InboxStore` on Redis: one hash per scope (field = idempotency key,
    value = JSON `InboxEntry`) plus a sorted-set TTL index so
    `purge_expired()` is a range query, not a scan.

    Shares a namespace with a `RedisStore` given the same ``prefix``;
    `RedisStore.forget()` does not touch inbox rows (they are per
    principal/scope, not per instance) -- call `inbox.forget(scope)`.
    """

    def __init__(self, client_or_url: Any, *, prefix: str) -> None:
        self.k = Keys(prefix)
        self.r: Any = (
            redis.Redis.from_url(client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self._claim = self.r.register_script(_CLAIM)
        self._mark = self.r.register_script(_MARK)
        self._release = self.r.register_script(_RELEASE)
        self._purge = self.r.register_script(_PURGE)

    def _expiry(self, ttl_s: Optional[float]) -> str:
        return "" if ttl_s is None else repr(time.time() + float(ttl_s))

    @redis_errors_typed
    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        raw = self.r.hget(self.k.inbox(scope), key)
        if raw is None:
            return None
        e = json.loads(_s(raw))
        exp = e.get("expires_at")
        if exp is not None and float(exp) <= time.time():
            return None
        return InboxEntry(
            str(e.get("fingerprint", "")), e.get("receipt_json"), exp
        )

    @redis_errors_typed
    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        res = self._claim(
            keys=[self.k.inbox(scope), self.k.inbox_exp],
            args=[key, fp, self._expiry(ttl_s), repr(time.time()), scope],
        )
        return int(res) == 1

    @redis_errors_typed
    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        self._mark(
            keys=[self.k.inbox(scope), self.k.inbox_exp],
            args=[key, receipt_json, self._expiry(ttl_s), scope],
        )

    @redis_errors_typed
    def release(self, scope: str, key: str) -> None:
        self._release(
            keys=[self.k.inbox(scope), self.k.inbox_exp], args=[key, scope]
        )

    @redis_errors_typed
    def purge_expired(self, *, now: Optional[float] = None) -> int:
        at = time.time() if now is None else now
        return int(
            self._purge(keys=[self.k.inbox_exp], args=[repr(at), self.k.p])
        )

    @redis_errors_typed
    def forget(self, scope: str) -> int:
        name = self.k.inbox(scope)
        fields = [_s(f) for f in self.r.hkeys(name)]
        pipe = self.r.pipeline()
        pipe.delete(name)
        for f in fields:
            pipe.zrem(self.k.inbox_exp, f"{scope}|{f}")
        pipe.execute()
        return len(fields)

    @redis_errors_typed
    def __len__(self) -> int:
        n = 0
        for name in self.r.scan_iter(match=f"{self.k.p}:inbox:*", count=500):
            n += int(self.r.hlen(name))
        return n
