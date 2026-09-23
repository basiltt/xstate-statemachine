"""Regression tests for the round-12 re-verification findings (#225–#235).

One class per issue. Every test that involves an action is parametrised
over how it is spelled (``def`` / ``async def``); where an issue is about
engine parity the test runs BOTH engines. `unittest`-based like its
siblings; the parametrisation is `subTest`.
"""

from __future__ import annotations

import asyncio
import contextvars
import copy
import gc
import json
import logging
import pickle
import unittest
import warnings
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine import (
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    ReentrantWaitError,
    RestoredError,
    RunawayChainError,
    SimulatedClock,
    SyncInterpreter,
    UnknownEventError,
    create_machine,
)
from src.xstate_statemachine.events import (
    _engine_after,
    _engine_done,
    _engine_error,
    is_system_event,
)
from src.xstate_statemachine.exceptions import InvalidEventPayloadError
from src.xstate_statemachine.plugins import PluginBase

KINDS: Tuple[str, ...] = ("def", "async def")
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


def _act(kind: str, body: Callable[[Any, Any], None]) -> Callable[..., Any]:
    if kind == "def":

        def plain(i: Any, c: Any, e: Any, a: Any) -> None:
            body(i, c)

        return plain

    async def coro(i: Any, c: Any, e: Any, a: Any) -> None:
        await asyncio.sleep(0)
        body(i, c)

    return coro


def _needs_n(payload: Dict[str, Any]) -> Dict[str, Any]:
    """An `event_schemas` validator: a callable that RAISES to reject."""
    if "n" not in payload:
        raise ValueError("payload needs 'n'")
    return payload


class _InvalidSpy(PluginBase):
    def __init__(self) -> None:
        self.seen: List[Tuple[str, str]] = []

    def on_invalid_event(self, i: Any, exc: Any, raw: Any) -> None:
        self.seen.append((type(exc).__name__, getattr(raw, "type", str(raw))))


# =============================================================================
# #225 — the re-entrant-wait guard asks the LIVENESS question
# =============================================================================
class TestReentrantGuardIsLivenessNotProvenance(_Quiet):
    CFG = {
        "id": "de",
        "initial": "x",
        "states": {"x": {"entry": ["kick"], "on": {"GO": "y"}}, "y": {}},
    }

    def test_worker_spawned_in_an_action_may_wait_after_idle(self) -> None:
        """Lane A: a helper task born in an action outlives it and sends to
        a quiescent machine -- ordinary external traffic, never refused."""
        for kind in KINDS:
            with self.subTest(kind=kind):
                box: Dict[str, Any] = {}

                async def worker(i: Any) -> None:
                    await asyncio.sleep(0.05)  # the machine is idle by now
                    r = await i.send("GO", wait=True)
                    box["err"] = r.error

                def spawn(i: Any, c: Any) -> None:
                    box["task"] = asyncio.ensure_future(worker(i))

                async def go() -> Tuple[Any, str]:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                actions={"kick": _act(kind, spawn)}
                            ),
                        )
                    ).start()
                    await asyncio.wait_for(box["task"], 5)
                    v = i.value
                    await i.stop()
                    return box["err"], v

                self.assertEqual(_run(go()), (None, "y"))

    def test_handing_out_the_receipt_is_fine_whether_or_not_action_yields(
        self,
    ) -> None:
        """Lane B: the documented idiom, parametrised over whether the
        spawning action awaits again afterwards -- the arm the round-11
        pin could not exercise."""
        for action_yields in (False, True):
            with self.subTest(action_yields=action_yields):
                box: Dict[str, Any] = {}

                async def kick(i: Any, c: Any, e: Any, a: Any) -> None:
                    box["h"] = asyncio.ensure_future(i.send("GO", wait=True))
                    if action_yields:
                        await asyncio.sleep(0.02)

                async def go() -> Tuple[Any, str]:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(actions={"kick": kick}),
                        )
                    ).start()
                    r = await asyncio.wait_for(box["h"], 5)
                    v = i.value
                    await i.stop()
                    return r.error, v

                self.assertEqual(_run(go()), (None, "y"))

    def test_in_step_await_is_still_refused(self) -> None:
        """Regression guard: the genuine deadlock is still caught, and
        `start()` still returns."""
        seen: List[BaseException] = []

        async def kick(i: Any, c: Any, e: Any, a: Any) -> None:
            try:
                await i.send("GO", wait=True)
            except ReentrantWaitError as exc:
                seen.append(exc)

        async def go() -> None:
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"kick": kick}))
            )
            await asyncio.wait_for(i.start(), 5)
            await i.stop()

        _run(go())
        self.assertEqual([type(e) for e in seen], [ReentrantWaitError])

    def test_nested_actions_keep_the_counter_balanced(self) -> None:
        """An action that awaits a `send(wait=True)` on ANOTHER interpreter
        whose action in turn spawns a worker: the inner `finally` must not
        zero the outer's liveness count."""
        box: Dict[str, Any] = {}
        inner_cfg = {
            "id": "inner",
            "initial": "p",
            "states": {
                "p": {"on": {"T": {"target": "q", "actions": ["spawn"]}}},
                "q": {},
            },
        }

        async def worker(outer: Any) -> None:
            await asyncio.sleep(0.05)
            box["r"] = await outer.send("GO", wait=True)

        def spawn(i: Any, c: Any, e: Any, a: Any) -> None:
            box["t"] = asyncio.ensure_future(worker(box["outer"]))

        async def kick(i: Any, c: Any, e: Any, a: Any) -> None:
            box["outer"] = i
            await box["inner"].send("T", wait=True)  # other interpreter: fine
            self.assertIn(asyncio.current_task(), i._action_tasks)

        async def go() -> Tuple[Any, str]:
            box["inner"] = await Interpreter(
                _mk(inner_cfg, logic=MachineLogic(actions={"spawn": spawn}))
            ).start()
            outer = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"kick": kick}))
            ).start()
            await asyncio.wait_for(box["t"], 5)
            depth = len(outer._action_tasks)
            v = outer.value
            await outer.stop()
            await box["inner"].stop()
            return (box["r"].error, depth), v

        (err, depth), v = _run(go())
        self.assertEqual((err, depth, v), (None, 0, "y"))

    def test_fresh_context_spawn_still_works(self) -> None:
        """The workaround the reporter shipped keeps working."""
        box: Dict[str, Any] = {}

        async def worker(i: Any) -> None:
            await asyncio.sleep(0.02)
            box["r"] = await i.send("GO", wait=True)

        def kick(i: Any, c: Any, e: Any, a: Any) -> None:
            box["t"] = contextvars.Context().run(
                asyncio.ensure_future, worker(i)
            )

        async def go() -> Any:
            i = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"kick": kick}))
            ).start()
            await asyncio.wait_for(box["t"], 5)
            await i.stop()
            return box["r"].error

        self.assertIsNone(_run(go()))


