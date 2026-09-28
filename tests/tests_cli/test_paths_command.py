"""Tests for `xsm paths` (#269) and the engine-backed reachability finding
`xsm inspect` adds on top of the static pass."""

from __future__ import annotations

import io
import json
import logging
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from typing import List

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.analysis import analyse

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "tests_cli" / "stately_machines"
PAYMENT = FIX / "AdvancePayment.json"


def _run(argv: List[str]) -> tuple:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue()


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestPathsCommand(_Quiet):
    def test_plain_table_lists_every_configuration(self) -> None:
        code, out = _run(
            ["paths", str(PAYMENT), "--plain", "--guards", "both"]
        )
        self.assertEqual(code, 0, out)
        self.assertIn("4 paths (shortest, guards=both)", out)
        for state in ("editing", "challenge", "failure", "success"):
            self.assertIn(f"Advance payment flow.{state}", out)
        self.assertIn("(initial)", out)
        self.assertIn("service:", out)  # failure relies on a forced error

    def test_json_shape_and_event_grammar(self) -> None:
        code, out = _run(["paths", str(PAYMENT), "--json"])
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertEqual(data["mode"], "shortest")
        self.assertEqual(data["guards"], "true")
        finals = {tuple(p["final_states"]) for p in data["paths"]}
        self.assertIn(("Advance payment flow.challenge",), finals)
        for p in data["paths"]:
            for step in p["steps"]:
                self.assertEqual(
                    set(step),
                    {"event", "delay_ms", "from", "to", "assumptions"},
                )
            # the events column is the `xsm simulate --events` grammar
            self.assertNotIn(" ", p["events"])

    def test_simple_mode_respects_caps(self) -> None:
        code, out = _run(
            ["paths", str(PAYMENT), "--json", "--simple", "--max-paths", "2"]
        )
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertEqual(data["mode"], "simple")
        self.assertLessEqual(len(data["paths"]), 2)

    def test_broken_file_exits_one(self) -> None:
        bad = FIX / "AtmScenario.json"  # compound state without `initial`
        code, out = _run(["paths", str(bad), "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("does not build", out)


class TestEngineReachability(_Quiet):
    def test_off_by_default_and_static_findings_unchanged(self) -> None:
        plain = analyse(PAYMENT)
        self.assertEqual(plain.engine_unreachable, [])
        self.assertFalse(
            any("never entered" in f.message for f in plain.findings)
        )

    def test_inspect_adds_engine_only_finding(self) -> None:
        # `banned.permanent` is a static target whose compound parent has
        # no `initial`, so the engine can never settle there.
        path = FIX / "userModeration.json"
        facts = analyse(path, strict_config=False, engine_reachability=True)
        static_ids = set(facts.unreachable)
        self.assertTrue(set(facts.engine_unreachable).isdisjoint(static_ids))
        # never REMOVES a static warning
        self.assertEqual(facts.unreachable, analyse(path).unreachable)
        code, out = _run(["inspect", str(path), "--plain", "--no-events"])
        self.assertEqual(code, 0, out)
        if facts.engine_unreachable:
            self.assertIn("never entered by the engine", out)


if __name__ == "__main__":
    unittest.main()
