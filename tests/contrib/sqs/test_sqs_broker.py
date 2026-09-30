# tests/contrib/sqs/test_sqs_broker.py
"""#294: `SqsBroker` / `SyncSqsBroker` -- `AsyncBrokerContract` against
moto (FIFO queue), plus SQS specifics: MessageGroupId = subject and
MessageDeduplicationId = envelope id on FIFO, DeleteMessage on
ack/drop, visibility-timeout redelivery carries
ApproximateReceiveCount as the attempt, `extend_visibility`, both
engines. Skipped when moto is not installed."""

from __future__ import annotations

import os
import unittest
import uuid
from typing import Any

import pytest

from src.xstate_statemachine.eda import (
    BrokerAdapter,
    Envelope,
    SyncBrokerAdapter,
)

from ...eda.contract import AsyncBrokerContract
from ..conftest import requires_extra

pytestmark = requires_extra("sqs")
moto = pytest.importorskip("moto")


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class _Moto:
    fifo = True

    def setUp(self) -> None:
        import boto3

        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        self.mock = moto.mock_aws()
        self.mock.start()
        self.client = boto3.client("sqs", region_name="us-east-1")
        name = f"q{uuid.uuid4().hex[:8]}" + (".fifo" if self.fifo else "")
        attrs = {"FifoQueue": "true"} if self.fifo else {}
        self.client.create_queue(QueueName=name, Attributes=attrs)
        self.topic = name

    def tearDown(self) -> None:
        self.mock.stop()

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.sqs import SqsBroker

        return SqsBroker(self.client)

    def sync(self, **kw: Any) -> Any:
        from src.xstate_statemachine.contrib.brokers.sqs import SyncSqsBroker

        return SyncSqsBroker(self.client, **kw)


class TestSqsStandardContract(_Moto, AsyncBrokerContract, unittest.TestCase):
    """The unmodified contract (moto keeps a standard queue in order;
    real SQS standard queues do NOT -- use FIFO for ordered charts)."""

    fifo = False


class TestSqsFifoContract(_Moto, AsyncBrokerContract, unittest.TestCase):
    """FIFO: SQS will not hand out more messages of a group while one is
    in flight, so the order test settles as it drains (real semantics)."""

    def test_per_subject_order_is_preserved(self) -> None:
        import asyncio

        broker = self.make_broker()

        async def go() -> list:
            for n in range(20):
                await broker.publish(self.topic, _env(f"s{n % 3}", n))
            got = []
            for _ in range(50):
                batch = [
                    d async for d in broker.subscribe(self.topic, timeout=0)
                ]
                for d in batch:
                    got.append(d.envelope)
                    await broker.ack(d)
                if len(got) == 20:
                    break
            return got

        got = asyncio.run(go())
        for s in ("s0", "s1", "s2"):
            ns = [e.data["n"] for e in got if e.subject == s]
            self.assertEqual(ns, sorted(ns))
        self.assertEqual(len(got), 20)


class TestSqsSpecific(_Moto, unittest.TestCase):
    def test_protocols_and_repr(self) -> None:
        self.assertIsInstance(self.sync(), SyncBrokerAdapter)
        self.assertIsInstance(self.make_broker(), BrokerAdapter)
        self.assertEqual(repr(self.sync()), "SyncSqsBroker()")
        self.assertEqual(repr(self.make_broker()), "SqsBroker()")

    def test_fifo_group_and_dedup_ids(self) -> None:
        sent: list = []
        b = self.sync()
        real = b.sqs.client.send_message

        def spy(**kw: Any) -> Any:
            sent.append(kw)
            return real(**kw)

        b.sqs.client.send_message = spy  # type: ignore[method-assign]
        env = _env("o-1", 1)
        b.publish(self.topic, env)
        b.publish(self.topic, env)  # same id: SQS drops it
        self.assertEqual(sent[0]["MessageGroupId"], "o-1")
        self.assertEqual(sent[0]["MessageDeduplicationId"], env.id)
        got = list(b.subscribe(self.topic, timeout=0))
        self.assertEqual(len(got), 1)

    def test_visibility_timeout_redelivery_counts_attempts(self) -> None:
        b = self.sync(visibility_timeout_s=0)
        b.publish(self.topic, _env("k", 1))
        (d,) = list(b.subscribe(self.topic, timeout=0))
        self.assertEqual(d.envelope.attempt, 0)
        other = self.sync()  # the message became visible again
        (d2,) = list(other.subscribe(self.topic, timeout=0))
        self.assertEqual(d2.envelope.attempt, 1)
        other.ack(d2)
        self.assertEqual(
            list(self.sync().subscribe(self.topic, timeout=0)), []
        )

    def test_extend_visibility(self) -> None:
        b = self.sync(visibility_timeout_s=0)
        b.publish(self.topic, _env("k", 1))
        (d,) = list(b.subscribe(self.topic, timeout=0))
        b.extend_visibility(d, 60)
        self.assertEqual(
            list(self.sync().subscribe(self.topic, timeout=0)), []
        )
        b.extend_visibility(object(), 60)  # unknown delivery: ignored

    def test_default_client_from_region(self) -> None:
        from src.xstate_statemachine.contrib.brokers.sqs import SqsBroker

        b = SqsBroker(region_name="us-east-1")
        self.assertEqual(b.sqs.client.meta.region_name, "us-east-1")


class TestSqsStandard(_Moto, unittest.TestCase):
    fifo = False

    def test_standard_queue_has_no_group_id(self) -> None:
        b = self.sync()
        b.publish(self.topic, _env("k", 1))
        (d,) = list(b.subscribe(self.topic, timeout=0))
        b.nack(d, requeue=False)
        self.assertEqual(list(b.subscribe(self.topic, timeout=0)), [])
