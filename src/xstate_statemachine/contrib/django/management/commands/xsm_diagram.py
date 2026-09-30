# src/xstate_statemachine/contrib/django/management/commands/xsm_diagram.py
"""``manage.py xsm_diagram app.Model [-f mermaid|plantuml|ascii] [-o out]``
-- same output as ``xsm diagram <chart.json>``."""

from __future__ import annotations

from typing import Any

from ._cli_command import CLICommand


class Command(CLICommand):
    help = "Export a statechart model's chart as Mermaid, PlantUML or ASCII."

    def add_cli_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "-f",
            "--format",
            dest="fmt",
            choices=["mermaid", "plantuml", "ascii"],
            default="mermaid",
        )
        parser.add_argument("-o", "--output", default=None)

    def run(self, path: str, **options: Any) -> None:
        from .....cli.commands.diagram import run_diagram

        run_diagram(path, fmt=options["fmt"], output=options["output"])
