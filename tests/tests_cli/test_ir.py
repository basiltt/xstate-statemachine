# tests/tests_cli/test_ir.py
"""Tests for the code generation intermediate representation."""

import glob
import json
import logging
import os
import unittest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.cli.ir import (
    GuardIR,
    parse_guard,
    parse_machine,
)
from src.xstate_statemachine.machine_logic import MachineLogic

logger = logging.getLogger(__name__)

_CORPUS = os.path.join(
    os.path.dirname(__file__), "stately_machines", "*.json"
)


class TestHierarchyPreserved(unittest.TestCase):
    """The IR must keep nesting intact -- this is RC-1's regression test."""

    NESTED = {
        "id": "n",
        "initial": "outerA",
        "states": {
            "outerA": {
                "initial": "innerX",
                "states": {"innerX": {"on": {"GO": "innerY"}}, "innerY": {}},
                "on": {"NEXT": "outerB"},
            },
            "outerB": {"type": "final"},
        },
    }

    def test_children_are_a_tree_not_a_flat_list(self) -> None:
        """Nested states remain children, not underscore-joined siblings."""
        ir = parse_machine(self.NESTED)
        self.assertEqual(len(ir.states), 2)
        outer_a = ir.states[0]
        self.assertEqual(outer_a.key, "outerA")
        self.assertEqual(len(outer_a.children), 2)
        self.assertEqual(
            [c.key for c in outer_a.children], ["innerX", "innerY"]
        )

    def test_dotted_paths(self) -> None:
        """Every state knows its full path from the root."""
        ir = parse_machine(self.NESTED)
        self.assertEqual(
            sorted(s.dotted for s in ir.walk()),
            ["outerA", "outerA.innerX", "outerA.innerY", "outerB"],
        )

    def test_nested_initial_is_scoped_to_its_parent(self) -> None:
        """Defect #6: nested initial must not leak into the root namespace."""
        ir = parse_machine(self.NESTED)
        self.assertEqual(ir.initial, "outerA")
        self.assertEqual(ir.find("outerA").initial, "innerX")
        self.assertIsNone(ir.find("outerA.innerX").initial)

    def test_final_state_kind_is_kept(self) -> None:
        """Defect #4: `type: final` must survive parsing."""
        ir = parse_machine(self.NESTED)
        self.assertEqual(ir.find("outerB").kind, "final")


class TestCompositeGuards(unittest.TestCase):
    """RC-4: the old extractor only understood scalar string guards."""

    def test_scalar_guard(self) -> None:
        """A plain string guard parses to a single leaf."""
        self.assertEqual(parse_guard("isReady"), GuardIR(type="isReady"))

    def test_composite_guard_exposes_leaves(self) -> None:
        """Defect #5: leaves inside and/or/not must be discoverable."""
        raw = {
            "type": "and",
            "params": {
                "guards": [
                    "partialStock",
                    {"type": "not", "params": {"guards": ["isRush"]}},
                ]
            },
        }
        guard = parse_guard(raw)
        self.assertTrue(guard.is_composite)
        self.assertEqual(
            sorted(guard.leaf_names()), ["isRush", "partialStock"]
        )


class TestTimersAndRichFeatures(unittest.TestCase):
    """Defect #4/#8: after, always, tags and meta must all survive."""

    CONFIG = {
        "id": "rich",
        "initial": "waiting",
        "states": {
            "waiting": {
                "tags": ["busy"],
                "meta": {"note": "hi"},
                "after": {
                    1000: "done",
                    "BACKOFF": {"target": "done", "guard": "canRetry"},
                },
                "always": [{"target": "done", "guard": "isSkippable"}],
            },
            "done": {"type": "final"},
        },
    }

    def test_after_transitions_keep_delay_keys(self) -> None:
        """Both numeric and *named* delays are collected."""
        waiting = parse_machine(self.CONFIG).find("waiting")
        self.assertEqual(
            sorted(str(t.delay) for t in waiting.after), ["1000", "BACKOFF"]
        )

    def test_always_transitions_are_separate(self) -> None:
        """Eventless transitions are not mixed into `on`."""
        waiting = parse_machine(self.CONFIG).find("waiting")
        self.assertEqual(len(waiting.always), 1)
        self.assertEqual(waiting.always[0].guard.type, "isSkippable")

    def test_tags_and_meta_survive(self) -> None:
        """Metadata is carried through rather than dropped."""
        waiting = parse_machine(self.CONFIG).find("waiting")
        self.assertEqual(waiting.tags, ("busy",))
        self.assertEqual(waiting.meta, {"note": "hi"})


class TestCorpusFidelity(unittest.TestCase):
    """RC-2: parsing must be total across real-world machines."""

    def setUp(self) -> None:
        self.files = sorted(glob.glob(_CORPUS))
        if not self.files:  # pragma: no cover - corpus ships with the repo
            self.skipTest("stately_machines corpus not present")

    def _configs(self):
        for path in self.files:
            try:
                with open(path, encoding="utf-8") as handle:
                    yield path, json.load(handle)
            except (OSError, json.JSONDecodeError):  # pragma: no cover
                continue

    def test_every_machine_parses(self) -> None:
        """No real-world machine may crash the parser."""
        for path, config in self._configs():
            with self.subTest(machine=os.path.basename(path)):
                parse_machine(config)

    def test_no_unsupported_keys_in_corpus(self) -> None:
        """Nothing is silently dropped across 100+ real machines."""
        offenders = {}
        for path, config in self._configs():
            unsupported = parse_machine(config).all_unsupported()
            if unsupported:
                offenders[os.path.basename(path)] = sorted(set(unsupported))
        self.assertEqual(offenders, {})

    def test_state_count_matches_engine(self) -> None:
        """The IR sees exactly the states the real engine builds.

        This is the strongest available fidelity check: it compares the
        generator's view of a machine against the interpreter's own.
        """

        def count(node) -> int:
            return 1 + sum(count(c) for c in node.states.values())

        for path, config in self._configs():
            name = os.path.basename(path)
            try:
                machine = create_machine(config, logic=MachineLogic())
            except Exception:  # noqa: BLE001 - invalid fixtures are skipped
                continue
            with self.subTest(machine=name):
                self.assertEqual(
                    len(list(parse_machine(config).walk())),
                    count(machine) - 1,  # exclude the machine root itself
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
