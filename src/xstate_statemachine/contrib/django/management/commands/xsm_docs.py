# src/xstate_statemachine/contrib/django/management/commands/xsm_docs.py
"""``manage.py xsm_docs app.Model [-o dir]`` -- same Markdown as
``xsm docs <chart.json>``."""

from __future__ import annotations

from typing import Any

from ._cli_command import CLICommand


class Command(CLICommand):
    help = "Generate a Markdown reference page for a statechart model."

    def add_cli_arguments(self, parser: Any) -> None:
        parser.add_argument("-o", "--output", default=None)

    def run(self, path: str, **options: Any) -> None:
        from .....cli.commands.docs import run_docs

        run_docs([path], output=options["output"])