# =============================================================================
# #232 — a `def` action that drops its wait=True receipt is told so
# =============================================================================
class TestDroppedReceiptWarns(_Quiet):
    CFG = {
        "id": "m",
        "initial": "s1",
        "states": {
            "s1": {"on": {"A": {"target": "s2", "actions": ["act"]}}},
            "s2": {"on": {"B": "s3"}},
            "s3": {"type": "final"},
        },
    }

    def _drive(self, act: Callable[..., Any]) -> List[warnings.WarningMessage]:
        async def go() -> None:
            i = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"act": act}))
            ).start()
            await i.send("A", wait=True)
            await asyncio.sleep(0.02)
            await i.stop()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _run(go())
            gc.collect()
        return [m for m in w if issubclass(m.category, RuntimeWarning)]

    def test_def_action_dropping_the_receipt_gets_a_runtime_warning(
        self,
    ) -> None:
        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("B", wait=True)  # dropped: nothing can await it here

        found = self._drive(act)
        self.assertEqual(len(found), 1, found)
        msg = str(found[0].message)
        self.assertIn("never awaited", msg)
        self.assertIn("'B'", msg)
        self.assertIn("wait=True", msg)

    def test_def_action_handing_the_receipt_out_is_silent(self) -> None:
        box: Dict[str, Any] = {}

        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            box["f"] = asyncio.ensure_future(i.send("B", wait=True))

        self.assertEqual(self._drive(act), [])
        self.assertIsNone(box["f"].result().error)

    def test_def_action_sending_without_wait_is_silent(self) -> None:
        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("B")

        self.assertEqual(self._drive(act), [])

    def test_async_action_awaiting_later_is_silent(self) -> None:
        async def act(i: Any, c: Any, e: Any, a: Any) -> None:
            asyncio.ensure_future(i.send("B", wait=True))
            await asyncio.sleep(0)

        self.assertEqual(self._drive(act), [])


