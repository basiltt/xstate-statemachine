# tests/tests_cli/test_check_mode.py
"""Tests for --check / --diff (N1).

🏛️ These make generated code safe to commit. Without them a checked-in
module drifts from its source JSON silently: someone edits the machine,
forgets to regenerate, and the repository holds code describing a machine
that no longer exists. A CI step running --check turns that into a
build failure.
"""

import json
import logging
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine.cli.__main__ import main

SIMPLE: Dict[str, Any] = {
    "id": "n",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


class CheckModeTestCase(unittest.TestCase):
    """Shared fixture: a temp dir holding one machine definition."""

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = self._tmp.name
        self.json_path = os.path.join(self.out, "n.json")
        with open(self.json_path, "w", encoding="utf-8") as handle:
            json.dump(SIMPLE, handle)

        self.logic = os.path.join(self.out, "n_logic.py")
        self.runner = os.path.join(self.out, "n_runner.py")

    def run_cli(self, *extra: str) -> int:
        """Invoke the CLI, returning its exit status."""
        argv: List[str] = [
            "xsm",
            "generate-template",
            self.json_path,
            "--template",
            "pythonic-functional",
            "-o",
            self.out,
            *extra,
        ]
        saved, sys.argv = sys.argv, argv
        try:
            main()
            return 0
        except SystemExit as exc:
            return exc.code or 0
        finally:
            sys.argv = saved


class TestCheckMode(CheckModeTestCase):
    """--check reports drift and never writes."""

    def test_reports_missing_files(self) -> None:
        """Nothing generated yet means out of date."""
        self.assertEqual(self.run_cli("--check"), 1)
        self.assertFalse(os.path.exists(self.logic))

    def test_passes_when_in_sync(self) -> None:
        """Freshly generated files satisfy --check."""
        self.assertEqual(self.run_cli("--force"), 0)
        self.assertEqual(self.run_cli("--check"), 0)

    def test_detects_hand_edits(self) -> None:
        """A modified file is reported as out of date."""
        self.run_cli("--force")
        with open(self.logic, "a", encoding="utf-8") as handle:
            handle.write("\n# hand edit\n")
        self.assertEqual(self.run_cli("--check"), 1)

    def test_detects_source_drift(self) -> None:
        """Editing the machine without regenerating fails the check."""
        self.run_cli("--force")
        changed = dict(SIMPLE)
        changed["states"] = {
            "a": {"on": {"GO": "b"}},
            "b": {"on": {"BACK": "a"}},
        }
        with open(self.json_path, "w", encoding="utf-8") as handle:
            json.dump(changed, handle)
        self.assertEqual(self.run_cli("--check"), 1)

    def test_never_writes(self) -> None:
        """--check must leave every file byte-identical."""
        self.run_cli("--force")
        with open(self.logic, encoding="utf-8") as handle:
            before = handle.read()
        with open(self.logic, "a", encoding="utf-8") as handle:
            handle.write("\n# stray\n")
        with open(self.logic, encoding="utf-8") as handle:
            edited = handle.read()

        self.run_cli("--check")

        with open(self.logic, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), edited)
        self.assertNotEqual(before, edited)

    def test_does_not_prompt_for_overwrite(self) -> None:
        """--check must never block on stdin.

        The overwrite prompt would hang CI -- the exact environment
        --check exists to serve. Closing stdin makes any prompt raise.
        """
        self.run_cli("--force")
        saved, sys.stdin = sys.stdin, None
        try:
            self.assertEqual(self.run_cli("--check"), 0)
        finally:
            sys.stdin = saved


class TestDiffMode(CheckModeTestCase):
    """--diff behaves like --check and shows what changed."""

    def test_diff_implies_check_and_exits_nonzero(self) -> None:
        """A drifted file exits 1 under --diff."""
        self.run_cli("--force")
        with open(self.logic, "a", encoding="utf-8") as handle:
            handle.write("\n# hand edit\n")
        self.assertEqual(self.run_cli("--diff"), 1)

    def test_diff_passes_when_in_sync(self) -> None:
        """No differences means exit 0."""
        self.run_cli("--force")
        self.assertEqual(self.run_cli("--diff"), 0)

    def test_diff_does_not_write(self) -> None:
        """--diff is read-only, like --check."""
        self.run_cli("--force")
        with open(self.logic, "a", encoding="utf-8") as handle:
            handle.write("\n# stray\n")
        with open(self.logic, encoding="utf-8") as handle:
            before = handle.read()

        self.run_cli("--diff")

        with open(self.logic, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
