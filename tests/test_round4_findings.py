"""Regression tests for the round-4 re-verification findings (#102–#138 and
the reopened #91 / #99).

One class per issue. Each test is the reporter's acceptance criterion in
miniature, so a future regression names the issue it reopens.
"""

from __future__ import annotations

import asyncio
import copy
import decimal
import json
import logging
import pickle
import threading
import time
import unittest
import warnings
from typing import Any, Dict, List

import xstate_statemachine as xsm
from src.xstate_statemachine import (
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    Interpreter,
    InvalidConfigError,
    InvalidEventError,
    MachineLogic,
    OverflowPolicy,
    Receipt,
    RootTargetError,
    RunawayChainError,
    SimulatedClock,
    SnapshotCorruptError,
    SnapshotMidStepError,
    SnapshotSerializationError,
    SyncInterpreter,
    UnknownEventError,
    create_machine,
    is_system_event,
    system_event,
)
from src.xstate_statemachine.events import persist_event, restore_event
from src.xstate_statemachine.exceptions import XStateMachineError
from src.xstate_statemachine.plugins import (
    LoggingInspector,
    PluginBase,
    redact,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _run(coro):
    return asyncio.run(asyncio.wait_for(coro, 15))


def _bump(key: str):
    return lambda i, c, e, a: c.__setitem__(key, c[key] + 1)


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.dropped: List = []

    def on_event_dropped(self, interp, event, reason):
        self.dropped.append((event.type, reason))


# =============================================================================
# #91 — config-side: two required names collapse onto one callable
# =============================================================================
class TestConfigNamesCollapseWarn(_Quiet):
    def test_two_config_spellings_one_impl_warns(self) -> None:
        def store(i, c, e, a):
            pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"entry": ["store_user", "storeUser"]}},
                },
                logic=MachineLogic(actions={"store_user": store}),
            )
        msgs = [str(x.message) for x in w if x.category is UserWarning]
        self.assertTrue(
            any("store_user" in m and "storeUser" in m for m in msgs), msgs
        )

    def test_single_spelling_does_not_warn(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"entry": ["storeUser"]}},
                },
                logic=MachineLogic(
                    actions={"store_user": lambda i, c, e, a: None}
                ),
            )
        self.assertFalse(
            [
                x
                for x in w
                if x.category is UserWarning
                and "differ only" in str(x.message)
            ]
        )


# =============================================================================
# #99 — async unhandled child failure fails the parent
# =============================================================================
class TestAsyncUnhandledChildFailure(_Quiet):
    BAD = {
        "id": "bad",
        "initial": "s",
        "actionErrorPolicy": "fail",
        "states": {"s": {"entry": ["boom"]}},
    }

    def test_both_engines_fail_parent_when_unhandled(self) -> None:
        def boom(i, c, e, a):
            raise ValueError("child boom")

        parent = {
            "id": "p",
            "initial": "w",
            "states": {"w": {"invoke": {"src": "kid", "id": "kid"}}},
        }

        def logic():
            return MachineLogic(
                services={
                    "kid": create_machine(
                        self.BAD, logic=MachineLogic(actions={"boom": boom})
                    )
                }
            )

        s = SyncInterpreter(create_machine(parent, logic=logic()))
        s.start()
        for _ in range(100):
            if s.status == "error":
                break
            s.tick()
            time.sleep(0.01)

        async def main():
            i = await Interpreter(
                create_machine(parent, logic=logic())
            ).start()
            await asyncio.sleep(0.2)
            out = (i.status, type(i.error).__name__ if i.error else None)
            try:
                await asyncio.wait_for(i.stop(), 2)
            except Exception:
                pass
            return out

        a_status, a_err = _run(main())
        self.assertEqual((s.status, a_status), ("error", "error"))
        self.assertIsNotNone(s.error)
        self.assertIsNotNone(a_err)


