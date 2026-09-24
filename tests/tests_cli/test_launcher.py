"""Tests for the interactive launcher (`xsm` with no arguments), driven
by an injected key source so no pty is needed."""

from __future__ import annotations

import io
import json
import logging
import os
import pathlib
import tempfile
import unittest
from typing import Optional
from unittest import mock

import src.xstate_statemachine.cli.commands as cmds
from src.xstate_statemachine.cli.args import get_parser
from src.xstate_statemachine.cli.commands import launcher, reset_console
from src.xstate_statemachine.cli.ui import Capabilities, Console
from src.xstate_statemachine.cli.ui import keys as K

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYMENT = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)

CAPS = Capabilities(
    tty=True,
    color=True,
    truecolor=True,
    unicode=True,
    animate=False,
    width=100,
    height=30,
)


class _Launcher(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # isolate ~/.xsm/recent.json
        self._recent = mock.patch.object(
            launcher,
            "RECENT_PATH",
            pathlib.Path(self.tmp.name) / "recent.json",
        )
        self._recent.start()
        self.addCleanup(self._recent.stop)
        self.buf = io.StringIO()
        cmds._console = Console(CAPS, self.buf)
        self.addCleanup(reset_console)
        self.parser = get_parser()

    def out(self) -> str:
        import re

        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", self.buf.getvalue())


class TestMenu(_Launcher):
    def test_quit_immediately(self) -> None:
        launcher.run_launcher(self.parser, source=K.scripted("q"))
        out = self.out()
        self.assertIn("bye", out)
        self.assertIn("v0.", out)  # banner meta line drawn
        self.assertIn("What would you like to do?", out)

    def test_about_and_templates_then_quit(self) -> None:
        # About is item 8 (index 7); Templates is 7 (index 6); then quit
        launcher.run_launcher(
            self.parser, source=K.scripted("8 enter 7 enter q")
        )
        out = self.out()
        self.assertIn("Version:", out)
        self.assertIn("Available code generation templates", out)

    def test_validate_via_typed_glob(self) -> None:
        keys = f"4 enter enter {' '.join(_spell(str(PAYMENT)))} enter q"
        launcher.run_launcher(self.parser, source=K.scripted(keys))
        out = self.out()
        self.assertIn("All 1 file(s) are valid", out)
        # the file is now in recent
        self.assertEqual(
            [pathlib.Path(p).name for p in launcher.load_recent()],
            ["AdvancePayment.json"],
        )

    def test_inspect_from_recent(self) -> None:
        launcher.remember([str(PAYMENT)])
        # Inspect (2) → first recent entry
        launcher.run_launcher(
            self.parser, source=K.scripted("2 enter enter q")
        )
        self.assertIn("state tree", self.out())

    def test_command_failure_does_not_kill_the_launcher(self) -> None:
        bogus = str(pathlib.Path(self.tmp.name) / "nope.json")
        keys = f"2 enter enter {' '.join(_spell(bogus))} enter esc q"
        launcher.run_launcher(self.parser, source=K.scripted(keys))
        self.assertIn("not found", self.out())
        self.assertIn("bye", self.out())


class TestGenerateWizard(_Launcher):
    def test_full_wizard_writes_files(self) -> None:
        src = pathlib.Path(self.tmp.name) / "m.json"
        src.write_text(PAYMENT.read_text(encoding="utf-8"), encoding="utf-8")
        launcher.remember([str(src)])
        out_dir = pathlib.Path(self.tmp.name) / "out"
        # Generate (1) → recent file → template pythonic-class (3) →
        # companions: space on tests, enter → options: keep defaults, enter →
        # output dir typed → confirm yes → back at menu → quit
        keys = (
            "1 enter enter 3 enter space enter enter "
            + " ".join(_spell(str(out_dir), clear=len(str(src.parent))))
            + " enter y q"
        )
        launcher.run_launcher(self.parser, source=K.scripted(keys))
        out = self.out()
        self.assertIn("preview · pythonic-class", out)
        self.assertIn("Write these files?", out)
        names = sorted(p.name for p in out_dir.glob("*.py"))
        self.assertTrue(any(n.endswith("_logic.py") for n in names), names)
        self.assertTrue(any(n.startswith("test_") for n in names), names)

    def test_cancel_at_confirm_writes_nothing(self) -> None:
        launcher.remember([str(PAYMENT)])
        out_dir = pathlib.Path(self.tmp.name) / "out2"
        keys = (
            "1 enter enter enter enter enter "
            + " ".join(_spell(str(out_dir), clear=len(str(PAYMENT.parent))))
            + " enter n q"
        )
        launcher.run_launcher(self.parser, source=K.scripted(keys))
        self.assertIn("nothing written", self.out())
        self.assertFalse(out_dir.exists())


def _spell(text: str, *, clear: int = 0) -> list:
    """Key names that type *text* into a `prompt.text`, after *clear*
    backspaces to erase a default."""
    keys = ["backspace"] * clear
    for ch in text:
        keys.append("space" if ch == " " else ch)
    return keys


if __name__ == "__main__":
    unittest.main()
