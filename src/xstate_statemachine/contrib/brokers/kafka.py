# src/xstate_statemachine/contrib/brokers/kafka.py
# -----------------------------------------------------------------------------
# ðŸŸ« Kafka broker (aiokafka) -- key = subject, commit the acked prefix (#294)
# -----------------------------------------------------------------------------
# ðŸ›ï¸ Kafka has no per-message ack: a consumer commits an OFFSET per
#    partition. The adapter keeps, per partition, the offsets it handed
#    out and the ones settled, and commits only the contiguous settled
#    prefix -- so a crash re-delivers everything from the first
#    un-settled message (at-least-once; the inbox dedups). A
#    ``nack(requeue=True)`` is served from the local buffer (see
#    `_base`), never by seeking.
#
#    * Partition key = ``envelope.subject`` (Kafka's default partitioner
#      hashes the key), so per-subject order is Kafka's per-partition
#      order.
#    * Structured-mode CloudEvents body + ``content-type`` header
#      (CloudEvents Kafka binding); ``ce_id`` / ``ce_type`` headers too so
#      a router can filter without parsing.
#    * Kafka keeps no delivery count: the attempt number carried across a
#      restart is the envelope's own ``xsmattempt`` (the dispatcher's
#      count lives for the process).
#    * TLS / SASL: pass the aiokafka keyword arguments through
#      (``security_protocol=``, ``ssl_context=``, ``sasl_*``); they are
#      never echoed by ``repr``.
# -----------------------------------------------------------------------------
"""`KafkaBroker` -- an async `BrokerAdapter` over aiokafka."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .._compat import require_extra

require_extra("kafka", "aiokafka")

from ...eda.envelope import Envelope  # noqa: E402
from ._base import CE_CONTENT_TYPE, AsyncBroker, Raw, structured  # noqa: E402

__all__ = ["KafkaBroker", "KafkaTransport"]

_BATCH = 100


class _Partition:
    """Offsets handed out / settled on one partition (commit bookkeeping)."""

    __slots__ = ("handed", "settled", "committed")

    def __init__(self) -> None:
        self.handed: List[int] = []
        self.settled: Set[int] = set()
        self.committed: Optional[int] = None

    def commit_point(self) -> Optional[int]:
        """The next offset to commit, or ``None`` if nothing advanced."""
        last = None
        while self.handed and self.handed[0] in self.settled:
            off = self.handed.pop(0)
            self.settled.discard(off)
            last = off
        return None if last is None else last + 1


class KafkaTransport:
    """The four native operations over an aiokafka producer + consumers.

    Args:
        bootstrap_servers: Passed to aiokafka (ignored when both
            *producer* and *consumer_factory* are given).
        group_id: Consumer group (one per logical consumer service).
        producer: A started-or-not ``AIOKafkaProducer``-compatible object.
        consumer_factory: ``(topic) -> AIOKafkaConsumer``-compatible
            object (auto-commit OFF). Default builds a real one.
        client_kw: Extra aiokafka keyword arguments (TLS, SASL, ...).
    """

    def __init__(
        self,
        *,
        bootstrap_servers: Any = None,
        group_id: str = "xsm",
        producer: Any = None,
        consumer_factory: Optional[Callable[[str], Any]] = None,
        batch: int = _BATCH,
        max_bytes: int,
        client_kw: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.batch = int(batch)
        self.max_bytes = max_bytes
        self._client_kw = dict(client_kw or {})
        self._producer = producer
        self._owns_producer = producer is None
        self._producer_started = False
        self._factory = consumer_factory or self._real_consumer
        self._consumers: Dict[str, Any] = {}
        self._parts: Dict[Tuple[str, Any], _Partition] = {}

    # -- clients ----------------------------------------------------------------
    def _real_consumer(self, topic: str) -> Any:
        from aiokafka import AIOKafkaConsumer

        return AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            **self._client_kw,
        )

    async def _producer_ready(self) -> Any:
        if self._producer is None:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                acks="all",
                enable_idempotence=True,
                **self._client_kw,
            )
        if not self._producer_started:
            await self._producer.start()
            self._producer_started = True
        return self._producer

    async def _consumer(self, topic: str) -> Any:
        c = self._consumers.get(topic)
        if c is None:
            c = self._factory(topic)
            await c.start()
            self._consumers[topic] = c
        return c

    # -- operations -------------------------------------------------------------
    async def send(self, topic: str, envelope: Envelope) -> None:
        producer = await self._producer_ready()
        headers = [
            ("content-type", CE_CONTENT_TYPE.encode()),
            ("ce_id", envelope.id.encode()),
            ("ce_type", envelope.type.encode()),
        ]
        key = (envelope.subject or "").encode("utf-8") or None
        await producer.send_and_wait(
            topic,
            value=structured(envelope, self.max_bytes),
            key=key,
            headers=headers,
        )

    async def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        consumer = await self._consumer(topic)
        batches = await consumer.getmany(
            timeout_ms=int(wait_s * 1000), max_records=self.batch
        )
        out: List[Raw] = []
        for tp, records in batches.items():
            part = self._parts.setdefault((topic, tp), _Partition())
            for rec in records:
                part.handed.append(rec.offset)
                out.append(Raw(rec.value, (topic, tp, rec.offset), 0))
        return out

    async def ack(self, native: Any) -> None:
        topic, tp, offset = native
        part = self._parts.setdefault((topic, tp), _Partition())
        part.settled.add(offset)
        point = part.commit_point()
        if point is not None:
            consumer = await self._consumer(topic)
            await consumer.commit({tp: point})
            part.committed = point

    drop = ack

    def rebind(self) -> None:
        """Forget clients opened on a previous event loop (see `_base`).
        Only clients WE built are dropped; injected ones are kept."""
        self._consumers.clear()
        self._parts.clear()
        if self._owns_producer:
            self._producer = None
            self._producer_started = False

    async def close(self) -> None:
        for c in list(self._consumers.values()):
            await c.stop()
        self._consumers.clear()
        if self._producer is not None and self._producer_started:
            await self._producer.stop()
            self._producer_started = False


class KafkaBroker(AsyncBroker):
    """Async `BrokerAdapter` over Kafka (aiokafka).

    ::

        broker = KafkaBroker(bootstrap_servers="kafka:9092",
                             group_id="orders-svc")
        await broker.publish("orders", envelope)   # key = subject

    Args:
        bootstrap_servers / group_id / producer / consumer_factory:
            See `KafkaTransport`.
        client_kw: aiokafka keyword arguments (TLS, SASL).
        max_bytes / on_disconnect / on_reconnect / on_undecodable: See
            `contrib.brokers`.
    """

    def __init__(
        self,
        *,
        bootstrap_servers: Any = None,
        group_id: str = "xsm",
        producer: Any = None,
        consumer_factory: Optional[Callable[[str], Any]] = None,
        batch: int = _BATCH,
        client_kw: Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        super().__init__(None, **kw)
        self.transport = KafkaTransport(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            producer=producer,
            consumer_factory=consumer_factory,
            batch=batch,
            max_bytes=self.max_bytes,
            client_kw=client_kw,
        )

    def __repr__(self) -> str:
        return f"KafkaBroker(group_id={self.transport.group_id!r})"
