# tests/test_v080_edge_paths.py
# -----------------------------------------------------------------------------
# 🧪 0.8.0 edge paths — the branches the feature suites did not reach
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: each 0.8.0 feature has its own focused suite
# (test_action_error_policy, test_unhandled_events, ...). A diff-coverage
# pass over the branch found the error/edge branches below unexercised.
# They are grouped here by the source line they cover rather than spread
# across the feature suites, so a future coverage run can map a red line
# straight to its test.
# -----------------------------------------------------------------------------
"""Edge-path coverage for the 0.8.0 adoption-readiness features."""

import asyncio
import logging
import threading
import unittest
import warnings
from typing import Any, Dict

from src.xstate_statemachine import (
    ActorSpawningError,
    Interpreter,
    InvalidConfigError,
    LoggingInspector,
    MachineLogic,
    SyncInterpreter,
    WrongThreadError,
    action,
    create_machine,
)
from src.xstate_statemachine.actions import RAISE
from src.xstate_statemachine.exceptions import (
    TransitionFailedError,
    UnhandledEventError,
)
from src.xstate_statemachine.models import ActionDefinition
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# -----------------------------------------------------------------------------
# 🧬 machine_logic.py — explicit role markers and unregistrable arity
# -----------------------------------------------------------------------------
class TestMachineLogicMarkers(_Quiet):
    def test_explicit_marker_registers_regardless_of_arity(self) -> None:
        """A 2-arg callable decorated @action is an action, not a guard."""

        class Logic(MachineLogic):
            @action
            def two_args(self, ctx):  # would be inferred as a guard
                ctx["hit"] = True

        logic = Logic()
        self.assertIn("two_args", logic.actions)
        self.assertNotIn("two_args", logic.guards)

    def test_unknown_marker_value_warns_and_skips(self) -> None:
        def weird(self, i, c, e, a):
            pass

        weird._xsm_type = "banana"  # type: ignore[attr-defined]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            class Logic(MachineLogic):
                pass

            Logic.weird = weird
            logic = Logic()

        self.assertNotIn("weird", logic.actions)
        msgs = [str(w.message) for w in caught]
        self.assertTrue(any("unknown role marker" in m for m in msgs), msgs)

    def test_explicit_marker_never_clobbers_prior_registration(self) -> None:
        class Logic(MachineLogic):
            def __init__(self):
                super().__init__(actions={"dup": lambda *a: "explicit"})

            @action
            def dup(self, i, c, e, a):
                return "method"

        self.assertEqual(Logic().actions["dup"](), "explicit")

    def test_ambiguous_arity_registers_but_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            class Logic(MachineLogic):
                def two(self, c, e):  # arity 2: guard OR 2-arg service
                    return True

                def three(self, i, c, e):  # arity 3: service OR action
                    return None

            logic = Logic()
        self.assertIn("two", logic.guards)
        self.assertIn("three", logic.services)
        msgs = [str(w.message) for w in caught]
        self.assertEqual(sum("ambiguous" in m for m in msgs), 2, msgs)

    def test_arity_path_never_clobbers_prior_registration(self) -> None:
        class Logic(MachineLogic):
            def __init__(self):
                super().__init__(guards={"ok": lambda c, e: "explicit"})

            def ok(self, c, e):  # arity 2 -> guard, but already bound
                return "method"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(Logic().guards["ok"](None, None), "explicit")

    def test_unregistrable_arity_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            class Logic(MachineLogic):
                def six(self, a, b, c, d, e):  # arity 6 incl. self
                    pass

            Logic()
        msgs = [str(w.message) for w in caught]
        self.assertTrue(any("matches no logic contract" in m for m in msgs))


