# src/xstate_statemachine/contrib/django/management/commands/xsm_migrate_fsm.py
# -----------------------------------------------------------------------------
# 🔁 manage.py xsm_migrate_fsm app.Model --field state [...]
# -----------------------------------------------------------------------------
#    --dry-run               print the extracted XState JSON (step 1) and
#                            the recipe; touch nothing
#    --write-chart PATH      write that JSON for review / commit
#    (default)               step 3: fill empty snapshots from the FSM
#                            column, batched, resumable, idempotent
#    --batch N               rows per transaction (1000)
#    --statechart-field F    the StatechartField added in step 2
# -----------------------------------------------------------------------------
"""The ``xsm_migrate_fsm`` management command (#310)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

__all__ = ["Command", "RECIPE"]

RECIPE = """\
Migrating {label}.{field} from django-fsm to a statechart:

  1. Review the chart above (states, events = method names, guards =
     conditions / permissions). Implement each guard in the model's
     statechart_logic (PermissionGuard for permissions).
  2. Add `statechart = StatechartField()` BESIDE the FSMField, point
     `statechart_machine` at the chart, and run makemigrations/migrate.
  3. python manage.py xsm_migrate_fsm {label} --field {field}
     (batched, resumable, idempotent -- safe to re-run).
  4. Dual-read for one release: mix FSMDualWriteMixin into the model so
     every send() also writes {field}; then drop the FSMField.
"""


class Command(BaseCommand):
    help = "Migrate a django-fsm FSMField to a StatechartField."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        parser.add_argument("--field", default="state")
        parser.add_argument("--statechart-field", default="statechart")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--write-chart", default=None, metavar="PATH")
        parser.add_argument("--machine-id", default=None)
        parser.add_argument("--batch", type=int, default=1000)
        parser.add_argument("--database", default="default")

    def handle(self, *args: Any, **opts: Any) -> None:
        from ...fsm import extract_chart, migrate_rows

        try:
            model = apps.get_model(opts["model"])
        except (LookupError, ValueError) as exc:
            raise CommandError(f"unknown model {opts['model']!r}: {exc}")
        from django.core.exceptions import FieldDoesNotExist

        try:
            chart = extract_chart(
                model, opts["field"], machine_id=opts["machine_id"]
            )
        except (TypeError, ValueError, LookupError, FieldDoesNotExist) as exc:
            raise CommandError(str(exc)) from None
        text = json.dumps(chart, indent=2)
        if opts["write_chart"]:
            out = Path(opts["write_chart"])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
            self.stdout.write(f"wrote {out}")
        if opts["dry_run"]:
            self.stdout.write(text)
            self.stdout.write(
                RECIPE.format(label=opts["model"], field=opts["field"])
            )
            return
        from ...mixin import StatechartModelMixin

        if not issubclass(model, StatechartModelMixin):
            raise CommandError(
                f"{opts['model']} has no StatechartField yet (step 2); run "
                f"with --dry-run to see the chart and the recipe."
            )
        done, batches = migrate_rows(
            model,
            opts["field"],
            statechart_field=opts["statechart_field"],
            batch=opts["batch"],
            using=opts["database"],
        )
        remaining = (
            model._base_manager.using(opts["database"])
            .filter(**{f"{opts['statechart_field']}__isnull": True})
            .count()
        )
        self.stdout.write(
            f"migrated {done} row(s) in {batches} batch(es); "
            f"{remaining} remaining"
        )
