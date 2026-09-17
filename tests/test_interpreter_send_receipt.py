# tests/test_interpreter_send_receipt.py
# -----------------------------------------------------------------------------
# 🏛️ #39 (LC-42) + #38 (LC-41): a machine can ANSWER, and its inbox is bounded
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `Interpreter.send()` is fire-and-forget by
# design -- the correct default for an actor. But a caller that must gate
# an action on the machine's decision ("is the kill-switch tripped?") had
# no way to wait for THAT event's macrostep short of polling state. And the
# inbox accepted 20,000 events with no bound, no depth, no signal. Both are
# opt-in additions to `send()` and the constructor; defaults are unchanged.
# -----------------------------------------------------------------------------
"""`send(wait=True)` receipts, `priority=True`, bounded inbox (#38, #39)."""

import asyncio
import logging
import statistics
import time
import unittest
import warnings
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Event,
    Interpreter,
    InterpreterStoppedError,
    MachineLogic,
    OverflowPolicy,
    QueueOverflowError,
    Receipt,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# The filer's kill switch.
GOV: Dict[str, Any] = {
    "id": "gov",
    "initial": "armed",
    "context": {"n": 0},
    "states": {
        "armed": {
            "on": {
                "TRIP": "tripped",
                "TICK": {"actions": ["inc"]},
                "BOOM": {"actions": ["boom"]},
            }
        },
        "tripped": {"on": {"TICK": {"actions": ["inc"]}}},
    },
}


def _logic() -> MachineLogic:
    def inc(i, c, e, a):
        c["n"] += 1

    def boom(i, c, e, a):
        raise RuntimeError("action exploded")

    return MachineLogic(actions={"inc": inc, "boom": boom})


def _run(coro):
    return asyncio.run(coro)


# -----------------------------------------------------------------------------
# #39 -- receipts
# -----------------------------------------------------------------------------
class TestSendReceipt(_Quiet):
    def test_send_wait_returns_receipt_after_processing(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            r = await i.send("TRIP", wait=True)
            out = (type(r).__name__, set(i.current_state_ids))
            await i.stop()
            return r, out

        r, (cls, state) = _run(main())
        self.assertEqual(cls, "Receipt")
        self.assertEqual(state, {"gov.tripped"})
        self.assertEqual(r.state_ids, frozenset({"gov.tripped"}))

    def test_send_wait_receipt_reports_state_and_changed(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            r1 = await i.send("TICK", wait=True)  # targetless, mutates ctx
            r2 = await i.send("TRIP", wait=True)
            r3 = await i.send("NOISE", wait=True)  # unhandled
            await i.stop()
            return r1, r2, r3

        r1, r2, r3 = _run(main())
        # `changed` means "this event's macrostep changed configuration OR
        # context". A targetless transition whose action increments a
        # counter DID change something; only the unhandled event did not.
        self.assertTrue(r1.changed)
        self.assertEqual(r1.state_ids, frozenset({"gov.armed"}))
        self.assertTrue(r2.changed)
        self.assertEqual(r2.state_ids, frozenset({"gov.tripped"}))
        self.assertFalse(r3.changed)
        self.assertIsNone(r3.error)

    def test_send_wait_receipt_carries_processing_error(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            r = await i.send("BOOM", wait=True)
            status = i.status
            await i.stop()
            return r, status

        r, status = _run(main())
        # Default actionErrorPolicy "continue": machine keeps running, but
        # the receipt tells THIS caller its event's actions failed.
        self.assertIsInstance(r.error, RuntimeError)
        self.assertIn("exploded", str(r.error))
        self.assertEqual(status, "running")

    def test_send_without_wait_is_unchanged_and_returns_none(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            r = await i.send("TRIP")
            await asyncio.sleep(0.01)
            out = (r, set(i.current_state_ids))
            await i.stop()
            return out

        r, state = _run(main())
        self.assertIsNone(r)
        self.assertEqual(state, {"gov.tripped"})

    def test_stop_resolves_pending_receipts(self) -> None:
        async def main():
            async def slow(i, c, e, a):
                await asyncio.sleep(0.2)

            cfg = dict(GOV)
            cfg["states"] = {
                "armed": {"on": {"SLOW": {"actions": ["slow"]}, "X": {}}}
            }
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"slow": slow}))
            ).start()
            i.send("SLOW")  # occupies the loop
            fut = asyncio.ensure_future(i.send("X", wait=True))
            await asyncio.sleep(0.01)
            await i.stop()
            return await asyncio.wait_for(fut, timeout=2.0)

        r = _run(main())
        self.assertIsInstance(r, Receipt)
        self.assertIsNotNone(r.error)
        self.assertIn("stopped", str(r.error).lower())

    def test_dropped_event_resolves_receipt_with_error(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            await i.stop()
            i.status = "done"  # a terminal machine drops sends
            return await i.send("TICK", wait=True)

        r = _run(main())
        self.assertIsNotNone(r.error)

    def test_reserved_payload_key_warns(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"seen": None},
            "states": {"a": {"on": {"E": {"actions": ["rec"]}}}},
        }

        def rec(i, c, e, a):
            c["seen"] = dict(e.payload)

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))
            ).start()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                await i.send(
                    {"type": "E", "wait": "yes", "priority": 3}, wait=True
                )
            out = (i.context["seen"], [str(w.message) for w in caught])
            await i.stop()
            return out

        seen, msgs = _run(main())
        # Dict form keeps the keys in the payload but warns about the clash.
        self.assertEqual(seen, {"wait": "yes", "priority": 3})
        self.assertTrue(any("reserved" in m for m in msgs), msgs)

    def test_sync_interpreter_send_returns_receipt_when_asked(self) -> None:
        """The sync engine already answers inline; `wait=True` is honoured
        for API symmetry and returns the same Receipt shape."""
        i = SyncInterpreter(create_machine(GOV, logic=_logic())).start()
        r = i.send("TRIP", wait=True)
        self.assertIsInstance(r, Receipt)
        self.assertTrue(r.changed)
        self.assertEqual(r.state_ids, frozenset({"gov.tripped"}))
        self.assertIsNone(i.send("TICK"))
        i.stop()