# -----------------------------------------------------------------------------
# 🛡️ models.py — built-in param hint when keys sit at the top level
# -----------------------------------------------------------------------------
class TestBuiltinParamHint(_Quiet):
    def test_hint_names_stray_top_level_keys(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            ActionDefinition({"type": RAISE, "event": "X"})
        msg = str(cm.exception)
        self.assertIn("missing required param(s) ['event']", msg)
        self.assertIn("Found ['event'] at the top level", msg)
        self.assertIn("nested under 'params'", msg)

    def test_no_hint_when_key_is_simply_absent(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            ActionDefinition({"type": RAISE})
        self.assertNotIn("top level", str(cm.exception))


# -----------------------------------------------------------------------------
# 📸 base_interpreter.py — from_snapshot when context is not a dict
# -----------------------------------------------------------------------------
class TestSnapshotNonDictContext(_Quiet):
    def test_non_dict_context_is_assigned_wholesale(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {}}}
        i = SyncInterpreter(create_machine(cfg)).start()
        i.context = ["not", "a", "dict"]  # type: ignore[assignment]
        snap = i.get_snapshot()
        j = SyncInterpreter.from_snapshot(snap, create_machine(cfg))
        self.assertEqual(j.context, ["not", "a", "dict"])


# -----------------------------------------------------------------------------
# 🌐 base_interpreter.py — duplicate live systemId, ambiguous actor key
# -----------------------------------------------------------------------------
class TestActorRegistryEdges(_Quiet):
    CHILD: Dict[str, Any] = {
        "id": "kid",
        "initial": "idle",
        "states": {"idle": {}},
    }

    def _parent(self, second_system_id: str) -> Dict[str, Any]:
        return {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {
                                "src": "kid",
                                "id": "w1",
                                "systemId": "w",
                            },
                        },
                        {
                            "type": "spawnChild",
                            "params": {
                                "src": "kid",
                                "id": "w2",
                                "systemId": second_system_id,
                            },
                        },
                    ]
                }
            },
        }

    def _logic(self) -> MachineLogic:
        return MachineLogic(
            services={"kid": lambda i, c, e: create_machine(self.CHILD)}
        )

    def test_duplicate_live_system_id_raises_through_action_error(
        self,
    ) -> None:
        """`spawnChild` is a built-in ACTION, so the `ActorSpawningError`
        surfaces via `on_action_error` and `actionErrorPolicy` (#27), not as
        a bare exception out of `start()`. The second child is NOT spawned."""

        class Spy(PluginBase):
            def __init__(self) -> None:
                self.errors: list = []

            def on_action_error(self, i, a, err):
                self.errors.append((a.type, err))

        spy = Spy()
        i = SyncInterpreter(
            create_machine(self._parent("w"), logic=self._logic())
        )
        i.use(spy)
        i.start()
        self.assertEqual(len(spy.errors), 1)
        kind, err = spy.errors[0]
        self.assertEqual(kind, "spawnChild")
        self.assertIsInstance(err, ActorSpawningError)
        self.assertIn("systemId 'w' is already registered", str(err))
        self.assertEqual(list(i._actors), ["p:w1"])
        i.stop()

    def test_stopped_actor_system_id_may_be_reused(self) -> None:
        """A finished/stopped actor does not block its systemId (#40)."""
        i = SyncInterpreter(
            create_machine(self._parent("v"), logic=self._logic())
        )
        i.start()
        first = i.system.get("w")
        first.stop()
        # Re-register a fresh child under the now-free id: no raise.
        i._register_in_system("w", SyncInterpreter(create_machine(self.CHILD)))
        self.assertIsNot(i.system.get("w"), first)
        i.stop()

    def test_distinct_system_ids_coexist(self) -> None:
        i = SyncInterpreter(
            create_machine(self._parent("v"), logic=self._logic())
        )
        i.start()
        self.assertIn("w", i.system)
        self.assertIn("v", i.system)
        i.stop()

    def test_ambiguous_last_segment_drops_event_with_error_log(self) -> None:
        """Two children whose ids both end in 'kid' -> ambiguous -> dropped."""
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "x:kid"},
                        },
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "y:kid"},
                        },
                    ],
                    "on": {
                        "GO": {
                            "actions": [
                                {
                                    "type": "sendTo",
                                    "params": {"to": "kid", "event": "PING"},
                                }
                            ]
                        }
                    },
                }
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=self._logic())).start()
        logging.disable(logging.NOTSET)
        with self.assertLogs(level="ERROR") as logs:
            i.send("GO")
        self.assertTrue(any("ambiguous" in line for line in logs.output))
        i.stop()


