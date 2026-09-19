# tests/test_v080_review_findings.py
# -----------------------------------------------------------------------------
# 🧪 Pre-merge critical review of the 0.8.0 branch — regression pins
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: each test here was written FIRST, against a
# confirmed defect found by the adversarial review of PR #61, and made to
# fail before the fix landed. They are kept in one file so the review's
# findings map 1:1 onto tests and none can be quietly dropped later.
# -----------------------------------------------------------------------------
"""Regression pins for the PR #61 review findings."""

import asyncio
import logging
import subprocess
import sys
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import TransitionFailedError
from src.xstate_statemachine.plugins import PluginBase
from src.xstate_statemachine.pythonic import State, Transition, build_machine


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _boom_logic() -> MachineLogic:
    def boom(i, c, e, a):
        c["n"] = 99
        raise RuntimeError("boom")

    def bump(i, c, e, a):
        c["n"] += 1

    return MachineLogic(actions={"boom": boom, "bump": bump})


def _cfg(policy: str, states: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": "m",
        "initial": "a",
        "context": {"n": 0},
        "actionErrorPolicy": policy,
        "states": states,
    }


# -----------------------------------------------------------------------------
# Finding 1 (CRITICAL): the policy must cover EVERY action slot
# -----------------------------------------------------------------------------
class TestActionErrorPolicyCoversAllSlots(_Quiet):
    """Entry, exit, targetless and internal-self actions all honour the
    policy -- not just `transition.actions` on an external transition."""

    SHAPES: Dict[str, Dict[str, Any]] = {
        "targetless": {"a": {"on": {"GO": {"actions": ["boom"]}}}},
        "internal_self": {
            "a": {"on": {"GO": {"target": "a", "actions": ["boom"]}}}
        },
        "entry": {"a": {"on": {"GO": "b"}}, "b": {"entry": ["boom"]}},
        "exit": {"a": {"exit": ["boom"], "on": {"GO": "b"}}, "b": {}},
        "entry_after_bump": {
            "a": {"on": {"GO": "b"}},
            "b": {"entry": ["bump", "boom"]},
        },
    }

    def _run_sync(self, policy: str, shape: str) -> SyncInterpreter:
        i = SyncInterpreter(
            create_machine(
                _cfg(policy, self.SHAPES[shape]), logic=_boom_logic()
            )
        )
        i.start()
        i.send("GO")
        return i

    def _run_async(self, policy: str, shape: str) -> Any:
        async def main():
            i = Interpreter(
                create_machine(
                    _cfg(policy, self.SHAPES[shape]), logic=_boom_logic()
                )
            )
            await i.start()
            await i.send("GO")
            await asyncio.sleep(0.05)
            out = (
                set(i.current_state_ids),
                dict(i.context),
                i.status,
                i.last_transition_ok,
                i.error,
            )
            await i.stop()
            return out

        return asyncio.run(main())

    def test_fail_policy_every_shape_sync(self) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape=shape):
                i = self._run_sync("fail", shape)
                # #145: "fail" STOPS the machine; configuration is cleared.
                self.assertEqual(i.status, "stopped", shape)
                self.assertIsInstance(i.error, TransitionFailedError)
                self.assertEqual(i.context["n"], 0, "context not rolled back")
                self.assertEqual(i.current_state_ids, set())
                self.assertFalse(i.last_transition_ok)

    def test_fail_policy_every_shape_async(self) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape=shape):
                state, ctx, status, ok, err = self._run_async("fail", shape)
                self.assertEqual(status, "stopped", shape)  # #145
                self.assertIsInstance(err, TransitionFailedError)
                self.assertEqual(ctx["n"], 0)
                self.assertEqual(state, set())
                self.assertFalse(ok)

    def test_rollback_policy_every_shape_sync(self) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape=shape):
                i = self._run_sync("rollback", shape)
                self.assertEqual(i.status, "running", shape)
                self.assertEqual(i.context["n"], 0)
                self.assertEqual(i.current_state_ids, {"m.a"})
                self.assertFalse(i.last_transition_ok)

    def test_rollback_policy_every_shape_async(self) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape=shape):
                state, ctx, status, ok, _ = self._run_async("rollback", shape)
                self.assertEqual(status, "running", shape)
                self.assertEqual(ctx["n"], 0)
                self.assertEqual(state, {"m.a"})
                self.assertFalse(ok)

    def test_continue_policy_still_commits_but_reports(self) -> None:
        """0.7.x behaviour preserved under the default, now observable."""
        for shape in ("targetless", "entry", "exit"):
            with self.subTest(shape=shape):
                i = self._run_sync("continue", shape)
                self.assertEqual(i.status, "running")
                self.assertEqual(i.context["n"], 99)  # mutation kept
                self.assertFalse(i.last_transition_ok)

    def test_transition_failed_hook_fires_for_entry_failure(self) -> None:
        class Spy(PluginBase):
            def __init__(self):
                self.failed: List[Any] = []

            def on_transition_failed(self, i, t, failed):
                self.failed.append([a.type for a, _ in failed])

        spy = Spy()
        i = SyncInterpreter(
            create_machine(
                _cfg("rollback", self.SHAPES["entry"]),
                logic=_boom_logic(),
            )
        )
        i.use(spy)
        i.start()
        i.send("GO")
        self.assertEqual(spy.failed, [["boom"]])

    def test_initial_entry_failure_on_start_is_reported(self) -> None:
        """`start()` enters the initial state; its entry actions count too."""
        cfg = _cfg("fail", {"a": {"entry": ["boom"]}})
        i = SyncInterpreter(create_machine(cfg, logic=_boom_logic()))
        i.start()
        self.assertEqual(i.status, "stopped")  # #145
        self.assertIsInstance(i.error, TransitionFailedError)