# =============================================================================
# #226 — the chain-trip latch survives a snapshot
# =============================================================================
class TestChainTripLatchIsPersisted(_Quiet):
    CFG = {
        "id": "p1",
        "initial": "a",
        "maxIterations": 3,
        "states": {
            "a": {
                "entry": [{"type": "raise", "params": {"event": "GO"}}],
                "on": {"GO": {"target": "a", "reenter": True}, "CALM": "b"},
            },
            "b": {"on": {"BENIGN": "b"}},
        },
    }

    def _trip_and_snapshot(self, engine: Any) -> Tuple[int, Dict[str, Any]]:
        if engine is SyncInterpreter:
            s = SyncInterpreter(_mk(self.CFG)).start()
            s.send("GO")
            trips, blob = s.chain_trips, s.get_persisted_snapshot()
            s.stop()
            return trips, blob

        async def go() -> Tuple[int, Dict[str, Any]]:
            i = await Interpreter(_mk(self.CFG)).start()
            await i.send("GO", wait=True)
            await asyncio.sleep(0.05)
            out = (i.chain_trips, i.get_persisted_snapshot())
            await i.stop()
            return out

        return _run(go())

    def test_chain_trip_latch_survives_snapshot_round_trip(self) -> None:
        for engine in ENGINES:
            with self.subTest(engine=engine.__name__):
                trips, blob = self._trip_and_snapshot(engine)
                self.assertGreaterEqual(trips, 1)
                self.assertEqual(blob["chain_trips"], trips)
                self.assertIn("exceeded", blob["last_chain_error"])
                r = engine.from_snapshot(json.dumps(blob), _mk(self.CFG))
                self.assertEqual(r.chain_trips, trips)
                self.assertIsInstance(r.last_chain_error, RestoredError)
                self.assertEqual(
                    str(r.last_chain_error), blob["last_chain_error"]
                )
                # and it re-persists identically without start()
                again = r.get_persisted_snapshot()
                self.assertEqual(again["chain_trips"], trips)
                self.assertEqual(
                    again["last_chain_error"], blob["last_chain_error"]
                )

    def test_restored_latch_is_cleared_only_by_clear_chain_error(self) -> None:
        trips, blob = self._trip_and_snapshot(SyncInterpreter)
        blob["configuration"] = ["p1", "p1.b"]
        blob["state_ids"] = ["p1.b"]
        r = SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        r.start()
        for _ in range(3):
            r.send("BENIGN")
        self.assertIsNone(r.last_error)  # the eraser ran
        self.assertIsInstance(r.last_chain_error, RestoredError)  # latch held
        r.clear_chain_error()
        self.assertIsNone(r.last_chain_error)
        self.assertEqual(r.chain_trips, trips)  # the count is not cleared
        r.stop()

    def test_chain_trips_is_monotonic_across_the_restore(self) -> None:
        trips, blob = self._trip_and_snapshot(SyncInterpreter)
        r = SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        r.start()  # entering `a` again re-runs the raise cycle -> a new trip
        r.send("GO")
        self.assertGreaterEqual(r.chain_trips, trips + 1)
        self.assertIsInstance(r.last_chain_error, RunawayChainError)
        r.stop()

    def test_snapshot_without_chain_keys_upcasts_to_zero_and_none(
        self,
    ) -> None:
        for engine in ENGINES:
            with self.subTest(engine=engine.__name__):
                _, blob = self._trip_and_snapshot(engine)
                blob.pop("chain_trips")
                blob.pop("last_chain_error")
                r = engine.from_snapshot(json.dumps(blob), _mk(self.CFG))
                self.assertEqual(
                    (r.chain_trips, r.last_chain_error), (0, None)
                )


