# src/xstate_statemachine/contrib/sqlalchemy/mixin.py
# -----------------------------------------------------------------------------
# 🧬 StatechartMixin -- a statechart ON a mapped row, optimistic by default
# -----------------------------------------------------------------------------
# 🏛️ The snapshot lives in the business row (`statechart` column, a
#    `StatechartType`); four denormalised columns make it queryable:
#
#      statechart_state            "o.b.x.x1,o.b.y.y1"  (sorted leaf ids)
#      statechart_state_ids        ["o.b.x.x1", "o.b.y.y1"]
#      statechart_version          Integer -- `version_id_col` via optimistic()
#      statechart_machine_version  the chart's `version`
#
#    A `before_insert` / `before_update` mapper listener recomputes them
#    from the snapshot on EVERY flush, so a direct edit of `statechart`
#    cannot leave them stale. `send()` is create → act → persist → discard
#    on a `SyncInterpreter` against the row, flushed in the caller's
#    session: a `StaleDataError` from ``version_id_col`` becomes
#    `ConflictError`, and `send_with_retry` rolls back, reloads, retries.
#
# ⚠️ X0.3: under optimistic retry the machine's ACTIONS MAY RUN MORE THAN
#    ONCE per logical send -- side effects belong in services or an outbox.
# -----------------------------------------------------------------------------
"""`StatechartMixin`, `send_with_retry`, and the row-backed `StateStore`."""

from __future__ import annotations

import contextlib
import copy
import json
import time
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from sqlalchemy import JSON, Integer, String, event, insert, literal, or_
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import StaleDataError

from ...events import Receipt
from ...exceptions import ConflictError, LockTimeoutError
from ...models import MachineNode
from ...patterns.retry import RetryPolicy
from ...persistence.deadline import Deadline
from ...persistence.log import AuditPlugin, TransitionRecord
from . import _ops
from ._schema import build_tables

__all__ = ["StatechartMixin", "send_with_retry", "state_string"]

#: Separator of leaf ids in `statechart_state`. State ids never contain it
#: in practice; `in_state()` matches whole ids between separators.
SEP = ","
_LOCKS = ("optimistic", "pessimistic")
_RETRY_BACKOFF = RetryPolicy(
    max_attempts=8, base_ms=1.0, factor=2.0, max_ms=50.0, jitter="full"
)


def state_string(state_ids: Iterable[str]) -> str:
    """The `statechart_state` value for a set of leaf ids."""
    return SEP.join(sorted(state_ids))


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class _BufferLog:
    """A `TransitionLogStore` that buffers records until the flush."""

    def __init__(self, first_seq: Callable[[str], int]) -> None:
        self.records: List[TransitionRecord] = []
        self._first = first_seq

    def next_seq(self, machine_id: str) -> int:
        mine = [r for r in self.records if r.machine_id == machine_id]
        return (mine[-1].seq + 1) if mine else self._first(machine_id)

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        self.records.append(rec)

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:  # pragma: no cover - protocol filler
        return [r for r in self.records if r.machine_id == machine_id]

    def purge_older_than(self, cutoff_ts: float) -> int:  # pragma: no cover
        return 0

    def forget(self, machine_id: str) -> int:  # pragma: no cover
        return 0


@contextlib.contextmanager
def _joined(plugins: Iterable[Any], session: Any) -> Iterator[None]:
    """Bind every plugin sink's shared `SQLAlchemyStore` to *session*'s
    connection for the block (see `SQLAlchemyStore.bound_to`)."""
    from .store import SQLAlchemyStore

    stores: List[Any] = []
    for p in plugins:
        sink = getattr(p, "sink", None)
        shared = getattr(sink, "shares_connection_with", sink)
        if isinstance(shared, SQLAlchemyStore) and shared not in stores:
            stores.append(shared)
    if not stores:
        yield
        return
    with contextlib.ExitStack() as stack:
        conn = session.connection()
        for st in stores:
            stack.enter_context(st.bound_to(conn))
        yield


