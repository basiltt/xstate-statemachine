# src/xstate_statemachine/contrib/django/management/commands/xsm_inspect.py
"""``manage.py xsm_inspect app.Model [pk] [--json] [--no-events] [--plain]``.

Same output as ``xsm inspect <chart.json>``. With *pk*, also prints that
row's active state ids and version after the chart report.
"""

from __future__ import annotations

from typing import Any

from ._cli_command import CLICommand


class Command(CLICommand):
    help = "Show a statechart model's state tree, events, logic, policies."

    def add_cli_arguments(self, parser: Any) -> None:
        parser.add_argument("pk", nargs="?", default=None)
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--no-events", action="store_true")

    def run(self, path: str, **options: Any) -> None:
        from .....cli.commands.inspect import run_inspect

        run_inspect(
            path, as_json=options["as_json"], no_events=options["no_events"]
        )

    def handle(self, *args: Any, **options: Any) -> None:
        super().handle(*args, **options)
        pk = options.get("pk")
        if pk is None:
            return
        from ._resolve import model_from_label

        model = model_from_label(options["model"])
        try:
            row = model._base_manager.get(pk=pk)
        except model.DoesNotExist:
            from django.core.management.base import CommandError

            raise CommandError(f"{options['model']} pk={pk} not found")
        name = model.statechart_field_obj().name
        self.stdout.write(f"row {pk}: {row.state or '-'}")
        self.stdout.write(
            f"version {getattr(row, name + '_version')}  "
            f"machine_version {getattr(row, name + '_machine_version') or '-'}"
        )
