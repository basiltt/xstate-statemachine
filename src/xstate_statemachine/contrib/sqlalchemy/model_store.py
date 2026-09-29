# src/xstate_statemachine/contrib/sqlalchemy/model_store.py
# -----------------------------------------------------------------------------
# ⏰ ModelStore -- a `StateStore` view over `StatechartMixin` rows
# -----------------------------------------------------------------------------
# 🏛️ Exists so the stock `DueTimerScanner` (and `persisted()`) can drive a
#    mapped model's rows: a key is the row's primary key as ``str``; the
#    snapshot is the ``statechart`` column; the version is
#    ``statechart_version``; deadlines are the ``xsm_deadlines`` rows whose
#    ``source`` is the model's table. Writes are a conditional Core UPDATE
#    (``WHERE statechart_version = expected``) that also refreshes the
#    denormalised columns -- the same fence the ORM's ``version_id_col``
#    applies, so a scanner and a web request racing on one row cannot lose
#    an update. Rows are never created or deleted through this view.
# -----------------------------------------------------------------------------
"""`ModelStore`: `StatechartMixin.statechart_store()`."""

from __future__ import annotations

import contextlib
import json
import time
from typing import (
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from sqlalchemy import String, cast, delete, func, select, update

from ...exceptions import ConflictError
from ...persistence.deadline import Deadline
from ...persistence.store import BaseStore
from . import _ops
from ._schema import build_tables

__all__ = ["ModelStore"]


class ModelStore(BaseStore):
    """Row-backed store for a `StatechartMixin` model (see module notes).

    `lock()` is a no-op context (row locks belong to the caller's own
    session); use the default `OptimisticLock` with it.
    """

    backend = "sqlalchemy-model"

    def __init__(self, session_factory: Any, model: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self.session_factory = session_factory
        self.model = model
        self.table = model.__table__
        pk = list(self.table.primary_key.columns)
        if len(pk) != 1:
            raise TypeError("ModelStore needs a single-column primary key")
        self.pk = pk[0]
        md = model.metadata
        if "xsm_deadlines" not in md.tables:
            raise TypeError(
                f"{model.__name__}: call xsm_sqlalchemy_ddl(Base.metadata) "
                f"so the deadline index table exists."
            )
        self.tables = build_tables(md)

    @contextlib.contextmanager
    def _tx(self) -> Iterator[Any]:
        with self.session_factory() as session:
            with session.begin():
                yield session.connection()

    def _pk_value(self, key: str) -> Any:
        try:
            ptype = self.pk.type.python_type
        except NotImplementedError:  # pragma: no cover - exotic types
            return key
        return ptype(key) if ptype is not str else key

    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        t = self.table
        with self._tx() as conn:
            row = conn.execute(
                select(t.c.statechart, t.c.statechart_version).where(
                    self.pk == self._pk_value(key)
                )
            ).first()
            if row is None or row[0] is None:
                return None
            snap = row[0]
            d = self.tables.deadlines
            deadlines = [
                Deadline(r[0], int(r[1]), float(r[2]), int(r[3]), r[4])
                for r in conn.execute(
                    select(
                        d.c.state_id,
                        d.c.entry_seq,
                        d.c.due_at_wall,
                        d.c.delay_ms,
                        d.c.event_type,
                    )
                    .where(d.c.source == t.name, d.c.key == key)
                    .order_by(d.c.due_at_wall, d.c.id)
                )
            ]
        mv = snap.get("machine_version") if isinstance(snap, dict) else None
        return (
            json.dumps(snap),
            int(row[1] or 0),
            "" if mv is None else str(mv),
            float(snap.get("taken_at") or time.time()),
            deadlines,
        )

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        from .mixin import state_string

        t = self.table
        snap = json.loads(data)
        ids = sorted(str(s) for s in (snap.get("state_ids") or ()))
        with self._tx() as conn:
            row = conn.execute(
                select(t.c.statechart_version).where(
                    self.pk == self._pk_value(key)
                )
            ).first()
            if row is None:
                raise ConflictError(key, expected_version, None)
            current = int(row[0] or 0)
            if expected_version is not None and expected_version != current:
                raise ConflictError(key, expected_version, current)
            res = conn.execute(
                update(t)
                .where(
                    self.pk == self._pk_value(key),
                    t.c.statechart_version == current,
                )
                .values(
                    statechart=snap,
                    statechart_state=state_string(ids),
                    statechart_state_ids=ids,
                    statechart_machine_version=machine_version or None,
                    statechart_version=current + 1,
                )
            )
            if res.rowcount != 1:
                raise ConflictError(key, expected_version, None)
            _ops.write_deadlines(conn, self.tables, t.name, key, deadlines)
        return current + 1

    def _delete_raw(self, key: str) -> bool:
        raise NotImplementedError(
            "ModelStore never deletes rows; delete the model instance."
        )

    def _forget_raw(self, key: str) -> Dict[str, int]:
        """Erase the auxiliary rows (deadlines, transition log) of *key*;
        the business row itself is the application's to delete."""
        with self._tx() as conn:
            d = self.tables.deadlines
            n = conn.execute(
                delete(d).where(d.c.source == self.table.name, d.c.key == key)
            ).rowcount
            tr = self.tables.transitions
            lg = conn.execute(
                delete(tr).where(tr.c.machine_id == f"{self.table.name}:{key}")
            ).rowcount
        return {"snapshots": 0, "deadlines": int(n), "log_entries": int(lg)}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        k = cast(self.pk, String)
        q = select(k).where(self.table.c.statechart.is_not(None))
        if prefix:
            q = q.where(func.substr(k, 1, len(prefix)) == prefix)
        with self._tx() as conn:
            return [
                str(r[0]) for r in conn.execute(q.order_by(k).limit(limit))
            ]

    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        with self._tx() as conn:
            return _ops.due_keys_raw(
                conn, self.tables, self.table.name, until_wall, limit
            )

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return contextlib.nullcontext()
