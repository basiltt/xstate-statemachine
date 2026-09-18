"""Regression tests for the round-3 re-verification findings (#84–#99 and
the reopened #31 / #77 / #79).

One class per issue. Each test is the reporter's acceptance criterion in
miniature, so a future regression names the issue it reopens.
"""

from __future__ import annotations

import asyncio
import json
import logging
import types
import unittest
import warnings
from typing import Any, Dict, List

from src.xstate_statemachine import (
    ErrorEvent,
    Event,
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    RunawayChainError,
    SimulatedClock,
    StateNotFoundError,
    SyncInterpreter,
    UnknownEventError,
    create_machine,
)
from src.xstate_statemachine.events import (
    AfterEvent,
    DoneEvent,
    is_system_event,
    persist_event,
    restore_event,
    system_event,
)
from src.xstate_statemachine.plugins import LoggingInspector, PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _bump(key: str):
    return lambda i, c, e, a: c.__setitem__(key, c[key] + 1)


# =============================================================================
# #84 — Receipt.deferred
# =============================================================================
class TestReceiptDeferred(_Quiet):
    CFG: Dict[str, Any] = {
        "id": "g",
        "initial": "closed",
        "onUnhandled": "defer",
        "context": {"f": 0},
        "states": {
            "closed": {"on": {"OPEN": "open"}},
            "open": {"on": {"FILL": {"target": "filled", "actions": "mark"}}},
            "filled": {},
        },
    }

    def _logic(self) -> MachineLogic:
        return MachineLogic(actions={"mark": _bump("f")})

    def test_async_receipt_says_deferred_not_noop(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(self.CFG, logic=self._logic())
            ).start()
            r = await i.send("FILL", wait=True)
            r2 = await i.send("OPEN", wait=True)
            await asyncio.sleep(0.02)
            out = (r.deferred, r.changed, r.error, r2.deferred, i.value)
            await i.stop()
            return out

        deferred, changed, err, later, state = asyncio.run(main())
        self.assertTrue(deferred)
        self.assertFalse(changed)
        self.assertIsNone(err)
        self.assertFalse(later, "a processed event is not deferred")
        self.assertEqual(state, "filled")

    def test_sync_receipt_says_deferred(self) -> None:
        i = SyncInterpreter(create_machine(self.CFG, logic=self._logic()))
        i.start()
        r = i.send("FILL", wait=True)
        self.assertTrue(r.deferred)
        r2 = i.send("OPEN", wait=True)
        self.assertFalse(r2.deferred)
        self.assertEqual(i.value, "filled")
        i.stop()

    def test_correct_noop_is_not_deferred(self) -> None:
        cfg = {"id": "n", "initial": "a", "states": {"a": {"on": {"X": "a"}}}}
        i = SyncInterpreter(create_machine(cfg))
        i.start()
        r = i.send("NOPE", wait=True)
        self.assertFalse(r.deferred)
        self.assertFalse(r.changed)
        i.stop()


# =============================================================================
# #85 — provenance is not user-settable
# =============================================================================
class TestProvenanceNotForgeable(_Quiet):
    def test_event_constructor_has_no_system_parameter(self) -> None:
        with self.assertRaises(TypeError):
            Event("X", system=True)  # type: ignore[call-arg]

    def test_system_property_is_read_only_and_false_for_users(self) -> None:
        e = Event("X")
        self.assertFalse(e.system)
        self.assertFalse(is_system_event(e))
        with self.assertRaises(Exception):
            e.system = True  # type: ignore[misc]

    def test_mutating_private_slot_with_a_bool_does_not_forge(self) -> None:
        e = Event("NOT_DECLARED")
        object.__setattr__(e, "_provenance", True)
        self.assertFalse(is_system_event(e), "identity sentinel, not a bool")
        cfg = {
            "id": "t",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg), strict=True)
        i.start()
        with self.assertRaises(UnknownEventError):
            i.send(e)
        i.stop()

    def test_engine_minted_event_is_system(self) -> None:
        e = system_event("___xstate_statemachine_init___")
        self.assertTrue(e.system)
        self.assertTrue(is_system_event(e))
        self.assertEqual(e, Event("___xstate_statemachine_init___"))


