# tests/test_state_value.py
# -----------------------------------------------------------------------------
# 🏛️ #58 (LC-55): hierarchical `value`, XState's state-value shape
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `current_state_ids` is a flat Set[str] of leaf
# ids -- fine for `in` checks, useless for anything that wants the TREE
# (UI rendering, metrics labels, `matches({"life": "booking"})`). XState's
# `snapshot.value` is the canonical hierarchical form; this adds it as a
# derived, read-only property on BaseInterpreter so both engines get it. It
# walks the node tree rather than splitting ids, so keys containing "." are
# safe. `current_state_ids` is unchanged and remains canonical internally.
# -----------------------------------------------------------------------------
"""`interpreter.value` and dict-form `matches()` (#58)."""

import json
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# The filer's OMS shape: a parallel root with a compound region.
OMS: Dict[str, Any] = {
    "id": "order",
    "type": "parallel",
    "states": {
        "life": {
            "initial": "booking",
            "states": {
                "booking": {"on": {"FILL": "filled"}},
                "filled": {"type": "final"},
            },
        },
        "protection": {
            "initial": "risk",
            "states": {
                "risk": {
                    "initial": "armed",
                    "states": {
                        "armed": {"on": {"TRIP": "tripped"}},
                        "tripped": {},
                    },
                }
            },
        },
    },
}


def _sync(cfg: Dict[str, Any]) -> SyncInterpreter:
    return SyncInterpreter(create_machine(cfg, logic=MachineLogic())).start()


class TestValueShapes(_Quiet):
    def test_atomic_root_is_leaf_key_string(self) -> None:
        i = _sync({"id": "m", "initial": "a", "states": {"a": {}, "b": {}}})
        self.assertEqual(i.value, "a")

    def test_compound_collapses_innermost_to_string(self) -> None:
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "q",
                    "states": {"q": {"initial": "r", "states": {"r": {}}}},
                }
            },
        }
        self.assertEqual(_sync(cfg).value, {"p": {"q": "r"}})

    def test_parallel_root_one_key_per_region(self) -> None:
        i = _sync(OMS)
        self.assertEqual(
            i.value, {"life": "booking", "protection": {"risk": "armed"}}
        )
        i.send("FILL")
        i.send("TRIP")
        self.assertEqual(
            i.value, {"life": "filled", "protection": {"risk": "tripped"}}
        )

    def test_nested_parallel_inside_compound(self) -> None:
        cfg = {
            "id": "m",
            "initial": "run",
            "states": {
                "run": {
                    "type": "parallel",
                    "states": {
                        "x": {"initial": "x1", "states": {"x1": {}}},
                        "y": {"initial": "y1", "states": {"y1": {}}},
                    },
                }
            },
        }
        self.assertEqual(_sync(cfg).value, {"run": {"x": "x1", "y": "y1"}})

    def test_final_leaf_renders_as_key(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"E": "z"}}, "z": {"type": "final"}},
        }
        i = _sync(cfg)
        i.send("E")
        self.assertEqual(i.value, "z")
        self.assertEqual(i.status, "done")

    def test_dotted_keys_round_trip(self) -> None:
        """Proves the walk is tree-based, not string-split."""
        cfg = {
            "id": "m",
            "initial": "v1.0",
            "states": {
                "v1.0": {"initial": "rc.1", "states": {"rc.1": {}}},
            },
        }
        self.assertEqual(_sync(cfg).value, {"v1.0": "rc.1"})

    def test_uninitialized_returns_empty_dict(self) -> None:
        i = SyncInterpreter(create_machine(OMS, logic=MachineLogic()))
        self.assertEqual(i.value, {})

    def test_async_engine_has_same_value(self) -> None:
        import asyncio

        async def main():
            i = await Interpreter(
                create_machine(OMS, logic=MachineLogic())
            ).start()
            v = i.value
            await i.stop()
            return v

        self.assertEqual(
            asyncio.run(main()),
            {"life": "booking", "protection": {"risk": "armed"}},
        )


class TestMatchesDictForm(_Quiet):
    def test_matches_dotted_string_and_nested_dict(self) -> None:
        i = _sync(OMS)
        self.assertTrue(i.matches("protection.risk.armed"))
        self.assertTrue(i.matches({"life": "booking"}))
        self.assertTrue(i.matches({"protection": {"risk": "armed"}}))
        self.assertTrue(i.matches({"life": "booking", "protection": "risk"}))
        self.assertFalse(i.matches({"life": "filled"}))
        self.assertFalse(i.matches({"protection": {"risk": "tripped"}}))
        self.assertFalse(i.matches({"nope": "x"}))

    def test_partial_dict_matches_ancestor(self) -> None:
        """A dict naming only an ancestor matches when any descendant is active."""
        i = _sync(OMS)
        self.assertTrue(i.matches({"protection": "risk"}))


class TestSnapshotCarriesValue(_Quiet):
    def test_persisted_snapshot_has_value_and_restore_ignores_it(self) -> None:
        i = _sync(OMS)
        i.send("FILL")
        snap = json.loads(i.get_snapshot())
        self.assertEqual(
            snap["value"], {"life": "filled", "protection": {"risk": "armed"}}
        )
        # Tamper with `value`; restore must rebuild from `configuration`.
        snap["value"] = {"life": "booking"}
        j = SyncInterpreter.from_snapshot(
            json.dumps(snap), create_machine(OMS, logic=MachineLogic())
        )
        self.assertEqual(
            j.value, {"life": "filled", "protection": {"risk": "armed"}}
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