# =============================================================================
# #102 — mid-macrostep snapshot is refused
# =============================================================================
class TestMidStepSnapshotRefused(_Quiet):
    CFG = {
        "id": "t",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": {"target": "b", "actions": ["slow"]}}},
            "b": {},
        },
    }

    def test_snapshot_inside_transition_window_raises_typed(self) -> None:
        async def slow(i, c, e, a):
            await asyncio.sleep(0.3)

        async def main():
            i = await Interpreter(
                create_machine(
                    self.CFG, logic=MachineLogic(actions={"slow": slow})
                )
            ).start()
            t = asyncio.ensure_future(i.send("GO"))
            await asyncio.sleep(0.1)
            with self.assertRaises(SnapshotMidStepError) as ctx:
                i.get_persisted_snapshot()
            self.assertIsInstance(ctx.exception, XStateMachineError)
            await t
            await asyncio.sleep(0.35)  # the 0.3 s action must finish
            settled = i.get_persisted_snapshot()  # fine once settled
            await i.stop()
            return settled["state_ids"]

        self.assertEqual(_run(main()), ["t.b"])

    def test_settled_snapshot_restores_to_a_live_machine(self) -> None:
        i = SyncInterpreter(
            create_machine(
                self.CFG,
                logic=MachineLogic(actions={"slow": lambda i, c, e, a: None}),
            )
        )
        i.start()
        i.send("GO")
        snap = i.get_snapshot()
        i.stop()
        r = SyncInterpreter.from_snapshot(
            snap,
            create_machine(
                self.CFG,
                logic=MachineLogic(actions={"slow": lambda i, c, e, a: None}),
            ),
        )
        self.assertEqual(r.value, "b")


# =============================================================================
# #103 / #112 — settle budget is per macrostep; a trip is observable
# =============================================================================
class TestSettleBudgetTerminates(_Quiet):
    def test_cross_region_always_into_invoking_state_returns(self) -> None:
        cfg = {
            "id": "m",
            "type": "parallel",
            "maxIterations": 50,
            "states": {
                "A": {
                    "initial": "a1",
                    "states": {
                        "a1": {
                            "invoke": {"id": "s", "src": "svc", "onDone": "a1"}
                        },
                        "a2": {},
                    },
                },
                "B": {
                    "initial": "b1",
                    "states": {"b1": {"always": {"target": "#m.A.a1"}}},
                },
            },
        }
        out: Dict[str, Any] = {}

        def go():
            i = SyncInterpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(services={"svc": lambda i, c, e: 1}),
                )
            )
            i.start()
            out["ok"] = i.last_transition_ok
            out["err"] = type(i.last_error).__name__ if i.last_error else None
            out["status"] = i.status

        th = threading.Thread(target=go, daemon=True)
        th.start()
        th.join(5)
        self.assertFalse(th.is_alive(), "start() must return")
        self.assertFalse(out["ok"])
        self.assertEqual(out["err"], "RunawayChainError")
        self.assertEqual(out["status"], "running")

    def test_trip_leaves_a_legal_configuration(self) -> None:
        cfg = {
            "id": "m",
            "initial": "p",
            "maxIterations": 5,
            "states": {
                "p": {
                    "initial": "x",
                    "states": {"x": {"always": "y"}, "y": {"always": "x"}},
                }
            },
        }
        i = SyncInterpreter(create_machine(cfg))
        i.start()
        active = {n.id for n in i._active_state_nodes}
        for n in i._active_state_nodes:
            if n.parent is not None:
                self.assertIn(
                    n.parent.id, active, f"{n.id} has an inactive ancestor"
                )
        self.assertFalse(i.last_transition_ok)
        self.assertIsInstance(i.last_error, RunawayChainError)


# =============================================================================
# #104 — BLOCK: fire-and-forget send is delivered
# =============================================================================
class TestBlockPolicyEagerEnqueue(_Quiet):
    def test_unawaited_send_is_delivered_when_room(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"T": {"actions": "inc"}}}},
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg, logic=MachineLogic(actions={"inc": _bump("n")})
                ),
                max_queue_size=10,
                overflow_policy=OverflowPolicy.BLOCK,
            ).start()
            i.send("T")
            i.send("T")
            await asyncio.sleep(0.05)
            n = i.context["n"]
            await i.stop()
            return n

        self.assertEqual(_run(main()), 2)

    def test_stopped_machine_still_refuses_under_block(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {"on": {"T": "a"}}}}

        async def main():
            i = Interpreter(
                create_machine(cfg),
                max_queue_size=1,
                overflow_policy=OverflowPolicy.BLOCK,
            )
            await i.start()
            await i.stop()
            r = await asyncio.wait_for(i.send("T", wait=True), 2)
            return r.error is not None

        self.assertTrue(_run(main()))


