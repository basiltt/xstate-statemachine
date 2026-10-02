# tests/persistence/test_battle_259_stores_crash_concurrency.py
# -----------------------------------------------------------------------------
# ⚔️ Battle test #259 part A -- crash consistency, concurrency, filesystem
#    edge cases for MemoryStore / FileStore / SQLiteStore / as_async.
# -----------------------------------------------------------------------------
# 🏛️ Oracle: docs/_guide/guarantees.md ("Crash windows, one by one") and
#    docs/_guide/persistence.md ("Safety rails", "Concurrency"). Real
#    process kills go through a subprocess that `os._exit`s at an injected
#    point; everything else is deterministic fault injection. Windows
#    semantics (sharing violations, reserved names, case folding, 255-char
#    components, msvcrt locks) are exercised for real on a Windows host.
#
# 📝 Stress sizes are small by default (PR budget < 120 s); set
#    XSM_STRESS_SAVES=200 for the full 16 x 200 run.
# -----------------------------------------------------------------------------
"""Battle tests for #259 stores: crash consistency and concurrency."""

from __future__ import annotations

import asyncio
import contextlib
import errno
import faulthandler
import gc
import os
import pathlib
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from typing import Any, Callable, List, Optional
from unittest import mock

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    ConflictError,
    InvalidKeyError,
    LockTimeoutError,
    StoreError,
)
from src.xstate_statemachine.patterns.retry import RetryPolicy
from src.xstate_statemachine.persistence import (
    FileStore,
    MemoryStore,
    OptimisticLock,
    PessimisticLock,
    SQLiteStore,
    apersisted,
    as_async,
    persisted,
    persisted_retry,
)
from src.xstate_statemachine.persistence import file_store as fs_mod

ROOT = pathlib.Path(__file__).resolve().parents[2]
STRESS = int(os.environ.get("XSM_STRESS_SAVES", "20"))
NO_BACKOFF = RetryPolicy(base_ms=1, max_ms=5, jitter="full")
WATCHDOG_S = 60.0
TEST_WATCHDOG_S = 240 if STRESS > 50 else 90

_CFG = {
    "id": "c",
    "initial": "s",
    "context": {"n": 0},
    "states": {"s": {"on": {"T": {"actions": "inc"}}}},
}


def _inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["n"] += 1


MACHINE = create_machine(_CFG, logic=MachineLogic(actions={"inc": _inc}))


def _count(store: Any, key: str) -> int:
    rec = store.load(key)
    if rec is None:
        return 0
    r = SyncInterpreter.from_snapshot(rec.snapshot, MACHINE).start()
    try:
        return int(r.context["n"])
    finally:
        r.stop()


def _run_threads(target: Callable[[int], None], n: int) -> List[BaseException]:
    """Run *n* threads; fail (not hang) if any outlives the watchdog."""
    errors: List[BaseException] = []

    def wrap(i: int) -> None:
        try:
            target(i)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [
        threading.Thread(target=wrap, args=(i,), daemon=True) for i in range(n)
    ]
    for t in ts:
        t.start()
    deadline = time.monotonic() + WATCHDOG_S
    for t in ts:
        t.join(max(0.0, deadline - time.monotonic()))
    hung = [t for t in ts if t.is_alive()]
    if hung:
        raise AssertionError(f"{len(hung)} threads deadlocked/hung")
    return errors


class _TmpDir(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="xsm259-"))
        # ⏱️ Hard watchdog: a hang dumps every stack and exits instead of
        #    wedging CI (and the children die with their pipes).
        faulthandler.dump_traceback_later(TEST_WATCHDOG_S, exit=True)

    def tearDown(self) -> None:
        faulthandler.cancel_dump_traceback_later()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _py(
        self, code: str, *args: str, timeout: float = 60
    ) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            [sys.executable, "-c", code, *args],
            cwd=str(ROOT),
            timeout=timeout,
            capture_output=True,
            text=True,
        )


# =============================================================================
# 💥 FileStore: kill -9 at every step of save
# =============================================================================
_KILL_AT = r"""
import os, sys, tempfile
sys.path.insert(0, {root!r})
from src.xstate_statemachine.persistence import FileStore
from src.xstate_statemachine.persistence import file_store as m
point = sys.argv[1]
s = FileStore({d!r})
die = lambda *a, **k: os._exit(9)
def after(real):
    def f(*a, **k):
        r = real(*a, **k)
        os._exit(9)
    return f
if point == "after_mkstemp":
    m.tempfile = type("T", (), {{"mkstemp": staticmethod(after(tempfile.mkstemp))}})
elif point == "after_write":
    m.os.fsync = die
elif point == "after_fsync":
    s._before_replace_hook = die
elif point == "after_replace":
    m.os.replace = after(os.replace)
elif point == "after_lock_write":
    m.os.write = after(os.write)
elif point == "after_unlock":
    m._unlock = after(m._unlock)
s.save("k", '{{"new": true}}', expected_version=1)
os._exit(0)
"""

