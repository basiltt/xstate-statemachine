"""Regression tests for the round-11 re-verification findings (#218–#222).

One class per issue. Every test that involves an action is parametrised
over how it is spelled (``def`` / ``async def``); where an issue is about
engine parity the test runs BOTH engines. `unittest`-based like its
siblings; the parametrisation is `subTest`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import unittest
import warnings
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    ReentrantWaitError,
    RunawayChainError,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase
from src.xstate_statemachine.validation import (
    KNOWN_INVOKE_KEYS,
    KNOWN_MACHINE_KEYS,
    KNOWN_ROOT_KEYS,
    KNOWN_STATE_KEYS,
    KNOWN_TRANSITION_KEYS,
)

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


# =============================================================================
# #218 — a delayed self-send's clock handle is released when it fires
# =============================================================================
class TestDelayedSendHandleIsReleased(_Quiet):
    @staticmethod
    def _cfg(period: int) -> Dict[str, Any]:
        arm = {"type": "raise", "params": {"event": "BEAT", "delay": period}}
        return {
            "id": "leak",
            "initial": "up",
            "states": {
                "up": {"entry": [arm, "beat"], "on": {"BEAT": "down"}},
                "down": {"entry": [arm, "beat"], "on": {"BEAT": "up"}},
            },
        }

    def test_async_heartbeat_holds_at_most_one_handle(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                n = {"beats": 0}
                logic = MachineLogic(
                    actions={
                        "beat": _act(
                            kind,
                            lambda i, c: n.__setitem__(
                                "beats", n["beats"] + 1
                            ),
                        )
                    }
                )
                clock = SimulatedClock()

                async def go() -> Tuple[int, int]:
                    i = await Interpreter(
                        _mk(self._cfg(10), logic=logic), clock=clock
                    ).start()
                    for _ in range(200):
                        await clock.increment(10)
                    held = sum(len(v) for v in i._timer_handles.values())
                    await i.stop()
                    return n["beats"], held

                beats, held = _run(go())
                self.assertGreaterEqual(beats, 150)
                # one armed send for the NEXT beat, nothing retained
                self.assertLessEqual(held, 1)

    def test_sync_heartbeat_holds_at_most_one_handle(self) -> None:
        n = {"beats": 0}
        logic = MachineLogic(
            actions={
                "beat": lambda i, c, e, a: n.__setitem__(
                    "beats", n["beats"] + 1
                )
            }
        )
        clock = SimulatedClock()
        s = SyncInterpreter(_mk(self._cfg(10), logic=logic), clock=clock)
        s.start()
        for _ in range(200):
            clock.increment(10)
        held = sum(len(v) for v in s._timer_handles.values())
        s.stop()
        self.assertGreaterEqual(n["beats"], 150)
        self.assertLessEqual(held, 1)

    def test_cancelled_send_releases_its_handle_on_both_engines(self) -> None:
        arm = {
            "type": "raise",
            "params": {"event": "X", "delay": 500, "id": "k"},
        }
        cfg = {
            "id": "c",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [arm],
                    "on": {
                        "CUT": {
                            "actions": [
                                {"type": "cancel", "params": {"sendId": "k"}}
                            ]
                        }
                    },
                }
            },
        }

        def held(i: Any) -> int:
            return sum(len(v) for v in i._timer_handles.values())

        s = SyncInterpreter(_mk(cfg), clock=SimulatedClock()).start()
        self.assertEqual(held(s), 1)
        s.send("CUT")
        self.assertEqual(held(s), 0)
        self.assertEqual(s.get_persisted_snapshot()["scheduled_sends"], [])
        s.stop()

        async def go() -> Tuple[int, int]:
            i = await Interpreter(_mk(cfg), clock=SimulatedClock()).start()
            before = held(i)
            await i.send("CUT", wait=True)
            after = held(i)
            await i.stop()
            return before, after

        self.assertEqual(_run(go()), (1, 0))


# =============================================================================
# #219 — awaiting your own interpreter's receipt from an action is refused
# =============================================================================
class TestReentrantWaitIsRefused(_Quiet):
    CFG = {
        "id": "dead",
        "initial": "x",
        "states": {
            "x": {"entry": ["act"], "on": {"GO": "y"}},
            "y": {},
        },
    }

    def test_async_action_awaiting_own_receipt_raises_not_hangs(self) -> None:
        seen: List[str] = []

        async def act(i: Any, c: Any, e: Any, a: Any) -> None:
            try:
                await i.send("GO", wait=True)
            except ReentrantWaitError as exc:
                seen.append(str(exc))
                raise

        async def go() -> Tuple[str, Any]:
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"act": act}))
            )
            try:
                await asyncio.wait_for(i.start(), 5)
            except ReentrantWaitError:
                pass
            status = i.status
            if i.status == "running":
                await i.stop()
            return status, i.last_error

        status, err = _run(go())
        self.assertEqual(len(seen), 1)
        self.assertIn("GO", seen[0])
        self.assertIn("deadlock", seen[0])
        # whichever way the engine surfaces it, nothing hung and it is named
        self.assertTrue(
            isinstance(err, ReentrantWaitError) or status == "error",
            (status, err),
        )

    def test_handing_out_the_receipt_and_awaiting_later_is_fine(self) -> None:
        box: Dict[str, Any] = {}

        async def act(i: Any, c: Any, e: Any, a: Any) -> None:
            # supported shape (#27): schedule, do not await in-step
            box["fut"] = asyncio.ensure_future(i.send("GO", wait=True))

        async def go() -> Tuple[Any, Any]:
            i = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"act": act}))
            ).start()
            r = await asyncio.wait_for(box["fut"], 5)
            v = i.value
            await i.stop()
            return r.error, v

        self.assertEqual(_run(go()), (None, "y"))

    def test_send_without_wait_from_an_action_still_works(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                logic = MachineLogic(
                    actions={"act": _act(kind, lambda i, c: i.send("GO"))}
                )

                async def go() -> str:
                    i = await Interpreter(_mk(self.CFG, logic=logic)).start()
                    await asyncio.sleep(0.05)
                    v = i.value
                    await i.stop()
                    return v

                self.assertEqual(_run(go()), "y")

    def test_sync_engine_refuses_the_same_shape(self) -> None:
        seen: List[BaseException] = []

        def act(i: Any, c: Any, e: Any, a: Any) -> None:
            try:
                i.send("GO", wait=True)
            except ReentrantWaitError as exc:
                seen.append(exc)

        s = SyncInterpreter(
            _mk(self.CFG, logic=MachineLogic(actions={"act": act}))
        ).start()
        self.assertEqual(len(seen), 1)
        self.assertEqual(s.value, "x")  # the event was never queued
        s.send("GO")
        self.assertEqual(s.value, "y")
        s.stop()

    def test_sync_send_without_wait_from_action_is_queued(self) -> None:
        s = SyncInterpreter(
            _mk(
                self.CFG,
                logic=MachineLogic(
                    actions={"act": lambda i, c, e, a: i.send("GO")}
                ),
            )
        ).start()
        self.assertEqual(s.value, "y")
        s.stop()


# =============================================================================
# #220 — unknown keys are checked in every state, transition and invoke
# =============================================================================
class TestUnknownNestedKeys(_Quiet):
    BASE = {"id": "m", "initial": "a", "states": {"a": {}, "b": {}}}

    LOGIC = MachineLogic(
        actions={"x": lambda i, c, e, a: None},
        guards={"g": lambda c, e: True},
        services={"svc": lambda i, c, e: None},
    )

    def _capture(self, cfg: Dict[str, Any]) -> Tuple[Any, List[str]]:
        cap = _Capture()
        logging.disable(logging.NOTSET)
        lg = logging.getLogger(_PKG_LOGGER)
        lg.addHandler(cap)
        old = lg.level
        lg.setLevel(logging.WARNING)
        try:
            m = _mk(cfg)
        finally:
            lg.removeHandler(cap)
            lg.setLevel(old)
            logging.disable(logging.CRITICAL)
        return m, [r.getMessage() for r in cap.records]

    def test_every_reporter_state_typo_is_refused_under_strict(self) -> None:
        typos = {
            "entyr": ["x"],
            "exti": ["x"],
            "onn": {"GO": "b"},
            "afer": {"10": "b"},
            "alwyas": {"target": "b"},
            "invoek": {"src": "svc"},
            "onDoen": "b",
        }
        for key, val in typos.items():
            with self.subTest(key=key):
                cfg = json.loads(json.dumps(self.BASE))
                cfg["states"]["a"][key] = val
                with self.assertRaises(InvalidConfigError) as cm:
                    _mk(cfg, strict_config=True)
                msg = str(cm.exception)
                self.assertIn(f"'{key}'", msg)
                self.assertIn("m.a", msg)
                self.assertIn("did you mean", msg)

    def test_default_warns_naming_the_state_and_the_key(self) -> None:
        cfg = json.loads(json.dumps(self.BASE))
        cfg["states"]["a"]["entryy"] = ["x"]
        cfg["states"]["a"]["onn"] = {"GO": "b"}
        m, msgs = self._capture(cfg)
        self.assertIsNotNone(m)
        self.assertTrue(
            any(
                "m.a" in s
                and "'entryy'" in s
                and "'onn'" in s
                and "'entry'" in s
                and "'on'" in s
                for s in msgs
            ),
            msgs,
        )

    def test_deeply_nested_and_parallel_regions_are_checked(self) -> None:
        cfg = {
            "id": "m",
            "type": "parallel",
            "states": {
                "r1": {"initial": "x", "states": {"x": {"enrty": ["a"]}}},
                "r2": {
                    "initial": "y",
                    "states": {
                        "y": {
                            "initial": "z",
                            "states": {"z": {"tpye": "final"}},
                        }
                    },
                },
            },
        }
        with self.assertRaises(InvalidConfigError) as cm:
            _mk(cfg, strict_config=True)
        msg = str(cm.exception)
        self.assertIn("m.r1.x: 'enrty'", msg)
        self.assertIn("m.r2.y.z: 'tpye'", msg)

    def test_transition_and_invoke_keys_are_checked(self) -> None:
        cases = {
            "on": {"GO": {"target": "b", "action": ["x"]}},
            "always": [{"target": "b", "gaurd": "g"}],
            "after": {"10": {"target": "b", "reentre": True}},
            "onDone": {"target": "b", "actoins": ["x"]},
            "invoke": {"src": "svc", "onDoen": "b"},
        }
        for key, val in cases.items():
            with self.subTest(key=key):
                cfg = json.loads(json.dumps(self.BASE))
                cfg["states"]["a"][key] = val
                if key == "onDone":
                    cfg["states"]["a"]["initial"] = "f"
                    cfg["states"]["a"]["states"] = {"f": {"type": "final"}}
                with self.assertRaises(InvalidConfigError) as cm:
                    _mk(cfg, logic=self.LOGIC, strict_config=True)
                self.assertIn("did you mean", str(cm.exception))
        # invoke onDone / onError transition bodies too
        cfg = json.loads(json.dumps(self.BASE))
        cfg["states"]["a"]["invoke"] = {
            "src": "svc",
            "onDone": {"target": "b", "actoin": ["x"]},
            "onError": [{"target": "b", "trget": "b"}],
        }
        with self.assertRaises(InvalidConfigError) as cm:
            _mk(cfg, logic=self.LOGIC, strict_config=True)
        self.assertIn("invoke[", str(cm.exception))

    def test_config_level_strict_config_reaches_nested_keys(self) -> None:
        cfg = json.loads(json.dumps(self.BASE))
        cfg["strictConfig"] = True
        cfg["states"]["a"]["entyr"] = ["x"]
        with self.assertRaises(InvalidConfigError):
            _mk(cfg)

    def test_metadata_and_reserved_namespace_allowed_at_every_level(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "x-root": 1,
            "meta": {},
            "states": {
                "a": {
                    "x-owner": "ops",
                    "meta": {"k": 1},
                    "description": "d",
                    "tags": ["t"],
                    "on": {
                        "GO": {
                            "target": "b",
                            "x-note": 1,
                            "meta": {},
                            "description": "d",
                        }
                    },
                    "invoke": {
                        "id": "svc",
                        "src": "svc",
                        "x-owner": "ops",
                        "meta": {},
                        "onDone": {"target": "b", "x-k": 1},
                    },
                },
                "b": {},
            },
        }
        _mk(cfg, logic=self.LOGIC, strict_config=True)  # does not raise

    def test_full_state_grammar_builds_clean_under_strict(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "id": "aa",
                    "entry": ["x"],
                    "exit": ["x"],
                    "on": {
                        "GO": [
                            {
                                "target": "b",
                                "actions": ["x"],
                                "guard": "g",
                                "reenter": True,
                            },
                            {"target": "b", "cond": "g", "internal": False},
                        ],
                        "STAY": None,
                    },
                    "after": {"10": "b", "NAMED": {"target": "b"}},
                    "always": [{"target": "b", "guard": "g"}],
                    "invoke": [
                        {
                            "id": "svc",
                            "src": "svc",
                            "input": {},
                            "systemId": "s",
                            "onDone": "b",
                            "onError": {"target": "b"},
                        }
                    ],
                    "initial": "i",
                    "states": {
                        "i": {"type": "final", "output": {"k": 1}},
                        "h": {
                            "type": "history",
                            "history": "deep",
                            "target": "i",
                        },
                    },
                    "onDone": "b",
                },
                "b": {"type": "final"},
            },
        }
        m = _mk(cfg, logic=self.LOGIC, strict_config=True)
        self.assertEqual(m.id, "m")

    def test_key_sets_are_layered_and_alias_kept(self) -> None:
        self.assertTrue(KNOWN_STATE_KEYS <= KNOWN_ROOT_KEYS)
        self.assertIs(KNOWN_MACHINE_KEYS, KNOWN_ROOT_KEYS)
        self.assertIn("actionErrorPolicy", KNOWN_ROOT_KEYS)
        self.assertNotIn("actionErrorPolicy", KNOWN_STATE_KEYS)
        self.assertIn("cond", KNOWN_TRANSITION_KEYS)
        self.assertIn("systemId", KNOWN_INVOKE_KEYS)

    def test_root_policy_typo_still_reported_as_before(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            _mk(
                {**self.BASE, "actionErrorPolicyy": "rollback"},
                strict_config=True,
            )
        self.assertIn("actionErrorPolicy", str(cm.exception))


# =============================================================================
# #221 — restore then re-persist WITHOUT start() keeps the armed sends
# =============================================================================
class TestRestoreRepersistKeepsScheduledSends(_Quiet):
    CFG = {
        "id": "sla",
        "initial": "a",
        "states": {
            "a": {
                "entry": [
                    {
                        "type": "raise",
                        "params": {
                            "event": "PONG",
                            "delay": 60000,
                            "id": "sla",
                        },
                    },
                    "noop",
                ],
                "on": {"PONG": "b"},
            },
            "b": {},
        },
    }

    def _hop1(self, engine: Any, logic: MachineLogic) -> Dict[str, Any]:
        clock = SimulatedClock()
        if engine is SyncInterpreter:
            s = SyncInterpreter(_mk(self.CFG, logic=logic), clock=clock)
            s.start()
            clock.increment(1000)
            blob = s.get_persisted_snapshot()
            s.stop()
            return blob

        async def snap() -> Any:
            i = await Interpreter(
                _mk(self.CFG, logic=logic), clock=clock
            ).start()
            await clock.increment(1000)
            b = i.get_persisted_snapshot()
            await i.stop()
            return b

        return _run(snap())

    def test_no_start_repersist_round_trips_verbatim(self) -> None:
        for engine in (SyncInterpreter, Interpreter):
            for kind in KINDS:
                with self.subTest(engine=engine.__name__, kind=kind):
                    if engine is SyncInterpreter and kind == "async def":
                        continue
                    logic = MachineLogic(
                        actions={"noop": _act(kind, lambda i, c: None)}
                    )
                    blob = self._hop1(engine, logic)
                    self.assertEqual(len(blob["scheduled_sends"]), 1)
                    self.assertEqual(
                        blob["scheduled_sends"][0]["send_id"], "sla"
                    )
                    self.assertAlmostEqual(
                        blob["scheduled_sends"][0]["remaining_ms"],
                        59000.0,
                        delta=1.0,
                    )
                    # hop 2: restore, do NOT start, re-persist
                    r = engine.from_snapshot(
                        json.dumps(blob), _mk(self.CFG, logic=logic)
                    )
                    blob2 = r.get_persisted_snapshot()
                    self.assertEqual(
                        blob2["scheduled_sends"], blob["scheduled_sends"]
                    )
                    # and a third hop still carries it
                    r2 = engine.from_snapshot(
                        json.dumps(blob2), _mk(self.CFG, logic=logic)
                    )
                    self.assertEqual(
                        r2.get_persisted_snapshot()["scheduled_sends"],
                        blob["scheduled_sends"],
                    )

    def test_started_restore_still_arms_exactly_once(self) -> None:
        logic = MachineLogic(actions={"noop": lambda i, c, e, a: None})
        blob = self._hop1(SyncInterpreter, logic)
        clock = SimulatedClock()
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(self.CFG, logic=logic), clock=clock
        )
        r.start()
        recs = r.get_persisted_snapshot()["scheduled_sends"]
        self.assertEqual(len(recs), 1)  # parked list consumed, live one armed
        self.assertAlmostEqual(recs[0]["remaining_ms"], 59000.0, delta=1.0)
        clock.increment(59000)
        self.assertEqual(r.value, "b")
        self.assertEqual(r.get_persisted_snapshot()["scheduled_sends"], [])
        r.stop()


# =============================================================================
# #222 — a chain trip is sticky
# =============================================================================
class _TripWatcher(PluginBase):
    def __init__(self) -> None:
        self.hits: List[Tuple[str, str]] = []

    def on_chain_budget_exceeded(self, i: Any, error: Any, event: Any) -> None:
        self.hits.append((type(error).__name__, event.type))


class TestChainTripIsSticky(_Quiet):
    MAXIT = 6

    @classmethod
    def _cfg(cls) -> Dict[str, Any]:
        return {
            "id": "trip",
            "initial": "spin",
            "maxIterations": cls.MAXIT,
            "states": {
                "spin": {
                    "entry": [
                        {"type": "raise", "params": {"event": "LAP"}},
                        "bump",
                    ],
                    "on": {
                        "LAP": {"target": "spin", "reenter": True},
                        "BENIGN": {"target": "spin", "reenter": False},
                    },
                }
            },
        }

    def test_async_engine_both_kinds(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                logic = MachineLogic(
                    actions={"bump": _act(kind, lambda i, c: None)}
                )

                async def go() -> Dict[str, Any]:
                    w = _TripWatcher()
                    i = Interpreter(_mk(self._cfg(), logic=logic)).use(w)
                    await i.start()
                    await asyncio.sleep(0.2)
                    at = (
                        i.chain_trips,
                        type(i.last_chain_error).__name__,
                        type(i.last_error).__name__,
                    )
                    for _ in range(3):
                        await i.send("BENIGN", wait=True)
                    after = (
                        i.chain_trips,
                        type(i.last_chain_error).__name__,
                        type(i.last_error).__name__,
                    )
                    hits = list(w.hits)
                    i.clear_chain_error()
                    cleared = (i.chain_trips, i.last_chain_error)
                    await i.stop()
                    return {
                        "at": at,
                        "after": after,
                        "hits": hits,
                        "cleared": cleared,
                    }

                r = _run(go())
                self.assertEqual(
                    r["at"], (1, "RunawayChainError", "RunawayChainError")
                )
                # the eraser ran (last_error is None) but the latch held
                self.assertEqual(
                    r["after"], (1, "RunawayChainError", "NoneType")
                )
                self.assertEqual(r["hits"], [("RunawayChainError", "LAP")])
                self.assertEqual(r["cleared"], (1, None))

    def test_sync_engine(self) -> None:
        w = _TripWatcher()
        s = SyncInterpreter(
            _mk(
                self._cfg(),
                logic=MachineLogic(actions={"bump": lambda i, c, e, a: None}),
            )
        ).use(w)
        s.start()
        self.assertEqual(s.chain_trips, 1)
        self.assertIsInstance(s.last_chain_error, RunawayChainError)
        self.assertIsInstance(s.last_error, RunawayChainError)
        s.send("BENIGN")
        self.assertIsNone(s.last_error)
        self.assertIsInstance(s.last_chain_error, RunawayChainError)
        self.assertEqual(w.hits, [("RunawayChainError", "LAP")])
        s.stop()

    def test_a_new_external_cycle_counts_a_new_trip(self) -> None:
        cfg = {
            "id": "t",
            "initial": "idle",
            "maxIterations": 4,
            "states": {
                "idle": {"on": {"KICK": "spin"}},
                "spin": {
                    "entry": [{"type": "raise", "params": {"event": "LAP"}}],
                    "on": {
                        "LAP": {"target": "spin", "reenter": True},
                        "STOP": "idle",
                    },
                },
            },
        }
        w = _TripWatcher()
        s = SyncInterpreter(_mk(cfg)).use(w).start()
        self.assertEqual(s.chain_trips, 0)
        s.send("KICK")
        self.assertEqual(s.chain_trips, 1)
        s.send("STOP")
        self.assertEqual(s.value, "idle")
        s.send("KICK")
        self.assertEqual(s.chain_trips, 2)
        self.assertEqual(len(w.hits), 2)
        s.stop()

    def test_settle_trip_is_latched_too(self) -> None:
        cfg = {
            "id": "s",
            "initial": "x",
            "maxIterations": 5,
            "states": {
                "x": {"always": {"target": "y"}, "on": {"B": "x"}},
                "y": {"always": {"target": "x"}},
            },
        }
        w = _TripWatcher()
        s = SyncInterpreter(_mk(cfg)).use(w).start()
        self.assertEqual(s.chain_trips, 1)
        self.assertIsInstance(s.last_chain_error, RunawayChainError)
        self.assertEqual(w.hits[0][0], "RunawayChainError")
        s.stop()

        async def go() -> Tuple[int, str]:
            w2 = _TripWatcher()
            i = Interpreter(_mk(cfg)).use(w2)
            await i.start()
            await asyncio.sleep(0.1)
            out = (i.chain_trips, type(i.last_chain_error).__name__)
            await i.stop()
            return out

        self.assertEqual(_run(go()), (1, "RunawayChainError"))


if __name__ == "__main__":
    unittest.main()
