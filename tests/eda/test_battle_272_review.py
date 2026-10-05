# tests/eda/test_battle_272_review.py
"""#272 independent review: `drain(limit=)` edge semantics, BaseException
inside a handler, cancelled `subscribe` loops, `_read_all` paging."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, List

from src.xstate_statemachine.eda import Envelope
from src.xstate_statemachine.eda.fake import (
    FakeBrokerAdapter,
    SyncFakeBrokerAdapter,
)


def env(subject: str = "k", n: int = 0) -> Envelope:
    return Envelope.new(type="x.y", subject=subject, data={"n": n})


class TestDrainLimit(unittest.TestCase):
    def test_exactly_limit_envelopes_drain_without_raising(self) -> None:
        # H1: the old top-of-pass check raised AFTER a completed drain
        b = SyncFakeBrokerAdapter()
        b.on("t", lambda e: None)
        for n in range(5):
            b.deliver("t", env(n=n))
        self.assertEqual(b.drain("t", limit=5), 5)
        self.assertEqual(b.pending("t"), 0)

    def test_one_over_limit_raises_without_overshoot(self) -> None:
        b = SyncFakeBrokerAdapter()
        handled: List[int] = []
        b.on("t", lambda e: handled.append(e.data["n"]))
        for n in range(6):
            b.deliver("t", env(n=n))
        with self.assertRaises(RuntimeError):
            b.drain("t", limit=5)
        self.assertEqual(len(handled), 5)  # never more than `limit`
        self.assertEqual(b.pending("t"), 1)

    def test_two_handlers_do_not_overshoot(self) -> None:
        b = SyncFakeBrokerAdapter()
        handled: List[str] = []
        b.on("a", lambda e: handled.append("a"))
        b.on("b", lambda e: handled.append("b"))
        for _ in range(3):
            b.deliver("a", env())
            b.deliver("b", env())
        with self.assertRaises(RuntimeError):
            b.drain(limit=3)
        self.assertEqual(len(handled), 3)

    def test_limit_validated(self) -> None:
        b = SyncFakeBrokerAdapter()
        for bad in (0, -1, 1.5, True, "3"):
            with self.assertRaises(ValueError):
                b.drain(limit=bad)  # type: ignore[arg-type]


class TestHandlerBaseException(unittest.TestCase):
    def test_exception_nacks_without_requeue(self) -> None:
        b = SyncFakeBrokerAdapter()

        def boom(e: Envelope) -> None:
            raise ValueError("x")

        b.on("t", boom)
        b.deliver("t", env())
        with self.assertRaises(ValueError):
            b.drain("t")
        self.assertEqual((b.pending("t"), len(b.nacked)), (0, 1))

    def test_keyboard_interrupt_requeues_untouched(self) -> None:
        # H2: a runner teardown is not a handler failure
        b = SyncFakeBrokerAdapter()

        def boom(e: Envelope) -> None:
            raise KeyboardInterrupt()

        b.on("t", boom)
        b.deliver("t", env())
        with self.assertRaises(KeyboardInterrupt):
            b.drain("t")
        self.assertEqual(b.pending("t"), 1)
        self.assertEqual(b.nacked, [])
        self.assertEqual(b.in_flight, 0)
        [d] = list(b.subscribe("t", timeout=0))
        self.assertEqual(d.envelope.attempt, 0)


class TestSubscribeAbandonedDelivery(unittest.TestCase):
    """M4: as on a real broker, an unsettled delivery survives the end of
    the consumer loop -- it is in flight until settled (never silently
    requeued, never lost)."""

    def test_sync_break_leaves_delivery_in_flight_and_settleable(
        self,
    ) -> None:
        b = SyncFakeBrokerAdapter()
        b.deliver("t", env(n=1))
        b.deliver("t", env(n=2))
        kept = None
        for d in b.subscribe("t", timeout=0):
            kept = d
            break  # unsettled
        self.assertEqual((b.pending("t"), b.in_flight), (1, 1))
        assert kept is not None
        b.nack(kept, requeue=True)  # the handle is still valid
        self.assertEqual((b.pending("t"), b.in_flight), (2, 0))
        got = [
            (d.envelope.data["n"], d.envelope.attempt)
            for d in b.subscribe("t", timeout=0)
        ]
        self.assertEqual(got, [(1, 1), (2, 0)])

    def test_async_cancel_leaves_delivery_in_flight(self) -> None:
        b = FakeBrokerAdapter()

        async def go() -> Any:
            await b.deliver("t", env(n=1))
            started = asyncio.Event()
            box: List[Any] = []

            async def consume() -> None:
                async for d in b.subscribe("t"):
                    box.append(d)
                    started.set()
                    await asyncio.sleep(60)  # never settles

            task = asyncio.ensure_future(consume())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)
            before = (b.pending("t"), b.in_flight)
            await b.ack(box[0])
            return before, (b.pending("t"), b.in_flight, len(b.acked))

        self.assertEqual(asyncio.run(go()), ((0, 1), (0, 0, 1)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
