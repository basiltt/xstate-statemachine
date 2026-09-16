# tests/test_hot_path_perf.py
# -----------------------------------------------------------------------------
# ⚡ Hot-path optimisations -- behaviour pins, not timings
# -----------------------------------------------------------------------------
# 🏛️ Each optimisation below removes work from the per-event path by
# answering a question ONCE at build time. A timing test would be flaky;
# instead these pin (a) that the build-time answer is right for the shapes
# that matter and (b) that the slow path is still taken when it must be, so
# a future refactor cannot quietly drop the fast path OR the safety net.
# -----------------------------------------------------------------------------
"""Pins for the build-time indexes the interpreters rely on for speed."""

import logging
import unittest
import warnings
from typing import Any, Dict
from unittest import mock

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.base_interpreter import BaseInterpreter


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


FLAT: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}},
}


class TestResolvedTargetMemo(_Quiet):
    def test_every_target_is_resolved_at_build(self) -> None:
        cfg = {
            "id": "h",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {"a1": {"on": {"X": "#h.b.b2"}}},
                    "on": {"UP": "b"},
                },
                "b": {"initial": "b1", "states": {"b1": {}, "b2": {}}},
            },
        }
        m = create_machine(cfg)
        a1 = m.get_state_by_id("h.a.a1")
        assert a1 is not None
        self.assertIs(
            a1.on["X"][0].resolved_target, m.get_state_by_id("h.b.b2")
        )
        self.assertIs(m.states["a"].on["UP"][0].resolved_target, m.states["b"])

    def test_runtime_does_not_call_the_resolver_for_a_memoised_target(
        self,
    ) -> None:
        m = create_machine(FLAT)
        i = SyncInterpreter(m).start()
        with mock.patch.object(
            BaseInterpreter,
            "_resolve_target_state_node",
            wraps=i._resolve_target_state_node,
        ) as spy:
            i.send("T")
        spy.assert_not_called()
        self.assertEqual(i.current_state_ids, {"m.b"})
        i.stop()

    def test_unresolvable_target_still_takes_the_slow_path(self) -> None:
        """`strict_targets=False` keeps a bad target alive; the runtime must
        still try (and fail) to resolve it rather than treating the missing
        memo as 'targetless'."""
        from src.xstate_statemachine import StateNotFoundError

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "ghost"}}},
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = create_machine(cfg, strict_targets=False)
        self.assertIsNone(m.states["a"].on["GO"][0].resolved_target)
        i = SyncInterpreter(m).start()
        self.assertIsInstance(
            i.send("GO", wait=True).error, StateNotFoundError
        )
        self.assertEqual(i.current_state_ids, {"m.a"})


class TestTreeFeatureFlags(_Quiet):
    def test_flags_false_for_a_plain_machine(self) -> None:
        m = create_machine(FLAT)
        self.assertFalse(m.has_history_states)
        self.assertFalse(m.has_always_transitions)

    def test_history_flag_sees_a_deeply_nested_history_child(self) -> None:
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "q",
                    "states": {
                        "q": {
                            "initial": "x",
                            "states": {
                                "x": {},
                                "hist": {"type": "history"},
                            },
                        }
                    },
                }
            },
        }
        self.assertTrue(create_machine(cfg).has_history_states)

    def test_always_flag_sees_root_and_nested_always(self) -> None:
        root = {
            "id": "m",
            "initial": "a",
            "states": {"a": {}, "b": {}},
            "always": {"target": "b", "guard": "never"},
        }
        nested = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {"a1": {"always": "a2"}, "a2": {}},
                }
            },
        }
        logic = MachineLogic(guards={"never": lambda c, e: False})
        self.assertTrue(
            create_machine(root, logic=logic).has_always_transitions
        )
        self.assertTrue(create_machine(nested).has_always_transitions)

    def test_history_is_still_recorded_when_declared(self) -> None:
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "a",
                    "states": {
                        "a": {"on": {"N": "b"}},
                        "b": {},
                        "h": {"type": "history"},
                    },
                    "on": {"OUT": "q"},
                },
                "q": {"on": {"BACK": "p.h"}},
            },
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        for e in ("N", "OUT", "BACK"):
            i.send(e)
        self.assertEqual(i.current_state_ids, {"m.p.b"})

    def test_always_chain_still_settles_on_both_engines(self) -> None:
        import asyncio

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {"always": "c"},
                "c": {"always": "d"},
                "d": {},
            },
        }
        s = SyncInterpreter(create_machine(cfg)).start()
        s.send("GO")
        self.assertEqual(s.current_state_ids, {"m.d"})

        async def main():
            i = await Interpreter(create_machine(cfg)).start()
            r = await i.send("GO", wait=True)
            await i.stop()
            return r.state_ids

        self.assertEqual(asyncio.run(main()), frozenset({"m.d"}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
