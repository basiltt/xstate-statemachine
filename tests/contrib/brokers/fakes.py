# tests/contrib/brokers/fakes.py
"""In-memory stand-ins for the aiokafka / aio-pika / nats-py client objects
the adapters touch, so `AsyncBrokerContract` runs in CI with no service.

Each fake models only the broker semantics the adapter relies on (and no
more): Kafka partitions + committed offsets, AMQP un-acked messages that
return to the queue on channel close, JetStream num_delivered + ack_wait.
Real-broker behaviour is covered by the opt-in `-m containers` suite.
"""

from __future__ import annotations

import asyncio
import zlib
from collections import deque
from types import SimpleNamespace
from typing import Any, Deque, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Kafka
# -----------------------------------------------------------------------------
class FakeKafkaCluster:
    def __init__(self, partitions: int = 3) -> None:
        self.partitions = partitions
        self.logs: Dict[Tuple[str, int], List[Any]] = {}
        self.committed: Dict[Tuple[str, str, int], int] = {}
        self.fail_sends = 0

    def producer(self) -> "FakeKafkaProducer":
        return FakeKafkaProducer(self)

    def consumer_factory(self, group: str = "g") -> Any:
        return lambda topic: FakeKafkaConsumer(self, topic, group)


class FakeKafkaProducer:
    def __init__(self, cluster: FakeKafkaCluster) -> None:
        self.cluster = cluster
        self.started = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.started = 0

    async def send_and_wait(
        self, topic: str, value: bytes, key: Any, headers: Any
    ) -> None:
        if self.cluster.fail_sends:
            self.cluster.fail_sends -= 1
            raise ConnectionError("kafka down")
        p = zlib.crc32(key or b"") % self.cluster.partitions
        log = self.cluster.logs.setdefault((topic, p), [])
        log.append(
            SimpleNamespace(
                value=value, key=key, headers=headers, offset=len(log)
            )
        )


class FakeKafkaConsumer:
    def __init__(self, cluster: FakeKafkaCluster, topic: str, group: str):
        self.cluster = cluster
        self.topic = topic
        self.group = group
        self.position: Dict[int, int] = {}

    async def start(self) -> None:
        for p in range(self.cluster.partitions):
            self.position[p] = self.cluster.committed.get(
                (self.group, self.topic, p), 0
            )

    async def stop(self) -> None:
        pass

    async def getmany(self, timeout_ms: int = 0, max_records: int = 100):
        out: Dict[Any, List[Any]] = {}
        for p, pos in self.position.items():
            log = self.cluster.logs.get((self.topic, p), [])
            recs = log[pos : pos + max_records]
            if recs:
                out[_TP(self.topic, p)] = recs
                self.position[p] = pos + len(recs)
        if not out and timeout_ms:
            await asyncio.sleep(min(timeout_ms, 20) / 1000)
        return out

    async def commit(self, offsets: Dict[Any, int]) -> None:
        for tp, off in offsets.items():
            self.cluster.committed[(self.group, tp.topic, tp.partition)] = off


class _TP(tuple):
    def __new__(cls, topic: str, partition: int) -> "_TP":
        return super().__new__(cls, (topic, partition))

    @property
    def topic(self) -> str:
        return self[0]

    @property
    def partition(self) -> int:
        return self[1]


# -----------------------------------------------------------------------------
# RabbitMQ (aio-pika surface)
# -----------------------------------------------------------------------------
class FakeAmqpBroker:
    def __init__(self) -> None:
        self.queues: Dict[str, Deque[Any]] = {}

    def channel(self) -> "FakeChannel":
        return FakeChannel(self)


class FakeIncoming:
    def __init__(self, queue: "FakeQueue", message: Any, redelivered: bool):
        self._queue = queue
        self._message = message
        self.body = message.body
        self.headers = dict(message.headers or {})
        self.redelivered = redelivered
        self.settled = False

    async def ack(self) -> None:
        self.settled = True
        self._queue.unacked.discard(self)

    async def reject(self, requeue: bool = False) -> None:
        self.settled = True
        self._queue.unacked.discard(self)
        if requeue:
            self._queue.store.appendleft((self._message, True))