#: point -> version visible after the kill (1 = previous, 2 = new).
_KILL_POINTS = {
    "after_lock_write": 1,
    "after_mkstemp": 1,
    "after_write": 1,
    "after_fsync": 1,
    "after_replace": 2,
    "after_unlock": 2,
}


class TestFileStoreKillPoints(_TmpDir):
    def test_kill9_at_every_step_old_or_new_never_torn(self) -> None:
        for point, want in _KILL_POINTS.items():
            with self.subTest(point=point):
                d = str(self.tmp / point)
                FileStore(d).save("k", '{"old": true}')
                r = self._py(_KILL_AT.format(root=str(ROOT), d=d), point)
                self.assertEqual(r.returncode, 9, r.stderr)
                s = FileStore(d)
                rec = s.load("k")
                self.assertEqual(rec.version, want)
                body = '{"new": true}' if want == 2 else '{"old": true}'
                self.assertEqual(rec.snapshot, body)
                # no temp/partial file is ever a key
                self.assertEqual(s.list_keys(), ["k"])
                # the lock is not wedged: the next writer proceeds at once
                t0 = time.monotonic()
                self.assertEqual(
                    s.save("k", "{}", expected_version=want), want + 1
                )
                self.assertLess(time.monotonic() - t0, 2.0)

    def test_orphan_temp_from_killed_writer_is_swept(self) -> None:
        # REGRESSION (#259 battle): a SIGKILL between mkstemp and replace
        # left `.tmp-*` litter forever; guarantees.md says "no temp litter".
        d = str(self.tmp / "s")
        FileStore(d).save("k", '{"old": true}')
        r = self._py(_KILL_AT.format(root=str(ROOT), d=d), "after_fsync")
        self.assertEqual(r.returncode, 9)
        temps = [p for p in os.listdir(d) if p.startswith(".tmp-")]
        self.assertEqual(len(temps), 1)
        # A fresh temp (younger than stale_lock_after) is left alone -- it
        # may belong to a live writer in another process.
        FileStore(d)
        self.assertEqual(
            len([p for p in os.listdir(d) if p.startswith(".tmp-")]), 1
        )
        old = time.time() - 3600
        os.utime(os.path.join(d, temps[0]), (old, old))
        FileStore(d)
        self.assertEqual(
            [p for p in os.listdir(d) if p.startswith(".tmp-")], []
        )


# =============================================================================
# 🔒 Cross-process locks (msvcrt.locking on Windows, flock on POSIX)
# =============================================================================
_HOLD = r"""
import os, sys, time
sys.path.insert(0, {root!r})
from src.xstate_statemachine.persistence import FileStore
s = FileStore({d!r})
with s.lock("k", timeout=5):
    print("HELD", os.getpid(), flush=True)
    time.sleep(float(sys.argv[1]))
"""


class TestCrossProcessLock(_TmpDir):
    def _holder(self, d: str, hold: float) -> "subprocess.Popen[str]":
        p = subprocess.Popen(
            [
                sys.executable,
                "-c",
                _HOLD.format(root=str(ROOT), d=d),
                str(hold),
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            text=True,
        )
        assert p.stdout is not None
        word, pid = p.stdout.readline().split()
        self.assertEqual(word, "HELD")
        # 📝 a Windows venv `python.exe` is a launcher: Popen.pid is the
        #    stub, not the interpreter that holds the lock.
        self.holder_pid = int(pid)
        return p

    def _hard_kill(self, p: "subprocess.Popen[str]") -> None:
        """Kill the interpreter that HOLDS the lock (not a launcher stub)
        and wait until it is gone."""
        if self.holder_pid != p.pid and sys.platform == "win32":
            with contextlib.suppress(subprocess.TimeoutExpired, OSError):
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(self.holder_pid)],
                    capture_output=True,
                    timeout=10,
                )
        p.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            p.wait(10)

    def test_second_process_times_out_at_documented_bound(self) -> None:
        d = str(self.tmp / "s")
        p = self._holder(d, 4)
        try:
            s = FileStore(d)
            t0 = time.monotonic()
            with self.assertRaises(LockTimeoutError) as cm:
                with s.lock("k", timeout=0.5):
                    pass
            took = time.monotonic() - t0
            self.assertGreaterEqual(took, 0.5)
            self.assertLess(took, 1.5)
            self.assertIn(str(self.holder_pid), str(cm.exception))
        finally:
            self._hard_kill(p)

    def test_killed_holder_lock_is_reclaimed(self) -> None:
        d = str(self.tmp / "s")
        p = self._holder(d, 60)
        self._hard_kill(p)  # TerminateProcess / SIGKILL: no cleanup runs
        s = FileStore(d)
        t0 = time.monotonic()
        with s.lock("k", timeout=2):
            s.save("k", "{}")
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_slow_live_holder_older_than_stale_after_still_times_out(
        self,
    ) -> None:
        # REGRESSION (#259 battle): holder info older than
        # `stale_lock_after` made `_file_lock` `continue` past the deadline
        # check -- waiters spun at 100% CPU forever, ignoring `timeout`.
        d = str(self.tmp / "s")
        p = self._holder(d, 4)
        try:
            s = FileStore(d, stale_lock_after=0.0)
            box: List[Any] = []

            def wait() -> None:
                t0 = time.monotonic()
                try:
                    with s.lock("k", timeout=0.3):
                        box.append("acquired")
                except LockTimeoutError:
                    box.append(time.monotonic() - t0)

            t = threading.Thread(target=wait, daemon=True)
            t.start()
            t.join(3)
            self.assertFalse(t.is_alive(), "waiter ignored its timeout")
            self.assertIsInstance(box[0], float)  # live lock never stolen
            self.assertLess(box[0], 1.0)
        finally:
            self._hard_kill(p)


