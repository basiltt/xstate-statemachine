# tests/test_wave2_review_findings.py
# -----------------------------------------------------------------------------
# 🧪 Pre-merge critical review of the wave-2 branch -- regression pins
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: same contract as test_v080_review_findings.py.
# Every test here was written against a defect the adversarial review of
# the wave-2 branch CONFIRMED BY REPRODUCTION, and failed before its fix.
# Claims the review made that did NOT reproduce (pure-probe thread safety,
# history leaking across pure calls) are pinned below as passing guards so
# they stay disproved.
# -----------------------------------------------------------------------------
"""Regression pins for the wave-2 review findings."""

import asyncio
import json
import logging
import threading
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    SnapshotMidStepError,
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
    get_initial_snapshot,
    get_next_snapshot,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# -----------------------------------------------------------------------------
# F1 (CRITICAL): `value` / snapshot must never raise on a live machine
# -----------------------------------------------------------------------------
class TestValueNeverRaisesOnLiveMachine(_Quiet):
    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"GO": {"target": "b", "actions": ["work"]}}},
            "b": {"initial": "b1", "states": {"b1": {}}},
        },
    }

    def test_snapshot_during_async_transition_succeeds(self) -> None:
        async def work(i, c, e, a):
            await asyncio.sleep(0.15)

        async def main():
            i = await Interpreter(
                create_machine(
                    self.CFG, logic=MachineLogic(actions={"work": work})
                )
            ).start()
            await i.send("GO")
            values = []
            refused = 0
            for _ in range(30):
                # `value` itself never raises (the original review finding).
                values.append(i.value)
                # 🏛️ #102: a SNAPSHOT mid-transition is refused, typed. The
                #    old contract let it succeed with `state_ids: []`, which
                #    restored as a permanently inert machine reporting
                #    `running`. `{}` is an honest answer for `value`; it is
                #    not a restorable configuration.
                try:
                    i.get_persisted_snapshot()
                except SnapshotMidStepError:
                    refused += 1
                await asyncio.sleep(0.01)
            await i.stop()
            return values, refused

        values, refused = asyncio.run(main())
        self.assertIn("a", values[:2])
        self.assertEqual(values[-1], {"b": "b1"})
        self.assertTrue(all(v in ("a", {}, {"b": "b1"}) for v in values))
        self.assertGreater(refused, 0, "the 150 ms window must be refused")
        self.assertLess(refused, 30, "settled snapshots must still succeed")

    def test_value_from_entry_action_does_not_raise(self) -> None:
        seen = []

        def peek(i, c, e, a):
            seen.append(i.value)

        cfg = json.loads(json.dumps(self.CFG))
        cfg["states"]["b"]["entry"] = ["peek"]
        i = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(
                    actions={"peek": peek, "work": lambda *a: 0}
                ),
            )
        ).start()
        i.send("GO")
        self.assertEqual(len(seen), 1)

    def test_value_on_torn_restore_is_partial_not_exception(self) -> None:
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {"p": {"initial": "q", "states": {"q": {}}}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i._active_state_nodes.discard(i.machine.states["p"].states["q"])
        self.assertEqual(i.value, "p")  # ancestor key, not a raise


# -----------------------------------------------------------------------------
# F2 (CRITICAL): spawn_blocking_ with no timeout must not wedge the machine
# -----------------------------------------------------------------------------
class TestSpawnBlockingDefaultIsBounded(_Quiet):
    """A `spawn_blocking_` child that never reaches a final state must not
    wedge its parent forever. The DEFAULT wait is finite (30 s -- long
    enough for any real child, short enough to surface as a warning rather
    than a hang); machines tune it with `spawnBlockingTimeout`. The tests
    set a short value so they run fast; the default itself is pinned."""

    FOREVER: Dict[str, Any] = {
        "id": "f",
        "initial": "x",
        "states": {"x": {"after": {"30": "y"}}, "y": {}},  # never final
    }

    def _parent(self) -> Dict[str, Any]:
        return {
            "id": "p",
            "initial": "a",
            "spawnBlockingTimeout": 80,
            "states": {
                "a": {"entry": ["spawn_blocking_f"], "on": {"GO": "b"}},
                "b": {},
            },
        }

    def test_default_timeout_is_finite(self) -> None:
        from src.xstate_statemachine.models import (
            DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS,
        )

        self.assertIsInstance(DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS, float)
        self.assertGreater(DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS, 0)
        # And a machine that sets nothing inherits it (not None).
        m = create_machine({"id": "m", "initial": "a", "states": {"a": {}}})
        self.assertIsNone(m.spawn_blocking_timeout_ms)  # None -> default

    def test_async_start_returns_and_machine_stays_responsive(self) -> None:
        async def main():
            i = Interpreter(
                create_machine(
                    self._parent(),
                    logic=MachineLogic(
                        services={"f": create_machine(self.FOREVER)}
                    ),
                )
            )
            await asyncio.wait_for(i.start(), timeout=5.0)
            await i.send("GO")
            for _ in range(500):
                if i.current_state_ids == {"p.b"}:
                    break
                await asyncio.sleep(0.002)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), {"p.b"})

    def test_sync_default_timeout_is_applied_when_unset(self) -> None:
        """No `spawnBlockingTimeout` -> the module default is used (not None).
        Patched short so the test does not wait the real 30 s."""
        from unittest import mock

        import src.xstate_statemachine.sync_interpreter as sync_mod

        parent = self._parent()
        del parent["spawnBlockingTimeout"]
        logic = MachineLogic(services={"f": create_machine(self.FOREVER)})
        with mock.patch.object(
            sync_mod, "DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS", 60.0
        ):
            i = SyncInterpreter(create_machine(parent, logic=logic)).start()
        self.assertEqual(i.status, "running")
        i.stop()

    def test_sync_start_returns(self) -> None:
        done = threading.Event()
        holder: Dict[str, Any] = {}

        def run():
            i = SyncInterpreter(
                create_machine(
                    self._parent(),
                    logic=MachineLogic(
                        services={"f": create_machine(self.FOREVER)}
                    ),
                )
            ).start()
            holder["i"] = i
            done.set()

        threading.Thread(target=run, daemon=True).start()
        self.assertTrue(done.wait(5.0), "sync start() wedged")
        holder["i"].stop()