# =============================================================================
# #105 — external send during an in-flight step is not budgeted
# =============================================================================
class TestExternalSendNotChargedToChain(_Quiet):
    def test_concurrent_producer_during_slow_step(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 10,
            "states": {
                "a": {
                    "on": {
                        "SLOW": {"actions": "slow"},
                        "T": {"actions": "inc"},
                    }
                }
            },
        }

        async def slow(i, c, e, a):
            await asyncio.sleep(0.2)

        async def main():
            d = _Drops()
            i = Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={"slow": slow, "inc": _bump("n")}
                    ),
                )
            ).use(d)
            await i.start()
            t = asyncio.ensure_future(i.send("SLOW"))
            await asyncio.sleep(0.02)
            for _ in range(30):
                await i.send("T")
            await t
            await asyncio.sleep(0.3)
            out = (
                i.context["n"],
                [r for _, r in d.dropped if r == "chain_budget"],
            )
            await i.stop()
            return out

        n, drops = _run(main())
        self.assertEqual(n, 30)
        self.assertEqual(drops, [])

    def test_action_self_send_is_still_budgeted(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 20,
            "states": {"a": {"on": {"LOOP": {"actions": "ss"}}}},
        }

        async def ss(i, c, e, a):
            c["n"] += 1
            await i.send("LOOP")

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"ss": ss}))
            ).start()
            await i.send("LOOP")
            await asyncio.sleep(0.3)
            n = i.context["n"]
            await i.stop()
            return n

        self.assertLessEqual(_run(main()), 22)


# =============================================================================
# #106 — Receipt.deferred bookkeeping is per-step and by reference
# =============================================================================
class TestDeferredBookkeeping(_Quiet):
    CFG = {
        "id": "g",
        "initial": "closed",
        "onUnhandled": "defer",
        "states": {
            "closed": {"on": {"OPEN": "open"}},
            "open": {"on": {"FILL": "open", "CLOSE": "closed"}},
        },
    }

    def test_set_does_not_grow_and_no_false_deferred(self) -> None:
        i = SyncInterpreter(create_machine(self.CFG))
        i.start()
        for _ in range(300):
            i.send("FILL")
            i.send("OPEN")
            r = i.send("CLOSE", wait=True)
            self.assertFalse(
                r.deferred, "a handled event must never read as deferred"
            )
        self.assertEqual(len(i._deferred_this_step), 0)
        i.stop()


# =============================================================================
# #107 — priority lane persists
# =============================================================================
class TestPriorityLanePersisted(_Quiet):
    def test_fired_after_event_in_priority_lane_is_in_snapshot(self) -> None:
        cfg = {
            "id": "lanes",
            "initial": "waiting",
            "context": {"fired": 0},
            "states": {
                "waiting": {
                    "after": {
                        "1000": {"target": "expired", "actions": ["mark"]}
                    }
                },
                "expired": {"type": "final"},
            },
        }

        def build():
            return create_machine(
                cfg, logic=MachineLogic(actions={"mark": _bump("fired")})
            )

        async def main():
            clock = SimulatedClock()
            i = Interpreter(build(), clock=clock)
            await i.start()
            await asyncio.sleep(0.02)
            i._processing = True
            t, i._event_loop_task = i._event_loop_task, None
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
            i.status = "running"
            clock._now += 1.5
            clock.pump()
            await asyncio.sleep(0.02)
            recs = [
                r["type"] for r in i.get_persisted_snapshot()["pending_events"]
            ]
            i._processing = False
            return recs

        recs = _run(main())
        self.assertEqual(recs, ["after.1000.lanes.waiting"])


# =============================================================================
# #108 — root target rejected at build
# =============================================================================
class TestRootTargetRejected(_Quiet):
    def test_always_to_root_is_invalid_config(self) -> None:
        with self.assertRaises(InvalidConfigError) as ctx:
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"always": "#m"}, "b": {}},
                }
            )
        self.assertIn("machine root", str(ctx.exception))

    def test_on_to_root_is_invalid_config(self) -> None:
        with self.assertRaises(InvalidConfigError):
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"on": {"GO": "#m"}}, "b": {}},
                }
            )


# =============================================================================
# #109 — done.invoke carries output
# =============================================================================
class TestDoneInvokeCarriesOutput(_Quiet):
    CHILD = {
        "id": "c",
        "initial": "w",
        "context": {"secret": "s3cr3t"},
        "states": {
            "w": {"always": "d"},
            "d": {"type": "final", "output": {"result": 42}},
        },
    }
    PARENT = {
        "id": "p",
        "initial": "w",
        "context": {"got": None},
        "states": {
            "w": {
                "invoke": {
                    "src": "kid",
                    "id": "kid",
                    "onDone": {"target": "d", "actions": "keep"},
                }
            },
            "d": {},
        },
    }

    def _logic(self):
        return MachineLogic(
            services={"kid": create_machine(self.CHILD)},
            actions={"keep": lambda i, c, e, a: c.__setitem__("got", e.data)},
        )

    def test_sync_and_async_deliver_output_not_context(self) -> None:
        s = SyncInterpreter(create_machine(self.PARENT, logic=self._logic()))
        s.start()
        for _ in range(50):
            if s.value == "d":
                break
            s.tick()
            time.sleep(0.01)
        self.assertEqual(s.context["got"], {"result": 42})

        async def main():
            i = await Interpreter(
                create_machine(self.PARENT, logic=self._logic())
            ).start()
            await asyncio.sleep(0.1)
            g = i.context["got"]
            await i.stop()
            return g

        self.assertEqual(_run(main()), {"result": 42})


