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
import sys
from typing import Any, Dict, List, Tuple

from ...plugin_discovery import (
    DISABLE_ENV,
    GROUPS,
    _disabled,
    discover,
    last_failed,
    last_skipped,
)
from . import get_console


def _rows(
    strict: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for group in GROUPS:
        found = discover(group=group, strict=strict)
        skipped.extend(s._asdict() for s in last_skipped)
        for p in found:
            rows.append(
                {
                    "name": p.name,
                    "distribution": p.distribution,
                    "version": p.version,
                    "group": group,
                    "hooks": list(p.hooks),
                }
            )
    return rows, skipped


def run_plugins(as_json: bool = False, strict: bool = False) -> int:
    """Print every discovered entry point (name, dist, version, hooks).

    Returns the exit code: 0, or 1 under ``--strict`` when an entry point
    could not be loaded (the first failure is named; no traceback).
    """
    c = get_console()
    disabled = _disabled()
    try:
        rows, skipped = ([], []) if disabled else _rows(strict=strict)
    except Exception as exc:  # noqa: BLE001 -- --strict: name it, exit 1
        # 📝 #296 review (4): without --strict a loader never raises here;
        #    anything else (corrupt site-packages metadata) is a real
        #    error -- let it surface instead of blaming a flag not given.
        if not strict:
            raise
        who = (
            f"{last_failed['name']!r} from {last_failed['dist'] or '?'}"
            if last_failed
            else "an entry point"
        )
        print(
            f"error: plugin entry point {who} failed to load "
            f"({type(exc).__name__}: {exc}); run `xsm plugins` without "
            "--strict for the full list",
            file=sys.stderr,
        )
        return 1
    if as_json:
        c.print(
            json.dumps(
                {"disabled": disabled, "plugins": rows, "skipped": skipped},
                indent=2,
            )
        )
        return 0
    if disabled:
        c.print(f"Plugin discovery is disabled ({DISABLE_ENV}=1).")
        return 0
    if not rows and not skipped:
        c.print(
            "No third-party plugins installed "
            "(entry-point groups: " + ", ".join(GROUPS) + ")."
        )
        return 0
    for row in rows:
        c.print(
            f"{row['name']}  {row['distribution'] or '?'} "
            f"{row['version'] or '?'}  [{row['group']}]"
        )
        if row["hooks"]:
            c.print("    hooks: " + ", ".join(row["hooks"]))
    for row in skipped:
        c.print(
            f"{row['name']}  {row['distribution'] or '?'} "
            f"{row['version'] or '?'}  [{row['group']}]  SKIPPED: "
            f"{row['error']}"
        )
    return 0
