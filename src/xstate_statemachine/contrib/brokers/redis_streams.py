# src/xstate_statemachine/contrib/brokers/redis_streams.py
# -----------------------------------------------------------------------------
# 🟥 Redis Streams broker -- consumer groups, XACK, PEL reclaim (#294)
# -----------------------------------------------------------------------------
# 🏛️ Lives under `contrib/brokers/` (not `contrib/redis/`) so every broker
#    is found in one place; it is gated by the SAME `[redis]` extra and
#    shares `contrib.redis`'s key conventions (mandatory `prefix`, X0.15):
#
#        {prefix}:stream:{topic}            the stream (shards=1)
#        {prefix}:stream:{topic}:{n}        shard n of `shards` (n >= 2)
#
#    * Partition key = ``envelope.subject``: with ``shards > 1`` a subject
#      always hashes (crc32, stable across processes) to one shard, so
#      per-subject order holds; one stream is totally ordered anyway.
#    * Consumer group `group` (created lazily, ``MKSTREAM``, from id 0 so
#      nothing published before the first consumer is lost), consumer
#      name `consumer`. ``ack`` = ``XACK``; ``nack(requeue=False)`` =
#      ``XACK`` too (dead-lettering is the dispatcher's job -- X0.8).
#    * Crash recovery: entries a dead consumer left in the PEL for at
#      least ``min_idle_ms`` are claimed with ``XAUTOCLAIM`` before new
#      entries are read; their delivery count becomes the envelope's
#      attempt count (`Envelope.with_attempt`).
#    * ``maxlen`` trims the stream approximately on ``XADD`` (backpressure
#      on disk, X0.8); ``None`` keeps everything.
#
#    Built on a SYNC redis-py client (thread-safe connection pool) so one
#    client backs both engines; the async adapter runs the calls on a
#    worker thread. A redis-py ``block`` of 0 means "forever", so a zero
#    wait is sent as no ``BLOCK`` at all.
# -----------------------------------------------------------------------------
"""`RedisStreamsBroker` (async) and `SyncRedisStreamsBroker`."""

from __future__ import annotations

import os
import socket
import zlib
from typing import Any, Dict, List, Optional, Set

from .._compat import require_extra

require_extra("redis", "redis")

import redis  # noqa: E402

from ...eda.envelope import Envelope  # noqa: E402
from ..redis._keys import validate_prefix  # noqa: E402
from ._base import (  # noqa: E402
    AsyncBroker,
    Raw,
    SyncBroker,
    ThreadedTransport,
    structured,
)

__all__ = [
    "RedisStreamsBroker",
    "RedisStreamsTransport",
    "SyncRedisStreamsBroker",
]

#: M1: small by default -- fetched entries wait locally while the
#: broker's redelivery clock runs.
_BATCH = 10


def _default_consumer() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


