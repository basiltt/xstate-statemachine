# src/xstate_statemachine/cli/commands/templates.py
# -----------------------------------------------------------------------------
# 📋 `xsm list-templates` -- the generator's catalogue as a comparison table
# -----------------------------------------------------------------------------
"""The `list-templates` subcommand."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ..validation import builds_machine_inline
from ..ui import Column, Table
from . import get_console

#: (id, style, description, kind) -- `kind` groups the catalogue.
#: The generator strategies are registered in `cli.strategies`; this table
#: is what a human reads, so it also carries the one-line pitch.
TEMPLATES = (
    (
        "class-json",
        "Class + JSON",
        "OOP logic class with MachineLogic, bound to a JSON config loaded at runtime.",
        "runtime",
    ),
    (
        "function-json",
        "Functions + JSON",
        "Module-level functions with LogicLoader auto-discovery, JSON config at runtime.",
        "runtime",
    ),
    (
        "pythonic-class",
        "Class-Based",
        "StateMachine subclass with @action, @guard, @service decorators. Pure Python.",
        "pythonic",
    ),
    (
        "pythonic-builder",
        "Builder Pattern",
        "Fluent MachineBuilder API for dynamic, programmatic machine construction.",
        "pythonic",
    ),
    (
        "pythonic-functional",
        "Functional",
        "Simple build_machine() call with explicit state and transition definitions.",
        "pythonic",
    ),
    (
        "pytest",
        "Test scaffold",
        "A pytest module per machine: initial state, every reachable transition, guards, timers via SimulatedClock.",
        "companion",
    ),
    (
        "typed",
        "Typed context + events",
        "TypedDict for context, Literal alias for event names, typed action / guard / service stubs.",
        "companion",
    ),
    (
        "plugin",
        "Plugin skeleton",
        "A PluginBase subclass wired for exactly the hooks this machine can fire, with structured logging.",
        "companion",
    ),
)


def catalogue() -> List[Dict[str, Any]]:
    out = []
    for tid, style, desc, kind in TEMPLATES:
        inline = builds_machine_inline(tid)
        out.append(
            {
                "id": tid,
                "style": style,
                "description": desc,
                "kind": kind,
                "machine_built": (
                    "in Python"
                    if inline
                    else ("from JSON" if kind == "runtime" else "n/a")
                ),
                "verified": (
                    "structural"
                    if inline
                    else ("syntax" if kind == "runtime" else "compiles")
                ),
                "config_needed_at_runtime": kind == "runtime",
            }
        )
    return out


def run_list_templates(as_json: bool = False) -> None:
    c = get_console()
    rows = catalogue()
    if as_json:
        c.print(json.dumps(rows, indent=2))
        return
    c.blank()
    c.print(c.style("Available code generation templates", "title"))
    c.blank()
    for kind, heading in (
        ("runtime", "Logic modules that load the JSON at runtime"),
        (
            "pythonic",
            "Pure-Python re-expressions of the machine (structurally verified)",
        ),
        ("companion", "Companion outputs -- add alongside any template"),
    ):
        c.rule(heading)
        t = Table(
            [
                Column("Template ID", role="accent", min_width=20),
                Column("Style", min_width=14),
                Column("Description", max_width=0),
            ],
            border=False,
        )
        for r in rows:
            if r["kind"] == kind:
                t.add(r["id"], r["style"], r["description"])
        c.table(t)
        c.blank()

    c.print(c.style("Feature support", "title"))
    c.blank()
    t = Table(
        [
            Column("Template ID", role="accent", min_width=20),
            Column("Machine built", min_width=13),
            Column("Verified", min_width=10),
            Column("Config needed at runtime", min_width=24),
        ]
    )
    for r in rows:
        t.add(
            r["id"],
            r["machine_built"],
            r["verified"],
            "yes -- ship the .json" if r["config_needed_at_runtime"] else "no",
        )
    c.table(t)
    c.blank()
    c.print(
        "  All templates support nesting, parallel regions, history, guards,",
        "  timers (numeric and named delays), invoke, tags and meta.",
        "  'Verified' is what the generator proves before writing: templates that",
        "  build the machine in Python are executed and compared against the source.",
        "",
        "  Usage: "
        + c.style(
            "xsm generate-template <file.json> --template <template-id>",
            "code",
        ),
        "         "
        + c.style(
            "xsm gt <file.json> -t pythonic-class --with-types --with-tests",
            "code",
        ),
        "",
    )
