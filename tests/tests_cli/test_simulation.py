# tests/tests_cli/test_simulation.py
"""Tests for reachable event sequences in generated runners (S4)."""

import glob
import json
import logging
import os
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import SyncInterpreter, create_machine
from src.xstate_statemachine.cli.ir import parse_machine
from src.xstate_statemachine.cli.simulation import (
    demo_events,
    reachable_event_sequence,
)
from src.xstate_statemachine.machine_logic import MachineLogic

_CORPUS = os.path.join(os.path.dirname(__file__), "stately_machines", "*.json")

# 📝 The motivating example. Alphabetical order sends ALPHA, MIKE, ZULU --
#    and ZULU is a dead no-op because nothing in `c` handles it.
SPELLING_TRAP: Dict[str, Any] = {
    "id": "n",
    "initial": "a",
    "states": {
        "a": {"on": {"ZULU": "c", "ALPHA": "b"}},
        "b": {"on": {"MIKE": "c"}},
        "c": {},
    },
}


def _run(config: Dict[str, Any], events: List[str]) -> List[bool]:
    """Send *events* to a real interpreter, recording which ones moved it."""
    interpreter = SyncInterpreter(
        create_machine(config, logic=MachineLogic())
    ).start()
    moved: List[bool] = []
    for event in events:
        before = set(interpreter.current_state_ids)
        interpreter.send(event)
        moved.append(set(interpreter.current_state_ids) != before)
    return moved


class TestReachableOrder(unittest.TestCase):
    """Sequences must be walkable, not alphabetical."""

    def test_no_dead_events_in_the_spelling_trap(self) -> None:
        """Every emitted event actually moves the machine."""
        events = reachable_event_sequence(parse_machine(SPELLING_TRAP))
        self.assertTrue(events)
        self.assertTrue(all(_run(SPELLING_TRAP, events)))

    def test_prefers_a_path_that_keeps_going(self) -> None:
        """A greedy walk would take ZULU and end the demo immediately.

        ZULU jumps straight to the terminal state `c`, so a naive
        "anything unvisited" rule stops after one event and never shows
        `b` at all.
        """
        events = reachable_event_sequence(parse_machine(SPELLING_TRAP))
        self.assertEqual(events, ["ALPHA", "MIKE"])

    def test_descends_into_nested_initial_states(self) -> None:
        """Entering a compound state activates its initial descendant."""
        config = {
            "id": "n",
            "initial": "outer",
            "states": {
                "outer": {
                    "initial": "innerX",
                    "states": {
                        "innerX": {"on": {"GO": "innerY"}},
                        "innerY": {},
                    },
                },
                "done": {},
            },
        }
        events = reachable_event_sequence(parse_machine(config))
        self.assertIn("GO", events)
        self.assertTrue(all(_run(config, events)))

    def test_includes_machine_level_escape_events(self) -> None:
        """A root-level `on` block is live from every state."""
        config = {
            "id": "n",
            "initial": "a",
            "on": {"EMERGENCY": "halt"},
            "states": {"a": {"on": {"GO": "b"}}, "b": {}, "halt": {}},
        }
        self.assertIn(
            "EMERGENCY", reachable_event_sequence(parse_machine(config))
        )

    def test_terminates_on_a_cyclic_machine(self) -> None:
        """A ping-pong machine must not produce an unbounded demo."""
        config = {
            "id": "n",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {"on": {"BACK": "a"}},
            },
        }
        events = reachable_event_sequence(parse_machine(config), max_events=5)
        self.assertLessEqual(len(events), 5)

    def test_machine_with_no_transitions_yields_nothing(self) -> None:
        """Nothing to demonstrate means an empty sequence, not a crash."""
        config = {"id": "n", "initial": "a", "states": {"a": {}}}
        self.assertEqual(reachable_event_sequence(parse_machine(config)), [])


class TestDemoEventsFallback(unittest.TestCase):
    """A demo is a convenience and must never break generation."""

    def test_falls_back_to_alphabetical_when_unreachable(self) -> None:
        """Events that cannot be walked are still worth listing."""
        config = {
            "id": "n",
            "initial": "a",
            "states": {"a": {"on": {"NOWHERE": {"actions": "noop"}}}},
        }
        self.assertEqual(demo_events(config), ["NOWHERE"])

    def test_malformed_config_does_not_raise(self) -> None:
        """A broken machine yields an empty demo rather than an exception."""
        self.assertEqual(demo_events({"id": "n"}), [])


class TestCorpusEffectiveness(unittest.TestCase):
    """Across real machines, most emitted events should do something."""

    def test_most_events_move_the_machine(self) -> None:
        """Measured across the corpus, dead events should be rare.

        Alphabetical ordering routinely ended demos on a no-op. Guarded
        transitions are deliberately included (guards depend on user code
        that does not exist yet), so a small no-op tail is expected.
        """
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        effective = total = 0
        for path in sorted(glob.glob(_CORPUS))[:40]:
            try:
                with open(path, encoding="utf-8") as handle:
                    config = json.load(handle)
                machine = create_machine(config, logic=MachineLogic())
            except Exception:  # noqa: BLE001 - invalid fixtures skipped
                continue

            events = reachable_event_sequence(parse_machine(config))
            if not events:
                continue
            try:
                interpreter = SyncInterpreter(machine).start()
            except Exception:  # noqa: BLE001 - unstartable machines skipped
                continue

            for event in events:
                before = set(interpreter.current_state_ids)
                try:
                    interpreter.send(event)
                except Exception:  # noqa: BLE001
                    break
                total += 1
                if set(interpreter.current_state_ids) != before:
                    effective += 1

        self.assertGreater(total, 50, "corpus did not exercise enough events")
        self.assertGreater(effective / total, 0.85)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