def _identity(row: Any) -> Any:
    state: Any = sa_inspect(row)
    return state.identity


class StatechartMixin:
    """Mix into a declarative model that declares a `StatechartType` column
    named ``statechart``.

    Class attributes:
        __xsm_machine__: A `MachineNode`, or ``(row) -> MachineNode``.
        __xsm_logic__: Optional `MachineLogic`, or ``(row) -> MachineLogic``,
            swapped onto (a shallow copy of) the machine per send.
        __xsm_audit__: ``True`` writes one ``xsm_transitions`` row per
            processed event IN THE SAME FLUSH as the state change (needs
            `xsm_sqlalchemy_ddl(Base.metadata)`).
    """

    __xsm_machine__: ClassVar[Any] = None
    __xsm_logic__: ClassVar[Any] = None
    __xsm_audit__: ClassVar[bool] = False

    statechart_state: Mapped[Optional[str]] = mapped_column(
        String(512), index=True, nullable=True
    )
    statechart_state_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )
    statechart_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    statechart_machine_version: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # -- declaration helpers ----------------------------------------------------
    @staticmethod
    def optimistic() -> Dict[str, Any]:
        """``__mapper_args__`` enabling optimistic locking on
        ``statechart_version`` (SQLAlchemy's ``version_id_col``)."""
        return {"version_id_col": StatechartMixin.statechart_version}

    @hybrid_property
    def state(self) -> Optional[str]:
        """The sorted, comma-joined leaf ids (SQL: the column)."""
        return self.statechart_state

    @classmethod
    def in_state(cls, *state_ids: str) -> Any:
        """A WHERE clause: rows where ANY of *state_ids* is active -- a leaf
        id or an ancestor of one (``in_state("o.b")`` matches ``o.b.x.x1``)::

            session.scalars(select(Order).where(Order.in_state("o.paid")))
        """
        if not state_ids:
            raise ValueError("in_state() needs at least one state id")
        col = literal(SEP) + cls.statechart_state + literal(SEP)
        clauses = []
        for sid in state_ids:
            e = _escape_like(sid)
            clauses.append(col.like(f"%{SEP}{e}{SEP}%", escape="\\"))
            clauses.append(col.like(f"%{SEP}{e}.%", escape="\\"))
        return or_(*clauses)

    # -- machine resolution -----------------------------------------------------
    def _xsm_machine(self) -> MachineNode[Any]:
        m = type(self).__xsm_machine__
        if m is None:
            raise TypeError(
                f"{type(self).__name__} must set __xsm_machine__ "
                f"(a MachineNode or a callable returning one)."
            )
        if not isinstance(m, MachineNode):
            m = m(self)
        logic = type(self).__xsm_logic__
        if logic is not None:
            if callable(logic) and not hasattr(logic, "actions"):
                logic = logic(self)
            m = copy.copy(m)
            m.logic = logic
        return m

    def _xsm_key(self) -> str:
        ident = _identity(self)
        if ident is None:
            raise ValueError("row has no primary key yet; flush it first")
        if len(ident) != 1:
            raise TypeError("StatechartMixin needs a single-column key")
        return str(ident[0])

    def _xsm_log_id(self) -> str:
        return f"{self.__table__.name}:{self._xsm_key()}"  # type: ignore

    @property
    def machine(self) -> Any:
        """A (not started) `SyncInterpreter` restored from the snapshot --
        read ``.context`` / ``.current_state_ids`` / ``.can()`` without
        sending anything."""
        from ...sync_interpreter import SyncInterpreter

        m = self._xsm_machine()
        snap = getattr(self, "statechart", None)
        if snap is None:
            return SyncInterpreter(m)
        return SyncInterpreter.from_snapshot(json.dumps(snap), m)

    # -- send ------------------------------------------------------------------
    def send(
        self,
        event_type: str,
        *,
        session: Any = None,
        lock: str = "optimistic",
        plugins: Iterable[Any] = (),
        **payload: Any,
    ) -> Receipt:
        """Apply *event_type* to this row's statechart and FLUSH.

        The caller commits. ``lock="pessimistic"`` re-selects the row
        ``FOR UPDATE`` first (Postgres / MySQL; SQLite serialises writers
        on its own). On a ``version_id_col`` conflict raises
        `ConflictError` -- the session's transaction must then be rolled
        back (`send_with_retry` does all of that).
        """
        if lock not in _LOCKS:
            raise ValueError(f"lock must be one of {_LOCKS}")
        session = session if session is not None else object_session(self)
        if session is None:
            raise ValueError(
                "send() needs session= (or a row attached to a Session)"
            )
        if object_session(self) is None:
            session.add(self)
        if _identity(self) is None:
            session.flush()  # a primary key for the deadline / log rows
        if lock == "pessimistic":
            session.refresh(self, with_for_update=True)
        key = self._xsm_key()
        expected = self.statechart_version
        plugins = list(plugins)
        try:
            # 🔒 #284 battle: a plugin sink that lives in a `SQLAlchemyStore`
            #    (outbox, inbox) joins THIS session's transaction, so a
            #    rollback drops its rows with the state change (X0.3).
            with _joined(plugins, session):
                receipt, snap, deadlines, records = self._xsm_run(
                    session, event_type, payload, plugins
                )
                self.statechart = snap
                session.flush()
                self._xsm_write_aux(
                    session.connection(), key, deadlines, records
                )
        except StaleDataError as exc:
            raise ConflictError(key, expected, None) from exc
        except OperationalError as exc:
            msg = str(getattr(exc, "orig", exc)).lower()
            if "locked" in msg or "busy" in msg:
                raise LockTimeoutError(key, 0.0) from exc
            raise
        return receipt

    @classmethod
    def _xsm_tables(cls) -> Any:
        """The extra's tables IF `xsm_sqlalchemy_ddl` put them on this
        model's metadata, else ``None``."""
        md = cls.metadata  # type: ignore[attr-defined]
        if "xsm_deadlines" not in md.tables:
            return None
        return build_tables(md)

    def _xsm_write_aux(
        self,
        conn: Any,
        key: str,
        deadlines: Sequence[Deadline],
        records: List[TransitionRecord],
    ) -> None:
        """Deadline index + audit rows, on the flush's connection -- so they
        commit (or roll back) with the state change."""
        tables = self._xsm_tables()
        if tables is None:
            # 📝 Without the DDL the deadlines still live INSIDE the
            #    snapshot (they resume when the row is next touched); only
            #    the scanner's index is absent. Audit was checked in _run.
            return
        source = self.__table__.name  # type: ignore[attr-defined]
        _ops.write_deadlines(conn, tables, source, key, deadlines)
        if records:
            conn.execute(
                insert(tables.transitions),
                [
                    {
                        "machine_id": r.machine_id,
                        "seq": r.seq,
                        "ts": r.ts,
                        "record": json.dumps(
                            r.to_dict(), sort_keys=True, default=str
                        ),
                    }
                    for r in records
                ],
            )

    def _xsm_run(
        self,
        session: Any,
        event_type: str,
        payload: Dict[str, Any],
        plugins: Iterable[Any],
    ) -> Tuple[Receipt, Dict[str, Any], Sequence[Deadline], list]:
        from ...sync_interpreter import SyncInterpreter

        m = self._xsm_machine()
        plugins = list(plugins)
        buffer: Optional[_BufferLog] = None
        if type(self).__xsm_audit__:
            tables = self._xsm_tables()
            if tables is None:
                raise TypeError(
                    f"{type(self).__name__}.__xsm_audit__ needs the "
                    f"xsm_transitions table: call "
                    f"xsm_sqlalchemy_ddl(Base.metadata)."
                )
            t = tables.transitions

            def first(mid: str) -> int:
                from sqlalchemy import func, select

                q = select(func.coalesce(func.max(t.c.seq), 0)).where(
                    t.c.machine_id == mid
                )
                return int(session.execute(q).scalar_one()) + 1

            buffer = _BufferLog(first)
            log_id = self._xsm_log_id()
            plugins.append(AuditPlugin(buffer, machine_id=lambda i: log_id))
        snap = getattr(self, "statechart", None)
        if snap is None:
            interp = SyncInterpreter(m)
            for p in plugins:
                interp.use(p)
        else:
            interp = SyncInterpreter.from_snapshot(
                json.dumps(snap),
                m,
                plugins=plugins,
                restart_timers="resume",
            )
        interp.store_key = self._xsm_key()
        interp.start()
        try:
            receipt = interp.send(event_type, wait=True, **payload)
            new_snap = json.loads(interp.get_snapshot())
            deadlines = tuple(interp._persist_deadlines())
        finally:
            interp.stop()
        return receipt, new_snap, deadlines, (buffer.records if buffer else [])

    def send_with_retry(
        self,
        event_type: str,
        *,
        session: Any = None,
        retries: int = 10,
        backoff: Optional[RetryPolicy] = None,
        lock: str = "optimistic",
        **payload: Any,
    ) -> Receipt:
        """`send()` retried on `ConflictError` / `LockTimeoutError`: roll the
        session back, reload the row, back off, re-apply."""
        return send_with_retry(
            self,
            event_type,
            session=session,
            retries=retries,
            backoff=backoff,
            lock=lock,
            **payload,
        )

    # -- scanner support ---------------------------------------------------------
    @classmethod
    def statechart_store(cls, session_factory: Any) -> Any:
        """A `StateStore` view over this model's rows (key = primary key
        as ``str``) -- hand it to `DueTimerScanner` so persisted ``after``
        deadlines fire for rows nobody touches."""
        from .model_store import ModelStore

        return ModelStore(session_factory, cls)


