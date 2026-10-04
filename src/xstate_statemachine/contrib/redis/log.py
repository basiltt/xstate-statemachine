# src/xstate_statemachine/contrib/redis/log.py
"""`RedisLog` -- the transition log (#262) as a Redis Stream (#306)."""

from __future__ import annotations

import json
from typing import Any, List, Optional

import redis

from ...persistence.log import TransitionRecord
from ._errors import redis_errors_typed
from ._keys import Keys

__all__ = ["RedisLog"]


def _s(v: Any) -> str:
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


class RedisLog:
    """`TransitionLogStore` on a Redis Stream per machine id.

    ``XADD`` with ``MAXLEN ~ maxlen`` retention; ``seq`` is kept as a
    field (the stream id is Redis' own). `read(after_seq=)` scans forward
    from the start -- audit trails are short per instance; for millions
    of rows use the SQL stores.

    Args:
        client_or_url: ``redis.Redis`` or URL.
        prefix: **Mandatory** namespace (X0.15).
        maxlen: Approximate per-stream retention (``None`` = unbounded).
    """

    def __init__(
        self,
        client_or_url: Any,
        *,
        prefix: str,
        maxlen: Optional[int] = 10_000,
    ) -> None:
        self.k = Keys(prefix)
        self.r: Any = (
            redis.Redis.from_url(client_or_url)
            if isinstance(client_or_url, str)
            else client_or_url
        )
        self.maxlen = maxlen

    @redis_errors_typed
    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        body = json.dumps(rec.to_dict(), sort_keys=True, default=str)
        kw = (
            {"maxlen": self.maxlen, "approximate": True} if self.maxlen else {}
        )
        self.r.xadd(
            self.k.log(rec.machine_id),
            {"seq": rec.seq, "ts": repr(rec.ts), "record": body},
            **kw,
        )

    @redis_errors_typed
    def next_seq(self, machine_id: str) -> int:
        last = self.r.xrevrange(self.k.log(machine_id), count=1)
        if not last:
            return 1
        _id, fields = last[0]
        fields = {_s(a): b for a, b in fields.items()}
        return int(_s(fields["seq"])) + 1

    @redis_errors_typed
    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        out: List[TransitionRecord] = []
        for _id, fields in self.r.xrange(self.k.log(machine_id)):
            fields = {_s(a): b for a, b in fields.items()}
            seq = int(_s(fields["seq"]))
            if seq <= after_seq:
                continue
            out.append(
                TransitionRecord.from_dict(json.loads(_s(fields["record"])))
            )
            if len(out) >= limit:
                break
        return out

    @redis_errors_typed
    def purge_older_than(self, cutoff_ts: float) -> int:
        n = 0
        for name in self.r.scan_iter(match=f"{self.k.p}:log:*", count=500):
            for _id, fields in self.r.xrange(name):
                fields = {_s(a): b for a, b in fields.items()}
                if float(_s(fields["ts"])) < cutoff_ts:
                    n += int(self.r.xdel(name, _id))
        return n

    @redis_errors_typed
    def forget(self, machine_id: str) -> int:
        name = self.k.log(machine_id)
        n = int(self.r.xlen(name))
        self.r.delete(name)
        return n
