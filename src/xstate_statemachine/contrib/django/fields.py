# src/xstate_statemachine/contrib/django/fields.py
# -----------------------------------------------------------------------------
# 🧾 StatechartField -- a snapshot column plus queryable siblings
# -----------------------------------------------------------------------------
# 🏛️ A `JSONField` holding the snapshot DICT, and -- added by
#    `contribute_to_class` so ``makemigrations`` sees ordinary fields --
#    four sibling columns (for a field named ``statechart``):
#
#      statechart_state            "o.b.x.x1,o.b.y.y1"  (sorted leaf ids)
#      statechart_state_ids        ["o.b.x.x1", "o.b.y.y1"]
#      statechart_version          PositiveInteger (optimistic fence)
#      statechart_machine_version  the chart's `version`
#
#    The column layout and the comma-joined ``_state`` string are the
#    SQLAlchemy extra's (`StatechartMixin`), so a team running both ORMs
#    reads one schema. ``filter(statechart__state=...)`` and
#    ``statechart__state__in=[...]`` compile to the indexed sibling column.
#
# 📝 Migrations: a migration lists the siblings explicitly, so when Django
#    renders a HISTORICAL model (module ``__fake__``) the field must not
#    add them a second time -- the one special case below.
#
# 🔐 X0.4: the snapshot is size-checked on write AND on read.
# -----------------------------------------------------------------------------
"""`StatechartField`."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Transform
from django.db.models.expressions import Col

from ...exceptions import SnapshotTooLargeError
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

__all__ = ["SIBLINGS", "StatechartField", "sibling_values", "state_string"]

#: Separator of leaf ids in ``<name>_state`` (shared with [sqlalchemy]).
SEP = ","
#: suffix -> purpose; the order is the order the columns are created in.
SIBLINGS = ("state", "state_ids", "version", "machine_version")


def state_string(state_ids: Any) -> Optional[str]:
    """The ``<name>_state`` value for a set of leaf ids."""
    ids = sorted(str(s) for s in (state_ids or ()))
    return SEP.join(ids) if ids else None


def sibling_values(
    name: str, snap: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """``{<name>_state, <name>_state_ids, <name>_machine_version}`` for a
    snapshot dict (the version column is the caller's to bump)."""
    if snap is None:
        return {
            f"{name}_state": None,
            f"{name}_state_ids": None,
            f"{name}_machine_version": None,
        }
    if not isinstance(snap, dict):
        raise ValidationError(
            f"{name} stores a snapshot dict, got {type(snap).__name__}"
        )
    ids: List[str] = sorted(str(s) for s in (snap.get("state_ids") or ()))
    mv = snap.get("machine_version")
    return {
        f"{name}_state": state_string(ids),
        f"{name}_state_ids": ids,
        f"{name}_machine_version": None if mv is None else str(mv),
    }


class _SiblingTransform(Transform):
    """``statechart__state`` → the ``statechart_state`` column itself."""

    sibling: str = ""

    def as_sql(self, compiler: Any, connection: Any) -> Any:
        field = self.lhs.output_field
        model = field.model
        target = model._meta.get_field(f"{field.name}_{self.sibling}")
        col = Col(self.lhs.alias, target)
        return compiler.compile(col)

    @property
    def output_field(self) -> Any:  # type: ignore[override]
        field = self.lhs.output_field
        return field.model._meta.get_field(f"{field.name}_{self.sibling}")


def _transform(suffix: str) -> Any:
    return type(
        f"Statechart{suffix.title().replace('_', '')}Transform",
        (_SiblingTransform,),
        {"sibling": suffix, "lookup_name": suffix},
    )


_TRANSFORMS = {s: _transform(s) for s in SIBLINGS}


class StatechartField(models.JSONField):
    """The statechart snapshot of a row (see module notes).

    Args:
        max_snapshot_bytes: X0.4 cap on the serialised snapshot (default
            1 MiB); enforced on save and on load.
        state_max_length: Width of ``<name>_state`` (default 512).
        denormalize: Add the sibling columns (default ``True``). Without
            them ``in_state()`` / ``__state`` lookups and the optimistic
            version fence are unavailable.
    """

    description = "Statechart snapshot (JSON) with denormalised state"

    def __init__(
        self,
        *args: Any,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        state_max_length: int = 512,
        denormalize: bool = True,
        **kwargs: Any,
    ) -> None:
        if max_snapshot_bytes < 1:
            raise ValueError("max_snapshot_bytes must be >= 1")
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("editable", False)
        self.max_snapshot_bytes = int(max_snapshot_bytes)
        self.state_max_length = int(state_max_length)
        self.denormalize = bool(denormalize)
        super().__init__(*args, **kwargs)

    # -- migrations -------------------------------------------------------------
    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        path = "xstate_statemachine.contrib.django.fields.StatechartField"
        for key, default in (("null", True), ("blank", True)):
            if kwargs.get(key) == default:
                kwargs.pop(key)
        if kwargs.get("editable", True) is False:
            kwargs.pop("editable", None)
        else:
            kwargs["editable"] = True
        if self.max_snapshot_bytes != DEFAULT_MAX_SNAPSHOT_BYTES:
            kwargs["max_snapshot_bytes"] = self.max_snapshot_bytes
        if self.state_max_length != 512:
            kwargs["state_max_length"] = self.state_max_length
        if not self.denormalize:
            kwargs["denormalize"] = False
        return name, path, args, kwargs

    def sibling_fields(self) -> Dict[str, models.Field]:  # type: ignore[type-arg]
        """Fresh instances of the sibling fields, keyed by column name."""
        n = self.name
        return {
            f"{n}_state": models.CharField(
                max_length=self.state_max_length,
                null=True,
                blank=True,
                db_index=True,
                editable=False,
            ),
            f"{n}_state_ids": models.JSONField(
                null=True, blank=True, editable=False
            ),
            f"{n}_version": models.PositiveIntegerField(
                default=0, editable=False
            ),
            f"{n}_machine_version": models.CharField(
                max_length=255, null=True, blank=True, editable=False
            ),
        }

    def contribute_to_class(
        self, cls: Any, name: str, *args: Any, **kwargs: Any
    ) -> None:
        super().contribute_to_class(cls, name, *args, **kwargs)
        if not self.denormalize or cls.__module__ == "__fake__":
            # 📝 Historical (migration) models list the siblings
            #    themselves; adding them again would duplicate columns.
            return
        existing = {f.name for f in cls._meta.local_fields}
        for col, field in self.sibling_fields().items():
            if col not in existing:
                cls.add_to_class(col, field)

    # -- lookups ------------------------------------------------------------------
    def get_transform(self, name: str) -> Any:
        if self.denormalize and name in _TRANSFORMS:
            return _TRANSFORMS[name]
        return super().get_transform(name)

    # -- values -------------------------------------------------------------------
    def _check(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise ValidationError(
                "StatechartField stores a snapshot dict, got "
                f"{type(value).__name__}"
            )
        size = len(json.dumps(value, default=str).encode("utf-8"))
        if size > self.max_snapshot_bytes:
            raise SnapshotTooLargeError(
                f"{getattr(self.model, '__name__', '?')}.{self.name}",
                size,
                self.max_snapshot_bytes,
            )
        return value

    def get_prep_value(self, value: Any) -> Any:
        return super().get_prep_value(self._check(value))

    def from_db_value(
        self, value: Any, expression: Any, connection: Any
    ) -> Any:
        return self._check(
            super().from_db_value(value, expression, connection)
        )