# =============================================================================
# #86 / #87 — provenance and engine events survive a snapshot
# =============================================================================
class TestSnapshotRoundTripsEngineEvents(_Quiet):
    UNH = {
        "id": "u",
        "initial": "a",
        "onUnhandled": "error",
        "states": {"a": {"on": {"GO": "b"}}, "b": {}},
    }

    def test_persist_restore_every_kind(self) -> None:
        cases = [
            Event("USER", {"k": 1}),
            system_event("___xstate_statemachine_init___"),
            system_event("xstate.error.actor.kid", error="x"),
            DoneEvent("done.invoke.svc", {"n": 2}, "svc"),
            ErrorEvent("error.platform.svc", ValueError("boom"), "svc"),
            AfterEvent("after.500"),
        ]
        for ev in cases:
            rec = json.loads(json.dumps(persist_event(ev)))
            back = restore_event(rec)
            self.assertEqual(type(back), type(ev), rec)
            self.assertEqual(back.type, ev.type)
            self.assertEqual(is_system_event(back), is_system_event(ev), rec)
        err = restore_event(persist_event(cases[4]))
        self.assertIn("boom", str(err.error))

    def test_v1_record_without_kind_rederives_engine_shape(self) -> None:
        self.assertTrue(
            is_system_event(
                restore_event({"type": "xstate.error.actor.k", "payload": {}})
            )
        )
        self.assertTrue(
            is_system_event(
                restore_event(
                    {"type": "___xstate_statemachine_init___", "payload": {}}
                )
            )
        )
        self.assertFalse(
            is_system_event(
                restore_event({"type": "done.review", "payload": {}})
            )
        )

    def test_restored_escalate_does_not_fail_on_unhandled_error(self) -> None:
        async def main():
            it = await Interpreter(create_machine(self.UNH)).start()
            it._put_inbox(system_event("xstate.error.actor.kid", error="x"))
            snap = json.dumps(it.get_persisted_snapshot())
            await it.stop()
            it2 = Interpreter.from_snapshot(snap, create_machine(self.UNH))
            await it2.start()
            await asyncio.sleep(0.05)
            st = it2.status
            await it2.stop()
            return st

        self.assertEqual(asyncio.run(main()), "running")

    def test_pending_done_and_error_events_are_persisted(self) -> None:
        cfg = {
            "id": "m",
            "initial": "w",
            "states": {
                "w": {"invoke": {"src": "svc", "id": "svc", "onError": "bad"}},
                "bad": {"type": "final"},
            },
        }

        async def main():
            it = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        services={"svc": lambda i, c, e: asyncio.sleep(10)}
                    ),
                )
            ).start()
            it._put_inbox(
                ErrorEvent("error.platform.svc", ValueError("boom"), "svc")
            )
            it._put_inbox(DoneEvent("done.invoke.svc", {"k": 1}, "svc"))
            recs = it.get_persisted_snapshot()["pending_events"]
            await it.stop()
            return recs

        recs = asyncio.run(main())
        self.assertEqual([r["kind"] for r in recs], ["error", "done"])
        self.assertEqual(
            [r["type"] for r in recs],
            ["error.platform.svc", "done.invoke.svc"],
        )