def send_with_retry(
    row: Any,
    event_type: str,
    *,
    session: Any = None,
    retries: int = 10,
    backoff: Optional[RetryPolicy] = None,
    lock: str = "optimistic",
    **payload: Any,
) -> Receipt:
    """Module-level form of `StatechartMixin.send_with_retry`.

    ⚠️ A retry ROLLS BACK the session's transaction (the only portable way
    to discard a stale read): call it on a session with no other pending
    work, then commit. Actions may run once per attempt (X0.3).
    """
    if retries < 0:
        raise ValueError("retries must be >= 0")
    session = session if session is not None else object_session(row)
    policy = backoff or _RETRY_BACKOFF
    attempt = 0
    while True:
        attempt += 1
        try:
            return row.send(event_type, session=session, lock=lock, **payload)
        except (ConflictError, LockTimeoutError) as exc:
            if attempt > retries:
                setattr(exc, "attempts", attempt)
                raise
            session.rollback()
            time.sleep(policy.delay_ms(min(attempt, 30)) / 1000.0)


# -----------------------------------------------------------------------------
# 🔁 Keep the denormalised columns true on every flush
# -----------------------------------------------------------------------------
def _sync_columns(mapper: Any, connection: Any, target: Any) -> None:
    snap = getattr(target, "statechart", None)
    if snap is None:
        target.statechart_state = None
        target.statechart_state_ids = None
        target.statechart_machine_version = None
        return
    ids = sorted(str(s) for s in (snap.get("state_ids") or ()))
    target.statechart_state = state_string(ids)
    target.statechart_state_ids = ids
    mv = snap.get("machine_version")
    target.statechart_machine_version = None if mv is None else str(mv)


def _before_update(mapper: Any, connection: Any, target: Any) -> None:
    _sync_columns(mapper, connection, target)
    if mapper.version_id_col is None:
        hist = sa_inspect(target).attrs.statechart.history
        if hist.has_changes():
            target.statechart_version = (target.statechart_version or 0) + 1


def _before_insert(mapper: Any, connection: Any, target: Any) -> None:
    _sync_columns(mapper, connection, target)
    if mapper.version_id_col is None and target.statechart_version is None:
        target.statechart_version = 0


event.listen(StatechartMixin, "before_insert", _before_insert, propagate=True)
event.listen(StatechartMixin, "before_update", _before_update, propagate=True)
