# src/xstate_statemachine/cli/commands/__init__.py
# -----------------------------------------------------------------------------
# 🧩 One module per `xsm` subcommand. `__main__` only dispatches.
# -----------------------------------------------------------------------------
"""Command implementations for the `xsm` CLI."""

from __future__ import annotations

import argparse
from typing import Optional

from ..ui import Console, detect

_console: Optional[Console] = None


def get_console() -> Console:
    """The process-wide console; built lazily from the environment."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def configure_console(args: argparse.Namespace) -> Console:
    """Build the console from the global flags on *args* (idempotent)."""
    global _console
    _console = Console(
        detect(
            plain=bool(getattr(args, "plain", False)),
            no_color=bool(getattr(args, "no_color", False)),
            no_anim=bool(getattr(args, "no_anim", False)),
        )
    )
    return _console


def reset_console() -> None:
    """For tests: forget the cached console."""
    global _console
    _console = None
