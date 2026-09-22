"""Regression tests for the round-10 re-verification findings (#212–#216).

One class per issue. Every test that involves a service or an action is
parametrised over how it is spelled (``def`` / ``async def``); where an
issue is about engine parity the test runs BOTH engines. `unittest`-based
like its siblings; the parametrisation is `subTest`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import unittest
import warnings
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine import (
    InvalidConfigError,
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SimulatedClock,
    SyncInterpreter,
    UnknownEventError,
    create_machine,
)
from src.xstate_statemachine.events import engine_after, persist_event
from src.xstate_statemachine.persistence import SNAPSHOT_VERSION
from src.xstate_statemachine.plugins import PluginBase
from src.xstate_statemachine.validation import KNOWN_MACHINE_KEYS

_PKG_LOGGER = SyncInterpreter.__module__.rsplit(".", 1)[0]
KINDS: Tuple[str, ...] = ("def", "async def")


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


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _Invalid(PluginBase):
    def __init__(self) -> None:
        self.seen: List[str] = []

    def on_invalid_event(self, interp: Any, error: Any, raw: Any) -> None:
        self.seen.append(type(error).__name__)


# =============================================================================
# #212 — a raise(delay=) heartbeat is a timer, not a chain (see round 9's
# TestDelayedSelfSendIsATimer for the full matrix; this pins the reporter's
# exact cells)
# =============================================================================
class TestRaiseDelayHeartbeatSurvivesMaxIterations(_Quiet):
    def test_reporter_cells(self) -> None:
        def raise_cfg(p: int) -> Dict[str, Any]:
            arm = {"type": "raise", "params": {"event": "BEAT", "delay": p}}
            return {
                "id": "hb",
                "initial": "up",
                "maxIterations": 8,
                "context": {"n": 0},
                "states": {
                    "up": {"entry": [arm, "beat"], "on": {"BEAT": "down"}},
                    "down": {"entry": [arm, "beat"], "on": {"BEAT": "up"}},
                },
            }

        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            raise_cfg(30),
                            logic=MachineLogic(
                                actions={
                                    "beat": _act(
                                        kind,
                                        lambda i, c: c.__setitem__(
                                            "n", c["n"] + 1
                                        ),
                                    )
                                }
                            ),
                        )
                    ).start()
                    await asyncio.sleep(1.5)
                    out = (i.context["n"], i.last_error)
                    await i.stop()
                    return out

                n, err = _run(main())
                self.assertGreaterEqual(n, 30)  # >> maxIterations + 1
                self.assertIsNone(err)


# =============================================================================
# #213 — an armed, unfired delayed self-send survives a snapshot
# =============================================================================
class TestArmedSelfSendSurvivesSnapshot(_Quiet):
    CFG = {
        "id": "debt",
        "initial": "a",
        "context": {},
        "states": {
            "a": {
                "entry": [
                    {
                        "type": "raise",
                        "params": {"event": "PONG", "delay": 300},
                    },
                    "noop",
                ],
                "on": {"PONG": "b"},
            },
            "b": {},
        },
    }

    def test_snapshot_records_the_debt_and_restore_progresses(self) -> None:
        for engine in (SyncInterpreter, Interpreter):
            for kind in KINDS:
                if engine is SyncInterpreter and kind == "async def":
                    continue
                with self.subTest(engine=engine.__name__, kind=kind):
                    logic = MachineLogic(
                        actions={"noop": _act(kind, lambda i, c: None)}
                    )
                    clock = SimulatedClock()
                    if engine is SyncInterpreter:
                        s = SyncInterpreter(
                            _mk(self.CFG, logic=logic), clock=clock
                        ).start()
                        clock.increment(50)
                        blob = s.get_persisted_snapshot()
                        s.stop()
                    else:

                        async def snap() -> Any:
                            i = await Interpreter(
                                _mk(self.CFG, logic=logic), clock=clock
                            ).start()
                            await clock.increment(50)
                            b = i.get_persisted_snapshot()
                            await i.stop()
                            return b

                        blob = _run(snap())
                    recs = blob["scheduled_sends"]
                    self.assertEqual(len(recs), 1)
                    self.assertEqual(recs[0]["type"], "PONG")
                    self.assertAlmostEqual(
                        recs[0]["remaining_ms"], 250.0, delta=1.0
                    )
                    self.assertEqual(blob["pending_events"], [])

                    clock2 = SimulatedClock()
                    if engine is SyncInterpreter:
                        r = SyncInterpreter.from_snapshot(
                            json.dumps(blob),
                            _mk(self.CFG, logic=logic),
                            clock=clock2,
                        ).start()
                        clock2.increment(200)
                        self.assertEqual(r.value, "a")
                        clock2.increment(60)
                        self.assertEqual(r.value, "b")
                        self.assertEqual(
                            r.get_persisted_snapshot()["scheduled_sends"], []
                        )
                        r.stop()
                    else:

                        async def restore() -> Any:
                            r = Interpreter.from_snapshot(
                                json.dumps(blob),
                                _mk(self.CFG, logic=logic),
                                clock=clock2,
                            )
                            await r.start()
                            await clock2.increment(200)
                            v1 = r.value
                            await clock2.increment(60)
                            v2 = r.value
                            left = r.get_persisted_snapshot()[
                                "scheduled_sends"
                            ]
                            await r.stop()
                            return v1, v2, left

                        self.assertEqual(_run(restore()), ("a", "b", []))

    def test_cancelled_send_leaves_no_record(self) -> None:
        cfg = {
            "id": "c",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "raise",
                            "params": {"event": "X", "delay": 500, "id": "k"},
                        },
                        {"type": "cancel", "params": {"sendId": "k"}},
                    ]
                }
            },
        }
        s = SyncInterpreter(_mk(cfg)).start()
        self.assertEqual(s.get_persisted_snapshot()["scheduled_sends"], [])

    def test_external_delayed_send_still_survives(self) -> None:
        # A delayed send issued from OUTSIDE an action is persisted too.
        cfg = {
            "id": "e",
            "initial": "a",
            "states": {"a": {"on": {"X": "b"}}, "b": {}},
        }
        clock = SimulatedClock()
        s = SyncInterpreter(_mk(cfg), clock=clock).start()
        s._deliver_sync(s, s._prepare_event("X"), 100, None)
        blob = s.get_persisted_snapshot()
        self.assertEqual([r["type"] for r in blob["scheduled_sends"]], ["X"])
        clock2 = SimulatedClock()
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(cfg), clock=clock2
        ).start()
        clock2.increment(110)
        self.assertEqual(r.value, "b")


# =============================================================================
# #214 — the restore path applies strict, keeps legacy after deadlines, lanes
# =============================================================================
class TestRestorePathStrictAndLegacy(_Quiet):
    CFG = {
        "id": "t",
        "initial": "wait",
        "strict": True,
        "context": {"fired": 0},
        "states": {
            "wait": {
                "after": {60000: {"target": "done", "actions": ["mark"]}},
                "on": {"KNOWN": {}},
            },
            "done": {},
        },
    }

    def _logic(self) -> MachineLogic:
        return MachineLogic(
            actions={"mark": lambda i, c, e, a: c.__setitem__("fired", 1)}
        )

    def _blob(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        b = s.get_persisted_snapshot()
        s.stop()
        return b

    def test_restore_applies_strict_to_restored_events(self) -> None:
        blob = self._blob()
        blob["pending_events"] = [
            {"kind": "event", "type": "BOGUS", "payload": {}}
        ]
        for engine in (SyncInterpreter, Interpreter):
            with self.subTest(engine=engine.__name__):
                plug = _Invalid()
                r = engine.from_snapshot(
                    json.dumps(blob), _mk(self.CFG, logic=self._logic())
                )
                r.use(plug)
                # the refusal is recorded at restore time
                self.assertIsInstance(r.last_error, UnknownEventError)
                self.assertFalse(r.last_transition_ok)
                self.assertEqual(list(r.pending_events), [])

    def test_pre_081_after_record_is_upcast_and_fires(self) -> None:
        # A v2 (0.8.0-era) record: kind=after, no `engine` flag.
        blob = self._blob()
        blob["version"] = 2
        blob["pending_events"] = [
            {
                "kind": "after",
                "type": "after.60000.t.wait",
                "scheduled_for": 1.0,
                "fired_at": 61.0,
            }
        ]
        for engine in (SyncInterpreter, Interpreter):
            with self.subTest(engine=engine.__name__):
                r = engine.from_snapshot(
                    json.dumps(blob), _mk(self.CFG, logic=self._logic())
                )
                if engine is SyncInterpreter:
                    r.start()
                    self.assertEqual(
                        (r.value, r.context["fired"]), ("done", 1)
                    )
                    r.stop()
                else:

                    async def main(r: Any = r) -> Any:
                        await r.start()
                        await asyncio.sleep(0.05)
                        out = (r.value, r.context["fired"])
                        await r.stop()
                        return out

                    self.assertEqual(_run(main()), ("done", 1))

    def test_v3_record_without_engine_flag_is_user_traffic(self) -> None:
        # A CURRENT-version hand-written record stays untrusted (#203).
        blob = self._blob()
        self.assertEqual(blob["version"], SNAPSHOT_VERSION)
        blob["strict"] = False
        cfg = json.loads(json.dumps(self.CFG))
        cfg["strict"] = False
        blob["pending_events"] = [
            {"kind": "after", "type": "after.60000.t.wait"}
        ]
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(cfg, logic=self._logic())
        ).start()
        self.assertEqual((r.value, r.context["fired"]), ("wait", 0))

    def test_priority_lane_round_trips(self) -> None:
        cfg = {
            "id": "p",
            "initial": "a",
            "context": {"order": []},
            "states": {
                "a": {
                    "on": {
                        "FIRST": {"actions": ["rec"]},
                        "SECOND": {"actions": ["rec"]},
                    }
                }
            },
        }
        logic = MachineLogic(
            actions={"rec": lambda i, c, e, a: c["order"].append(e.type)}
        )

        async def main() -> Any:
            i = Interpreter(_mk(cfg, logic=logic))
            await i.start()
            # freeze the loop, queue one inbox item and one lane item
            i._event_loop_task.cancel()
            try:
                await i._event_loop_task
            except asyncio.CancelledError:
                pass
            i.status = "running"
            i._put_inbox(i._prepare_event("SECOND"))
            i._deliver_priority(
                engine_after("FIRST", 0.0, 0.0), engine_completion=True
            )
            i._deliver_priority(i._prepare_event("FIRST"))  # external priority
            blob = i.get_persisted_snapshot()
            lanes = [r.get("lane") for r in blob["pending_events"]]
            r = Interpreter.from_snapshot(
                json.dumps(blob), _mk(cfg, logic=logic)
            )
            restored_lane = [ev.type for ev, _ in r._priority_queue]
            await r.start()
            await asyncio.sleep(0.05)
            out = (lanes, restored_lane, r.context["order"])
            await r.stop()
            return out

        lanes, restored_lane, order = _run(main())
        self.assertEqual(lanes, ["priority", "priority", None])
        self.assertEqual(restored_lane, ["FIRST", "FIRST"])
        self.assertEqual(
            order[-1], "SECOND", "lane items processed ahead of the inbox"
        )


# =============================================================================
# #215 — three-lane lap parity on an engine-work-only chart
# =============================================================================
class TestLapParityOnEngineWorkOnlyChart(_Quiet):
    @staticmethod
    def _cfg(mi: int) -> Dict[str, Any]:
        return {
            "id": "w",
            "initial": "a",
            "maxIterations": mi,
            "states": {
                "a": {
                    "entry": [
                        {"type": "raise", "params": {"event": "GO"}},
                        "tick",
                    ],
                    "on": {"GO": "b"},
                },
                "b": {"always": "a", "entry": ["tick"]},
            },
        }

    def test_always_plus_raise_cycle_identical_on_all_lanes(self) -> None:
        for mi in (1, 3, 5, 10, 15, 19, 25):
            n = [0]

            def bump(i: Any, c: Any) -> None:
                n[0] += 1

            s = SyncInterpreter(
                _mk(
                    self._cfg(mi),
                    logic=MachineLogic(actions={"tick": _act("def", bump)}),
                )
            ).start()
            sync_n = n[0]
            self.assertIsInstance(s.last_error, RunawayChainError)
            for kind in KINDS:
                with self.subTest(limit=mi, kind=kind):
                    n[0] = 0

                    async def main() -> Any:
                        i = await Interpreter(
                            _mk(
                                self._cfg(mi),
                                logic=MachineLogic(
                                    actions={"tick": _act(kind, bump)}
                                ),
                            )
                        ).start()
                        await asyncio.sleep(0.3)
                        out = (n[0], type(i.last_error))
                        await i.stop()
                        return out

                    laps, err = _run(main())
                    self.assertEqual(laps, sync_n)
                    self.assertIs(err, RunawayChainError)

    def test_run_loop_does_not_interleave_the_initial_descent(self) -> None:
        # An `async def` entry action yields; the loop must not consume the
        # descent's own raise mid-descent (the mechanism behind #215).
        order: List[str] = []
        cfg = {
            "id": "d",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {"type": "raise", "params": {"event": "GO"}},
                        "slow",
                    ],
                    "on": {"GO": "b"},
                },
                "b": {"entry": ["mark_b"]},
            },
        }

        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            order.append("slow-start")
            await asyncio.sleep(0.02)
            order.append("slow-end")

        async def main() -> None:
            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        actions={
                            "slow": slow,
                            "mark_b": lambda i, c, e, a: order.append(
                                "enter-b"
                            ),
                        }
                    ),
                )
            ).start()
            await asyncio.sleep(0.05)
            await i.stop()

        _run(main())
        self.assertEqual(order, ["slow-start", "slow-end", "enter-b"])


# =============================================================================
# #216 — unknown top-level config keys
# =============================================================================
class TestUnknownTopLevelKeys(_Quiet):
    BASE = {"id": "m", "initial": "a", "states": {"a": {}}}

    def test_default_warns_with_hint(self) -> None:
        cap = _Capture()
        logging.disable(logging.NOTSET)
        lg = logging.getLogger(_PKG_LOGGER)
        lg.addHandler(cap)
        old = lg.level
        lg.setLevel(logging.WARNING)
        try:
            m = _mk({**self.BASE, "actionErrorPolicyy": "rollback"})
        finally:
            lg.removeHandler(cap)
            lg.setLevel(old)
            logging.disable(logging.CRITICAL)
        self.assertEqual(m.action_error_policy, "continue")  # dropped
        msgs = [r.getMessage() for r in cap.records]
        self.assertTrue(
            any(
                "actionErrorPolicyy" in m and "actionErrorPolicy" in m
                for m in msgs
            ),
            msgs,
        )

    def test_strict_config_refuses_every_reporter_typo(self) -> None:
        typos = {
            "spawnBlockingTimeoutMs": 1234,
            "actionErrorPolicyy": "rollback",
            "guardErrorPolicies": "raise",
            "maxIteration": 42,
            "onUnhandledEvent": "error",
            "Strict": True,
        }
        for key, val in typos.items():
            with self.subTest(key=key):
                with self.assertRaises(InvalidConfigError) as cm:
                    _mk({**self.BASE, key: val}, strict_config=True)
                self.assertIn(key, str(cm.exception))

    def test_config_level_strict_config_key(self) -> None:
        with self.assertRaises(InvalidConfigError):
            _mk({**self.BASE, "strictConfig": True, "maxIteration": 42})
        _mk({**self.BASE, "strictConfig": True})  # itself known

    def test_reserved_namespace_and_metadata_always_allowed(self) -> None:
        m = _mk(
            {
                **self.BASE,
                "x-team": "ops",
                "meta": {"k": 1},
                "description": "d",
                "tags": ["a"],
                "version": "1.2",
            },
            strict_config=True,
        )
        self.assertEqual(m.id, "m")

    def test_known_set_covers_every_key_the_parser_reads(self) -> None:
        # A correct-key config with every policy set builds clean under strict.
        full = {
            **self.BASE,
            "actionErrorPolicy": "rollback",
            "guardErrorPolicy": "raise",
            "onUnhandled": "error",
            "maxIterations": 42,
            "spawnBlockingTimeout": 1234,
            "strict": True,
            "strictTargets": True,
            "context": {},
            "output": None,
        }
        m = _mk(full, strict_config=True)
        self.assertEqual(
            (m.action_error_policy, m.max_iterations, m.strict),
            ("rollback", 42, True),
        )
        for k in full:
            self.assertIn(k, KNOWN_MACHINE_KEYS)


if __name__ == "__main__":
    unittest.main()
