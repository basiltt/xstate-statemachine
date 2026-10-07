# src/xstate_statemachine/contrib/django/migration_helpers.py
# -----------------------------------------------------------------------------
# 🧰 Data-migration helpers
# -----------------------------------------------------------------------------
# 🏛️ `refresh_statechart_columns` recomputes the denormalised siblings from
#    the snapshot -- run it (``migrations.RunPython``) after a chart change
#    renamed states, or after a bulk import that wrote the JSON column
#    directly. Works on HISTORICAL models (``apps.get_model``), which carry
#    the fields but not the mixin's methods, so it is plain column math.
# -----------------------------------------------------------------------------
"""`refresh_statechart_columns`, `refresh_statechart_columns_op`."""

from __future__ import annotations

import copy
from typing import Any, Callable, Optional

from .fields import sibling_values

__all__ = ["refresh_statechart_columns", "refresh_statechart_columns_op"]


def refresh_statechart_columns(
    model: Any,
    field: str = "statechart",
    *,
    using: str = "default",
    batch: int = 1000,
    migrate: Optional[Callable[[dict], dict]] = None,
    dry_run: bool = False,
) -> int:
    """Recompute ``<field>_state`` / ``_state_ids`` / ``_machine_version``
    for every row; returns how many rows changed (or, with *dry_run*,
    WOULD change -- nothing is written).

    Rows are read in primary-key batches of *batch* (keyset pagination),
    so memory stays bounded on any table size. A row whose columns are
    already right is not written and not counted.

    Args:
        migrate: Optional ``(snapshot) -> snapshot`` applied first (e.g.
            a `SnapshotMigrator` step renaming a state). It receives a
            DEEP copy, so mutating nested dicts in place is fine. A
            changed snapshot bumps ``<field>_version`` so an optimistic
            writer holding the old one conflicts instead of overwriting.
    """
    if batch < 1:
        raise ValueError("batch must be >= 1")
    mgr = model._base_manager.using(using)
    vcol = f"{field}_version"
    cols = list(sibling_values(field, None))
    changed = 0
    last = None
    while True:
        qs = mgr.order_by("pk")
        if last is not None:
            qs = qs.filter(pk__gt=last)
        rows = list(qs.only("pk", field, vcol, *cols)[:batch])
        if not rows:
            return changed
        for row in rows:
            last = row.pk
            values = _row_update(row, field, vcol, cols, migrate)
            if not values:
                continue
            if dry_run:
                changed += 1
            else:
                changed += mgr.filter(pk=row.pk).update(**values)


def _row_update(
    row: Any,
    field: str,
    vcol: str,
    cols: list,
    migrate: Optional[Callable[[dict], dict]],
) -> dict:
    """The column values to write for *row* (empty: already right)."""
    snap = getattr(row, field)
    # 🔥 #280 battle: a shallow ``dict(snap)`` let a migrate step that
    #    mutated ``snap["context"]`` in place change the "old" snapshot
    #    too -- the comparison saw no change and the rewrite was lost.
    new_snap = migrate(copy.deepcopy(snap)) if (migrate and snap) else snap
    values = sibling_values(field, new_snap)
    if new_snap != snap:
        values[field] = new_snap
        values[vcol] = int(getattr(row, vcol) or 0) + 1
        return values
    return {k: v for k, v in values.items() if getattr(row, k) != v}


def refresh_statechart_columns_op(
    app_label: str,
    model_name: str,
    field: str = "statechart",
    *,
    batch: int = 1000,
    migrate: Optional[Callable[[dict], dict]] = None,
) -> Any:
    """A ``migrations.RunPython`` operation wrapping the helper::

    operations = [refresh_statechart_columns_op("shop", "Order")]
    """
    from django.db import migrations

    def forwards(apps: Any, schema_editor: Any) -> None:
        refresh_statechart_columns(
            apps.get_model(app_label, model_name),
            field,
            using=schema_editor.connection.alias,
            batch=batch,
            migrate=migrate,
        )

    return migrations.RunPython(forwards, migrations.RunPython.noop)
