# src/xstate_statemachine/contrib/redis/log.py
"""`RedisLog` -- the transition log (#262) as a Redis Stream (#306).

🏛️ Battle #306 (agent B): the stream entry id IS the record's seq
(``"{seq}-0"``) and every append is one Lua compare-and-append that
refuses a seq not above the stream's top, so

* two writers can never store the same seq (the old auto-id layout let
  32 concurrent appenders mint 640 rows with 37 distinct seqs -- `replay`
  then rebuilt a wrong state or refused the whole log);
* `append_next` is atomic: read the top, compare-and-append top+1, and
  on refusal (another writer won) read again;
* ``read(after_seq=, limit=)`` is ``XRANGE (after_seq+1)-0 + COUNT limit``
  -- O(log n + limit), not a scan of the whole stream per page.

📝 Not transactional with `RedisStore`: there is no multi-key transaction
spanning the snapshot save, so `TransitionLogPlugin` writes records after
the block commits -- the log may TRAIL the snapshot after a crash, never
lead it (#262). The ``connection=`` argument (SQLite's same-transaction
hook) is accepted for protocol parity and ignored.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, List, Optional, Tuple

import redis

from ...exceptions import StoreError
from ...persistence.log import (
    LogCorruptError,
    TransitionRecord,
    _check_append,
    _check_cutoff,
    _check_read,
)
from ._errors import redis_errors_typed
from ._keys import Keys
from .store import escape_glob

__all__ = ["RedisLog"]

#: How often `append_next` re-reads the top after losing a race before it
#: gives up loudly (32 writers on one key need a handful).
_MAX_APPEND_RETRIES = 1000

#: Page size for `purge_older_than`'s walk of a stream.
_PURGE_PAGE = 1000

#: KEYS[1]=stream ARGV=ids. Delete them; drop the stream if now empty so
#: its last-generated id does not block a restart at seq 1 (SQLite parity:
#: ``MAX(seq)`` of an empty table is 0).
_XDEL_AND_DROP = """
local n = redis.call('XDEL', KEYS[1], unpack(ARGV))
if redis.call('XLEN', KEYS[1]) == 0 then redis.call('DEL', KEYS[1]) end
return n
"""

#: KEYS[1]=stream ARGV: seq, ts, record JSON, maxlen|"". Append at id
#: "{seq}-0" iff seq is above the top seq (compare-and-append); 0 if not.
_APPEND = """
local top = redis.call('XREVRANGE', KEYS[1], '+', '-', 'COUNT', 1)
if top[1] then
  local s = tonumber(string.match(top[1][1], '^(%d+)-'))
  if s and s >= tonumber(ARGV[1]) then return 0 end
end
local id = ARGV[1] .. '-0'
if ARGV[4] ~= '' then
  redis.call('XADD', KEYS[1], 'MAXLEN', '~', ARGV[4], id,
    'seq', ARGV[1], 'ts', ARGV[2], 'record', ARGV[3])
else
  redis.call('XADD', KEYS[1], id,
    'seq', ARGV[1], 'ts', ARGV[2], 'record', ARGV[3])
