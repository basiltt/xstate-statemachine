"""Tests for the CLI's auxiliary subcommands and `main()` dispatch.

`generate-template` is covered exhaustively elsewhere in this package. The
three small subcommands -- `list-templates`, `validate`, `info` -- and the
`main()` dispatcher had no tests, so a regression there (a renamed template,
`validate` accepting a broken file, a subcommand silently falling through to
`print_help`) would ship unnoticed.
"""

from __future__ import annotations

import io
import json
import logging
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import List

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.strategies import STRATEGY_REGISTRY


def _run(argv: List[str]) -> tuple:
    """Invoke `main()` with *argv*; return (exit_code, stdout)."""
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
    return code, buf.getvalue()


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestListTemplates(_Quiet):
    def test_lists_every_registered_template(self) -> None:
        for alias in ("list-templates", "lt"):
            with self.subTest(alias=alias):
                code, out = _run([alias])
                self.assertEqual(0, code)
                for name in STRATEGY_REGISTRY:
                    self.assertIn(name, out, f"{name} missing from {alias}")

    def test_mentions_how_to_use_a_template(self) -> None:
        _, out = _run(["lt"])
        self.assertIn("--template", out)


class TestInfo(_Quiet):
    def test_reports_version_python_and_links(self) -> None:
        from src.xstate_statemachine import __version__

        code, out = _run(["info"])
        self.assertEqual(0, code)
        self.assertIn(__version__, out)
        self.assertIn("Python:", out)
        self.assertIn("basiltt.github.io/xstate-statemachine", out)
        self.assertIn("pypi.org/project/xstate-statemachine", out)

    def test_names_the_launcher_free_invocation(self) -> None:
        """Windows Application Control policies block pip's `xsm.exe`
        stub; `info` must tell the user the `python -m` spelling."""
        code, out = _run(["info"])
        self.assertEqual(0, code)
        self.assertIn("-m xstate_statemachine", out)
        code, out = _run(["info", "--json"])
        self.assertIn(
            "-m xstate_statemachine", json.loads(out)["module_invocation"]
        )


class TestModuleEntryPoints(unittest.TestCase):
    """`python -m xstate_statemachine` and `python -m xstate_statemachine.cli`
    are the documented way around a blocked `xsm.exe`; both must reach the
    same `main()` with the same `prog` name in the usage line."""

    def _run_module(self, module: str, *args: str):
        import os
        import subprocess

        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, "-m", module, *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    def test_top_level_package_is_runnable(self) -> None:
        from src.xstate_statemachine import __version__

        r = self._run_module("xstate_statemachine", "--version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"xsm {__version__}", r.stdout)

    def test_both_spellings_share_prog_and_dispatch(self) -> None:
        for module in ("xstate_statemachine", "xstate_statemachine.cli"):
            r = self._run_module(module, "list-templates", "--plain")
            self.assertEqual(r.returncode, 0, (module, r.stderr))
            self.assertIn("pythonic-class", r.stdout, module)
            r = self._run_module(module, "--help")
            self.assertTrue(
                r.stdout.startswith("usage: xsm "), (module, r.stdout[:40])
            )


class TestValidate(_Quiet):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _write(self, name: str, content: object) -> str:
        p = self.dir / name
        p.write_text(
            content if isinstance(content, str) else json.dumps(content),
            encoding="utf-8",
        )
        return str(p)

    def test_valid_file_reports_summary_and_exit_0(self) -> None:
        path = self._write(
            "ok.json",
            {
                "id": "light",
                "initial": "green",
                "states": {
                    "green": {
                        "on": {
                            "T": {
                                "target": "red",
                                "guard": "isSafe",
                                "actions": ["recordEntry"],
                            }
                        }
                    },
                    "red": {"invoke": {"src": "fetch"}},
                },
            },
        )
        for alias in ("validate", "val"):
            with self.subTest(alias=alias):
                code, out = _run([alias, path])
                self.assertEqual(0, code)
                self.assertIn("ok", out)
                self.assertIn("Machine: light", out)
                self.assertIn("States:  2", out)
                self.assertIn("Actions: recordEntry", out)
                self.assertIn("Guards:  isSafe", out)
                self.assertIn("Services: fetch", out)
                self.assertIn("All 1 file(s) are valid", out)

    def test_structural_issues_are_listed_and_exit_1(self) -> None:
        path = self._write(
            "bad.json",
            {"initial": "nope", "states": {"a": {}}},  # no id; bad initial
        )
        code, out = _run(["validate", path])
        self.assertEqual(1, code)
        self.assertIn("missing 'id' field", out)
        self.assertIn("initial state 'nope' not found", out)
        self.assertIn("1 file(s) had errors", out)

    def test_states_must_be_an_object(self) -> None:
        path = self._write(
            "states.json", {"id": "m", "initial": "a", "states": ["a"]}
        )
        code, out = _run(["validate", path])
        self.assertEqual(1, code)
        self.assertIn("'states' must be an object", out)

    def test_parallel_root_needs_no_initial(self) -> None:
        path = self._write(
            "par.json",
            {"id": "p", "type": "parallel", "states": {"a": {}, "b": {}}},
        )
        code, out = _run(["validate", path])
        self.assertEqual(0, code)
        self.assertNotIn("missing 'initial'", out)

    def test_non_object_root_missing_file_and_invalid_json(self) -> None:
        arr = self._write("arr.json", [1, 2])
        broken = self._write("broken.json", "{not json")
        missing = str(self.dir / "does-not-exist.json")
        code, out = _run(["validate", arr, broken, missing])
        self.assertEqual(1, code)
        self.assertIn("root must be a JSON object", out)
        self.assertIn("invalid JSON", out)
        self.assertIn("file not found", out)
        self.assertIn("3 file(s) had errors", out)


class TestMainDispatch(_Quiet):
    def test_no_subcommand_is_a_usage_error(self) -> None:
        # argparse's required subparser: exit code 2, usage on stderr.
        code, _ = _run([])
        self.assertEqual(2, code)

    def test_unknown_subcommand_is_a_usage_error(self) -> None:
        code, _ = _run(["frobnicate"])
        self.assertEqual(2, code)

    def test_ctrl_c_exits_130_without_a_traceback(self) -> None:
        """The raw-mode key reader raises KeyboardInterrupt on Ctrl+C; the
        entry point must turn that into a quiet exit, not a traceback."""
        from unittest import mock

        import src.xstate_statemachine.cli.__main__ as entry

        err = io.StringIO()
        with (
            mock.patch.object(
                entry, "_dispatch", side_effect=KeyboardInterrupt
            ),
            mock.patch.object(sys, "stderr", err),
        ):
            with self.assertRaises(SystemExit) as cm:
                entry.main()
        self.assertEqual(cm.exception.code, entry.EXIT_INTERRUPTED)
        self.assertIn("interrupted", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
