# src/xstate_statemachine/cli/commands/paths.py
# -----------------------------------------------------------------------------
# 🗺️ `xsm paths` -- every reachable configuration and how to get there
# -----------------------------------------------------------------------------
# 🏛️ #269: the chart already IS the graph. `graph.shortest_paths` executes
#    the real engine on a SimulatedClock with stub logic, so what is
#    printed here is what the engine does -- parallel regions, history,
#    `after` timers and all -- not a hand-written approximation.
# -----------------------------------------------------------------------------
"""The `paths` subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ...graph import Path as GraphPath
from ...graph import shortest_paths, simple_paths
from ..ui import Column, Table
from . import get_console
from .analysis import analyse


def _path_json(p: GraphPath) -> Dict[str, Any]:
    return {
        "final_states": sorted(p.final_states),
        "events": p.event_string(),
        "steps": [
            {
                "event": s.event,
                "delay_ms": s.delay_ms,
                "from": sorted(s.from_states),
                "to": sorted(s.to_states),
                "assumptions": list(s.assumptions),
            }
            for s in p.steps
        ],
    }


def run_paths(
    json_file: str,
    *,
    simple: bool = False,
    guards: str = "true",
    max_depth: int = 50,
    max_paths: int = 1000,
    as_json: bool = False,
) -> None:
    """Print a path to every reachable configuration (or every simple path).

    Args:
        json_file: The chart.
        simple: `simple_paths` (every acyclic path) instead of one
            shortest path per configuration.
        guards: ``true`` / ``false`` / ``both`` -- what stub guards return
            during exploration; ``both`` records the assumption each path
            relies on.
        max_depth: Exploration depth bound.
        max_paths: Cap for ``--simple``.
        as_json: Emit JSON instead of the table.
    """
    c = get_console()
    facts = analyse(Path(json_file))
    if not facts.ok or facts.machine is None:
        c.print(c.style(f"x {json_file} does not build:", "err"))
        for f in facts.findings:
            if f.severity == "error":
                c.print(f"    - {f.message}")
        raise SystemExit(1)
    m = facts.machine
    if simple:
        found: List[GraphPath] = simple_paths(
            m, guards=guards, max_paths=max_paths, max_depth=max_depth
        )
    else:
        found = sorted(
            shortest_paths(m, guards=guards, max_depth=max_depth).values(),
            key=lambda p: (len(p.steps), sorted(p.final_states)),
        )
    if as_json:
        c.print(
            json.dumps(
                {
                    "machine": m.id,
                    "mode": "simple" if simple else "shortest",
                    "guards": guards,
                    "paths": [_path_json(p) for p in found],
                },
                indent=2,
            )
        )
        return
    c.blank()
    c.print(
        f"  {c.style(m.id, 'key')}  "
        f"{len(found)} {'path' if len(found) == 1 else 'paths'} "
        f"({'simple' if simple else 'shortest'}, guards={guards})"
    )
    t = Table([Column("Configuration"), Column("Events"), Column("Assumes")])
    for p in found:
        t.add(
            ", ".join(sorted(p.final_states)),
            p.event_string() or "(initial)",
            "; ".join(sorted({a for s in p.steps for a in s.assumptions})),
        )
    c.table(t)
