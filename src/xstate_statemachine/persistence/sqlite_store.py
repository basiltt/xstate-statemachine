# src/xstate_statemachine/persistence/sqlite_store.py
# -----------------------------------------------------------------------------
# 🗄️ SQLiteStore -- a real database, in the stdlib (#259)
# -----------------------------------------------------------------------------
# 🏛️ Good for: one host, many processes (gunicorn workers, Celery + web),
#    durability, optimistic AND pessimistic locking, thousands of keys.
#    Not for: several hosts (use Redis #306 / Postgres via SQLAlchemy #276)
#    or a database on a network share (SQLite's own documentation says no;
#    we warn and fall back to `journal_mode=DELETE`, which is at least
#    consistent).
#
# 🔒 Optimistic: `UPDATE ... WHERE key=? AND version=?` -- the row count
#    tells us whether we won; there is no read-then-write window.
#    Pessimistic: `lock()` is `BEGIN IMMEDIATE` on a dedicated connection,
#    which takes SQLite's RESERVED lock -- every other writer waits (up to
#    `busy_timeout`) or gets `database is locked`, mapped to
#    `LockTimeoutError` (retryable) and never leaked as a bare
#    `sqlite3.OperationalError`.
#
# 🔐 X0 (#303): DB / -wal / -shm created 0600 (X0.10); an `xsm_schema`
#    table records the schema version with explicit upgrade steps (X0.15),
#    so a store written by 0.11 is upgraded, never guessed at, by 0.12.
#    Connection per thread (`sqlite3` objects are not shareable).
# -----------------------------------------------------------------------------
"""`SQLiteStore`: WAL-mode SQLite store with optimistic + pessimistic locks."""

from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
import time
import warnings
from pathlib import Path
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

from ..exceptions import (
    ConflictError,
    LockTimeoutError,
    SnapshotCorruptError,
    StoreError,
)
from .deadline import Deadline, check_deadline_record
from .store import BaseStore, check_record_fields

__all__ = ["SQLiteStore", "SCHEMA_VERSION"]

#: Bump with an entry in `_UPGRADES`. Never edit an existing step.
SCHEMA_VERSION = 1
_BUSY_TIMEOUT_S = 5.0

