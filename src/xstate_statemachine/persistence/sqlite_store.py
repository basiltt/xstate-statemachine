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
import functools
import os
import sqlite3
import threading
import time
import warnings
from pathlib import Path
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    cast,
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
SCHEMA_VERSION = 2
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
    # 📈 #259 battle (CI, py3.12): `deadlines(key)` had no index, so every
    #    `load` (SELECT ... WHERE key), `save` (DELETE ... WHERE key) and
    #    `delete` (the FK cascade) did a full SCAN of `deadlines` -- O(n) in
    #    the store's deadline count: 114 us -> 308 us -> 1.1 ms per
    #    save+delete at 100 / 2 000 / 10 000 keys with one deadline each.
    "CREATE INDEX IF NOT EXISTS deadlines_key ON deadlines(key)",
)

#: schema_version -> statements that bring it to schema_version + 1.
_UPGRADES: Dict[int, Tuple[str, ...]] = {
    1: ("CREATE INDEX IF NOT EXISTS deadlines_key ON deadlines(key)",),
}

_F = TypeVar("_F", bound=Callable[..., Any])

#: Columns `_CREATE_V1` gives `statecharts`; anything else is not ours.
_STATECHARTS_COLUMNS = frozenset(
    {"key", "snapshot", "version", "machine_version", "updated_at"}
)


