"""Offline stand-ins for Kafka, RabbitMQ, NATS JetStream and SQS.

The adapters in ``xstate_statemachine.contrib.brokers`` are the REAL ones;
only the client object underneath is replaced when no live broker is
configured:

* **Kafka** -- `FakeKafkaCluster`: partitions keyed by a CRC of the
  subject, a log per partition and committed offsets per group. No
  rebalance, no replication, no retention.
* **RabbitMQ** -- `FakeAmqpBroker`: one deque per queue; messages fetched
  and not acked return to the head of the queue, marked ``redelivered``,
  when their channel closes (the AMQP rule the adapter relies on).
* **NATS JetStream** -- `FakeJetStream`: one stream per topic, a durable
  pull consumer with ``num_delivered`` and a ``Nats-Msg-Id`` dedup
  window that never expires. ``ack_wait`` only elapses when
  `crash()` says so.
* **SQS** -- `moto` (``mock_aws``), a real in-process SQS emulation with a
  FIFO queue: ``MessageGroupId`` ordering, ``MessageDeduplicationId``
  dedup and ``ApproximateReceiveCount``.

These are copies of the fakes the library's own unit tests inject
(``tests/contrib/brokers/fakes.py``), trimmed to what this app touches,
so the example is self-contained.
"""

import asyncio
import os
import zlib
from collections import deque
from types import SimpleNamespace
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

#: The SQS adapter picks FIFO semantics from the ``.fifo`` suffix.
SQS_QUEUE = "events.fifo"


# -------------------------------------------------------------------------
# 🟫 Kafka (aiokafka surface)
# -------------------------------------------------------------------------
class FakeKafkaCluster:
    """Partitioned logs + committed offsets per (group, topic, partition)."""

    def __init__(self, partitions: int = 3) -> None:
        self.partitions = partitions
        self.logs: Dict[Tuple[str, int], List[Any]] = {}
        self.committed: Dict[Tuple[str, str, int], int] = {}

    def producer(self) -> "FakeKafkaProducer":
        return FakeKafkaProducer(self)

    def consumer_factory(self, group: str) -> Callable[[str], Any]:
        return lambda topic: FakeKafkaConsumer(self, topic, group)


class FakeKafkaProducer:
    def __init__(self, cluster: FakeKafkaCluster) -> None:
        self.cluster = cluster

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send_and_wait(
        self, topic: str, value: bytes, key: Any, headers: Any
    ) -> None:
        p = zlib.crc32(key or b"") % self.cluster.partitions
        log = self.cluster.logs.setdefault((topic, p), [])
        log.append(
            SimpleNamespace(
                value=value, key=key, headers=headers, offset=len(log)
            )
        )


class _TP(tuple):
    def __new__(cls, topic: str, partition: int) -> "_TP":
        return super().__new__(cls, (topic, partition))

    @property
    def topic(self) -> str:
        return self[0]

    @property
    def partition(self) -> int:
        return self[1]


class FakeKafkaConsumer:
    """Starts at the group's committed offsets (a restart re-reads the
    un-committed tail); owns every partition -- no rebalance."""

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

    async def getmany(
        self, timeout_ms: int = 0, max_records: int = 100
    ) -> Dict[Any, List[Any]]:
        out: Dict[Any, List[Any]] = {}
        for p, pos in self.position.items():
            log = self.cluster.logs.get((self.topic, p), [])
            recs = log[pos : pos + max_records]
            if recs:
                out[_TP(self.topic, p)] = recs
                self.position[p] = pos + len(recs)
        return out

    async def commit(self, offsets: Dict[Any, int]) -> None:
        for tp, off in offsets.items():
            self.cluster.committed[(self.group, tp.topic, tp.partition)] = off


# -------------------------------------------------------------------------
# 🐇 RabbitMQ (aio-pika surface)
# -------------------------------------------------------------------------
class FakeAmqpBroker:
    """Queues shared by every channel; `channel()` opens a consumer."""

    def __init__(self) -> None:
        self.queues: Dict[str, Deque[Any]] = {}
        self.channels: List["FakeChannel"] = []

    def channel(self) -> "FakeChannel":
        chan = FakeChannel(self)
        self.channels.append(chan)
        return chan


class FakeIncoming:
    def __init__(self, queue: "FakeQueue", message: Any, redelivered: bool):
        self._queue = queue
        self._message = message
        self.body = message.body
        self.headers = dict(message.headers or {})
        self.redelivered = redelivered

    async def ack(self) -> None:
        self._queue.unacked.discard(self)

    async def reject(self, requeue: bool = False) -> None:
        self._queue.unacked.discard(self)
        if requeue:
            self._queue.store.appendleft((self._message, True))


