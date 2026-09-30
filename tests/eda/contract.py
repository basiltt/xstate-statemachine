# tests/eda/contract.py
"""The `BrokerAdapter` contract suite (#272).

Every broker adapter -- the in-memory fakes here, and the real Kafka /
RabbitMQ / NATS / SQS / Redis Streams adapters of #294 -- subclasses
`AsyncBrokerContract` (or `SyncBrokerContract`) and implements
``make_broker()``. The contract is deliberately small: per-subject FIFO,
explicit ack / nack, requeue to the head, a failed publish raises.

Not collected on its own (no ``test_`` prefix): import the mixins.
"""

from __future__ import annotations

import asyncio
from typing import Any, List

from src.xstate_statemachine.eda import Envelope


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class AsyncBrokerContract:
    """Mixin for `unittest.TestCase`; override `make_broker`."""

    topic = "contract"

    def make_broker(self) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError

    def inject(self, broker: Any, env: Envelope) -> Any:
        """How the suite puts inbound traffic on the topic (publish by
        default; the fakes also accept `deliver`)."""
        return broker.publish(self.topic, env)

    def _drain(self, broker: Any) -> List[Any]:
        async def go() -> List[Any]:
            got = []
            async for d in broker.subscribe(self.topic, timeout=0.05):
                got.append(d)
            return got

        return asyncio.run(go())

    def test_per_subject_order_is_preserved(self) -> None:
        broker = self.make_broker()

        async def fill() -> None:
            for n in range(20):
                await self.inject(broker, _env(f"s{n % 3}", n))

        asyncio.run(fill())
        got = self._drain(broker)
        for s in ("s0", "s1", "s2"):
            ns = [d.envelope.data["n"] for d in got if d.envelope.subject == s]
            self.assertEqual(ns, sorted(ns))  # type: ignore[attr-defined]
        self.assertEqual(len(got), 20)  # type: ignore[attr-defined]

    def test_ack_removes_and_nack_requeue_redelivers_first(self) -> None:
        broker = self.make_broker()

        async def go() -> List[int]:
            await self.inject(broker, _env("k", 1))
            await self.inject(broker, _env("k", 2))
            first = None
            async for d in broker.subscribe(self.topic, timeout=0.05):
                first = d
                break
            assert first is not None
            await broker.nack(first, requeue=True)
            seen = []
            async for d in broker.subscribe(self.topic, timeout=0.05):
                seen.append(d.envelope.data["n"])
                await broker.ack(d)
            return seen

        self.assertEqual(asyncio.run(go()), [1, 2])  # type: ignore[attr-defined]

    def test_nack_without_requeue_drops(self) -> None:
        broker = self.make_broker()

        async def go() -> int:
            await self.inject(broker, _env("k", 1))
            async for d in broker.subscribe(self.topic, timeout=0.05):
                await broker.nack(d, requeue=False)
            left = 0
            async for _ in broker.subscribe(self.topic, timeout=0.05):
                left += 1
            return left

        self.assertEqual(asyncio.run(go()), 0)  # type: ignore[attr-defined]

    def test_settling_twice_is_a_noop(self) -> None:
        broker = self.make_broker()

        async def go() -> int:
            await self.inject(broker, _env("k", 1))
            async for d in broker.subscribe(self.topic, timeout=0.05):
                await broker.ack(d)
                await broker.nack(d, requeue=True)  # ignored
            left = 0
            async for _ in broker.subscribe(self.topic, timeout=0.05):
                left += 1
            return left

        self.assertEqual(asyncio.run(go()), 0)  # type: ignore[attr-defined]

    def test_envelope_round_trips_unchanged(self) -> None:
        broker = self.make_broker()
        env = Envelope.new(
            type="order.paid",
            subject="o-1",
            data={"total": 5},
            correlationid="c-1",
            causationid="x-1",
        )

        async def go() -> Envelope:
            await self.inject(broker, env)
            async for d in broker.subscribe(self.topic, timeout=0.05):
                await broker.ack(d)
                return d.envelope
            raise AssertionError("nothing delivered")

        self.assertEqual(asyncio.run(go()), env)  # type: ignore[attr-defined]
