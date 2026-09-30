# tests/contrib/nats/test_nats_broker.py
"""#294: `NatsBroker` -- `AsyncBrokerContract` over an in-memory JetStream
stand-in, plus NATS specifics: subject suffix = sanitised envelope subject,
``Nats-Msg-Id`` dedup of a re-published envelope, +TERM on drop, attempts
from ``num_delivered`` after ``ack_wait`` redelivery."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, List

from src.xstate_statemachine.eda import BrokerAdapter, Envelope

from ...eda.contract import AsyncBrokerContract
from ..brokers.fakes import FakeJetStream
from ..conftest import requires_extra

pytestmark = requires_extra("nats")


def _broker(js: Any, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.brokers.nats import NatsBroker

    return NatsBroker(js=js, **kw)


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class TestNatsContract(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return _broker(FakeJetStream())


class TestNatsSpecific(unittest.TestCase):
    def test_protocol_repr_and_args(self) -> None:
        b = _broker(FakeJetStream(), durable="orders")
        self.assertIsInstance(b, BrokerAdapter)
        self.assertEqual(repr(b), "NatsBroker(durable='orders')")
        from src.xstate_statemachine.contrib.brokers.nats import NatsBroker

        with self.assertRaises(ValueError):
            NatsBroker()

    def test_subject_token_is_sanitised(self) -> None:
        from src.xstate_statemachine.contrib.brokers.nats import (
            subject_token,
        )

        self.assertEqual(subject_token("a.b *>c d"), "a_b___c_d")
        self.assertEqual(subject_token(None), "_")
        js = FakeJetStream()
        asyncio.run(_broker(js).publish("orders", _env("o.1", 1)))
        self.assertEqual(js.streams["orders"][0][0], "orders.o_1")

    def test_republish_is_deduped_by_msg_id(self) -> None:
        js = FakeJetStream()
        env = _env("k", 1)

        async def go() -> None:
            b = _broker(js)
            await b.publish("t", env)
            await b.publish("t", env)

        asyncio.run(go())
        self.assertEqual(len(js.streams["t"]), 1)

    def test_ack_wait_redelivery_carries_attempts(self) -> None:
        js = FakeJetStream()

        async def go() -> List[int]:
            b = _broker(js)
            await b.publish("t", _env("k", 1))
            got = [d async for d in b.subscribe("t", timeout=0)]
            self.assertEqual(len(got), 1)
            js.consumers[("t", "xsm")].expire_ack_wait()
            fresh = _broker(js)  # another process after the crash
            return [
                d.envelope.attempt
                async for d in fresh.subscribe("t", timeout=0)
            ]

        self.assertEqual(asyncio.run(go()), [1])

    def test_attempts_of_a_plain_message(self) -> None:
        from src.xstate_statemachine.contrib.brokers.nats import _attempts

        self.assertEqual(_attempts(object()), 0)