# -----------------------------------------------------------------------------
# Finding 2 (HIGH): rollback must cancel tasks of partially-entered states
# -----------------------------------------------------------------------------
class TestRollbackCancelsEnteredTasks(_Quiet):
    def test_after_timer_of_rolled_back_state_never_fires(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "actionErrorPolicy": "rollback",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {
                    "type": "parallel",
                    "states": {
                        "r1": {
                            "initial": "x",
                            "states": {
                                "x": {"after": {"30": "y"}},
                                "y": {},
                            },
                        },
                        "r2": {
                            "initial": "p",
                            "states": {"p": {"entry": ["boom"]}},
                        },
                    },
                },
            },
        }

        async def main():
            i = Interpreter(create_machine(cfg, logic=_boom_logic()))
            await i.start()
            await i.send("GO")
            await asyncio.sleep(0.15)  # well past the 30 ms timer
            out = (set(i.current_state_ids), i.status)
            await i.stop()
            return out

        state, status = asyncio.run(main())
        self.assertEqual(state, {"m.a"})
        self.assertEqual(status, "running")

    def test_sync_after_timer_of_rolled_back_state_never_fires(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "actionErrorPolicy": "rollback",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {
                    "type": "parallel",
                    "states": {
                        "r1": {
                            "initial": "x",
                            "states": {
                                "x": {"after": {"30": "y"}},
                                "y": {},
                            },
                        },
                        "r2": {
                            "initial": "p",
                            "states": {"p": {"entry": ["boom"]}},
                        },
                    },
                },
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=_boom_logic()))
        i.start()
        i.send("GO")
        time.sleep(0.15)
        self.assertEqual(i.current_state_ids, {"m.a"})
        i.stop()


# -----------------------------------------------------------------------------
# Finding 3 (HIGH): engine-synthesised `xstate.*` events are system events
# -----------------------------------------------------------------------------
class TestEscalateIsNotUnhandled(_Quiet):
    def test_escalate_with_no_parent_handler_does_not_error_machine(
        self,
    ) -> None:
        child = {
            "id": "kid",
            "initial": "i",
            "states": {
                "i": {
                    "entry": [{"type": "escalate", "params": {"error": "bad"}}]
                }
            },
        }
        parent = {
            "id": "p",
            "initial": "a",
            "onUnhandled": "error",
            "states": {"a": {"invoke": {"src": "kid"}}},
        }
        logic = MachineLogic(services={"kid": create_machine(child)})
        i = SyncInterpreter(create_machine(parent, logic=logic))
        i.start()
        self.assertEqual(i.status, "running")
        self.assertEqual(i.deferred_count, 0)
        i.stop()


