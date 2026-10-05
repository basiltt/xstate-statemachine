# tests/eda/test_battle_272_fake.py
"""Battle #272 (adversary A): the in-memory fakes against the real
adapters' semantics, failure injection, envelope isolation, threads,
both engines in parity, and bounded drains."""

from __future__ import annotations

import asyncio
import threading
import time
import unittest
from typing import Any, Callable, List

from src.xstate_statemachine.eda import (
    BrokerPublishError,
    Envelope,
    FakeBrokerAdapter,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.eda.envelope import (
    EnvelopeTooLargeError,
)
from src.xstate_statemachine.eda.fake import DEFAULT_DRAIN_LIMIT

from .contract import SyncBrokerContract


def env(subject: str = "k", n: int = 0, **kw: Any) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n}, **kw)


def run(broker: Any, coro_or_value: Any) -> Any:
    """Call through either engine: await a coroutine, pass a value."""
    if asyncio.iscoroutine(coro_or_value):
        return asyncio.run(coro_or_value)
    return coro_or_value


def take_all(broker: Any, topic: str, timeout: float = 0.02) -> List[Any]:
    if isinstance(broker, SyncFakeBrokerAdapter):
        return list(broker.subscribe(topic, timeout=timeout))

    async def go() -> List[Any]:
        return [d async for d in broker.subscribe(topic, timeout=timeout)]

    return asyncio.run(go())


ENGINES: List[Callable[[], Any]] = [FakeBrokerAdapter, SyncFakeBrokerAdapter]