# -----------------------------------------------------------------------------
# F5 (CRITICAL): stop(drain=True) must return when a drained event completes
# -----------------------------------------------------------------------------
class TestDrainCompletesWhenMachineFinishes(_Quiet):
    def test_stop_drain_returns_after_terminal_event(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"FIN": "f", "X": {}}},
                "f": {"type": "final"},
            },
        }

        async def main():
            i = await Interpreter(create_machine(cfg)).start()
            i.send("FIN")
            i.send("X")
            i.send("X")
            await asyncio.wait_for(i.stop(drain=True), timeout=3.0)
            return i.status, i.pending_events

        status, left = asyncio.run(main())
        self.assertEqual(status, "done")
        self.assertEqual(left, ())


# -----------------------------------------------------------------------------
# F3 (HIGH): completed spawned children leave the parent's actor map
# -----------------------------------------------------------------------------
class TestCompletedChildrenAreReaped(_Quiet):
    def test_actor_map_does_not_grow_with_completed_spawns(self) -> None:
        kid = {"id": "k", "initial": "f", "states": {"f": {"type": "final"}}}
        p = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"on": {"S": {"actions": ["spawn_k"]}}}},
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    p, logic=MachineLogic(services={"k": create_machine(kid)})
                )
            ).start()
            for _ in range(50):
                await i.send("S")
            for _ in range(200):
                if not i._actors:
                    break
                await asyncio.sleep(0.005)
            out = len(i._actors)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), 0)

    def test_sync_actor_map_does_not_grow(self) -> None:
        kid = {"id": "k", "initial": "f", "states": {"f": {"type": "final"}}}
        p = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"on": {"S": {"actions": ["spawn_blocking_k"]}}}},
        }
        i = SyncInterpreter(
            create_machine(
                p, logic=MachineLogic(services={"k": create_machine(kid)})
            )
        ).start()
        for _ in range(50):
            i.send("S")
        self.assertEqual(len(i._actors), 0)
        i.stop()


