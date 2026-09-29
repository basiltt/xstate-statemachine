"""`on_before_send` / `on_event_processed` (#304) -- both engines.

🏛️ Two hooks that every persistence/observability plugin depends on:
an interceptor that can answer a `send()` without the machine seeing the
event (idempotency inbox, rate limiting), and a per-event outcome hook that
carries the same `Receipt` a `wait=True` caller gets. They are exercised
here on `Interpreter` and `SyncInterpreter` side by side, because each
engine has its own `send()` and its own drain.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import unittest
from typing import Any, List, Optional, Tuple

from src.xstate_statemachine import (
    Event,
    Interpreter,
    LoggingInspector,
    PluginBase,
    Receipt,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.testing_utils import logic_names, stub_logic

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAYMENT = json.loads(
    (
        ROOT
        / "tests"
        / "tests_cli"
        / "stately_machines"
        / "AdvancePayment.json"
    ).read_text(encoding="utf-8")
)

# A small chart with every outcome reachable: changed, unchanged (unknown
# event), denied (guard False), deferred (onUnhandled), error (action raises),
# and an `after` timer so engine-minted events are covered.
CFG = {
    "id": "t",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "GO": {"target": "b", "actions": "inc"},
                "GUARDED": {"target": "b", "guard": "never"},
                "BOOM": {"actions": "boom"},
                "LATER": "c",
            },
        },
        "b": {"after": {"100": "a"}, "on": {"BACK": "a"}},
        "c": {"on": {"WAIT_FOR_ME": "a"}},
    },
}


DEFER_CFG = {
    "id": "d",
    "initial": "a",
    "onUnhandled": "defer",
    "states": {"a": {"on": {"LATER": "c"}}, "c": {"on": {"WAIT_FOR_ME": "a"}}},
}


def _logic():
    from src.xstate_statemachine import MachineLogic

    def boom(i, c, e, a):
        raise RuntimeError("kaboom")

    return MachineLogic(
        actions={
            "inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1),
            "boom": boom,
        },
        guards={"never": lambda c, e: False},
    )


class Recorder(PluginBase):
    """Records every `on_event_processed`; optionally intercepts."""

    def __init__(self, block: Optional[str] = None, raise_in_intercept=False):
        self.processed: List[Tuple[str, Receipt]] = []
        self.received: List[str] = []
        self.block = block
        self.raise_in_intercept = raise_in_intercept
        self.plugin_errors: List[str] = []

    def on_before_send(self, interpreter, event):
        if self.raise_in_intercept:
            raise ValueError("interceptor bug")
        if self.block is not None and event.type == self.block:
            return Receipt(
                frozenset(interpreter.current_state_ids),
                False,
                None,
                False,
                False,
                True,  # duplicate
            )
        return None

    def on_event_received(self, interpreter, event):
        self.received.append(event.type)

    def on_event_processed(self, interpreter, event, receipt):
        self.processed.append((event.type, receipt))

    def on_plugin_error(self, interpreter, plugin, hook, error):
        self.plugin_errors.append(f"{hook}:{type(error).__name__}")


class BadReturn(PluginBase):
    def on_before_send(self, interpreter, event):
        return "nope"  # not a Receipt -> reported, event admitted


def _outcomes(rec: Recorder):
    return [
        (
            t,
            r.changed,
            r.denied,
            r.deferred,
            r.duplicate,
            type(r.error).__name__ if r.error else None,
        )
        for t, r in rec.processed
    ]


class TestSyncEngine(unittest.TestCase):
    def _interp(self, *plugins):
        clk = SimulatedClock()
        i = SyncInterpreter(create_machine(CFG, logic=_logic()), clock=clk)
        for p in plugins:
            i.use(p)
        return i.start(), clk

    def test_intercept_short_circuits_and_caller_gets_the_receipt(self):
        rec = Recorder(block="GO")
        i, _ = self._interp(rec)
        r = i.send("GO", wait=True)
        self.assertTrue(r.duplicate)
        self.assertFalse(r.changed)
        self.assertEqual(i.current_state_ids, {"t.a"})  # never queued
        self.assertEqual(rec.received, [])  # on_event_received not fired
        self.assertEqual(rec.processed, [])  # on_event_processed not fired
        self.assertIsNone(i.send("GO"))  # fire-and-forget shape

    def test_processed_fires_once_per_event_with_correct_flags(self):
        rec = Recorder()
        i, clk = self._interp(rec)
        self.assertTrue(i.send("GO", wait=True).changed)
        i.send("BACK")
        i.send("GUARDED")
        i.send("NOPE")
        self.assertEqual(
            _outcomes(rec),
            [
                ("GO", True, False, False, False, None),
                ("BACK", True, False, False, False, None),
                ("GUARDED", False, True, False, False, None),
                ("NOPE", False, False, False, False, None),
            ],
        )

    def test_deferred_events_report_deferred_then_their_replay(self):
        rec = Recorder()
        i = SyncInterpreter(create_machine(DEFER_CFG)).use(rec).start()
        i.send("WAIT_FOR_ME")  # unhandled in a -> deferred
        i.send("LATER")  # -> c; the held event is replayed as its own step
        self.assertEqual(
            [(t, r.deferred, r.changed) for t, r in rec.processed],
            [
                ("WAIT_FOR_ME", True, False),
                ("LATER", False, True),
                ("WAIT_FOR_ME", False, True),  # the replay
            ],
        )

    def test_processed_fires_for_engine_minted_events_and_errors(self):
        rec = Recorder()
        i, clk = self._interp(rec)
        i.send("GO")  # -> b, arms after 100
        clk.increment(101)
        i.tick()  # timer fires -> back to a
        i.send("BOOM", wait=True)
        kinds = [t for t, _ in rec.processed]
        self.assertEqual(kinds[0], "GO")
        self.assertTrue(kinds[1].startswith("after."), kinds)
        self.assertEqual(kinds[2], "BOOM")
        after_receipt = rec.processed[1][1]
        self.assertTrue(after_receipt.changed)
        boom = rec.processed[2][1]
        self.assertEqual(type(boom.error).__name__, "RuntimeError")

    def test_caller_receipt_is_identical_to_hook_receipt(self):
        rec = Recorder()
        i, _ = self._interp(rec)
        r = i.send("GO", wait=True)
        self.assertIs(r, rec.processed[0][1])

    def test_raising_interceptor_is_fail_open(self):
        bug = Recorder(raise_in_intercept=True)
        watcher = Recorder()
        i, _ = self._interp(bug, watcher)
        r = i.send("GO", wait=True)
        self.assertTrue(r.changed)  # admitted
        self.assertIn("on_before_send:ValueError", watcher.plugin_errors)

    def test_wrong_return_type_is_reported_and_admitted(self):
        watcher = Recorder()
        i, _ = self._interp(BadReturn(), watcher)
        self.assertTrue(i.send("GO", wait=True).changed)
        self.assertIn("on_before_send:TypeError", watcher.plugin_errors)

    def test_first_interceptor_wins(self):
        a = Recorder(block="GO")
        b = Recorder(block="GO")
        calls: List[str] = []
        orig_a, orig_b = a.on_before_send, b.on_before_send
        a.on_before_send = lambda i, e: (calls.append("a"), orig_a(i, e))[1]
        b.on_before_send = lambda i, e: (calls.append("b"), orig_b(i, e))[1]
        i, _ = self._interp(a, b)
        i.send("GO", wait=True)
        self.assertEqual(calls, ["a"])

    def test_send_events_is_intercepted_too(self):
        rec = Recorder(block="GO")
        i, _ = self._interp(rec)
        i.send_events(["GO", "LATER"])
        self.assertEqual(i.current_state_ids, {"t.c"})
        self.assertEqual([t for t, _ in rec.processed], ["LATER"])

    def test_no_overhead_path_when_no_plugin_wants_it(self):
        i, _ = self._interp(LoggingInspector())  # implements the hook
        self.assertTrue(i._wants_event_processed)
        j, _ = self._interp()
        self.assertFalse(j._wants_event_processed)


class TestAsyncEngine(unittest.IsolatedAsyncioTestCase):
    async def _interp(self, *plugins):
        clk = SimulatedClock()
        i = Interpreter(create_machine(CFG, logic=_logic()), clock=clk)
        for p in plugins:
            i.use(p)
        await i.start()
        return i, clk

    async def test_intercept_short_circuits_and_resolves_awaitable(self):
        rec = Recorder(block="GO")
        i, _ = await self._interp(rec)
        r = await i.send("GO", wait=True)
        self.assertTrue(r.duplicate)
        self.assertIsNone(await i.send("GO"))
        await asyncio.sleep(0)
        self.assertEqual(i.current_state_ids, {"t.a"})
        self.assertEqual(rec.received, [])
        self.assertEqual(rec.processed, [])
        await i.stop()

    async def test_processed_flags_and_identity(self):
        rec = Recorder()
        i, clk = await self._interp(rec)
        r = await i.send("GO", wait=True)  # -> b
        await i.send("BACK", wait=True)  # -> a (GUARDED/BOOM live here)
        await i.send("GUARDED", wait=True)
        await i.send("NOPE", wait=True)
        await i.send("BOOM", wait=True)
        got = _outcomes(rec)
        self.assertEqual(
            got,
            [
                ("GO", True, False, False, False, None),
                ("BACK", True, False, False, False, None),
                ("GUARDED", False, True, False, False, None),
                ("NOPE", False, False, False, False, None),
                ("BOOM", False, False, False, False, "RuntimeError"),
            ],
        )
        # same fields as the caller's receipt
        self.assertEqual(rec.processed[0][1], r)
        await i.stop()

    async def test_processed_fires_for_timer_events(self):
        rec = Recorder()
        i, clk = await self._interp(rec)
        await i.send("GO", wait=True)
        await clk.increment(101)  # async engine: increment is awaitable
        for _ in range(200):
            await asyncio.sleep(0.005)
            if len(rec.processed) >= 2:
                break
        self.assertEqual(len(rec.processed), 2, _outcomes(rec))
        self.assertTrue(rec.processed[1][0].startswith("after."))
        self.assertTrue(rec.processed[1][1].changed)
        await i.stop()

    async def test_send_events_and_threadsafe_are_intercepted(self):
        rec = Recorder(block="GO")
        i, _ = await self._interp(rec)
        await i.send_events(["GO", "LATER"])
        await asyncio.sleep(0.01)
        self.assertEqual(i.current_state_ids, {"t.c"})
        await i.send("WAIT_FOR_ME", wait=True)  # back to a
        fut = i.send_threadsafe("GO")
        await asyncio.wrap_future(fut)
        await asyncio.sleep(0.01)
        self.assertEqual(i.current_state_ids, {"t.a"})  # blocked
        await i.stop()

    async def test_raising_interceptor_is_fail_open(self):
        bug = Recorder(raise_in_intercept=True)
        watcher = Recorder()
        i, _ = await self._interp(bug, watcher)
        r = await i.send("GO", wait=True)
        self.assertTrue(r.changed)
        self.assertIn("on_before_send:ValueError", watcher.plugin_errors)
        await i.stop()


class TestReceiptShape(unittest.TestCase):
    def test_duplicate_defaults_false_and_positional_unpacking_of_five(self):
        r = Receipt(frozenset({"x"}), True, None, False, False)
        self.assertFalse(r.duplicate)
        ids, changed, err, deferred, denied, dup = r
        self.assertEqual((changed, dup), (True, False))


class TestStubLogic(unittest.TestCase):
    def test_builds_and_records_actions_on_a_corpus_machine(self):
        ran: List[str] = []
        m = create_machine(PAYMENT, logic=stub_logic(PAYMENT, ran=ran))
        i = SyncInterpreter(m).start()
        i.send("SUBMIT")  # guard isFormValid stubbed True; service completes
        self.assertIn("Advance payment flow.challenge", i.current_state_ids)
        i.send("RESET")
        self.assertIn("resetForm", ran)

    def test_guard_mapping_is_live(self):
        guards = {"isFormValid": False}
        m = create_machine(PAYMENT, logic=stub_logic(PAYMENT, guards=guards))
        i = SyncInterpreter(m).start()
        self.assertTrue(i.send("SUBMIT", wait=True).denied)
        guards["isFormValid"] = True
        self.assertTrue(i.send("SUBMIT", wait=True).changed)

    def test_service_results_become_done_data(self):
        cfg = {
            "id": "s",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "fetch",
                        "onDone": {"target": "b", "actions": "keep"},
                    }
                },
                "b": {},
            },
        }
        seen: List[Any] = []
        from src.xstate_statemachine import MachineLogic

        logic = stub_logic(cfg, service_results={"fetch": {"x": 1}})
        logic.actions["keep"] = lambda i, c, e, a: seen.append(e.data)
        i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        self.assertEqual(seen, [{"x": 1}])
        self.assertIn("s.b", i.current_state_ids)

    def test_logic_names_from_config_and_machine_agree_for_corpus(self):
        m = create_machine(PAYMENT, logic=stub_logic(PAYMENT))
        self.assertEqual(logic_names(PAYMENT), logic_names(m))

    def test_every_corpus_and_example_file_builds(self):
        files = sorted(
            list(
                (ROOT / "tests" / "tests_cli" / "stately_machines").glob(
                    "*.json"
                )
            )
            + [
                # 📝 `fixtures/` folders hold recorded payloads (#308's
                #    Stripe webhooks), not charts.
                p
                for p in (ROOT / "examples").rglob("*.json")
                if "fixtures" not in p.parts
            ]
        )
        built, refused = 0, []
        for f in files:
            cfg = json.loads(f.read_text(encoding="utf-8"))
            try:
                create_machine(cfg, logic=stub_logic(cfg))
                built += 1
            except Exception as exc:  # noqa: BLE001
                refused.append((f.name, type(exc).__name__))
        # emailProcessing.json is a known-invalid fixture (bad config), see
        # tests_cli; everything else must build with stubs.
        self.assertGreater(built, 140)
        self.assertEqual([n for n, _ in refused], ["emailProcessing.json"])


if __name__ == "__main__":
    unittest.main()
