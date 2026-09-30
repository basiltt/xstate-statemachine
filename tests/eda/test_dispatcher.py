# tests/eda/test_dispatcher.py
"""#293: `InboundDispatcher` -- per-subject order, duplicates dropped, none
lost; poison → DLQ + ack after `max_attempts` (X0.8); unknown type /
corrupt envelope → DLQ, never raised into the loop; both consumer APIs."""

from __future__ import annotations

import asyncio
import random
import threading
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.eda import (
    ATTEMPT_EXTENSION,
    DispatchResult,
    Envelope,
    FakeBrokerAdapter,
    InboundDispatcher,
    MemoryDeadLetterStore,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
)

COUNTER = {
    "id": "counter",
    "initial": "on",
    "context": {"seen": []},
    "states": {"on": {"on": {"ADD": {"actions": "record"}}}},
}


def _counter(fail: Any = None) -> Any:
    def record(i: Any, c: Dict[str, Any], e: Any, a: Any) -> None:
        if fail is not None:
            fail(e)
        c["seen"] = list(c["seen"]) + [e.payload["n"]]

    return create_machine(
        COUNTER,
        logic=MachineLogic(actions={"record": record}),
    )


def _add(subject: str, n: int, **kw: Any) -> Envelope:
    return Envelope.new(
        type="xsm.counter.ADD", subject=subject, data={"n": n}, **kw
    )


class TestThousandEnvelopes(unittest.TestCase):
    """The #293 acceptance criterion."""

    def test_order_preserved_duplicates_dropped_none_lost(self) -> None:
        store, inbox = MemoryStore(), MemoryInbox()
        broker = FakeBrokerAdapter()
        m = _counter()
        disp = InboundDispatcher(
            store, {"xsm.counter.ADD": m}, inbox=inbox, max_in_flight=4
        )
        rng = random.Random(7)
        sent: List[Envelope] = []
        per: Dict[str, int] = {f"s{k}": 0 for k in range(10)}
        for _ in range(900):
            s = f"s{rng.randrange(10)}"
            sent.append(_add(s, per[s]))
            per[s] += 1
        # 100 redeliveries of already-sent envelopes (same id), later
        dups = [sent[rng.randrange(len(sent))] for _ in range(100)]

        async def go() -> DispatchResult:
            for e in sent + dups:
                await broker.deliver("in", e)
            return await disp.run_once(broker, "in")

        res = asyncio.run(go())
        self.assertEqual(res.processed, 900)
        self.assertEqual(res.duplicates, 100)
        self.assertEqual(res.dead_lettered + res.retried, 0)
        for s, n in per.items():
            rec = store.load(s)
            self.assertIsNotNone(rec, s)
            import json

            seen = json.loads(rec.snapshot)["context"]["seen"]
            self.assertEqual(seen, list(range(n)), s)  # order, none lost
        self.assertEqual(broker.pending("in") + broker.in_flight, 0)


class TestConcurrency(unittest.TestCase):
    def test_one_subject_at_a_time_up_to_max_in_flight(self) -> None:
        active: Dict[str, int] = {}
        peak = {"subject": 0, "total": 0}
        lock = threading.Lock()

        def slow(e: Any) -> None:
            pass

        m = _counter()
        disp = InboundDispatcher(MemoryStore(), lambda t: m, max_in_flight=3)
        real = disp.handle

        def spy(env: Envelope, *, topic: Any = None) -> Any:
            with lock:
                active[env.subject] = active.get(env.subject, 0) + 1
                peak["subject"] = max(peak["subject"], active[env.subject])
                peak["total"] = max(peak["total"], sum(active.values()))
            time.sleep(0.005)
            try:
                return real(env, topic=topic)
            finally:
                with lock:
                    active[env.subject] -= 1

        disp.handle = spy  # type: ignore[method-assign]
        broker = FakeBrokerAdapter()

        async def go() -> None:
            for n in range(40):
                await broker.deliver("in", _add(f"s{n % 8}", n))
            await disp.run_once(broker, "in")

        asyncio.run(go())
        self.assertEqual(peak["subject"], 1)
        self.assertLessEqual(peak["total"], 3)
        self.assertGreater(peak["total"], 1)

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            InboundDispatcher(MemoryStore(), {}, max_in_flight=0)
        with self.assertRaises(ValueError):
            InboundDispatcher(MemoryStore(), {}, max_attempts=0)
        with self.assertRaises(ValueError):
            InboundDispatcher(MemoryStore(), {}, on_unknown="drop")
        d = InboundDispatcher(MemoryStore(), {}, on_unknown="ignore")
        self.assertEqual(d.handle(_add("k", 1)).ignored, 1)