# =============================================================================
# #110 — malformed snapshots are typed
# =============================================================================
class TestSnapshotShapeValidation(_Quiet):
    def test_every_malformed_shape_is_snapshotcorrupterror(self) -> None:
        m = create_machine({"id": "m", "initial": "a", "states": {"a": {}}})
        good = json.loads(SyncInterpreter(m).start().get_snapshot())
        shapes = {
            "no_status": {k: v for k, v in good.items() if k != "status"},
            "context_list": {**good, "context": [1, 2]},
            "status_garbage": {**good, "status": "banana"},
            "configuration_str": {**good, "configuration": "m.a"},
            "running_empty": {**good, "state_ids": [], "configuration": []},
        }
        for name, snap in shapes.items():
            with self.assertRaises(SnapshotCorruptError, msg=name):
                SyncInterpreter.from_snapshot(json.dumps(snap), m)


# =============================================================================
# #111 — _detach keeps provenance
# =============================================================================
class TestDetachKeepsProvenance(_Quiet):
    def test_engine_event_with_wait_true_stays_engine(self) -> None:
        cfg = {
            "id": "u",
            "initial": "a",
            "onUnhandled": "error",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }

        async def main():
            i = await Interpreter(create_machine(cfg)).start()
            await i.send(
                system_event("xstate.error.actor.kid", error="x"), wait=True
            )
            st = i.status
            await i.stop()
            return st

        self.assertEqual(_run(main()), "running")


# =============================================================================
# #113 — malformed events are typed
# =============================================================================
class TestInvalidEventTyped(_Quiet):
    def test_bad_shapes_raise_invalid_event_error(self) -> None:
        i = SyncInterpreter(
            create_machine({"id": "m", "initial": "a", "states": {"a": {}}}),
            strict=True,
        )
        i.start()
        for bad in ({"type": None}, {"type": 5}, {"no_type": 1}, 42, object()):
            with self.assertRaises(InvalidEventError, msg=repr(bad)):
                i.send(bad)  # type: ignore[arg-type]
        self.assertTrue(issubclass(InvalidEventError, XStateMachineError))
        self.assertTrue(issubclass(InvalidEventError, TypeError))
        i.stop()


# =============================================================================
# #114 — CancelledError from a hook is contained; loop death is reported
# =============================================================================
class TestLoopDeathIsReported(_Quiet):
    def test_plugin_cancellederror_is_contained(self) -> None:
        class Evil(PluginBase):
            def on_event_received(self, i, e):
                raise asyncio.CancelledError()

        async def main():
            i = Interpreter(
                create_machine(
                    {
                        "id": "m",
                        "initial": "a",
                        "context": {"n": 0},
                        "states": {"a": {"on": {"T": {"actions": "inc"}}}},
                    },
                    logic=MachineLogic(actions={"inc": _bump("n")}),
                )
            ).use(Evil())
            await i.start()
            r = await asyncio.wait_for(i.send("T", wait=True), 2)
            out = (i.status, r.changed, i.last_plugin_error is not None)
            await i.stop()
            return out

        self.assertEqual(_run(main()), ("running", True, True))

    def test_external_cancel_flips_status_and_fails_receipts(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(
                    {
                        "id": "m",
                        "initial": "a",
                        "states": {"a": {"on": {"T": "a"}}},
                    }
                )
            ).start()
            await asyncio.sleep(0)  # the loop task must have started
            i._event_loop_task.cancel()
            await asyncio.sleep(0.05)
            return i.status, isinstance(i.error, RuntimeError)

        self.assertEqual(_run(main()), ("error", True))


# =============================================================================
# #115 — SimulatedClock detaches on teardown
# =============================================================================
class TestClockDetach(_Quiet):
    def test_settlers_do_not_accumulate(self) -> None:
        clk = SimulatedClock()
        cfg = {"id": "m", "initial": "a", "states": {"a": {}}}
        for _ in range(25):
            i = SyncInterpreter(create_machine(cfg), clock=clk)
            i.start()
            i.stop()
        self.assertEqual(len(clk._settlers), 0)


