"""Regression tests for the round-5 re-verification findings (#142–#162 and
the reopened #118 / #122 / #125 / #133 / #134).

One class per issue. Each test is the reporter's acceptance criterion in
miniature, so a future regression names the issue it reopens. Where an
issue is about engine parity the test runs BOTH engines.
"""

from __future__ import annotations

import asyncio
import contextvars
import copy
import io
import json
import logging
import threading
import time
import unittest
import warnings
from typing import Any, Dict, List

from src.xstate_statemachine import (
    AfterEvent,
    Event,
    Interpreter,
    InvalidConfigError,
    InvalidEventError,
    MachineLogic,
    OverflowPolicy,
    QueueOverflowError,
    RootTargetError,
    RunawayChainError,
    SimulatedClock,
    SnapshotCorruptError,
    SnapshotMidStepError,
    SnapshotSerializationError,
    SyncInterpreter,
    TransitionFailedError,
    create_machine,
    is_system_event,
)
from src.xstate_statemachine.events import persist_event, restore_event
from src.xstate_statemachine.exceptions import XStateMachineError
from src.xstate_statemachine.plugins import (
    DEFAULT_REDACT_KEYS,
    PluginBase,
    redact,
)

#: The package's logger root as IMPORTED here (tests import via `src.`).
_PKG_LOGGER = SyncInterpreter.__module__.rsplit(".", 1)[0]


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _run(coro, timeout: float = 20):
    return asyncio.run(asyncio.wait_for(coro, timeout))


def _mk(cfg: Dict[str, Any], **kw: Any):
    return create_machine(json.loads(json.dumps(cfg)), **kw)


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.dropped: List = []

    def on_event_dropped(self, interp, event, reason):
        self.dropped.append((getattr(event, "type", event), reason))


# =============================================================================
# #118 — absent AfterEvent telemetry restores as None, never 0.0
# =============================================================================
class TestAfterEventTelemetryNone(_Quiet):
    def test_missing_keys_restore_as_none(self) -> None:
        r = restore_event({"kind": "after", "type": "after.5000.o.p"})
        self.assertIsNone(r.scheduled_for)
        self.assertIsNone(r.fired_at)
        self.assertIsNone(r.lateness_ms)

    def test_present_keys_round_trip_exactly(self) -> None:
        e = AfterEvent("after.5.m.a", scheduled_for=1.25, fired_at=1.5)
        back = restore_event(json.loads(json.dumps(persist_event(e))))
        self.assertEqual((1.25, 1.5), (back.scheduled_for, back.fired_at))
        self.assertAlmostEqual(250.0, back.lateness_ms or -1)


# =============================================================================
# #122 — tick() contract is documented (drains what is DUE, does not advance)
# =============================================================================
class TestTickContractDocumented(_Quiet):
    def test_docstring_states_the_contract(self) -> None:
        doc = SyncInterpreter.tick.__doc__ or ""
        self.assertIn("does NOT advance", doc)
        self.assertIn("SimulatedClock", doc)

    def test_simulated_clock_settles_a_real_delay_ladder(self) -> None:
        cfg = {
            "id": "o",
            "initial": "s",
            "states": {
                "s": {"after": {50: "a"}},
                "a": {"after": {50: "r"}},
                "r": {"after": {50: "e"}},
                "e": {},
            },
        }
        clock = SimulatedClock()
        i = SyncInterpreter(_mk(cfg), clock=clock).start()
        clock.increment(250)
        self.assertEqual({"o.e"}, i.current_state_ids)


# =============================================================================
# #125 — sync: deferred replay is its own macrostep, receipt is the caller's
# =============================================================================
class TestSyncReplayIsOwnMacrostep(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "onUnhandled": "defer",
        "states": {
            "a": {"on": {"ARM": "b"}},
            "b": {"on": {"LATE": "c"}},
            "c": {},
        },
    }

    def test_arm_receipt_reports_arm_only_then_replay_lands(self) -> None:
        i = SyncInterpreter(_mk(self.CFG)).start()
        self.assertTrue(i.send("LATE", wait=True).deferred)
        r = i.send("ARM", wait=True)
        self.assertEqual({"m.b"}, set(r.state_ids))
        # ...and the replay DID run, as its own step, right after.
        self.assertEqual({"m.c"}, i.current_state_ids)

    def test_send_events_and_tick_also_run_held_replays(self) -> None:
        i = SyncInterpreter(_mk(self.CFG)).start()
        i.send_events(["LATE", "ARM"])
        self.assertEqual({"m.c"}, i.current_state_ids)


# =============================================================================
# #133 — forwardTo shares sendTo's unresolved-target reporting
# =============================================================================
class TestForwardToUnresolved(_Quiet):
    def _cfg(self, action: str):
        return {
            "id": "m",
            "initial": "s",
            "states": {
                "s": {
                    "on": {
                        "GO": {
                            "actions": [
                                (
                                    {"type": action, "params": {"to": "nope"}}
                                    if action == "forwardTo"
                                    else {
                                        "type": action,
                                        "params": {"to": "nope", "event": "X"},
                                    }
                                )
                            ]
                        }
                    }
                }
            },
        }

    def test_both_siblings_report_identically_on_both_engines(self) -> None:
        for action in ("sendTo", "forwardTo"):
            with self.subTest(action=action):
                d = _Drops()
                s = SyncInterpreter(_mk(self._cfg(action))).use(d).start()
                r = s.send("GO", wait=True)
                self.assertEqual("unresolved_target", d.dropped[0][1])
                self.assertIsNotNone(r.error)
                self.assertFalse(s.last_transition_ok)

                async def main():
                    d2 = _Drops()
                    i = Interpreter(_mk(self._cfg(action))).use(d2)
                    await i.start()
                    r2 = await i.send("GO", wait=True)
                    out = (d2.dropped[0][1], r2.error is not None)
                    await i.stop()
                    return out

                self.assertEqual(("unresolved_target", True), _run(main()))


