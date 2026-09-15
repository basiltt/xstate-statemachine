# tests/test_target_resolution.py
# -----------------------------------------------------------------------------
# 🏛️ #34 (LC-06): target resolution must be lexically scoped, never a search
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: a bare target names a sibling; `#id` names a node
# by id; `.child` names a descendant. There is no "search the whole tree for
# a state with that leaf name" rule in XState or SCXML. The runtime used to
# have three such fallbacks, ending in an exhaustive last-segment walk, so a
# typo bound to an unrelated state in another parallel region and MOVED it.
# Build-time validation (#30) catches this for strict machines; this suite
# pins the RUNTIME contract, which must hold even under `strict_targets=False`.
# -----------------------------------------------------------------------------
"""Runtime target-resolution contract (#34)."""

import logging
import unittest
import warnings
from typing import Any, Dict

from src.xstate_statemachine import (
    InvalidConfigError,
    MachineLogic,
    StateNotFoundError,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# The filer's machine: `order` has no `filled`; `audit.archive.filled` does.
FOREIGN: Dict[str, Any] = {
    "id": "m",
    "type": "parallel",
    "states": {
        "audit": {
            "initial": "archive",
            "states": {
                "archive": {
                    "initial": "open",
                    "states": {"open": {}, "filled": {}},
                }
            },
        },
        "order": {
            "initial": "submitting",
            "states": {
                "submitting": {"on": {"FILL": "filled"}},
                "done": {},
            },
        },
    },
}


def _lenient(cfg: Dict[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return create_machine(cfg, logic=MachineLogic(), strict_targets=False)


class TestUnresolvableTargets(_Quiet):
    def test_unresolvable_target_raises_at_build_time(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(FOREIGN, logic=MachineLogic())
        self.assertIn("'filled'", str(cm.exception))

    def test_foreign_region_never_bound_by_leaf_name(self) -> None:
        """Even with build-time validation off, the RUNTIME must not bind
        `m.audit.archive.filled` from a transition declared in `order`."""
        i = SyncInterpreter(_lenient(FOREIGN)).start()
        before = set(i.current_state_ids)
        with self.assertRaises(StateNotFoundError):
            i.send("FILL")
        # `audit` untouched; `order` did not move either.
        self.assertEqual(set(i.current_state_ids), before)
        self.assertIn("m.audit.archive.open", i.current_state_ids)

    def test_lenient_runtime_error_names_target_and_source(self) -> None:
        i = SyncInterpreter(_lenient(FOREIGN)).start()
        with self.assertRaises(StateNotFoundError) as cm:
            i.send("FILL")
        msg = str(cm.exception)
        self.assertIn("filled", msg)
        self.assertIn("m.order.submitting", msg)


class TestStandardResolutionUnchanged(_Quiet):
    def test_sibling_and_hash_id_targets_still_resolve(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"S": "b", "H": "#m.c.c1", "R": "c"}},
                "b": {"on": {"BACK": "a"}},
                "c": {"initial": "c1", "states": {"c1": {}}},
            },
        }
        for ev, expected in (("S", "m.b"), ("H", "m.c.c1"), ("R", "m.c.c1")):
            with self.subTest(event=ev):
                i = SyncInterpreter(create_machine(cfg)).start()
                i.send(ev)
                self.assertEqual(i.current_state_ids, {expected})

    def test_unanchored_root_prefixed_id_is_rejected_with_hint(self) -> None:
        """`"m.b"` (machine id, no `#`) is NOT a target form in XState; the
        validator rejects it and names the anchored spelling."""
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"G": "m.b"}}, "b": {}},
        }
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(cfg)
        self.assertIn('"#m.b"', str(cm.exception))

    def test_dotted_top_level_key_still_resolves(self) -> None:
        cfg = {
            "id": "m",
            "initial": "v1.0",
            "states": {"v1.0": {"on": {"G": "v2.0"}}, "v2.0": {}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i.send("G")
        self.assertEqual(i.current_state_ids, {"m.v2.0"})

    def test_child_target_from_compound_parent_transition(self) -> None:
        """A parent's `on` may name its own child by bare key (XState)."""
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "x",
                    "on": {"J": ".y"},
                    "states": {"x": {}, "y": {}},
                }
            },
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i.send("J")
        self.assertEqual(i.current_state_ids, {"m.p.y"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