# =============================================================================
# #227 — restored scheduled_sends go through the strict / schema check
# =============================================================================
class TestRestoredScheduledSendsAreAdmitted(_Quiet):
    CFG = {
        "id": "p2",
        "initial": "a",
        "strict": True,
        "states": {"a": {"on": {"KNOWN": "b"}}, "b": {}},
    }

    def _blob(self, machine: Any, rec: Dict[str, Any]) -> str:
        s = SyncInterpreter(machine).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["pending_events"] = []
        blob["scheduled_sends"] = [rec]
        return json.dumps(blob)

    def test_restored_scheduled_send_is_refused_by_strict(self) -> None:
        rec = {
            "kind": "event",
            "type": "UNDECLARED_TYPO",
            "payload": {},
            "remaining_ms": 1.0,
            "send_id": "probe",
        }
        for engine in ENGINES:
            with self.subTest(engine=engine.__name__):
                m = _mk(self.CFG)
                spy = _InvalidSpy()
                r = engine.from_snapshot(self._blob(m, rec), m, plugins=[spy])
                if engine is SyncInterpreter:
                    r.start()
                    armed_left = r.get_persisted_snapshot()["scheduled_sends"]
                    err, value = r.last_error, r.value
                    r.stop()
                else:

                    async def go() -> Any:
                        await r.start()
                        await asyncio.sleep(0.05)
                        out = (
                            r.get_persisted_snapshot()["scheduled_sends"],
                            r.last_error,
                            r.value,
                        )
                        await r.stop()
                        return out

                    armed_left, err, value = _run(go())
                self.assertEqual(armed_left, [])
                self.assertIsInstance(err, UnknownEventError)
                self.assertEqual(
                    spy.seen, [("UnknownEventError", "UNDECLARED_TYPO")]
                )
                self.assertEqual(value, "a")  # never reached the run loop

    def test_restored_scheduled_send_honours_event_schema(self) -> None:
        cfg = {**self.CFG, "strict": False}
        m = _mk(cfg, event_schemas={"KNOWN": _needs_n})
        rec = {
            "kind": "event",
            "type": "KNOWN",
            "payload": {},
            "remaining_ms": 1.0,
        }
        spy = _InvalidSpy()
        r = SyncInterpreter.from_snapshot(self._blob(m, rec), m, plugins=[spy])
        r.start()
        self.assertEqual(r.value, "a")
        self.assertIsInstance(r.last_error, InvalidEventPayloadError)
        self.assertEqual(spy.seen, [("InvalidEventPayloadError", "KNOWN")])
        r.stop()

    def test_rearm_returns_the_number_actually_armed(self) -> None:
        m = _mk(self.CFG)
        s = SyncInterpreter(m).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["scheduled_sends"] = [
            {
                "kind": "event",
                "type": "KNOWN",
                "payload": {},
                "remaining_ms": 5.0,
            },
            {
                "kind": "event",
                "type": "NOPE",
                "payload": {},
                "remaining_ms": 5.0,
            },
        ]
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), m, clock=SimulatedClock()
        )
        self.assertEqual(r._rearm_restored_self_sends(), 1)

    def test_genuine_delayed_self_raise_still_rearms_under_strict(
        self,
    ) -> None:
        cfg = {
            "id": "s",
            "initial": "a",
            "strict": True,
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "raise",
                            "params": {"event": "PONG", "delay": 300},
                        }
                    ],
                    "on": {"PONG": "b"},
                },
                "b": {},
            },
        }
        clock = SimulatedClock()
        s = SyncInterpreter(_mk(cfg), clock=clock).start()
        clock.increment(50)
        blob = s.get_persisted_snapshot()
        s.stop()
        self.assertEqual(len(blob["scheduled_sends"]), 1)
        clock2 = SimulatedClock()
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(cfg), clock=clock2
        )
        r.start()
        self.assertIsNone(r.last_error)
        clock2.increment(260)
        self.assertEqual(r.value, "b")
        r.stop()

    def test_pending_events_schema_refusal_no_longer_aborts_the_restore(
        self,
    ) -> None:
        m = _mk(
            {"id": "m", "initial": "w", "states": {"w": {"on": {"GO": "w"}}}},
            event_schemas={"GO": _needs_n},
        )
        s = SyncInterpreter(m).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["pending_events"] = [{"type": "GO", "payload": {}}]
        r = SyncInterpreter.from_snapshot(json.dumps(blob), m)  # no raise
        self.assertIsInstance(r.last_error, InvalidEventPayloadError)
        self.assertEqual(len(r._event_queue), 0)


