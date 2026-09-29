# src/xstate_statemachine/cli/commands/coverage.py
# -----------------------------------------------------------------------------
# 📊 `xsm coverage` -- render a state & transition coverage report (#270)
# -----------------------------------------------------------------------------
# 🏛️ The pytest plugin (`--xsm-coverage-report=json:PATH`) writes the stable
#    version-1 JSON document; this command renders it for CI logs (plain or
#    styled) and applies a `--fail-under` gate, like `coverage report`.
# -----------------------------------------------------------------------------
"""The `coverage` subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...coverage import below, format_edge, reports_from_json, reports_to_json
from ..ui import Column, Table
from . import get_console


def run_coverage(
    report_file: str,
    *,
    fail_under: Optional[float] = None,
    as_json: bool = False,
) -> None:
    """Print *report_file*; exit 1 if any machine is under *fail_under*
    (applied to both state and transition coverage) or the file is bad."""
    c = get_console()
    try:
        reports = reports_from_json(
            Path(report_file).read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        c.error(f"{report_file}: {exc}")
        raise SystemExit(1)
    failures = below(reports, state=fail_under, transition=fail_under)
    if as_json:
        c.print(reports_to_json(reports).rstrip("\n"))
    else:
        c.blank()
        t = Table([Column("Machine"), Column("States"), Column("Transitions")])
        for r in reports:
            t.add(
                r.machine_id,
                f"{r.states_visited}/{r.states_total} "
                f"({r.state_percent:g}%)",
                f"{r.transitions_hit}/{r.transitions_total} "
                f"({r.transition_percent:g}%)",
            )
        c.table(t)
        for r in reports:
            if r.unvisited or r.unhit:
                c.blank()
                c.print(f"  {c.style(r.machine_id, 'key')}")
            for s in r.unvisited:
                c.print(f"    unvisited  {s}")
            for u in r.unhit:
                c.print(f"    unhit      {format_edge(u, r.machine_id)}")
        if not reports:
            c.info("no machines in the report")
    for failure in failures:
        c.error(f"coverage below --fail-under: {failure}")
    if failures:
        raise SystemExit(1)