_CREATE_V1 = (
    """
    CREATE TABLE IF NOT EXISTS xsm_schema (
        version INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS statecharts (
        key             TEXT PRIMARY KEY,
        snapshot        TEXT NOT NULL,
        version         INTEGER NOT NULL,
        machine_version TEXT NOT NULL DEFAULT '',
        updated_at      REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deadlines (
        key         TEXT NOT NULL,
        state_id    TEXT NOT NULL,
        entry_seq   INTEGER NOT NULL,
        due_at_wall REAL NOT NULL,
        delay_ms    INTEGER NOT NULL,
        event_type  TEXT NOT NULL,
        FOREIGN KEY (key) REFERENCES statecharts(key) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS deadlines_due ON deadlines(due_at_wall)",
)

#: schema_version -> statements that bring it to schema_version + 1.
_UPGRADES: Dict[int, Tuple[str, ...]] = {}


def _is_locked_error(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


def _looks_like_network_path(path: Path) -> bool:
    s = str(path)
    return s.startswith("\\\\") or s.startswith("//")


class SQLiteStore(BaseStore):
    """SQLite-backed store; one connection per thread; WAL mode.

    Args:
        path: Database file (created if missing) or ``":memory:"`` for a
            private in-memory database (single connection; tests only).
        busy_timeout: Seconds a connection waits on a busy database before
            `LockTimeoutError`.
        journal_mode: ``"WAL"`` (default) or ``"DELETE"``; forced to
            ``DELETE`` with a warning on a UNC/network path.
    """

    backend = "sqlite"

    def __init__(
        self,
        path: Any,
        *,
        busy_timeout: float = _BUSY_TIMEOUT_S,
        journal_mode: str = "WAL",
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self.path = str(path)
        self.busy_timeout = float(busy_timeout)
        self._memory = self.path == ":memory:"
        if not self._memory and _looks_like_network_path(Path(self.path)):
            warnings.warn(
                f"SQLiteStore on a network path ({self.path}): SQLite "
                f"locking is unreliable over SMB/NFS. Falling back to "
                f"journal_mode=DELETE; prefer a local path or a server "
                f"database.",
                RuntimeWarning,
                stacklevel=2,
            )
            journal_mode = "DELETE"
        self.journal_mode = journal_mode.upper()
        self._local = threading.local()
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._init_lock = threading.Lock()
        self._ensure_schema()

    # -- connections --------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        # 🔐 X0.10: create the file 0600 BEFORE sqlite opens it, so the
        #    -wal / -shm siblings (which inherit the umask otherwise) and
        #    the DB itself are never world-readable.
        if not self._memory and not os.path.exists(self.path):
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(fd)
        conn = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout,
            isolation_level=None,  # autocommit; we manage BEGIN explicitly
            check_same_thread=False,
        )
        conn.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout * 1000)}")
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._memory:
            # 📝 `journal_mode` is PERSISTENT in the file, and changing it
            #    needs an exclusive lock -- so a second handle opening a
            #    database another connection is reading (a CLI against a
            #    live store, a second process) failed here with `database
            #    is locked` (seen on the Linux runners, #293's DLQ tests).
            #    Only switch when the file is not already in the requested
            #    mode, and if that switch is refused by a lock, keep the
            #    mode the file already has rather than fail to open.
            current = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
            if current.upper() != self.journal_mode:
                try:
                    conn.execute(f"PRAGMA journal_mode = {self.journal_mode}")
                except sqlite3.OperationalError as exc:
                    if not _is_locked_error(exc):
                        raise
                    warnings.warn(
                        f"SQLiteStore({self.path}): could not switch "
                        f"journal_mode {current} -> {self.journal_mode} "
                        "(database is locked by another connection); "
                        f"continuing with {current}.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _conn(self) -> sqlite3.Connection:
        if self._memory:
            # One shared connection: a second `:memory:` connection would
            # be a different database.
            if self._memory_conn is None:
                self._memory_conn = self._connect()
            return self._memory_conn
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _ensure_schema(self) -> None:
        with self._init_lock:
            try:
                conn = self._conn()
                self._ensure_schema_locked(conn)
            except sqlite3.DatabaseError as exc:
                # 🛡️ Battle #259 (X0.4): a file that is not a SQLite
                #    database -- or one another program wrote -- surfaced
                #    as a bare `sqlite3.DatabaseError` from the
                #    constructor (from the first PRAGMA in `_connect`, or
                #    from the schema statements). The caller asked for a
                #    store; the answer must be the store's own exception.
                if isinstance(exc, sqlite3.OperationalError) and (
                    _is_locked_error(exc)
                ):
                    raise LockTimeoutError("<db>", self.busy_timeout) from exc
                raise StoreError(
                    f"SQLiteStore cannot open {self.path!r}: {exc}"
                ) from exc
            if not self._memory and os.name == "posix":
                for suffix in ("", "-wal", "-shm"):
                    with contextlib.suppress(OSError):
                        os.chmod(self.path + suffix, 0o600)

    def _ensure_schema_locked(self, conn: sqlite3.Connection) -> None:
        with self._tx(conn, immediate=True):
            for stmt in _CREATE_V1:
                conn.execute(stmt)
            row = conn.execute("SELECT version FROM xsm_schema").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO xsm_schema(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                current = SCHEMA_VERSION
            else:
                current = int(row[0])
            if current > SCHEMA_VERSION:
                raise StoreError(
                    f"SQLiteStore schema is version {current}, newer "
                    f"than this library supports ({SCHEMA_VERSION}). "
                    f"Upgrade xstate-statemachine."
                )
            while current < SCHEMA_VERSION:
                for stmt in _UPGRADES[current]:
                    conn.execute(stmt)
                current += 1
                conn.execute("UPDATE xsm_schema SET version = ?", (current,))

    @contextlib.contextmanager
    def _tx(
        self, conn: sqlite3.Connection, *, immediate: bool = False
    ) -> Iterator[None]:
        # 🔁 Inside a `lock()` block this thread's connection is ALREADY in
        #    an IMMEDIATE transaction; nest into it (SQLite has no nested
        #    BEGIN) and let the lock's exit commit.
        if conn.in_transaction:
            yield
            return
        try:
            conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        except sqlite3.OperationalError as exc:
            if _is_locked_error(exc):
                raise LockTimeoutError("<db>", self.busy_timeout) from exc
            raise
        try:
            yield
        except BaseException:
            with contextlib.suppress(sqlite3.Error):
                conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")

    # -- primitives ---------------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        conn = self._conn()
        row = conn.execute(
            "SELECT snapshot, version, machine_version, updated_at "
            "FROM statecharts WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        # 🛡️ #303/#259 battle: a row another writer damaged (BLOB or
        #    non-UTF-8 snapshot, non-numeric version, NULL / text in a typed
        #    column -- SQLite's type affinity lets all of these in) is
        #    corruption, not a bare ValueError / AttributeError.
        check_record_fields(
            f"SQLiteStore row for {key!r}", row[0], row[1], row[2], row[3]
        )
        deadlines = []
        for r in conn.execute(
            "SELECT state_id, entry_seq, due_at_wall, delay_ms, event_type "
            "FROM deadlines WHERE key = ? ORDER BY due_at_wall",
            (key,),
        ):
            rec = dict(
                zip(
                    (
                        "state_id",
                        "entry_seq",
                        "due_at_wall",
                        "delay_ms",
                        "event_type",
                    ),
                    r,
                )
            )
            problem = check_deadline_record(rec)
            if problem is not None:
                raise SnapshotCorruptError(
                    f"SQLiteStore deadline row for {key!r}: {problem}."
                )
            deadlines.append(Deadline.from_dict(rec))
        return (row[0], int(row[1]), row[2], float(row[3]), deadlines)

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        conn = self._conn()
        now = time.time()
        try:
            with self._tx(conn, immediate=True):
                row = conn.execute(
                    "SELECT version FROM statecharts WHERE key = ?", (key,)
                ).fetchone()
                current = int(row[0]) if row else 0
                if (
                    expected_version is not None
                    and expected_version != current
                ):
                    raise ConflictError(
                        key, expected_version, current if row else None
                    )
                new_version = current + 1
                if row is None:
                    conn.execute(
                        "INSERT INTO statecharts"
                        "(key, snapshot, version, machine_version, updated_at)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (key, data, new_version, machine_version, now),
                    )
                else:
                    # 🔒 The conditional UPDATE is the real optimistic
                    #    check; the SELECT above only shapes the error.
                    cur = conn.execute(
                        "UPDATE statecharts SET snapshot=?, version=?, "
                        "machine_version=?, updated_at=? "
                        "WHERE key=? AND version=?",
                        (
                            data,
                            new_version,
                            machine_version,
                            now,
                            key,
                            current,
                        ),
                    )
                    if cur.rowcount != 1:  # pragma: no cover - IMMEDIATE tx
                        raise ConflictError(key, expected_version, None)
                conn.execute("DELETE FROM deadlines WHERE key = ?", (key,))
                if deadlines:
                    conn.executemany(
                        "INSERT INTO deadlines"
                        "(key, state_id, entry_seq, due_at_wall, delay_ms, "
                        "event_type) VALUES (?, ?, ?, ?, ?, ?)",
                        [
                            (
                                key,
                                d.state_id,
                                d.entry_seq,
                                d.due_at_wall,
                                d.delay_ms,
                                d.event_type,
                            )
                            for d in deadlines
                        ],
                    )
                return new_version
        except sqlite3.OperationalError as exc:
            if _is_locked_error(exc):
                raise LockTimeoutError(key, self.busy_timeout) from exc
            raise

    def _delete_raw(self, key: str) -> bool:
        conn = self._conn()
        with self._tx(conn, immediate=True):
            cur = conn.execute("DELETE FROM statecharts WHERE key = ?", (key,))
            return cur.rowcount > 0

    def _forget_raw(self, key: str) -> Dict[str, int]:
        conn = self._conn()
        with self._tx(conn, immediate=True):
            d = conn.execute(
                "DELETE FROM deadlines WHERE key = ?", (key,)
            ).rowcount
            s = conn.execute(
                "DELETE FROM statecharts WHERE key = ?", (key,)
            ).rowcount
            # 🔐 X0.5 (#303 battle): a `SQLiteLog` sharing this file keys
            #    its rows by the store key; `forget` left them behind
            #    (`SQLAlchemyStore.forget` already erased them).
            has_log = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='transitions'"
            ).fetchone()
            t = (
                conn.execute(
                    "DELETE FROM transitions WHERE machine_id = ?", (key,)
                ).rowcount
                if has_log
                else 0
            )
        return {"snapshots": s, "deadlines": d, "log_entries": t}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT key FROM statecharts WHERE substr(key, 1, ?) = ? "
            "ORDER BY key LIMIT ?",
            (len(prefix), prefix, limit),
        ).fetchall()
        return [r[0] for r in rows]

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._db_lock(key, timeout)

    @contextlib.contextmanager
    def _db_lock(self, key: str, timeout: float) -> Iterator[None]:
        """Pessimistic lock = this thread's connection holding BEGIN IMMEDIATE.

        Database-wide (SQLite has no row locks), which is the honest
        granularity; callers that need per-key concurrency use the
        optimistic path. Every `save` / `delete` this thread performs
        inside the block joins the same transaction and is committed when
        the block exits cleanly -- or rolled back if it raises, so a
        failed step never half-writes.
        """
        if self._memory:
            # A single shared connection cannot be reasoned about per
            # thread; a process lock gives the same exclusion.
            lk = self._init_lock
            if not lk.acquire(timeout=timeout):
                raise LockTimeoutError(key, timeout)
            try:
                yield
            finally:
                lk.release()
            return
        conn = self._conn()
        if conn.in_transaction:
            # Re-entrant use on the same thread: join the outer lock.
            yield
            return
        conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
        try:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if _is_locked_error(exc):
                    raise LockTimeoutError(key, timeout) from exc
                raise
            try:
                yield
            except BaseException:
                with contextlib.suppress(sqlite3.Error):
                    conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.execute(
                f"PRAGMA busy_timeout = {int(self.busy_timeout * 1000)}"
            )

    def health(self) -> Dict[str, Any]:
        try:
            conn = self._conn()
            n = conn.execute("SELECT count(*) FROM statecharts").fetchone()[0]
            jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
            return {
                "ok": True,
                "backend": self.backend,
                "path": self.path,
                "keys": int(n),
                "journal_mode": str(jm),
                "schema_version": SCHEMA_VERSION,
            }
        except sqlite3.Error as exc:
            return {"ok": False, "backend": self.backend, "error": str(exc)}

    def close(self) -> None:
        """Close this thread's connection (and the shared memory one)."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None
