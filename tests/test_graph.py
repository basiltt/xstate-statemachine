"""Tests for `xstate_statemachine.graph` (#269).

🏛️ The central property: every `Path` the traversal produces replays on a
fresh `SyncInterpreter` + `SimulatedClock` to exactly its `final_states`,
for every machine in the Stately corpus.
"""

from __future__ import annotations

import json
import logging
import pathlib
import unittest
from typing import Any, Dict, Tuple

from src.xstate_statemachine import SyncInterpreter, create_machine
from src.xstate_statemachine.cli.commands.analysis import _unreachable
from src.xstate_statemachine.clock import SimulatedClock
from src.xstate_statemachine.graph import (
    Path,
    Step,
    reachable_states,
    shortest_paths,
    simple_paths,
    transition_coverage_targets,
)
from src.xstate_statemachine.testing_utils import stub_logic
from src.xstate_statemachine.validation import walk

CORPUS = pathlib.Path(__file__).parent / "tests_cli" / "stately_machines"
AP = "Advance payment flow"


def _build(cfg: Dict[str, Any]):
    m = create_machine(cfg, logic=stub_logic(cfg))
    # 📝 `logic_names(config)` and `logic_names(machine)` disagree on a bare
    #    `"guard": "and"` string (DebtState_v4); the parsed machine is what
    #    the engine looks names up in, so re-stub from it.
    m.logic = stub_logic(m)
    return m


def _load(path: pathlib.Path):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return _build(cfg)


def _replay(machine, path: Path) -> frozenset:
    clock = SimulatedClock()
    interp = SyncInterpreter(machine, clock=clock)
    try:
        path.replay(interp, clock)
        return frozenset(interp.current_state_ids)
    finally:
        interp.stop()


def _corpus_machines():
    for p in sorted(CORPUS.glob("*.json")):
        try:
            m = _load(p)
            SyncInterpreter(m, clock=SimulatedClock()).start().stop()
        except Exception as exc:  # rejected at build or start
            yield p.name, None, f"{type(exc).__name__}: {exc}"[:120]
            continue
        yield p.name, m, None


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestAdvancePayment(_Quiet):
    def setUp(self) -> None:
        super().setUp()
        self.m = _load(CORPUS / "AdvancePayment.json")

    def test_reaches_challenge_and_failure(self) -> None:
        paths = shortest_paths(self.m)
        self.assertIn(frozenset({f"{AP}.challenge"}), paths)
        self.assertIn(frozenset({f"{AP}.success"}), paths)
        both = shortest_paths(self.m, guards="both")
        self.assertIn(frozenset({f"{AP}.failure"}), both)
        for p in list(paths.values()) + list(both.values()):
            self.assertEqual(_replay(self.m, p), p.final_states)

    def test_success_via_after_is_a_clock_step(self) -> None:
        # With the onDone guard True, SUBMIT lands in challenge; success is
        # then reached by the 2000 ms `after`.
        p = shortest_paths(self.m)[frozenset({f"{AP}.success"})]
        self.assertEqual(p.event_string(), "SUBMIT,+2000")
        self.assertEqual(p.steps[-1].delay_ms, 2000.0)
        self.assertIsNone(p.steps[-1].event)

    def test_guard_false_records_assumption(self) -> None:
        both = shortest_paths(self.m, guards="both")
        p = both[frozenset({f"{AP}.failure"})]
        self.assertTrue(any(s.assumptions for s in p.steps))

    def test_guards_false_mode_blocks_submit(self) -> None:
        paths = shortest_paths(self.m, guards="false")
        self.assertEqual(set(paths), {frozenset({f"{AP}.editing"})})

    def test_reachable_includes_root(self) -> None:
        self.assertIn(AP, reachable_states(self.m))

    def test_coverage_targets(self) -> None:
        targets = transition_coverage_targets(self.m)
        self.assertIn(
            (f"{AP}.challenge", "after 2000", f"{AP}.success"), targets
        )
        self.assertIn(
            (f"{AP}.editing", "on 'UPDATE_FORM'", f"{AP}.editing"), targets
        )


PARALLEL = {
    "id": "p",
    "type": "parallel",
    "states": {
        "a": {
            "initial": "a1",
            "states": {"a1": {"on": {"A": "a2"}}, "a2": {}},
        },
        "b": {
            "initial": "b1",
            "states": {"b1": {"on": {"B": "b2"}}, "b2": {}},
        },
    },
}

CYCLE = {
    "id": "c",
    "initial": "x",
    "states": {
        "x": {"on": {"NEXT": "y", "JUMP": "z"}},
        "y": {"on": {"NEXT": "z", "BACK": "x"}},
        "z": {"on": {"NEXT": "x"}},
    },
}

TIMED = {
    "id": "t",
    "initial": "s",
    "states": {
        # Step-shortest: s -(+5000)-> goal. Time-shortest: s -GO-> m -(+10)->
        # goal.
        "s": {"after": {"5000": "goal"}, "on": {"GO": "m"}},
        "m": {"after": {"10": "goal"}},
        "goal": {"type": "final"},
    },
}


