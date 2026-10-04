# src/xstate_statemachine/contrib/redis/_layout.py
"""Lua scripts, key/argument layout and record parsing shared by
`RedisStore` and `AsyncRedisStore` (#306).

🏛️ #306 battle: the async store was a hand-copy of the sync one and had
drifted (no schema check, no non-str / negative-version refusal, raw
codec errors, no key filtering in `list_keys`). Everything both engines
need now lives here once; the two classes only differ in *delivery*.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...exceptions import ConflictError, SnapshotCorruptError, StoreError
from ...persistence.deadline import Deadline, check_deadline_record
from ...persistence.store import BaseStore, check_save_args, validate_key
from ._keys import SCHEMA_VERSION, Keys

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
  redis.call('ZREM', KEYS[4], f)
  redis.call('ZREM', KEYS[4], ARGV[5] .. '|' .. f)  -- layout-1 member
end
redis.call('DEL', KEYS[3])
local i = 7
while i <= #ARGV do
  local field = ARGV[i]; local due = ARGV[i+1]; local body = ARGV[i+2]
  redis.call('HSET', KEYS[3], field, body)
  redis.call('ZADD', KEYS[4], due, field)
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
  redis.call('ZREM', KEYS[4], f)
  redis.call('ZREM', KEYS[4], ARGV[1] .. '|' .. f)  -- layout-1 member
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
  redis.call('ZREM', KEYS[4], f)
  redis.call('ZREM', KEYS[4], ARGV[1] .. '|' .. f)  -- layout-1 member
end
redis.call('DEL', KEYS[3])
return {snaps, #fields, 0}
"""

#: KEYS[1]=deadlines zset; ARGV = (member, snapshot hash) pairs. Drops
#: index members whose snapshot hash is gone (a `ttl_s` expiry leaves the
#: zset entry behind -- Redis cannot expire a zset MEMBER). The EXISTS and
#: the ZREM run in one script, so a concurrent save that recreates the
#: record (and re-adds its member) is never undone. Returns the removed.
_PRUNE = """
local gone = {}
local i = 1
while i <= #ARGV do
  if redis.call('EXISTS', ARGV[i+1]) == 0 then
    redis.call('ZREM', KEYS[1], ARGV[i])
    gone[#gone + 1] = ARGV[i]
  end
  i = i + 2
end
return gone
"""

#: KEYS[1]=lock ARGV[1]=token. Compare-and-delete: only the owner releases.
_UNLOCK = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


def _dl_member(key: str, d: Deadline) -> str:
    """The zset member AND dl-hash field for deadline *d* of *key*.

    🐛 #306 battle: the layout-1 member was ``"{key}|{state_id}|..."`` and
    `due_keys` split on the first ``|`` -- a key containing ``|`` (legal:
    `validate_key` allows it) woke the WRONG instance ("a" for "a|b"), and
    the real one never woke. Layout 2 is a JSON array, unambiguous for
    any key / state id; `_member_key` still reads layout-1 members.
    """
    return json.dumps(
        [key, d.state_id, d.entry_seq, d.event_type],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _member_key(member: Any) -> str:
    text = _s(member)
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], str):
            return parsed[0]
    return text.split("|", 1)[0]  # layout-1 member


def _dl_args(key: str, deadlines: Sequence[Deadline]) -> List[str]:
    out: List[str] = []
    for d in deadlines:
        out.extend(
            [
                _dl_member(key, d),
                repr(float(d.due_at_wall)),
                json.dumps(d.to_dict()),
            ]
        )
    return out


def _check_options(ttl_s: Optional[float], lock_ttl_ms: int) -> None:
    # 🐛 #306 battle: `lock_ttl_ms=0` reached Redis as `SET PX 0` (a raw
    #    ResponseError on the first lock), and `ttl_s=0.0001` / `ttl_s=-1`
    #    made every save write a record that was ALREADY expired -- a
    #    silent "save succeeded, load returns None". Fail at construction.
    if int(lock_ttl_ms) < 1:
        raise ValueError("lock_ttl_ms must be >= 1")
    if ttl_s is not None and int(ttl_s * 1000) < 1:
        raise ValueError("ttl_s must be None or >= 0.001 (one millisecond)")


#: 📝 Bounds applied when the store builds its own client from a URL. A
#: Redis that accepts TCP but never answers must not hang `load()`
#: forever (redis-py < 6 defaults to NO socket timeout). A URL query
#: string (``?socket_timeout=30``) overrides these -- redis-py lets the
#: query string win over keyword arguments.
DEFAULT_SOCKET_TIMEOUT_S = 5.0
DEFAULT_SOCKET_CONNECT_TIMEOUT_S = 5.0


def _client_from_url(factory: Any, url: str) -> Any:
    return factory.from_url(
        url,
        socket_timeout=DEFAULT_SOCKET_TIMEOUT_S,
        socket_connect_timeout=DEFAULT_SOCKET_CONNECT_TIMEOUT_S,
    )


