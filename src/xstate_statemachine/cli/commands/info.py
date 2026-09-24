# src/xstate_statemachine/cli/commands/info.py
# -----------------------------------------------------------------------------
# ℹ️ `xsm info` -- library, environment and feature summary
# -----------------------------------------------------------------------------
"""The `info` subcommand."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict

from ...plugins import PluginBase
from ..strategies import STRATEGY_REGISTRY
from . import get_console

DOCS = "https://basiltt.github.io/xstate-statemachine/"
PYPI = "https://pypi.org/project/xstate-statemachine/"
GITHUB = "https://github.com/basiltt/xstate-statemachine"

#: The feature grid. Each card: (title, *lines). Kept as data so `--json`
#: and the rendered cards cannot drift apart.
FEATURES = (
    (
        "Engines",
        "Async Interpreter + SyncInterpreter",
        "same JSON, same semantics",
    ),
    (
        "XState interop",
        "run Stately exports unmodified",
        "v5 action creators, guards, invoke",
    ),
    (
        "Statecharts",
        "nested, parallel, history, final",
        "after timers, always, done data",
    ),
    (
        "Actors",
        "spawn / invoke child machines",
        "sendTo, sendParent, escalate",
    ),
    (
        "Persistence",
        "snapshot layout v3, drift check",
        "strict applies on restore",
    ),
    (
        "Reliability",
        "actionErrorPolicy, strict, strictConfig",
        "maxIterations with a sticky record",
    ),
    (
        "Observability",
        "plugin hooks, LoggingInspector",
        "receipts, chain_trips, last_error",
    ),
    (
        "Pythonic API",
        "class, builder, functional",
        "typed context, decorators",
    ),
    (
        "Tooling",
        "xsm generate / inspect / simulate",
        "Mermaid + PlantUML export",
    ),
)


def _payload() -> Dict[str, Any]:
    from ... import __version__

    hooks = [n for n in dir(PluginBase) if n.startswith("on_")]
    return {
        "version": __version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": f"{platform.system()} {platform.machine()}",
        "install_path": str(Path(__file__).resolve().parents[2]),
        "templates": sorted(STRATEGY_REGISTRY),
        "plugin_hooks": len(hooks),
        "features": [
            {"title": t, "lines": list(rest)} for t, *rest in FEATURES
        ],
        "links": {"docs": DOCS, "pypi": PYPI, "github": GITHUB},
        # 🪟 The same command without pip's `xsm.exe` launcher -- for Windows
        #    machines whose Application Control policy blocks that stub.
        "module_invocation": f"{Path(sys.executable).name} -m xstate_statemachine",
    }


def run_info(as_json: bool = False) -> None:
    c = get_console()
    data = _payload()
    if as_json:
        c.print(json.dumps(data, indent=2))
        return
    c.banner(data["version"])
    c.blank()
    # 📋 The strings below are pinned by tests/tests_cli/test_subcommands.py.
    c.kv(
        [
            ("Version:", data["version"]),
            ("Python:", f"{data['python']} ({data['implementation']})"),
            ("Platform:", data["platform"]),
            ("Install path:", c.style(data["install_path"], "path")),
            ("Templates:", ", ".join(data["templates"])),
            ("Plugin hooks:", str(data["plugin_hooks"])),
            ("Also run as:", c.style(data["module_invocation"], "code")),
        ]
    )
    if sys.platform.startswith("win"):
        # 🪟 Discoverability for the one machine class where `xsm` itself
        #    may be refused (pip's unsigned launcher vs. Application Control).
        c.print(
            c.style(
                "  Windows blocking xsm.exe? Run "
                f"`{data['module_invocation']} setup` once.",
                "muted",
            )
        )
    c.blank()
    c.cards(
        FEATURES,
        columns=3 if c.caps.width >= 96 else 2 if c.caps.width >= 64 else 1,
    )
    c.blank()
    c.kv(
        [
            ("Documentation:", c.style(DOCS, "path")),
            ("PyPI:", c.style(PYPI, "path")),
            ("GitHub:", c.style(GITHUB, "path")),
        ]
    )
    c.blank()
    c.print(
        c.style("  Zero runtime dependencies. Python 3.9 → 3.14.", "muted")
        if c.caps.unicode
        else "  Zero runtime dependencies. Python 3.9 - 3.14."
    )
    if sys.stdout.isatty() and c.caps.tty:
        c.print(
            c.style(
                "  Try: xsm  (no arguments) for the interactive launcher.",
                "dim",
            )
        )
