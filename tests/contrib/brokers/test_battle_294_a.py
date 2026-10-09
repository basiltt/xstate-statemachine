# tests/contrib/brokers/test_battle_294_a.py
"""Battle #294 (adversary A): the adapter core under hostile transports,
forged producers, raising user hooks and many threads. Stdlib only."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import threading
import tracemalloc
import unittest

import pytest
from typing import Any, List

from src.xstate_statemachine.contrib.brokers._base import (
    AsyncBroker,
    Raw,
    SyncBroker,
    ThreadedTransport,
)
from src.xstate_statemachine.eda import Envelope

from .test_base import MemTransport, env


class _Recorder:
    """A DeadLetterStore stand-in."""

    def __init__(self) -> None:
        self.records: List[Any] = []

    def put(self, record: Any) -> None:
        self.records.append(record)


def _patch_attempts(t: MemTransport, values: List[Any]) -> None:
    """Make the transport return *values* as the native attempts."""
    orig = t.fetch

    def fetch(topic: str, wait_s: float) -> List[Raw]:
        raws = orig(topic, wait_s)
        return [
            r._replace(attempts=values[i % len(values)])
            for i, r in enumerate(raws)
        ]

    t.fetch = fetch  # type: ignore[method-assign]


class TestAttempts(unittest.TestCase):
    def test_forged_wire_attempt_is_not_trusted(self) -> None:
        # 🔥 a producer stamping xsmattempt=10**9 would dead-letter a
        #    healthy message on its first transient failure
        t = MemTransport()
        b = SyncBroker(t)
        b.publish("t", env().with_attempt(10**9))
        got = [d.envelope.attempt for d in b.subscribe("t", timeout=0.05)]
        self.assertEqual(got, [0])

    def test_native_count_wins_and_local_requeue_is_monotonic(self) -> None:
        t = MemTransport()
        _patch_attempts(t, [3])
        b = SyncBroker(t)
        b.publish("t", env())
        seen = []
        for d in b.subscribe("t", timeout=0.05):
            seen.append(d.envelope.attempt)
            if len(seen) < 3:
                d.nack(requeue=True)
            else:
                d.ack()
        self.assertEqual(seen, [3, 4, 5])

    def test_hostile_native_attempts_never_strand_a_batch(self) -> None:
        # 🔥 None / str / negative attempts raised TypeError mid-decode:
        #    the whole fetched batch was lost (un-acked, never delivered)
        t = MemTransport()
        _patch_attempts(t, [None, "x", -5, 2, True])
        b = SyncBroker(t)
        for n in range(5):
            b.publish("t", env(n=n))
        got = []
        for d in b.subscribe("t", timeout=0.05):
            got.append(d.envelope.attempt)
            d.ack()
        self.assertEqual(got, [0, 0, 0, 2, 1])


class TestRaisingHooks(unittest.TestCase):
    def test_raising_on_reconnect_does_not_lose_the_batch(self) -> None:
        def boom() -> None:
            raise RuntimeError("hook")

        t = MemTransport()
        b = SyncBroker(t, on_reconnect=boom)
        b.publish("t", env())
        t.fail = 1
        with self.assertRaises(ConnectionError):
            list(b.subscribe("t", timeout=0.05))
        with self.assertLogs(
            "src.xstate_statemachine.contrib.brokers._base", logging.WARNING
        ):
            got = list(b.subscribe("t", timeout=0.05))
        self.assertEqual(len(got), 1)
        self.assertTrue(b.healthy)

    def test_raising_on_disconnect_keeps_the_transport_error(self) -> None:
        def boom(exc: Exception) -> None:
            raise RuntimeError("hook")

        t = MemTransport()
        b = SyncBroker(t, on_disconnect=boom)
        t.fail = 1
        with self.assertRaises(ConnectionError):
            b.publish("t", env())
        self.assertFalse(b.healthy)

    def test_raising_dead_letter_store_strands_nothing(self) -> None:
        class Broken:
            def put(self, record: Any) -> None:
                raise OSError("disk full")

        t = MemTransport()
        b = SyncBroker(t, dead_letters=Broken())
        t.q.append(("{not json SECRET", 0))
        b.publish("t", env(n=1))
        got = [d.envelope.data["n"] for d in b.subscribe("t", timeout=0.05)]
        self.assertEqual(got, [1])
        self.assertEqual(len(t.dropped), 1)


class TestNoBodyLeak(unittest.TestCase):
    def test_dead_letter_and_logs_never_hold_the_body(self) -> None:
        dlq = _Recorder()
        t = MemTransport()
        b = SyncBroker(t, dead_letters=dlq)
        t.q.append((json.dumps({"x": "SECRET-TOKEN"}), 0))
        with self.assertLogs(
            "src.xstate_statemachine.contrib.brokers._base", logging.WARNING
        ) as logs:
            list(b.subscribe("t", timeout=0.05))
        self.assertNotIn("SECRET-TOKEN", repr(dlq.records[0]))
        self.assertNotIn("SECRET-TOKEN", "\n".join(logs.output))

    def test_io_failure_log_has_type_only(self) -> None:
        class Leaky(MemTransport):
            def send(self, topic: str, e: Envelope) -> None:
                raise ConnectionError("redis://u:hunter2@host")

        b = SyncBroker(Leaky())
        with self.assertLogs(
            "src.xstate_statemachine.contrib.brokers._base", logging.WARNING
        ) as logs:
            with self.assertRaises(ConnectionError):
                b.publish("t", env())
        self.assertNotIn("hunter2", "\n".join(logs.output))


class TestConcurrency(unittest.TestCase):
    def test_threads_publish_subscribe_nack_ack(self) -> None:
        class Locked(MemTransport):
            def __init__(self) -> None:
                super().__init__()
                self.lock = threading.Lock()

            def send(self, topic: str, e: Envelope) -> None:
                with self.lock:
                    super().send(topic, e)

            def fetch(self, topic: str, wait_s: float) -> List[Raw]:
                with self.lock:
                    return super().fetch(topic, wait_s)

        t = Locked()
        b = SyncBroker(t)
        seen: List[str] = []
        guard = threading.Lock()
        rng = random.Random(7)

        def produce() -> None:
            for n in range(500):
                b.publish("t", env(n=n))

        def consume() -> None:
            for d in b.subscribe("t", timeout=0.3):
                if rng.random() < 0.2:
                    d.nack(requeue=True)
                    continue
                with guard:
                    seen.append(d.envelope.id)
                d.ack()
                d.ack()  # settle-once under contention

        threads = [threading.Thread(target=produce) for _ in range(4)]
        threads += [threading.Thread(target=consume) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(30)
        self.assertEqual(len(seen), 2000)
        self.assertEqual(len(set(seen)), 2000)
        self.assertEqual((b.in_flight, b.held("t")), (0, 0))
        self.assertEqual(len(t.acked), 2000)

    def test_health_flaps_fire_one_callback_per_transition(self) -> None:
        events: List[str] = []
        b = SyncBroker(
            MemTransport(),
            on_disconnect=lambda e: events.append("down"),
            on_reconnect=lambda: events.append("up"),
        )

        def flap() -> None:
            for _ in range(200):
                b._io_failed(ConnectionError())
                b._io_ok()

        threads = [threading.Thread(target=flap) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(30)
        # 📝 one callback per real transition: ended healthy, so every
        #    "down" was matched by exactly one "up"
        self.assertEqual(events.count("down"), events.count("up"))
        self.assertGreater(len(events), 0)
        self.assertTrue(b.healthy)


class TestAsync(unittest.TestCase):
    def test_async_tasks_interleaved(self) -> None:
        async def main() -> int:
            b = AsyncBroker(ThreadedTransport(MemTransport()))
            for n in range(200):
                await b.publish("t", env(n=n))
            got: List[str] = []

            async def consume() -> None:
                async for d in b.subscribe("t", timeout=0.1):
                    got.append(d.envelope.id)
                    await d.ack()

            await asyncio.gather(*(consume() for _ in range(4)))
            self.assertEqual((b.in_flight, b.held("t")), (0, 0))
            return len(set(got))

        self.assertEqual(asyncio.run(main()), 200)

    def test_aclose_mid_stream_keeps_unsettled_redeliverable(self) -> None:
        async def main() -> None:
            t = MemTransport()
            b = AsyncBroker(ThreadedTransport(t))
            for n in range(3):
                await b.publish("t", env(n=n))
            gen = b.subscribe("t", timeout=0.1)
            first = await gen.__anext__()
            await gen.aclose()
            await first.ack()
            rest = [d async for d in b.subscribe("t", timeout=0.05)]
            self.assertEqual([d.envelope.data["n"] for d in rest], [1, 2])

        asyncio.run(main())


class TestKafkaPartition(unittest.TestCase):
    def test_out_of_order_ack_never_commits_past_a_gap(self) -> None:
        # 📝 the Kafka module needs aiokafka (CI core cells lack it);
        #    `require_extra` raises MissingExtraError, which is an
        #    ImportError -- but importorskip only catches ImportError
        #    raised while FINDING the module, so skip on it explicitly
        pytest.importorskip("aiokafka")
        from src.xstate_statemachine.contrib.brokers.kafka import _Partition

        p = _Partition()
        for off in range(5):
            p.track(off)
        p.settled.update({1, 2, 4})
        self.assertIsNone(p.commit_point())  # offset 0 unsettled
        p.settled.add(0)
        self.assertEqual(p.commit_point(), 3)  # 3 still open
        p.settled.add(3)
        self.assertEqual(p.commit_point(), 5)


class TestLeak(unittest.TestCase):
    def test_round_trips_do_not_grow(self) -> None:
        t = MemTransport()
        b = SyncBroker(t)

        def run(n: int) -> None:
            for i in range(n):
                b.publish("t", env(n=i))
            for d in b.subscribe("t", timeout=0.01):
                d.ack()
            t.acked.clear()

        import gc

        run(2000)
        tracemalloc.start()
        try:
            run(5000)
            gc.collect()
            mid = tracemalloc.get_traced_memory()[0]
            run(5000)
            gc.collect()
            end = tracemalloc.get_traced_memory()[0]
        finally:
            tracemalloc.stop()
        # 📝 N/2 vs N (HANDOVER §2.3): the second 5,000 round trips must
        #    not retain more than a bounded slice over the first (the
        #    local deque / inflight map are empty afterwards); a
        #    tracemalloc-vs-tracemalloc delta, not a ratio of totals
        #    (which CI's allocator noise made fail at 1.37x).
        self.assertLess(end - mid, 512 * 1024, (mid, end))
        self.assertEqual((b.in_flight, b.held("t")), (0, 0))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
