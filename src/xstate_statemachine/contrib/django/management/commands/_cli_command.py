# src/xstate_statemachine/contrib/django/management/commands/_cli_command.py
# -----------------------------------------------------------------------------
# ⌨️ Base for the ``xsm_*`` commands that delegate to the `xsm` CLI
# -----------------------------------------------------------------------------
# 🏛️ Thin delegation, exactly like ``flask xsm``: resolve the MODEL's chart
#    to a JSON file (its own path, or a temp copy of the parsed config) and
#    call the same function ``xsm <cmd>`` calls, writing to the command's
#    raw stdout -- so ``manage.py xsm_inspect shop.Order --plain`` prints
#    byte for byte what ``xsm inspect shop/machines/order.json --plain``
#    prints (the tests pin it).
# -----------------------------------------------------------------------------
"""Shared base for the CLI-delegating management commands (internal)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from ._resolve import (
    add_console_flags,
    console,
    machine_json_path,
    model_from_label,
    run_cli,
)

__all__ = ["CLICommand"]


class CLICommand(BaseCommand):
    """Subclasses implement `run(path, **options)`."""

    requires_system_checks: Any = []

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        add_console_flags(parser)
        self.add_cli_arguments(parser)

    def add_cli_arguments(self, parser: Any) -> None:
        """Subclass hook for command-specific flags."""

    def run(self, path: str, **options: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def handle(self, *args: Any, **options: Any) -> None:
        model = model_from_label(options["model"])
        with machine_json_path(model) as path:
            console(options, self.stdout)
            run_cli(self.run, path, **options)
