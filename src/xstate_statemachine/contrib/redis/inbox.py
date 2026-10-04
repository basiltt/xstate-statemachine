# src/xstate_statemachine/contrib/redis/inbox.py
"""`RedisInbox` -- the idempotency inbox (#261) on Redis (#306).

🏛️ Battle #306 (agent B) decisions, each pinned by
``tests/contrib/redis/test_battle_306_inbox_log.py``:

* **Server clock.** Every expiry is computed AND compared on the Redis
  server's ``TIME`` inside the Lua scripts, never on the caller's
  ``time.time()``. Two hosts five minutes apart used to disagree on
  whether a key was still live: the fast host re-admitted a key the slow
  host had just claimed (a double charge), the slow one kept answering
  409 for a key that had expired. One clock -- Redis' -- makes the TTL a
  fleet-wide fact.
* **TTL index member** is ``"{len(scope_bytes)}:{scope}{key}"``. The old
  ``"{scope}|{key}"`` was split at the FIRST ``|``, so a principal
  containing ``|`` made `purge_expired` delete the wrong field (or none)
  and the entry was never purged.
* **`mark(ttl_s=None)` removes the index member.** It used to keep the
  claim's expiry in the index, so the next `purge_expired` deleted a
  receipt that was meant to live forever -- and the redelivery ran the
  actions again.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import redis

from ...persistence.idempotency import InboxEntry
from ._errors import redis_errors_typed
from ._keys import Keys
from .store import escape_glob

__all__ = ["RedisInbox"]

#: Shared Lua prelude: ``now()`` = the server clock in float seconds and
#: ``member(scope, key)`` = the TTL-index member for one entry.
_PRELUDE = """
local function now()
  local t = redis.call('TIME')
  return tonumber(t[1]) + tonumber(t[2]) / 1000000
end
local function member(scope, key)
  return string.len(scope) .. ':' .. scope .. key
end
local function expiry(ttl)
  if ttl == '' then return nil end
  return now() + tonumber(ttl)
end
local function put(hash, zset, scope, key, fp, receipt, ttl)
  local exp = expiry(ttl)
  local e = {fingerprint = fp, receipt_json = receipt}
  if exp then e.expires_at = string.format('%.6f', exp) end
  redis.call('HSET', hash, key, cjson.encode(e))
  if exp then
    redis.call('ZADD', zset, exp, member(scope, key))
  else
    redis.call('ZREM', zset, member(scope, key))
  end
end
local function live(raw)
  if not raw then return false end
  local e = cjson.decode(raw)
  return e.expires_at == nil or e.expires_at == cjson.null
    or tonumber(e.expires_at) > now()
end
"""

#: KEYS: inbox hash, exp zset. ARGV: key, fp, ttl|"", scope.
_CLAIM = _PRELUDE + """
if live(redis.call('HGET', KEYS[1], ARGV[1])) then return 0 end
put(KEYS[1], KEYS[2], ARGV[4], ARGV[1], ARGV[2], cjson.null, ARGV[3])
return 1
"""

#: KEYS: inbox hash, exp zset. ARGV: key, receipt, ttl|"", scope.
_MARK = _PRELUDE + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
local fp = ''
if raw then fp = cjson.decode(raw).fingerprint end
put(KEYS[1], KEYS[2], ARGV[4], ARGV[1], fp, ARGV[2], ARGV[3])
return 1
"""

#: KEYS: inbox hash. ARGV: key. Returns the entry iff live, else nil.
_GET = _PRELUDE + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if live(raw) then return raw end
return nil
"""

#: KEYS: inbox hash, exp zset. ARGV: key, scope. Drop only if in flight.
_RELEASE = _PRELUDE + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if raw then
  local e = cjson.decode(raw)
  if e.receipt_json == cjson.null or e.receipt_json == nil then
    redis.call('HDEL', KEYS[1], ARGV[1])
    redis.call('ZREM', KEYS[2], member(ARGV[2], ARGV[1]))
    return 1
  end
end
return 0
"""

