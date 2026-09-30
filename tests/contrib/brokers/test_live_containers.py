# tests/contrib/brokers/test_live_containers.py
"""#294 acceptance on REAL brokers (opt-in: ``XSM_CONTAINERS=1`` + Docker).

For each broker: the `AsyncBrokerContract`, then 1,000 envelopes across
10 subjects through `InboundDispatcher` + an inbox, with the broker
container RESTARTED mid-consume -- the adapter must resume, lose nothing,
keep per-subject order, and the inbox must absorb redeliveries. Images
are pinned by digest. SQS runs on LocalStack without the restart (the
free LocalStack does not persist across restarts).

Run: ``XSM_CONTAINERS=1 pytest tests/contrib/brokers -m containers``.
"""

from __future__ import annotations

import asyncio
import json
import socket
import time
import unittest
import uuid
from typing import Any, Callable, Dict, List, Optional

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.eda import Envelope, InboundDispatcher
from src.xstate_statemachine.persistence import MemoryStore
from src.xstate_statemachine.persistence.idempotency import MemoryInbox

from ...eda.contract import AsyncBrokerContract
from .conftest import LIVE

pytestmark = [
    pytest.mark.containers,
    pytest.mark.skipif(not LIVE, reason="live brokers: XSM_CONTAINERS=1"),
]

IMAGES = {
    "redis": "redis@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499",  # 7.4-alpine
    "redpanda": "redpandadata/redpanda@sha256:82a69763bef8d8b55ea5a520fa1b38f993908ef68946819ca1aed43541824c48",  # v24.2.7
    "rabbitmq": "rabbitmq@sha256:d7af1c87c5f1eda13fcfca06db452bf3aeab6619fc3358b68535c0c02c4e52bc",  # 3.13-alpine
    "nats": "nats@sha256:b83efabe3e7def1e0a4a31ec6e078999bb17c80363f881df35edc70fcb6bb927",  # 2.10-alpine
    "localstack": "localstack/localstack@sha256:b279c01f4cfb8f985a482e4014cabc1e2697b9d7a6c8c8db2e40f4d9f93687c7",  # 3.8
}
N, SUBJECTS = 1000, 10


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_port(port: int, timeout: float = 60.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), 1):
                return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(port)


def _wait_amqp(port: int, timeout: float = 90.0) -> None:
    """RabbitMQ opens its port before it accepts AMQP: really connect."""
    import aio_pika

    _wait_port(port, timeout)
    end = time.monotonic() + timeout

    async def once() -> None:
        conn = await aio_pika.connect(f"amqp://guest:guest@127.0.0.1:{port}/")
        await conn.close()

    while True:
        try:
            asyncio.run(once())
            return
        except Exception:  # noqa: BLE001 - not ready yet
            if time.monotonic() > end:
                raise
            time.sleep(1)


def _wait_kafka(port: int, timeout: float = 90.0) -> None:
    """Redpanda opens its port before it serves metadata: really produce."""
    from aiokafka import AIOKafkaProducer

    _wait_port(port, timeout)
    end = time.monotonic() + timeout

    async def once() -> None:
        p = AIOKafkaProducer(bootstrap_servers=f"127.0.0.1:{port}")
        try:
            await p.start()
            await p.send_and_wait("xsm-ready", b"1")
        finally:
            await p.stop()

    while True:
        try:
            asyncio.run(once())
            return
        except Exception:  # noqa: BLE001 - not ready yet
            if time.monotonic() > end:
                raise
            time.sleep(1)


class _Container:
    """A container on FIXED host ports so a restart keeps the address."""

    def __init__(self, image: str, ports: Dict[int, int], **kw: Any):
        from testcontainers.core.container import DockerContainer

        self.c = DockerContainer(image)
        for inner, outer in ports.items():
            self.c.with_bind_ports(inner, outer)
        for k, v in kw.get("env", {}).items():
            self.c.with_env(k, v)
        if kw.get("command"):
            self.c.with_command(kw["command"])
        self.ports = ports

    def start(self, ready: Callable[[], None]) -> "_Container":
        self.c.start()
        self._ready = ready
        ready()
        return self

    def restart(self) -> None:
        self.c.get_wrapped_container().restart(timeout=5)
        self._ready()

    def stop(self) -> None:
        self.c.stop()


def _machine() -> Any:
    cfg = {
        "id": "m",
        "initial": "on",
        "context": {"seen": []},
        "states": {"on": {"on": {"E": {"actions": "rec"}}}},
    }

    def rec(i: Any, ctx: Any, e: Any, a: Any) -> None:
        ctx["seen"] = ctx["seen"] + [e.payload["n"]]

    return create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))


