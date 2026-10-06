"""#277 battle (A): racing processes switching an empty file to WAL.

`uvicorn --workers 4` without `--role init`: every worker opens the empty
file and asks for WAL; a worker that lost the race got `database is
locked` at once and ran in rollback-journal mode for its whole life (2 of
10 fleets) -- silently, with a warning in a log nobody reads. The switch
now retries for `busy_timeout`, and re-reads the mode the winner set.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import warnings
from pathlib import Path

from src.xstate_statemachine.persistence import SQLiteStore


def _rollback_journal_file(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("CREATE TABLE IF NOT EXISTS t(x)")
    conn.commit()
    conn.close()


def test_a_briefly_locked_file_still_ends_up_in_wal(tmp_path: Path) -> None:
    path = tmp_path / "s.db"
    _rollback_journal_file(path)
    holder = sqlite3.connect(
        str(path), isolation_level=None, check_same_thread=False
    )
    # 🔥 a RESERVED (writer) lock -- another worker inside
    #    `_ensure_schema`'s BEGIN IMMEDIATE. SQLite's busy handler does
    #    NOT wait for this one: the old code failed in 0 ms.
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO t VALUES (1)")

    def release() -> None:
        time.sleep(0.3)
        holder.execute("COMMIT")

    t = threading.Thread(target=release)
    t.start()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # 🔥 no "could not switch"
            store = SQLiteStore(path, busy_timeout=5.0)
        conn = store._conn()
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        store.close()
    finally:
        t.join()
        holder.close()


def test_the_racer_that_switched_first_is_accepted(tmp_path: Path) -> None:
    """The lock clears because ANOTHER process switched to WAL: the
    re-read sees `wal` and the store opens without a warning."""
    path = tmp_path / "s.db"
    _rollback_journal_file(path)
    holder = sqlite3.connect(
        str(path), isolation_level=None, check_same_thread=False
    )
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO t VALUES (1)")

    def switch() -> None:
        time.sleep(0.3)
        holder.execute("COMMIT")
        holder.execute("PRAGMA journal_mode = WAL")

    t = threading.Thread(target=switch)
    t.start()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            store = SQLiteStore(path, busy_timeout=5.0)
        conn = store._conn()
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        store.close()
    finally:
        t.join()
        holder.close()


def test_four_threads_open_an_empty_file_concurrently(tmp_path: Path) -> None:
    """The in-process shape of four workers starting at once."""
    path = tmp_path / "s.db"
    errors: list = []
    modes: list = []
    barrier = threading.Barrier(4)

    def open_one() -> None:
        try:
            barrier.wait()
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                s = SQLiteStore(path, busy_timeout=5.0)
            modes.append(
                s._conn().execute("PRAGMA journal_mode").fetchone()[0]
            )
            s.close()
        except BaseException as exc:  # noqa: BLE001 -- collected
            errors.append(exc)

    threads = [threading.Thread(target=open_one) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    assert errors == []
    assert modes == ["wal"] * 4
