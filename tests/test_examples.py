# tests/test_examples.py
# -----------------------------------------------------------------------------
# 🏛️ Shipped examples must actually run for the people who receive them
# -----------------------------------------------------------------------------
# 🏛️ `examples/` is included in the sdist, so these files reach every user who
# installs the package. They are also the first code most people read.
#
# Before v0.7.0 all 71 example modules imported `src.xstate_statemachine`, the
# SOURCE-CHECKOUT path. That resolves when running from a clone of the repo and
# fails with ModuleNotFoundError for anyone who pip-installed — so every shipped
# example was broken for its actual audience, and nothing caught it because the
# test suite never executed them.
# -----------------------------------------------------------------------------
"""Every example runner must execute successfully."""

import glob
import os
import subprocess
import sys
import unittest
from typing import List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")

# 📝 Generous: several examples simulate timers and sleep between events.
_TIMEOUT_SECONDS = 60


def _runners() -> List[str]:
    """Every runnable example entry point."""
    return sorted(
        glob.glob(os.path.join(_EXAMPLES, "**", "*_runner.py"), recursive=True)
    )


class TestExampleImports(unittest.TestCase):
    """Static checks — fast, and they localise the failure precisely."""

    def test_no_source_checkout_imports(self) -> None:
        """Examples must import the INSTALLED package, not `src.*`.

        `from src.xstate_statemachine import ...` works only from a clone.
        Users who pip-install get ModuleNotFoundError.
        """
        offenders = []
        for path in glob.glob(
            os.path.join(_EXAMPLES, "**", "*.py"), recursive=True
        ):
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if "src.xstate_statemachine" in content:
                offenders.append(os.path.relpath(path, _ROOT))
        self.assertEqual(offenders, [])

    def test_no_repo_rooted_package_imports(self) -> None:
        """`from examples.a.b.c import ...` needs the repo root on sys.path.

        Sibling modules should be imported by name after adding the
        example's own directory, which works regardless of install method.
        """
        offenders = []
        for path in glob.glob(
            os.path.join(_EXAMPLES, "**", "*.py"), recursive=True
        ):
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("from examples.") or line.startswith(
                        "import examples."
                    ):
                        offenders.append(os.path.relpath(path, _ROOT))
                        break
        self.assertEqual(offenders, [])


class TestExamplesRun(unittest.TestCase):
    """Execute every runner exactly as a user would."""

    def test_every_runner_exits_zero(self) -> None:
        """Each example runs to completion from its own directory."""
        runners = _runners()
        self.assertGreater(runners, [], "no example runners found")

        failures = []
        for path in runners:
            name = os.path.relpath(path, _ROOT)
            with self.subTest(example=name):
                try:
                    result = subprocess.run(
                        [sys.executable, os.path.basename(path)],
                        cwd=os.path.dirname(path),
                        capture_output=True,
                        text=True,
                        timeout=_TIMEOUT_SECONDS,
                        encoding="utf-8",
                        errors="replace",
                    )
                except subprocess.TimeoutExpired:  # pragma: no cover
                    failures.append(f"{name}: timed out")
                    continue

                # 📝 Judge by exit status only. These examples log to stderr
                #    at INFO level by design, so treating stderr output as
                #    failure would flag every one of them.
                if result.returncode != 0:
                    tail = (result.stderr or "").strip().splitlines()
                    failures.append(
                        f"{name}: exit {result.returncode} — "
                        f"{tail[-1] if tail else 'no output'}"
                    )

        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
