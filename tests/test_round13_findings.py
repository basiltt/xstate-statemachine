"""Regression tests for the round-13 re-verification findings (#239–#248).

One class per issue. Where an issue is about engine parity the test runs
BOTH engines; where an action is involved it is parametrised over how it
is spelled (``def`` / ``async def``). `unittest`-based like its siblings.
"""

from __future__ import annotations

import asyncio
import gc
import importlib.util
import json
import logging
import pathlib
import sys
import unittest
import warnings
from typing import Any, Dict, List, Tuple

from src.xstate_statemachine import (
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Interpreter,
    InterpreterStoppedError,
    MachineLogic,
    OverflowPolicy,
    RestoredChainError,
    RestoredError,
    RunawayChainError,
    SnapshotCorruptError,
    SyncInterpreter,
    create_machine,
    is_system_event,
    re_mint,
)
from src.xstate_statemachine.events import (
    _engine_after,
    _engine_done,
    _engine_error,
)
from src.xstate_statemachine.plugins import PluginBase

ENGINES: Tuple[Any, ...] = (SyncInterpreter, Interpreter)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _run(coro: Any, timeout: float = 30.0) -> Any:
    return asyncio.run(asyncio.wait_for(coro, timeout))


def _mk(cfg: Dict[str, Any], **kw: Any) -> Any:
    return create_machine(json.loads(json.dumps(cfg)), **kw)


def _types(events: Any) -> List[str]:
    return [getattr(e, "type", e) for e in events]


class _Lifecycle(PluginBase):
    def __init__(self) -> None:
        self.seen: List[str] = []

    def on_interpreter_start(self, i: Any) -> None:
        self.seen.append(
            "start:resume" if i.restored_from_snapshot else "start:boot"
        )

    def on_interpreter_stop(self, i: Any) -> None:
        self.seen.append("stop")


# =============================================================================
# #239 — drain_pending() drains BOTH lanes, priority first
# =============================================================================
class TestDrainPendingCoversPriorityLane(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "GO": {"target": "b", "actions": ["slow"]},
                    "P1": "a",
                    "P2": "a",
                    "I1": "a",
                    "I2": "a",
                }
            },
            "b": {"on": {"P1": "b", "P2": "b", "I1": "b", "I2": "b"}},
        },
    }

    async def _park_and_fill(self) -> Any:
        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            await asyncio.sleep(0.4)

        i = await Interpreter(
            _mk(self.CFG, logic=MachineLogic(actions={"slow": slow}))
        ).start()
        await i.send("GO")
        await asyncio.sleep(0.05)  # run loop is parked inside `slow`
        await i.send("I1")
        i.send_priority("P1", wait=False)
        await i.send("I2")
        i.send_priority("P2", wait=False)
        await asyncio.sleep(0.01)
        return i

    def test_drain_returns_every_pending_event_priority_first(self) -> None:
        async def go() -> Tuple[List[str], List[str], List[str], int]:
            i = await self._park_and_fill()
            view = _types(i.pending_events)
            drained = _types(await i.drain_pending())
            after = _types(i.pending_events)
            lane = len(i._priority_queue)
            await i.stop()
            return view, drained, after, lane

        view, drained, after, lane = _run(go())
        self.assertEqual(view, ["P1", "P2", "I1", "I2"])
        self.assertEqual(drained, view)  # same set, same order
        self.assertEqual(after, [])
        self.assertEqual(lane, 0)

    def test_receipt_on_a_drained_priority_event_is_failed_not_hung(
        self,
    ) -> None:
        async def go() -> Tuple[type, List[str]]:
            i = await self._park_and_fill()
            fut = asyncio.ensure_future(i.send("P1", priority=True, wait=True))
            await asyncio.sleep(0.01)
            drained = _types(await i.drain_pending())
            r = await asyncio.wait_for(fut, 2)
            await i.stop()
            return type(r.error), drained

        err_type, drained = _run(go())
        self.assertIs(err_type, InterpreterStoppedError)
        self.assertIn("P1", drained)

    def test_drain_then_stop_loses_nothing_the_recipe_persists(self) -> None:
        """The documented shutdown recipe: drain, persist, stop."""

        async def go() -> Tuple[List[str], List[str]]:
            i = await self._park_and_fill()
            persisted = _types(await i.drain_pending())
            await i.stop()
            return persisted, _types(i.pending_events)

        persisted, left = _run(go())
        self.assertEqual(sorted(persisted), ["I1", "I2", "P1", "P2"])
        self.assertEqual(left, [])

    def test_pre_start_drain_still_works(self) -> None:
        async def go() -> List[str]:
            i = Interpreter(
                _mk(
                    self.CFG,
                    logic=MachineLogic(actions={"slow": lambda *a: None}),
                )
            )
            await i.send("I1")
            out = _types(await i.drain_pending())
            return out

        self.assertEqual(_run(go()), ["I1"])