class FakeQueue:
    def __init__(self, store: Deque[Any]) -> None:
        self.store = store
        self.unacked: set = set()

    async def get(
        self, no_ack: bool = False, fail: bool = True, timeout: Any = 5
    ) -> Optional[FakeIncoming]:
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

    async def declare_queue(self, name: str, durable: bool = True) -> Any:
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


# -------------------------------------------------------------------------
# 🟩 NATS JetStream (nats-py surface)
# -------------------------------------------------------------------------
class FakeJetStream:
    def __init__(self) -> None:
        self.streams: Dict[str, List[Any]] = {}
        self.seen_ids: set = set()
        self.consumers: Dict[Tuple[str, str], "FakePullSub"] = {}

    async def add_stream(self, name: str, subjects: List[str]) -> None:
        self.streams.setdefault(name, [])

    async def publish(
        self, subject: str, payload: bytes, headers: Any = None
    ) -> None:
        msg_id = (headers or {}).get("Nats-Msg-Id")
        if msg_id in self.seen_ids:
            return  # the duplicate window (never expires here)
        self.seen_ids.add(msg_id)
        stream = subject.split(".", 1)[0]
        self.streams.setdefault(stream, []).append((subject, payload))

    async def pull_subscribe(
        self, subject: str, durable: str, stream: str, config: Any = None
    ) -> "FakePullSub":
        key = (stream, durable)
        sub = self.consumers.get(key)
        if sub is None:
            sub = self.consumers[key] = FakePullSub(self, stream)
        return sub

    def expire_ack_wait(self) -> None:
        for sub in self.consumers.values():
            sub.expire_ack_wait()


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

    async def fetch(
        self, batch: int = 1, timeout: Optional[float] = 5
    ) -> List[FakeJsMsg]:
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
            raise asyncio.TimeoutError()
        return out

    def expire_ack_wait(self) -> None:
        """``ack_wait`` elapsed: every pending message is redelivered."""
        for seq in sorted(self.pending):
            if seq not in self.done:
                self.redeliver.append(seq)


# -------------------------------------------------------------------------
# 🟧 SQS (moto)
# -------------------------------------------------------------------------
class MotoSqs:
    """A started ``moto.mock_aws`` plus a boto3 client and the FIFO queue."""

    def __init__(self) -> None:
        import boto3
        import moto

        # 📝 moto needs credentials to exist; they are never sent anywhere.
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        self.mock = moto.mock_aws()
        self.mock.start()
        self.client = boto3.client("sqs", region_name="us-east-1")
        ensure_queue(self.client)

    def stop(self) -> None:
        self.mock.stop()


def ensure_queue(client: Any) -> None:
    """Create the FIFO queue (idempotent on SQS for equal attributes)."""
    client.create_queue(QueueName=SQS_QUEUE, Attributes={"FifoQueue": "true"})


# -------------------------------------------------------------------------
# 🧰 Construction + crash simulation
# -------------------------------------------------------------------------
def new_stand_in(name: str) -> Any:
    """The shared in-process backend for broker *name*."""
    if name == "redis-streams":
        import fakeredis

        return fakeredis.FakeRedis()
    if name == "kafka":
        return FakeKafkaCluster()
    if name == "rabbitmq":
        return FakeAmqpBroker()
    if name == "nats":
        return FakeJetStream()
    if name == "sqs":
        return MotoSqs()
    raise ValueError(f"no offline stand-in for {name!r}")


def close_stand_in(stand_in: Any) -> None:
    stop = getattr(stand_in, "stop", None)
    if isinstance(stand_in, MotoSqs) and stop is not None:
        stop()


def crash(name: str, stand_in: Any, broker: Any, deliveries: Any) -> None:
    """Simulate the consumer that holds *deliveries* dying before it acks,
    using each broker's own redelivery path:

    * Redis Streams / Kafka: nothing to do -- the entries stay pending /
      the offsets stay un-committed; the next consumer re-reads them.
    * RabbitMQ: the channel closes; the queue re-offers the messages with
      ``redelivered=True``.
    * NATS: ``ack_wait`` elapses; JetStream redelivers, ``num_delivered``
      counts up.
    * SQS: the visibility timeout elapses (set to 0 through the adapter's
      own ``extend_visibility``); ``ApproximateReceiveCount`` counts up.
    """
    if name == "rabbitmq":
        for chan in stand_in.channels:
            chan.close()
    elif name == "nats":
        stand_in.expire_ack_wait()
    elif name == "sqs":
        for d in deliveries:
            broker.extend_visibility(d, 0)