class TestSyncFakeContract(SyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return SyncFakeBrokerAdapter()


class TestSyncFakeContractViaDeliver(SyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return SyncFakeBrokerAdapter()

    def inject(self, broker: Any, env: Envelope) -> None:
        broker.deliver(self.topic, env)


class TestParityAcrossEngines(unittest.TestCase):
    """Identical semantics; only delivery (await vs call) differs."""

    def test_requeue_stamps_attempt_like_real_adapters(self) -> None:
        for make in ENGINES:
            with self.subTest(engine=make.__name__):
                b = make()
                run(b, b.publish("t", env(n=1)))
                (d,) = take_all(b, "t")
                self.assertEqual(d.envelope.attempt, 0)
                run(b, b.nack(d, requeue=True))
                (d2,) = take_all(b, "t")
                self.assertEqual(d2.envelope.attempt, 1)
                self.assertEqual(d2.envelope.id, d.envelope.id)
                run(b, b.nack(d2, requeue=True))
                (d3,) = take_all(b, "t")
                self.assertEqual(d3.envelope.attempt, 2)

    def test_requeue_goes_to_head_of_line(self) -> None:
        for make in ENGINES:
            with self.subTest(engine=make.__name__):
                b = make()
                for n in range(3):
                    run(b, b.publish("t", env(n=n)))
                ds = take_all(b, "t")
                run(b, b.nack(ds[1], requeue=True))
                run(b, b.nack(ds[0], requeue=True))
                got = [d.envelope.data["n"] for d in take_all(b, "t")]
                self.assertEqual(got, [0, 1])

    def test_double_settle_and_unknown_delivery_are_noops(self) -> None:
        for make in ENGINES:
            with self.subTest(engine=make.__name__):
                b, other = make(), make()
                run(b, b.publish("t", env()))
                run(other, other.publish("t", env()))
                (d,) = take_all(b, "t")
                (od,) = take_all(other, "t")
                run(b, b.ack(d))
                run(b, b.nack(d, requeue=True))
                run(b, b.ack(od))  # another broker's delivery
                self.assertEqual((len(b.acked), len(b.nacked)), (1, 0))
                self.assertEqual(b.pending("t"), 0)
                self.assertEqual(other.in_flight, 1)

    def test_publish_and_deliver_records(self) -> None:
        for make in ENGINES:
            with self.subTest(engine=make.__name__):
                b = make()
                run(b, b.deliver("in", env()))
                run(b, b.publish("out", env()))
                self.assertEqual(len(b.published), 1)
                self.assertEqual(b.published_on("in"), [])
                self.assertEqual(b.topics(), ["in", "out"])

    def test_publish_to_unsubscribed_topic_is_buffered_and_clearable(
        self,
    ) -> None:
        for make in ENGINES:
            with self.subTest(engine=make.__name__):
                b = make()
                run(b, b.publish("nobody", env()))
                self.assertEqual(b.pending("nobody"), 1)
                b.fail_next_publish()
                b.on("nobody", lambda e: None)
                b.clear()
                self.assertEqual(
                    (b.pending("nobody"), b.published, b.topics()),
                    (0, [], []),
                )
                run(b, b.publish("x", env()))  # failure was cleared too
                self.assertEqual(b.drain(), 0)  # handler was cleared


class TestEnvelopeHandling(unittest.TestCase):
    def test_consumer_mutation_does_not_rewrite_published(self) -> None:
        b = SyncFakeBrokerAdapter()
        original = env(n=1)
        b.publish("t", original)
        (d,) = list(b.subscribe("t", timeout=0))
        d.envelope.data["n"] = 999
        self.assertEqual(b.published[0].data, {"n": 1})
        self.assertEqual(original.data, {"n": 1})

    def test_producer_mutation_after_publish_does_not_leak(self) -> None:
        b = SyncFakeBrokerAdapter()
        payload = {"n": 1}
        b.publish("t", Envelope.new(type="x", data=payload))
        payload["n"] = 2
        (d,) = list(b.subscribe("t", timeout=0))
        self.assertEqual(d.envelope.data, {"n": 1})

    def test_round_trip_is_equal(self) -> None:
        b = SyncFakeBrokerAdapter()
        e = env(correlationid="c", causationid="x", extensions={"zz": "1"})
        b.publish("t", e)
        (d,) = list(b.subscribe("t", timeout=0))
        self.assertEqual(d.envelope, e)

    def test_size_cap_enforced_on_publish_and_deliver(self) -> None:
        b = SyncFakeBrokerAdapter(max_bytes=512)
        big = Envelope.new(type="x", data={"blob": "a" * 1000})
        with self.assertRaises(EnvelopeTooLargeError):
            b.publish("t", big)
        with self.assertRaises(EnvelopeTooLargeError):
            b.deliver("t", big)
        self.assertEqual((b.published, b.pending("t")), ([], 0))

    def test_non_json_payload_becomes_str_like_a_real_wire(self) -> None:
        b = SyncFakeBrokerAdapter()
        b.publish("t", Envelope.new(type="x", data={"o": object(), "t": (1,)}))
        (d,) = list(b.subscribe("t", timeout=0))
        self.assertIsInstance(d.envelope.data["o"], str)
        self.assertEqual(d.envelope.data["t"], [1])

    def test_mutation_before_nack_does_not_change_redelivery(self) -> None:
        b = SyncFakeBrokerAdapter()
        b.publish("t", env(n=1))
        (d,) = list(b.subscribe("t", timeout=0))
        d.envelope.data["n"] = 999
        b.nack(d, requeue=True)
        (d2,) = list(b.subscribe("t", timeout=0))
        self.assertEqual(d2.envelope.data, {"n": 1})

    def test_non_envelope_refused_on_deliver(self) -> None:
        with self.assertRaises(TypeError):
            SyncFakeBrokerAdapter().deliver("t", {"type": "x"})  # type: ignore[arg-type]

    def test_ids_monotonic_across_threads(self) -> None:
        ids: List[List[str]] = [[] for _ in range(8)]

        def mint(i: int) -> None:
            for _ in range(500):
                ids[i].append(Envelope.new(type="x").id)

        ts = [threading.Thread(target=mint, args=(i,)) for i in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        flat = [x for per in ids for x in per]
        self.assertEqual(len(set(flat)), len(flat))
        for per in ids:
            self.assertEqual(per, sorted(per))


class TestFailureInjection(unittest.TestCase):
    def test_consumed_exactly_n_in_order_across_topics(self) -> None:
        b = SyncFakeBrokerAdapter()
        b.fail_next_publish(ValueError("a"), times=2)
        b.fail_next_publish(KeyError("b"))
        outcomes = []
        for topic in ("x", "y", "z", "x"):
            try:
                b.publish(topic, env())
                outcomes.append("ok")
            except Exception as exc:
                outcomes.append(type(exc).__name__)
        self.assertEqual(
            outcomes, ["ValueError", "ValueError", "KeyError", "ok"]
        )
        self.assertEqual([t for t in b.topics()], ["x"])

    def test_default_error_is_a_connection_error(self) -> None:
        b = FakeBrokerAdapter()
        b.fail_next_publish()
        with self.assertRaises(ConnectionError):
            asyncio.run(b.publish("t", env()))
        with self.assertRaises(BrokerPublishError):
            b.fail_next_publish()
            asyncio.run(b.publish("t", env()))

    def test_refuses_base_exceptions_and_bad_times(self) -> None:
        b = SyncFakeBrokerAdapter()
        for bad in (KeyboardInterrupt(), SystemExit(1), GeneratorExit()):
            with self.assertRaises(TypeError):
                b.fail_next_publish(bad)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            b.fail_next_publish(ValueError)  # type: ignore[arg-type]
        for times in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                b.fail_next_publish(times=times)  # type: ignore[arg-type]
        b.publish("t", env())  # nothing was queued by the refusals
        self.assertEqual(len(b.published), 1)

    def test_injection_while_publishers_run(self) -> None:
        b = SyncFakeBrokerAdapter()
        failed = []
        lock = threading.Lock()

        def pub() -> None:
            for _ in range(200):
                try:
                    b.publish("t", env())
                except BrokerPublishError:
                    with lock:
                        failed.append(1)

        ts = [threading.Thread(target=pub) for _ in range(8)]
        for t in ts:
            t.start()
        for _ in range(50):
            b.fail_next_publish()
        for t in ts:
            t.join()
        pending_failures = len(b._fail)
        self.assertEqual(len(failed) + pending_failures, 50)
        self.assertEqual(len(b.published), 1600 - len(failed))


class TestDrain(unittest.TestCase):
    def test_self_feeding_handler_is_bounded(self) -> None:
        b = SyncFakeBrokerAdapter()
        b.on("t", lambda e: b.publish("t", env()))
        b.publish("t", env())
        with self.assertRaises(RuntimeError):
            b.drain(limit=50)
        self.assertEqual(len(b.acked), 50)
        self.assertGreater(DEFAULT_DRAIN_LIMIT, 1000)

    def test_drain_topic_scope(self) -> None:
        b = SyncFakeBrokerAdapter()
        seen: List[str] = []
        b.on("a", lambda e: (seen.append("a"), b.publish("b", env())))
        b.on("b", lambda e: seen.append("b"))
        b.deliver("a", env())
        b.deliver("b", env())
        self.assertEqual(b.drain("a"), 1)
        self.assertEqual((seen, b.pending("b")), (["a"], 2))
        self.assertEqual(b.drain(), 2)

    def test_keyboard_interrupt_in_handler_releases_and_propagates(
        self,
    ) -> None:
        # 📝 independent review (H2): a runner teardown is not a handler
        #    failure -- the envelope goes back untouched, nothing counted.
        b = SyncFakeBrokerAdapter()

        def stop(e: Envelope) -> None:
            raise KeyboardInterrupt

        b.on("t", stop)
        b.deliver("t", env())
        with self.assertRaises(KeyboardInterrupt):
            b.drain()
        self.assertEqual(
            (len(b.nacked), b.in_flight, b.pending("t")), (0, 0, 1)
        )


class TestSubscribe(unittest.TestCase):
    def test_timeout_is_idle_time_not_total(self) -> None:
        """A producer that keeps feeding at < timeout intervals keeps the
        consumer alive (the real adapters' contract)."""
        b = SyncFakeBrokerAdapter()

        def produce() -> None:
            for n in range(6):
                time.sleep(0.03)
                b.publish("t", env(n=n))

        t = threading.Thread(target=produce)
        t.start()
        got = []
        for d in b.subscribe("t", timeout=0.15):
            got.append(d.envelope.data["n"])
            b.ack(d)
        t.join()
        self.assertEqual(got, list(range(6)))

    def test_timeout_zero_ends_on_empty(self) -> None:
        b = SyncFakeBrokerAdapter()
        self.assertEqual(list(b.subscribe("t", timeout=0)), [])

    def test_unsettled_delivery_stays_in_flight(self) -> None:
        b = SyncFakeBrokerAdapter()
        b.publish("t", env())
        list(b.subscribe("t", timeout=0))
        self.assertEqual((b.in_flight, b.pending("t")), (1, 0))


class TestThreads(unittest.TestCase):
    def test_32_publishers_one_drainer(self) -> None:
        b = SyncFakeBrokerAdapter()
        seen: List[int] = []
        b.on("t", lambda e: seen.append(e.data["n"]))
        done = threading.Event()

        def pub(i: int) -> None:
            for k in range(100):
                b.publish("t", env(subject=f"s{i}", n=i * 1000 + k))

        def drainer() -> None:
            while not done.is_set() or b.pending("t"):
                b.drain("t")
                time.sleep(0.001)

        d = threading.Thread(target=drainer)
        d.start()
        ts = [threading.Thread(target=pub, args=(i,)) for i in range(32)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        done.set()
        d.join()
        self.assertEqual(len(seen), 3200)
        for i in range(32):
            per = [n for n in seen if n // 1000 == i]
            self.assertEqual(per, sorted(per))
        self.assertEqual((b.in_flight, len(b.acked)), (0, 3200))

    def test_async_publishers_and_consumer_one_loop(self) -> None:
        b = FakeBrokerAdapter()

        async def go() -> List[int]:
            async def pub(i: int) -> None:
                for k in range(50):
                    await b.publish("t", env(subject=f"s{i}", n=i * 100 + k))
                    await asyncio.sleep(0)

            got: List[int] = []

            async def consume() -> None:
                async for d in b.subscribe("t", timeout=0.1):
                    got.append(d.envelope.data["n"])
                    await b.ack(d)

            await asyncio.gather(consume(), *(pub(i) for i in range(16)))
            return got

        got = asyncio.run(go())
        self.assertEqual(len(got), 800)
        for i in range(16):
            per = [n for n in got if n // 100 == i]
            self.assertEqual(per, sorted(per))

    def test_sync_producer_thread_async_consumer(self) -> None:
        b = FakeBrokerAdapter()

        async def go() -> int:
            loop = asyncio.get_running_loop()

            def produce() -> None:
                for n in range(200):
                    asyncio.run_coroutine_threadsafe(
                        b.publish("t", env(n=n)), loop
                    ).result()

            prod = asyncio.ensure_future(asyncio.to_thread(produce))
            got = []
            async for d in b.subscribe("t", timeout=0.2):
                got.append(d.envelope.data["n"])
                await b.ack(d)
            await prod
            self.assertEqual(got, list(range(200)))
            return b.in_flight

        self.assertEqual(asyncio.run(go()), 0)


class TestScale(unittest.TestCase):
    def test_20k_settles_leave_nothing_in_flight(self) -> None:
        b = SyncFakeBrokerAdapter()
        e = env()
        for _ in range(20_000):
            b.deliver("t", e)
        t0 = time.perf_counter()
        for d in b.subscribe("t", timeout=0):
            b.ack(d)
        self.assertLess(time.perf_counter() - t0, 10)
        self.assertEqual((b.in_flight, len(b.acked)), (0, 20_000))
        self.assertFalse(hasattr(b, "_settled"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