# =============================================================================
# #240 — on_interpreter_start fires on a restored interpreter
# =============================================================================
class TestStartHookFiresOnRestore(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"GO": "a"}}},
    }

    def _blob(self, engine: Any, with_pending: bool = False) -> str:
        # The layout is engine-independent; mint it on the sync engine so
        # this helper is safe to call from inside a running loop.
        m = _mk(self.CFG)
        s = SyncInterpreter(m).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        if with_pending:
            blob["pending_events"] = [{"type": "GO", "payload": {}}]
        return json.dumps(blob)

    def _drive(self, engine: Any, make: Any) -> List[str]:
        p = _Lifecycle()
        if engine is SyncInterpreter:
            i = make(p)
            i.start()
            i.send("GO")
            i.stop()
            return p.seen

        async def go() -> List[str]:
            i = make(p)
            await i.start()
            await i.send("GO", wait=True)
            await i.stop()
            return p.seen

        return _run(go())

    def test_fresh_start_is_boot_restored_start_is_resume(self) -> None:
        for engine in ENGINES:
            m = _mk(self.CFG)
            with self.subTest(engine=engine.__name__, route="fresh"):
                seen = self._drive(engine, lambda p: engine(m).use(p))
                self.assertEqual(seen, ["start:boot", "stop"])
            for route, make in (
                (
                    "plugins=",
                    lambda p: engine.from_snapshot(
                        self._blob(engine), m, plugins=[p]
                    ),
                ),
                (
                    ".use()",
                    lambda p: engine.from_snapshot(self._blob(engine), m).use(
                        p
                    ),
                ),
                (
                    "pending inbox",
                    lambda p: engine.from_snapshot(
                        self._blob(engine, with_pending=True), m, plugins=[p]
                    ),
                ),
                (
                    "restart_services",
                    lambda p: engine.from_snapshot(
                        self._blob(engine),
                        m,
                        plugins=[p],
                        restart_services=True,
                    ),
                ),
            ):
                with self.subTest(engine=engine.__name__, route=route):
                    seen = self._drive(engine, make)
                    self.assertEqual(seen, ["start:resume", "stop"], route)

    def test_second_start_does_not_fire_twice(self) -> None:
        m = _mk(self.CFG)
        p = _Lifecycle()
        r = SyncInterpreter.from_snapshot(self._blob(SyncInterpreter), m)
        r.use(p)
        r.start()
        r.start()  # idempotent no-op
        self.assertEqual(p.seen, ["start:resume"])
        r.stop()

    def test_restored_from_snapshot_property(self) -> None:
        m = _mk(self.CFG)
        self.assertFalse(SyncInterpreter(m).restored_from_snapshot)
        r = SyncInterpreter.from_snapshot(self._blob(SyncInterpreter), m)
        self.assertTrue(r.restored_from_snapshot)