# =============================================================================
# 🗄️ SQLiteStore: kills, WAL files, foreign files
# =============================================================================
_SQLITE_MANY = r"""
import os, sys, threading
sys.path.insert(0, {root!r})
from src.xstate_statemachine.persistence import SQLiteStore
s = SQLiteStore({d!r})
for i in range(40):
    s.save("k", '{{"i": %d}}' % i)
def ck():
    s2 = SQLiteStore({d!r})
    s2._conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
t = threading.Thread(target=ck); t.start()
os._exit(9)  # mid-checkpoint (or just before/after: all are legal)
"""


class TestSQLiteCrash(_TmpDir):
    def test_kill9_mid_wal_checkpoint_keeps_every_commit(self) -> None:
        d = str(self.tmp / "s.db")
        for _ in range(2):
            r = self._py(_SQLITE_MANY.format(root=str(ROOT), d=d))
            self.assertEqual(r.returncode, 9, r.stderr)
        s = SQLiteStore(d)
        self.assertEqual(s.load("k").version, 80)
        self.assertEqual(s.load("k").snapshot, '{"i": 39}')
        s.close()

    def test_wal_and_shm_deleted_between_clean_runs(self) -> None:
        d = str(self.tmp / "s.db")
        s = SQLiteStore(d)
        s.save("k", '{"a": 1}')
        s.close()
        for suffix in ("-wal", "-shm"):
            with self._suppress():
                os.unlink(d + suffix)
        s = SQLiteStore(d)
        self.assertEqual(s.load("k").snapshot, '{"a": 1}')
        self.assertEqual(s.save("k", "{}", expected_version=1), 2)
        s.close()

    def _suppress(self) -> Any:
        import contextlib

        return contextlib.suppress(FileNotFoundError)

    def test_non_sqlite_file_is_store_error(self) -> None:
        # REGRESSION (#259 battle): escaped as sqlite3.DatabaseError.
        d = self.tmp / "s.db"
        d.write_bytes(b"this is not a database" * 100)
        with self.assertRaises(StoreError) as cm:
            SQLiteStore(d)
        self.assertNotIsInstance(cm.exception, sqlite3.Error)
        self.assertIsInstance(cm.exception.__cause__, sqlite3.DatabaseError)

    def test_foreign_statecharts_table_is_store_error(self) -> None:
        # REGRESSION (#259 battle): `CREATE TABLE IF NOT EXISTS` no-op'd
        # and the first load raised sqlite3.OperationalError.
        d = str(self.tmp / "s.db")
        c = sqlite3.connect(d)
        c.execute("CREATE TABLE statecharts(x)")
        c.commit()
        c.close()
        with self.assertRaisesRegex(StoreError, "statecharts"):
            SQLiteStore(d)

    def test_newer_schema_version_is_store_error(self) -> None:
        d = str(self.tmp / "s.db")
        SQLiteStore(d).close()
        c = sqlite3.connect(d)
        c.execute("UPDATE xsm_schema SET version = 99")
        c.commit()
        c.close()
        with self.assertRaisesRegex(StoreError, "newer"):
            SQLiteStore(d)

    def test_empty_file_is_initialised(self) -> None:
        d = self.tmp / "s.db"
        d.write_bytes(b"")
        s = SQLiteStore(d)
        self.assertIsNone(s.load("k"))
        self.assertEqual(s.save("k", "{}"), 1)
        s.close()

    def test_file_corrupted_under_a_live_store_is_store_error(self) -> None:
        d = str(self.tmp / "s.db")
        s = SQLiteStore(d, journal_mode="DELETE")
        s.save("k", "{}")
        s.close()
        with open(d, "r+b") as fh:
            fh.write(b"garbage!" * 64)
        with self.assertRaises(StoreError):
            s.load("k")
        s.close()


# =============================================================================
# 💾 Disk full / permission errors
# =============================================================================
def _enospc(*a: Any, **k: Any) -> Any:
    raise OSError(errno.ENOSPC, "No space left on device")


class _CommitFails:
    """Connection proxy whose next COMMIT fails like a full disk."""

    def __init__(self, conn: sqlite3.Connection, msg: str) -> None:
        self._c = conn
        self._msg = msg
        self.armed = True

    def execute(self, sql: str, *a: Any) -> Any:
        if self.armed and sql.strip().upper() == "COMMIT":
            self.armed = False
            raise sqlite3.OperationalError(self._msg)
        return self._c.execute(sql, *a)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._c, name)


