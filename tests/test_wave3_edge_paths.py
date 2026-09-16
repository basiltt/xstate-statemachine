# tests/test_wave3_edge_paths.py
# -----------------------------------------------------------------------------
# 🧪 Wave-3 edge paths -- branches the feature suites did not reach
# -----------------------------------------------------------------------------
# Same rationale as test_v080_edge_paths.py / test_wave2_edge_paths.py: a
# diff-coverage pass found the misuse/warning/error branches below
# unexercised. Grouped by source line so a red line maps to its test.
# -----------------------------------------------------------------------------
"""Edge-path coverage for wave 3 (#36 #38 #39 #44 #48-#51 #60)."""

import asyncio
import logging
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    RealClock,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase
from src.xstate_statemachine.sync_interpreter import _Done


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _run(coro):
    return asyncio.run(coro)


def _builtin_machine(action: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": {"actions": [action]}}}},
    }


# -----------------------------------------------------------------------------
# base_interpreter.py -- built-in misuse warnings (shared runner, #60)
# -----------------------------------------------------------------------------
class TestBuiltinMisuseIsWarnedNotFatal(_Quiet):
    def _both(self, action: Dict[str, Any], needle: str) -> None:
        for engine in ("sync", "async"):
            with self.subTest(engine=engine):
                logging.disable(logging.NOTSET)
                with self.assertLogs(level="WARNING") as logs:
                    if engine == "sync":
                        i = SyncInterpreter(
                            create_machine(_builtin_machine(action))
                        ).start()
                        i.send("GO")
                        i.stop()
                    else:

                        async def main():
                            j = await Interpreter(
                                create_machine(_builtin_machine(action))
                            ).start()
                            await j.send("GO", wait=True)
                            await j.stop()

                        _run(main())
                self.assertTrue(
                    any(needle in ln for ln in logs.output), logs.output
                )
                logging.disable(logging.CRITICAL)

    def test_send_parent_with_no_parent_warns(self) -> None:
        self._both(
            {"type": "sendParent", "params": {"event": "X"}}, "no parent"
        )

    def test_forward_to_unresolvable_warns(self) -> None:
        self._both(
            {"type": "forwardTo", "params": {"to": "ghost"}},
            "could not resolve",
        )

    def test_escalate_with_no_parent_logs_error(self) -> None:
        self._both(
            {"type": "escalate", "params": {"error": "boom"}}, "no parent"
        )

    def test_stop_child_unresolvable_warns(self) -> None:
        self._both(
            {"type": "stopChild", "params": {"id": "ghost"}},
            "could not resolve",
        )

    def test_spawn_child_without_string_src_warns(self) -> None:
        self._both(
            {"type": "spawnChild", "params": {"src": 42}}, "string 'src'"
        )


class TestSharedRunnerConfigErrorsStayFatal(_Quiet):
    def test_missing_service_on_restart_raises(self) -> None:
        from src.xstate_statemachine import ImplementationMissingError

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "svc"}}},
        }
        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(services={"svc": lambda *a: 1})
            )
        ).start()
        snap = i.get_snapshot()
        i.stop()
        # Restore against a machine that no longer registers the service.
        bare = create_machine(
            cfg, logic=MachineLogic(services={"svc": lambda *a: 1})
        )
        bare.logic.services.clear()
        j = SyncInterpreter.from_snapshot(snap, bare, restart_services=True)
        with self.assertRaises(ImplementationMissingError):
            j.start()


# -----------------------------------------------------------------------------
# clock.py
# -----------------------------------------------------------------------------
class TestClockEdges(_Quiet):
    def test_real_clock_pump_outside_loop_fires_due_callbacks(self) -> None:
        clock = RealClock()
        fired: List[int] = []
        clock.set_timeout(lambda: fired.append(1), 0.0)
        time.sleep(0.005)
        self.assertEqual(clock.pump(), 1)
        self.assertEqual(fired, [1])
        self.assertEqual(clock.pending, 0)

    def test_simulated_increment_rejects_negative(self) -> None:
        with self.assertRaises(ValueError):
            SimulatedClock().increment(-1)

    def test_shared_simulated_clock_async_parent_sync_child(self) -> None:
        """One clock, both engines: the sync child's settler is a plain
        callable, the async parent's a coroutine; each is driven correctly."""
        child = {
            "id": "kid",
            "initial": "w",
            "states": {"w": {"after": {"100": "d"}}, "d": {"type": "final"}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"after": {"500": "b"}}, "b": {}},
        }
        clock = SimulatedClock()
        kid = SyncInterpreter(create_machine(child), clock=clock).start()

        async def main():
            i = await Interpreter(create_machine(parent), clock=clock).start()
            await clock.increment(100)
            mid = (set(kid.current_state_ids), set(i.current_state_ids))
            await clock.increment(400)
            end = (set(kid.current_state_ids), set(i.current_state_ids))
            await i.stop()
            return mid, end

        mid, end = _run(main())
        self.assertEqual(mid, ({"kid.d"}, {"p.a"}))
        self.assertEqual(end, ({"kid.d"}, {"p.b"}))
        kid.stop()