# =============================================================================
# #77 / #88 / #94 — sync budget: observable, per-chain, completions exempt
# =============================================================================
class TestSyncChainBudget(_Quiet):
    def test_overflow_is_observable(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 10,
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                "cnt",
                                {"type": "raise", "params": {"event": "SPIN"}},
                            ]
                        }
                    }
                }
            },
        }
        dropped: List = []

        class Spy(PluginBase):
            def on_event_dropped(self, interp, event, reason):
                dropped.append(reason)

        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(actions={"cnt": _bump("n")})
            )
        ).use(Spy())
        i.start()
        r = i.send("SPIN", wait=True)
        self.assertIsInstance(r.error, RunawayChainError)
        self.assertFalse(i.last_transition_ok)
        self.assertIsInstance(i.last_error, RunawayChainError)
        self.assertEqual(i.status, "running", "the machine survives the trip")
        self.assertTrue(dropped and all(x == "chain_budget" for x in dropped))
        i.stop()

    def test_runaway_does_not_starve_unrelated_events_in_same_batch(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"inner": 0, "spin": 0},
            "maxIterations": 50,
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                "cs",
                                {"type": "raise", "params": {"event": "SPIN"}},
                            ]
                        },
                        "WORK": {
                            "actions": [
                                {"type": "raise", "params": {"event": "INNER"}}
                            ]
                        },
                        "INNER": {"actions": "ci"},
                    }
                }
            },
        }
        i = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(
                    actions={"cs": _bump("spin"), "ci": _bump("inner")}
                ),
            )
        )
        i.start()
        i.send_events(["SPIN"] + ["WORK"] * 5)
        self.assertEqual(i.context["inner"], 5)
        self.assertEqual(i.context["spin"], 51)
        i.stop()

    def test_sync_service_completion_survives_a_trip(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 20,
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        },
                        "GO": "work",
                    }
                },
                "work": {
                    "invoke": {"src": "svc", "id": "svc", "onDone": "done"}
                },
                "done": {},
            },
        }
        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(services={"svc": lambda i, c, e: 1})
            )
        )
        i.start()
        i.send_events(["SPIN", "GO"])
        self.assertEqual(i.value, "done")
        i.stop()

    def test_completion_arriving_mid_runaway_is_kept(self) -> None:
        """A `done.invoke` queued while a chain is tripping is pulled out of
        the discarded tail and delivered."""
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 5,
            "states": {
                "a": {
                    "invoke": {"src": "svc", "id": "svc", "onDone": "done"},
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        }
                    },
                },
                "done": {},
            },
        }
        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(services={"svc": lambda i, c, e: 1})
            )
        )
        i.start()
        self.assertEqual(i.value, "done")
        i.stop()