# =============================================================================
# #116 — plain-sync invoke completes at the same point on both engines
# =============================================================================
class TestPlainSyncInvokeTimingParity(_Quiet):
    CFG = {
        "id": "d8",
        "initial": "idle",
        "context": {"ok": 0, "cancel": 0},
        "states": {
            "idle": {"on": {"GO": "busy"}},
            "busy": {
                "invoke": {
                    "id": "s",
                    "src": "work",
                    "onDone": {"target": "idle", "actions": ["ok"]},
                },
                "on": {"CANCEL": {"target": "idle", "actions": ["cancel"]}},
            },
        },
    }

    def _logic(self):
        return MachineLogic(
            actions={"ok": _bump("ok"), "cancel": _bump("cancel")},
            services={"work": lambda i, c, e: 1},
        )

    def test_go_cancel_script_agrees(self) -> None:
        s = SyncInterpreter(create_machine(self.CFG, logic=self._logic()))
        s.start()
        for _ in range(10):
            s.send("GO")
            s.send("CANCEL")
        sync_ctx = dict(s.context)
        s.stop()

        async def main():
            i = await Interpreter(
                create_machine(self.CFG, logic=self._logic())
            ).start()
            for _ in range(10):
                await i.send("GO")
                await i.send("CANCEL")
            # Settle on the SIGNAL, not a fixed spin: since #149 a plain
            # service completes via an executor hop, so on a slow runner
            # the last `done.invoke` may still be in flight after N yields.
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and not (
                i.value == "idle"
                and i.context["ok"] + i.context["cancel"] >= 10
            ):
                await asyncio.sleep(0.01)
            out = dict(i.context)
            await i.stop()
            return out

        self.assertEqual(sync_ctx, _run(main()))
        self.assertEqual(sync_ctx, {"ok": 10, "cancel": 0})


# =============================================================================
# #117 / #128 / #135 — from_snapshot clock=, restart_timers, dormancy
# =============================================================================
class TestRestoreClockAndTimers(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"after": {"50": "b"}}, "b": {}},
    }

    def test_clock_param_and_timer_rearm(self) -> None:
        async def main():
            clk = SimulatedClock()
            i = await Interpreter(create_machine(self.CFG), clock=clk).start()
            snap = i.get_snapshot()
            await i.stop()
            c2 = SimulatedClock()
            i2 = Interpreter.from_snapshot(
                snap, create_machine(self.CFG), clock=c2
            )
            self.assertIs(i2.clock, c2)
            self.assertTrue(i2.has_dormant_timers)
            self.assertEqual(
                i2.status, "running"
            )  # documented: not a liveness signal
            await i2.start()
            await c2.increment(100)
            await asyncio.sleep(0.02)
            static = i2.value
            await i2.stop()
            c3 = SimulatedClock()
            i3 = Interpreter.from_snapshot(
                snap, create_machine(self.CFG), clock=c3, restart_timers=True
            )
            await i3.start()
            self.assertFalse(i3.has_dormant_timers)
            await c3.increment(100)
            await asyncio.sleep(0.02)
            rearmed = i3.value
            await i3.stop()
            return static, rearmed

        self.assertEqual(_run(main()), ("a", "b"))


# =============================================================================
# #118 / #131 — event record fidelity
# =============================================================================
class TestEventRecordFidelity(_Quiet):
    def test_after_event_telemetry_round_trips(self) -> None:
        ev = AfterEvent("after.500", scheduled_for=100.0, fired_at=100.7)
        back = restore_event(json.loads(json.dumps(persist_event(ev))))
        self.assertEqual((back.scheduled_for, back.fired_at), (100.0, 100.7))
        self.assertAlmostEqual(back.lateness_ms, 700.0, places=3)

    def test_non_json_data_is_refused_typed(self) -> None:
        with self.assertRaises(SnapshotSerializationError):
            persist_event(
                DoneEvent(
                    "done.invoke.x", {"amt": decimal.Decimal("1.50")}, "x"
                )
            )


# =============================================================================
# #120 — async trip spares completions
# =============================================================================
class TestAsyncTripSparesCompletion(_Quiet):
    def test_completion_during_trip_is_delivered(self) -> None:
        cfg = {
            "id": "m",
            "maxIterations": 5,
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {"id": "svc", "src": "svc", "onDone": "ok"},
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        }
                    },
                },
                "ok": {},
            },
        }

        async def svc(i, c, e):
            await asyncio.sleep(0.05)
            return 1

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(services={"svc": svc}))
            ).start()
            await i.send("SPIN")
            await asyncio.sleep(0.5)
            v = i.value
            await i.stop()
            return v

        self.assertEqual(_run(main()), "ok")


# =============================================================================
# #121 — duck-typed logic is not mutated
# =============================================================================
class TestDuckTypedLogicNotMutated(_Quiet):
    def test_registries_untouched(self) -> None:
        class Duck:
            def __init__(self):
                self.actions = {"fetch_data": lambda i, c, e, a: None}
                self.guards: Dict = {}
                self.services: Dict = {}
                self.delays: Dict = {}

        d = Duck()
        before = dict(d.actions)
        m = create_machine({"id": "m", "initial": "a", "states": {"a": {"entry": "fetchData"}}}, logic=d)  # type: ignore[arg-type]
        self.assertEqual(d.actions, before)
        self.assertIn("fetchData", m.logic.actions)