# -----------------------------------------------------------------------------
# Finding 4 (HIGH): sync defer replay must not eat the macrostep budget
# -----------------------------------------------------------------------------
class TestSyncDeferReplayBudget(_Quiet):
    def test_replaying_a_full_buffer_does_not_drop_live_events(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"seen": 0, "live": False},
            "onUnhandled": "defer",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {
                    "on": {
                        "LATER": {"actions": ["count"]},
                        "LIVE": {"actions": ["mark"]},
                    }
                },
            },
        }

        def count(i, c, e, a):
            c["seen"] += 1

        def mark(i, c, e, a):
            c["live"] = True

        logic = MachineLogic(actions={"count": count, "mark": mark})
        i = SyncInterpreter(create_machine(cfg, logic=logic))
        i.DEFER_MAX = 1000
        i.start()
        for _ in range(1000):
            i.send("LATER")
        self.assertEqual(i.deferred_count, 1000)
        i.send_events(["GO", "LIVE"])
        self.assertEqual(i.context["seen"], 1000)
        self.assertTrue(i.context["live"], "live event was discarded")
        self.assertEqual(i.deferred_count, 0)


# -----------------------------------------------------------------------------
# Finding 5 (HIGH): `#id` targets when the machine id contains a dot
# -----------------------------------------------------------------------------
class TestDottedMachineIdTargets(_Quiet):
    def test_hash_target_with_dotted_machine_id_resolves(self) -> None:
        cfg = {
            "id": "my.machine",
            "initial": "a",
            "states": {
                "a": {"on": {"G": "#my.machine.b"}},
                "b": {},
            },
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i.send("G")
        self.assertEqual(i.current_state_ids, {"my.machine.b"})

    def test_pythonic_nested_target_with_dotted_machine_id(self) -> None:
        up = State("up")
        moving = State("moving", states=[up])
        idle = State("idle", initial=True)
        m = build_machine(
            id="my.lift",
            states=[idle, moving],
            transitions=[Transition(source=idle, event="GO", target=up)],
        )
        i = SyncInterpreter(m).start()
        i.send("GO")
        self.assertEqual(i.current_state_ids, {"my.lift.moving.up"})


# -----------------------------------------------------------------------------
# Finding 8 (MEDIUM): the unresolvable-target error must teach the fix
# -----------------------------------------------------------------------------
class TestUnresolvableTargetHint(_Quiet):
    def test_nested_bare_name_error_suggests_absolute_form(self) -> None:
        cfg = {
            "id": "m",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "up"}},
                "moving": {"initial": "up", "states": {"up": {}, "down": {}}},
            },
        }
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(cfg)
        msg = str(cm.exception)
        self.assertIn("'up'", msg)
        self.assertIn("#m.moving.up", msg)


# -----------------------------------------------------------------------------
# Findings 6 + 7 (MEDIUM): `send()` semantics and stale-loop diagnostics
# -----------------------------------------------------------------------------
class TestSendSemantics(_Quiet):
    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": "b"}}, "b": {}},
    }

    def test_unawaited_in_loop_send_is_delivered(self) -> None:
        """Fire-and-forget `send()` inside the loop must not drop the event."""
        import warnings

        async def main():
            i = await Interpreter(create_machine(self.CFG)).start()
            i.send("GO")  # deliberately NOT awaited
            await asyncio.sleep(0.05)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            state = asyncio.run(main())
        self.assertEqual(state, {"m.b"})
        self.assertFalse(
            [w for w in caught if "never awaited" in str(w.message)],
            "send() leaked an un-awaited coroutine",
        )

    def test_awaited_send_still_works(self) -> None:
        async def main():
            i = await Interpreter(create_machine(self.CFG)).start()
            await i.send("GO")
            await asyncio.sleep(0.02)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), {"m.b"})

    def test_send_after_loop_closed_explains_itself(self) -> None:
        i = Interpreter(create_machine(self.CFG))

        async def boot():
            await i.start()

        asyncio.run(boot())  # loop is now closed; interpreter outlived it
        with self.assertRaises(RuntimeError) as cm:
            i.send("GO")
        self.assertIn("closed", str(cm.exception))
        self.assertNotIn("WrongThread", type(cm.exception).__name__)

    def test_send_threadsafe_after_loop_closed_does_not_leak(self) -> None:
        import warnings

        i = Interpreter(create_machine(self.CFG))

        async def boot():
            await i.start()

        asyncio.run(boot())
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with self.assertRaises(RuntimeError) as cm:
                i.send_threadsafe("GO")
        self.assertIn("closed", str(cm.exception))
        self.assertFalse(
            [w for w in caught if "never awaited" in str(w.message)]
        )