# =============================================================================
# #134 — on_resolve_error fires on the SYNC engine too
# =============================================================================
class TestResolveErrorHookBothEngines(_Quiet):
    CFG = {"id": "m", "initial": "a", "states": {"a": {"on": {"GO": "zz"}}}}

    class Spy(PluginBase):
        def __init__(self):
            self.seen: List = []

        def on_resolve_error(self, i, err, ev):
            self.seen.append((type(err).__name__, ev.type))

    def test_sync_fires_exactly_once(self) -> None:
        spy = self.Spy()
        i = SyncInterpreter(_mk(self.CFG, strict_targets=False)).use(spy)
        i.start()
        with self.assertRaises(XStateMachineError):
            i.send("GO")
        self.assertEqual([("StateNotFoundError", "GO")], spy.seen)

    def test_async_still_fires_exactly_once(self) -> None:
        spy = self.Spy()

        async def main():
            i = Interpreter(_mk(self.CFG, strict_targets=False)).use(spy)
            await i.start()
            await i.send("GO", wait=True)
            await i.stop()

        _run(main())
        self.assertEqual([("StateNotFoundError", "GO")], spy.seen)


# =============================================================================
# #142 / #143 — configuration LEGALITY on both the write and read side
# =============================================================================
class TestConfigurationLegality(_Quiet):
    PAR = {
        "id": "ord",
        "type": "parallel",
        "context": {},
        "states": {
            "exchange": {
                "initial": "working",
                "states": {
                    "working": {
                        "on": {
                            "FILL": {"target": "filled", "actions": ["slow"]}
                        }
                    },
                    "filled": {},
                },
            },
            "risk": {"initial": "checking", "states": {"checking": {}}},
        },
    }

    @staticmethod
    def _noop_logic():
        return MachineLogic(actions={"slow": lambda *a: None})

    def test_parallel_region_mid_step_snapshot_is_refused(self) -> None:
        async def slow(i, c, e, a):
            await asyncio.sleep(0.3)

        async def main():
            live = await Interpreter(
                _mk(self.PAR, logic=MachineLogic(actions={"slow": slow}))
            ).start()
            t = asyncio.ensure_future(live.send("FILL"))
            await asyncio.sleep(0.1)
            with self.assertRaises(SnapshotMidStepError):
                live.get_persisted_snapshot()
            await t
            await asyncio.sleep(0.3)
            snap = live.get_persisted_snapshot()  # settled: fine
            await live.stop()
            return snap["configuration"]

        cfg = _run(main())
        self.assertIn("ord.exchange.filled", cfg)

    def test_predicate_cases(self) -> None:
        i = Interpreter(_mk(self.PAR, logic=self._noop_logic()))
        m = i.machine
        ex, risk = m.states["exchange"], m.states["risk"]
        legal = {m, ex, ex.states["working"], risk, risk.states["checking"]}
        i._active_state_nodes = set(legal)
        self.assertTrue(i._configuration_is_legal())
        # parallel with a region that has no leaf
        i._active_state_nodes = legal - {ex.states["working"]}
        self.assertFalse(i._configuration_is_legal())
        # compound with two live children
        i._active_state_nodes = legal | {ex.states["filled"]}
        self.assertFalse(i._configuration_is_legal())
        # orphan leaf without its ancestors
        i._active_state_nodes = {ex.states["working"]}
        self.assertFalse(i._configuration_is_legal())
        i._active_state_nodes = set()
        self.assertFalse(i._configuration_is_legal())

    def test_restore_refuses_root_only_and_leafless_region(self) -> None:
        flat = {
            "id": "ord",
            "initial": "working",
            "context": {},
            "states": {"working": {"on": {"FILL": "filled"}}, "filled": {}},
        }
        snap = SyncInterpreter(_mk(flat)).start().get_persisted_snapshot()
        snap["configuration"] = ["ord"]
        for cls in (SyncInterpreter, Interpreter):
            with self.subTest(engine=cls.__name__):
                with self.assertRaises(SnapshotCorruptError):
                    cls.from_snapshot(json.dumps(snap), _mk(flat))
        par = (
            SyncInterpreter(_mk(self.PAR, logic=self._noop_logic()))
            .start()
            .get_persisted_snapshot()
        )
        par["configuration"] = [
            c for c in par["configuration"] if c != "ord.exchange.working"
        ]
        with self.assertRaises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(
                json.dumps(par), _mk(self.PAR, logic=self._noop_logic())
            )