# -----------------------------------------------------------------------------
# #39 -- priority send
# -----------------------------------------------------------------------------
class TestPrioritySend(_Quiet):
    def test_send_priority_is_a_discoverable_alias(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            for _ in range(500):
                i.send("TICK")
            r = await i.send_priority("TRIP")
            n = i.context["n"]
            await i.stop()
            return r, n

        r, n = _run(main())
        self.assertIsInstance(r, Receipt)
        self.assertTrue(r.changed)
        self.assertLess(n, 50)

    def test_priority_event_jumps_queued_backlog(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            for _ in range(2000):
                i.send("TICK")
            r = await i.send("TRIP", wait=True, priority=True)
            processed_when_tripped = i.context["n"]
            await i.stop()
            return r, processed_when_tripped

        r, n = _run(main())
        self.assertTrue(r.changed)
        # TRIP ran before the bulk of the 2,000 TICKs behind it.
        self.assertLess(n, 100, f"{n} TICKs processed before TRIP")

    def test_priority_events_are_fifo_among_themselves(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"log": []},
            "states": {
                "a": {
                    "on": {
                        "P": {"actions": ["rec"]},
                        "T": {"actions": ["rec"]},
                    }
                }
            },
        }

        def rec(i, c, e, a):
            c["log"].append(e.payload["k"])

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))
            ).start()
            for k in range(50):
                i.send("T", k=f"t{k}")
            for k in range(5):
                i.send("P", k=f"p{k}", priority=True)
            while len(i.context["log"]) < 55:
                await asyncio.sleep(0)
            out = list(i.context["log"])
            await i.stop()
            return out

        log = _run(main())
        self.assertEqual(log[:5], ["p0", "p1", "p2", "p3", "p4"])

    def test_priority_plus_wait_bounds_decision_latency(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            lat: List[float] = []
            for _ in range(20):
                for _ in range(2000):
                    i.send("TICK")
                t0 = time.perf_counter()
                await i.send("TICK", wait=True, priority=True)
                lat.append((time.perf_counter() - t0) * 1000)
            await i.stop()
            return statistics.median(lat)

        p50 = _run(main())
        self.assertLess(p50, 5.0, f"p50 decision latency {p50:.2f} ms")


# -----------------------------------------------------------------------------
# #38 -- bounded, observable inbox
# -----------------------------------------------------------------------------
class TestQueueDepthAndBound(_Quiet):
    def test_queue_depth_is_public_on_both_engines(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            for _ in range(7):
                i.send("TICK")
            d = i.queue_depth
            await i.stop()
            return d

        self.assertEqual(_run(main()), 7)
        s = SyncInterpreter(create_machine(GOV, logic=_logic())).start()
        self.assertEqual(s.queue_depth, 0)
        s.stop()

    def test_unbounded_default_is_unchanged(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            for _ in range(20_000):
                i.send("TICK")
            d = i.queue_depth
            await i.stop()
            return d

        self.assertEqual(_run(main()), 20_000)

    def test_raise_policy_raises_queue_overflow_error(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(GOV, logic=_logic()),
                max_queue_size=10,
                overflow_policy=OverflowPolicy.RAISE,
            ).start()
            for _ in range(10):
                i.send("TICK")
            try:
                i.send("TICK")
            except QueueOverflowError as exc:
                out = (exc.interpreter_id, exc.depth, exc.maxsize)
            else:
                out = None
            await i.stop()
            return out

        self.assertEqual(_run(main()), ("gov", 10, 10))

    def test_raise_is_default_when_bound_is_set(self) -> None:
        async def main():
            i = Interpreter(
                create_machine(GOV, logic=_logic()), max_queue_size=1
            )
            await i.start()
            i.send("TICK")
            try:
                i.send("TICK")
                out = "no raise"
            except QueueOverflowError:
                out = "raised"
            await i.stop()
            return out

        self.assertEqual(_run(main()), "raised")

    def test_block_policy_suspends_until_space(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(GOV, logic=_logic()),
                max_queue_size=2,
                overflow_policy=OverflowPolicy.BLOCK,
            ).start()
            t0 = time.perf_counter()
            for _ in range(50):
                await i.send("TICK")  # each may suspend until consumed
            while i.context["n"] < 50:
                await asyncio.sleep(0)
            out = (i.context["n"], time.perf_counter() - t0)
            await i.stop()
            return out

        n, _ = _run(main())
        self.assertEqual(n, 50)

    def test_drop_newest_discards_logs_and_notifies_plugin(self) -> None:
        class Spy(PluginBase):
            def __init__(self):
                self.dropped: List[Any] = []

            def on_event_dropped(self, i, event, reason):
                self.dropped.append((event.type, reason))

        async def main():
            spy = Spy()
            i = Interpreter(
                create_machine(GOV, logic=_logic()),
                max_queue_size=3,
                overflow_policy=OverflowPolicy.DROP_NEWEST,
            )
            i.use(spy)
            await i.start()
            logging.disable(logging.NOTSET)
            with self.assertLogs(level="WARNING") as logs:
                for _ in range(5):
                    i.send("TICK")
            out = (i.queue_depth, spy.dropped, logs.output)
            await i.stop()
            return out

        depth, dropped, logs = _run(main())
        self.assertEqual(depth, 3)
        self.assertEqual(dropped, [("TICK", "queue_full")] * 2)
        self.assertTrue(any("dropped" in line.lower() for line in logs))

    def test_send_events_honours_the_bound(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(GOV, logic=_logic()), max_queue_size=3
            ).start()
            try:
                await i.send_events(["TICK"] * 5)
                out = "no raise"
            except QueueOverflowError:
                out = "raised"
            await i.stop()
            return out

        self.assertEqual(_run(main()), "raised")

    def test_priority_lane_is_not_subject_to_the_bound(self) -> None:
        """Backpressure applies to routine traffic; an urgent decision must
        still get through a full inbox."""

        async def main():
            i = await Interpreter(
                create_machine(GOV, logic=_logic()), max_queue_size=2
            ).start()
            i.send("TICK")
            i.send("TICK")
            r = await i.send("TRIP", wait=True, priority=True)
            await i.stop()
            return r.changed

        self.assertTrue(_run(main()))


# -----------------------------------------------------------------------------
# #75 -- receipts keyed on the QUEUED envelope, not the caller's object
# -----------------------------------------------------------------------------
class TestReusedEventInstanceReceipts(_Quiet):
    """A pre-built `Event` used as a template must never hang a receipt."""

    def test_reused_event_instance_resolves_both_receipts(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            ev = Event(type="TICK", payload={})
            r1, r2 = await asyncio.wait_for(
                asyncio.gather(i.send(ev, wait=True), i.send(ev, wait=True)),
                timeout=2,
            )
            n = i.context["n"]
            await i.stop()
            return r1, r2, n

        r1, r2, n = _run(main())
        self.assertIsInstance(r1, Receipt)
        self.assertIsInstance(r2, Receipt)
        self.assertTrue(r1.changed and r2.changed)
        self.assertEqual(n, 2)

    def test_many_concurrent_receipts_on_one_instance(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            ev = Event(type="TICK", payload={})
            rs = await asyncio.wait_for(
                asyncio.gather(*(i.send(ev, wait=True) for _ in range(150))),
                timeout=5,
            )
            n = i.context["n"]
            await i.stop()
            return rs, n

        rs, n = _run(main())
        self.assertEqual(len(rs), 150)
        self.assertTrue(all(isinstance(r, Receipt) for r in rs))
        self.assertEqual(n, 150)

    def test_stop_resolves_duplicate_instance_receipts(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            ev = Event(type="TICK", payload={})
            # Park the run loop so the sends stay queued, then stop.
            i._processing = True
            i._event_loop_task.cancel()
            f1 = asyncio.ensure_future(i.send(ev, wait=True))
            f2 = asyncio.ensure_future(i.send(ev, wait=True))
            await asyncio.sleep(0)
            await i.stop()
            return await asyncio.wait_for(asyncio.gather(f1, f2), timeout=2)

        r1, r2 = _run(main())
        self.assertIsInstance(r1.error, InterpreterStoppedError)
        self.assertIsInstance(r2.error, InterpreterStoppedError)

    def test_caller_object_is_not_mutated_and_payload_preserved(self) -> None:
        async def main():
            i = await Interpreter(create_machine(GOV, logic=_logic())).start()
            ev = Event(type="TICK", payload={"k": 1})
            await i.send(ev, wait=True)
            await i.stop()
            return ev

        ev = _run(main())
        self.assertEqual(ev, Event(type="TICK", payload={"k": 1}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