class TestShapes(_Quiet):
    def test_parallel_configurations(self) -> None:
        m = _build(PARALLEL)
        paths = shortest_paths(m)
        self.assertEqual(len(paths), 4)
        for config, p in paths.items():
            self.assertEqual(len(config), 2)
            self.assertEqual(_replay(m, p), config)
        self.assertIn(frozenset({"p.a.a2", "p.b.b2"}), paths)

    def test_simple_paths_terminate_on_cycle(self) -> None:
        m = _build(CYCLE)
        paths = simple_paths(m)
        self.assertTrue(paths)
        for p in paths:
            configs = [p.steps[0].from_states] + [s.to_states for s in p.steps]
            self.assertEqual(len(configs), len(set(configs)))
            self.assertEqual(_replay(m, p), p.final_states)

    def test_simple_paths_caps(self) -> None:
        m = _build(CYCLE)
        self.assertEqual(len(simple_paths(m, max_paths=2)), 2)
        self.assertTrue(
            all(len(p.steps) <= 1 for p in simple_paths(m, max_depth=1))
        )

    def test_weight_time_prefers_smaller_delay(self) -> None:
        m = _build(TIMED)
        goal = frozenset({"t.goal"})
        by_steps = shortest_paths(m)[goal]
        by_time = shortest_paths(m, weight="time")[goal]
        self.assertEqual(by_steps.event_string(), "+5000")
        self.assertEqual(by_time.event_string(), "GO,+10")
        self.assertLess(by_time.total_delay_ms, by_steps.total_delay_ms)
        self.assertEqual(_replay(m, by_time), goal)

    def test_bad_arguments(self) -> None:
        m = _build(CYCLE)
        with self.assertRaises(ValueError):
            shortest_paths(m, guards="maybe")
        with self.assertRaises(ValueError):
            shortest_paths(m, weight="hops")
        with self.assertRaises(ValueError):
            reachable_states(m, guards="")
        with self.assertRaises(ValueError):
            simple_paths(m, guards="TRUE")

    def test_event_string_grammar(self) -> None:
        e: frozenset = frozenset()
        p = Path(
            (Step("A", None, e, e), Step(None, 1500.0, e, e)),
            e,
        )
        self.assertEqual(p.event_string(), "A,+1500")

    def test_machine_logic_restored(self) -> None:
        m = _build(CYCLE)
        logic = m.logic
        shortest_paths(m)
        self.assertIs(m.logic, logic)


#: 🐢 Machines whose `guards="both"` state space is too large to replay
#: exhaustively in a unit test (measured: addressFields has 2,700+ parallel
#: configurations by depth 6; savage needs ~50 s for depth 4). They still
#: get a shallow replay check below.
HEAVY = {"addressFields.json", "savage.json"}
DEPTH = 8


def _ancestors(machine, configs) -> set:
    nodes = {n.id: n for n in walk(machine)}
    out = set()
    for config in configs:
        for sid in config:
            node = nodes.get(sid)
            while node is not None:
                out.add(node.id)
                node = node.parent
    return out


def _transient(node) -> bool:
    """A state the engine passes THROUGH and never settles in.

    📝 With `stub_logic` a service resolves inside the entering macrostep,
    and `always` fires immediately; history nodes are pseudo-states. None
    of these can appear in a stable configuration, so static reachability
    of them is not comparable with traversal reachability.
    """
    return bool(node.invoke or "" in node.on or node.type == "history")


def _subtree(machine, sid: str):
    for n in walk(machine):
        if n.id == sid:
            return list(walk(n))
    return []


class TestCorpus(_Quiet):
    """Property checks over every machine in the corpus."""

    def test_corpus(self) -> None:
        replayed, reach_ok = 0, 0
        skipped: Dict[str, str] = {}
        mismatches: Dict[str, Tuple[str, ...]] = {}
        for name, m, err in _corpus_machines():
            if m is None:
                skipped[name] = str(err)
                continue
            with self.subTest(machine=name):
                depth = 3 if name in HEAVY else DEPTH
                found = shortest_paths(m, guards="both", max_depth=depth)
                paths = list(found.values())
                paths += simple_paths(m, max_paths=20, max_depth=4)
                for p in paths:
                    self.assertEqual(_replay(m, p), p.final_states)
                replayed += 1
                if name in HEAVY:
                    continue
                static = {n.id for n in walk(m) if not _transient(n)} - set(
                    _unreachable(m)
                )
                missing = {
                    s
                    for s in static - _ancestors(m, found)
                    if not any(_transient(d) for d in _subtree(m, s))
                }
                if missing:
                    # 📝 Static reachability over-approximates (e.g. states
                    #    behind a named delay, a spawn, or deeper than
                    #    DEPTH); record rather than force.
                    mismatches[name] = tuple(sorted(missing))
                else:
                    reach_ok += 1
        self.assertGreater(replayed, 0)
        self.assertGreater(reach_ok, 0)
        print(
            f"\n[graph corpus] replayed={replayed} skipped={skipped}"
            f"\n[graph reachable ⊇ static] ok={reach_ok} "
            f"mismatched={mismatches}"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
