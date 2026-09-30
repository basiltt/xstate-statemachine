# tests/contrib/brokers/test_base.py
"""#294: the shared adapter core (`contrib.brokers._base`) -- stdlib only,
so it runs in the default job: settle-once, local requeue to the head,
attempt stamping, the size cap before parsing, undecodable messages
dropped (never looped), health callbacks, both engines."""

from __future__ import annotations

import asyncio
import unittest
from collections import deque
from typing import Any, Deque, List, Tuple

from src.xstate_statemachine.contrib.brokers._base import (
    AsyncBroker,
    Raw,
    SyncBroker,
    ThreadedTransport,
)
from src.xstate_statemachine.eda import (
    BrokerAdapter,
    Envelope,
    SyncBrokerAdapter,
)

from ...eda.contract import AsyncBrokerContract


class MemTransport:
    """A blocking transport with native redelivery counts."""

    def __init__(self) -> None:
        self.q: Deque[Tuple[Any, int]] = deque()
        self.acked: List[Any] = []
        self.dropped: List[Any] = []
        self.fail = 0
        self.n = 0

    def send(self, topic: str, env: Envelope) -> None:
        if self.fail:
            self.fail -= 1
            raise ConnectionError("down")
        self.q.append((env.to_json(), 0))

    def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        if self.fail:
            self.fail -= 1
            raise ConnectionError("down")
        out = []
        while self.q:
            body, attempts = self.q.popleft()
            self.n += 1
            out.append(Raw(body, (self.n, body), attempts))
        return out

    def ack(self, native: Any) -> None:
        self.acked.append(native)

    def drop(self, native: Any) -> None:
        self.dropped.append(native)


def env(subject: str = "k", n: int = 1) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class TestAsyncBaseContract(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return AsyncBroker(ThreadedTransport(MemTransport()))


class TestSyncBase(unittest.TestCase):
    def test_protocols(self) -> None:
        self.assertIsInstance(SyncBroker(MemTransport()), SyncBrokerAdapter)
        self.assertIsInstance(
            AsyncBroker(ThreadedTransport(MemTransport())), BrokerAdapter
        )

    def test_requeue_goes_to_head_with_attempt_and_settles_once(self) -> None:
        t = MemTransport()
        b = SyncBroker(t)
        b.publish("t", env(n=1))
        b.publish("t", env(n=2))
        it = b.subscribe("t", timeout=0)
        first = next(it)
        b.nack(first, requeue=True)
        b.ack(first)  # no-op: already settled
        seen = []
        for d in b.subscribe("t", timeout=0):
            seen.append((d.envelope.data["n"], d.envelope.attempt))
            d.ack()
        self.assertEqual(seen, [(1, 1), (2, 0)])
        self.assertEqual(len(t.acked), 2)
        self.assertEqual(b.in_flight, 0)

    def test_nack_without_requeue_drops_natively(self) -> None:
        t = MemTransport()
        b = SyncBroker(t)
        b.publish("t", env())
        for d in b.subscribe("t", timeout=0):
            d.nack(False)
        self.assertEqual(len(t.dropped), 1)
        self.assertEqual(list(b.subscribe("t", timeout=0)), [])

    def test_native_redelivery_count_becomes_attempt(self) -> None:
        t = MemTransport()
        t.q.append((env().to_json(), 3))
        (d,) = list(SyncBroker(t).subscribe("t", timeout=0))
        self.assertEqual(d.envelope.attempt, 3)

    def test_undecodable_and_oversized_are_dropped_not_looped(self) -> None:
        t = MemTransport()
        bad: List[str] = []
        b = SyncBroker(
            t,
            max_bytes=2048,
            on_undecodable=lambda topic, raw, exc: bad.append(
                type(exc).__name__
            ),
        )
        t.q.append(("{not json", 0))
        t.q.append(("x" * 5000, 0))
        t.q.append((env().to_json(), 0))
        got = list(b.subscribe("t", timeout=0))
        self.assertEqual(len(got), 1)
        self.assertEqual(
            bad, ["EnvelopeCorruptError", "EnvelopeTooLargeError"]
        )
        self.assertEqual(len(t.dropped), 2)

    def test_default_undecodable_handler_logs(self) -> None:
        t = MemTransport()
        t.q.append(("[]", 0))
        with self.assertLogs(
            "src.xstate_statemachine.contrib.brokers._base", "WARNING"
        ):
            self.assertEqual(list(SyncBroker(t).subscribe("t", timeout=0)), [])

    def test_health_callbacks_fire_once_per_transition(self) -> None:
        t = MemTransport()
        events: List[str] = []
        b = SyncBroker(
            t,
            on_disconnect=lambda exc: events.append("down"),
            on_reconnect=lambda: events.append("up"),
        )
        t.fail = 2
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                b.publish("t", env())
        self.assertFalse(b.healthy)
        b.publish("t", env())
        self.assertTrue(b.healthy)
        self.assertEqual(events, ["down", "up"])

    def test_publish_needs_an_envelope(self) -> None:
        with self.assertRaises(TypeError):
            SyncBroker(MemTransport()).publish("t", {"x": 1})  # type: ignore
        with self.assertRaises(TypeError):
            asyncio.run(
                AsyncBroker(ThreadedTransport(MemTransport())).publish(
                    "t", "x"  # type: ignore[arg-type]
                )
            )

    def test_delivery_callables_settle(self) -> None:
        t = MemTransport()
        b = SyncBroker(t)
        b.publish("t", env())
        (d,) = list(b.subscribe("t", timeout=0))
        self.assertEqual(b.in_flight, 1)
        d.ack()
        self.assertEqual(b.in_flight, 0)
        self.assertEqual(b.held("t"), 0)

    def test_close_delegates(self) -> None:
        class C(MemTransport):
            closed = False

            def close(self) -> None:
                self.closed = True

        t = C()
        SyncBroker(t).close()
        self.assertTrue(t.closed)
        t2 = C()
        asyncio.run(AsyncBroker(ThreadedTransport(t2)).close())
        self.assertTrue(t2.closed)


class TestAsyncBase(unittest.TestCase):
    def test_async_nack_drop_and_health(self) -> None:
        t = MemTransport()
        ups: List[str] = []
        b = AsyncBroker(
            ThreadedTransport(t),
            on_disconnect=lambda e: ups.append("down"),
            on_reconnect=lambda: ups.append("up"),
        )

        async def go() -> None:
            await b.publish("t", env())
            async for d in b.subscribe("t", timeout=0):
                await d.nack(False)
            t.fail = 1
            with self.assertRaises(ConnectionError):
                async for _ in b.subscribe("t", timeout=0):
                    pass
            t.q.append(("nope", 0))
            async for _ in b.subscribe("t", timeout=0):
                pass

        asyncio.run(go())
        self.assertEqual(len(t.dropped), 2)
        self.assertEqual(ups, ["down", "up"])


if __name__ == "__main__":
    unittest.main()