# =============================================================================
# #90 — async action-side send() is budgeted
# =============================================================================
class TestAsyncSelfSendBudget(_Quiet):
    def test_action_side_send_loop_is_bounded(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "maxIterations": 100,
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
            ok = i.last_transition_ok
            await i.stop()
            return n, ok

        n, ok = asyncio.run(main())
        self.assertLessEqual(n, 102)
        self.assertFalse(ok, "the trip is observable on the async engine too")


# =============================================================================
# #89 — **kwargs is not consent
# =============================================================================
class TestClockKwargsNotConsent(_Quiet):
    def test_kwargs_clock_never_receives_sync(self) -> None:
        got: List = []

        class LegacyWrapper:
            def __init__(self):
                self.inner = SimulatedClock()

            def now(self):
                return self.inner.now()

            def set_timeout(self, fn, delay_sec, **kwargs):
                got.append(sorted(kwargs))
                assert "sync" not in kwargs, kwargs
                return self.inner.set_timeout(
                    fn, delay_sec, owner=kwargs.get("owner")
                )

            def clear_timeout(self, h):
                self.inner.clear_timeout(h)

            def pump(self):
                return self.inner.pump()

        cfg = {
            "id": "c",
            "initial": "a",
            "states": {"a": {"after": {"10": "b"}}, "b": {}},
        }
        clk = LegacyWrapper()
        i = SyncInterpreter(create_machine(cfg), clock=clk)
        i.start()
        self.assertTrue(got and all("sync" not in k for k in got))
        clk.inner.increment(10)
        i.tick()
        self.assertEqual(i.value, "b")
        i.stop()


# =============================================================================
# #91 / #92 / #93 — logic-name resolution
# =============================================================================
class TestLogicNameResolutionRound3(_Quiet):
    @staticmethod
    def _f1(i, c, e, a):
        pass

    @staticmethod
    def _f2(i, c, e, a):
        pass

    CFG = {"id": "m", "initial": "a", "states": {"a": {"entry": "fetchData"}}}

    def test_exact_key_with_shadowed_duplicate_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_machine(
                self.CFG,
                logic=MachineLogic(
                    actions={"fetch_data": self._f1, "fetchData": self._f2}
                ),
            )
        msgs = [str(x.message) for x in w if x.category is UserWarning]
        self.assertTrue(
            any("DIFFERENT callables" in m and "fetchData" in m for m in msgs),
            msgs,
        )

    def test_create_machine_does_not_mutate_caller_logic(self) -> None:
        ml = MachineLogic(actions={"fetch_data": self._f1})
        before = dict(ml.actions)
        m = create_machine(self.CFG, logic=ml)
        self.assertEqual(ml.actions, before)
        self.assertIn(
            "fetchData", m.logic.actions, "the MACHINE has the alias"
        )
        self.assertIsNot(m.logic.actions, ml.actions)

    def test_second_machine_from_same_logic_still_guards_ambiguity(
        self,
    ) -> None:
        ml = MachineLogic(
            actions={"fetch_data": self._f1, "fetchdata": self._f2}
        )
        with self.assertRaises(InvalidConfigError):
            create_machine(self.CFG, logic=ml)
        with self.assertRaises(
            InvalidConfigError,
            msg="first failure must not have mutated `ml` into passing",
        ):
            create_machine(self.CFG, logic=ml)

    def test_logic_modules_duplicate_normalised_names_is_an_error(
        self,
    ) -> None:
        mod = types.ModuleType("m93")
        exec(
            "def fetch_data(i,c,e,a): pass\ndef fetchData(i,c,e,a): pass",
            mod.__dict__,
        )
        with self.assertRaises(InvalidConfigError) as ctx:
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"entry": "FETCHDATA"}},
                },
                logic_modules=[mod],
            )
        self.assertIn("ambiguous", str(ctx.exception))

    def test_logic_modules_exact_key_still_wins(self) -> None:
        mod = types.ModuleType("m93b")
        exec(
            "def fetch_data(i,c,e,a): pass\ndef fetchData(i,c,e,a): pass",
            mod.__dict__,
        )
        m = create_machine(self.CFG, logic_modules=[mod])
        self.assertIs(m.logic.actions["fetchData"], mod.fetchData)


