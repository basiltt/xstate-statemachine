# tests/contrib/rabbitmq/test_rabbitmq_broker.py
"""#294: `RabbitMQBroker` -- `AsyncBrokerContract` over an in-memory
aio-pika channel stand-in, plus AMQP specifics: persistent CloudEvents
message with ``message_id``, reject-without-requeue on drop, a lost
channel returns un-acked messages as ``redelivered`` (attempt >= 1),
``x-delivery-count`` from quorum queues, exchange routing = subject."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, List

from src.xstate_statemachine.eda import BrokerAdapter, Envelope

from ...eda.contract import AsyncBrokerContract
from ..brokers.fakes import FakeAmqpBroker
from ..conftest import requires_extra

pytestmark = requires_extra("rabbitmq")


def _broker(channel: Any, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.brokers.rabbitmq import (
        RabbitMQBroker,
    )

    return RabbitMQBroker(channel=channel, **kw)


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class TestRabbitContract(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return _broker(FakeAmqpBroker().channel())


class TestRabbitSpecific(unittest.TestCase):
    def test_protocol_repr_and_url_required(self) -> None:
        b = _broker(FakeAmqpBroker().channel())
        self.assertIsInstance(b, BrokerAdapter)
        self.assertNotIn("amqp", repr(b))
        from src.xstate_statemachine.contrib.brokers.rabbitmq import (
            RabbitMQBroker,
        )

        with self.assertRaises(ValueError):
            RabbitMQBroker()

    def test_message_is_persistent_cloudevents(self) -> None:
        amqp = FakeAmqpBroker()
        env = _env("o-1", 1)
        asyncio.run(_broker(amqp.channel()).publish("orders", env))
        ((message, _),) = amqp.queues["orders"]
        self.assertEqual(message.message_id, env.id)
        self.assertEqual(message.type, env.type)
        self.assertIn("cloudevents", message.content_type)
        self.assertEqual(int(message.delivery_mode), 2)

    def test_lost_channel_redelivers_with_attempt(self) -> None:
        amqp = FakeAmqpBroker()
        chan = amqp.channel()

        async def go() -> List[int]:
            await _broker(chan).publish("t", _env("k", 1))
            got = [d async for d in _broker(chan).subscribe("t", timeout=0)]
            self.assertEqual(len(got), 1)
            chan.close()  # consumer died before acking
            again = [d async for d in _broker(chan).subscribe("t", timeout=0)]
            return [d.envelope.attempt for d in again]

        self.assertEqual(asyncio.run(go()), [1])

    def test_delivery_count_header_wins(self) -> None:
        from src.xstate_statemachine.contrib.brokers.rabbitmq import _attempts
        from types import SimpleNamespace

        self.assertEqual(
            _attempts(
                SimpleNamespace(
                    headers={"x-delivery-count": 4}, redelivered=True
                )
            ),
            4,
        )
        self.assertEqual(
            _attempts(SimpleNamespace(headers=None, redelivered=False)), 0
        )

    def test_exchange_routes_by_subject(self) -> None:
        published: List[Any] = []

        class Ex:
            async def publish(self, message: Any, routing_key: str) -> None:
                published.append(routing_key)

        class Chan:
            async def get_exchange(self, name: str) -> Any:
                return Ex()

        b = _broker(Chan(), exchange="orders-hash")
        asyncio.run(b.publish("orders", _env("o-7", 1)))
        self.assertEqual(published, ["o-7"])
