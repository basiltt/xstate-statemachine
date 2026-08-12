# tests/tests_cli/test_code_quality.py
# -----------------------------------------------------------------------------
# 🏛️ Generated code must meet the same bar as hand-written code
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: a user should be able to drop generated modules into
# a linted, type-checked project without special-casing them. Code that trips
# the tooling is code the user cannot fix — editing it means losing the edit on
# the next regeneration.
#
# Each check is skipped rather than failed when its tool is absent: black,
# isort and mypy are development dependencies, not runtime ones.
# -----------------------------------------------------------------------------
"""Lint and type-check the output of every template."""

import itertools
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine.cli.__main__ import main

# 📝 Exercises the full feature surface: nesting, parallel, composite guards,
#    invoke with handlers, numeric AND named delays, always, tags and meta.
RICH_MACHINE: Dict[str, Any] = {
    "id": "shop",
    "initial": "cart",
    "context": {"items": 0, "total": 0.0},
    "on": {"RESET": "cart"},
    "states": {
        "cart": {
            "entry": "logCart",
            "exit": "saveCart",
            "on": {
                "CHECKOUT": {
                    "target": "pay",
                    "guard": {
                        "type": "and",
                        "params": {
                            "guards": [
                                "hasItems",
                                {
                                    "type": "not",
                                    "params": {"guards": ["isBanned"]},
                                },
                            ]
                        },
                    },
                    "actions": ["lock"],
                }
            },
        },
        "pay": {
            "invoke": {
                "src": "charge",
                "id": "chg",
                "onDone": {"target": "ship", "actions": "receipt"},
                "onError": "failed",
            },
            "after": {
                "30000": "failed",
                "RETRY": {"target": "pay", "guard": "canRetry"},
            },
            "tags": ["busy"],
        },
        "ship": {
            "always": [{"target": "done", "guard": "autoShip"}],
            "on": {"SHIPPED": "done"},
        },
        "failed": {"on": {"AGAIN": "pay"}, "meta": {"alert": True}},
        "done": {"type": "final"},
    },
}

TEMPLATES = (
    "pythonic-functional",
    "pythonic-builder",
    "pythonic-class",
    "class-json",
    "function-json",
)


def _tool_available(module: str) -> bool:
    """Whether *module* can be run as ``python -m module``."""
    return (
        subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True,
        ).returncode
        == 0
    )


class TestGeneratedCodeQuality(unittest.TestCase):
    """Every template, sync and async, must satisfy standard tooling."""

    generated: Dict[str, List[str]] = {}

    @classmethod
    def setUpClass(cls) -> None:
        """Generate every template/mode combination once."""
        logging.disable(logging.CRITICAL)
        cls._dir = tempfile.TemporaryDirectory()
        root = cls._dir.name
        source = os.path.join(root, "shop.json")
        with open(source, "w", encoding="utf-8") as handle:
            json.dump(RICH_MACHINE, handle)

        cls.generated = {}
        for template, async_mode in itertools.product(
            TEMPLATES, ("no", "yes")
        ):
            out = os.path.join(root, f"{template}_{async_mode}")
            argv = [
                "xsm",
                "generate-template",
                source,
                "--template",
                template,
                "-o",
                out,
                "--force",
                "-am",
                async_mode,
            ]
            saved, sys.argv = sys.argv, argv
            try:
                main()
            except SystemExit as exc:  # pragma: no cover — refusal is a bug
                raise AssertionError(
                    f"{template}/{async_mode} refused to generate: "
                    f"{exc.code}"
                ) from exc
            finally:
                sys.argv = saved

            cls.generated[f"{template}/{async_mode}"] = [
                os.path.join(out, name)
                for name in sorted(os.listdir(out))
                if name.endswith(".py")
            ]

    @classmethod
    def tearDownClass(cls) -> None:
        """Restore logging and remove the scratch directory."""
        logging.disable(logging.NOTSET)
        cls._dir.cleanup()

    def test_black_clean(self) -> None:
        """Output is already formatted; ``black --check`` finds nothing."""
        if not _tool_available("black"):  # pragma: no cover
            self.skipTest("black not installed")
        for label, paths in self.generated.items():
            for path in paths:
                with self.subTest(target=label, file=os.path.basename(path)):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "black",
                            "--check",
                            "-l",
                            "79",
                            path,
                        ],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_isort_clean(self) -> None:
        """Imports are grouped stdlib / third-party / first-party."""
        if not _tool_available("isort"):  # pragma: no cover
            self.skipTest("isort not installed")
        for label, paths in self.generated.items():
            for path in paths:
                with self.subTest(target=label, file=os.path.basename(path)):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "isort",
                            "--check-only",
                            "--profile",
                            "black",
                            "-l",
                            "79",
                            path,
                        ],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_lint_findings(self) -> None:
        """flake8 reports nothing the user would have to silence.

        The ``I00x`` codes are excluded: that plugin applies its own isort
        profile and flags this project's OWN hand-written source
        identically. Real isort is asserted separately above.
        """
        if not _tool_available("flake8"):  # pragma: no cover
            self.skipTest("flake8 not installed")
        for label, paths in self.generated.items():
            with self.subTest(target=label):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "flake8",
                        "--max-line-length",
                        "100",
                        "--extend-ignore=I001,I003,I004,I005",
                        *paths,
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.stdout.strip(), "")

    def test_mypy_strict_clean(self) -> None:
        """The logic module type-checks under ``mypy --strict``.

        Generated stubs are the user's contract with the machine. If they
        do not type-check, every project with a strict gate has to exclude
        them — which defeats the point of generating typed scaffolding.
        """
        if not _tool_available("mypy"):  # pragma: no cover
            self.skipTest("mypy not installed")
        for label, paths in self.generated.items():
            logic = [p for p in paths if p.endswith("_logic.py")]
            if not logic:  # pragma: no cover — every template emits one
                continue
            with self.subTest(target=label):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "mypy",
                        "--strict",
                        "--no-error-summary",
                        logic[0],
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
