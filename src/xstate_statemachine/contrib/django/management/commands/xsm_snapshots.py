# src/xstate_statemachine/contrib/django/management/commands/xsm_snapshots.py
"""``manage.py xsm_snapshots app.Model [--stale] [--json]`` -- the rows of
a statechart model and their machine version; ``--stale`` lists only rows
whose snapshot was written by a different chart version (candidates for
a `SnapshotMigrator` step / `refresh_statechart_columns`)."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from ._resolve import model_from_label


class Command(BaseCommand):
    help = "List statechart rows and their machine versions (--stale)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        parser.add_argument("--stale", action="store_true")
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--limit", type=int, default=1000)

    def handle(self, *args: Any, **options: Any) -> None:
        model = model_from_label(options["model"])
        current = model().statechart_machine_node().version
        name = model.statechart_field_obj().name
        qs = (
            model._base_manager.exclude(**{f"{name}__isnull": True})
            .order_by("pk")
            .values_list(
                "pk",
                f"{name}_state",
                f"{name}_version",
                f"{name}_machine_version",
            )
        )
        rows = [
            {
                "key": str(pk),
                "state": state,
                "version": int(ver or 0),
                "machine_version": mv,
            }
            for pk, state, ver, mv in qs[: options["limit"]]
        ]
        if options["stale"]:
            rows = [r for r in rows if r["machine_version"] != current]
        if options["as_json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "model": model._meta.label,
                        "machine_version": current,
                        "stale_only": options["stale"],
                        "count": len(rows),
                        "snapshots": rows,
                    },
                    indent=2,
                )
            )
            return
        label = "stale snapshots" if options["stale"] else "snapshots"
        self.stdout.write(
            f"{model._meta.label} {label} (machine version {current!r}): "
            f"{len(rows)}"
        )
        for r in rows:
            self.stdout.write(
                f"  {r['key']:>8}  v{r['version']:<5} "
                f"{r['machine_version'] or '-':<10} {r['state'] or '-'}"
            )
