# src/xstate_statemachine/cli/commands/plugins.py
# -----------------------------------------------------------------------------
# 🔎 `xsm plugins` -- list third-party plugins / stores / brokers (#296)
# -----------------------------------------------------------------------------
# 🔐 Listing IS loading: an entry point has to be imported to report which
#    hooks it implements. That is why this is an explicit command and the
#    library itself never discovers on import. XSM_DISABLE_PLUGIN_DISCOVERY=1
#    makes it list nothing.
# -----------------------------------------------------------------------------
"""The `plugins` subcommand."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ...plugin_discovery import DISABLE_ENV, GROUPS, _disabled, discover
from . import get_console


def _rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for group in GROUPS:
        for p in discover(group=group):
            rows.append(
                {
                    "name": p.name,
                    "distribution": p.distribution,
                    "version": p.version,
                    "group": group,
                    "hooks": list(p.hooks),
                }
            )
    return rows


def run_plugins(as_json: bool = False) -> None:
    """Print every discovered entry point (name, dist, version, hooks)."""
    c = get_console()
    disabled = _disabled()
    rows = [] if disabled else _rows()
    if as_json:
        c.print(json.dumps({"disabled": disabled, "plugins": rows}, indent=2))
        return
    if disabled:
        c.print(f"Plugin discovery is disabled ({DISABLE_ENV}=1).")
        return
    if not rows:
        c.print(
            "No third-party plugins installed "
            "(entry-point groups: " + ", ".join(GROUPS) + ")."
        )
        return
    for row in rows:
        c.print(
            f"{row['name']}  {row['distribution'] or '?'} "
            f"{row['version'] or '?'}  [{row['group']}]"
        )
        if row["hooks"]:
            c.print("    hooks: " + ", ".join(row["hooks"]))
