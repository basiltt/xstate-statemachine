# tests/eda/test_fake_broker.py
"""#272: `FakeBrokerAdapter` satisfies the `BrokerAdapter` contract (the
same suite #294's adapters run), plus its test affordances; the sync
twin; and an inbound → machine → outbound round trip with NO real broker
asserting causation ids."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, List

from src.xstate_statemachine import (
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.eda import (
    BrokerAdapter,
    BrokerPublishError,
    Envelope,
    FakeBrokerAdapter,
    SyncBrokerAdapter,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.eda.broker import settle_awaitable

from .contract import AsyncBrokerContract


class TestFakeContract(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return FakeBrokerAdapter()


class TestFakeContractViaDeliver(AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        return FakeBrokerAdapter()

    def inject(self, broker: Any, env: Envelope) -> Any:
        return broker.deliver(self.topic, env)


class TestProtocols(unittest.TestCase):
    def test_runtime_checkable(self) -> None:
        self.assertIsInstance(FakeBrokerAdapter(), BrokerAdapter)
        self.assertIsInstance(SyncFakeBrokerAdapter(), SyncBrokerAdapter)


class TestAffordances(unittest.TestCase):
    def test_published_and_deliver_are_distinct(self) -> None:
        b = FakeBrokerAdapter()

        async def go() -> None:
            await b.deliver("in", Envelope.new(type="a"))
            await b.publish("out", Envelope.new(type="b"))

        asyncio.run(go())
        self.assertEqual([e.type for e in b.published], ["b"])
        self.assertEqual([e.type for e in b.published_on("out")], ["b"])
        self.assertEqual(b.published_on("in"), [])
        self.assertEqual((b.pending("in"), b.pending("out")), (1, 1))
        self.assertEqual(b.topics(), ["in", "out"])

    def test_failure_injection(self) -> None:
        b = FakeBrokerAdapter()
        b.fail_next_publish(times=2)

        async def attempt() -> bool:
            try:
                await b.publish("t", Envelope.new(type="x"))
                return True
            except BrokerPublishError:
                return False

        results = [asyncio.run(attempt()) for _ in range(3)]
        self.assertEqual(results, [False, False, True])
        self.assertEqual(len(b.published), 1)
        b.fail_next_publish(ValueError("custom"))
        with self.assertRaises(ValueError):
            asyncio.run(b.publish("t", Envelope.new(type="x")))

    def test_publish_requires_an_envelope(self) -> None:
        with self.assertRaises(TypeError):
            SyncFakeBrokerAdapter().publish("t", {"type": "x"})  # type: ignore[arg-type]

    def test_drain_runs_handlers_and_their_output(self) -> None:
        b = SyncFakeBrokerAdapter()
        seen: List[str] = []

        def a(env: Envelope) -> None:
            seen.append(env.type)
            b.publish("b", Envelope.new(type="from-a"))

        b.on("a", a)
        b.on("b", lambda env: seen.append(env.type))
        b.deliver("a", Envelope.new(type="first"))
        self.assertEqual(b.drain(), 2)
        self.assertEqual(seen, ["first", "from-a"])
        self.assertEqual(len(b.acked), 2)

    def test_drain_raising_handler_nacks_and_propagates(self) -> None:
        b = SyncFakeBrokerAdapter()

        def boom(env: Envelope) -> None:
            raise RuntimeError("x")

        b.on("t", boom)
        b.deliver("t", Envelope.new(type="t"))
        with self.assertRaises(RuntimeError):
            b.drain("t")
        self.assertEqual(len(b.nacked), 1)
        self.assertEqual(b.pending("t"), 0)
        self.assertEqual(b.in_flight, 0)

    def test_sync_subscribe_contract(self) -> None:
        b = SyncFakeBrokerAdapter()
        for n in range(3):
            b.publish("t", Envelope.new(type="t", subject="k", data={"n": n}))
        first = next(iter(b.subscribe("t", timeout=0)))
        b.nack(first, requeue=True)
        got = []
        for d in b.subscribe("t", timeout=0.02):
            got.append(d.envelope.data["n"])
            b.ack(d)
        self.assertEqual(got, [0, 1, 2])
        # settle callables on the delivery itself
        b.publish("t", Envelope.new(type="t"))
        d = next(iter(b.subscribe("t", timeout=0)))
        d.nack(False)
        self.assertEqual(b.pending("t"), 0)
        b.publish("t", Envelope.new(type="t"))
        d = next(iter(b.subscribe("t", timeout=0)))
        d.ack()
        self.assertEqual(b.in_flight, 0)


class TestSettleAwaitable(unittest.TestCase):
    def test_modes(self) -> None:
        hits: List[str] = []

        async def co(tag: str) -> None:
            hits.append(tag)

        settle_awaitable(None)
        settle_awaitable(co("no-loop"))

        async def inside() -> None:
            tasks: List[Any] = []
            settle_awaitable(co("task"), tasks=tasks)
            await asyncio.gather(*tasks)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, lambda: settle_awaitable(co("thread"), loop=loop)
            )

        asyncio.run(inside())
        self.assertEqual(hits, ["no-loop", "task", "thread"])


class _Publisher(PluginBase):
    """A hand-rolled `on_transition` publisher (the issue's outbound half)."""

    def __init__(self, broker: SyncFakeBrokerAdapter) -> None:
        self.broker = broker
        self.cause: Any = None

    def on_transition(self, i: Any, frm: Any, to: Any, t: Any) -> None:
        if t is not None and t.event == "PAY":
            self.broker.publish(
                "out",
                Envelope.from_transition(
                    i, type="order.paid", cause=self.cause
                ),
            )


class TestRoundTripWithoutARealBroker(unittest.TestCase):
    def test_inbound_to_send_and_outbound_publisher(self) -> None:
        broker = SyncFakeBrokerAdapter()
        m = create_machine(
            {
                "id": "order",
                "initial": "open",
                "context": {"total": 0},
                "states": {
                    "open": {
                        "on": {"PAY": {"target": "paid", "actions": "add"}}
                    },
                    "paid": {},
                },
            },
            logic=MachineLogic(
                actions={
                    "add": lambda i, c, e, a: c.__setitem__(
                        "total", c["total"] + e.payload["amount"]
                    )
                }
            ),
        )
        pub = _Publisher(broker)
        interp = SyncInterpreter(m).use(pub).start()

        def inbound(env: Envelope) -> None:
            pub.cause = env
            interp.send(env.to_event())

        broker.on("in", inbound)
        cmd = Envelope.new(
            type="xsm.order.PAY",
            subject="o-1",
            data={"amount": 5},
            correlationid="corr-1",
        )
        broker.deliver("in", cmd)
        broker.drain("in")
        self.assertIn("order.paid", interp.current_state_ids)
        self.assertEqual(interp.context["total"], 5)
        [out] = broker.published_on("out")
        self.assertEqual(out.causationid, cmd.id)
        self.assertEqual(out.correlationid, "corr-1")
        self.assertEqual(out.subject, "o-1")
        interp.stop()


if __name__ == "__main__":
    unittest.main()