end
return 1
"""


def _s(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


def _seq_of(entry_id: Any) -> int:
    ms, _, part = _s(entry_id).partition("-")
    if part != "0" or not ms.isdigit():
        raise LogCorruptError(f"stream id {_s(entry_id)!r} is not '<seq>-0'")
    return int(ms)


class RedisLog:
    """`TransitionLogStore` on a Redis Stream per machine id.

    Args:
        client_or_url: ``redis.Redis`` or URL.
        prefix: **Mandatory** namespace (X0.15).
        maxlen: Per-stream retention, ``XADD MAXLEN ~`` (approximate: at
            least *maxlen* newest entries are kept). ``None`` (default)
            = unbounded, like `SQLiteLog`. ⚠️ Trimming drops the HEAD of
            the audit trail: `replay()` then needs a snapshot taken at
            the first retained record and refuses (`ReplayDivergenceError`
            on ``seq``) without one.
    """

    def __init__(
        self,
        client_or_url: Any,
        *,
        prefix: str,
        maxlen: Optional[int] = None,
    ) -> None:
        if maxlen is not None and (
            isinstance(maxlen, bool) or not isinstance(maxlen, int)
        ):
            raise ValueError(f"maxlen must be None or an int, got {maxlen!r}")
        if maxlen is not None and maxlen < 1:
            raise ValueError(f"maxlen must be >= 1, got {maxlen!r}")
        self.k = Keys(prefix)
        self.r: Any = (
            redis.Redis.from_url(client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self.maxlen = maxlen
        self._drop = self.r.register_script(_XDEL_AND_DROP)
        self._append = self.r.register_script(_APPEND)

    # -- write -----------------------------------------------------------------
    def _xadd(self, rec: TransitionRecord) -> bool:
        """Compare-and-append *rec*; ``False`` when its seq is taken."""
        body = json.dumps(rec.to_dict(), sort_keys=True, default=str)
        res = self._append(
            keys=[self.k.log(rec.machine_id)],
            args=[rec.seq, repr(rec.ts), body, self.maxlen or ""],
        )
        return int(res) == 1

    @redis_errors_typed
    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        """Append *rec* at its own seq. A seq not above the stream's top
        is refused (`StoreError`) -- never stored twice."""
        _check_append(rec)
        if not self._xadd(rec):
            raise StoreError(
                f"RedisLog: seq {rec.seq} of {rec.machine_id!r} is not "
                f"above the stream's last seq (duplicate append refused)"
            )

    @redis_errors_typed
    def append_next(
        self, rec: TransitionRecord, *, connection: Any = None
    ) -> TransitionRecord:
        """Assign top+1 and append; atomic across workers (the append is
        a compare-and-set, the loser re-reads and tries the next seq)."""
        _check_append(replace(rec, seq=1))
        for _ in range(_MAX_APPEND_RETRIES):
            out = replace(rec, seq=self.next_seq(rec.machine_id))
            if self._xadd(out):
                return out
        raise StoreError(
            f"RedisLog: could not append to {rec.machine_id!r} after "
            f"{_MAX_APPEND_RETRIES} attempts (write contention)"
        )

    # -- read ------------------------------------------------------------------
    @redis_errors_typed
    def next_seq(self, machine_id: str) -> int:
        last = self.r.xrevrange(self.k.log(machine_id), count=1)
        return _seq_of(last[0][0]) + 1 if last else 1

    @redis_errors_typed
    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        _check_read(after_seq, limit)
        if limit == 0:
            return []
        name = self.k.log(machine_id)
        if after_seq == 0:
            head = self.r.xrange(name, count=1)
            if head and _seq_of(head[0][0]) < 1:
                raise LogCorruptError(f"{name}: entry with seq < 1")
        rows = self.r.xrange(name, min=f"{after_seq + 1}-0", count=limit)
        return [self._decode(name, machine_id, i, f) for i, f in rows]

    @staticmethod
    def _decode(
        name: str, machine_id: str, entry_id: Any, fields: Any
    ) -> TransitionRecord:
        where = f"{name} id={_s(entry_id)}"
        try:
            f = {_s(a): b for a, b in fields.items()}
            rec = TransitionRecord.from_dict(json.loads(_s(f["record"])))
        except (KeyError, ValueError, TypeError) as exc:
            raise LogCorruptError(f"{where}: {exc}") from exc
        if rec.seq != _seq_of(entry_id) or rec.machine_id != machine_id:
            raise LogCorruptError(
                f"{where}: entry id disagrees with its record "
                f"({rec.machine_id!r}, {rec.seq})"
            )
        return rec

    # -- retention ---------------------------------------------------------------
    @redis_errors_typed
    def purge_older_than(self, cutoff_ts: float) -> int:
        """Delete records with ``ts < cutoff_ts`` in every stream of this
        prefix. O(total entries): pages through each stream."""
        cutoff = _check_cutoff(cutoff_ts)
        n = 0
        pattern = escape_glob(self.k.log("")) + "*"
        for name in self.r.scan_iter(match=pattern, count=500):
            n += self._purge_stream(_s(name), cutoff)
        return n

    def _purge_stream(self, name: str, cutoff: float) -> int:
        n, start = 0, "-"
        while True:
            page: List[Tuple[Any, Any]] = self.r.xrange(
                name, min=start, count=_PURGE_PAGE
            )
            if not page:
                return n
            dead = [
                _s(i)
                for i, f in page
                if float(_s({_s(a): b for a, b in f.items()}["ts"])) < cutoff
            ]
            if dead:
                n += int(self._drop(keys=[name], args=dead))
            start = f"({_s(page[-1][0])}"

    @redis_errors_typed
    def forget(self, machine_id: str) -> int:
        name = self.k.log(machine_id)
        pipe = self.r.pipeline()
        pipe.xlen(name)
        pipe.delete(name)
        n, _ = pipe.execute()
        return int(n)