class TestAfterTypeHintMatchesNamedDelays(_Quiet):
    """🐛 [Issue #60] `StateNode.after`'s class-level type hint must match
    what `_parse_after` actually returns/assigns (`Dict[Union[int, str],
    ...]`), since named delays (e.g. ``after: {"TIMEOUT": ...}``) resolve
    to string keys, not just int millisecond keys.
    """

    def test_models_module_has_no_after_dict_assignment_mypy_error(
        self,
    ) -> None:
        # 🧪 Regression pin: mypy previously flagged the `self.after = ...`
        # assignment in `_parse_after` as incompatible with the stale
        # `Dict[int, ...]` class attribute annotation. This must be clean.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/xstate_statemachine/models.py",
                "--ignore-missing-imports",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotIn(
            "Incompatible types in assignment",
            result.stdout,
            msg=result.stdout,
        )


class TestSpawnedActorRolledBackWithTransition(_Quiet):
    """Finding: a `spawn_*` action's child actor must not survive a
    rollback of the SAME transition (issue #61 follow-up review).
    """

    def test_spawned_actor_is_stopped_when_its_own_transition_rolls_back(
        self,
    ) -> None:
        child_cfg = {
            "id": "child",
            "initial": "running",
            "states": {"running": {}},
        }

        def failing_action(interpreter, context, event, action_def=None):
            raise RuntimeError("boom")

        cfg = {
            "id": "m",
            "actionErrorPolicy": "rollback",
            "initial": "A",
            "states": {
                "A": {
                    "on": {
                        "GO": {
                            "target": "B",
                            "actions": [
                                {
                                    "type": "spawn_childMachine",
                                    "params": {"id": "kid"},
                                },
                                "fail",
                            ],
                        }
                    }
                },
                "B": {},
            },
        }
        child_machine = create_machine(child_cfg)
        logic = MachineLogic(
            services={"childMachine": child_machine},
            actions={"fail": failing_action},
        )

        async def main():
            machine = create_machine(cfg, logic=logic)
            interp = await Interpreter(machine).start()
            await interp.send("GO")
            await asyncio.sleep(0.05)
            states = set(interp.current_state_ids)
            kid = interp._actors.get("m:kid")
            kid_status = kid.status if kid is not None else None
            await interp.stop()
            return states, kid, kid_status

        states, kid, kid_status = asyncio.run(main())
        self.assertEqual(states, {"m.A"})
        # 👶 #60 review: the child spawned inside the rolled-back
        # transition must be neither registered nor left running.
        self.assertIsNone(kid)
        self.assertIsNone(kid_status)


# -----------------------------------------------------------------------------
# Finding (HIGH): spawned SyncInterpreter children must inherit the parent's
# clock so SimulatedClock-driven `after` timers fire deterministically.
# -----------------------------------------------------------------------------
class TestSpawnedChildInheritsParentClock(_Quiet):
    """🕰️ #60: a spawned child must share the parent's `Clock` instance."""

    def test_spawned_child_uses_parent_simulated_clock(self) -> None:
        from src.xstate_statemachine.clock import SimulatedClock

        child_cfg = {
            "id": "child",
            "initial": "waiting",
            "states": {
                "waiting": {"after": {"1000": "done"}},
                "done": {"type": "final"},
            },
        }
        child_machine = create_machine(child_cfg)

        parent_cfg = {
            "id": "parent",
            "initial": "active",
            "states": {
                "active": {
                    "entry": [
                        {
                            "type": "xstate.spawnChild",
                            "params": {"src": "child", "id": "kid"},
                        }
                    ],
                }
            },
        }
        parent_machine = create_machine(
            parent_cfg,
            logic=MachineLogic(services={"child": child_machine}),
        )

        clock = SimulatedClock()
        interp = SyncInterpreter(parent_machine, clock=clock).start()
        kid = interp._actors.get("parent:kid")

        # 🕵️ The child must share the SAME SimulatedClock instance as its
        # parent, not silently fall back to a fresh RealClock.
        self.assertIs(kid.clock, clock)

        # ⏩ Advancing the parent's virtual clock must fire the child's
        # `after` timer deterministically (no real wall-clock wait).
        clock.increment(1000)
        self.assertEqual(kid.status, "done")