# =============================================================================
# #122 — tick() drains chained deadlines
# =============================================================================
class TestTickDrainsChain(_Quiet):
    def test_after_zero_chain_in_one_tick(self) -> None:
        cfg = {
            "id": "o",
            "initial": "a",
            "states": {
                "a": {"after": {0: "b"}},
                "b": {"after": {0: "c"}},
                "c": {"after": {0: "d"}},
                "d": {},
            },
        }
        s = SyncInterpreter(create_machine(cfg))
        s.start()
        s.tick()
        self.assertEqual(s.value, "d")
        s.stop()


# =============================================================================
# #123 / #124 / #129 — hook parity
# =============================================================================
class TestHookParity(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"T": "b"}}, "b": {}},
    }

    def test_send_to_stopped_fires_not_running_on_both(self) -> None:
        d1 = _Drops()
        s = SyncInterpreter(create_machine(self.CFG)).use(d1)
        s.start()
        s.stop()
        s.send("T")

        async def main():
            d2 = _Drops()
            i = Interpreter(create_machine(self.CFG)).use(d2)
            await i.start()
            await i.stop()
            await i.send("T")
            return d2.dropped

        self.assertEqual([r for _, r in d1.dropped], ["not_running"])
        self.assertEqual([r for _, r in _run(main())], ["not_running"])

    def test_init_on_transition_record_on_both(self) -> None:
        def spy(store):
            class S(PluginBase):
                def on_transition(self, i, src, tgt, tr):
                    store.append(tr.event)

            return S()

        a: List = []
        s = SyncInterpreter(create_machine(self.CFG)).use(spy(a))
        s.start()
        s.send("T")
        s.stop()

        async def main():
            b: List = []
            i = Interpreter(create_machine(self.CFG)).use(spy(b))
            await i.start()
            await i.send("T", wait=True)
            await i.stop()
            return b

        self.assertEqual(a, _run(main()))
        self.assertEqual(a[0], "___xstate_statemachine_init___")

    def test_stop_reports_abandoned_events_on_both(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"X": "a", "SLOW": {"actions": "slow"}}}},
        }

        async def slow(i, c, e, a):
            await asyncio.sleep(0.3)

        async def main():
            d = _Drops()
            i = Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"slow": slow}))
            ).use(d)
            await i.start()
            asyncio.ensure_future(i.send("SLOW"))
            await asyncio.sleep(0.02)
            for _ in range(4):
                i.send("X")
            await i.stop()
            return [r for _, r in d.dropped]

        self.assertEqual(_run(main()), ["stopped"] * 4)


# =============================================================================
# #125 — deferred replay does not fold into the triggering receipt
# =============================================================================
class TestReplayIsItsOwnMacrostep(_Quiet):
    def test_arm_receipt_reports_arm_transition_only(self) -> None:
        cfg = {
            "id": "g",
            "initial": "a",
            "onUnhandled": "defer",
            "context": {"late": 0},
            "states": {
                "a": {"on": {"ARM": "b"}},
                "b": {"on": {"LATE": {"target": "c", "actions": "l"}}},
                "c": {},
            },
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg, logic=MachineLogic(actions={"l": _bump("late")})
                )
            ).start()
            await i.send("LATE")
            r = await i.send("ARM", wait=True)
            await asyncio.sleep(0.05)
            out = (sorted(r.state_ids), i.value, i.context["late"])
            await i.stop()
            return out

        ids, final, late = _run(main())
        self.assertEqual(ids, ["g.b"], "ARM's receipt describes ARM")
        self.assertEqual(
            (final, late), ("c", 1), "LATE still replays afterwards"
        )


# =============================================================================
# #126 — LoggingInspector redacts
# =============================================================================
class TestLoggingInspectorRedaction(_Quiet):
    def test_default_denylist_redacts_nested(self) -> None:
        out = redact(
            {
                "apiKey": "x",
                "user": {"password": "y", "name": "ok"},
                "l": [{"token": "z"}],
            }
        )
        self.assertEqual(
            out,
            {
                "apiKey": "***",
                "user": {"password": "***", "name": "ok"},
                "l": [{"token": "***"}],
            },
        )

    def test_plugin_never_logs_secret(self) -> None:
        import io

        buf = io.StringIO()
        h = logging.StreamHandler(buf)
        lg = logging.getLogger("xstate_statemachine")
        logging.disable(logging.NOTSET)
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
        try:
            i = SyncInterpreter(
                create_machine(
                    {
                        "id": "m",
                        "initial": "a",
                        "context": {"api_key": "SECRET-KEY"},
                        "states": {"a": {"on": {"T": "b"}}, "b": {}},
                    }
                )
            ).use(LoggingInspector())
            i.start()
            i.send("T", password="hunter2")
        finally:
            lg.removeHandler(h)
            logging.disable(logging.CRITICAL)
        text = buf.getvalue()
        self.assertNotIn("SECRET-KEY", text)
        self.assertNotIn("hunter2", text)
        self.assertIn("***", text)