# =============================================================================
# #144 — conservative invoke cycle is bounded by maxIterations
# =============================================================================
class TestInvokeCycleTerminates(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {
                "initial": "a",
                "invoke": {
                    "id": "i1",
                    "src": "svc",
                    "onDone": {"target": "#m.a"},
                },
                "states": {
                    "a": {
                        "invoke": {
                            "id": "i2",
                            "src": "svc",
                            "onDone": {"target": "#m.a"},
                        }
                    }
                },
            }
        },
    }

    def test_start_returns_for_every_budget(self) -> None:
        for mi in (None, 10, 1000):
            with self.subTest(maxIterations=mi):
                cfg = copy.deepcopy(self.CFG)
                if mi is not None:
                    cfg["maxIterations"] = mi
                i = SyncInterpreter(
                    create_machine(
                        cfg,
                        logic=MachineLogic(
                            services={"svc": lambda *a: {"ok": 1}}
                        ),
                    )
                )
                out: Dict[str, Any] = {}

                def go():
                    i.start()
                    out["done"] = True

                th = threading.Thread(target=go, daemon=True)
                th.start()
                th.join(5)
                self.assertFalse(th.is_alive(), "start() livelocked")
                self.assertIsInstance(i.last_error, RunawayChainError)

    def test_independent_raises_still_reset_the_budget(self) -> None:
        cfg = {
            "id": "r",
            "initial": "a",
            "maxIterations": 3,
            "context": {"n": 0},
            "states": {
                "a": {
                    "on": {
                        "T": {
                            "actions": [
                                {"type": "raise", "params": {"event": "INNER"}}
                            ]
                        },
                        "INNER": {"actions": ["bump"]},
                    }
                }
            },
        }
        i = SyncInterpreter(
            _mk(
                cfg,
                logic=MachineLogic(
                    actions={
                        "bump": lambda i, c, e, a: c.__setitem__(
                            "n", c["n"] + 1
                        )
                    }
                ),
            )
        ).start()
        i.send_events(["T"] * 20)  # 20 one-deep chains: never trips
        self.assertEqual(20, i.context["n"])
        self.assertTrue(i.last_transition_ok)


# =============================================================================
# #145 — actionErrorPolicy "fail" STOPS the machine
# =============================================================================
class TestFailPolicyStops(_Quiet):
    CFG = {
        "id": "f",
        "initial": "a",
        "actionErrorPolicy": "fail",
        "states": {"a": {"on": {"GO": "b"}}, "b": {"entry": ["ok1", "boom"]}},
    }

    def _logic(self):
        def boom(*a):
            raise RuntimeError("boom")

        return MachineLogic(actions={"ok1": lambda *a: None, "boom": boom})

    def test_sync_and_async_parity(self) -> None:
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        s.send("GO")
        self.assertEqual("stopped", s.status)
        self.assertEqual(set(), s.current_state_ids)
        self.assertIsInstance(s.error, TransitionFailedError)
        self.assertIsInstance(s.error.__cause__, RuntimeError)
        snap = s.get_persisted_snapshot()
        self.assertEqual(("stopped", []), (snap["status"], snap["state_ids"]))

        async def main():
            i = await Interpreter(_mk(self.CFG, logic=self._logic())).start()
            r = await i.send("GO", wait=True)
            out = (
                i.status,
                sorted(i.current_state_ids),
                type(r.error).__name__,
            )
            await i.stop()
            return out

        self.assertEqual(("stopped", [], "RuntimeError"), _run(main()))

    def test_rollback_policy_unchanged(self) -> None:
        cfg = {**self.CFG, "actionErrorPolicy": "rollback"}
        s = SyncInterpreter(_mk(cfg, logic=self._logic())).start()
        s.send("GO")
        self.assertEqual("running", s.status)
        self.assertEqual({"f.a"}, s.current_state_ids)

    def test_error_snapshot_from_failed_service_still_round_trips(
        self,
    ) -> None:
        cfg = {
            "id": "e",
            "initial": "w",
            "states": {"w": {"invoke": {"src": "svc"}}},
        }

        def svc(*a):
            raise ValueError("dead service")

        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(services={"svc": svc}))
        ).start()
        self.assertEqual("error", s.status)
        r = SyncInterpreter.from_snapshot(
            s.get_snapshot(),
            _mk(cfg, logic=MachineLogic(services={"svc": svc})),
        )
        self.assertEqual("error", r.status)
        self.assertIn("dead service", str(r.error))

    def test_check_shape_rejects_error_without_message(self) -> None:
        cfg = {"id": "e", "initial": "a", "states": {"a": {}}}
        snap = SyncInterpreter(_mk(cfg)).start().get_persisted_snapshot()
        snap["status"] = "error"
        snap["error"] = None
        with self.assertRaises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(json.dumps(snap), _mk(cfg))