def run_resume_scenario(
    tc: unittest.TestCase,
    make: Callable[[], Any],
    topic: str,
    restart: Optional[Callable[[], None]],
) -> None:
    """Publish N envelopes, consume half, restart the broker, consume the
    rest with a FRESH adapter; assert order + completeness + dedup."""
    store, inbox = MemoryStore(), MemoryInbox()
    machine = _machine()

    async def phase(broker: Any, stop_after: Optional[int]) -> int:
        disp = InboundDispatcher(store, {"xsm.m.E": machine}, inbox=inbox)
        done, idle = 0, 0
        while idle < 20:
            try:
                res = await disp.run_once(broker, topic, timeout=0.5)
            except Exception:  # noqa: BLE001 - broker restarting
                await asyncio.sleep(0.5)
                continue
            got = res.processed + res.duplicates
            done += got
            idle = 0 if got else idle + 1
            if stop_after is not None and done >= stop_after:
                break
        return done

    async def go() -> None:
        pub = make()
        for n in range(N):
            await pub.publish(
                topic,
                Envelope.new(
                    type="xsm.m.E", subject=f"s{n % SUBJECTS}", data={"n": n}
                ),
            )
        await _close(pub)
        first = make()
        await phase(first, N // 2)
        await _close(first, quiet=True)

    asyncio.run(go())
    if restart is not None:
        restart()

    async def rest() -> None:
        second = make()
        await phase(second, None)
        await _close(second, quiet=True)

    asyncio.run(rest())
    for s in range(SUBJECTS):
        rec = store.load(f"s{s}")
        tc.assertIsNotNone(rec, s)
        seen = json.loads(rec.snapshot)["context"]["seen"]  # type: ignore
        tc.assertEqual(seen, list(range(s, N, SUBJECTS)), f"subject s{s}")


async def _close(broker: Any, quiet: bool = False) -> None:
    try:
        r = broker.close()
        if asyncio.iscoroutine(r):
            await r
    except Exception:  # noqa: BLE001
        if not quiet:
            raise


# -----------------------------------------------------------------------------
class TestLiveRedisStreams(AsyncBrokerContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.box = _Container(
            IMAGES["redis"],
            {6379: cls.port},
            command="redis-server --appendonly yes --appendfsync always",
        ).start(lambda: _wait_port(cls.port))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.stop()

    def make_broker(self, prefix: Optional[str] = None) -> Any:
        import redis

        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            RedisStreamsBroker,
        )

        client = redis.Redis(
            port=self.port, retry_on_timeout=True, socket_timeout=5
        )
        return RedisStreamsBroker(
            client,
            prefix=prefix or f"c{uuid.uuid4().hex[:6]}",
            min_idle_ms=1000,
        )

    def test_resume_after_restart(self) -> None:
        p = f"r{uuid.uuid4().hex[:6]}"
        run_resume_scenario(
            self, lambda: self.make_broker(p), "orders", self.box.restart
        )


class TestLiveKafka(AsyncBrokerContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.box = _Container(
            IMAGES["redpanda"],
            {9092: cls.port},
            command=(
                "redpanda start --mode dev-container --smp 1 "
                "--kafka-addr 0.0.0.0:9092 "
                f"--advertise-kafka-addr 127.0.0.1:{cls.port}"
            ),
        ).start(lambda: _wait_kafka(cls.port))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.stop()

    def setUp(self) -> None:
        self.topic = f"t{uuid.uuid4().hex[:8]}"
        self.group = f"g{uuid.uuid4().hex[:6]}"

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.kafka import KafkaBroker

        return KafkaBroker(
            bootstrap_servers=f"127.0.0.1:{self.port}", group_id=self.group
        )

    def _drain(self, broker: Any) -> List[Any]:
        async def go() -> List[Any]:
            got: List[Any] = []
            async for d in broker.subscribe(self.topic, timeout=5):
                got.append(d)
                if len(got) >= 20:
                    break
            return got

        return asyncio.run(go())

    @unittest.skip(
        "Kafka commits offsets: an un-acked delivery is not "
        "'removed' per poll -- covered by the resume scenario"
    )
    def test_nack_without_requeue_drops(self) -> None:  # pragma: no cover
        pass

    def test_resume_after_restart(self) -> None:
        run_resume_scenario(
            self, self.make_broker, self.topic, self.box.restart
        )


class TestLiveRabbitMQ(AsyncBrokerContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.box = _Container(IMAGES["rabbitmq"], {5672: cls.port}).start(
            lambda: _wait_amqp(cls.port)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.stop()

    def setUp(self) -> None:
        self.topic = f"q{uuid.uuid4().hex[:8]}"

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.rabbitmq import (
            RabbitMQBroker,
        )

        return RabbitMQBroker(url=f"amqp://guest:guest@127.0.0.1:{self.port}/")

    def test_resume_after_restart(self) -> None:
        run_resume_scenario(
            self, self.make_broker, self.topic, self.box.restart
        )


class TestLiveNats(AsyncBrokerContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.box = _Container(
            IMAGES["nats"], {4222: cls.port}, command="-js -sd /data"
        ).start(lambda: (_wait_port(cls.port), time.sleep(1)))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.stop()

    def setUp(self) -> None:
        self.topic = f"T{uuid.uuid4().hex[:8]}"

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.nats import NatsBroker

        return NatsBroker(
            servers=f"nats://127.0.0.1:{self.port}", ack_wait_s=5
        )

    def test_resume_after_restart(self) -> None:
        run_resume_scenario(
            self, self.make_broker, self.topic, self.box.restart
        )


class TestLiveSqs(AsyncBrokerContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.box = _Container(
            IMAGES["localstack"], {4566: cls.port}, env={"SERVICES": "sqs"}
        ).start(lambda: (_wait_port(cls.port), time.sleep(5)))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.box.stop()

    def _client(self) -> Any:
        import boto3

        return boto3.client(
            "sqs",
            region_name="us-east-1",
            endpoint_url=f"http://127.0.0.1:{self.port}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

    def setUp(self) -> None:
        self.topic = f"q{uuid.uuid4().hex[:8]}.fifo"
        self._client().create_queue(
            QueueName=self.topic,
            Attributes={"FifoQueue": "true", "VisibilityTimeout": "30"},
        )

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.sqs import SqsBroker

        return SqsBroker(self._client())

    @unittest.skip(
        "FIFO holds a group while a message is in flight; the "
        "moto suite covers the drained-order variant"
    )
    def test_per_subject_order_is_preserved(self) -> None:  # pragma: no cover
        pass

    def test_thousand_envelopes_in_order(self) -> None:
        run_resume_scenario(self, self.make_broker, self.topic, None)