def _check_save_call(
    policy: BaseStore,
    key: str,
    snapshot: Any,
    expected_version: Optional[int],
    machine_version: str,
    deadlines: Sequence[Deadline],
) -> Tuple[str, Optional[int], str, Tuple[Deadline, ...]]:
    """`BaseStore.save`'s argument policy, shared with the async store so
    the two cannot drift (#306 battle: async accepted a non-str snapshot,
    a negative ``expected_version`` and an unwrapped codec failure)."""
    validate_key(key)
    if not isinstance(snapshot, str):
        raise TypeError(
            "snapshot must be the JSON str from get_snapshot(), got "
            f"{type(snapshot).__name__}"
        )
    expected_version, machine_version, dls = check_save_args(
        expected_version, machine_version, deadlines
    )
    if expected_version is not None and expected_version < 0:
        raise ValueError("expected_version must be >= 0 or None")
    data = policy._encode(key, snapshot)
    policy._check_size(key, data)
    return data, expected_version, machine_version or "", tuple(dls)


def _parse_snap_hash(
    key: str, h: Dict[Any, Any]
) -> Tuple[str, int, str, float]:
    """``(data, version, machine_version, updated_at)`` from a raw hash.

    🐛 #306 battle: a hash another writer damaged (no ``snapshot`` field,
    ``version="x"``) escaped as a bare KeyError / ValueError -- a 500, not
    the typed `SnapshotCorruptError` every other backend raises.
    """
    row = {_s(a): b for a, b in h.items()}
    try:
        return (
            _s(row["snapshot"]),
            int(_s(row["version"])),
            _s(row.get("machine_version", "")),
            float(_s(row.get("updated_at", 0.0))),
        )
    except (KeyError, ValueError, UnicodeDecodeError) as exc:
        raise SnapshotCorruptError(
            f"Redis record for '{key}' is damaged: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _schema_check(prefix: str, cur: Any) -> bool:
    """Validate a stored schema value; True when it must be (re)written."""
    if cur is None:
        return True
    try:
        found = int(_s(cur))
    except (ValueError, UnicodeDecodeError):
        raise StoreError(
            f"Redis namespace '{prefix}' has an unreadable schema marker "
            f"{cur!r}; refusing to use it."
        ) from None
    if found > SCHEMA_VERSION:
        raise StoreError(
            f"Redis namespace '{prefix}' has schema version {found}, "
            f"newer than this library supports ({SCHEMA_VERSION})."
        )
    return found < SCHEMA_VERSION


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


#: KEYS[1]=schema ARGV[1]=this library's layout. Creates the marker, or
#: raises an OLDER one to ours -- never lowers a newer one (two processes
#: of different releases racing construction). Returns the marker.
_SCHEMA = """
local cur = redis.call('GET', KEYS[1])
if not cur or (tonumber(cur) and tonumber(cur) < tonumber(ARGV[1])) then
  redis.call('SET', KEYS[1], ARGV[1])
  return ARGV[1]
end
return cur
"""


class _Layout:
    """Key lists and script arguments shared by both engines -- one place,
    so `RedisStore` and `AsyncRedisStore` cannot drift (#306 battle)."""

    def __init__(self, keys: Keys, ttl_s: Optional[float]) -> None:
        self.k = keys
        self.ttl_s = ttl_s

    def save_keys(self, key: str) -> List[str]:
        k = self.k
        return [k.snap(key), k.keys, k.dl(key), k.deadlines]

    def forget_keys(self, key: str) -> List[str]:
        return self.save_keys(key) + [self.k.lock(key), self.k.log(key)]

    def save_args(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Sequence[Deadline],
    ) -> List[str]:
        ttl = "" if self.ttl_s is None else str(int(self.ttl_s * 1000))
        return [
            "" if expected_version is None else str(expected_version),
            data,
            machine_version,
            repr(time.time()),
            key,
            ttl,
            *_dl_args(key, deadlines),
        ]

    def prune_args(self, members: Sequence[Any]) -> List[str]:
        out: List[str] = []
        for m in members:
            out.extend([_s(m), self.k.snap(_member_key(m))])
        return out


def _saved_version(res: Any, key: str, expected_version: Optional[int]) -> int:
    new_version, actual = int(res[0]), int(res[1])
    if new_version == -1:
        raise ConflictError(
            key, expected_version, None if actual == -1 else actual
        )
    return new_version


def _forget_counts(res: Any) -> Dict[str, int]:
    return {
        "snapshots": int(res[0]),
        "deadlines": int(res[1]),
        "locks": int(res[2]),
        "log_entries": int(res[3]),
    }


def _due_rows(
    rows: Sequence[Tuple[Any, float]], gone: Sequence[Any]
) -> List[Tuple[str, float]]:
    dead = {_s(m) for m in gone}
    seen: Dict[str, float] = {}
    for member, score in rows:
        if _s(member) not in dead:
            seen.setdefault(_member_key(member), float(score))
    return sorted(seen.items(), key=lambda kv: (kv[1], kv[0]))


def _sorted_members(members: List[Any], limit: int) -> List[str]:
    found = sorted(_s(m) for m in members)
    return found[:limit]
