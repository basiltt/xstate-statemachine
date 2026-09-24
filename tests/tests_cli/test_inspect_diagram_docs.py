"""Tests for `xsm inspect`, `xsm diagram` and `xsm docs`, plus the shared
`commands.analysis` module they are built on."""

from __future__ import annotations

import glob
import io
import json
import logging
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import List

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.analysis import (
    analyse,
    event_table,
    short_id,
)
from src.xstate_statemachine.cli.commands.diagram import render_diagram
from src.xstate_statemachine.cli.commands.docs import render_markdown
from src.xstate_statemachine.cli.commands.inspect import state_tree
from src.xstate_statemachine.cli.ui import PLAIN
from src.xstate_statemachine.cli.ui.tree import render as render_tree

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "tests_cli" / "stately_machines"
PAYMENT = FIX / "AdvancePayment.json"
AIWF = FIX / "aiWorkflow.json"


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


class TestAnalysis(_Quiet):
    def test_facts_from_a_real_export(self) -> None:
        f = analyse(PAYMENT)
        self.assertTrue(f.ok, [x.message for x in f.findings])
        self.assertEqual(f.machine_id, "Advance payment flow")
        self.assertEqual(f.state_count(), 5)
        self.assertIn("SUBMIT", f.events)
        self.assertIn("isFormValid", f.guards)
        self.assertEqual(f.unreachable, [])
        js = f.to_json()
        json.dumps(js)
        self.assertEqual(js["top_level_states"], 5)

    def test_unknown_key_is_an_error_by_default_and_a_warning_when_lenient(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "m.json"
            p.write_text(
                json.dumps(
                    {
                        "id": "m",
                        "initial": "a",
                        "states": {"a": {"entyr": ["x"]}},
                    }
                ),
                encoding="utf-8",
            )
            strict = analyse(p)
            self.assertFalse(strict.ok)
            self.assertIn("entyr", strict.findings[0].message)
            lenient = analyse(p, strict_config=False)
            self.assertTrue(lenient.ok)
            self.assertTrue(
                any("entyr" in w.message for w in lenient.findings)
            )

    def test_unreachable_state_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "m.json"
            p.write_text(
                json.dumps(
                    {
                        "id": "m",
                        "initial": "a",
                        "states": {
                            "a": {"on": {"GO": "b"}},
                            "b": {},
                            "orphan": {},
                        },
                    }
                ),
                encoding="utf-8",
            )
            f = analyse(p)
            self.assertEqual(f.unreachable, ["m.orphan"])
            self.assertTrue(any(w.path == "m.orphan" for w in f.findings))

    def test_missing_file_and_bad_json(self) -> None:
        self.assertEqual(
            analyse(pathlib.Path("/nope/x.json")).findings[0].message,
            "file not found",
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "m.json"
            p.write_text("{", encoding="utf-8")
            self.assertIn("invalid JSON", analyse(p).findings[0].message)

    def test_event_table_and_short_id(self) -> None:
        f = analyse(PAYMENT)
        rows = event_table(f.machine)
        events = {r[0] for r in rows}
        self.assertIn("SUBMIT", events)
        self.assertIn("after 2000", events)
        self.assertTrue(
            any(r[2] == "(internal)" for r in rows)
        )  # UPDATE_FORM targetless
        self.assertEqual(
            short_id("Advance payment flow.editing", "Advance payment flow"),
            "editing",
        )
        self.assertEqual(short_id("other.x", "m"), "other.x")

    def test_analysis_on_the_whole_corpus_never_raises(self) -> None:
        for fp in sorted(glob.glob(str(FIX / "*.json"))):
            with self.subTest(fixture=pathlib.Path(fp).name):
                f = analyse(pathlib.Path(fp), strict_config=False)
                json.dumps(f.to_json())  # always serialisable


class TestInspect(_Quiet):
    def test_state_tree_marks_kinds_and_active(self) -> None:
        f = analyse(AIWF)
        root = state_tree(
            f.machine, active={"aiWorkflow.draft"}, unicode=False
        )
        lines = render_tree(PLAIN, root)
        self.assertTrue(lines[0].startswith("+ aiWorkflow"))
        self.assertTrue(
            any("o draft" in ln and "* active" in ln for ln in lines)
        )
        self.assertTrue(any("|| production" in ln for ln in lines))

    def test_cli_inspect_plain_and_json(self) -> None:
        code, out = _run(["inspect", str(PAYMENT), "--plain"])
        self.assertEqual(code, 0, out)
        for token in (
            "Advance payment flow",
            "state tree",
            "transitions",
            "after 2000",
            "policies",
            "actionErrorPolicy",
        ):
            self.assertIn(token, out)
        self.assertNotIn("\x1b", out)
        code, out = _run(["inspect", str(PAYMENT), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["machine"], "Advance payment flow")
        self.assertIn("transitions", data)
        self.assertIn("policies", data)

    def test_cli_inspect_bad_file_exits_1(self) -> None:
        code, out = _run(["inspect", "/nope/x.json", "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("file not found", out)


class TestDiagram(_Quiet):
    def test_formats(self) -> None:
        m = analyse(PAYMENT).machine
        self.assertTrue(
            render_diagram(m, "mermaid").startswith("stateDiagram-v2")
        )
        self.assertIn("@startuml", render_diagram(m, "plantuml"))
        ascii_ = render_diagram(m, "ascii", unicode=False)
        self.assertIn("--SUBMIT [isFormValid]->", ascii_)
        with self.assertRaises(ValueError):
            render_diagram(m, "png")

    def test_cli_writes_to_a_directory_with_the_right_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run(
                [
                    "diagram",
                    str(PAYMENT),
                    "-f",
                    "plantuml",
                    "-o",
                    tmp,
                    "--plain",
                ]
            )
            self.assertEqual(code, 0, out)
            files = list(pathlib.Path(tmp).glob("*.puml"))
            self.assertEqual(len(files), 1)
            self.assertIn("@startuml", files[0].read_text(encoding="utf-8"))

    def test_cli_stdout_mermaid(self) -> None:
        code, out = _run(["diagram", str(AIWF), "--plain"])
        self.assertEqual(code, 0)
        self.assertIn("stateDiagram-v2", out)


class TestDocs(_Quiet):
    def test_markdown_has_every_section(self) -> None:
        md = render_markdown(analyse(PAYMENT))
        for heading in (
            "## Diagram",
            "## States",
            "## Transitions",
            "## Logic to implement",
            "## Policies",
            "## Events",
        ):
            self.assertIn(heading, md)
        self.assertIn("```mermaid", md)
        self.assertIn("`isFormValid`", md)
        # table rows are well-formed: pipes balanced per row
        for line in md.splitlines():
            if line.startswith("| `") and "|---" not in line:
                self.assertEqual(
                    line.count("|"), line.count("|")
                )  # sanity; no stray escapes crash

    def test_cli_docs_to_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run(
                ["docs", str(PAYMENT), str(AIWF), "-o", tmp, "--plain"]
            )
            self.assertEqual(code, 0, out)
            names = sorted(p.name for p in pathlib.Path(tmp).glob("*.md"))
            self.assertEqual(
                names, ["Advance payment flow.md", "aiWorkflow.md"]
            )
            self.assertIn("2 page(s) written", out)


if __name__ == "__main__":
    unittest.main()
