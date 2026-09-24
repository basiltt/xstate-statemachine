# src/xstate_statemachine/cli/commands/inspect.py
# -----------------------------------------------------------------------------
# 🔍 `xsm inspect` -- everything about a machine on one screen
# -----------------------------------------------------------------------------
"""The `inspect` subcommand: state tree, events, logic, timers, policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...models import MachineNode, StateNode
from ...validation import walk
from ..ui import Column, Node, Table
from . import get_console
from .analysis import Facts, analyse, event_table, short_id

KIND_GLYPH = {
    "atomic": "○",
    "compound": "◆",
    "parallel": "⫴",
    "final": "◉",
    "history": "↺",
}
KIND_ASCII = {
    "atomic": "o",
    "compound": "+",
    "parallel": "||",
    "final": "@",
    "history": "H",
}


def state_tree(
    machine: MachineNode,
    *,
    active: Optional[Set[str]] = None,
    unicode: bool = True,
) -> Node:
    """Build a `Node` tree for the machine; *active* ids get a marker."""
    active = active or set()
    glyphs = KIND_GLYPH if unicode else KIND_ASCII

    def build(node: StateNode, is_root: bool = False) -> Node:
        label = node.id.rsplit(".", 1)[-1] if not is_root else node.id
        kind = node.type
        role = "kind.active" if node.id in active else f"kind.{kind}"
        bits: List[str] = []
        if node.initial and kind == "compound":
            bits.append(f"initial={node.initial}")
        if node.after:
            bits.append("after " + ", ".join(str(k) for k in node.after))
        if node.invoke:
            bits.append(
                "invoke " + ", ".join(i.src or "?" for i in node.invoke)
            )
        if node.on and any(ev == "" for ev in node.on):
            bits.append("always")
        if node.tags:
            bits.append("#" + " #".join(sorted(node.tags)))
        note = "  ".join(bits)
        if node.id in active:
            note = ("● active  " if unicode else "* active  ") + note
        n = Node(f"{glyphs.get(kind, '?')} {label}", role=role, note=note)
        n.children = [build(ch) for ch in node.states.values()]
        return n

    return build(machine, is_root=True)


def _policies(m: MachineNode) -> List[List[str]]:
    return [
        ["actionErrorPolicy", m.action_error_policy],
        ["guardErrorPolicy", m.guard_error_policy],
        ["onUnhandled", m.on_unhandled],
        ["maxIterations", str(m.max_iterations)],
        ["strict", str(m.strict).lower()],
        ["strictTargets", str(m.strict_targets).lower()],
        [
            "event schemas",
            str(len(m.event_schemas)) if m.event_schemas else "none",
        ],
    ]


def render_inspect(facts: Facts, *, show_events: bool = True) -> None:
    c = get_console()
    m = facts.machine
    if m is None:
        for f in facts.findings:
            c.error(f"{facts.path}: {f.message}")
        raise SystemExit(1)

    total = facts.state_count(all_levels=True)
    kinds: Dict[str, int] = {}
    for n in walk(m):
        if n is not m:
            kinds[n.type] = kinds.get(n.type, 0) + 1
    timers = sum(len(n.after) for n in walk(m))
    invokes = sum(len(n.invoke) for n in walk(m))

    c.blank()
    c.panel(
        [
            f"{c.style('Machine', 'key')}   {c.style(m.id, 'title')}",
            f"{c.style('States', 'key')}    {total}  "
            + c.style(
                "  ".join(f"{k} {v}" for k, v in sorted(kinds.items())),
                "muted",
            ),
            f"{c.style('Events', 'key')}    {len(facts.events)}    "
            f"{c.style('Timers', 'key')} {timers}    {c.style('Invokes', 'key')} {invokes}",
            f"{c.style('Logic', 'key')}     "
            f"{len(facts.actions)} actions · {len(facts.guards)} guards · "
            f"{len(facts.services)} services · {len(facts.delays)} named delays",
        ],
        title="inspect",
        subtitle=str(facts.path),
    )
    c.blank()

    c.rule("state tree")
    c.tree(state_tree(m, unicode=c.caps.unicode))
    c.blank()

    if show_events:
        rows = event_table(m)
        if rows:
            c.rule(f"transitions ({len(rows)})")
            t = Table(
                [
                    Column("Event", role="event", min_width=12, max_width=32),
                    Column("From", min_width=10),
                    Column("To", min_width=10),
                    Column("Guard", role="guard", min_width=5),
                    Column("Actions", role="action", min_width=7),
                ],
                zebra=True,
            )
            for ev, src, dst, guard, acts in rows:
                t.add(
                    ev,
                    short_id(src, m.id),
                    (
                        short_id(dst, m.id)
                        if dst != "(internal)"
                        else c.style(dst, "muted")
                    ),
                    guard or "",
                    acts or "",
                )
            c.table(t)
            c.blank()

    c.rule("logic to implement")
    lt = Table([Column("Kind", min_width=8), Column("Names")], border=False)
    lt.add(
        c.style("actions", "action"),
        ", ".join(sorted(facts.actions)) or c.style("none", "muted"),
    )
    lt.add(
        c.style("guards", "guard"),
        ", ".join(sorted(facts.guards)) or c.style("none", "muted"),
    )
    lt.add(
        c.style("services", "service"),
        ", ".join(sorted(facts.services)) or c.style("none", "muted"),
    )
    if facts.delays:
        lt.add("delays", ", ".join(sorted(facts.delays)))
    c.table(lt)
    c.blank()

    c.rule("policies")
    pt = Table([Column("Key", role="key"), Column("Value")], border=False)
    for k, v in _policies(m):
        pt.add(k, v)
    c.table(pt)
    c.blank()

    warnings = [f for f in facts.findings if f.severity == "warning"]
    if warnings:
        c.rule(f"warnings ({len(warnings)})")
        for w in warnings:
            c.warn(
                f"{w.message}"
                + (f"  {c.style(w.path, 'muted')}" if w.path else "")
            )
        c.blank()


def run_inspect(
    path: str, *, as_json: bool = False, no_events: bool = False
) -> None:
    facts = analyse(Path(path), strict_config=False)
    if as_json:
        data: Dict[str, Any] = facts.to_json()
        if facts.machine is not None:
            data["policies"] = dict(_policies(facts.machine))
            data["transitions"] = [
                {"event": e, "from": s, "to": t, "guard": g, "actions": a}
                for e, s, t, g, a in event_table(facts.machine)
            ]
            data["state_kinds"] = {
                n.id: n.type
                for n in walk(facts.machine)
                if n is not facts.machine
            }
        get_console().print(json.dumps(data, indent=2))
        if not facts.ok:
            raise SystemExit(1)
        return
    render_inspect(facts, show_events=not no_events)