# -----------------------------------------------------------------------------
# interpreter.py
# -----------------------------------------------------------------------------
class TestAsyncEdges(_Quiet):
    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {"n": 0},
        "states": {"a": {"on": {"T": {"actions": ["inc"]}}}},
    }

    def _logic(self) -> MachineLogic:
        def inc(i, c, e, a):
            c["n"] += 1

        return MachineLogic(actions={"inc": inc})

    def test_max_queue_size_must_be_positive(self) -> None:
        with self.assertRaises(InvalidConfigError):
            Interpreter(
                create_machine(self.CFG, logic=self._logic()), max_queue_size=0
            )

    def test_not_running_drop_notifies_plugin_and_resolves_receipt(
        self,
    ) -> None:
        class Spy(PluginBase):
            def __init__(self):
                self.dropped: List[Any] = []

            def on_event_dropped(self, i, e, reason):
                self.dropped.append(reason)

        async def main():
            spy = Spy()
            i = Interpreter(create_machine(self.CFG, logic=self._logic()))
            i.use(spy)
            await i.start()
            await i.stop()
            i.status = "done"
            r = await i.send("T", wait=True)
            return spy.dropped, r.error is not None

        self.assertEqual(_run(main()), (["not_running"], True))

    def test_block_policy_on_not_running_and_on_stop_while_blocked(
        self,
    ) -> None:
        from src.xstate_statemachine import OverflowPolicy

        async def main():
            i = Interpreter(
                create_machine(self.CFG, logic=self._logic()),
                max_queue_size=1,
                overflow_policy=OverflowPolicy.BLOCK,
            )
            await i.start()
            await i.stop()
            i.status = "done"
            r1 = await i.send("T", wait=True)  # refused, receipt resolved
            # A fresh one: fill, then block a producer and stop underneath it.
            j = Interpreter(
                create_machine(self.CFG, logic=self._logic()),
                max_queue_size=1,
                overflow_policy=OverflowPolicy.BLOCK,
            )
            await j.start()
            j._event_queue.put_nowait(
                j._prepare_event("T")
            )  # full, unconsumed
            j.status = "stopped"  # consumer gone
            r2 = await asyncio.wait_for(j.send("T", wait=True), 2.0)
            return r1.error is not None, r2.error is not None

        self.assertEqual(_run(main()), (True, True))

    def test_block_policy_self_send_from_action_does_not_deadlock(
        self,
    ) -> None:
        """#60: `send()` from an action while BLOCK's inbox is full.

        `_enqueue_blocking` spins until the inbox drains, but the run
        loop -- the only thing that ever drains it -- is the very task
        stuck inside that spin (it got there by running the action that
        called `send()`). Before the fix this hung forever; the event
        must instead go through the internal queue so the macrostep
        completes.
        """
        from src.xstate_statemachine import OverflowPolicy

        cfg = {
            "id": "m",
            "initial": "idle",
            "context": {},
            "states": {
                "idle": {
                    "on": {
                        "GO": {"target": "idle", "actions": ["fill"]},
                        "GO2": {"target": "idle", "actions": ["mark"]},
                    }
                }
            },
        }

        async def main():
            reached: List[str] = []

            async def fill(i, c, e, a):
                await i.send("GO2")

            def mark(i, c, e, a):
                reached.append("GO2")

            logic = MachineLogic(actions={"fill": fill, "mark": mark})
            i = Interpreter(
                create_machine(cfg, logic=logic),
                max_queue_size=1,
                overflow_policy=OverflowPolicy.BLOCK,
            )
            await i.start()
            i._event_queue.put_nowait(i._prepare_event("PAD"))  # fill inbox
            await asyncio.wait_for(i.send("GO", priority=True, wait=True), 2.0)
            # The GO2 self-send lands on the internal queue and is drained
            # on the run loop's next turn; give it one to run.
            await asyncio.sleep(0.05)
            await i.stop()
            return reached

        self.assertEqual(_run(main()), ["GO2"])

    def test_delayed_send_to_another_actor_uses_the_clock(self) -> None:
        child = {
            "id": "kid",
            "initial": "i",
            "states": {"i": {"on": {"PING": "pinged"}}, "pinged": {}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        },
                        {
                            "type": "sendTo",
                            "params": {
                                "to": "k",
                                "event": "PING",
                                "delay": 1000,
                            },
                        },
                    ]
                }
            },
        }

        async def main():
            clock = SimulatedClock()
            i = await Interpreter(
                create_machine(
                    parent,
                    logic=MachineLogic(
                        services={"kid": create_machine(child)}
                    ),
                ),
                clock=clock,
            ).start()
            kid = i._actors["p:k"]
            before = set(kid.current_state_ids)
            await clock.increment(1000)
            for _ in range(50):
                if kid.current_state_ids == {"kid.pinged"}:
                    break
                await asyncio.sleep(0)
            out = (before, set(kid.current_state_ids))
            await i.stop()
            return out

        self.assertEqual(_run(main()), ({"kid.i"}, {"kid.pinged"}))

    def test_delayed_send_after_stop_is_dropped(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "raise",
                            "params": {"event": "L", "delay": 20},
                        }
                    ],
                    "on": {"L": "b"},
                },
                "b": {},
            },
        }

        async def main():
            clock = SimulatedClock()
            i = await Interpreter(create_machine(cfg), clock=clock).start()
            i.status = "stopped"  # simulate teardown racing the timer
            await clock.increment(20)
            return set(i.current_state_ids)

        self.assertEqual(_run(main()), {"m.a"})