# =============================================================================
# #241 — malformed chain fields are SnapshotCorruptError
# =============================================================================
class TestChainFieldsAreShapeChecked(_Quiet):
    CFG = {"id": "d13", "initial": "a", "states": {"a": {"on": {"P": "a"}}}}

    def _base(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG)).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        return blob

    def test_malformed_chain_trips_is_corrupt_not_raw(self) -> None:
        base = self._base()
        for bad in ("NaN", [1, 2], {"a": 1}, "1e3", -1, True, 1.5):
            for engine in ENGINES:
                with self.subTest(engine=engine.__name__, chain_trips=bad):
                    blob = {**base, "chain_trips": bad}
                    with self.assertRaises(SnapshotCorruptError) as cm:
                        engine.from_snapshot(json.dumps(blob), _mk(self.CFG))
                    self.assertIn("chain_trips", str(cm.exception))

    def test_malformed_last_chain_error_is_corrupt_not_latched(self) -> None:
        base = self._base()
        for bad in ({"not": "a message"}, [1], 42, True):
            with self.subTest(last_chain_error=bad):
                blob = {**base, "last_chain_error": bad}
                with self.assertRaises(SnapshotCorruptError) as cm:
                    SyncInterpreter.from_snapshot(
                        json.dumps(blob), _mk(self.CFG)
                    )
                self.assertIn("last_chain_error", str(cm.exception))

    def test_well_formed_values_still_restore(self) -> None:
        base = self._base()
        for trips in (0, 3, "12"):
            with self.subTest(chain_trips=trips):
                blob = {**base, "chain_trips": trips, "last_chain_error": "m"}
                r = SyncInterpreter.from_snapshot(
                    json.dumps(blob), _mk(self.CFG)
                )
                self.assertEqual(r.chain_trips, int(trips))
                self.assertEqual(str(r.last_chain_error), "m")
        blob = {**base, "chain_trips": None, "last_chain_error": None}
        r = SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        self.assertEqual((r.chain_trips, r.last_chain_error), (0, None))


# =============================================================================
# #243 — the restored latch IS a RunawayChainError
# =============================================================================
class TestRestoredChainLatchKeepsTheHierarchy(_Quiet):
    CFG = {
        "id": "trip",
        "initial": "spin",
        "maxIterations": 4,
        "states": {
            "spin": {
                "entry": [{"type": "raise", "params": {"event": "LAP"}}],
                "on": {"LAP": {"target": "spin", "reenter": True}},
            }
        },
    }

    def test_isinstance_guard_survives_the_restart_on_both_engines(
        self,
    ) -> None:
        for engine in ENGINES:
            with self.subTest(engine=engine.__name__):
                m = _mk(self.CFG)
                if engine is SyncInterpreter:
                    s = SyncInterpreter(m).start()
                    live = s.last_chain_error
                    blob = s.get_snapshot()
                    s.stop()
                else:

                    async def go() -> Tuple[Any, str]:
                        i = await Interpreter(m).start()
                        await asyncio.sleep(0.05)
                        out = (i.last_chain_error, i.get_snapshot())
                        await i.stop()
                        return out

                    live, blob = _run(go())
                self.assertIsInstance(live, RunawayChainError)
                r = engine.from_snapshot(blob, m)
                restored = r.last_chain_error
                self.assertIsInstance(restored, RunawayChainError)  # #243
                self.assertIsInstance(restored, RestoredError)
                self.assertIsInstance(restored, RestoredChainError)
                self.assertEqual(str(restored), str(live))
                self.assertIsNone(restored.limit)
                self.assertIsNone(restored.dropped)
                self.assertEqual(restored.stranded, ())
                self.assertGreaterEqual(r.chain_trips, 1)

    def test_error_field_is_still_a_plain_restored_error(self) -> None:
        """`RestoredChainError` is for the chain latch only; the generic
        `error` field keeps its 0.7.x type."""
        cfg = {"id": "e", "initial": "a", "states": {"a": {}}}
        s = SyncInterpreter(_mk(cfg)).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["status"] = "error"
        blob["error"] = "boom"
        r = SyncInterpreter.from_snapshot(json.dumps(blob), _mk(cfg))
        self.assertIs(type(r.error), RestoredError)


