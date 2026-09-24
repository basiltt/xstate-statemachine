# src/xstate_statemachine/cli/commands/launcher.py
# -----------------------------------------------------------------------------
# 🧭 `xsm` with no arguments on a terminal -- the interactive launcher
# -----------------------------------------------------------------------------
"""Banner + menu. Each entry hands off to a command's interactive path."""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from . import get_console

MENU: List[Tuple[str, str, str]] = [
    (
        "generate",
        "Generate code",
        "Pick JSON files and a template; preview before writing",
    ),
    (
        "inspect",
        "Inspect a machine",
        "State tree, events, logic and policies at a glance",
    ),
    (
        "simulate",
        "Simulate",
        "Run a machine live: pick events, advance the clock",
    ),
    (
        "validate",
        "Validate",
        "Build files with the real library and list findings",
    ),
    ("diagram", "Diagram", "Mermaid / PlantUML / ASCII to stdout or a file"),
    ("templates", "Templates", "Browse the code generation catalogue"),
    ("info", "About", "Version, environment, links"),
    ("quit", "Quit", ""),
]


def run_launcher(parser: argparse.ArgumentParser) -> None:
    from ... import __version__

    c = get_console()
    c.banner(__version__)
    c.blank()
    while True:
        idx = c.select(
            "What would you like to do?",
            [(label, desc) for _key, label, desc in MENU],
        )
        if idx is None or MENU[idx][0] == "quit":
            c.print(c.style("bye", "muted"))
            return
        key = MENU[idx][0]
        c.blank()
        if key == "info":
            from .info import run_info

            run_info()
        elif key == "templates":
            from .templates import run_list_templates

            run_list_templates()
        elif key == "validate":
            path = c.text("Path to a machine JSON (or a glob):")
            if path:
                import glob

                from .validate import run_validate

                files = sorted(glob.glob(path)) or [path]
                try:
                    run_validate(files)
                except SystemExit:
                    pass
        else:
            # 🚧 Wired in the next phases (generate wizard, inspect,
            #    simulate, diagram). Tell the user how to run it today.
            c.info(
                f"'{MENU[idx][1]}' is available as: "
                + c.style(f"xsm {key} <file.json>", "code")
            )
        c.blank()
        if not sys.stdin.isatty():  # pragma: no cover -- defensive
            return