# =============================================================================
# #146 / #158 — every hostile field is a typed error
# =============================================================================
class TestHostileSnapshotFieldsAreTyped(_Quiet):
    CFG = {
        "id": "fz",
        "initial": "b",
        "states": {"b": {"on": {"GO": "c"}}, "c": {}},
    }

    def test_every_field_times_every_scalar(self) -> None:
        good = SyncInterpreter(_mk(self.CFG)).start().get_persisted_snapshot()
        hostile = [None, 7, 3.14, "junk", [], {}, True]
        for key in (
            "version",
            "status",
            "context",
            "state_ids",
            "configuration",
            "pending_events",
            "deferred",
            "history",
            "actors",
            "system",
            "output",
            "error",
        ):
            for val in hostile:
                blob = json.loads(json.dumps(good))
                blob[key] = val
                with self.subTest(key=key, val=val):
                    try:
                        SyncInterpreter.from_snapshot(
                            json.dumps(blob), _mk(self.CFG)
                        )
                    except XStateMachineError:
                        pass  # typed refusal is fine
                    # anything else propagates and fails the subtest

    def test_non_string_payload_and_bad_json_are_typed(self) -> None:
        with self.assertRaises(XStateMachineError):
            SyncInterpreter.from_snapshot(None, _mk(self.CFG))  # type: ignore[arg-type]
        with self.assertRaises(XStateMachineError):
            SyncInterpreter.from_snapshot("{not json", _mk(self.CFG))

    def test_non_str_pending_event_type_refused(self) -> None:
        for bad in (42, None, ["GO"], {"x": 1}, True):
            with self.subTest(bad=bad):
                blob = {
                    "version": 1,
                    "status": "running",
                    "context": {},
                    "state_ids": ["fz.b"],
                    "configuration": ["fz", "fz.b"],
                    "pending_events": [
                        {"kind": "event", "type": bad, "payload": {}}
                    ],
                }
                with self.assertRaises(SnapshotCorruptError):
                    SyncInterpreter.from_snapshot(
                        json.dumps(blob), _mk(self.CFG)
                    )
        with self.assertRaises(SnapshotCorruptError):
            restore_event({"kind": "event", "type": 42})


# =============================================================================
# #147 — root target rejected regardless of strict_targets
# =============================================================================
class TestRootTargetRegardlessOfStrictTargets(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": "#m"}}, "b": {}},
    }

    def test_both_flag_values_raise_root_target_error(self) -> None:
        for strict in (True, False):
            with self.subTest(strict_targets=strict):
                with self.assertRaises(RootTargetError) as cm:
                    _mk(self.CFG, strict_targets=strict)
                self.assertIn("machine root", str(cm.exception))
                self.assertIsInstance(cm.exception, InvalidConfigError)

    def test_genuinely_unresolvable_still_only_warns(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "nowhere"}}},
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _mk(cfg, strict_targets=False)
        self.assertTrue(any("unresolvable" in str(x.message) for x in w))


# =============================================================================
# #148 — cancel before the loop's first turn is published
# =============================================================================
class TestCancelBeforeFirstTurn(_Quiet):
    CFG = {
        "id": "c",
        "initial": "a",
        "states": {"a": {"on": {"GO": "b"}}, "b": {}},
    }

    class Spy(PluginBase):
        def __init__(self):
            self.errors = 0

        def on_error(self, i, e):
            self.errors += 1

    def _case(self, yield_first: bool):
        spy = self.Spy()

        async def main():
            i = Interpreter(_mk(self.CFG)).use(spy)
            await i.start()
            if yield_first:
                await asyncio.sleep(0)
            i._event_loop_task.cancel()
            await asyncio.sleep(0.05)
            r = await asyncio.wait_for(i.send("GO", wait=True), 2)
            out = (i.status, type(i.error).__name__, type(r.error).__name__)
            await i.stop()
            return out

        return _run(main()), spy.errors

    def test_publishes_in_both_windows_exactly_once(self) -> None:
        for yield_first in (False, True):
            with self.subTest(yield_first=yield_first):
                (status, err, receipt_err), n = self._case(yield_first)
                self.assertEqual("error", status)
                self.assertEqual("RuntimeError", err)
                self.assertEqual("InterpreterStoppedError", receipt_err)
                self.assertEqual(1, n, "on_error must fire exactly once")


# =============================================================================
# #149 — plain-def service does not block the loop; #116 ordering kept
# =============================================================================
class TestPlainServiceOffLoop(_Quiet):
    CFG = {
        "id": "s",
        "initial": "w",
        "states": {
            "w": {"invoke": {"id": "svc", "src": "slow", "onDone": "d"}},
            "d": {},
        },
    }

    def test_ticker_advances_and_start_returns_promptly(self) -> None:
        def slow(i, c, e):
            time.sleep(0.3)
            return 1

        async def main():
            ticks = {"n": 0}

            async def ticker():
                while True:
                    ticks["n"] += 1
                    await asyncio.sleep(0.01)

            t = asyncio.ensure_future(ticker())
            t0 = time.monotonic()
            i = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(services={"slow": slow}))
            ).start()
            blocked = time.monotonic() - t0
            base = ticks["n"]
            # Wait for the service to COMPLETE (observable), not a fixed
            # window: slow runners stretch a 0.3 s sleep well past 0.35 s.
            for _ in range(600):
                if i.value == "d":
                    break
                await asyncio.sleep(0.005)
            during = ticks["n"] - base
            t.cancel()
            v = i.value
            await i.stop()
            return blocked, during, v

        blocked, during, v = _run(main())
        self.assertLess(blocked, 0.15)
        # The loop stayed live: the 10 ms ticker ran many times while the
        # 0.3 s blocking service was in flight (was 0 before #149).
        self.assertGreaterEqual(during, 10)
        self.assertEqual("d", v)

    def test_raising_and_awaitable_returning_services(self) -> None:
        cfg = {
            "id": "s",
            "initial": "w",
            "states": {
                "w": {
                    "invoke": {
                        "id": "svc",
                        "src": "svc",
                        "onDone": "d",
                        "onError": "e",
                    }
                },
                "d": {},
                "e": {},
            },
        }

        def raises(i, c, e):
            raise ValueError("nope")

        def returns_coro(i, c, e):
            async def later():
                return 7

            return later()

        async def main(svc):
            i = await Interpreter(
                _mk(cfg, logic=MachineLogic(services={"svc": svc}))
            ).start()
            for _ in range(50):
                if i.value in ("d", "e"):
                    break
                await asyncio.sleep(0.01)
            v = i.value
            await i.stop()
            return v

        self.assertEqual("e", _run(main(raises)))
        self.assertEqual("d", _run(main(returns_coro)))

    def test_executor_released_on_stop(self) -> None:
        async def main():
            i = await Interpreter(
                _mk(
                    self.CFG,
                    logic=MachineLogic(services={"slow": lambda *a: 1}),
                )
            ).start()
            await asyncio.sleep(0.05)
            ex = i._service_executor
            await i.stop()
            return ex is not None, i._service_executor

        created, after = _run(main())
        self.assertTrue(created)
        self.assertIsNone(after)


