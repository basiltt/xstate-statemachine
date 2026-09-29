# src/xstate_statemachine/contrib/sqlalchemy/store.py
# -----------------------------------------------------------------------------
# 🗄️ SQLAlchemyStore / AsyncSQLAlchemyStore -- the A2 contract on any RDBMS
# -----------------------------------------------------------------------------
# 🏛️ Good for: Postgres / MySQL / SQLite behind an app that already owns a
#    SQLAlchemy engine; many hosts; durable timers with an indexed scan.
#    Not for: a mapped business row that should carry its own statechart --
#    that is `StatechartMixin` (the snapshot lives ON the row).
#
# 🔒 Optimistic: a conditional ``UPDATE ... WHERE version=?`` (see
#    `_ops.save_raw`). Pessimistic: `lock(key)` is a LEASE row in
#    ``xsm_locks`` (insert-or-wait, reclaimed after ``lock_ttl_s``) -- portable
#    across dialects, and fenced: `PessimisticLock` still saves with
#    ``expected_version``, so an expired lease yields `ConflictError`, never
#    a lost update. Inside ``lock()`` every store / inbox / log call made by
#    this thread joins ONE transaction that commits when the block exits
#    (X0.3: the inbox mark and the audit rows commit with the save, or not
#    at all). `transaction()` gives the same grouping without a lease.
#
# 🔐 X0: key validation, size cap on save AND load (X0.4), `forget()` erases
#    the record, its deadlines, its lease AND its transition log (X0.5),
#    versioned schema with newer-refused (X0.10).
# -----------------------------------------------------------------------------
"""`SQLAlchemyStore` (sync) and `AsyncSQLAlchemyStore` (asyncio)."""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
import uuid
from typing import (
    Any,
    AsyncIterator,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from sqlalchemy import MetaData, func, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from ...exceptions import LockTimeoutError, SnapshotTooLargeError
from ...persistence.deadline import Deadline
from ...persistence.store import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    BaseStore,
    SnapshotCodec,
    StoredSnapshot,
    _IdentityCodec,
    validate_key,
)
from . import _ops
from ._schema import (
    DEFAULT_TABLE,
    SCHEMA_VERSION,
    XsmTables,
    build_tables,
    ensure_schema,
)

__all__ = ["AsyncSQLAlchemyStore", "SQLAlchemyStore"]

#: Poll interval while waiting for a lease held by someone else.
_LOCK_POLL_S = 0.01
#: A lease older than this is reclaimable (a crashed holder).
DEFAULT_LOCK_TTL_S = 60.0