# =============================================================================
# #244 — a dropped receipt is observable deterministically
# =============================================================================
class TestDroppedReceiptIsCountable(_Quiet):
    CFG = {
        "id": "m",
        "initial": "s1",
        "states": {
            "s1": {"on": {"A": {"target": "s2", "actions": ["act"]}}},
            "s2": {"on": {"B": "s3"}},
            "s3": {"type": "final"},
        },
    }

    class _Spy(PluginBase):
        def __init__(self) -> None:
            self.dropped: List[str] = []

        def on_receipt_dropped(self, i: Any, event_type: str) -> None:
            self.dropped.append(event_type)

    def _drive(self, act: Any) -> Tuple[int, List[str], str]:
        spy = self._Spy()

        async def go() -> Tuple[int, List[str], str]:
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"act": act}))
            ).use(spy)
            await i.start()
            await i.send("A", wait=True)
            await asyncio.sleep(0.02)
            gc.collect()
            out = (i.dropped_receipts, list(spy.dropped), i.status)
            await i.stop()
            return out

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return _run(go())

    def test_counter_and_hook_fire_once_per_dropped_receipt(self) -> None:
        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("B", wait=True)  # dropped

        count, dropped, status = self._drive(act)
        self.assertEqual((count, dropped), (1, ["B"]))
        # transition logic unaffected: the dropped-receipt send still ran,
        # B drove the machine to its final state
        self.assertEqual(status, "done")

    def test_used_receipts_are_not_counted(self) -> None:
        box: Dict[str, Any] = {}

        def hand_out(i: Any, c: Any, e: Any, a: Any) -> None:
            box["f"] = asyncio.ensure_future(i.send("B", wait=True))

        def no_wait(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("B")

        async def awaited_later(i: Any, c: Any, e: Any, a: Any) -> None:
            asyncio.ensure_future(i.send("B", wait=True))
            await asyncio.sleep(0)

        for act in (hand_out, no_wait, awaited_later):
            with self.subTest(shape=act.__name__):
                count, dropped, _ = self._drive(act)
                self.assertEqual((count, dropped), (0, []))

    def test_counter_is_gateable_without_warning_filters(self) -> None:
        """The whole point: assertable under any -W setting."""

        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("B", wait=True)

        with warnings.catch_warnings():
            warnings.simplefilter("error")  # -W error
            count, _, _ = self._drive(act)
        self.assertEqual(count, 1)


# =============================================================================
# #245 — SyncInterpreter refuses an inbox bound by contract
# =============================================================================
class TestSyncInterpreterHasNoInboxBound(_Quiet):
    CFG = {"id": "m", "initial": "a", "states": {"a": {"on": {"T": "a"}}}}

    def test_bound_is_a_documented_value_error(self) -> None:
        with self.assertRaises(ValueError) as cm:
            SyncInterpreter(_mk(self.CFG), max_queue_size=4)
        self.assertIn("no inbox to bound", str(cm.exception))
        self.assertIn("wrapper", str(cm.exception))

    def test_parity_keywords_with_none_are_accepted(self) -> None:
        s = SyncInterpreter(
            _mk(self.CFG),
            max_queue_size=None,
            overflow_policy=OverflowPolicy.RAISE,
        ).start()
        for _ in range(40):
            s.send("T")
        self.assertEqual(s.status, "running")
        s.stop()


# =============================================================================
# #246 — the benchmark script emits JSON
# =============================================================================
class TestBenchmarkJson(_Quiet):
    def _module(self) -> Any:
        path = (
            pathlib.Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "production_characteristics.py"
        )
        # The script imports the INSTALLED package name; make the source
        # tree importable under it so this works in an un-installed checkout.
        src = str(path.parents[1] / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        spec = importlib.util.spec_from_file_location("prodchar", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["prodchar"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_host_info_has_the_documented_keys(self) -> None:
        mod = self._module()
        host = mod.host_info()
        for k in (
            "library_version",
            "python_version",
            "platform",
            "processor",
            "cpu_count",
            "method",
        ):
            self.assertIn(k, host)
        json.dumps(host)  # serialisable

    def test_argparse_accepts_json_flags(self) -> None:
        mod = self._module()
        a = mod.parse_args(["--quick", "--json", "--json-file", "x.json"])
        self.assertTrue(a.quick and a.json)
        self.assertEqual(a.json_file, "x.json")

    def test_sections_return_structured_rows(self) -> None:
        """A tiny run of §1 at N=1 through the real machinery."""
        mod = self._module()
        rate = _run(mod.aggregate_throughput(1, 50))
        self.assertGreater(rate, 0)
        late = _run(mod.timer_error_ms(0, quick=True))
        self.assertIsInstance(late, float)


# =============================================================================
# #248 — re_mint(): the sanctioned provenance-preserving patch
# =============================================================================
class TestReMint(_Quiet):
    def test_re_mint_keeps_provenance_and_patches_the_field(self) -> None:
        cases = (
            (
                _engine_done("done.invoke.f", {"secret": 1}, "f"),
                {"data": {"ok": 1}},
            ),
            (
                _engine_error("error.platform.f", RuntimeError("x"), "f"),
                {"src": "g"},
            ),
            (_engine_after("after.10.s", 1.0, None), {"fired_at": 2.0}),
        )
        for ev, change in cases:
            with self.subTest(kind=type(ev).__name__):
                out = re_mint(ev, **change)
                self.assertIs(type(out), type(ev))
                self.assertTrue(is_system_event(out))
                for k, v in change.items():
                    self.assertEqual(getattr(out, k), v)
                self.assertTrue(is_system_event(ev))  # original untouched
                self.assertNotEqual(out, ev)

    def test_re_mint_refuses_user_and_demoted_events(self) -> None:
        hand_built = DoneEvent("done.invoke.f", {}, "f")
        demoted = _engine_done("done.invoke.f", {}, "f")._replace(
            data={"x": 1}
        )
        for bad in (
            hand_built,
            demoted,
            AfterEvent("after.1.x"),
            ErrorEvent("e", RuntimeError(), "s"),
            "GO",
        ):
            with self.subTest(value=type(bad).__name__):
                with self.assertRaises(TypeError) as cm:
                    re_mint(bad, data={})
                self.assertIn("engine minted", str(cm.exception))

    def test_replace_is_still_a_one_way_demotion(self) -> None:
        ev = _engine_done("done.invoke.f", {}, "f")
        self.assertFalse(is_system_event(ev._replace(data={"y": 2})))

    def test_re_minted_event_is_accepted_by_strict_machine(self) -> None:
        """End to end: a plugin patches a completion and re-sends it under
        `strict`, where a demoted copy would have been refused."""
        cfg = {
            "id": "m",
            "initial": "a",
            "strict": True,
            "states": {
                "a": {"invoke": {"id": "svc", "src": "svc", "onDone": "b"}},
                "b": {"on": {"done.invoke.svc": "c"}},
                "c": {},
            },
        }
        seen: Dict[str, Any] = {}

        class _Capture(PluginBase):
            def on_event_received(self, i: Any, event: Any) -> None:
                if getattr(event, "type", "") == "done.invoke.svc":
                    seen.setdefault("ev", event)

        s = (
            SyncInterpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(services={"svc": lambda i, c, e: 1}),
                )
            )
            .use(_Capture())
            .start()
        )
        self.assertEqual(s.value, "b")
        patched = re_mint(seen["ev"], data={"redacted": True})
        s.send(patched)  # engine provenance: accepted under strict
        self.assertEqual(s.value, "c")
        s.stop()


if __name__ == "__main__":
    unittest.main()