class FakeQueue:
    def __init__(self, store: Deque[Any]) -> None:
        self.store = store
        self.unacked: set = set()

    async def get(self, no_ack: bool = False, fail: bool = True, timeout=5):
        if not self.store:
            return None
        message, redelivered = self.store.popleft()
        msg = FakeIncoming(self, message, redelivered)
        self.unacked.add(msg)
        return msg


class _FakeExchange:
    def __init__(self, broker: FakeAmqpBroker) -> None:
        self.broker = broker

    async def publish(self, message: Any, routing_key: str) -> None:
        self.broker.queues.setdefault(routing_key, deque()).append(
            (message, False)
        )


class FakeChannel:
    def __init__(self, broker: FakeAmqpBroker) -> None:
        self.broker = broker
        self.default_exchange = _FakeExchange(broker)
        self._queues: Dict[str, FakeQueue] = {}

    async def declare_queue(self, name: str, durable: bool = True):
        store = self.broker.queues.setdefault(name, deque())
        q = self._queues.get(name)
        if q is None:
            q = self._queues[name] = FakeQueue(store)
        return q

    def close(self) -> None:
        """Connection lost: un-acked messages return, marked redelivered."""
        for q in self._queues.values():
            for m in sorted(q.unacked, key=id):
                q.store.appendleft((m._message, True))
            q.unacked.clear()


# -----------------------------------------------------------------------------
# NATS JetStream
# -----------------------------------------------------------------------------
class FakeJetStream:
    def __init__(self) -> None:
        self.streams: Dict[str, List[Any]] = {}
        self.seen_ids: set = set()
        self.consumers: Dict[Tuple[str, str], "FakePullSub"] = {}

    async def add_stream(self, name: str, subjects: List[str]) -> None:
        self.streams.setdefault(name, [])

    async def publish(self, subject: str, payload: bytes, headers=None):
        msg_id = (headers or {}).get("Nats-Msg-Id")
        if msg_id in self.seen_ids:
            return  # duplicate window
        self.seen_ids.add(msg_id)
        stream = subject.split(".", 1)[0]
        self.streams.setdefault(stream, []).append((subject, payload))

    async def pull_subscribe(self, subject, durable, stream, config=None):
        key = (stream, durable)
        sub = self.consumers.get(key)
        if sub is None:
            sub = self.consumers[key] = FakePullSub(self, stream)
        return sub


class FakeJsMsg:
    def __init__(self, sub: "FakePullSub", seq: int, data: bytes, n: int):
        self._sub = sub
        self.seq = seq
        self.data = data
        self.metadata = SimpleNamespace(num_delivered=n)

    async def ack(self) -> None:
        self._sub.done.add(self.seq)
        self._sub.pending.pop(self.seq, None)

    async def term(self) -> None:
        await self.ack()


class FakePullSub:
    def __init__(self, js: FakeJetStream, stream: str) -> None:
        self.js = js
        self.stream = stream
        self.next = 0
        self.done: set = set()
        self.pending: Dict[int, int] = {}  # seq -> deliveries
        self.redeliver: Deque[int] = deque()

    async def fetch(self, batch: int = 1, timeout: Optional[float] = 5):
        log = self.js.streams.get(self.stream, [])
        out: List[FakeJsMsg] = []
        while self.redeliver and len(out) < batch:
            seq = self.redeliver.popleft()
            self.pending[seq] += 1
            out.append(FakeJsMsg(self, seq, log[seq][1], self.pending[seq]))
        while self.next < len(log) and len(out) < batch:
            seq = self.next
            self.next += 1
            self.pending[seq] = 1
            out.append(FakeJsMsg(self, seq, log[seq][1], 1))
        if not out:
            await asyncio.sleep(min(timeout or 0, 0.02))
            raise asyncio.TimeoutError()
        return out

    def expire_ack_wait(self) -> None:
        """Simulate ack_wait elapsing: every pending message redelivers."""
        for seq in sorted(self.pending):
            if seq not in self.done:
                self.redeliver.append(seq)