# =============================================================================
# #230 — from_snapshot(plugins=...)
# =============================================================================
class TestFromSnapshotPlugins(_Quiet):
    CFG = {
        "id": "m",
        "initial": "w",
        "strict": True,
        "states": {"w": {"on": {"GO": "d"}}, "d": {"type": "final"}},
    }

    def _blob(self, m: Any) -> str:
        s = SyncInterpreter(m).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["pending_events"] = [{"type": "UNDECLARED", "payload": {}}]
        return json.dumps(blob)

    def test_from_snapshot_plugins_observe_refusal(self) -> None:
        for engine in ENGINES:
            with self.subTest(engine=engine.__name__):
                m = _mk(self.CFG)
                spy = _InvalidSpy()
                r = engine.from_snapshot(self._blob(m), m, plugins=[spy])
                self.assertEqual(
                    spy.seen, [("UnknownEventError", "UNDECLARED")]
                )
                self.assertIsInstance(r.last_error, UnknownEventError)
                self.assertIs(r.plugins[0], spy)

    def test_plugins_kw_is_optional_and_unchanged_without_it(self) -> None:
        m = _mk(self.CFG)
        r = SyncInterpreter.from_snapshot(self._blob(m), m)
        self.assertEqual(r.plugins, [])
        self.assertIsInstance(r.last_error, UnknownEventError)

    def test_plugins_registered_early_keep_receiving_runtime_hooks(
        self,
    ) -> None:
        """`plugins=` is `.use()` done early: the same instance keeps
        observing the restored machine once it runs."""

        class _Transitions(PluginBase):
            def __init__(self) -> None:
                self.n = 0

            def on_transition(self, i: Any, *a: Any, **k: Any) -> None:
                self.n += 1

        m = _mk({**self.CFG, "strict": False})
        p = _Transitions()
        s = SyncInterpreter(m).start()
        blob = s.get_snapshot()
        s.stop()
        r = SyncInterpreter.from_snapshot(blob, m, plugins=[p]).start()
        r.send("GO")
        self.assertGreaterEqual(p.n, 1)
        self.assertEqual(r.value, "d")
        r.stop()


# =============================================================================
# #233 — the sync engine honours the priority lane on restore
# =============================================================================
class TestSyncRestoreHonoursPriorityLane(_Quiet):
    CFG = {
        "id": "m",
        "initial": "w",
        "context": {"seen": []},
        "states": {
            "w": {
                "on": {
                    "A": {"actions": ["mark"]},
                    "B": {"actions": ["mark"]},
                    "C": {"actions": ["mark"]},
                    "D": {"actions": ["mark"]},
                }
            }
        },
    }

    @staticmethod
    def _mark(i: Any, c: Any, e: Any, a: Any) -> None:
        c["seen"].append(e.type)

    def _blob(self, m: Any, records: List[Dict[str, Any]]) -> str:
        s = SyncInterpreter(m).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["pending_events"] = records
        return json.dumps(blob)

    def test_sync_restore_honours_priority_lane(self) -> None:
        m = _mk(self.CFG, logic=MachineLogic(actions={"mark": self._mark}))
        records = [
            {"type": "A", "payload": {}, "lane": "normal"},
            {"type": "B", "payload": {}, "lane": "priority"},
            {"type": "C", "payload": {}, "lane": "normal"},
            {"type": "D", "payload": {}, "lane": "priority"},
        ]
        r = SyncInterpreter.from_snapshot(self._blob(m, records), m)
        self.assertEqual(
            [e.type for e in r._event_queue], ["B", "D", "A", "C"]
        )
        r.start()
        self.assertEqual(r.context["seen"], ["B", "D", "A", "C"])
        r.stop()

    def test_async_engine_gives_the_same_order(self) -> None:
        m = _mk(self.CFG, logic=MachineLogic(actions={"mark": self._mark}))
        records = [
            {"type": "A", "payload": {}, "lane": "normal"},
            {"type": "B", "payload": {}, "lane": "priority"},
            {"type": "C", "payload": {}, "lane": "normal"},
            {"type": "D", "payload": {}, "lane": "priority"},
        ]

        async def go() -> List[str]:
            r = Interpreter.from_snapshot(self._blob(m, records), m)
            await r.start()
            await asyncio.sleep(0.05)
            out = list(r.context["seen"])
            await r.stop()
            return out

        self.assertEqual(_run(go()), ["B", "D", "A", "C"])

    def test_lane_round_trips_through_the_sync_engine(self) -> None:
        """A restore that is re-persisted keeps the priority records
        first, so a second restore reproduces the order."""
        m = _mk(self.CFG, logic=MachineLogic(actions={"mark": self._mark}))
        records = [
            {"type": "A", "payload": {}, "lane": "normal"},
            {"type": "B", "payload": {}, "lane": "priority"},
        ]
        r = SyncInterpreter.from_snapshot(self._blob(m, records), m)
        again = r.get_persisted_snapshot()["pending_events"]
        self.assertEqual([e["type"] for e in again], ["B", "A"])


