"""Battle test #304: `on_before_send` / `on_event_processed` under load.

🏛️ `tests/test_plugin_hooks_send.py` proves the hooks' single-threaded
contract. This file attacks what that one cannot: many producer threads,
re-entrant hooks, hooks that block or raise `BaseException`s, timers
racing user sends, and a seeded randomised stress run on both engines.
Every bound on a potentially hanging call is a thread join or an
`asyncio.wait_for` with a timeout -- `pytest-timeout` is not a dependency.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import random
import threading
import unittest
from typing import Any, Callable, List, Optional, Tuple

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    Receipt,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)

HANG_BOUND_S = 10.0

# PING is handled everywhere (counts admitted PINGs in context); TOGGLE
# flips a <-> b; b leaves by itself after 50 ms so timers race user sends.
CFG = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "on": {"PING": {"actions": "inc"}, "NOTE": {}},
    "states": {
        "a": {"on": {"TOGGLE": "b"}},
        "b": {"after": {"50": "a"}, "on": {"TOGGLE": "a"}},
    },
}
VALID_STATES = ({"m.a"}, {"m.b"})


def _machine():
    return create_machine(
        CFG,
        logic=MachineLogic(
            actions={"inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}
        ),
    )


def _dup(interpreter) -> Receipt:
    return Receipt(
        frozenset(interpreter.current_state_ids), False, duplicate=True
    )


class Counter(PluginBase):
    """Short-circuits events whose payload ``k`` is a multiple of
    ``block_every``; counts every hook call under a lock."""

    def __init__(self, block_every: int = 0) -> None:
        self.lock = threading.Lock()
        self.block_every = block_every
        self.blocked: List[Any] = []
        self.processed: List[Tuple[str, Any, Receipt]] = []
        self.errors: List[str] = []

    def on_before_send(self, interpreter, event):
        k = event.payload.get("k")
        if self.block_every and k is not None and k % self.block_every == 0:
            with self.lock:
                self.blocked.append(k)
            return _dup(interpreter)
        return None

    def on_event_processed(self, interpreter, event, receipt):
        with self.lock:
            # 📝 Engine-minted `after` events carry no `.payload`.
            payload = getattr(event, "payload", None) or {}
            self.processed.append((event.type, payload.get("k"), receipt))

    def on_plugin_error(self, interpreter, plugin, hook, error):
        self.errors.append(f"{hook}:{type(error).__name__}")

    def user_ks(self) -> List[Any]:
        return [k for t, k, _ in self.processed if t == "PING"]


def _run_bounded(fn: Callable[[], Any]) -> List[Any]:
    """Run `fn` on a daemon thread; fail (not hang) past HANG_BOUND_S."""
    box: List[Any] = []

    def _target() -> None:
        try:
            box.append(("ok", fn()))
        except BaseException as exc:  # noqa: BLE001 -- relayed to test
            box.append(("err", exc))

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(HANG_BOUND_S)
    if t.is_alive():
        raise AssertionError(f"hung for more than {HANG_BOUND_S}s")
    return box


# =========================================================================
# 🧵 Sync engine
# =========================================================================
class TestSyncConcurrency(unittest.TestCase):
    def _interp(self, *plugins):
        clk = SimulatedClock()
        i = SyncInterpreter(_machine(), clock=clk)
        for p in plugins:
            i.use(p)
        return i.start(), clk

    def test_threadsafe_producers_exactly_once_per_admitted_event(self):
        # Arrange
        rec = Counter(block_every=3)
        i, _ = self._interp(rec)
        threads, per = 8, 250
        barrier = threading.Barrier(threads)

        def produce(tid: int) -> None:
            barrier.wait()
            for j in range(per):
                i.send_threadsafe("PING", k=tid * per + j)

        # Act
        workers = [
            threading.Thread(target=produce, args=(t,)) for t in range(threads)
        ]
        for w in workers:
            w.start()
        for w in workers:
            w.join(HANG_BOUND_S)
        i.send("NOTE")  # the owner's next step drains the mailbox

        # Assert
        total = threads * per
        admitted = [k for k in range(total) if k % 3]
        self.assertEqual(sorted(rec.user_ks()), admitted)  # once each
        self.assertEqual(
            sorted(rec.blocked), [k for k in range(total) if not k % 3]
        )
        self.assertEqual(i.context["n"], len(admitted))
        self.assertEqual(rec.errors, [])

    def test_threadsafe_preserves_fifo_per_producer_thread(self):
        # Arrange
        rec = Counter()
        i, _ = self._interp(rec)

        def produce(tid: int) -> None:
            for j in range(200):
                i.send_threadsafe("PING", k=(tid, j))

        workers = [
            threading.Thread(target=produce, args=(t,)) for t in range(4)
        ]

        # Act
        for w in workers:
            w.start()
        for w in workers:
            w.join(HANG_BOUND_S)
        i.send("NOTE")

        # Assert
        for tid in range(4):
            seq = [j for (t, j) in rec.user_ks() if t == tid]
            self.assertEqual(seq, list(range(200)))

    def test_receipts_carry_a_coherent_configuration_under_contention(self):
        # Arrange: owner keeps toggling while producers flood the mailbox.
        rec = Counter()
        i, _ = self._interp(rec)
        stop = threading.Event()

        def produce() -> None:
            # 📝 Bounded: an unbounded producer outruns the owner by
            #    design ("bound the producers, not the mailbox").
            for _ in range(3000):
                if stop.is_set():
                    return
                i.send_threadsafe("PING", k=0)

        w = threading.Thread(target=produce)
        w.start()

        # Act
        for _ in range(300):
            i.send("TOGGLE")
        stop.set()
        w.join(HANG_BOUND_S)
        i.send("NOTE")

        # Assert
        for _, _, receipt in rec.processed:
            self.assertIsInstance(receipt.state_ids, frozenset)
            self.assertIn(set(receipt.state_ids), VALID_STATES)

    def test_interceptor_that_sends_reentrantly_admits_both_events(self):
        # Arrange: on PING, the interceptor sends NOTE itself and admits.
        rec = Counter()

        class Echo(PluginBase):
            def on_before_send(self, interpreter, event):
                if event.type == "PING":
                    interpreter.send("NOTE")
                return None

        i, _ = self._interp(Echo(), rec)

        # Act
        box = _run_bounded(lambda: i.send("PING", wait=True))

        # Assert: NOTE ran first (it was sent before PING was queued).
        self.assertEqual(box[0][0], "ok")
        self.assertEqual([t for t, _, _ in rec.processed], ["NOTE", "PING"])

    def test_interceptor_that_resends_the_same_event_recurses_loudly(self):
        # Arrange: an unguarded self-resend is unbounded recursion; it is
        # contained by _SafePlugin as RecursionError (fail-open), not a hang.
        rec = Counter()

        class Loop(PluginBase):
            def on_before_send(self, interpreter, event):
                interpreter.send(event.type)

        i, _ = self._interp(Loop(), rec)

        # Act
        box = _run_bounded(lambda: i.send("NOTE"))

        # Assert
        self.assertEqual(box[0][0], "ok")
        self.assertIn("on_before_send:RecursionError", rec.errors)
        self.assertEqual(i.status, "running")

    def test_processed_hook_that_sends_runs_the_follow_up_exactly_once(self):
        # Arrange: every TOGGLE that settles triggers one PING.
        rec = Counter()

        class Chain(PluginBase):
            def on_event_processed(self, interpreter, event, receipt):
                if event.type == "TOGGLE":
                    interpreter.send("PING", k=1)

        # 📝 `rec` first: a send from the hook is processed INLINE (the
        #    step has finished), so plugins after `Chain` would see the
        #    follow-up PING before the TOGGLE that caused it.
        i, _ = self._interp(rec, Chain())

        # Act
        box = _run_bounded(lambda: [i.send("TOGGLE") for _ in range(10)])

        # Assert
        self.assertEqual(box[0][0], "ok", box)
        self.assertEqual(i.context["n"], 10)
        self.assertEqual(
            [t for t, _, _ in rec.processed], ["TOGGLE", "PING"] * 10
        )

    def test_timer_fired_before_a_user_send_is_reported_first(self):
        # Arrange
        rec = Counter()
        i, clk = self._interp(rec)
        i.send("TOGGLE")  # -> b, arms after 50

        # Act
        clk.increment(51)
        i.send("PING", k=7)

        # Assert
        kinds = [t for t, _, _ in rec.processed]
        self.assertEqual(kinds[0], "TOGGLE")
        self.assertTrue(kinds[1].startswith("after."), kinds)
        self.assertEqual(kinds[2:], ["PING"])
        self.assertEqual(rec.processed[2][2].state_ids, frozenset({"m.a"}))

    def test_blocked_interceptor_does_not_hold_the_mailbox_lock(self):
        # Arrange: the owner's interceptor parks; producers must not.
        gate, entered = threading.Event(), threading.Event()

        class Park(PluginBase):
            def on_before_send(self, interpreter, event):
                if event.type == "TOGGLE":
                    entered.set()
                    gate.wait(HANG_BOUND_S)
                return None

        rec = Counter()
        i, _ = self._interp(Park(), rec)
        owner = threading.Thread(target=lambda: i.send("TOGGLE"))
        owner.start()
        self.assertTrue(entered.wait(HANG_BOUND_S))

        # Act: a producer posts while the owner is parked in the hook.
        box = _run_bounded(lambda: i.send_threadsafe("PING", k=1))
        gate.set()
        owner.join(HANG_BOUND_S)
        i.send("NOTE")

        # Assert
        self.assertEqual(box, [("ok", None)])
        self.assertIn(1, rec.user_ks())

    def test_keyboard_interrupt_and_system_exit_escape_the_interceptor(self):
        for exc_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(exc=exc_type.__name__):
                # Arrange
                class Bail(PluginBase):
                    def on_before_send(self, interpreter, event):
                        raise exc_type()

                rec = Counter()
                i, _ = self._interp(Bail(), rec)

                # Act / Assert: not swallowed, event never processed.
                with self.assertRaises(exc_type):
                    i.send("PING", k=1)
                self.assertEqual(rec.processed, [])
                self.assertEqual(rec.errors, [])

    def test_cancelled_error_in_interceptor_is_contained_fail_open(self):
        # Arrange: #114 deliberately contains CancelledError from a hook.
        class Cancel(PluginBase):
            def on_before_send(self, interpreter, event):
                raise asyncio.CancelledError()

        rec = Counter()
        i, _ = self._interp(Cancel(), rec)

        # Act
        i.send("PING", k=1)

        # Assert
        self.assertEqual(rec.errors, ["on_before_send:CancelledError"])
        self.assertEqual(rec.user_ks(), [1])

    def test_wrong_return_type_is_reported_and_the_event_admitted(self):
        # Arrange
        class Wrong(PluginBase):
            def on_before_send(self, interpreter, event):
                return {"duplicate": True}

        rec = Counter()
        i, _ = self._interp(Wrong(), rec)

        # Act
        receipt = i.send("PING", k=1, wait=True)

        # Assert
        self.assertFalse(receipt.duplicate)
        self.assertEqual(rec.errors, ["on_before_send:TypeError"])
        self.assertEqual(i.context["n"], 1)

    def test_stop_inside_processed_hook_ends_cleanly(self):
        # Arrange
        rec = Counter()

        class Stopper(PluginBase):
            def on_event_processed(self, interpreter, event, receipt):
                if event.type == "TOGGLE":
                    interpreter.stop()

        i, _ = self._interp(Stopper(), rec)
        i.send_threadsafe("PING", k=2)  # queued behind the stop

        # Act
        box = _run_bounded(lambda: i.send("TOGGLE", wait=True))

        # Assert
        self.assertEqual(box[0][0], "ok", box)
        self.assertEqual(i.status, "stopped")
        self.assertIsNone(i.send("PING", k=3))
        self.assertEqual(rec.user_ks(), [2])  # the drained one only

    def test_seeded_stress_two_thousand_mixed_operations(self):
        # Arrange
        rng = random.Random(1234)
        rec = Counter(block_every=5)
        i, clk = self._interp(rec)
        admitted: List[int] = []

        # Act
        for k in range(1, 2001):
            op = rng.random()
            if op < 0.45:
                i.send("PING", k=k)
            elif op < 0.65:
                i.send_threadsafe("PING", k=k)
            elif op < 0.85:
                i.send("TOGGLE")
                continue
            else:
                clk.increment(rng.choice((10, 30, 60)))
                continue
            if k % 5:
                admitted.append(k)
        i.send("NOTE")

        # Assert
        self.assertEqual(sorted(rec.user_ks()), admitted)
        self.assertEqual(i.context["n"], len(admitted))
        self.assertTrue(all(k % 5 == 0 for k in rec.blocked))
        for _, _, receipt in rec.processed:
            self.assertIn(set(receipt.state_ids), VALID_STATES)
        self.assertEqual(rec.errors, [])


# =========================================================================
# ⚡ Async engine
# =========================================================================
class TestAsyncConcurrency(unittest.IsolatedAsyncioTestCase):
    async def _interp(self, *plugins, clock: Optional[SimulatedClock] = None):
        i = Interpreter(_machine(), clock=clock or SimulatedClock())
        for p in plugins:
            i.use(p)
        return await i.start()

    async def test_gather_and_threadsafe_producers_exactly_once(self):
        # Arrange
        rec = Counter(block_every=4)
        i = await self._interp(rec)
        loop_ks = list(range(0, 1000))
        thread_ks = list(range(1000, 2000))

        def produce(ks: List[int]) -> None:
            for k in ks:
                i.send_threadsafe("PING", k=k).result(HANG_BOUND_S)

        # Act
        await asyncio.wait_for(
            asyncio.gather(
                *(i.send("PING", k=k) for k in loop_ks),
                asyncio.to_thread(produce, thread_ks[:500]),
                asyncio.to_thread(produce, thread_ks[500:]),
            ),
            HANG_BOUND_S,
        )
        await asyncio.wait_for(i.send("NOTE", wait=True), HANG_BOUND_S)
        await i.stop()

        # Assert
        admitted = [k for k in loop_ks + thread_ks if k % 4]
        self.assertEqual(sorted(rec.user_ks()), admitted)
        self.assertEqual(i.context["n"], len(admitted))
        self.assertEqual(len(rec.blocked), 2000 - len(admitted))

    async def test_wait_true_short_circuit_resolves_immediately(self):
        # Arrange
        rec = Counter(block_every=1)
        i = await self._interp(rec)

        # Act
        receipt = await asyncio.wait_for(
            i.send("PING", k=5, wait=True), HANG_BOUND_S
        )
        await i.stop()

        # Assert
        self.assertTrue(receipt.duplicate)
        self.assertEqual(rec.processed, [])

    async def test_interceptor_that_sends_reentrantly_admits_both(self):
        # Arrange
        rec = Counter()

        class Echo(PluginBase):
            def on_before_send(self, interpreter, event):
                if event.type == "PING":
                    interpreter.send("NOTE")
                return None

        i = await self._interp(Echo(), rec)

        # Act
        await asyncio.wait_for(i.send("PING", k=1, wait=True), HANG_BOUND_S)
        await i.stop()

        # Assert
        self.assertEqual([t for t, _, _ in rec.processed], ["NOTE", "PING"])

    async def test_cancelled_error_contained_keyboard_interrupt_escapes(self):
        # Arrange
        class Cancel(PluginBase):
            def on_before_send(self, interpreter, event):
                if event.type == "PING":
                    raise asyncio.CancelledError()
                raise KeyboardInterrupt()

        rec = Counter()
        i = await self._interp(Cancel(), rec)

        # Act
        receipt = await asyncio.wait_for(
            i.send("PING", k=1, wait=True), HANG_BOUND_S
        )
        with self.assertRaises(KeyboardInterrupt):
            i.send("NOTE")
        await i.stop()

        # Assert
        self.assertFalse(receipt.duplicate)
        self.assertEqual(rec.errors, ["on_before_send:CancelledError"])
        self.assertEqual(rec.user_ks(), [1])

    async def test_timer_and_user_events_each_reported_once(self):
        # Arrange
        rec = Counter()
        clk = SimulatedClock()
        i = await self._interp(rec, clock=clk)
        await i.send("TOGGLE", wait=True)

        # Act
        await clk.increment(51)
        await i.send("PING", k=9, wait=True)
        await i.stop()

        # Assert
        kinds = [t for t, _, _ in rec.processed]
        self.assertEqual(kinds[0], "TOGGLE")
        self.assertTrue(kinds[1].startswith("after."), kinds)
        self.assertEqual(kinds[2:], ["PING"])

    async def test_seeded_stress_two_thousand_mixed_operations(self):
        # Arrange
        rng = random.Random(1234)
        rec = Counter(block_every=5)
        clk = SimulatedClock()
        i = await self._interp(rec, clock=clk)
        admitted: List[int] = []
        futures = []

        # Act
        for k in range(1, 2001):
            op = rng.random()
            if op < 0.45:
                await i.send("PING", k=k)
            elif op < 0.65:
                futures.append(i.send_threadsafe("PING", k=k))
            elif op < 0.85:
                await i.send("TOGGLE")
                continue
            else:
                await clk.increment(rng.choice((10, 30, 60)))
                continue
            if k % 5:
                admitted.append(k)
        await asyncio.wait_for(
            asyncio.gather(*(asyncio.wrap_future(f) for f in futures)),
            HANG_BOUND_S,
        )
        await asyncio.wait_for(i.send("NOTE", wait=True), HANG_BOUND_S)
        await i.stop()

        # Assert
        self.assertEqual(sorted(rec.user_ks()), admitted)
        self.assertEqual(i.context["n"], len(admitted))
        for _, _, receipt in rec.processed:
            self.assertIn(set(receipt.state_ids), VALID_STATES)
        self.assertEqual(rec.errors, [])


if __name__ == "__main__":
    unittest.main()


def test_sync_interceptor_runs_before_the_not_running_refusal() -> None:
    """#283 battle (parity with the async engine): a `on_before_send`
    interceptor -- the idempotency inbox -- must answer a replayed key
    even when the machine has since FINISHED; the sync engine refused
    with `InterpreterStoppedError` first, so a retrying client got a 409
    instead of its original receipt."""
    from src.xstate_statemachine import (
        PluginBase,
        SyncInterpreter,
        create_machine,
    )
    from src.xstate_statemachine.events import Receipt

    cfg = {
        "id": "f",
        "initial": "a",
        "states": {"a": {"on": {"GO": "done"}}, "done": {"type": "final"}},
    }
    seen = []

    class Replay(PluginBase):
        def on_before_send(self, interp, event):
            seen.append(event.type)
            if event.type == "GO":
                return Receipt(
                    frozenset({"f.done"}), True, None, duplicate=True
                )
            return None

    i = SyncInterpreter(create_machine(cfg)).use(Replay()).start()
    i.send("GO")  # intercepted (the plugin answers) -- machine stays in a
    assert "f.a" in i.current_state_ids
    i.stop()
    assert i.status != "running"
    r = i.send("GO", wait=True)
    assert r is not None and r.duplicate is True, r
    assert seen == ["GO", "GO"]
