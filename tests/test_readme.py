# tests/test_readme.py
# -----------------------------------------------------------------------------
# 🏛️ The README is the first code most people run
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: README examples are executed, not merely eyeballed.
#
# Earlier drafts of this project's documentation shipped four API errors that
# reading could not have caught — `initial_transition` returns a tuple, not a
# snapshot; `PureSnapshot` has no `.actions`; `MachineBuilder.transition()`
# takes positional arguments; `enqueue_actions` callbacks receive ONE mapping.
# Every one was found by running the snippet.
#
# A doc example that does not run is worse than no example: it costs the reader
# their trust, and they cannot tell whether the bug is in the docs or in their
# own code.
# -----------------------------------------------------------------------------
"""Every runnable Python block in README.md must import and execute."""

import ast
import logging
import os
import re
import subprocess
import sys
import textwrap
import unittest
from typing import List, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_README = os.path.join(_ROOT, "README.md")

# 📝 Blocks that are deliberately partial — a JSON fragment shown as Python, a
#    signature sketch, or a line that only makes sense inside a bigger file.
#    Each is listed by a substring that appears in it, so the reason a block is
#    skipped stays visible rather than becoming an opaque index.
_FRAGMENT_MARKERS = (
    "# …",  # elided body (unicode ellipsis)
    "# elsewhere",  # two disconnected snippets shown together
    "await ",  # async usage outside an event loop
    "async def",
    "statsd.",  # illustrative third-party integrations
    "sentry.",
    "analytics.",
    "audit_log.",
    "save_button",
    "show_spinner",
    'open("checkout.json")',  # reads a file the reader supplies
)

# 📝 Names a snippet may legitimately inherit from the paragraph above it.
#    A continuation block is still checked for SYNTAX; it is only exempt from
#    standalone EXECUTION, because requiring every snippet to restate its
#    whole machine would make the README unreadable.
_CONTINUATION_NAMES = ("config", "machine", "ed", "interp", "snapshot")

# 📝 A block that constructs a machine is self-contained by definition.
_SELF_CONTAINED = ("create_machine(", "build_machine(", "MachineBuilder(")


def _needs_context(source: str) -> bool:
    """Whether *source* uses a name the surrounding prose established."""
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover — the parse test owns this
        return False

    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    imported = {
        (alias.asname or alias.name).split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    if any(marker in source for marker in _SELF_CONTAINED):
        return False

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return any(
        name in used and name not in assigned and name not in imported
        for name in _CONTINUATION_NAMES
    )


def _python_blocks(text: str) -> List[Tuple[int, str]]:
    """Return ``(line_number, source)`` for every ```python block."""
    blocks: List[Tuple[int, str]] = []
    for match in re.finditer(r"```python\n(.*?)```", text, re.S):
        line_no = text[: match.start()].count("\n") + 1
        blocks.append((line_no, match.group(1)))
    return blocks


def _is_fragment(source: str) -> bool:
    """Whether a block is an illustrative fragment rather than a program."""
    return any(marker in source for marker in _FRAGMENT_MARKERS)


class TestReadmeBlocksParse(unittest.TestCase):
    """Fast gate: every block must at least be valid Python."""

    def test_all_blocks_are_syntactically_valid(self) -> None:
        """A block that cannot parse is a typo the reader will hit."""
        with open(_README, encoding="utf-8") as handle:
            text = handle.read()

        failures = []
        for line_no, source in _python_blocks(text):
            try:
                ast.parse(textwrap.dedent(source))
            except SyntaxError as exc:
                failures.append(f"README.md:{line_no}: {exc.msg}")

        self.assertEqual(failures, [], "\n".join(failures))

    def test_readme_has_substantial_examples(self) -> None:
        """Guard against the suite silently passing on an empty README."""
        with open(_README, encoding="utf-8") as handle:
            blocks = _python_blocks(handle.read())
        self.assertGreater(len(blocks), 25)


class TestReadmeBlocksRun(unittest.TestCase):
    """Execute every self-contained block in a fresh subprocess."""

    def test_runnable_blocks_execute(self) -> None:
        """A complete example must actually work against the real library."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        with open(_README, encoding="utf-8") as handle:
            text = handle.read()

        # 🔁 Blocks build on each other only within a section, so each is run
        #    standalone. That is the stricter reading: a snippet a user copies
        #    should work on its own or clearly say what it needs.
        preamble = (
            "import logging\n"
            "logging.disable(logging.CRITICAL)\n"
            "import sys\n"
            f"sys.path.insert(0, {_ROOT!r})\n"
            "import src.xstate_statemachine as _x\n"
            "sys.modules['xstate_statemachine'] = _x\n"
        )

        failures = []
        executed = 0
        for line_no, source in _python_blocks(text):
            body = textwrap.dedent(source)
            if _is_fragment(body) or _needs_context(body):
                continue
            if "import" not in body:
                continue  # 📝 attribute-only demos, covered by the parse test

            executed += 1
            result = subprocess.run(
                [sys.executable, "-c", preamble + body],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                tail = (result.stderr or "").strip().splitlines()
                failures.append(
                    f"README.md:{line_no}: {tail[-1] if tail else 'failed'}"
                )

        # 🔒 Floor, not a target. If a future edit makes fewer blocks
        #    self-contained, that is a README regression worth failing on:
        #    this test is only as strong as the number of blocks it runs.
        self.assertGreaterEqual(
            executed, 12, f"only {executed} README blocks were executed"
        )
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
