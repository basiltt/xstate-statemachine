# src/xstate_statemachine/contrib/django/management/commands/xsm_refresh_columns.py
# -----------------------------------------------------------------------------
# 🧰 manage.py xsm_refresh_columns app.Model [--batch N] [--dry-run]
# -----------------------------------------------------------------------------
# 🏛️ `refresh_statechart_columns` from the shell: recompute the
#    denormalised ``<field>_state`` / ``_state_ids`` / ``_machine_version``
#    columns from the snapshot after a bulk import or a raw SQL edit.
#    Keyset-paginated (bounded memory); ``--dry-run`` only counts.
# -----------------------------------------------------------------------------
"""The ``xsm_refresh_columns`` management command."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from ._resolve import model_from_label

__all__ = ["Command"]


class Command(BaseCommand):
    help = (
        "Recompute a statechart model's denormalised state columns from "
        "its snapshots (batched; --dry-run counts only)."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        parser.add_argument("--batch", type=int, default=1000)
        parser.add_argument("--database", default="default")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **opts: Any) -> None:
        from ...migration_helpers import refresh_statechart_columns

        if opts["batch"] < 1:
            raise CommandError("--batch must be >= 1")
        model = model_from_label(opts["model"])
        n = refresh_statechart_columns(
            model,
            model.statechart_field_obj().name,
            using=opts["database"],
            batch=opts["batch"],
            dry_run=opts["dry_run"],
        )
        verb = "would change" if opts["dry_run"] else "changed"
        self.stdout.write(f"{model._meta.label}: {verb} {n} row(s)")
