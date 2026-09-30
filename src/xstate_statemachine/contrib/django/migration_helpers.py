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
) -> int:
    """Recompute ``<field>_state`` / ``_state_ids`` / ``_machine_version``
    for every row; returns how many rows changed.

    Args:
        migrate: Optional ``(snapshot) -> snapshot`` applied first (e.g.
            a `SnapshotMigrator` step renaming a state). A changed
            snapshot bumps ``<field>_version`` so an optimistic writer
            holding the old one conflicts instead of overwriting it.
    """
    if batch < 1:
        raise ValueError("batch must be >= 1")
    mgr = model._base_manager.using(using)
    vcol = f"{field}_version"
    changed = 0
    last = None
    while True:
        qs = mgr.order_by("pk")
        if last is not None:
            qs = qs.filter(pk__gt=last)
        rows = list(qs.only("pk", field, vcol)[:batch])
        if not rows:
            return changed
        for row in rows:
            last = row.pk
            snap = getattr(row, field)
            new_snap = migrate(dict(snap)) if (migrate and snap) else snap
            values = sibling_values(field, new_snap)
            if new_snap != snap:
                values[field] = new_snap
                values[vcol] = int(getattr(row, vcol) or 0) + 1
            changed += mgr.filter(pk=row.pk).update(**values)


def refresh_statechart_columns_op(
    app_label: str, model_name: str, field: str = "statechart"
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
        )

    return migrations.RunPython(forwards, migrations.RunPython.noop)
