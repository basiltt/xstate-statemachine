# tests/tests_cli/test_args.py
"""Tests for CLI argument parsing -- --template flag and deprecation."""

import logging
import unittest
import warnings
from unittest.mock import patch

logger = logging.getLogger(__name__)


class TestTemplateFlag(unittest.TestCase):
    """Tests for the new --template / -t flag."""

    def test_template_flag_accepted(self) -> None:
        """--template with valid value is parsed correctly."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json", "--template", "pythonic-class"]
        )
        self.assertEqual(args.template, "pythonic-class")

    def test_template_short_flag(self) -> None:
        """-t short flag works for --template."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json", "-t", "pythonic-builder"]
        )
        self.assertEqual(args.template, "pythonic-builder")

    def test_template_default_is_none(self) -> None:
        """--template defaults to None when not provided."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(["generate-template", "f.json"])
        self.assertIsNone(args.template)

    def test_template_all_valid_choices(self) -> None:
        """All 5 template choices are accepted."""
        from src.xstate_statemachine.cli.args import get_parser

        valid = [
            "class-json",
            "function-json",
            "pythonic-class",
            "pythonic-builder",
            "pythonic-functional",
        ]
        parser = get_parser()
        for t in valid:
            args = parser.parse_args(["generate-template", "f.json", "-t", t])
            self.assertEqual(args.template, t)

    def test_template_invalid_choice_errors(self) -> None:
        """Invalid --template value causes a parser error."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["generate-template", "f.json", "-t", "invalid"])

    def test_async_mode_default_is_none(self) -> None:
        """--async-mode defaults to None (resolved later)."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(["generate-template", "f.json"])
        self.assertIsNone(args.async_mode)


class TestStyleDeprecation(unittest.TestCase):
    """Tests for --style backward compat with deprecation."""

    def test_resolve_template_from_style_class(self) -> None:
        """--style class resolves to class-json with warning."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template(style="class", template=None)
            self.assertEqual(result, "class-json")
            self.assertEqual(len(w), 1)
            self.assertIn("deprecated", str(w[0].message).lower())
            self.assertTrue(issubclass(w[0].category, DeprecationWarning))

    def test_resolve_template_from_style_function(self) -> None:
        """--style function resolves to function-json."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template(style="function", template=None)
            self.assertEqual(result, "function-json")
            self.assertEqual(len(w), 1)

    def test_resolve_template_explicit_template_wins(
        self,
    ) -> None:
        """--template takes precedence when --style not set."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        result = resolve_template(style=None, template="pythonic-class")
        self.assertEqual(result, "pythonic-class")

    def test_resolve_template_both_raises_error(self) -> None:
        """Using both --style and --template raises ValueError."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with self.assertRaises(ValueError) as cm:
            resolve_template(style="class", template="pythonic-class")
        self.assertIn("Cannot use both", str(cm.exception))

    def test_resolve_template_neither_defaults(self) -> None:
        """Neither --style nor --template defaults to class-json."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        result = resolve_template(style=None, template=None)
        self.assertEqual(result, "class-json")


class TestAsyncModeResolution(unittest.TestCase):
    """Tests for template-aware async mode defaults."""

    def test_resolve_async_explicit_yes(self) -> None:
        """Explicit --async-mode yes overrides template."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode("yes", "pythonic-class")
        self.assertTrue(result)

    def test_resolve_async_explicit_no(self) -> None:
        """Explicit --async-mode no overrides template."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode("no", "class-json")
        self.assertFalse(result)

    def test_resolve_async_json_template_defaults_true(
        self,
    ) -> None:
        """JSON templates default to async when not specified."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode(None, "class-json")
        self.assertTrue(result)
        result2 = resolve_async_mode(None, "function-json")
        self.assertTrue(result2)

    def test_resolve_async_pythonic_defaults_false(
        self,
    ) -> None:
        """Pythonic templates default to sync."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        for t in [
            "pythonic-class",
            "pythonic-builder",
            "pythonic-functional",
        ]:
            result = resolve_async_mode(None, t)
            self.assertFalse(result)