# -----------------------------------------------------------------------------
# F6 (HIGH): stop(drain=True) on a restored-but-unstarted interpreter
# -----------------------------------------------------------------------------
class TestDrainOnRestoredUnstarted(_Quiet):
    def test_does_not_raise(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }

        async def main():
            i = await Interpreter(create_machine(cfg)).start()
            snap = i.get_snapshot()
            await i.stop()
            j = Interpreter.from_snapshot(snap, create_machine(cfg))
            await j.stop(drain=True)
            return j.status

        self.assertEqual(asyncio.run(main()), "stopped")


# -----------------------------------------------------------------------------
# F8 (HIGH): sync engine replays a restored inbox on start()
# -----------------------------------------------------------------------------
class TestSyncRestoredInboxReplays(_Quiet):
    def test_restored_pending_events_processed_on_start(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        snap = json.loads(i.get_snapshot())
        snap["pending_events"] = [{"type": "GO", "payload": {}}]
        j = SyncInterpreter.from_snapshot(
            json.dumps(snap), create_machine(cfg)
        )
        self.assertEqual(len(j.pending_events), 1)
        j.start()
        self.assertEqual(j.current_state_ids, {"m.b"})
        self.assertEqual(j.pending_events, ())


# -----------------------------------------------------------------------------
# F9 (HIGH): structure_hash must see composite-guard children
# -----------------------------------------------------------------------------
class TestStructureHashCompositeGuards(_Quiet):
    def _m(self, guard: Any) -> Any:
        return create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"E": {"target": "b", "guard": guard}}},
                    "b": {},
                },
            },
            logic=MachineLogic(
                guards={n: (lambda c, e: True) for n in ("g1", "g2", "g3")}
            ),
        )

    def test_changing_a_composite_child_changes_the_hash(self) -> None:
        a = self._m({"type": "and", "children": ["g1", "g2"]})
        b = self._m({"type": "and", "children": ["g1", "g3"]})
        self.assertNotEqual(a.structure_hash, b.structure_hash)

    def test_state_in_target_is_part_of_the_hash(self) -> None:
        a = self._m({"type": "stateIn", "params": {"stateValue": "b"}})
        b = self._m({"type": "stateIn", "params": {"stateValue": "a"}})
        self.assertNotEqual(a.structure_hash, b.structure_hash)


# -----------------------------------------------------------------------------
# F10 (HIGH): resolve_input must cope with un-introspectable callables
# -----------------------------------------------------------------------------
class TestResolveInputRobustness(_Quiet):
    def _inv(self, fn: Any) -> Any:
        m = create_machine(
            {
                "id": "h",
                "initial": "s",
                "states": {"s": {"invoke": {"src": "svc", "input": fn}}},
            },
            logic=MachineLogic(services={"svc": lambda *a: 1}),
        )
        return m.states["s"].invoke[0]

    def test_builtin_type_as_factory(self) -> None:
        self.assertEqual(self._inv(dict).resolve_input({}, None), {})

    def test_callable_with_defaults_uses_required_arity(self) -> None:
        def f(args, debug=False):
            return {"c": args["context"]["x"]}

        self.assertEqual(self._inv(f).resolve_input({"x": 1}, None), {"c": 1})

    def test_sync_engine_routes_resolver_error_to_on_error(self) -> None:
        def bad(ctx, evt):
            raise KeyError("nope")

        cfg = {
            "id": "book",
            "initial": "running",
            "states": {
                "running": {
                    "invoke": {"src": "leg", "input": bad, "onError": "failed"}
                },
                "failed": {},
            },
        }
        child = {"id": "leg", "initial": "w", "states": {"w": {}}}
        i = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(services={"leg": create_machine(child)}),
            )
        ).start()
        self.assertEqual(i.current_state_ids, {"book.failed"})
        i.stop()


# -----------------------------------------------------------------------------
# F11 (MEDIUM): `input` must not overwrite declared context keys by default
# -----------------------------------------------------------------------------
class TestInputDoesNotClobberContext(_Quiet):
    def test_interpreter_input_keeps_0_7_semantics(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"user": "default"},
            "states": {"a": {}},
        }
        i = SyncInterpreter(
            create_machine(cfg), input={"user": "attacker"}
        ).start()
        self.assertEqual(i.context["user"], "default")
        self.assertEqual(i.context["input"], {"user": "attacker"})

    def test_invoke_child_still_seeded_via_factory(self) -> None:
        """#42's contract: parameterise a child through its context FACTORY."""
        child = {
            "id": "leg",
            "initial": "w",
            "context": lambda args: {"snapshot": args["input"]["snapshot"]},
            "states": {"w": {}},
        }
        parent = {
            "id": "book",
            "initial": "r",
            "states": {
                "r": {
                    "invoke": {
                        "src": "leg",
                        "id": "l",
                        "input": {"snapshot": 7},
                    }
                }
            },
        }
        i = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(services={"leg": create_machine(child)}),
            )
        ).start()
        self.assertEqual(i._actors["book:l"].context, {"snapshot": 7})
        i.stop()