# =============================================================================
# #231 — an inline-dict `invoke.src` is refused by name
# =============================================================================
class TestInlineDictInvokeSrcIsNamed(_Quiet):
    def _cfg(self, src: Any) -> Dict[str, Any]:
        return {
            "id": "m",
            "initial": "a",
            "states": {"a": {"invoke": {"id": "kid", "src": src}}},
        }

    def test_inline_dict_invoke_src_is_named(self) -> None:
        inline = {"id": "kid", "initial": "k", "states": {"k": {}}}
        for strict in (False, True):
            with self.subTest(strict_config=strict):
                with self.assertRaises(InvalidConfigError) as cm:
                    _mk(
                        self._cfg(inline),
                        logic=MachineLogic(),
                        strict_config=strict,
                    )
                msg = str(cm.exception)
                self.assertIn("'src'", msg)
                self.assertIn("m.a", msg)
                self.assertIn("kid", msg)
                self.assertIn("dict", msg)
                self.assertIn("create_machine", msg)

    def test_other_non_string_src_values_are_named_too(self) -> None:
        for bad in (42, ["svc"], True):
            with self.subTest(src=bad):
                with self.assertRaises(InvalidConfigError) as cm:
                    _mk(self._cfg(bad), logic=MachineLogic())
                self.assertIn(type(bad).__name__, str(cm.exception))

    def test_string_src_still_builds(self) -> None:
        m = _mk(
            self._cfg("svc"),
            logic=MachineLogic(services={"svc": lambda i, c, e: None}),
            strict_config=True,
        )
        self.assertEqual(m.id, "m")


# =============================================================================
# #235 — engine mint helpers are private; `_replace` demotes to public
# =============================================================================
class TestEngineEventHardening(_Quiet):
    def test_engine_event_replace_downgrades_to_public_class(self) -> None:
        cases = (
            (
                _engine_done("done.invoke.f", {"x": 1}, "f"),
                DoneEvent,
                {"data": {"y": 2}},
            ),
            (
                _engine_error("error.platform.f", RuntimeError("x"), "f"),
                ErrorEvent,
                {"src": "g"},
            ),
            (
                _engine_after("after.10.s", 1.0, None),
                AfterEvent,
                {"fired_at": 2.0},
            ),
        )
        for ev, public, change in cases:
            with self.subTest(kind=public.__name__):
                self.assertTrue(is_system_event(ev))
                out = ev._replace(**change)
                self.assertIs(type(out), public)
                self.assertFalse(is_system_event(out))
                for k, v in change.items():
                    self.assertEqual(getattr(out, k), v)
                self.assertTrue(is_system_event(ev))  # original untouched

    def test_pickle_and_deepcopy_still_preserve_provenance(self) -> None:
        ev = _engine_done("done.invoke.f", {"x": 1}, "f")
        self.assertTrue(is_system_event(copy.deepcopy(ev)))
        self.assertTrue(is_system_event(pickle.loads(pickle.dumps(ev))))

    def test_fired_after_events_keep_engine_provenance_on_both_engines(
        self,
    ) -> None:
        """The engine's own `fired_at` stamp used `_replace`; it must still
        deliver a system event or `strict` would refuse every `after`."""
        cfg = {
            "id": "t",
            "initial": "a",
            "strict": True,
            "states": {"a": {"after": {"10": "b"}}, "b": {}},
        }
        clock = SimulatedClock()
        s = SyncInterpreter(_mk(cfg), clock=clock).start()
        clock.increment(15)
        self.assertEqual((s.value, s.last_error), ("b", None))
        s.stop()

        async def go() -> Tuple[str, Any]:
            c2 = SimulatedClock()
            i = await Interpreter(_mk(cfg), clock=c2).start()
            await c2.increment(15)
            out = (i.value, i.last_error)
            await i.stop()
            return out

        self.assertEqual(_run(go()), ("b", None))

    def test_unprefixed_aliases_warn_and_are_not_used_internally(self) -> None:
        import pathlib

        from src.xstate_statemachine import events

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ev = events.engine_done("done.invoke.k", {}, "k")
        self.assertTrue(is_system_event(ev))
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertIn("_engine_done", str(w[0].message))
        src_dir = pathlib.Path(events.__file__).parent
        for f in src_dir.glob("*.py"):
            if f.name == "events.py":
                continue
            text = f.read_text(encoding="utf-8")
            for name in ("engine_done(", "engine_error(", "engine_after("):
                for line in text.splitlines():
                    if (
                        name in line
                        and "_" + name not in line
                        and not line.lstrip().startswith("#")
                    ):
                        self.fail(
                            f"{f.name}: unprefixed {name} still used: {line.strip()}"
                        )


if __name__ == "__main__":
    unittest.main()
