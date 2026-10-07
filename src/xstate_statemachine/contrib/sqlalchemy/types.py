# src/xstate_statemachine/contrib/sqlalchemy/types.py
# -----------------------------------------------------------------------------
# 🧾 StatechartType -- a snapshot column (JSON, JSONB on Postgres)
# -----------------------------------------------------------------------------
# 🏛️ #284 battle (adversary B):
#    * errors raised here are `DontWrapMixin`, so the mixin path raises the
#      SAME `SnapshotTooLargeError` the store path does (it used to arrive
#      wrapped in SQLAlchemy's ``StatementError``), and a corrupt blob is
#      `SnapshotCorruptError`, never a bare ``JSONDecodeError``;
#    * `compare_against_backend` + `render_statechart_type` make Alembic
#      autogenerate quiet on Postgres (it saw JSONB vs JSON as a diff).
# -----------------------------------------------------------------------------
"""`StatechartType`: the column type for a stored snapshot dict."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DontWrapMixin
from sqlalchemy.types import TypeDecorator

from ...exceptions import SnapshotCorruptError, SnapshotTooLargeError
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

__all__ = ["StatechartType", "render_statechart_type"]

#: What Alembic writes for a `StatechartType` column (see
#: `render_statechart_type`): JSON everywhere, JSONB on Postgres -- the
#: same DDL `create_all` emits, so autogenerate sees no diff on either.
RENDERED = 'sa.JSON().with_variant(postgresql.JSONB(), "postgresql")'


class _ColumnTooLarge(SnapshotTooLargeError, DontWrapMixin):
    """`SnapshotTooLargeError` that SQLAlchemy does not wrap in
    ``StatementError``."""


class _ColumnCorrupt(SnapshotCorruptError, DontWrapMixin):
    """A ``statechart`` value that is not a JSON object."""


class StatechartType(TypeDecorator):  # type: ignore[type-arg]
    """A statechart snapshot stored as JSON (``JSONB`` on Postgres).

    The Python value is the snapshot DICT (``json.loads`` of
    ``get_snapshot()``) or ``None``. Values are size-checked on the way in
    AND out (X0.4, ``max_snapshot_bytes``, default 1 MiB) so a poisoned row
    cannot make a reader allocate unboundedly -- the bound applies to the
    re-serialised form, which is what every reader rebuilds an interpreter
    from. Over the limit is `SnapshotTooLargeError`; a stored value that is
    not a JSON object is `SnapshotCorruptError`. Hydration into an
    interpreter is lazy (``row.machine``).
    """

    impl = JSON().with_variant(JSONB(), "postgresql")
    cache_ok = True

    def __init__(
        self, *args: Any, max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES
    ) -> None:
        super().__init__(*args)
        if max_snapshot_bytes < 1:
            raise ValueError("max_snapshot_bytes must be >= 1")
        self.max_snapshot_bytes = int(max_snapshot_bytes)

    def _check(self, value: Any, *, reading: bool) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise _ColumnCorrupt(
                    f"statechart column holds invalid JSON: {exc}"
                ) from exc
        if not isinstance(value, dict):
            msg = (
                "StatechartType stores a snapshot dict, got "
                f"{type(value).__name__}"
            )
            # 📝 Writing a non-dict is a programming error; READING one
            #    means the row is corrupt.
            if reading:
                raise _ColumnCorrupt(msg)
            raise TypeError(msg)
        size = len(json.dumps(value, default=str).encode("utf-8"))
        if size > self.max_snapshot_bytes:
            raise _ColumnTooLarge(
                "<statechart column>", size, self.max_snapshot_bytes
            )
        return value

    def compare_against_backend(self, dialect: Any, conn_type: Any) -> Any:
        """Alembic autogenerate: a JSONB column on Postgres (JSON
        elsewhere) IS this type -- no spurious ``modify_type``."""
        if dialect.name == "postgresql":
            return isinstance(conn_type, JSONB)
        return isinstance(conn_type, JSON) or None

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[Any]:
        return self._check(value, reading=False)

    def process_result_value(self, value: Any, dialect: Any) -> Optional[Any]:
        return self._check(value, reading=True)


def render_statechart_type(type_: str, obj: Any, autogen_context: Any) -> Any:
    """An Alembic ``render_item`` hook rendering `StatechartType` as
    ``sa.JSON().with_variant(postgresql.JSONB(), "postgresql")``::

        context.configure(..., render_item=render_statechart_type)

    Returns ``False`` for everything else (Alembic's default rendering).
    """
    if type_ == "type" and isinstance(obj, StatechartType):
        autogen_context.imports.add(
            "from sqlalchemy.dialects import postgresql"
        )
        return RENDERED
    return False
