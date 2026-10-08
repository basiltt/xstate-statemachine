# src/xstate_statemachine/contrib/django/management/commands/xsm_snapshots.py
"""``manage.py xsm_snapshots app.Model [--stale] [--json]`` -- the rows of
a statechart model and their machine version; ``--stale`` lists only rows
whose snapshot was written by a different chart version (candidates for
a `SnapshotMigrator` step / `refresh_statechart_columns`)."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from ._resolve import database, field_name, model_from_label


class Command(BaseCommand):
    help = "List statechart rows and their machine versions (--stale)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        parser.add_argument("--stale", action="store_true")
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--limit", type=int, default=1000)
        parser.add_argument("--database", default="default")

    def handle(self, *args: Any, **options: Any) -> None:
        from django.core.management.base import CommandError

        if options["limit"] < 1:
            raise CommandError("--limit must be >= 1")
        using = database(options["database"])
        model = model_from_label(options["model"])
        current = model().statechart_machine_node().version
        name = field_name(model)
        qs = (
            model._base_manager.using(using)
            .exclude(**{f"{name}__isnull": True})
            .order_by("pk")
            .values_list(
                "pk",
                f"{name}_state",
                f"{name}_version",
                f"{name}_machine_version",
            )
        )
        mv_col = f"{name}_machine_version"
        if options["stale"]:
            # 📝 #263 battle: filter BEFORE `--limit` (it used to cap the
            #    rows scanned, hiding stale rows past the first 1000), and
            #    agree with restore + `xsm snapshots`: a chart with no
            #    version never mismatches; an unlabelled row cannot be
            #    checked, so it is not listed as stale.
            if current is None:
                qs = qs.none()
            else:
                qs = (
                    qs.exclude(**{f"{mv_col}__isnull": True})
                    .exclude(**{mv_col: ""})
                    .exclude(**{mv_col: current})
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
                    ensure_ascii=False,
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