class SQLAlchemyStore(BaseStore):
    """`StateStore` over a SQLAlchemy ``sessionmaker``.

    Args:
        session_factory: A ``sessionmaker`` (or any zero-arg callable that
            returns a `Session`). The store opens a short session per call.
        table: Snapshot table name (``xsm_snapshots``). The auxiliary
            tables (``xsm_deadlines``, ``xsm_locks``, ``xsm_inbox``,
            ``xsm_transitions``, ``xsm_schema``) are shared.
        metadata: Put the tables on YOUR metadata (Alembic); default: a
            private `MetaData`.
        create_tables: Create missing tables and record the schema version
            on construction (idempotent). Pass ``False`` when migrations own
            the DDL; the version check still runs.
        lock_ttl_s: Lease lifetime for `lock()`.
        codec / max_snapshot_bytes: As for every `BaseStore`.
    """

    backend = "sqlalchemy"

    def __init__(
        self,
        session_factory: Any,
        *,
        table: str = DEFAULT_TABLE,
        metadata: Optional[MetaData] = None,
        create_tables: bool = True,
        lock_ttl_s: float = DEFAULT_LOCK_TTL_S,
        codec: Optional[SnapshotCodec] = None,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        super().__init__(codec=codec, max_snapshot_bytes=max_snapshot_bytes)
        if lock_ttl_s <= 0:
            raise ValueError("lock_ttl_s must be > 0")
        self.session_factory = session_factory
        self.tables: XsmTables = build_tables(metadata or MetaData(), table)
        self.lock_ttl_s = float(lock_ttl_s)
        self._local = threading.local()
        with self._fresh() as conn:
            if create_tables:
                ensure_schema(conn, self.tables)
            else:
                self._check_version(conn)

    # -- connections / transactions -------------------------------------------
    @contextlib.contextmanager
    def _fresh(self) -> Iterator[Any]:
        """A NEW session + transaction, never the thread's shared one."""
        with self.session_factory() as session:
            with session.begin():
                yield session.connection()

    @contextlib.contextmanager
    def _tx(self) -> Iterator[Any]:
        """Join this thread's open `transaction()` if any, else a new one."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            yield conn
            return
        with self._fresh() as conn:
            yield conn

    @contextlib.contextmanager
    def transaction(self) -> Iterator[Any]:
        """Group every store / inbox / log call this thread makes into ONE
        database transaction, committed on clean exit, rolled back on an
        exception. Re-entrant. Yields the SQLAlchemy `Connection`."""
        if getattr(self._local, "conn", None) is not None:
            yield self._local.conn
            return
        with self._fresh() as conn:
            self._local.conn = conn
            try:
                yield conn
            finally:
                self._local.conn = None

    def _check_version(self, conn: Any) -> None:
        from ...exceptions import StoreError

        sc = self.tables.schema
        row = conn.execute(
            select(sc.c.version).where(sc.c.component == "sqlalchemy")
        ).first()
        if row is not None and int(row[0]) > SCHEMA_VERSION:
            raise StoreError(
                f"xstate-statemachine [sqlalchemy] schema is version "
                f"{row[0]}, newer than this library supports "
                f"({SCHEMA_VERSION}). Upgrade xstate-statemachine."
            )

    # -- primitives -------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        with self._tx() as conn:
            return _ops.load_raw(conn, self.tables, key)

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        try:
            with self._tx() as conn:
                return _ops.save_raw(
                    conn,
                    self.tables,
                    key,
                    data,
                    expected_version,
                    machine_version,
                    deadlines,
                )
        except OperationalError as exc:
            if _is_locked(exc):
                raise LockTimeoutError(key, 0.0) from exc
            raise

    def _delete_raw(self, key: str) -> bool:
        with self._tx() as conn:
            return _ops.delete_raw(conn, self.tables, key)

    def _forget_raw(self, key: str) -> Dict[str, int]:
        with self._tx() as conn:
            return _ops.forget_raw(conn, self.tables, key)

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        with self._tx() as conn:
            return _ops.list_keys_raw(conn, self.tables, prefix, limit)

    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, earliest due_at)`` from the deadline INDEX -- what
        `DueTimerScanner` uses instead of loading every record."""
        with self._tx() as conn:
            return _ops.due_keys_raw(
                conn,
                self.tables,
                self.tables.snapshots.name,
                until_wall,
                limit,
            )

    # -- pessimistic lease --------------------------------------------------------
    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._lease(key, timeout)

    def _held(self) -> set:
        held = getattr(self._local, "held", None)
        if held is None:
            held = self._local.held = set()
        return held

    @contextlib.contextmanager
    def _lease(self, key: str, timeout: float) -> Iterator[None]:
        held = self._held()
        if key in held:  # re-entrant on this thread
            yield
            return
        owner = uuid.uuid4().hex
        source = self.tables.snapshots.name
        deadline = time.monotonic() + timeout
        while True:
            try:
                with self._fresh() as conn:
                    got = _ops.try_lock(
                        conn, self.tables, source, key, owner, self.lock_ttl_s
                    )
            except OperationalError as exc:
                if not _is_locked(exc):
                    raise
                got = False
            if got:
                break
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            time.sleep(_LOCK_POLL_S)
        held.add(key)
        try:
            with self.transaction():
                yield
        finally:
            held.discard(key)
            with contextlib.suppress(SQLAlchemyError):
                with self._fresh() as conn:
                    _ops.unlock(conn, self.tables, source, key, owner)

    def health(self) -> Dict[str, Any]:
        try:
            with self._fresh() as conn:
                n = conn.execute(
                    select(func.count()).select_from(self.tables.snapshots)
                ).scalar_one()
                dialect = conn.dialect.name
            return {
                "ok": True,
                "backend": self.backend,
                "dialect": dialect,
                "table": self.tables.snapshots.name,
                "keys": int(n),
                "schema_version": SCHEMA_VERSION,
            }
        except SQLAlchemyError as exc:
            return {
                "ok": False,
                "backend": self.backend,
                "error": type(exc).__name__,
            }


def _is_locked(exc: BaseException) -> bool:
    msg = str(getattr(exc, "orig", exc)).lower()
    return "locked" in msg or "busy" in msg


# -----------------------------------------------------------------------------
# ⚡ AsyncSQLAlchemyStore
# -----------------------------------------------------------------------------
class AsyncSQLAlchemyStore:
    """`AsyncStateStore` over an ``async_sessionmaker``.

    The statements are the SAME functions `SQLAlchemyStore` runs, executed
    through ``AsyncSession.run_sync`` -- one semantics, two drivers.
    `lock()` is the same lease, polled with ``asyncio.sleep``; unlike the
    sync store it does NOT open a shared transaction (each call commits).

    Tables are created lazily on first use (or call `create_all()`).
    """

    backend = "sqlalchemy-async"

    def __init__(
        self,
        async_session_factory: Any,
        *,
        table: str = DEFAULT_TABLE,
        metadata: Optional[MetaData] = None,
        create_tables: bool = True,
        lock_ttl_s: float = DEFAULT_LOCK_TTL_S,
        codec: Optional[SnapshotCodec] = None,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        if max_snapshot_bytes < 1:
            raise ValueError("max_snapshot_bytes must be >= 1")
        if lock_ttl_s <= 0:
            raise ValueError("lock_ttl_s must be > 0")
        self.session_factory = async_session_factory
        self.tables = build_tables(metadata or MetaData(), table)
        self.create_tables = bool(create_tables)
        self.lock_ttl_s = float(lock_ttl_s)
        self.codec: SnapshotCodec = codec or _IdentityCodec()
        self.max_snapshot_bytes = int(max_snapshot_bytes)
        self._ready = False
        # 📝 Created lazily: on 3.9 `asyncio.Lock()` binds to the loop
        #    current at construction (#334).
        self._init_lock: Optional[asyncio.Lock] = None

    async def create_all(self) -> None:
        """Create missing tables / check the schema version (idempotent)."""
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
        async with self._init_lock:
            if self._ready:
                return
            await self._call(
                lambda conn: ensure_schema(conn, self.tables), ensure=False
            )
            self._ready = True

    async def _call(self, fn: Any, *, ensure: bool = True) -> Any:
        if ensure and not self._ready and self.create_tables:
            await self.create_all()
        async with self.session_factory() as session:
            async with session.begin():
                return await session.run_sync(lambda s: fn(s.connection()))

    def _check_size(self, key: str, data: str) -> None:
        size = len(data.encode("utf-8"))
        if size > self.max_snapshot_bytes:
            raise SnapshotTooLargeError(key, size, self.max_snapshot_bytes)

    async def load(self, key: str) -> Optional[StoredSnapshot]:
        validate_key(key)
        raw = await self._call(lambda c: _ops.load_raw(c, self.tables, key))
        if raw is None:
            return None
        data, version, mv, updated_at, deadlines = raw
        self._check_size(key, data)
        return StoredSnapshot(
            key=key,
            snapshot=self.codec.decode(data),
            version=version,
            machine_version=mv,
            updated_at=updated_at,
            deadlines=tuple(deadlines),
        )

    async def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        validate_key(key)
        if not isinstance(snapshot, str):
            raise TypeError(
                "snapshot must be the JSON str from get_snapshot()"
            )
        if expected_version is not None and expected_version < 0:
            raise ValueError("expected_version must be >= 0 or None")
        data = self.codec.encode(snapshot)
        self._check_size(key, data)
        dl = tuple(deadlines)
        return int(
            await self._call(
                lambda c: _ops.save_raw(
                    c,
                    self.tables,
                    key,
                    data,
                    expected_version,
                    machine_version or "",
                    dl,
                )
            )
        )

    async def delete(self, key: str) -> bool:
        validate_key(key)
        return bool(
            await self._call(lambda c: _ops.delete_raw(c, self.tables, key))
        )

    async def forget(self, key: str) -> Dict[str, int]:
        validate_key(key)
        return dict(
            await self._call(lambda c: _ops.forget_raw(c, self.tables, key))
        )

    async def list_keys(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[str]:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        return list(
            await self._call(
                lambda c: _ops.list_keys_raw(c, self.tables, prefix, limit)
            )
        )

    async def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        src = self.tables.snapshots.name
        return list(
            await self._call(
                lambda c: _ops.due_keys_raw(
                    c, self.tables, src, until_wall, limit
                )
            )
        )

    def lock(self, key: str, *, timeout: float = 10.0) -> Any:
        validate_key(key)
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        return self._alease(key, timeout)

    @contextlib.asynccontextmanager
    async def _alease(self, key: str, timeout: float) -> AsyncIterator[None]:
        owner = uuid.uuid4().hex
        src = self.tables.snapshots.name
        deadline = time.monotonic() + timeout
        while True:
            try:
                got = await self._call(
                    lambda c: _ops.try_lock(
                        c, self.tables, src, key, owner, self.lock_ttl_s
                    )
                )
            except OperationalError as exc:
                if not _is_locked(exc):
                    raise
                got = False
            if got:
                break
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            await asyncio.sleep(_LOCK_POLL_S)
        try:
            yield
        finally:
            with contextlib.suppress(SQLAlchemyError):
                await self._call(
                    lambda c: _ops.unlock(c, self.tables, src, key, owner)
                )

    async def health(self) -> Dict[str, Any]:
        try:
            n = await self._call(
                lambda c: c.execute(
                    select(func.count()).select_from(self.tables.snapshots)
                ).scalar_one()
            )
            return {
                "ok": True,
                "backend": self.backend,
                "keys": int(n),
                "schema_version": SCHEMA_VERSION,
            }
        except SQLAlchemyError as exc:
            return {
                "ok": False,
                "backend": self.backend,
                "error": type(exc).__name__,
            }