def _is_locked_error(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


def _looks_like_network_path(path: Path) -> bool:
    s = str(path)
    return s.startswith("\\\\") or s.startswith("//")


def _commit_or_rollback(conn: sqlite3.Connection) -> None:
    """``COMMIT``; if that fails, ``ROLLBACK`` and re-raise.

    🛡️ #259 battle: a failed ``COMMIT`` (``database or disk is full``,
    ``database is locked``) leaves the connection ``in_transaction``. Every
    later `_tx` on this thread then "joined" that dead transaction and
    never committed -- saves returned a version and were silently lost.
    """
    try:
        conn.execute("COMMIT")
    except BaseException:
        with contextlib.suppress(sqlite3.Error):
            conn.execute("ROLLBACK")
        raise


def _typed(exc: sqlite3.Error, key: str, timeout: float) -> StoreError:
    """Map a raw `sqlite3.Error` onto the documented store exceptions.

    🛡️ #259 battle: a non-SQLite file at *path* (``file is not a
    database``), a foreign ``statecharts`` table (``no such column``), a
    full disk at ``COMMIT`` (``database or disk is full``) or a read-only
    directory all escaped as bare `sqlite3.DatabaseError` /
    `OperationalError`, past ``except StoreError``.
    """
    if isinstance(exc, sqlite3.OperationalError) and _is_locked_error(exc):
        return LockTimeoutError(key, timeout)
    return StoreError(f"SQLiteStore: {type(exc).__name__}: {exc}")


def _sqlite_errors_typed(fn: _F) -> _F:
    @functools.wraps(fn)
    def wrapper(self: "SQLiteStore", *a: Any, **kw: Any) -> Any:
        try:
            return fn(self, *a, **kw)
        except sqlite3.Error as exc:
            key = a[0] if a and isinstance(a[0], str) else "<db>"
            raise _typed(exc, key, self.busy_timeout) from exc

    return cast(_F, wrapper)


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
                current = self._switch_journal_mode(conn, current)
                if current.upper() != self.journal_mode:
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

    def _switch_journal_mode(
        self, conn: sqlite3.Connection, current: str
    ) -> str:
        """Switch to `journal_mode`, retrying a lock for `busy_timeout`.

        🔥 battle #277-a: `uvicorn --workers 4` on an empty file (no
        `--role init`) had workers race the switch; a loser got `database
        is locked` at once and silently ran in rollback-journal mode for
        its lifetime (2 of 10 fleets) -- its writers then block readers.
        The racer switches the file within milliseconds, so re-read the
        mode and retry until the busy timeout. Returns the mode the file
        is in afterwards.
        """
        deadline = time.monotonic() + self.busy_timeout
        while True:
            try:
                row = conn.execute(
                    f"PRAGMA journal_mode = {self.journal_mode}"
                ).fetchone()
                return str(row[0]) if row else current
            except sqlite3.OperationalError as exc:
                if not _is_locked_error(exc):
                    raise
            current = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
            if (
                current.upper() == self.journal_mode
                or time.monotonic() >= deadline
            ):
                return current
            time.sleep(0.02)

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

    @_sqlite_errors_typed
    def _ensure_schema(self) -> None:
        with self._init_lock:
            conn = self._conn()
            with self._tx(conn, immediate=True):
                for stmt in _CREATE_V1:
                    conn.execute(stmt)
                cols = {
                    str(r[1])
                    for r in conn.execute("PRAGMA table_info(statecharts)")
                }
                if not _STATECHARTS_COLUMNS <= cols:
                    # 🛡️ #259 battle: a pre-existing, foreign `statecharts`
                    #    table made `CREATE ... IF NOT EXISTS` a no-op and
                    #    the first `load` died with `no such column`.
                    raise StoreError(
                        f"SQLiteStore({self.path}): table 'statecharts' "
                        f"exists with columns {sorted(cols)}, not the "
                        f"xstate-statemachine schema. Use another file."
                    )
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
                    conn.execute(
                        "UPDATE xsm_schema SET version = ?", (current,)
                    )
            if not self._memory and os.name == "posix":
                for suffix in ("", "-wal", "-shm"):
                    with contextlib.suppress(OSError):
                        os.chmod(self.path + suffix, 0o600)

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
            _commit_or_rollback(conn)

    # -- primitives ---------------------------------------------------------------------
    @_sqlite_errors_typed
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

    @_sqlite_errors_typed
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

    @_sqlite_errors_typed
    def _delete_raw(self, key: str) -> bool:
        conn = self._conn()
        with self._tx(conn, immediate=True):
            cur = conn.execute("DELETE FROM statecharts WHERE key = ?", (key,))
            return cur.rowcount > 0

    @_sqlite_errors_typed
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

    @_sqlite_errors_typed
    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, earliest due_at)`` for keys with a deadline at or before
        *until_wall*, earliest first, at most *limit* -- one query on the
        ``deadlines_due`` index instead of loading every record.

        🏛️ #264 battle (public-API widening, flagged): `DueTimerScanner`
        fell back to ``list_keys`` + one full ``load`` per record --
        100 000 records = 100 000 loads per tick, and only the first
        ``limit`` in KEY order were ever inspected.
        """
        if limit < 1:
            return []
        rows = (
            self._conn()
            .execute(
                "SELECT key, MIN(due_at_wall) AS first FROM deadlines "
                "WHERE due_at_wall <= ? GROUP BY key "
                "ORDER BY first, key LIMIT ?",
                (float(until_wall), int(limit)),
            )
            .fetchall()
        )
        return [(str(r[0]), float(r[1])) for r in rows]

    @_sqlite_errors_typed
    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT key FROM statecharts WHERE substr(key, 1, ?) = ? "
            "ORDER BY key LIMIT ?",
            (len(prefix), prefix, limit),
        ).fetchall()
        return [r[0] for r in rows]

    @_sqlite_errors_typed
    def _list_versions_raw(
        self, prefix: str, limit: int
    ) -> List[Tuple[str, str]]:
        # 📝 #263 battle: one SELECT over the label column; the snapshot
        #    blob is never read. A non-str label is corruption, as in load.
        rows = (
            self._conn()
            .execute(
                "SELECT key, machine_version FROM statecharts "
                "WHERE substr(key, 1, ?) = ? ORDER BY key LIMIT ?",
                (len(prefix), prefix, limit),
            )
            .fetchall()
        )
        for k, mv in rows:
            if not isinstance(mv, str):
                raise SnapshotCorruptError(
                    f"SQLiteStore row {k!r}: machine_version is "
                    f"{type(mv).__name__}, not str."
                )
        return [(r[0], r[1]) for r in rows]

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
            except sqlite3.Error as exc:
                raise _typed(exc, key, timeout) from exc
            try:
                yield
            except BaseException:
                with contextlib.suppress(sqlite3.Error):
                    conn.execute("ROLLBACK")
                raise
            else:
                try:
                    _commit_or_rollback(conn)
                except sqlite3.Error as exc:
                    raise _typed(exc, key, timeout) from exc
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