class RedisStreamsTransport:
    """The four native operations over one redis-py client."""

    def __init__(
        self,
        client: Any,
        *,
        prefix: str,
        group: str = "xsm",
        consumer: Optional[str] = None,
        shards: int = 1,
        min_idle_ms: int = 60_000,
        maxlen: Optional[int] = None,
        batch: int = _BATCH,
        max_bytes: int,
    ) -> None:
        if shards < 1:
            raise ValueError("shards must be >= 1")
        self.client = client
        self.prefix = validate_prefix(prefix)
        self.group = group
        self.consumer = consumer or _default_consumer()
        self.shards = int(shards)
        self.min_idle_ms = int(min_idle_ms)
        self.maxlen = maxlen
        self.batch = int(batch)
        self.max_bytes = max_bytes
        self._groups: Set[str] = set()
        #: (stream, entry id) fetched by THIS transport and not yet
        #: settled -- never reclaimed from ourselves.
        self._held: Set[Any] = set()
        #: XAUTOCLAIM cursor per stream: the scan resumes where it stopped
        #: so entries past a run of our own held ones are reached.
        self._cursor: Dict[str, str] = {}

    @property
    def redelivery_window_s(self) -> float:
        """Entries idle this long may be reclaimed by another consumer."""
        return self.min_idle_ms / 1000.0

    def forget(self, native: Any) -> None:
        """Released locally (M1): another consumer may reclaim it."""
        self._held.discard(native)

    # -- keys -------------------------------------------------------------------
    def stream(self, topic: str, shard: int = 0) -> str:
        """The stream key for *topic* (and *shard*)."""
        base = f"{self.prefix}:stream:{topic}"
        return base if self.shards == 1 else f"{base}:{shard}"

    def shard_of(self, subject: Optional[str]) -> int:
        """The shard a *subject* always hashes to (crc32)."""
        if self.shards == 1:
            return 0
        return zlib.crc32((subject or "").encode("utf-8")) % self.shards

    def streams(self, topic: str) -> List[str]:
        """Every shard stream key of *topic*."""
        return [self.stream(topic, n) for n in range(self.shards)]

    def _ensure_group(self, stream: str) -> None:
        if stream in self._groups:
            return
        try:
            self.client.xgroup_create(
                stream, self.group, id="0", mkstream=True
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._groups.add(stream)

    # -- operations -------------------------------------------------------------
    def send(self, topic: str, envelope: Envelope) -> None:
        """Publish *envelope* on *topic*; raise on failure."""
        stream = self.stream(topic, self.shard_of(envelope.subject))
        fields = {
            "ce": structured(envelope, self.max_bytes),
            "subject": envelope.subject or "",
        }
        if self.maxlen is None:
            self.client.xadd(stream, fields)
        else:
            self.client.xadd(
                stream, fields, maxlen=self.maxlen, approximate=True
            )

    def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        """Pull what is ready on *topic*, waiting at most *wait_s*."""
        out: List[Raw] = []
        for stream in self.streams(topic):
            self._ensure_group(stream)
            out.extend(self._reclaim(stream))
        if out:
            self._held.update(r.native for r in out)
            return out
        room = self.batch
        wanted: Dict[str, str] = {s: ">" for s in self.streams(topic)}
        kw: Dict[str, Any] = {"count": room}
        ms = int(wait_s * 1000)
        if ms > 0:
            kw["block"] = ms
        reply = self.client.xreadgroup(self.group, self.consumer, wanted, **kw)
        for stream_name, entries in reply or []:
            stream = _text(stream_name)
            for entry_id, fields in entries:
                out.append(self._raw(stream, entry_id, fields, 0))
        self._held.update(r.native for r in out)
        return out

    def _reclaim(self, stream: str) -> List[Raw]:
        """Claim entries idle >= min_idle_ms (a dead consumer's PEL).

        🏛️ M3: ONE ``XPENDING`` lists the candidates with their
        delivery counts; entries this transport still holds are excluded
        BEFORE claiming (a claim bumps ``times_delivered`` -- re-claiming
        our own would inflate attempts), then one ``XCLAIM`` takes the
        rest. The scan resumes from a per-stream cursor.
        """
        start = self._cursor.get(stream, "-")
        pending = self.client.xpending_range(
            stream,
            self.group,
            min=start,
            max="+",
            count=self.batch * 4,
        )
        if not pending:
            self._cursor.pop(stream, None)  # wrapped: rescan from the top
            return []
        last = _text(pending[-1]["message_id"])
        self._cursor[stream] = "(" + last
        counts: Dict[str, int] = {}
        for row in pending:
            eid = _text(row["message_id"])
            if (stream, eid) in self._held:
                continue  # ours, still being processed
            # 📝 idle filtered here, not with XPENDING IDLE: identical on
            #    every Redis >= 5 (IDLE is 6.2+) and on fakeredis.
            if int(row.get("time_since_delivered", 0)) < self.min_idle_ms:
                continue
            counts[eid] = int(row["times_delivered"])
            if len(counts) >= self.batch:
                break
        if not counts:
            return []
        claimed = self.client.xclaim(
            stream, self.group, self.consumer, self.min_idle_ms, list(counts)
        )
        out: List[Raw] = []
        for entry_id, fields in claimed or []:
            eid = _text(entry_id)
            if not fields:  # deleted while pending: nothing to deliver
                self.client.xack(stream, self.group, entry_id)
                continue
            # the claim itself was a delivery: attempts = count before it
            out.append(self._raw(stream, entry_id, fields, counts[eid]))
        return out

    @staticmethod
    def _raw(stream: str, entry_id: Any, fields: Any, attempts: int) -> Raw:
        body = fields.get(b"ce", fields.get("ce", b""))
        return Raw(body, (stream, _text(entry_id)), attempts)

    def ack(self, native: Any) -> None:
        """Settle a delivery for good."""
        stream, entry_id = native
        self.client.xack(stream, self.group, entry_id)
        self._held.discard(native)

    drop = ack

    def close(self) -> None:
        """Release the client connections this object opened."""
        close = getattr(self.client, "close", None)
        if close is not None:
            close()


def _text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _transport(
    client: Any, url: Optional[str], kw: Dict[str, Any], max_bytes: int
) -> RedisStreamsTransport:
    if client is None:
        if url is None:
            raise ValueError("pass client= or url=")
        client = redis.Redis.from_url(url)
    return RedisStreamsTransport(client, max_bytes=max_bytes, **kw)


_TRANSPORT_KEYS = (
    "prefix",
    "group",
    "consumer",
    "shards",
    "min_idle_ms",
    "maxlen",
    "batch",
)


def _split(kw: Dict[str, Any]) -> Dict[str, Any]:
    return {k: kw.pop(k) for k in _TRANSPORT_KEYS if k in kw}


class SyncRedisStreamsBroker(SyncBroker):
    """Blocking `SyncBrokerAdapter` over Redis Streams.

    Args:
        client: A ``redis.Redis`` (or ``fakeredis.FakeRedis``); or
        url: ``redis://...`` (``rediss://`` for TLS).
        prefix: Mandatory key namespace (X0.15).
        group / consumer: Consumer group and this consumer's name
            (default ``hostname-pid``).
        shards: Streams per topic; subjects hash to one shard.
        min_idle_ms: Reclaim another consumer's pending entries after
            this idle time (crash recovery).
        maxlen: Approximate stream cap on publish.
        max_bytes / on_disconnect / on_reconnect / on_undecodable: See
            `contrib.brokers`.
    """

    def __init__(
        self,
        client: Any = None,
        *,
        url: Optional[str] = None,
        prefix: str,
        **kw: Any,
    ) -> None:
        tkw = _split(kw)
        tkw["prefix"] = prefix
        super().__init__(
            None,
            **kw,
        )
        self.transport = _transport(client, url, tkw, self.max_bytes)

    def __repr__(self) -> str:  # no URL: it may carry a password
        t = self.transport
        return (
            f"SyncRedisStreamsBroker(prefix={t.prefix!r}, group={t.group!r})"
        )


class RedisStreamsBroker(AsyncBroker):
    """Async `BrokerAdapter` over Redis Streams (same arguments as
    `SyncRedisStreamsBroker`; calls run on a worker thread)."""

    def __init__(
        self,
        client: Any = None,
        *,
        url: Optional[str] = None,
        prefix: str,
        **kw: Any,
    ) -> None:
        tkw = _split(kw)
        tkw["prefix"] = prefix
        super().__init__(None, **kw)
        self.streams = _transport(client, url, tkw, self.max_bytes)
        self.transport = ThreadedTransport(self.streams)

    def __repr__(self) -> str:
        t = self.streams
        return f"RedisStreamsBroker(prefix={t.prefix!r}, group={t.group!r})"