# =============================================================================
# #150 — self-sends via send_threadsafe are budgeted
# =============================================================================
class TestThreadsafeSelfSendBudgeted(_Quiet):
    CFG = {
        "id": "spin",
        "initial": "a",
        "maxIterations": 20,
        "context": {},
        "states": {"a": {"on": {"T": {"actions": ["resend"]}}}},
    }

    def _count(self, mode: str) -> tuple:
        seen = {"n": 0}

        async def resend(i, c, e, a):
            seen["n"] += 1
            if seen["n"] >= 60:
                return
            if mode == "direct":
                await i.send("T")
            elif mode == "flag":
                threading.Thread(
                    target=lambda: i.send_threadsafe("T", internal=True),
                    daemon=True,
                ).start()
            else:
                ctx = contextvars.copy_context()
                threading.Thread(
                    target=lambda: ctx.run(i.send_threadsafe, "T"), daemon=True
                ).start()

        async def main():
            i = await Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"resend": resend}))
            ).start()
            await i.send("T")
            await asyncio.sleep(0.8)
            out = (
                seen["n"],
                type(i.last_error).__name__ if i.last_error else None,
                i.last_transition_ok,
            )
            await i.stop()
            return out

        return _run(main())

    def test_all_routes_stop_at_the_budget_and_trip_is_observable(
        self,
    ) -> None:
        direct = self._count("direct")
        for mode in ("flag", "ctx"):
            with self.subTest(mode=mode):
                n, err, ok = self._count(mode)
                self.assertLessEqual(abs(n - direct[0]), 2)
                self.assertEqual("RunawayChainError", err)
                self.assertFalse(ok)


# =============================================================================
# #151 — settle budget is per macrostep
# =============================================================================
class TestSettleBudgetPerMacrostep(_Quiet):
    @staticmethod
    def _cfg(n: int = 40, limit: int = 50):
        states: Dict[str, Any] = {"idle": {"on": {"GO": "s0", "GO2": "u0"}}}
        for k in range(n):
            states[f"s{k}"] = {"always": f"s{k + 1}"}
        states[f"s{n}"] = {"on": {"GO2": "u0"}}
        for k in range(n):
            states[f"u{k}"] = {"always": f"u{k + 1}"}
        states[f"u{n}"] = {}
        return {
            "id": "L",
            "initial": "idle",
            "maxIterations": limit,
            "states": states,
        }

    def test_batch_matches_sequential(self) -> None:
        a = SyncInterpreter(_mk(self._cfg())).start()
        a.send("GO")
        a.send("GO2")
        b = SyncInterpreter(_mk(self._cfg())).start()
        b.send_events(["GO", "GO2"])
        self.assertEqual(a.value, b.value)
        self.assertTrue(b.last_transition_ok)
        self.assertIsNone(b.last_error)

    def test_final_state_independent_of_batch_size(self) -> None:
        cfg = {
            "id": "b",
            "initial": "a",
            "maxIterations": 5,
            "states": {
                "a": {"on": {"GO": "s0"}},
                "s0": {"always": "s1"},
                "s1": {"always": "s2"},
                "s2": {"always": "s3"},
                "s3": {"on": {"GO": "s0"}},
            },
        }
        for size in range(1, 11):
            with self.subTest(size=size):
                i = SyncInterpreter(_mk(cfg)).start()
                i.send_events(["GO"] * size)
                self.assertEqual("s3", i.value)
                self.assertTrue(i.last_transition_ok)


