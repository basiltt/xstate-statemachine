# tests/contrib/kafka/test_kafka_broker.py
"""#294: `KafkaBroker` -- `AsyncBrokerContract` over an in-memory
aiokafka stand-in (partitions + committed offsets), plus Kafka specifics:
key = subject, CloudEvents headers, commit only the contiguous settled
prefix (a crash re-delivers from the first un-settled offset), health."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any, List

from src.xstate_statemachine.eda import BrokerAdapter, Envelope

from ...eda.contract import AsyncBrokerContract
from ..brokers.fakes import FakeKafkaCluster
from ..conftest import requires_extra

pytestmark = requires_extra("kafka")


def _broker(cluster: FakeKafkaCluster, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.brokers.kafka import KafkaBroker

    return KafkaBroker(
        producer=cluster.producer(),
        consumer_factory=cluster.consumer_factory("g"),
        **kw,
    )


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class TestKafkaContract(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return _broker(FakeKafkaCluster())


class TestKafkaSpecific(unittest.TestCase):
    def test_protocol_and_repr(self) -> None:
        b = _broker(FakeKafkaCluster(), group_id="orders")
        self.assertIsInstance(b, BrokerAdapter)
        self.assertEqual(repr(b), "KafkaBroker(group_id='orders')")

    def test_key_is_subject_and_headers_are_cloudevents(self) -> None:
        cluster = FakeKafkaCluster(partitions=1)
        env = _env("o-1", 1)
        asyncio.run(_broker(cluster).publish("t", env))
        (rec,) = cluster.logs[("t", 0)]
        self.assertEqual(rec.key, b"o-1")
        headers = dict(rec.headers)
        self.assertEqual(headers["ce_id"], env.id.encode())
        self.assertIn(b"cloudevents", headers["content-type"])
        self.assertEqual(json.loads(rec.value)["id"], env.id)

    def test_commit_advances_only_over_the_settled_prefix(self) -> None:
        cluster = FakeKafkaCluster(partitions=1)
        b = _broker(cluster)

        async def go() -> List[int]:
            for n in range(3):
                await b.publish("t", _env("k", n))
            got = [d async for d in b.subscribe("t", timeout=0)]
            await b.ack(got[1])  # out of order: nothing committable
            self.assertEqual(cluster.committed, {})
            await b.ack(got[0])  # 0 and 1 settled -> commit 2
            self.assertEqual(cluster.committed[("g", "t", 0)], 2)
            # "crash": a new consumer resumes from the committed offset
            fresh = _broker(cluster)
            return [
                d.envelope.data["n"]
                async for d in fresh.subscribe("t", timeout=0)
            ]

        self.assertEqual(asyncio.run(go()), [2])

    def test_refetch_after_rebalance_never_moves_commit_backwards(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib.brokers.kafka import _Partition

        p = _Partition()
        for off in (5, 6, 7):
            p.track(off)
        p.settled.update({5, 6, 7})
        self.assertEqual(p.commit_point(), 8)
        p.committed = 8
        self.assertFalse(p.track(5))  # re-fetched after a rebalance
        self.assertTrue(p.track(8))
        self.assertIsNone(p.commit_point())

    def test_publish_failure_raises_and_marks_unhealthy(self) -> None:
        cluster = FakeKafkaCluster()
        downs: List[Any] = []
        b = _broker(cluster, on_disconnect=downs.append)
        cluster.fail_sends = 1

        async def go() -> None:
            with self.assertRaises(ConnectionError):
                await b.publish("t", _env("k", 1))
            self.assertFalse(b.healthy)
            await b.publish("t", _env("k", 2))
            self.assertTrue(b.healthy)
            await b.close()

        asyncio.run(go())
        self.assertEqual(len(downs), 1)

    def test_real_client_objects_are_built_lazily(self) -> None:
        from src.xstate_statemachine.contrib.brokers.kafka import (
            KafkaTransport,
        )

        t = KafkaTransport(
            bootstrap_servers="127.0.0.1:1", group_id="g", max_bytes=1000
        )

        async def build() -> str:
            consumer = t._real_consumer("t")  # built, never started
            return type(consumer).__name__

        self.assertEqual(asyncio.run(build()), "AIOKafkaConsumer")