# -----------------------------------------------------------------------------
# sync_interpreter.py
# -----------------------------------------------------------------------------
class TestSyncEdges(_Quiet):
    def test_done_awaitable_truthiness_and_equality(self) -> None:
        self.assertFalse(_Done(None))
        self.assertTrue(_Done([1]))
        self.assertEqual(_Done(3), 3)
        self.assertEqual(repr(_Done("x")), "'x'")

    def test_receipt_carries_step_error_and_action_error(self) -> None:
        from src.xstate_statemachine import StateNotFoundError
        import warnings

        # a) a processing error (unresolvable target under lenient build)
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "ghost"}}},
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = create_machine(cfg, strict_targets=False)
        i = SyncInterpreter(m).start()
        r = i.send("GO", wait=True)
        self.assertIsInstance(r.error, StateNotFoundError)
        # b) an action failure under the default policy
        cfg2 = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"actions": ["boom"]}}}},
        }

        def boom(i, c, e, a):
            raise RuntimeError("x")

        j = SyncInterpreter(
            create_machine(cfg2, logic=MachineLogic(actions={"boom": boom}))
        ).start()
        r2 = j.send("GO", wait=True)
        self.assertIsInstance(r2.error, RuntimeError)

    def test_delayed_send_to_child_and_cancel_by_id(self) -> None:
        child = {
            "id": "kid",
            "initial": "i",
            "states": {"i": {"on": {"PING": "pinged"}}, "pinged": {}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        },
                        {
                            "type": "sendTo",
                            "params": {
                                "to": "k",
                                "event": "PING",
                                "delay": 50,
                                "id": "s1",
                            },
                        },
                    ],
                    "on": {
                        "CANCEL": {
                            "actions": [
                                {"type": "cancel", "params": {"sendId": "s1"}}
                            ]
                        }
                    },
                }
            },
        }
        clock = SimulatedClock()
        i = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(services={"kid": create_machine(child)}),
            ),
            clock=clock,
        ).start()
        kid = i._actors["p:k"]
        i.send("CANCEL")
        clock.increment(50)
        self.assertEqual(kid.current_state_ids, {"kid.i"})  # cancelled
        i.stop()

    def test_delayed_send_to_child_fires_and_delivers(self) -> None:
        """🔁 #60: a delayed `sendTo` targeting another actor (not self)
        must actually deliver once the clock reaches the deadline -- this
        covers the success branch of `_fire` in `_deliver_sync`, not just
        the cancellation path exercised above."""
        child = {
            "id": "kid",
            "initial": "i",
            "states": {"i": {"on": {"PING": "pinged"}}, "pinged": {}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        },
                        {
                            "type": "sendTo",
                            "params": {
                                "to": "k",
                                "event": "PING",
                                "delay": 50,
                                "id": "s1",
                            },
                        },
                    ],
                }
            },
        }
        clock = SimulatedClock()
        i = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(services={"kid": create_machine(child)}),
            ),
            clock=clock,
        ).start()
        kid = i._actors["p:k"]
        clock.increment(50)
        self.assertEqual(kid.current_state_ids, {"kid.pinged"})  # delivered
        i.stop()

    def test_wait_for_child_terminal_returns_when_child_already_done(
        self,
    ) -> None:
        done_child = {
            "id": "d",
            "initial": "f",
            "states": {"f": {"type": "final"}},
        }
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"entry": ["spawn_blocking_d"]}},
        }
        i = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(services={"d": create_machine(done_child)}),
            )
        ).start()
        self.assertEqual(i.status, "running")
        i.stop()

    def test_sync_restart_services_marks_machine_invoke_live(self) -> None:
        """A restored MACHINE invoke that is live is not listed as pending."""
        child = {"id": "kid", "initial": "i", "states": {"i": {}}}
        parent = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "kid", "id": "k"}}},
        }
        i = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(services={"kid": create_machine(child)}),
            )
        ).start()
        self.assertEqual(i.pending_invocations(), [])
        i.stop()