# =============================================================================
# #152 — guard "raise" cancels only its own candidate
# =============================================================================
class TestGuardRaiseKeepsFallback(_Quiet):
    def test_invoke_ondone_fallback_is_taken_on_both_engines(self) -> None:
        def gboom(c, e):
            raise RuntimeError("guardboom")

        cfg = {
            "id": "ld",
            "initial": "verifying",
            "guardErrorPolicy": "raise",
            "states": {
                "verifying": {
                    "invoke": {
                        "id": "ver",
                        "src": "svc",
                        "onDone": [
                            {"target": "accepted", "guard": "risk_ok"},
                            {"target": "rejected"},
                        ],
                    }
                },
                "accepted": {},
                "rejected": {},
            },
        }
        s = SyncInterpreter(
            _mk(
                cfg,
                logic=MachineLogic(
                    guards={"risk_ok": gboom},
                    services={"svc": lambda *a: {"ok": 1}},
                ),
            )
        ).start()
        self.assertEqual("rejected", s.value)
        self.assertIsInstance(s.last_error, RuntimeError)

        async def svc(i, c, e):
            return {"ok": True}

        async def main():
            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        guards={"risk_ok": gboom}, services={"svc": svc}
                    ),
                )
            ).start()
            await asyncio.sleep(0.1)
            out = (i.value, type(i.last_error).__name__)
            await i.stop()
            return out

        self.assertEqual(("rejected", "RuntimeError"), _run(main()))

    def test_caller_still_receives_the_exception(self) -> None:
        cfg = {
            "id": "g",
            "initial": "a",
            "guardErrorPolicy": "raise",
            "states": {
                "a": {
                    "on": {
                        "GO": [
                            {"target": "b", "guard": "boom"},
                            {"target": "c"},
                        ]
                    }
                },
                "b": {},
                "c": {},
            },
        }

        def boom(c, e):
            raise ValueError("x")

        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(guards={"boom": boom}))
        ).start()
        with self.assertRaises(ValueError):
            s.send("GO")
        self.assertEqual("c", s.value)

        async def main():
            i = await Interpreter(
                _mk(cfg, logic=MachineLogic(guards={"boom": boom}))
            ).start()
            r = await i.send("GO", wait=True)
            out = (i.value, type(r.error).__name__)
            await i.stop()
            return out

        self.assertEqual(("c", "ValueError"), _run(main()))


# =============================================================================
# #153 — guard-denied vs undeclared are distinguishable
# =============================================================================
class TestGuardDeniedDistinguishable(_Quiet):
    class Hook(PluginBase):
        def __init__(self):
            self.seen: List = []

        def on_unhandled_event(self, i, e, ids, disp):
            self.seen.append(disp)

    def _probe(self, guarded: bool, policy: str = "ignore", event: str = "GO"):
        on = {"GO": ({"target": "b", "guard": "deny"} if guarded else "b")}
        cfg = {
            "id": "m",
            "initial": "a",
            "onUnhandled": policy,
            "states": {"a": {"on": on}, "b": {}},
        }
        h = self.Hook()
        s = (
            SyncInterpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(guards={"deny": lambda c, e: False}),
                )
            )
            .use(h)
            .start()
        )
        r = s.send(event, wait=True)
        return (r.changed, r.denied, r.deferred, tuple(h.seen))

    def test_four_way_matrix_pairwise_distinct(self) -> None:
        noop = self._probe(False, event="NOPE")
        denied = self._probe(True)
        deferred = self._probe(False, policy="defer", event="NOPE")
        self.assertEqual((False, False, False, ("ignored",)), noop)
        self.assertEqual((False, True, False, ("guard_denied",)), denied)
        self.assertEqual((False, False, True, ("deferred",)), deferred)
        self.assertEqual(3, len({noop, denied, deferred}))

    def test_denied_only_when_all_candidates_denied(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": [
                            {"target": "b", "guard": "deny"},
                            {"target": "c"},
                        ]
                    }
                },
                "b": {},
                "c": {},
            },
        }
        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(guards={"deny": lambda c, e: False}))
        ).start()
        r = s.send("GO", wait=True)
        self.assertTrue(r.changed)
        self.assertFalse(r.denied)

    def test_async_receipt_denied(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "guard": "deny"}}},
                "b": {},
            },
        }

        async def main():
            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(guards={"deny": lambda c, e: False}),
                )
            ).start()
            r = await i.send("GO", wait=True)
            await i.stop()
            return r.denied, r.changed

        self.assertEqual((True, False), _run(main()))


# =============================================================================
# #154 — sync restore attaches the SimulatedClock
# =============================================================================
class TestSyncRestoreAttachesClock(_Quiet):
    CFG = {
        "id": "tm",
        "initial": "idle",
        "context": {"late": 0},
        "states": {
            "idle": {"on": {"GO": "armed"}},
            "armed": {
                "after": {"50": {"target": "idle", "actions": ["late"]}}
            },
        },
    }

    def _m(self):
        return _mk(
            self.CFG,
            logic=MachineLogic(
                actions={
                    "late": lambda i, c, e, a: c.__setitem__(
                        "late", c["late"] + 1
                    )
                }
            ),
        )

    def test_restart_timers_path(self) -> None:
        src = SyncInterpreter(self._m(), clock=SimulatedClock()).start()
        src.send("GO")
        snap = src.get_snapshot()
        clock = SimulatedClock()
        r = SyncInterpreter.from_snapshot(
            snap, self._m(), clock=clock, restart_timers=True
        ).start()
        self.assertEqual(1, len(clock._settlers))
        clock.increment(200)
        self.assertEqual(1, r.context["late"])

    def test_persisted_inbox_path(self) -> None:
        cfg = {
            "id": "q",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {"after": {"10": "c"}},
                "c": {},
            },
        }
        blob = {
            "version": 1,
            "status": "running",
            "context": {},
            "state_ids": ["q.a"],
            "configuration": ["q", "q.a"],
            "pending_events": [{"kind": "event", "type": "GO", "payload": {}}],
        }
        clock = SimulatedClock()
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(cfg), clock=clock
        ).start()
        self.assertEqual(1, len(clock._settlers))
        clock.increment(20)
        self.assertEqual("c", r.value)