# =============================================================================
# #127 — async-def hook surfaces; on_plugin_error
# =============================================================================
class TestPluginFailureSurface(_Quiet):
    def test_async_def_hook_reported(self) -> None:
        class Bad(PluginBase):
            async def on_transition(self, i, s, t, tr):
                pass

        class Watch(PluginBase):
            def __init__(self):
                self.seen = []

            def on_plugin_error(self, i, plugin, hook, err):
                self.seen.append(
                    (type(plugin).__name__, hook, type(err).__name__)
                )

        async def main():
            w = Watch()
            i = (
                Interpreter(
                    create_machine(
                        {
                            "id": "m",
                            "initial": "a",
                            "states": {"a": {"on": {"T": "b"}}, "b": {}},
                        }
                    )
                )
                .use(Bad())
                .use(w)
            )
            await i.start()
            await i.send("T", wait=True)
            out = (
                i.last_plugin_error[1],
                type(i.last_plugin_error[2]).__name__,
                w.seen,
            )
            await i.stop()
            return out

        hook, err, seen = _run(main())
        self.assertEqual((hook, err), ("on_transition", "TypeError"))
        self.assertIn(("Bad", "on_transition", "TypeError"), seen)


# =============================================================================
# #130 — escalate routes to onError
# =============================================================================
class TestEscalateRoutesToOnError(_Quiet):
    def test_parent_reaches_on_error_target(self) -> None:
        child = {
            "id": "c",
            "initial": "w",
            "states": {
                "w": {
                    "entry": [
                        {
                            "type": "escalate",
                            "params": {"error": "child exploded"},
                        }
                    ]
                }
            },
        }
        parent = {
            "id": "p",
            "initial": "w",
            "states": {
                "w": {
                    "invoke": {"src": "kid", "id": "kid", "onError": "caught"}
                },
                "caught": {},
            },
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    parent,
                    logic=MachineLogic(
                        services={"kid": create_machine(child)}
                    ),
                )
            ).start()
            await asyncio.sleep(0.2)
            v = i.value
            await i.stop()
            return v

        self.assertEqual(_run(main()), "caught")


# =============================================================================
# #132 / #133 / #134 / #136
# =============================================================================
class TestValidationAndHooks(_Quiet):
    def test_ambiguous_bare_state_in_is_rejected(self) -> None:
        cfg = {
            "id": "m",
            "type": "parallel",
            "states": {
                "L": {"initial": "work", "states": {"work": {}, "idle": {}}},
                "R": {"initial": "idle", "states": {"work": {}, "idle": {}}},
                "G": {
                    "initial": "q",
                    "states": {
                        "q": {
                            "on": {
                                "CHECK": {
                                    "target": "yes",
                                    "guard": {
                                        "type": "stateIn",
                                        "params": {"state": "work"},
                                    },
                                }
                            }
                        },
                        "yes": {},
                    },
                },
            },
        }
        i = SyncInterpreter(create_machine(cfg))
        i.start()
        with self.assertRaises(InvalidConfigError):
            i.send("CHECK")

    def test_send_to_unresolved_is_observable(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "T": {
                            "actions": {
                                "type": "sendTo",
                                "params": {"to": "nonexistent", "event": "X"},
                            }
                        }
                    }
                }
            },
        }

        async def main():
            d = _Drops()
            i = Interpreter(create_machine(cfg)).use(d)
            await i.start()
            r = await i.send("T", wait=True)
            out = (d.dropped, r.error is not None, i.last_error is not None)
            await i.stop()
            return out

        dropped, rerr, lerr = _run(main())
        self.assertEqual(dropped, [("X", "unresolved_target")])
        self.assertTrue(rerr and lerr)

    def test_on_resolve_error_hook_fires(self) -> None:
        seen: List = []

        class R(PluginBase):
            def on_resolve_error(self, i, err, ev):
                seen.append((type(err).__name__, ev.type))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = create_machine(
                {
                    "id": "b",
                    "initial": "a",
                    "states": {"a": {"on": {"GO": "nowhere"}}},
                },
                strict_targets=False,
            )

        async def main():
            i = Interpreter(m).use(R())
            await i.start()
            await i.send("GO", wait=True)
            await i.stop()

        _run(main())
        self.assertEqual(seen, [("StateNotFoundError", "GO")])

    def test_cyclic_config_is_typed(self) -> None:
        a: Dict = {"initial": "x", "states": {}}
        a["states"]["x"] = a
        with self.assertRaises(InvalidConfigError) as ctx:
            create_machine({"id": "m", "initial": "a", "states": {"a": a}})
        self.assertIn("cycle", str(ctx.exception))


