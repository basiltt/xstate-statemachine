# src/xstate_statemachine/contrib/django/management/commands/xsm_simulate.py
"""``manage.py xsm_simulate app.Model [-e A,B,+500] [--json]`` -- the
``xsm simulate`` session on a THROWAWAY in-memory copy of the chart with
stub logic: nothing touches the database."""

from __future__ import annotations

from typing import Any

from ._cli_command import CLICommand


class Command(CLICommand):
    help = "Simulate a statechart model's chart (stub logic, no database)."

    def add_cli_arguments(self, parser: Any) -> None:
        parser.add_argument("-e", "--events", default=None)
        parser.add_argument("--clock", default=None)
        parser.add_argument("--guards-false", default=None)
        parser.add_argument("--json", action="store_true", dest="as_json")

    def run(self, path: str, **options: Any) -> None:
        from .....cli.commands.simulate import run_simulate

        run_simulate(
            path,
            events=options["events"],
            clock=options["clock"],
            as_json=options["as_json"],
            guards_false=options["guards_false"],
        )
