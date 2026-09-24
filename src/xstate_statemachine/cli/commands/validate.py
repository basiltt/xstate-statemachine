# src/xstate_statemachine/cli/commands/validate.py
# -----------------------------------------------------------------------------
# ✅ `xsm validate` -- build each file with the real library and report
# -----------------------------------------------------------------------------
"""The `validate` subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..ui import Column, Table
from . import get_console
from .analysis import Facts, analyse


def _render_one(facts: Facts) -> None:
    c = get_console()
    name = c.style(str(facts.path), "path")
    errors = [f for f in facts.findings if f.severity == "error"]
    warnings = [f for f in facts.findings if f.severity == "warning"]
    if errors:
        # 📌 "x <file> -- N issue(s):" is pinned by tests/tests_cli.
        c.print(f"  {c.style('x', 'err')} {name} -- {len(errors)} issue(s):")
        for f in errors:
            where = f" {c.style('@ ' + f.path, 'muted')}" if f.path else ""
            c.print(f"      - {f.message}{where}")
        return
    c.print(f"  {c.style('ok', 'ok')} {name}")
    # 📌 The "Machine:" / "States:" / "Actions:" rows are pinned by tests.
    nested = facts.state_count(all_levels=True)
    top = facts.state_count()
    states = f"{top}" + (f"  ({nested} incl. nested)" if nested != top else "")
    rows = [
        ("Machine:", facts.machine_id),
        ("States: ", states),
        ("Events: ", str(len(facts.events))),
    ]
    if facts.actions:
        rows.append(("Actions:", ", ".join(sorted(facts.actions))))
    if facts.guards:
        rows.append(("Guards: ", ", ".join(sorted(facts.guards))))
    if facts.services:
        rows.append(("Services:", ", ".join(sorted(facts.services))))
    if facts.delays:
        rows.append(("Delays: ", ", ".join(sorted(facts.delays))))
    for k, v in rows:
        c.print(f"      {c.style(k, 'key')} {v}")
    for w in warnings:
        where = f" {c.style(w.path, 'muted')}" if w.path else ""
        c.print(f"      {c.style('!', 'warn')} {w.message}{where}")


def run_validate(
    paths: List[str], *, as_json: bool = False, lenient: bool = False
) -> None:
    """Validate every file; exit 1 if any has an error.

    Args:
        paths: JSON files to check.
        as_json: Emit one JSON array instead of the rendered report.
        lenient: Treat unknown config keys as warnings (the library's
            default) rather than errors (`strict_config`, the CLI default).
    """
    c = get_console()
    results = [analyse(Path(p), strict_config=not lenient) for p in paths]
    if as_json:
        c.print(json.dumps([f.to_json() for f in results], indent=2))
        if any(not f.ok for f in results):
            raise SystemExit(1)
        return

    c.blank()
    for facts in results:
        _render_one(facts)
    bad = sum(1 for f in results if not f.ok)
    warn = sum(
        1 for f in results for x in f.findings if x.severity == "warning"
    )
    c.blank()
    if len(results) > 1:
        t = Table(
            [
                Column("File"),
                Column("Result", min_width=6),
                Column("States", align="right"),
                Column("Events", align="right"),
                Column("Warnings", align="right"),
            ]
        )
        for f in results:
            t.add(
                f.path.name,
                c.style("ok", "ok") if f.ok else c.style("FAIL", "err"),
                f.state_count(all_levels=True),
                len(f.events),
                sum(1 for x in f.findings if x.severity == "warning"),
            )
        c.table(t)
        c.blank()
    if bad:
        # 📌 pinned: "N file(s) had errors."
        c.error(f"{bad} file(s) had errors.")
        raise SystemExit(1)
    # 📌 pinned: "All N file(s) are valid."
    tail = f" ({warn} warning(s))" if warn else ""
    c.ok(f"All {len(results)} file(s) are valid.{tail}")