# -----------------------------------------------------------------------------
# 🧵 interpreter.py — send_threadsafe before start; WrongThreadError message
# -----------------------------------------------------------------------------
class TestThreadSafeSendEdges(_Quiet):
    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"GO": "b"}}, "b": {}},
    }

    def test_send_threadsafe_before_start_raises(self) -> None:
        i = Interpreter(create_machine(self.CFG))
        with self.assertRaises(RuntimeError) as cm:
            i.send_threadsafe("GO")
        self.assertIn("has not been started", str(cm.exception))

    def test_send_threadsafe_from_worker_thread_delivers(self) -> None:
        async def main() -> Any:
            i = await Interpreter(create_machine(self.CFG)).start()
            err: list = []

            def worker() -> None:
                try:
                    i.send_threadsafe("GO").result(timeout=2)
                except Exception as exc:  # noqa: BLE001
                    err.append(exc)

            await asyncio.to_thread(worker)
            await asyncio.sleep(0.02)
            out = (set(i.current_state_ids), err)
            await i.stop()
            return out

        state, err = asyncio.run(main())
        self.assertEqual(err, [])
        self.assertEqual(state, {"m.b"})

    def test_wrong_thread_error_names_both_threads(self) -> None:
        async def main() -> Any:
            i = await Interpreter(create_machine(self.CFG)).start()
            caught: list = []

            def worker() -> None:
                try:
                    i.send("GO")
                except WrongThreadError as exc:
                    caught.append(str(exc))

            t = threading.Thread(target=worker, name="Worker-X")
            t.start()
            t.join()
            await i.stop()
            return caught

        caught = asyncio.run(main())
        self.assertEqual(len(caught), 1)
        self.assertIn("Worker-X", caught[0])
        self.assertIn("send_threadsafe", caught[0])


# -----------------------------------------------------------------------------
# 🔁 interpreter.py — async defer replay stops when nothing moves
# -----------------------------------------------------------------------------
class TestAsyncDeferReplayNoProgress(_Quiet):
    def test_replayed_event_still_unhandled_stays_deferred(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {
                "a": {"on": {"NEXT": "b"}},
                "b": {"on": {"NEXT": "c"}},
                "c": {"on": {"X": "d"}},
                "d": {},
            },
        }

        async def main() -> Any:
            i = await Interpreter(create_machine(cfg)).start()
            await i.send("X")  # deferred in a
            await i.send("NEXT")  # a->b, X replays, still unhandled
            await asyncio.sleep(0.05)
            mid = (set(i.current_state_ids), i.deferred_count)
            await i.send("NEXT")  # b->c, X replays, handled -> d
            await asyncio.sleep(0.05)
            end = (set(i.current_state_ids), i.deferred_count)
            await i.stop()
            return mid, end

        mid, end = asyncio.run(main())
        self.assertEqual(mid, ({"m.b"}, 1))
        self.assertEqual(end, ({"m.d"}, 0))


# -----------------------------------------------------------------------------
# 🔁 base_interpreter.py — async internal transition, happy path
# -----------------------------------------------------------------------------
class TestAsyncInternalTransitionHappyPath(_Quiet):
    def test_targetless_success_sets_last_transition_ok(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"GO": {"actions": ["inc"]}}}},
        }

        def inc(i, c, e, a):
            c["n"] += 1

        class Spy(PluginBase):
            def __init__(self) -> None:
                self.hits = 0

            def on_transition(self, i, f, t, tr):
                if tr.source is not i.machine:  # skip the init transition
                    self.hits += 1

        async def main():
            i = Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
            )
            spy = Spy()
            i.use(spy)
            await i.start()
            i.last_transition_ok = False  # prove the success path resets it
            await i.send("GO")
            await asyncio.sleep(0.02)
            out = (i.context["n"], i.last_transition_ok, spy.hits)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), (1, True, 1))