# =============================================================================
# #155 — user actions named spawn_* take precedence
# =============================================================================
class TestSpawnPrefixPrecedence(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {
                "on": {"GO": {"target": "b", "actions": ["spawn_place_order"]}}
            },
            "b": {},
        },
    }

    def test_explicit_logic(self) -> None:
        called = []
        s = SyncInterpreter(
            _mk(
                self.CFG,
                logic=MachineLogic(
                    actions={"spawn_place_order": lambda *a: called.append(1)}
                ),
            )
        ).start()
        s.send("GO")
        self.assertEqual([1], called)
        self.assertEqual("b", s.value)

    def test_auto_discovery(self) -> None:
        class P:
            def spawn_place_order(self, i, c, e, a):
                c["ran"] = True

        m = create_machine(
            json.loads(json.dumps(self.CFG)), logic_providers=[P()]
        )
        self.assertIn("spawn_place_order", m.logic.actions)
        self.assertNotIn("place_order", m.logic.services)

    def test_unregistered_spawn_prefix_still_spawns(self) -> None:
        child = {"id": "kid", "initial": "x", "states": {"x": {}}}
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"entry": ["spawn_kid"]}},
        }
        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(services={"kid": _mk(child)}))
        ).start()
        self.addCleanup(s.stop)  # reap the actor thread
        self.assertTrue(any(k.startswith("p:") for k in s._actors))


# =============================================================================
# #156 — escalate reaches onError without an explicit invoke id
# =============================================================================
class TestEscalateWithoutInvokeId(_Quiet):
    CHILD = {
        "id": "c",
        "initial": "w",
        "states": {
            "w": {
                "entry": [
                    {"type": "escalate", "params": {"error": "child exploded"}}
                ]
            }
        },
    }

    def _parent(self, explicit: bool):
        inv: Dict[str, Any] = {"src": "kid", "onError": "caught"}
        if explicit:
            inv["id"] = "kid"
        return {
            "id": "p",
            "initial": "w",
            "states": {"w": {"invoke": inv}, "caught": {}},
        }

    def test_both_shapes_both_engines(self) -> None:
        for explicit in (False, True):
            with self.subTest(explicit_id=explicit):
                s = SyncInterpreter(
                    _mk(
                        self._parent(explicit),
                        logic=MachineLogic(services={"kid": _mk(self.CHILD)}),
                    )
                ).start()
                self.addCleanup(s.stop)  # reap the invoked child's thread
                self.assertEqual("caught", s.value)

                async def main():
                    i = await Interpreter(
                        _mk(
                            self._parent(explicit),
                            logic=MachineLogic(
                                services={"kid": _mk(self.CHILD)}
                            ),
                        )
                    ).start()
                    for _ in range(50):
                        if i.value == "caught":
                            break
                        await asyncio.sleep(0.01)
                    v = i.value
                    await i.stop()
                    return v

                self.assertEqual("caught", _run(main()))


# =============================================================================
# #157 — send_threadsafe backpressure on the calling thread
# =============================================================================
class TestThreadsafeBackpressure(_Quiet):
    CFG = {
        "id": "q",
        "initial": "a",
        "context": {"n": 0},
        "states": {"a": {"on": {"PING": {"actions": ["bump"]}}}},
    }

    def test_raise_policy_raises_at_call_site_when_full(self) -> None:
        async def bump(i, c, e, a):
            await asyncio.sleep(0.05)

        async def main():
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"bump": bump})),
                max_queue_size=5,
                overflow_policy=OverflowPolicy.RAISE,
            )
            await i.start()
            for _ in range(5):
                await i.send("PING")
            out: Dict[str, Any] = {}

            def prod():
                try:
                    i.send_threadsafe("PING")
                    out["r"] = "none"
                except QueueOverflowError:
                    out["r"] = "raised"

            t = threading.Thread(target=prod)
            t.start()
            t.join()
            await i.stop()
            return out["r"]

        self.assertEqual("raised", _run(main()))

    def test_drop_newest_unchanged_and_future_still_carries_error(
        self,
    ) -> None:
        async def bump(i, c, e, a):
            await asyncio.sleep(0.05)

        async def main():
            d = _Drops()
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"bump": bump})),
                max_queue_size=2,
                overflow_policy=OverflowPolicy.DROP_NEWEST,
            ).use(d)
            await i.start()
            # One event is dequeued into the (slow) action immediately, so
            # three sends leave the 2-slot inbox full.
            for _ in range(3):
                await i.send("PING")
            self.assertTrue(i._inbox_is_full())
            f = i.send_threadsafe(
                "PING"
            )  # same thread is fine for DROP_NEWEST
            await asyncio.sleep(0.02)
            out = (
                f.exception() is None,
                d.dropped[-1][1] if d.dropped else None,
            )
            await i.stop()
            return out

        self.assertEqual((True, "queue_full"), _run(main()))