#: KEYS: exp zset. ARGV: now|"" (server clock), hash-name prefix.
#: Range-deletes expired members and their hash fields -- O(log n + k).
_PURGE = _PRELUDE + """
local at = ARGV[1]
if at == '' then at = now() end
local members = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', at)
local n = 0
for _, m in ipairs(members) do
  local sep = string.find(m, ':', 1, true)
  local len = sep and tonumber(string.sub(m, 1, sep - 1))
  if len then
    local scope = string.sub(m, sep + 1, sep + len)
    local key = string.sub(m, sep + len + 1)
    n = n + redis.call('HDEL', ARGV[2] .. scope, key)
  end
  redis.call('ZREM', KEYS[1], m)
end
return n
"""

#: KEYS: inbox hash, exp zset. ARGV: scope. Atomic tenant erase.
_FORGET = _PRELUDE + """
local fields = redis.call('HKEYS', KEYS[1])
for _, f in ipairs(fields) do
  redis.call('ZREM', KEYS[2], member(ARGV[1], f))
end
redis.call('DEL', KEYS[1])
return #fields
"""


def _s(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


def _ttl(ttl_s: Optional[float]) -> str:
    return "" if ttl_s is None else repr(float(ttl_s))


class RedisInbox:
    """`InboxStore` on Redis: one hash per scope (field = idempotency key,
    value = JSON `InboxEntry`) plus a sorted-set TTL index so
    `purge_expired()` is a range query, not a scan.

    Shares a namespace with a `RedisStore` given the same ``prefix``;
    `RedisStore.forget()` does not touch inbox rows (they are per
    principal/scope, not per instance) -- call `inbox.forget(scope)`.

    📝 Expiry uses the Redis server clock (see the module docstring), so
    hosts with skewed clocks agree on whether a key is live. A claim
    whose worker died before `mark` stays in flight (answering 409) until
    its TTL passes -- the same rule as `SQLiteInbox` / `MemoryInbox`
    (the plugin claims with its ``ttl_s``).

    ⚠️ Not transactional with `RedisStore`: Redis has no multi-key
    transaction spanning the snapshot save, so the mark is written right
    AFTER the save. A crash in between is covered by the in-snapshot
    ``processed_ids`` ring (#261), as for any non-shared inbox.
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
        self._get = self.r.register_script(_GET)
        self._release = self.r.register_script(_RELEASE)
        self._purge = self.r.register_script(_PURGE)
        self._forget = self.r.register_script(_FORGET)

    def _keys(self, scope: str) -> list:
        return [self.k.inbox(scope), self.k.inbox_exp]

    @redis_errors_typed
    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        raw = self._get(keys=[self.k.inbox(scope)], args=[key])
        if raw is None:
            return None
        e = json.loads(_s(raw))
        exp = e.get("expires_at")
        receipt = e.get("receipt_json")
        return InboxEntry(
            str(e.get("fingerprint", "")),
            None if receipt is None else str(receipt),
            None if exp is None else float(exp),
        )

    @redis_errors_typed
    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        res = self._claim(
            keys=self._keys(scope), args=[key, fp, _ttl(ttl_s), scope]
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
            keys=self._keys(scope),
            args=[key, receipt_json, _ttl(ttl_s), scope],
        )

    @redis_errors_typed
    def release(self, scope: str, key: str) -> None:
        self._release(keys=self._keys(scope), args=[key, scope])

    @redis_errors_typed
    def purge_expired(self, *, now: Optional[float] = None) -> int:
        """Drop every entry expired at *now* (default: the Redis server
        clock). A range query on the TTL index, not a scan."""
        at = "" if now is None else repr(float(now))
        return int(
            self._purge(
                keys=[self.k.inbox_exp],
                args=[at, self.k.inbox("")],
            )
        )

    @redis_errors_typed
    def forget(self, scope: str) -> int:
        """Erase one scope (tenant) atomically; other scopes -- including
        glob look-alikes such as ``x*`` vs ``xy`` -- are untouched."""
        return int(self._forget(keys=self._keys(scope), args=[scope]))

    @redis_errors_typed
    def __len__(self) -> int:
        n = 0
        pattern = escape_glob(self.k.inbox("")) + "*"
        for name in self.r.scan_iter(match=pattern, count=500):
            n += int(self.r.hlen(name))
        return n