class TestPoison(unittest.TestCase):
    def test_transient_failure_retried_in_order_then_succeeds(self) -> None:
        calls = {"n": 0}

        def flaky(e: Any) -> None:
            if e.payload["n"] == 0:
                calls["n"] += 1
                if calls["n"] < 3:
                    raise RuntimeError("transient")

        m = _counter(flaky)
        # actions that raise are contained by the engine; make the
        # failure reach the dispatcher via the action error policy
        m = create_machine(
            dict(COUNTER, actionErrorPolicy="fail"),
            logic=MachineLogic(
                actions={
                    "record": lambda i, c, e, a: (
                        flaky(e),
                        c.__setitem__(
                            "seen", list(c["seen"]) + [e.payload["n"]]
                        ),
                    )
                }
            ),
        )
        store = MemoryStore()
        disp = InboundDispatcher(store, lambda t: m, max_attempts=5)
        broker = SyncFakeBrokerAdapter()
        for n in range(3):
            broker.deliver("in", _add("k", n))
        total = DispatchResult()
        for _ in range(5):
            total.add(disp.run_once_sync(broker, "in"))
        import json

        seen = json.loads(store.load("k").snapshot)["context"]["seen"]
        self.assertEqual(seen, [0, 1, 2])
        self.assertEqual(total.retried, 2)
        self.assertEqual(total.processed, 3)

    def test_poison_dead_lettered_and_acked_after_max_attempts(self) -> None:
        def always(e: Any) -> None:
            raise RuntimeError("poison")

        m = create_machine(
            dict(COUNTER, actionErrorPolicy="fail"),
            logic=MachineLogic(
                actions={"record": lambda i, c, e, a: always(e)}
            ),
        )
        dlq = MemoryDeadLetterStore()
        disp = InboundDispatcher(
            MemoryStore(), lambda t: m, max_attempts=3, dead_letters=dlq
        )
        broker = FakeBrokerAdapter()
        env = _add("k", 1, extensions={"password": "x"} and {})

        async def go() -> List[DispatchResult]:
            await broker.deliver("in", env)
            return [await disp.run_once(broker, "in") for _ in range(5)]

        rounds = asyncio.run(go())
        self.assertEqual([r.retried for r in rounds[:2]], [1, 1])
        self.assertEqual(rounds[2].dead_lettered, 1)
        self.assertEqual(sum(r.dead_lettered for r in rounds), 1)
        self.assertEqual(broker.pending("in") + broker.in_flight, 0)
        [rec] = dlq.list()
        self.assertEqual(
            (rec.id, rec.reason, rec.attempts), (env.id, "max_attempts", 3)
        )
        self.assertEqual(rec.topic, "in")
        self.assertEqual(rec.errors[0]["message"], "poison")
        self.assertEqual(rec.envelope["id"], env.id)
        self.assertTrue(rec.machine_hash)

    def test_attempt_extension_counts(self) -> None:
        m = create_machine(
            dict(COUNTER, actionErrorPolicy="fail"),
            logic=MachineLogic(actions={"record": lambda i, c, e, a: 1 / 0}),
        )
        dlq = MemoryDeadLetterStore()
        disp = InboundDispatcher(
            MemoryStore(), lambda t: m, max_attempts=3, dead_letters=dlq
        )
        res = disp.handle(_add("k", 1).with_attempt(2))
        self.assertEqual(res.dead_lettered, 1)
        self.assertEqual(dlq.list()[0].attempts, 3)
        self.assertEqual(disp.attempts_of(_add("k", 1)), 0)

    def test_unknown_type_and_corrupt_envelopes(self) -> None:
        dlq = MemoryDeadLetterStore()
        disp = InboundDispatcher(
            MemoryStore(), {"xsm.counter.ADD": _counter()}, dead_letters=dlq
        )
        r1 = disp.handle(
            Envelope.new(type="nope", subject="k", data={"password": "p"}),
            topic="in",
        )
        r2 = disp.handle(Envelope.new(type="xsm.counter.ADD", data={"n": 1}))
        r3 = disp.handle(
            Envelope.new(type="xsm.counter.ADD", subject="k", data=[1])
        )
        self.assertEqual(
            [r1.outcomes[0][1], r2.outcomes[0][1], r3.outcomes[0][1]],
            [
                "dead_lettered:unknown_event",
                "dead_lettered:corrupt",
                "dead_lettered:corrupt",
            ],
        )
        unknown = [r for r in dlq.list() if r.reason == "unknown_event"][0]
        self.assertEqual(unknown.event["payload"]["password"], "***")
        self.assertEqual(unknown.envelope["data"]["password"], "***")

    def test_machine_lookup_keyerror_is_unknown(self) -> None:
        def lookup(t: str) -> Any:
            raise KeyError(t)

        disp = InboundDispatcher(MemoryStore(), lookup)
        self.assertIsNone(disp.machine_for("x"))

    def test_infrastructure_failure_requeues_never_raises(self) -> None:
        class DownDLQ(MemoryDeadLetterStore):
            def put(self, record: Any) -> None:
                raise ConnectionError("dlq down")

        def lookup(t: str) -> Any:
            raise RuntimeError("user hook bug")

        broker = FakeBrokerAdapter()
        good = _counter()
        bad = InboundDispatcher(
            MemoryStore(), {}, dead_letters=DownDLQ()
        )  # unknown type -> DLQ put raises
        self.assertEqual(bad.handle(_add("k", 1)).retried, 1)
        self.assertEqual(
            InboundDispatcher(MemoryStore(), lookup)
            .handle(_add("k", 1))
            .retried,
            1,
        )

        async def go() -> Any:
            await broker.deliver("in", _add("x", 0))
            await broker.deliver(
                "in", Envelope.new(type="nobody", subject="y", data={})
            )
            disp = InboundDispatcher(
                MemoryStore(),
                {"xsm.counter.ADD": good},
                dead_letters=DownDLQ(),
            )
            return await disp.run_once(broker, "in")

        res = asyncio.run(go())  # the other subject still completes
        self.assertEqual((res.processed, res.retried), (1, 1))
        self.assertEqual(broker.pending("in"), 1)  # requeued, not lost