# =============================================================================
# #137 / #138 — provenance API
# =============================================================================
class TestProvenanceApi(_Quiet):
    def test_exported_from_root(self) -> None:
        for name in (
            "is_system_event",
            "system_event",
            "DoneEvent",
            "AfterEvent",
            "ErrorEvent",
            "ENGINE_EVENT_SHAPES",
        ):
            self.assertTrue(hasattr(xsm, name), name)

    def test_provenance_survives_deepcopy_and_pickle(self) -> None:
        e = system_event("___xstate_statemachine_init___")
        self.assertTrue(is_system_event(copy.deepcopy(e)))
        self.assertTrue(is_system_event(pickle.loads(pickle.dumps(e))))
        self.assertFalse(is_system_event(copy.deepcopy(Event("T"))))


# =============================================================================
# #102 ride-along — child actors: snapshot recursion and deterministic start
# =============================================================================
class TestChildActorSnapshotRideAlongs(_Quiet):
    """Two ride-alongs surfaced by the #102 mid-step guard under load.

    1. A non-blocking sync child used to be *started* on its pump thread, so
       a parent snapshotting immediately after the spawn action could see
       a registered child with no grandchildren yet. The child now starts
       on the spawning thread; the snapshot is deterministic.
    2. The #102 refusal applies to the ROOT of `get_persisted_snapshot()`
       only; a child caught mid-step is waited for (bounded), never turns
       into a `SnapshotMidStepError` for the parent's snapshot.
    """

    GC = {"id": "gc", "initial": "g", "states": {"g": {}}}
    CHILD = {
        "id": "kid",
        "initial": "i",
        "context": {},
        "states": {
            "i": {
                "entry": [
                    {"type": "spawnChild", "params": {"src": "gc", "id": "g"}}
                ]
            }
        },
    }
    PARENT = {
        "id": "p",
        "initial": "a",
        "context": {},
        "states": {
            "a": {
                "entry": [
                    {
                        "type": "spawnChild",
                        "params": {"src": "kid", "id": "w"},
                    }
                ]
            }
        },
    }

    def _parent(self) -> SyncInterpreter:
        kid_logic = MachineLogic(
            services={"gc": lambda a, b, d: create_machine(self.GC)}
        )
        return SyncInterpreter(
            create_machine(
                self.PARENT,
                logic=MachineLogic(
                    services={
                        "kid": lambda i, c, e: create_machine(
                            self.CHILD, logic=kid_logic
                        )
                    }
                ),
            )
        )

    def test_grandchild_present_immediately_after_start(self) -> None:
        # 50 iterations: the pre-fix race was load-dependent, one miss fails.
        for _ in range(50):
            interp = self._parent().start()
            try:
                data = json.loads(interp.get_snapshot())
                self.assertIn(
                    "p:w:g", data["actors"]["p:w"]["snapshot"]["actors"]
                )
            finally:
                interp.stop()

    def test_child_mid_step_is_waited_for_not_refused(self) -> None:
        interp = self._parent().start()
        self.addCleanup(interp.stop)
        child = interp._actors["p:w"]
        # Simulate the child being caught between exit set and entry set.
        child._is_processing = True
        saved = set(child._active_state_nodes)
        child._active_state_nodes.clear()

        def _settle() -> None:
            time.sleep(0.02)
            child._active_state_nodes.update(saved)
            child._is_processing = False

        threading.Thread(target=_settle).start()
        data = interp.get_persisted_snapshot()  # must not raise
        self.assertIn("p:w", data["actors"])
        self.assertEqual(
            ["kid.i"], data["actors"]["p:w"]["snapshot"]["state_ids"]
        )

    def test_root_mid_step_is_still_refused(self) -> None:
        interp = SyncInterpreter(
            create_machine(
                {"id": "m", "initial": "a", "states": {"a": {}, "b": {}}}
            )
        ).start()
        self.addCleanup(interp.stop)
        interp._is_processing = True
        interp._active_state_nodes.clear()
        with self.assertRaises(SnapshotMidStepError):
            interp.get_persisted_snapshot()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