# =============================================================================
# #95 / #96 / #97 / #98 — ErrorEvent & provenance edges
# =============================================================================
class TestErrorEventEdges(_Quiet):
    CFG = {
        "id": "m",
        "initial": "w",
        "states": {
            "w": {"invoke": {"src": "svc", "id": "svc", "onError": "bad"}},
            "bad": {"type": "final"},
        },
    }

    def test_library_does_not_trip_its_own_deprecation(self) -> None:
        async def blow(i, c, e):
            raise ValueError("boom")

        async def main():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                it = Interpreter(
                    create_machine(
                        self.CFG, logic=MachineLogic(services={"svc": blow})
                    )
                ).use(LoggingInspector())
                await it.start()
                await asyncio.sleep(0.1)
                await it.stop()
            return [
                str(w.message)
                for w in caught
                if issubclass(w.category, DeprecationWarning)
                and "ErrorEvent.data" in str(w.message)
            ]

        self.assertEqual(asyncio.run(main()), [])

    def test_resolve_event_spec_always_yields_dict_payload(self) -> None:
        i = SyncInterpreter(
            create_machine({"id": "t", "initial": "a", "states": {"a": {}}})
        )
        i.start()
        for src in (
            ErrorEvent("error.platform.svc", ValueError("boom"), "svc"),
            DoneEvent("done.invoke.svc", {"k": 1}, "svc"),
            DoneEvent("done.invoke.svc", 42, "svc"),
            AfterEvent("after.5"),
        ):
            ev = i._resolve_event_spec(src, Event("X"))
            self.assertIsInstance(ev.payload, dict, type(src).__name__)
        err_ev = i._resolve_event_spec(
            ErrorEvent("error.platform.svc", ValueError("boom"), "svc"),
            Event("X"),
        )
        self.assertIsInstance(err_ev.payload["error"], ValueError)
        i.stop()

    def test_escalate_is_an_error_event(self) -> None:
        seen: Dict[str, Any] = {}
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
                    "invoke": {"src": "kid", "id": "kid"},
                    "on": {
                        "xstate.error.actor.p:kid": {
                            "target": "caught",
                            "actions": "look",
                        }
                    },
                },
                "caught": {},
            },
        }

        async def main():
            it = await Interpreter(
                create_machine(
                    parent,
                    logic=MachineLogic(
                        services={"kid": create_machine(child)},
                        actions={"look": lambda i, c, e, a: seen.update(ev=e)},
                    ),
                )
            ).start()
            await asyncio.sleep(0.2)
            st = it.value
            await it.stop()
            return st

        self.assertEqual(asyncio.run(main()), "caught")
        self.assertIsInstance(seen["ev"], ErrorEvent)
        self.assertIn("child exploded", str(seen["ev"].error))

    def test_strict_rejects_forged_engine_shaped_user_events(self) -> None:
        cfg = {
            "id": "t",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg), strict=True)
        i.start()
        for t in (
            "done.invoke.NEVER",
            "after.party",
            "xstate.whatever",
            "___xstate_forged",
            "error.platform.x",
        ):
            with self.assertRaises(UnknownEventError, msg=t):
                i.send(t)
        i.stop()

    def test_strict_still_exempts_real_engine_events(self) -> None:
        cfg = {
            "id": "t",
            "initial": "a",
            "states": {
                "a": {"invoke": {"src": "q", "id": "q", "onDone": "b"}},
                "b": {},
            },
        }
        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(services={"q": lambda i, c, e: 1})
            ),
            strict=True,
        )
        i.start()
        self.assertEqual(i.value, "b")
        i.stop()


# =============================================================================
# #99 — sync child machine failure
# =============================================================================
class TestSyncChildMachineFailure(_Quiet):
    BAD = {
        "id": "bad",
        "initial": "s",
        "actionErrorPolicy": "fail",
        "states": {"s": {"entry": ["boom"]}},
    }

    @staticmethod
    def _boom(i, c, e, a):
        raise RuntimeError("child exploded")

    def _kid(self):
        return create_machine(
            self.BAD, logic=MachineLogic(actions={"boom": self._boom})
        )

    def test_on_error_receives_error_event(self) -> None:
        seen: List = []
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "kid",
                        "id": "kid",
                        "onError": {"target": "c", "actions": "note"},
                    }
                },
                "c": {},
            },
        }
        i = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={"kid": self._kid()},
                    actions={"note": lambda i, c, e, a: seen.append(e)},
                ),
            )
        )
        i.start()
        import time

        for _ in range(100):
            if i.value == "c":
                break
            i.tick()
            time.sleep(0.01)
        self.assertEqual(i.value, "c")
        self.assertIsInstance(seen[0], ErrorEvent)
        # The child ran under `actionErrorPolicy: "fail"`, so its recorded
        # error is the policy's `TransitionFailedError`; the original
        # RuntimeError is its cause. Same shape the async engine delivers.
        err = seen[0].error
        self.assertIn("boom", str(err))
        self.assertIsInstance(err.__cause__ or err.__context__, RuntimeError)
        i.stop()

    def test_unhandled_child_failure_fails_parent_like_a_service(self) -> None:
        parent = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "kid", "id": "kid"}}},
        }
        i = SyncInterpreter(
            create_machine(
                parent, logic=MachineLogic(services={"kid": self._kid()})
            )
        )
        i.start()
        import time

        for _ in range(100):
            if i.status == "error":
                break
            i.tick()
            time.sleep(0.01)
        self.assertEqual(i.status, "error")
        self.assertIsNotNone(i.error)


