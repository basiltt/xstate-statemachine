# src/xstate_statemachine/contrib/django/management/commands/xsm_migrate_fsm.py
# -----------------------------------------------------------------------------
# 🔁 manage.py xsm_migrate_fsm app.Model --field state [...]
# -----------------------------------------------------------------------------
#    --dry-run               print the extracted XState JSON (step 1) on
#                            stdout, the recipe on stderr; touch nothing
#    --write-chart PATH      write that JSON for review / commit
#    (default)               step 3: fill empty snapshots from the FSM
#                            column, batched, resumable, idempotent
#    --batch N               rows per transaction (1000)
#    --statechart-field F    the StatechartField added in step 2
#    --map OLD=NEW           fold a renamed legacy value into a state
# -----------------------------------------------------------------------------
"""The ``xsm_migrate_fsm`` management command (#310)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

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
     (batched, resumable, idempotent -- safe to re-run). Rows whose
     {field} the chart does not know are skipped and reported per
     value; fold renames in with --map OLD=NEW and run again.
  4. Dual-read for one release: mix FSMDualWriteMixin into the model.
     It is two-way: every send() also writes {field}, and old code's
     @transition + save() re-adopts the snapshot. Then drop the FSMField.
"""


class Command(BaseCommand):
    help = "Migrate a django-fsm FSMField to a StatechartField."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("model", metavar="app.Model")
        parser.add_argument(
            "--field", default="state", help="the FSMField (state)"
        )
        parser.add_argument(
            "--statechart-field",
            default="statechart",
            help="the StatechartField added in step 2 (statechart)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="print the chart JSON on stdout (the recipe on stderr); "
            "touch no row",
        )
        parser.add_argument(
            "--write-chart",
            default=None,
            metavar="PATH",
            help="also write the chart JSON to PATH",
        )
        parser.add_argument("--machine-id", default=None)
        parser.add_argument(
            "--batch", type=int, default=1000, help="rows per transaction"
        )
        parser.add_argument("--database", default="default")
        parser.add_argument(
            "--map",
            action="append",
            default=[],
            metavar="OLD=NEW",
            help="fold a legacy column value into a chart state "
            "(repeatable); unknown values are reported and skipped",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        from django.core.exceptions import FieldDoesNotExist
        from django.db import DatabaseError

        from ...fsm import extract_chart

        # 🔥 #310 battle B: validate operator input before touching
        #    anything (a bad --batch / --map / --database / --statechart-
        #    field / unwritable --write-chart was a raw traceback).
        if opts["batch"] < 1:
            raise CommandError("--batch must be >= 1")
        value_map = _parse_map(opts["map"])
        try:
            model = apps.get_model(opts["model"])
        except (LookupError, ValueError) as exc:
            raise CommandError(f"unknown model {opts['model']!r}: {exc}")
        try:
            chart = extract_chart(
                model, opts["field"], machine_id=opts["machine_id"]
            )
        except (TypeError, ValueError, LookupError, FieldDoesNotExist) as exc:
            raise CommandError(str(exc)) from None
        text = json.dumps(chart, indent=2)
        # 📝 `--dry-run` means "step 1 only, no DATA migration"; the chart
        #    file is step 1's deliverable and IS written when asked.
        if opts["write_chart"]:
            out = Path(opts["write_chart"])
            try:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text + "\n", encoding="utf-8")
            except OSError as exc:
                raise CommandError(
                    f"cannot write {out}: {type(exc).__name__}: {exc}"
                ) from None
            self.stderr.write(f"wrote {out}")
        if opts["dry_run"]:
            # 🔥 #310 battle B: stdout is the chart ONLY, so
            #    `--dry-run | python -m json.tool` (or `> chart.json`)
            #    works; the human recipe goes to stderr.
            self.stdout.write(text)
            self.stderr.write(
                RECIPE.format(label=opts["model"], field=opts["field"])
            )
            return
        self._check_target(model, opts)
        try:
            self._migrate(model, value_map, opts)
        except DatabaseError as exc:
            raise CommandError(
                f"{type(exc).__name__}: {exc} (is the database migrated? "
                f"run `manage.py migrate` after step 2)"
            ) from None

    def _check_target(self, model: Any, opts: Any) -> None:
        from ...fields import StatechartField
        from ...mixin import StatechartModelMixin
        from ._resolve import database

        if not issubclass(model, StatechartModelMixin):
            raise CommandError(
                f"{opts['model']} has no StatechartField yet (step 2); run "
                f"with --dry-run to see the chart and the recipe."
            )
        name = opts["statechart_field"]
        found = [
            f.name
            for f in model._meta.get_fields()
            if isinstance(f, StatechartField)
        ]
        if name not in found:
            raise CommandError(
                f"{model.__name__} has no StatechartField named {name!r}; "
                f"--statechart-field one of: {', '.join(found) or '(none)'}"
            )
        database(opts["database"])

    def _migrate(
        self, model: Any, value_map: Dict[str, str], opts: Any
    ) -> None:
        from ...fsm import migrate_rows

        sfield, fsm = opts["statechart_field"], opts["field"]
        using = opts["database"]
        mgr = model._base_manager.using(using)
        unknown: Dict[str, int] = {}
        failed: Dict[Any, str] = {}
        try:
            done, batches = migrate_rows(
                model,
                fsm,
                statechart_field=sfield,
                batch=opts["batch"],
                using=using,
                value_map=value_map,
                unknown=unknown,
                failed=failed,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        if failed:
            # 📝 a `context()` hook that raised for a row: the row is left
            #    empty and named -- the migration finishes the others.
            self.stderr.write(
                f"{len(failed)} row(s) failed to adopt and were left "
                "empty (fix and run again):"
            )
            for pk, err in list(failed.items())[:20]:
                self.stderr.write(f"  pk={pk!r}: {err}")
            if len(failed) > 20:
                self.stderr.write(f"  ... and {len(failed) - 20} more")
        remaining = mgr.filter(**{f"{sfield}__isnull": True}).count()
        skipped = sum(unknown.values())
        # 📝 skipped rows stay empty, so they are part of `remaining`;
        #    say so, so the numbers add up for the operator.
        tail = f" ({skipped} of them skipped, below)" if skipped else ""
        self.stdout.write(
            f"migrated {done} row(s) in {batches} batch(es); "
            f"{remaining} remaining{tail}"
        )
        if unknown:
            self.stdout.write(
                self.style.WARNING(
                    f"skipped {skipped} row(s) whose "
                    f"{fsm!r} value the chart does not know:"
                )
            )
            for value, n in sorted(unknown.items(), key=lambda kv: -kv[1]):
                self.stdout.write(f"  {value!r}: {n} row(s)")
            self.stdout.write(
                "fold renamed values in with --map OLD=NEW, or fix the "
                "data, then run again"
            )
        unused = _unused_map_keys(mgr, fsm, value_map)
        if unused:
            # 🔥 #310 battle B: a typo'd --map OLD silently did nothing.
            self.stdout.write(
                self.style.WARNING(
                    f"--map: no row has {fsm} = "
                    f"{', '.join(repr(u) for u in unused)} (typo?)"
                )
            )


def _unused_map_keys(
    mgr: Any, fsm: str, value_map: Dict[str, str]
) -> List[str]:
    return sorted(
        old for old in value_map if not mgr.filter(**{fsm: old}).exists()
    )


def _parse_map(items: Any) -> Dict[str, str]:
    """``["open=new", ...]`` → ``{"open": "new"}``; malformed or
    contradictory items are a `CommandError` before anything runs."""
    out: Dict[str, str] = {}
    for item in items:
        old_v, sep, new_v = item.partition("=")
        # 📝 an empty OLD is legal: `--map =new` folds empty-string rows.
        if not sep or not new_v or "=" in new_v:
            raise CommandError(f"--map expects OLD=NEW, got {item!r}")
        if out.get(old_v, new_v) != new_v:
            raise CommandError(
                f"--map {old_v}= given twice ({out[old_v]!r}, {new_v!r})"
            )
        out[old_v] = new_v
    return out
