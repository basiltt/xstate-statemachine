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
        parser.add_argument(
            "--database", default="default", help="Alias to read *pk* from."
        )

    def run(self, path: str, **options: Any) -> None:
        from .....cli.commands.inspect import run_inspect

        run_inspect(
            path, as_json=options["as_json"], no_events=options["no_events"]
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from ._resolve import database, field_name, get_row, model_from_label

        pk = options.get("pk")
        if pk is not None:
            # 📝 Validate before printing the chart report, so a bad pk /
            #    alias fails without half the output (#282 battle).
            model = model_from_label(options["model"])
            row = get_row(model, pk, database(options["database"]))
            name = field_name(model)
        super().handle(*args, **options)
        if pk is None:
            return
        self.stdout.write(f"row {pk}: {row.state or '-'}")
        self.stdout.write(
            f"version {getattr(row, name + '_version')}  "
            f"machine_version {getattr(row, name + '_machine_version') or '-'}"
        )