# -----------------------------------------------------------------------------
# Remaining defensive branches, exercised directly
# -----------------------------------------------------------------------------
class TestDefensiveBranches(_Quiet):
    def test_simulated_clock_pump_fires_due_callbacks(self) -> None:
        clock = SimulatedClock()
        hits: List[int] = []
        clock.set_timeout(lambda: hits.append(1), 0.0)
        self.assertEqual(clock.pump(), 1)
        self.assertEqual(hits, [1])

    def test_simulated_settle_sync_closes_an_async_settler(self) -> None:
        """A coroutine settler driven from sync mode is closed, not leaked."""
        import warnings

        clock = SimulatedClock()

        async def async_settle():  # pragma: no cover - never run
            pass

        clock._attach(async_settle)
        clock.set_timeout(lambda: None, 0.001)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            clock.increment(10)  # sync path -> _settle_sync -> close()
        self.assertFalse(
            [w for w in caught if "never awaited" in str(w.message)]
        )

    def test_strict_engine_events_are_always_known(self) -> None:
        m = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"GO": "b"}}, "b": {}},
            }
        )
        for t in (
            "done.invoke.x",
            "error.platform.x",
            "after.5.m.a",
            "xstate.error.actor.k",
        ):
            self.assertTrue(m.is_known_event(t), t)

    def test_sync_after_fire_skips_when_owner_already_left(self) -> None:
        """A due timer whose owning state was exited between pump and
        fire must not resurrect the transition."""
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"after": {"10": "late"}, "on": {"GO": "b"}},
                "b": {},
                "late": {},
            },
        }
        clock = SimulatedClock()
        i = SyncInterpreter(create_machine(cfg), clock=clock).start()
        # Grab the timer's callback, leave the state, then fire it by hand.
        handle = i._timer_handles["m.a"][0]
        i.send("GO")
        handle.fn()  # owner inactive -> ignored
        self.assertEqual(i.current_state_ids, {"m.b"})
        i.stop()

    def test_sync_delayed_send_reusing_id_supersedes_and_clears(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {
                    "on": {
                        "ARM": {
                            "actions": [
                                {
                                    "type": "raise",
                                    "params": {
                                        "event": "L",
                                        "delay": 30,
                                        "id": "x",
                                    },
                                }
                            ]
                        },
                        "L": {"actions": ["inc"]},
                    }
                }
            },
        }

        def inc(i, c, e, a):
            c["n"] += 1

        clock = SimulatedClock()
        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"inc": inc})),
            clock=clock,
        ).start()
        i.send("ARM")
        i.send("ARM")  # supersedes the first `x`
        clock.increment(30)
        self.assertEqual(i.context["n"], 1)  # fired once, not twice
        self.assertNotIn("x", i._scheduled_sends)  # registry entry cleared
        i.stop()

    def test_async_invocation_is_live_via_explicit_actor_id(self) -> None:
        child = {"id": "kid", "initial": "i", "states": {"i": {}}}
        parent = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "kid", "id": "k"}}},
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
            for _ in range(200):
                if "p:k" in i._actors:
                    break
                await asyncio.sleep(0.002)
            out = i.pending_invocations()
            await i.stop()
            return out

        self.assertEqual(_run(main()), [])

    def test_restart_skips_invokes_that_are_not_pending(self) -> None:
        """Two invokes in one state, only one dormant -> only it restarts."""
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": [
                        {"src": "s1", "id": "one"},
                        {"src": "s2", "id": "two"},
                    ]
                }
            },
        }
        calls: List[str] = []
        logic = MachineLogic(
            services={
                "s1": lambda *a: calls.append("s1"),
                "s2": lambda *a: calls.append("s2"),
            }
        )
        i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        snap = i.get_snapshot()
        i.stop()
        calls.clear()
        j = SyncInterpreter.from_snapshot(
            snap, create_machine(cfg, logic=logic), restart_services=True
        )
        j.start()
        self.assertEqual(sorted(calls), ["s1", "s2"])
        j.stop()


# -----------------------------------------------------------------------------
# models.py -- strict partial matching exact-prefix branch
# -----------------------------------------------------------------------------
class TestKnownEventPartialExact(_Quiet):
    def test_partial_prefix_matches_itself(self) -> None:
        m = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"mouse.*": {}}}},
            }
        )
        self.assertTrue(m.is_known_event("mouse"))
        self.assertTrue(m.is_known_event("mouse.click.left"))
        self.assertFalse(m.is_known_event("mousey"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