# -----------------------------------------------------------------------------
# A2 (HIGH, wave 1): create_machine(strict_targets=True) must reach the machine
# -----------------------------------------------------------------------------
class TestStrictTargetsTwoSwitches(_Quiet):
    """`create_machine(strict_targets=)` and the `strictTargets` config key
    are DIFFERENT switches. The kwarg (default True) rejects unresolvable
    targets; the config key (default False) disables the `.child` sibling
    fallback. Review A2 flagged the naming; wiring them together turned the
    opt-in into the default and rejected every legitimate `.sibling`
    machine (8 CLI round-trip failures). Pinned so they stay independent."""

    SIBLING: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"G": ".b"}}, "b": {}},
    }

    def test_default_kwarg_keeps_sibling_fallback(self) -> None:
        m = create_machine(self.SIBLING)  # strict_targets=True by default
        self.assertFalse(m.strict_targets)
        i = SyncInterpreter(m).start()
        i.send("G")
        self.assertEqual(i.current_state_ids, {"m.b"})

    def test_config_key_disables_sibling_fallback(self) -> None:
        from src.xstate_statemachine import InvalidConfigError

        cfg = dict(self.SIBLING, strictTargets=True)
        with self.assertRaises(InvalidConfigError):
            create_machine(cfg)


# -----------------------------------------------------------------------------
# Disproved review claims -- kept as guards
# -----------------------------------------------------------------------------
class TestPureProbeGuards(_Quiet):
    def test_concurrent_pure_calls_from_threads_are_correct(self) -> None:
        """The probe cache is per-thread (`threading.local`).

        History: the review flagged the shared cache as unsafe; it did not
        reproduce on Windows but produced 502 wrong results out of 4,000 on
        Linux CI, where the GIL hands off differently. A per-thread cache
        removes the shared mutable state entirely. Uses a machine whose
        transition mutates context via `assign`, so an interleaved probe
        would also corrupt CONTEXT, not just the state id.
        """
        m = create_machine(
            {
                "id": "m",
                "initial": "a",
                "context": {"n": 0},
                "states": {
                    "a": {
                        "on": {
                            "GO": {
                                "target": "b",
                                "actions": [
                                    {
                                        "type": "assign",
                                        "params": {"assignment": {"n": 1}},
                                    }
                                ],
                            }
                        }
                    },
                    "b": {"on": {"BACK": "a"}},
                },
            }
        )
        base = get_initial_snapshot(m)
        bad = [0]
        start = threading.Barrier(8)

        def w():
            start.wait()
            for _ in range(500):
                nxt = get_next_snapshot(m, base, "GO")
                if nxt.state_ids != {"m.b"} or nxt.context != {"n": 1}:
                    bad[0] += 1
                back = get_next_snapshot(m, nxt, "BACK")
                if back.state_ids != {"m.a"}:
                    bad[0] += 1

        ts = [threading.Thread(target=w) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(bad[0], 0)

    def test_history_does_not_leak_between_pure_calls(self) -> None:
        h = {
            "id": "h",
            "initial": "work",
            "states": {
                "work": {
                    "initial": "one",
                    "states": {
                        "one": {"on": {"N": "two"}},
                        "two": {},
                        "hist": {"type": "history"},
                    },
                    "on": {"P": "paused"},
                },
                "paused": {"on": {"R": "work.hist"}},
            },
        }
        mh = create_machine(h)
        s = get_initial_snapshot(mh)
        for e in ("N", "P", "R"):
            s = get_next_snapshot(mh, s, e)
        self.assertEqual(s.state_ids, {"h.work.two"})
        s2 = get_initial_snapshot(mh)
        for e in ("P", "R"):
            s2 = get_next_snapshot(mh, s2, e)
        self.assertEqual(s2.state_ids, {"h.work.one"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