class TestTransactionalDedup(unittest.TestCase):
    def test_sqlite_inbox_shares_the_snapshot_transaction(self) -> None:
        import os
        import tempfile

        d = tempfile.mkdtemp()
        store = SQLiteStore(os.path.join(d, "x.db"))
        inbox = SQLiteInbox(store)
        disp = InboundDispatcher(
            store, lambda t: _counter(), inbox=inbox, lock=PessimisticLock()
        )
        e = _add("k", 1)
        self.assertEqual(disp.handle(e).processed, 1)
        self.assertEqual(disp.handle(e).duplicates, 1)
        self.assertEqual(disp.handle(e.with_attempt(1)).duplicates, 1)
        store.close()


class TestFinishedInstances(unittest.TestCase):
    """🐛 A final state stops the instance, and a stopped instance never
    reaches ``on_before_send`` -- so the inbox must be consulted first."""

    CFG = {
        "id": "o",
        "initial": "open",
        "states": {"open": {"on": {"PAY": "paid"}}, "paid": {"type": "final"}},
    }

    def test_redelivery_of_the_completing_event_is_a_duplicate(self) -> None:
        m = create_machine(self.CFG)
        disp = InboundDispatcher(
            MemoryStore(), lambda t: m, inbox=MemoryInbox()
        )
        e = Envelope.new(type="xsm.o.PAY", subject="o-1")
        self.assertEqual(disp.handle(e).processed, 1)
        self.assertEqual(disp.handle(e).duplicates, 1)
        # same id, different payload: a mismatch is dead-lettered
        bad = e.replace(data={"x": 1})
        self.assertEqual(
            disp.handle(bad).outcomes[0][1],
            "dead_lettered:idempotency_mismatch",
        )

    def test_new_event_for_a_finished_instance_is_dead_lettered_at_once(
        self,
    ) -> None:
        m = create_machine(self.CFG)
        dlq = MemoryDeadLetterStore()
        disp = InboundDispatcher(MemoryStore(), lambda t: m, dead_letters=dlq)
        disp.handle(Envelope.new(type="xsm.o.PAY", subject="o-1"))
        res = disp.handle(Envelope.new(type="xsm.o.PAY", subject="o-1"))
        self.assertEqual(res.outcomes[0][1], "dead_lettered:instance_done")
        self.assertEqual(dlq.list()[0].attempts, 1)


class TestRunForever(unittest.TestCase):
    def test_stops_on_event(self) -> None:
        broker = FakeBrokerAdapter()
        disp = InboundDispatcher(MemoryStore(), lambda t: _counter())

        async def go() -> DispatchResult:
            stop = asyncio.Event()
            task = asyncio.ensure_future(
                disp.run_forever(broker, "in", stop, poll_timeout=0.01)
            )
            await broker.deliver("in", _add("k", 0))
            for _ in range(200):
                if broker.pending("in") == 0 and broker.in_flight == 0:
                    break
                await asyncio.sleep(0.01)
            stop.set()
            return await task

        self.assertEqual(asyncio.run(go()).processed, 1)


if __name__ == "__main__":
    unittest.main()
