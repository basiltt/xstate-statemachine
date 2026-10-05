"""#269 battle (adversary B): `xsm paths` and the `xsm simulate --events`
grammar that consumes `Path.event_string()`."""

from __future__ import annotations

import io
import json
import logging
import pathlib
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import List, Tuple
from unittest import mock

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.simulate import parse_events_arg

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "tests_cli" / "stately_machines"
PAYMENT = FIX / "AdvancePayment.json"
#: Ten corpus charts covering parallel regions, `after`, invokes, history.
PARITY = (
    "AdvancePayment.json",
    "Parallelism.json",
    "HelloWorld.json",
    "Hierarchy.json",
    "Joyride.json",
    "Kiosk.json",
    "Parking.json",
    "SimplePayment.json",
    "Token.json",
    "savage.json",
)


def _run(argv: List[str]) -> Tuple[int, str, str]:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
        reset_console()
    return code, out.getvalue(), err.getvalue()


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestPathsSimulateParity(_Quiet):
    """The documented workflow: paste a printed path into `xsm sim`."""

    def test_every_printed_path_replays_to_its_configuration(self) -> None:
        for name in PARITY:
            chart = FIX / name
            with self.subTest(chart=name):
                code, out, _ = _run(["paths", str(chart), "--json"])
                self.assertEqual(code, 0, out)
                for p in json.loads(out)["paths"]:
                    scode, sout, _ = _run(
                        ["simulate", str(chart), "--json", "--events"]
                        + [p["events"] or ","]
                    )
                    self.assertEqual(scode, 0, sout)
                    self.assertEqual(
                        sorted(json.loads(sout)["active"]),
                        p["final_states"],
                        p["events"],
                    )

    def test_json_round_trips_path_fields(self) -> None:
        code, out, _ = _run(
            ["paths", str(PAYMENT), "--json", "--guards", "both"]
        )
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertEqual(data["weight"], "steps")
        for p in data["paths"]:
            self.assertEqual(p["final_states"], sorted(p["final_states"]))
            for s in p["steps"]:
                self.assertEqual(
                    set(s), {"event", "delay_ms", "from", "to", "assumptions"}
                )
                self.assertIsInstance(s["assumptions"], list)

    def test_json_carries_no_context_values(self) -> None:
        # 🔒 AdvancePayment's context holds `amount: 149900`.
        _, out, _ = _run(["paths", str(PAYMENT), "--json"])
        self.assertNotIn("149900", out)
        self.assertNotIn("context", out)