# =============================================================================
# #159 — on_invalid_event / on_snapshot_error
# =============================================================================
class TestErrorHooks(_Quiet):
    class Spy(PluginBase):
        def __init__(self):
            self.invalid: List = []
            self.snap: List = []

        def on_invalid_event(self, i, err, raw):
            self.invalid.append((type(err).__name__, raw))

        def on_snapshot_error(self, i, err):
            self.snap.append(type(err).__name__)

    def test_invalid_event_hook_fires_then_reraises_both_engines(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {}}}
        spy = self.Spy()
        s = SyncInterpreter(_mk(cfg)).use(spy).start()
        with self.assertRaises(InvalidEventError):
            s.send(42)  # type: ignore[arg-type]
        self.assertEqual([("InvalidEventError", 42)], spy.invalid)

        async def main():
            sp = self.Spy()
            i = Interpreter(_mk(cfg)).use(sp)
            await i.start()
            with self.assertRaises(InvalidEventError):
                await i.send(42)  # type: ignore[arg-type]
            await i.stop()
            return sp.invalid

        self.assertEqual([("InvalidEventError", 42)], _run(main()))

    def test_midstep_and_serialization_fire_snapshot_hook(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "actions": ["grab"]}}},
                "b": {},
            },
        }
        spy = self.Spy()
        res: Dict[str, Any] = {}

        def grab(i, c, e, a):
            try:
                i.get_persisted_snapshot()
            except SnapshotMidStepError as ex:
                res["raised"] = type(ex).__name__

        s = (
            SyncInterpreter(
                _mk(cfg, logic=MachineLogic(actions={"grab": grab}))
            )
            .use(spy)
            .start()
        )
        s.send("GO")
        self.assertEqual("SnapshotMidStepError", res["raised"])
        self.assertEqual(["SnapshotMidStepError"], spy.snap)
        # serialization: a pending event with non-JSON data
        cfg2 = {
            "id": "d",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {"a": {}},
        }
        spy2 = self.Spy()
        s2 = SyncInterpreter(_mk(cfg2)).use(spy2).start()
        s2.send("LATE", amount=__import__("decimal").Decimal("1.5"))
        with self.assertRaises(SnapshotSerializationError):
            s2.get_snapshot()
        self.assertEqual(["SnapshotSerializationError"], spy2.snap)


# =============================================================================
# #160 — redaction gaps
# =============================================================================
class TestRedactionGaps(_Quiet):
    def test_get_snapshot_debug_log_is_redacted(self) -> None:
        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        lg = logging.getLogger(_PKG_LOGGER)
        logging.disable(logging.NOTSET)
        lg.addHandler(h)
        lg.setLevel(logging.DEBUG)
        try:
            cfg = {
                "id": "m",
                "initial": "a",
                "context": {
                    "api_key": "sk-live-SECRET999",
                    "password": "hunter2",
                },
                "states": {"a": {}},
            }
            SyncInterpreter(_mk(cfg)).start().get_snapshot()
        finally:
            lg.removeHandler(h)
        text = buf.getvalue()
        self.assertNotIn("SECRET999", text)
        self.assertNotIn("hunter2", text)
        self.assertIn("***", text)

    def test_default_keys_cover_financial_and_session_pii(self) -> None:
        keys = [
            "account_number",
            "bearer",
            "cookie",
            "dob",
            "email",
            "iban",
            "mnemonic",
            "pan",
            "pin",
            "pwd",
            "seed_phrase",
            "sessionId",
            "signature",
            "cardNumber",
            "cvc",
            "otp",
            "phone",
            "passport",
        ]
        red = redact({k: f"LEAK-{k}" for k in keys})
        self.assertEqual([], [k for k in keys if red[k] != "***"])
        self.assertIn("iban", DEFAULT_REDACT_KEYS)

    def test_service_result_redacted_in_inspector(self) -> None:
        from src.xstate_statemachine.plugins import LoggingInspector

        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        lg = logging.getLogger(_PKG_LOGGER)
        logging.disable(logging.NOTSET)
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
        try:
            cfg = {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"invoke": {"src": "svc", "onDone": "b"}},
                    "b": {},
                },
            }
            SyncInterpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        services={"svc": lambda *a: {"token": "TOK-SECRET"}}
                    ),
                )
            ).use(LoggingInspector()).start()
        finally:
            lg.removeHandler(h)
        self.assertNotIn("TOK-SECRET", buf.getvalue())


# =============================================================================
# #161 — dict-event key validation is explicit
# =============================================================================
class TestDictEventKeys(_Quiet):
    def test_non_str_keys_raise_and_values_pass_through(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        s = SyncInterpreter(_mk(cfg)).start()
        with self.assertRaises(InvalidEventError):
            s.send({"type": "GO", 7: "x"})  # type: ignore[dict-item]
        s.send({"type": "GO", "anything": object()})  # values are the caller's
        self.assertEqual("b", s.value)

    def test_boundary_documented_on_send(self) -> None:
        for cls in (SyncInterpreter, Interpreter):
            self.assertIn("#161", cls.send.__doc__ or "")


# =============================================================================
# #162 — v1 records are USER events unless they are the init sentinel
# =============================================================================
class TestV1ProvenanceIsUser(_Quiet):
    def test_engine_shaped_user_names_stay_user(self) -> None:
        for t in (
            "after.hours",
            "xstate.custom",
            "done.review",
            "error.platform.x",
        ):
            with self.subTest(type=t):
                self.assertFalse(
                    is_system_event(restore_event({"type": t, "payload": {}}))
                )

    def test_init_sentinel_stays_system_and_v2_kinds_unaffected(self) -> None:
        self.assertTrue(
            is_system_event(
                restore_event(
                    {"type": "___xstate_statemachine_init___", "payload": {}}
                )
            )
        )
        self.assertTrue(
            is_system_event(
                restore_event(
                    {"kind": "system", "type": "after.hours", "payload": {}}
                )
            )
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