class TestDiskFull(_TmpDir):
    def _no_temps(self, s: FileStore) -> None:
        self.assertEqual(
            [p for p in os.listdir(s.directory) if p.startswith(".tmp-")], []
        )

    def test_filestore_enospc_at_write_and_replace(self) -> None:
        # (fsync is covered by test_battle_303_x0_core::TestX03Crash)
        for where in ("json.dump", "os.replace"):
            with self.subTest(where=where):
                s = FileStore(self.tmp / where)
                s.save("k", '{"old": true}')
                target = (
                    "src.xstate_statemachine.persistence.file_store.json.dump"
                    if where == "json.dump"
                    else "src.xstate_statemachine.persistence.file_store"
                    ".os.replace"
                )
                with mock.patch(target, side_effect=_enospc):
                    with self.assertRaises(OSError) as cm:
                        s.save("k", '{"new": true}', expected_version=1)
                self.assertEqual(cm.exception.errno, errno.ENOSPC)
                self.assertEqual(s.load("k").snapshot, '{"old": true}')
                self._no_temps(s)
                self.assertEqual(s.save("k", "{}", expected_version=1), 2)

    def test_sqlite_commit_disk_full_rolls_back_and_recovers(self) -> None:
        # REGRESSION (#259 battle): a failed COMMIT left the connection
        # in_transaction, so every LATER save on that thread "joined" the
        # dead transaction, returned a version, and was never committed.
        d = str(self.tmp / "s.db")
        s = SQLiteStore(d)
        s.save("k", '{"old": true}')
        proxy = _CommitFails(s._conn(), "database or disk is full")
        s._local.conn = proxy
        with self.assertRaises(StoreError) as cm:
            s.save("k", '{"new": true}', expected_version=1)
        self.assertNotIsInstance(cm.exception, sqlite3.Error)
        self.assertFalse(proxy.in_transaction)
        self.assertEqual(s.load("k").snapshot, '{"old": true}')
        self.assertEqual(s.save("k", '{"v": 2}', expected_version=1), 2)
        other = SQLiteStore(d)  # a separate connection sees it committed
        self.assertEqual(other.load("k").version, 2)
        other.close()
        s._local.conn = proxy._c
        s.close()

    def test_sqlite_commit_busy_inside_lock_is_lock_timeout(self) -> None:
        d = str(self.tmp / "s.db")
        s = SQLiteStore(d)
        s.save("k", "{}")
        proxy = _CommitFails(s._conn(), "database is locked")
        s._local.conn = proxy
        with self.assertRaises(LockTimeoutError):
            with s.lock("k", timeout=1):
                s.save("k", '{"x": 1}', expected_version=1)
        self.assertFalse(proxy.in_transaction)
        self.assertEqual(s.load("k").version, 1)
        s._local.conn = proxy._c
        s.close()

    def test_filestore_eacces_on_save_leaves_record(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("k", '{"old": true}')
        denied = PermissionError(errno.EACCES, "Access is denied")
        with mock.patch.object(fs_mod.tempfile, "mkstemp", side_effect=denied):
            with self.assertRaises(PermissionError):
                s.save("k", "{}", expected_version=1)
        self.assertEqual(s.load("k").version, 1)

    def test_filestore_directory_under_a_file_fails_at_construction(
        self,
    ) -> None:
        blocker = self.tmp / "file"
        blocker.write_text("x")
        with self.assertRaises(OSError):
            FileStore(blocker / "sub")

    def test_sqlite_read_only_database_is_store_error(self) -> None:
        d = str(self.tmp / "s.db")
        s = SQLiteStore(d, journal_mode="DELETE")
        s.save("k", "{}")
        s.close()
        os.chmod(d, stat.S_IREAD)
        try:
            with self.assertRaises(StoreError) as cm:
                ro = SQLiteStore(d, journal_mode="DELETE")
                ro.save("k", "{}", expected_version=1)
            self.assertNotIsInstance(cm.exception, sqlite3.Error)
        finally:
            os.chmod(d, stat.S_IREAD | stat.S_IWRITE)


# =============================================================================
# 🪟 Windows filesystem semantics (real on a Windows host)
# =============================================================================
class TestWindowsSemantics(_TmpDir):
    def test_transient_permission_error_on_replace_is_retried(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("k", '{"old": true}')
        real = os.replace
        calls = {"n": 0}

        def flaky(a: Any, b: Any) -> None:
            calls["n"] += 1
            if calls["n"] <= 3:
                raise PermissionError(errno.EACCES, "AV scanner has it open")
            real(a, b)

        with mock.patch.object(fs_mod, "_replace", flaky):
            self.assertEqual(s.save("k", "{}", expected_version=1), 2)
        self.assertEqual(calls["n"], 4)

    def test_permanent_permission_error_raises_after_budget(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("k", '{"old": true}')
        calls = {"n": 0}

        def denied(a: Any, b: Any) -> None:
            calls["n"] += 1
            raise PermissionError(errno.EACCES, "Access is denied")

        t0 = time.monotonic()
        with mock.patch.object(fs_mod, "_replace", denied):
            with self.assertRaises(PermissionError):
                s.save("k", "{}", expected_version=1)
        self.assertEqual(calls["n"], fs_mod._WRITE_RETRIES)
        self.assertLess(time.monotonic() - t0, 3.0)
        self.assertEqual(s.load("k").version, 1)
        self.assertEqual(
            [p for p in os.listdir(s.directory) if p.startswith(".tmp-")], []
        )

    def test_reader_holding_record_open_during_replace(self) -> None:
        # A foreign reader (plain `open()`, no FILE_SHARE_DELETE) blocks
        # the rename on Windows; the writer retries until it lets go.
        s = FileStore(self.tmp / "s")
        s.save("k", '{"old": true}')
        path = s._path("k")
        fh = open(path, "rb")
        whole = fh.read()
        threading.Timer(0.15, fh.close).start()
        self.assertTrue(whole.endswith(b"}"))
        self.assertEqual(s.save("k", '{"new": true}', expected_version=1), 2)
        self.assertEqual(s.load("k").snapshot, '{"new": true}')

    def test_store_reader_open_does_not_block_writer(self) -> None:
        # REGRESSION (#259 battle, Windows): the store's own readers used
        # plain `open()`; a reader polling in a loop starved the writer's
        # whole `os.replace` retry budget -> PermissionError from `save`.
        s = FileStore(self.tmp / "s")
        s.save("k", '{"old": true}')
        with fs_mod._open_for_read(s._path("k")) as fh:
            t0 = time.monotonic()
            self.assertEqual(
                s.save("k", '{"new": true}', expected_version=1), 2
            )
            self.assertLess(time.monotonic() - t0, 0.4)  # no retry wait
            self.assertIn(b"old", fh.read())  # reader keeps old bytes
        self.assertEqual(s.load("k").snapshot, '{"new": true}')

    def test_concurrent_reader_never_sees_torn_record(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("k", '{"i": 0}')
        stop = threading.Event()
        seen: List[int] = []

        def reader() -> None:
            while not stop.is_set():
                rec = s.load("k")  # raises on a torn record
                seen.append(rec.version)

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        try:
            for i in range(1, 60):
                s.save("k", '{"i": %d}' % i, expected_version=i)
        finally:
            stop.set()
            t.join(10)
        self.assertEqual(seen, sorted(seen))  # monotonic
        self.assertEqual(s.load("k").version, 60)

    def test_case_variants_are_distinct_records(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("Order-1", '{"a": 1}')
        s.save("order-1", '{"a": 2}')
        s.save("ORDER-1", '{"a": 3}')
        self.assertEqual(s.load("Order-1").snapshot, '{"a": 1}')
        self.assertEqual(s.load("order-1").snapshot, '{"a": 2}')
        self.assertEqual(s.list_keys(), ["ORDER-1", "Order-1", "order-1"])

    def test_200_char_keys_work_in_a_deep_directory(self) -> None:
        # REGRESSION (#259 battle): "A"*200 and 200 CJK chars percent-
        # encode to 600/1800 chars -> OSError EINVAL/ENAMETOOLONG on save.
        deep = self.tmp
        for _ in range(6):
            deep = deep / ("d" * 20)
        s = FileStore(deep)
        keys = ["a" * 200, "A" * 200, "中" * 200, "Ab" * 100, "ab" * 100]
        for k in keys:
            self.assertEqual(s.save(k, '{"k": 1}'), 1)
            self.assertEqual(s.load(k).version, 1)
            self.assertEqual(s.save(k, "{}", expected_version=1), 2)
        self.assertEqual(sorted(s.list_keys()), sorted(keys))
        self.assertEqual(s.list_keys(prefix="中"), ["中" * 200])
        # case variants of a hashed key stay distinct
        self.assertNotEqual(s._path("A" * 200), s._path("a" * 199 + "A"))
        for k in keys:
            self.assertEqual(s.forget(k)["snapshots"], 1)
        self.assertEqual(s.list_keys(), [])

    def test_201_char_key_is_invalid(self) -> None:
        s = FileStore(self.tmp / "s")
        for k in ("a" * 201, "A" * 201):
            with self.assertRaises(InvalidKeyError):
                s.save(k, "{}")

    def test_hashed_name_with_foreign_body_is_not_listed(self) -> None:
        s = FileStore(self.tmp / "s")
        s.save("A" * 200, "{}")
        (s.directory / "~deadbeef.xsm.json").write_text(
            '{"key": "x", "version": 1}'
        )
        self.assertEqual(s.list_keys(), ["A" * 200])

    def test_reserved_device_names_round_trip(self) -> None:
        s = FileStore(self.tmp / "s")
        names = ["CON", "con.json", "NUL", "COM1", "lpt9", "aux.txt"]
        for n in names:
            s.save(n, '{"n": "%s"}' % n)
        for n in names:
            self.assertEqual(s.load(n).snapshot, '{"n": "%s"}' % n)
        self.assertEqual(s.list_keys(), sorted(names))


# =============================================================================
# 🎯 Deterministic interleavings (the primary proof)
# =============================================================================
class FaultyStore:
    """Forces `ConflictError` on the k-th save attempt (k is 1-based)."""

    def __init__(self, inner: Any, fail_on: int) -> None:
        self.inner = inner
        self.fail_on = fail_on
        self.attempts = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def save(self, key: str, snapshot: str, **kw: Any) -> int:
        self.attempts += 1
        if self.attempts == self.fail_on:
            raise ConflictError(key, kw.get("expected_version"), -1)
        return self.inner.save(key, snapshot, **kw)


def _stores(tmp: pathlib.Path) -> List[Any]:
    return [
        MemoryStore(),
        FileStore(tmp / "fs"),
        SQLiteStore(tmp / "s.db"),
    ]


class TestDeterministicInterleaving(_TmpDir):
    def test_optimistic_retries_exactly_once_per_forced_conflict(self) -> None:
        for store in _stores(self.tmp):
            for k in (1, 2, 3):
                with self.subTest(store=type(store).__name__, k=k):
                    key = f"k{k}"
                    faulty = FaultyStore(store, fail_on=k)
                    calls = {"n": 0}

                    def fn(i: Any) -> None:
                        calls["n"] += 1
                        i.send("T")

                    lock = OptimisticLock(retries=3, backoff=NO_BACKOFF)
                    for _ in range(3):
                        persisted_retry(faulty, key, MACHINE, fn, lock=lock)
                    self.assertEqual(calls["n"], 4)  # 3 + one re-run
                    self.assertEqual(faulty.attempts, 4)
                    self.assertEqual(_count(store, key), 3)  # none doubled
                    self.assertEqual(store.load(key).version, 3)

    def test_retry_budget_exhausted_reports_attempts(self) -> None:
        store = MemoryStore()

        class Always(FaultyStore):
            def save(self, key: str, snapshot: str, **kw: Any) -> int:
                self.attempts += 1
                raise ConflictError(key, kw.get("expected_version"), -1)

        faulty = Always(store, 0)
        lock = OptimisticLock(retries=2, backoff=NO_BACKOFF)
        with self.assertRaises(ConflictError) as cm:
            persisted_retry(
                faulty, "k", MACHINE, lambda i: i.send("T"), lock=lock
            )
        self.assertEqual(cm.exception.attempts, 3)  # type: ignore
        self.assertEqual(faulty.attempts, 3)
        self.assertIsNone(store.load("k"))

    def test_pessimistic_second_worker_waits_for_first(self) -> None:
        for store in _stores(self.tmp):
            with self.subTest(store=type(store).__name__):
                entered, release = threading.Event(), threading.Event()
                log: List[str] = []

                def first() -> None:
                    with persisted(
                        store, "p", MACHINE, lock=PessimisticLock(timeout=5)
                    ) as i:
                        entered.set()
                        release.wait(5)
                        i.send("T")
                        log.append("first-done")

                def second() -> None:
                    entered.wait(5)
                    with persisted(
                        store, "p", MACHINE, lock=PessimisticLock(timeout=5)
                    ) as i:
                        log.append("second-in")
                        i.send("T")

                t1 = threading.Thread(target=first, daemon=True)
                t2 = threading.Thread(target=second, daemon=True)
                t1.start()
                t2.start()
                entered.wait(5)
                time.sleep(0.2)
                self.assertEqual(log, [])  # second is blocked
                release.set()
                t1.join(10)
                t2.join(10)
                self.assertEqual(log, ["first-done", "second-in"])
                self.assertEqual(_count(store, "p"), 2)


# =============================================================================
# 🔥 Stress (smoke): threads, then processes
# =============================================================================
class TestThreadStress(_TmpDir):
    THREADS = 16

    def _locks(self) -> List[Any]:
        return [
            OptimisticLock(retries=100_000, backoff=NO_BACKOFF),
            PessimisticLock(timeout=30),
        ]

    def test_one_key_every_store_every_lock(self) -> None:
        for store in _stores(self.tmp):
            for lock in self._locks():
                name = f"{type(store).__name__}/{type(lock).__name__}"
                with self.subTest(name):
                    key = "one-" + type(lock).__name__

                    def work(_: int) -> None:
                        for _ in range(STRESS):
                            persisted_retry(
                                store,
                                key,
                                MACHINE,
                                lambda i: i.send("T"),
                                lock=lock,
                            )

                    self.assertEqual(_run_threads(work, self.THREADS), [])
                    total = self.THREADS * STRESS
                    self.assertEqual(_count(store, key), total)
                    self.assertEqual(store.load(key).version, total)

    def test_distinct_keys_every_store(self) -> None:
        for store in _stores(self.tmp):
            with self.subTest(type(store).__name__):
                lock = OptimisticLock(retries=100_000, backoff=NO_BACKOFF)

                def work(n: int) -> None:
                    for j in range(STRESS):
                        persisted_retry(
                            store,
                            f"d{(n * STRESS + j) % 200}",
                            MACHINE,
                            lambda i: i.send("T"),
                            lock=lock,
                        )

                self.assertEqual(_run_threads(work, self.THREADS), [])
                keys = store.list_keys(prefix="d")
                total = sum(_count(store, k) for k in keys)
                self.assertEqual(total, self.THREADS * STRESS)


_PROC_WORKER = r"""
import sys
sys.path.insert(0, {root!r})
from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.patterns.retry import RetryPolicy
from src.xstate_statemachine.persistence import (
    FileStore, OptimisticLock, PessimisticLock, SQLiteStore, persisted_retry)
cfg = {cfg!r}
def inc(i, c, e, a): c["n"] += 1
m = create_machine(cfg, logic=MachineLogic(actions={{"inc": inc}}))
kind, path, mode, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
store = FileStore(path) if kind == "file" else SQLiteStore(path)
lock = (OptimisticLock(retries=100000,
                       backoff=RetryPolicy(base_ms=1, max_ms=10))
        if mode == "opt" else PessimisticLock(timeout=60))
for _ in range(n):
    persisted_retry(store, "k", m, lambda i: i.send("T"), lock=lock)
print("OK")
"""


class TestProcessStress(_TmpDir):
    PROCS = 4

    def test_four_processes_one_key(self) -> None:
        n = max(5, STRESS)
        code = _PROC_WORKER.format(root=str(ROOT), cfg=_CFG)
        for kind in ("file", "sqlite"):
            for mode in ("opt", "pess"):
                with self.subTest(kind=kind, mode=mode):
                    path = str(self.tmp / f"{kind}-{mode}")
                    if kind == "sqlite":
                        path += ".db"
                        SQLiteStore(path).close()  # schema once
                    procs = [
                        subprocess.Popen(
                            [
                                sys.executable,
                                "-c",
                                code,
                                kind,
                                path,
                                mode,
                                str(n),
                            ],
                            cwd=str(ROOT),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )
                        for _ in range(self.PROCS)
                    ]
                    try:
                        for p in procs:
                            out, err = p.communicate(timeout=60)
                            self.assertEqual(p.returncode, 0, err[-2000:])
                    finally:
                        for p in procs:
                            p.kill()
                            with contextlib.suppress(
                                subprocess.TimeoutExpired
                            ):
                                p.wait(10)
                    s = (
                        FileStore(path)
                        if kind == "file"
                        else SQLiteStore(path)
                    )
                    self.assertEqual(_count(s, "k"), self.PROCS * n)
                    self.assertEqual(s.load("k").version, self.PROCS * n)


# =============================================================================
# ⚡ as_async adapter
# =============================================================================
class TestAsyncAdapter(_TmpDir):
    def test_100_concurrent_apersisted_pessimistic_one_key(self) -> None:
        # REGRESSION (#259 battle): every adapter call runs on ONE thread;
        # two tasks inside lock() were the same thread to the sync store.
        # Memory/File: the 2nd acquire blocked the worker -> LockTimeout
        # for all waiters. SQLite: the 2nd joined the 1st's transaction ->
        # no exclusion, ConflictError for all but one.
        for store in _stores(self.tmp):
            with self.subTest(type(store).__name__):
                a = as_async(store)

                async def one() -> None:
                    async with apersisted(
                        a, "k", MACHINE, lock=PessimisticLock(timeout=30)
                    ) as i:
                        await asyncio.sleep(0)
                        await i.send("T")

                async def go() -> List[Any]:
                    return await asyncio.gather(
                        *[one() for _ in range(100)], return_exceptions=True
                    )

                res = asyncio.run(go())
                self.assertEqual([r for r in res if r is not None], [])
                self.assertEqual(_count(store, "k"), 100)
                a.close()

    def test_call_from_other_task_does_not_join_a_held_lock(self) -> None:
        # REGRESSION (#259 battle): a save() from task B while task A held
        # the adapter's SQLite lock ran inside A's transaction and was
        # rolled back with A -- save returned 1, load returned None.
        store = SQLiteStore(self.tmp / "s.db")
        a = as_async(store)

        async def holder(ev: asyncio.Event) -> None:
            try:
                async with a.lock("a", timeout=5):
                    ev.set()
                    await asyncio.sleep(0.1)
                    raise RuntimeError("abort A")
            except RuntimeError:
                pass

        async def other(ev: asyncio.Event) -> int:
            await ev.wait()
            return await a.save("b", "{}")

        async def go() -> Any:
            ev = asyncio.Event()
            return await asyncio.gather(holder(ev), other(ev))

        self.assertEqual(asyncio.run(go())[1], 1)
        self.assertEqual(store.load("b").version, 1)
        a.close()

    def test_lock_wait_on_adapter_respects_timeout(self) -> None:
        a = as_async(MemoryStore())

        async def go() -> float:
            async with a.lock("k", timeout=5):
                t0 = time.monotonic()
                with self.assertRaises(LockTimeoutError):
                    await asyncio.wait_for(self._inner(a), 5)
                return time.monotonic() - t0

        took = asyncio.run(go())
        self.assertLess(took, 1.5)
        a.close()

    async def _inner(self, a: Any) -> None:
        async def contender() -> None:
            async with a.lock("k", timeout=0.3):
                pass

        await asyncio.create_task(contender())

    def test_1000_callers_queue_not_raise(self) -> None:
        store = MemoryStore()
        store.save("k", "{}")
        a = as_async(store)

        async def go() -> List[Any]:
            return await asyncio.gather(*[a.load("k") for _ in range(1000)])

        res = asyncio.run(go())
        self.assertEqual(len(res), 1000)
        self.assertTrue(all(r.version == 1 for r in res))
        a.close()

    def test_close_while_operations_in_flight(self) -> None:
        store = SQLiteStore(self.tmp / "s.db")
        a = as_async(store)

        async def go() -> List[Any]:
            tasks = [
                asyncio.ensure_future(a.save(f"k{i}", "{}")) for i in range(50)
            ]
            await asyncio.sleep(0)
            a.close()  # waits for the in-flight work, never hangs
            return await asyncio.gather(*tasks, return_exceptions=True)

        t0 = time.monotonic()
        res = asyncio.run(go())
        self.assertLess(time.monotonic() - t0, 20)
        for r in res:
            self.assertTrue(r == 1 or isinstance(r, RuntimeError), r)
        a.close()  # idempotent

    def test_loop_closed_mid_sqlite_call_no_hang_no_leak(self) -> None:
        store = SQLiteStore(self.tmp / "s.db")
        before = threading.active_count()
        a = as_async(store)
        real = store._load_raw

        def slow(key: str) -> Any:
            time.sleep(0.3)
            return real(key)

        store._load_raw = slow  # type: ignore[method-assign]

        async def go() -> None:
            task = asyncio.ensure_future(a.load("k"))
            await asyncio.sleep(0.05)
            task.cancel()

        t0 = time.monotonic()
        asyncio.run(go())
        a.close()
        self.assertLess(time.monotonic() - t0, 5)
        gc.collect()
        deadline = time.monotonic() + 5
        while (
            threading.active_count() > before and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        self.assertLessEqual(threading.active_count(), before)

    def test_apersisted_with_sync_store_does_not_leak_threads(self) -> None:
        store = MemoryStore()
        before = threading.active_count()

        async def go() -> None:
            for _ in range(30):
                async with apersisted(store, "k", MACHINE) as i:
                    await i.send("T")

        asyncio.run(go())
        gc.collect()
        deadline = time.monotonic() + 5
        while (
            threading.active_count() > before and time.monotonic() < deadline
        ):
            time.sleep(0.05)
            gc.collect()
        self.assertLessEqual(threading.active_count(), before)
        self.assertEqual(_count(store, "k"), 30)


# =============================================================================
# ⏱️ Every wait in the store code is bounded
# =============================================================================
# Inventory (grep `sleep|acquire(|join(|while True` in persistence/
# {store,file_store,sqlite_store,async_store,locking}.py):
#   store.py         _timed_lock: lk.acquire(timeout=timeout)          bounded
#   file_store.py    _read / _write_atomic: <= _WRITE_RETRIES sleeps    bounded
#   file_store.py    _file_lock while True                    FIXED (#259 battle)
#   file_store.py    _save_raw: _maybe_lock(timeout=10.0)               bounded
#   sqlite_store.py  :memory: lock lk.acquire(timeout=timeout)          bounded
#   sqlite_store.py  BEGIN IMMEDIATE under busy_timeout                 bounded
#   async_store.py   _alock gate: asyncio.wait_for(timeout)             bounded
#   async_store.py   _run gate wait (holder's lock is itself bounded)   bounded
#   locking.py       OptimisticLock.run while True: <= retries + 1      bounded
class TestEveryWaitIsBounded(_TmpDir):
    def _timed(self, fn: Callable[[], None]) -> float:
        box: List[Optional[float]] = [None]

        def run() -> None:
            t0 = time.monotonic()
            try:
                fn()
            except LockTimeoutError:
                box[0] = time.monotonic() - t0

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(5)
        self.assertFalse(t.is_alive(), "unbounded wait")
        self.assertIsNotNone(box[0])
        return float(box[0])  # type: ignore[arg-type]

    def test_lock_timeout_bound_on_every_store(self) -> None:
        for store in _stores(self.tmp):
            with self.subTest(type(store).__name__):
                held, done = threading.Event(), threading.Event()

                def hold() -> None:
                    with store.lock("k", timeout=1):
                        held.set()
                        done.wait(5)

                t = threading.Thread(target=hold, daemon=True)
                t.start()
                held.wait(5)
                try:

                    def contend() -> None:
                        with store.lock("k", timeout=0.3):
                            pass

                    took = self._timed(contend)
                    self.assertGreaterEqual(took, 0.25)
                    self.assertLess(took, 1.5)
                finally:
                    done.set()
                    t.join(5)

    def test_sqlite_busy_save_is_bounded_lock_timeout(self) -> None:
        d = str(self.tmp / "s.db")
        holder = SQLiteStore(d)
        contender = SQLiteStore(d, busy_timeout=0.3)
        held, done = threading.Event(), threading.Event()

        def hold() -> None:
            with holder.lock("x", timeout=1):
                held.set()
                done.wait(5)

        t = threading.Thread(target=hold, daemon=True)
        t.start()
        held.wait(5)
        try:
            took = self._timed(lambda: contender.save("k", "{}") and None)
            self.assertLess(took, 1.5)
        finally:
            done.set()
            t.join(5)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