class TestPathsOptions(_Quiet):
    def test_weight_time_is_exposed(self) -> None:
        code, out, _ = _run(
            ["paths", str(PAYMENT), "--json", "--weight", "time"]
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["weight"], "time")

    def test_help_lists_every_option(self) -> None:
        code, out, _ = _run(["paths", "--help"])
        self.assertEqual(code, 0)
        for opt in (
            "--simple",
            "--guards",
            "--max-depth",
            "--max-paths",
            "--weight",
            "--json",
        ):
            self.assertIn(opt, out)

    def test_negative_bounds_are_usage_errors(self) -> None:
        for opt in ("--max-depth", "--max-paths"):
            with self.subTest(opt=opt):
                code, _, err = _run(["paths", str(PAYMENT), opt, "-1"])
                self.assertEqual(code, 2)
                self.assertIn("must be >= 0", err)

    def test_a_chart_that_cannot_start_is_one_line_exit_1(self) -> None:
        with mock.patch(
            "src.xstate_statemachine.cli.commands.paths.shortest_paths",
            side_effect=RuntimeError("boom at start"),
        ):
            code, out, err = _run(["paths", str(PAYMENT), "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("cannot be explored: RuntimeError: boom at start", out)
        self.assertNotIn("Traceback", out + err)

    def test_unbuildable_chart_exit_1(self) -> None:
        bad = pathlib.Path(self.id().replace(".", "_") + ".json")
        tmp = ROOT / "tests" / "tests_cli" / bad.name
        tmp.write_text('{"id":"b","initial":"nope","states":{"a":{}}}')
        self.addCleanup(tmp.unlink)
        code, out, _ = _run(["paths", str(tmp), "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("does not build", out)

    def test_huge_state_name(self) -> None:
        name = "s" * 10_000
        tmp = ROOT / "tests" / "tests_cli" / "_battle269_huge.json"
        tmp.write_text(
            json.dumps(
                {
                    "id": "h",
                    "initial": "a",
                    "states": {"a": {"on": {"GO": name}}, name: {}},
                }
            )
        )
        self.addCleanup(tmp.unlink)
        code, out, _ = _run(["paths", str(tmp), "--json"])
        self.assertEqual(code, 0)
        self.assertIn(f"h.{name}", json.loads(out)["paths"][1]["final_states"])


class TestEventsGrammar(_Quiet):
    BAD = ("+1e309", "+inf", "+nan", "+-5", "+abc", "+")

    def test_parse_rejects_non_finite_or_negative_advances(self) -> None:
        for tok in self.BAD:
            with self.subTest(tok=tok):
                with self.assertRaisesRegex(ValueError, "bad clock advance"):
                    parse_events_arg(tok, None)
        with self.assertRaisesRegex(ValueError, "bad clock advance"):
            parse_events_arg(None, "-1")

    def test_good_advances_still_parse(self) -> None:
        self.assertEqual(
            parse_events_arg("A,+0,+2.5,+1e3", None),
            [{"send": "A"}, {"clock": 0.0}, {"clock": 2.5}, {"clock": 1000}],
        )

    def test_simulate_reports_bad_advance_without_traceback(self) -> None:
        for tok in self.BAD:
            with self.subTest(tok=tok):
                code, out, err = _run(
                    ["simulate", str(PAYMENT), "--json", "--events", tok]
                )
                self.assertEqual(code, 2)
                self.assertIn("bad clock advance", out + err)
                self.assertNotIn("Infinity", out)
                self.assertNotIn("NaN", out)


class TestStaticUnreachable(_Quiet):
    """`xsm inspect` / `validate`: a state is never called unreachable
    when the engine enters it (deep `#id` / history targets enter every
    ancestor and every sibling region of a parallel ancestor)."""

    CFG = {
        "id": "m",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "DEEP": "#m.a.b.leaf",
                    "HIST": "#m.h.hist",
                    "PAR": "#m.p.left.x",
                }
            },
            "a": {
                "initial": "b",
                "states": {"b": {"initial": "leaf", "states": {"leaf": {}}}},
            },
            "h": {
                "initial": "one",
                "states": {"one": {}, "hist": {"type": "history"}},
            },
            "p": {
                "type": "parallel",
                "states": {
                    "left": {"initial": "x", "states": {"x": {}}},
                    "right": {"initial": "y", "states": {"y": {}}},
                },
            },
            "orphan": {},
        },
    }

    def test_deep_targets_mark_their_ancestors(self) -> None:
        from src.xstate_statemachine import create_machine
        from src.xstate_statemachine.cli.commands.analysis import (
            _unreachable,
        )
        from src.xstate_statemachine.graph import reachable_states
        from src.xstate_statemachine.testing_utils import stub_logic

        m = create_machine(self.CFG, logic=stub_logic(self.CFG))
        static = _unreachable(m)
        self.assertEqual(static, ["m.orphan"])
        self.assertFalse(set(static) & reachable_states(m, guards="both"))

    def test_corpus_charts_with_former_false_warnings(self) -> None:
        from src.xstate_statemachine.cli.commands.analysis import (
            _unreachable,
            analyse,
        )

        for name, state in (
            ("product.json", "product.unavailable"),
            ("Token.json", "Token.With Artists"),
            (
                "Thermostatic_Valve.json",
                "Thermostatic Valve Controller.online",
            ),
        ):
            with self.subTest(chart=name):
                m = analyse(FIX / name).machine
                self.assertNotIn(state, _unreachable(m))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