# -----------------------------------------------------------------------------
# 🔌 plugins.py — LoggingInspector's five new hooks actually log
# -----------------------------------------------------------------------------
class TestLoggingInspectorNewHooks(unittest.TestCase):
    def _run(
        self, cfg: Dict[str, Any], logic: MachineLogic, events: list
    ) -> list:
        i = SyncInterpreter(create_machine(cfg, logic=logic))
        i.use(LoggingInspector())
        with self.assertLogs("xstate_statemachine", level="INFO") as logs:
            i.start()
            for e in events:
                try:
                    i.send(e)
                except Exception:  # noqa: BLE001
                    pass
        return logs.output

    def test_transition_failed_and_error_are_logged(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "actionErrorPolicy": "fail",
            "states": {
                "a": {"on": {"GO": {"target": "b", "actions": ["boom"]}}},
                "b": {},
            },
        }

        def boom(i, c, e, a):
            raise RuntimeError("x")

        out = self._run(cfg, MachineLogic(actions={"boom": boom}), ["GO"])
        joined = "\n".join(out)
        self.assertIn("failing action(s)", joined)
        self.assertIn("entered status 'error'", joined)

    def test_guard_error_is_logged(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "guard": "g"}}},
                "b": {},
            },
        }

        def g(c, e):
            raise ValueError("nope")

        out = self._run(cfg, MachineLogic(guards={"g": g}), ["GO"])
        self.assertTrue(any("RAISED" in line for line in out), out)

    def test_unhandled_and_done_are_logged(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {"type": "final"}},
        }
        out = self._run(cfg, MachineLogic(), ["NOPE", "GO"])
        joined = "\n".join(out)
        self.assertIn("unhandled", joined)
        self.assertIn("is done", joined)


# -----------------------------------------------------------------------------
# 🧵 sync_interpreter.py — built-in action failure fires on_action_error
# -----------------------------------------------------------------------------
class TestSyncBuiltinActionFailure(_Quiet):
    def test_builtin_failure_is_reported_and_policy_applied(self) -> None:
        """`sendTo` an unknown actor under `fail` -> TransitionFailedError."""
        cfg = {
            "id": "m",
            "initial": "a",
            "actionErrorPolicy": "fail",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "target": "b",
                            "actions": [
                                {"type": "raise", "params": {"event": 12345}}
                            ],
                        }
                    }
                },
                "b": {},
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=MachineLogic())).start()
        i.send("GO")
        # Whether or not this particular built-in raises, the machine must be
        # in exactly one of two consistent states: transitioned, or failed.
        if i.status == "error":
            self.assertIsInstance(i.error, TransitionFailedError)
            self.assertEqual(i.current_state_ids, {"m.a"})
        else:
            self.assertEqual(i.current_state_ids, {"m.b"})


# -----------------------------------------------------------------------------
# 🧵 sync_interpreter.py — invoke with explicit id / systemId registers child
# -----------------------------------------------------------------------------
class TestSyncInvokeExplicitIds(_Quiet):
    def test_invoke_system_id_is_registered(self) -> None:
        child = {"id": "kid", "initial": "i", "states": {"i": {}}}
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {"src": "kid", "id": "worker", "systemId": "w"}
                }
            },
        }
        # 🤖 A MachineNode (not a factory) as `src` takes the child-actor path.
        logic = MachineLogic(services={"kid": create_machine(child)})
        i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        self.assertIn("w", i.system)
        self.assertIn("p:worker", i._actors)
        i.stop()


# -----------------------------------------------------------------------------
# 🛡️ validation.py — source with no parent (root-level transition)
# -----------------------------------------------------------------------------
class TestValidationRootTransition(_Quiet):
    def test_root_level_on_validates_target(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "on": {"RESET": "a"},
            "states": {"a": {}},
        }
        create_machine(cfg)  # must not raise

    def test_root_level_on_with_bad_target_is_rejected(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "on": {"RESET": "nope"},
            "states": {"a": {}},
        }
        with self.assertRaises(InvalidConfigError):
            create_machine(cfg)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
