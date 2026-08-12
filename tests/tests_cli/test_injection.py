# tests/tests_cli/test_injection.py
# -----------------------------------------------------------------------------
# 🏛️ A machine config is UNTRUSTED INPUT
# -----------------------------------------------------------------------------
# 🏛️ Threat model: a user runs `xsm generate-template machine.json` on a file
# they did not write — a Stately export, a colleague's branch, something from
# an issue tracker. The generator turns that JSON into Python source and then
# EXECUTES it in-process to verify fidelity.
#
# That makes every JSON string a potential code-injection channel. Values are
# emitted through ``repr()`` and are safe by construction, but DOCSTRINGS
# interpolate raw text — and a value containing a triple quote closes the
# docstring early, so everything after it is parsed as code.
#
# Reproduced before the fix: a machine id of
#
#     p\"\"\"\n    import os; os.system(...)\n    \"\"\"
#
# executed arbitrary code during `xsm generate-template`, with no --force, no
# prompt, and nothing written to disk yet.
# -----------------------------------------------------------------------------
"""Injection resistance for untrusted machine configs."""

import ast
import json
import logging
import os
import sys
import tempfile
import unittest
from typing import Any, Dict

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.naming import docstring_safe

TEMPLATES = (
    "pythonic-functional",
    "pythonic-builder",
    "pythonic-class",
    "class-json",
    "function-json",
)

# 📝 Indentation matters: the payload must be valid *inside* a function body,
#    or it fails on IndentationError for the wrong reason and the test would
#    pass without proving anything.
_BREAKOUT = (
    '"""\n    import pathlib; pathlib.Path({!r}).write_text("rce")\n    """'
)


class TestDocstringSafe(unittest.TestCase):
    """The sanitiser itself."""

    def test_strips_triple_quotes(self) -> None:
        """A docstring terminator must not survive."""
        self.assertNotIn('"', docstring_safe('a"""b'))

    def test_strips_newlines_and_backslashes(self) -> None:
        """Neither can start a new statement or an escape."""
        result = docstring_safe("a\nb\\c\r\nd")
        for char in ("\n", "\r", "\\"):
            self.assertNotIn(char, result)

    def test_never_returns_empty(self) -> None:
        """An all-unsafe name still needs a usable label."""
        self.assertTrue(docstring_safe('"""').strip())
        self.assertTrue(docstring_safe("").strip())

    def test_truncates_absurd_input(self) -> None:
        """A megabyte-long id should not become a megabyte-long docstring."""
        self.assertLessEqual(len(docstring_safe("x" * 10_000)), 121)

    def test_output_is_always_docstring_safe(self) -> None:
        """Whatever goes in, the result can be embedded verbatim."""
        hostile = [
            'a"""b',
            "a\\\nb",
            '"""',
            '\\"""',
            "x" * 500,
            '🎉\n"""',
            'end"""\nimport os',
        ]
        for value in hostile:
            with self.subTest(value=value[:24]):
                source = (
                    f'def f():\n    """{docstring_safe(value)}"""\n    pass\n'
                )
                tree = ast.parse(source)
                # 🔍 One function, one docstring, no smuggled statements.
                self.assertEqual(len(tree.body), 1)
                self.assertEqual(len(tree.body[0].body), 2)


class TestNoCodeExecutionDuringGeneration(unittest.TestCase):
    """Generating from a hostile config must not run its payload."""

    def _generate(self, config: Dict[str, Any], out_root: str) -> None:
        """Run the CLI for every template, ignoring refusals."""
        source = os.path.join(out_root, "m.json")
        with open(source, "w", encoding="utf-8") as handle:
            json.dump(config, handle)

        for template in TEMPLATES:
            argv = [
                "xsm",
                "generate-template",
                source,
                "--template",
                template,
                "-o",
                os.path.join(out_root, template),
                "--force",
            ]
            saved, sys.argv = sys.argv, argv
            try:
                main()
            except SystemExit:
                pass  # 📝 A refusal is a fine outcome; execution is not.
            except Exception:  # noqa: BLE001 — a crash is also acceptable
                pass
            finally:
                sys.argv = saved

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.canary = os.path.join(self.root, "OWNED.txt")

    def test_machine_id_cannot_execute_code(self) -> None:
        """The machine id reaches build() and class docstrings."""
        self._generate(
            {
                "id": "p" + _BREAKOUT.format(self.canary),
                "initial": "a",
                "states": {"a": {}},
            },
            self.root,
        )
        self.assertFalse(
            os.path.exists(self.canary),
            "machine id achieved code execution during generation",
        )

    def test_action_name_cannot_execute_code(self) -> None:
        """Action names reach every generated stub's docstring."""
        self._generate(
            {
                "id": "ok",
                "initial": "a",
                "states": {
                    "a": {"entry": "e" + _BREAKOUT.format(self.canary)}
                },
            },
            self.root,
        )
        self.assertFalse(
            os.path.exists(self.canary),
            "action name achieved code execution during generation",
        )

    def test_guard_and_service_names_cannot_execute_code(self) -> None:
        """Guards and services are stubbed with docstrings too."""
        payload = _BREAKOUT.format(self.canary)
        self._generate(
            {
                "id": "ok",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"GO": {"target": "b", "guard": "g" + payload}},
                        "invoke": {"src": "s" + payload, "onDone": "b"},
                    },
                    "b": {},
                },
            },
            self.root,
        )
        self.assertFalse(
            os.path.exists(self.canary),
            "guard/service name achieved code execution during generation",
        )

    def test_state_name_cannot_execute_code(self) -> None:
        """State names become identifiers and appear in output."""
        self._generate(
            {
                "id": "ok",
                "initial": "a",
                "states": {
                    "a": {"on": {"GO": "b"}},
                    "b" + _BREAKOUT.format(self.canary): {},
                },
            },
            self.root,
        )
        self.assertFalse(
            os.path.exists(self.canary),
            "state name achieved code execution during generation",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