# =============================================================================
# #31 — runtime parity for unresolvable targets under strict_targets=False
# =============================================================================
class TestUnresolvableTargetParity(_Quiet):
    def test_both_engines_expose_same_surface(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = create_machine(
                {
                    "id": "b",
                    "initial": "a",
                    "states": {"a": {"on": {"GO": "nowhere", "OK": "a"}}},
                },
                strict_targets=False,
            )

        def surface(i, r):
            return (
                i.status,
                i.last_transition_ok,
                type(i.last_error).__name__ if i.last_error else None,
                type(r.error).__name__ if r.error else None,
                i.value,
            )

        s = SyncInterpreter(m)
        s.start()
        sync_go = surface(s, s.send("GO", wait=True))
        sync_ok = surface(s, s.send("OK", wait=True))
        s.stop()

        async def main():
            i = await Interpreter(m).start()
            go = surface(i, await i.send("GO", wait=True))
            ok = surface(i, await i.send("OK", wait=True))
            await i.stop()
            return go, ok

        async_go, async_ok = asyncio.run(main())
        self.assertEqual(sync_go, async_go)
        self.assertEqual(sync_ok, async_ok)
        self.assertEqual(
            sync_go[1:4], (False, "StateNotFoundError", "StateNotFoundError")
        )
        self.assertEqual(
            sync_ok[1:4], (True, None, None), "recovers on the next clean step"
        )

    def test_sync_fire_and_forget_still_raises(self) -> None:
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
        s = SyncInterpreter(m)
        s.start()
        with self.assertRaises(StateNotFoundError):
            s.send("GO")
        self.assertFalse(s.last_transition_ok)
        s.stop()


# =============================================================================
# #77 ride-along — engines land on the same state when a chain is cut
# =============================================================================
class TestChainCutParity(_Quiet):
    @staticmethod
    def _entry_raise_chain(limit: int, depth: int) -> Dict[str, Any]:
        states = {
            f"s{k}": {
                "entry": [{"type": "raise", "params": {"event": "NEXT"}}],
                "on": {"NEXT": f"s{k + 1}"},
            }
            for k in range(depth + 1)
        }
        states[f"s{depth + 1}"] = {}
        return {
            "id": "m",
            "initial": "s0",
            "maxIterations": limit,
            "states": states,
        }

    def test_both_engines_cut_a_deep_chain_at_the_same_link(self) -> None:
        """The reporter's 1 001-deep chain landed on `s1000` (sync) vs
        `s1001` (async): raises seeded by `start()`'s initial entry were
        counted against the sync budget but not the async one."""
        for limit in (3, 5, 50):
            cfg = self._entry_raise_chain(limit, depth=limit + 5)
            s = SyncInterpreter(create_machine(cfg))
            s.start()
            sync_land = s.value
            s.stop()

            async def main():
                i = await Interpreter(create_machine(cfg)).start()
                await asyncio.sleep(0.2)
                v = i.value
                await i.stop()
                return v

            self.assertEqual(sync_land, asyncio.run(main()), f"limit={limit}")
            self.assertEqual(sync_land, f"s{limit + 1}")


# =============================================================================
# #31 ride-along — the sibling-fallback warning throttle is bounded
# =============================================================================
class TestSiblingFallbackThrottleBounded(_Quiet):
    def test_set_never_exceeds_cap(self) -> None:
        from src.xstate_statemachine import resolver as R

        R._SIBLING_FALLBACKS_WARNED.clear()
        cap = R._SIBLING_FALLBACKS_WARNED_MAX
        for k in range(cap + 50):
            cfg = {
                "id": f"m{k}",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"GO": ".b"},
                        "initial": "x",
                        "states": {"x": {}},
                    },
                    "b": {},
                },
            }
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                i = SyncInterpreter(create_machine(cfg, strict_targets=False))
                i.start()
                try:
                    i.send("GO")
                except Exception:
                    pass
                i.stop()
        self.assertLessEqual(len(R._SIBLING_FALLBACKS_WARNED), cap)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