class TestSendOverloadImplementationHasNoMiscMypyError(_Quiet):
    """🐛 The `# type: ignore[override]` on `Interpreter.send`'s
    implementation only suppresses the `[override]` error code, leaving
    the `[misc]` "does not accept all possible parameters" errors for
    both `@overload` signatures unsuppressed and uncovered.
    """

    def test_interpreter_module_has_no_send_overload_misc_error(
        self,
    ) -> None:
        # 🧪 Regression pin: mypy previously reported two `[misc]` errors
        # at the `send()` implementation line (overloaded implementation
        # does not accept all possible parameters of signature 1/2),
        # uncovered by the `[override]`-only ignore comment. Must be clean.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/xstate_statemachine/interpreter.py",
                "--ignore-missing-imports",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotIn(
            "does not accept all possible parameters",
            result.stdout,
            msg=result.stdout,
        )


class TestSendPriorityForwardsArgTypeHasNoMypyError(_Quiet):
    """🐛 [Issue #38/#39] `send_priority` forwards its `event_or_type`
    parameter (typed as the full `Union[str, Dict, Event, DoneEvent,
    AfterEvent]`) straight into `self.send(event_or_type, ...)`. Because
    `send` is `@overload`-ed, mypy resolves the call against the first,
    `str`-only overload and flags every non-`str` member of the union as
    an incompatible argument, even though the runtime dispatch is correct.
    """

    def test_interpreter_module_has_no_send_priority_arg_type_error(
        self,
    ) -> None:
        # 🧪 Regression pin: mypy previously reported an `[arg-type]` error
        # at the `self.send(event_or_type, ...)` call inside
        # `send_priority` ("Argument 1 to "send" of "Interpreter" has
        # incompatible type ... expected "str""). Must be clean.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/xstate_statemachine/interpreter.py",
                "--ignore-missing-imports",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotIn(
            'Argument 1 to "send" of "Interpreter" has incompatible type',
            result.stdout,
            msg=result.stdout,
        )


class TestNextEventLostWakeupRaceWindow(_Quiet):
    """🐛 [Coverage] `_next_event`'s re-check-before-sleep branch (an event
    arriving between the emptiness checks and `_wakeup.clear()`) had no
    test forcing that exact race window; a regression there would only
    show up as an intermittent hang, not a deterministic failure.
    """

    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": "b"}}, "b": {}},
    }

    def test_event_arriving_during_wakeup_clear_is_not_slept_through(
        self,
    ) -> None:
        # 🧪 Regression pin: force the race by making `_wakeup.clear()`
        # itself the thing that delivers the event -- simulating another
        # task enqueuing between the "is anything pending?" checks and the
        # clear call. If the re-check-after-clear guard at
        # interpreter.py:1528-1530 were removed, this event would only be
        # picked up after `_wakeup.wait()` unblocks it, which nothing here
        # ever does, so the test would hang until pytest's timeout.
        async def main():
            i = await Interpreter(create_machine(self.CFG)).start()
            await asyncio.sleep(0.02)  # let the loop settle into idle

            real_clear = i._wakeup.clear

            def clear_and_sneak_in_event():
                real_clear()
                i._event_queue.put_nowait(_make_go_event())

            i._wakeup.clear = clear_and_sneak_in_event

            # ▶️ Nudge the loop out of its current `await` so `_next_event`
            # re-enters and hits the patched `clear()`.
            i._wakeup.set()
            await asyncio.wait_for(asyncio.sleep(0.05), timeout=1)

            out = set(i.current_state_ids)
            await i.stop()
            return out

        state = asyncio.run(main())
        self.assertEqual(state, {"m.b"})


def _make_go_event() -> Any:
    from src.xstate_statemachine.models import Event

    return Event(type="GO")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
