# src/xstate_statemachine/cli/postprocess.py
# -----------------------------------------------------------------------------
# 🏛️ Post-emit polish: provenance, import hygiene, formatting
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: emitters produce *correct* code; this module makes
# it *presentable*. Keeping the two apart means an emitter never has to reason
# about line length, and a formatting change can never alter machine fidelity.
#
# Ordering matters and is deliberate:
#
#   1. prune unused imports  — must precede formatting, or black would
#                              carefully format lines we are about to delete
#   2. prepend provenance    — a reader's first question is "where did this
#                              come from and how do I regenerate it?"
#   3. run black             — last, so everything above is normalised
#
# Formatting is best-effort by design: black is a development dependency, not
# a runtime one. If it is unavailable the code is still valid and still
# faithful — it is simply not reformatted.
# -----------------------------------------------------------------------------
"""Post-processing for generated modules."""

from __future__ import annotations

import ast
import logging
import subprocess
import sys
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# 📝 Line length used across this project (see pyproject.toml [tool.black]).
_LINE_LENGTH = 79


def prune_unused_imports(code: str) -> str:
    """Remove imported names the module never references.

    Generated modules import a fixed set of helpers regardless of whether a
    particular machine needs them, so a simple machine arrives with
    ``Optional``, ``Union`` and ``Interpreter`` unused — 14 flake8 findings
    in the v0.7.0 audit. Anyone who lints their tree sees noise they did not
    write and cannot fix without editing generated code.

    Args:
        code: The generated module source.

    Returns:
        The source with unused imported names removed. Returned unchanged
        if it cannot be parsed.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:  # pragma: no cover — verification catches this
        return code

    used = _referenced_names(tree)
    lines = code.splitlines(keepends=True)
    drop_lines: Set[int] = set()
    edits: List[tuple] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        # 🛡️ Never touch star or relative imports: what they bind is not
        #    statically knowable, so "unused" cannot be established.
        if any(alias.name == "*" for alias in node.names):
            continue

        kept = [a for a in node.names if _binding(a) in used]
        if len(kept) == len(node.names):
            continue
        if not kept:
            for i in range(node.lineno - 1, (node.end_lineno or node.lineno)):
                drop_lines.add(i)
            continue
        edits.append((node, kept))

    for node, kept in edits:
        replacement = _render_import(node, kept)
        start = node.lineno - 1
        end = node.end_lineno or node.lineno
        lines[start] = replacement
        for i in range(start + 1, end):
            drop_lines.add(i)

    return "".join(
        line for i, line in enumerate(lines) if i not in drop_lines
    )


def _binding(alias: ast.alias) -> str:
    """The name an import alias actually binds in the module namespace."""
    if alias.asname:
        return alias.asname
    # 📝 `import a.b.c` binds `a`, not `a.b.c`.
    return alias.name.split(".")[0]


def _referenced_names(tree: ast.AST) -> Set[str]:
    """Every identifier the module mentions outside of import statements."""
    used: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                used.add(base.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # 📝 A string annotation such as "Optional[int]" is a real use.
            for token in _identifiers_in(node.value):
                used.add(token)
    return used


def _identifiers_in(text: str) -> Set[str]:
    """Best-effort identifier extraction from a string annotation."""
    if not text or len(text) > 200:
        return set()
    try:
        parsed = ast.parse(text, mode="eval")
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(parsed) if isinstance(n, ast.Name)}


def _render_import(node: ast.AST, kept: List[ast.alias]) -> str:
    """Re-render an import statement keeping only *kept* aliases."""
    names = ", ".join(
        a.name if not a.asname else f"{a.name} as {a.asname}" for a in kept
    )
    if isinstance(node, ast.ImportFrom):
        module = "." * (node.level or 0) + (node.module or "")
        return f"from {module} import {names}\n"
    return f"import {names}\n"


def build_provenance_header(
    *,
    source_files: List[str],
    template: str,
    version: str,
    command: str,
) -> str:
    """Build the module docstring identifying how this file was produced.

    A reader's first two questions about generated code are "where did this
    come from?" and "how do I regenerate it?". Answering both in the file
    removes the guesswork — and the regeneration command makes the file
    reproducible by anyone, not just whoever ran the CLI.
    """
    sources = ", ".join(source_files) if source_files else "unknown"
    return (
        '"""Generated state machine logic — DO NOT EDIT BY HAND.\n'
        "\n"
        f"Source:    {sources}\n"
        f"Template:  {template}\n"
        f"Generator: xstate-statemachine {version}\n"
        "\n"
        "Regenerate with::\n"
        "\n"
        f"    {command}\n"
        "\n"
        "Implement your logic in the stubs below; the machine structure\n"
        "above is derived from the source JSON and will be overwritten.\n"
        '"""\n'
    )


def apply_provenance(code: str, header: str) -> str:
    """Prepend *header*, replacing any existing module docstring."""
    try:
        tree = ast.parse(code)
    except SyntaxError:  # pragma: no cover — verification catches this
        return header + code

    body = tree.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        lines = code.splitlines(keepends=True)
        end = body[0].end_lineno or 1
        return header + "".join(lines[end:]).lstrip("\n")

    return header + "\n" + code.lstrip("\n")


def format_source(code: str, *, line_length: int = _LINE_LENGTH) -> str:
    """Format *code* with black, returning it unchanged if black is absent.

    🛡️ Best-effort by design. black is a development dependency; a user who
    installed only the runtime must still be able to generate code. An
    unformatted module is a cosmetic problem, a failed generation is not.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "black",
                "--quiet",
                f"--line-length={line_length}",
                "-",
            ],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("black unavailable (%s); emitting unformatted", exc)
        return code

    if result.returncode != 0 or not result.stdout:
        logger.debug(
            "black declined to format (exit %s); emitting unformatted",
            result.returncode,
        )
        return code
    return result.stdout


def polish(
    code: str,
    *,
    header: Optional[str] = None,
    line_length: int = _LINE_LENGTH,
) -> str:
    """Run the full post-emit pipeline over generated *code*.

    Order is deliberate: prune imports before formatting (so black does not
    format lines about to be deleted), then add provenance, then format.
    """
    code = prune_unused_imports(code)
    if header:
        code = apply_provenance(code, header)
    return format_source(code, line_length=line_length)
