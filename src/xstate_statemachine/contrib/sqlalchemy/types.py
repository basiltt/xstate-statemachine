# src/xstate_statemachine/contrib/sqlalchemy/types.py
# -----------------------------------------------------------------------------
# 🧾 StatechartType -- a snapshot column (JSON, JSONB on Postgres)
# -----------------------------------------------------------------------------
"""`StatechartType`: the column type for a stored snapshot dict."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from ...exceptions import SnapshotTooLargeError
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

__all__ = ["StatechartType"]


class StatechartType(TypeDecorator):  # type: ignore[type-arg]
    """A statechart snapshot stored as JSON (``JSONB`` on Postgres).

    The Python value is the snapshot DICT (``json.loads`` of
    ``get_snapshot()``) or ``None``. Values are size-checked on the way in
    AND out (X0.4, ``max_snapshot_bytes``, default 1 MiB) so a poisoned row
    cannot make a reader allocate unboundedly -- the bound applies to the
    re-serialised form, which is what every reader rebuilds an interpreter
    from. Hydration into an interpreter is lazy (``row.machine``).
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

    def _check(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise TypeError(
                "StatechartType stores a snapshot dict, got "
                f"{type(value).__name__}"
            )
        size = len(json.dumps(value, default=str).encode("utf-8"))
        if size > self.max_snapshot_bytes:
            raise SnapshotTooLargeError(
                "<column>", size, self.max_snapshot_bytes
            )
        return value

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[Any]:
        return self._check(value)

    def process_result_value(self, value: Any, dialect: Any) -> Optional[Any]:
        return self._check(value)
