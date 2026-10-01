# tests/test_battle_303_x0_core.py
"""Adversarial battle test of #303's X0 security baseline -- zero-dependency
core + persistence rows (X0.1-X0.5, X0.9, X0.10).

🏛️ Every test is an ATTACK: it must either fail safe against the library or
pin a defect this battle fixed (marked ``REGRESSION``). The static greps in
`test_security_baseline.py` and the contract suites are not repeated.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import errno
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from typing import Any, List, Optional
from unittest import mock

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Event,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    XStateMachineError,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    InvalidKeyError,
    SnapshotCorruptError,
    SnapshotDriftError,
    SnapshotTooLargeError,
    StoreError,
)
from src.xstate_statemachine.persistence import (
    DueTimerScanner,
    FileStore,
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    IdempotencyPlugin,
    MemoryInbox,
    PessimisticLock,
    SnapshotMigrator,
    SQLiteInbox,
    SQLiteLog,
    SQLiteStore,
    persisted,
)
from src.xstate_statemachine.persistence.deadline import Deadline
from src.xstate_statemachine.persistence.idempotency import (
    PROCESSED_RING_SIZE,
)
from src.xstate_statemachine.persistence.log import TransitionLogPlugin
from src.xstate_statemachine.persistence.store import validate_key
from src.xstate_statemachine.plugins import redact

ROOT = pathlib.Path(__file__).resolve().parents[1]

WALLET = {
    "id": "wallet",
    "initial": "open",
    "context": {"credits": 0},
    "states": {"open": {"on": {"CREDIT": {"actions": "add"}}}},
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["credits"] += e.payload.get("amount", 0)


def wallet() -> Any:
    return create_machine(WALLET, logic=MachineLogic(actions={"add": _add}))


def _stub_interp() -> Any:
    """Just enough interpreter for `IdempotencyPlugin.on_before_send`."""
    return types.SimpleNamespace(
        machine=types.SimpleNamespace(id="wallet"),
        current_state_ids={"wallet.open"},
        context={},
    )


def _event(key: str, **payload: Any) -> Any:
    return Event("CREDIT", {"idempotency_key": key, **payload})


class _TmpDir(unittest.TestCase):
    def setUp(self) -> None:
        # 🪟 Per-thread SQLite connections from worker threads can outlive
        #    `close()` on Windows; a locked temp file is not a test failure.
        #    (`ignore_cleanup_errors=` is 3.10+; the library supports 3.9.)
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


# =============================================================================
# X0.1 / X0.2 -- closed-by-default principal, principal-scoped idempotency
# =============================================================================
class TestX01Principal(unittest.TestCase):
    def _send(self, principal: Any, inbox: Any = None) -> Any:
        p = IdempotencyPlugin(
            inbox or MemoryInbox(),
            principal=lambda e: principal,
            instance_key=lambda i: "k",
        )
        i = SyncInterpreter(wallet()).use(p).start()
        r = i.send("CREDIT", wait=True, idempotency_key="z", amount=1)
        credits = i.context["credits"]
        i.stop()
        return r, credits

    def test_none_and_empty_principal_are_refused(self) -> None:
        # REGRESSION: None / "" became the shared scopes "None" / "".
        # Review H1: the literal renderings of nothing are refused too.
        for bad in (None, "", 0, b"alice", "None", "null", "anonymous"):
            with self.subTest(principal=bad):
                r, credits = self._send(bad)
                self.assertIsInstance(r.error, ValueError)
                self.assertEqual(credits, 0)

    def test_hostile_principals_are_their_own_scope(self) -> None:
        inbox = MemoryInbox()
        for p in ("alice\x00", "‮alice", "a" * 10_000, "ALICE", "alice"):
            with self.subTest(principal=p[:12]):
                r, credits = self._send(p, inbox)
                self.assertIsNone(r.error)
                self.assertFalse(r.duplicate)  # never alice's receipt
                self.assertEqual(credits, 1)

    def test_scope_join_is_injective(self) -> None:
        # REGRESSION: principal "alice/c" + machine "c" collided with
        #   principal "alice" + machine "c/c" ("alice/c/c/k" both).
        inbox = MemoryInbox()
        m1 = create_machine({**WALLET, "id": "c/c"}, logic=wallet().logic)
        m2 = create_machine({**WALLET, "id": "c"}, logic=wallet().logic)
        mk = lambda who: IdempotencyPlugin(  # noqa: E731
            inbox, principal=lambda e: who, instance_key=lambda i: "k"
        )
        i1 = SyncInterpreter(m1).use(mk("alice")).start()
        i2 = SyncInterpreter(m2).use(mk("alice/c")).start()
        i1.send("CREDIT", wait=True, idempotency_key="z", amount=5)
        r = i2.send("CREDIT", wait=True, idempotency_key="z", amount=5)
        self.assertFalse(r.duplicate)
        self.assertEqual(i2.context["credits"], 5)
        i1.stop()
        i2.stop()

    def test_raising_principal_fails_open_by_documented_contract(
        self,
    ) -> None:
        # 📝 `_SafePlugin` admits on a crashing interceptor (documented on
        #    `_intercept_before_send`): pinned so a change is deliberate.
        def boom(e: Any) -> str:
            raise RuntimeError("auth down")

        p = IdempotencyPlugin(MemoryInbox(), principal=boom)
        i = SyncInterpreter(wallet()).use(p).start()
        i.send("CREDIT", wait=True, idempotency_key="z", amount=1)
        self.assertEqual(i.context["credits"], 1)
        i.stop()


class TestX02Idempotency(_TmpDir):
    def _plugin(self, inbox: Any, who: str = "alice") -> Any:
        return IdempotencyPlugin(
            inbox, principal=lambda e: who, instance_key=lambda i: "k"
        )

    def test_cross_principal_replay_gets_no_receipt(self) -> None:
        inbox = SQLiteInbox(self.tmp / "i.db")
        a = SyncInterpreter(wallet()).use(self._plugin(inbox)).start()
        b = SyncInterpreter(wallet()).use(self._plugin(inbox, "bob")).start()
        a.send("CREDIT", wait=True, idempotency_key="k1", amount=7)
        r = b.send("CREDIT", wait=True, idempotency_key="k1", amount=7)
        self.assertFalse(r.duplicate)
        self.assertEqual(b.context["credits"], 7)
        a.stop()
        b.stop()
        inbox.close()

    def test_mismatch_and_in_flight(self) -> None:
        p = self._plugin(MemoryInbox())
        i = _stub_interp()
        self.assertIsNone(p.on_before_send(i, _event("k", amount=1)))
        r = p.on_before_send(i, _event("k", amount=1))
        self.assertIsInstance(r.error, IdempotencyInFlightError)
        r = p.on_before_send(i, _event("k", amount=2))
        self.assertIsInstance(r.error, IdempotencyMismatchError)

    def test_hostile_keys_refused_not_stored(self) -> None:
        inbox = MemoryInbox()
        p = self._plugin(inbox)
        for key in ("a/../b", "x" * 10_000, "é", "a\x00b", "", "‮"):
            with self.subTest(key=key[:10]):
                r = p.on_before_send(_stub_interp(), _event(key))
                if key == "a/../b":  # printable ASCII: opaque, accepted
                    self.assertIsNone(r)
                else:
                    self.assertIsInstance(r.error, ValueError)
        self.assertEqual(len(inbox), 1)

    def test_ttl_expiry_then_reuse_admits(self) -> None:
        inbox = MemoryInbox()
        p = IdempotencyPlugin(
            inbox,
            principal=lambda e: "a",
            instance_key=lambda i: "k",
            ttl_s=0.01,
        )
        i = SyncInterpreter(wallet()).use(p).start()
        i.send("CREDIT", wait=True, idempotency_key="t", amount=1)
        time.sleep(0.03)
        r = i.send("CREDIT", wait=True, idempotency_key="t", amount=1)
        self.assertFalse(r.duplicate)
        self.assertEqual(i.context["credits"], 2)
        i.stop()

    def test_ring_overflow_then_evicted_key_still_deduped_by_inbox(
        self,
    ) -> None:
        # 📝 The plugin has no `max_keys`; the bounded structure is the
        #    in-snapshot ring (PROCESSED_RING_SIZE). Evicting a key from
        #    the ring must not re-admit it -- the inbox is the authority.
        p = self._plugin(MemoryInbox())
        i = SyncInterpreter(wallet()).use(p).start()
        for n in range(PROCESSED_RING_SIZE + 5):
            i.send("CREDIT", idempotency_key=f"k{n}", amount=1)
        self.assertNotIn(
            "alice/wallet/k|k0", i.context["__xsm_processed_ids__"]
        )
        r = i.send("CREDIT", wait=True, idempotency_key="k0", amount=1)
        self.assertTrue(r.duplicate)
        self.assertEqual(i.context["credits"], PROCESSED_RING_SIZE + 5)
        i.stop()

    def test_crash_between_claim_and_mark_restart_refuses_409(
        self,
    ) -> None:
        # X0.3: claim persisted, process died before the effect was saved
        #   (no ring evidence) -> a restart sees IN FLIGHT, never a re-run.
        inbox = SQLiteInbox(self.tmp / "i.db")
        p = self._plugin(inbox)
        self.assertIsNone(p.on_before_send(_stub_interp(), _event("c")))
        inbox.close()
        inbox2 = SQLiteInbox(self.tmp / "i.db")
        r = self._plugin(inbox2).on_before_send(_stub_interp(), _event("c"))
        self.assertIsInstance(r.error, IdempotencyInFlightError)
        inbox2.close()

    def test_sixteen_threads_same_key_one_admission(self) -> None:
        for inbox in (MemoryInbox(), SQLiteInbox(self.tmp / "r.db")):
            p = self._plugin(inbox)
            barrier = threading.Barrier(16)
            admitted: List[int] = []

            def w(n: int) -> None:
                barrier.wait()
                if p.on_before_send(_stub_interp(), _event("race")) is None:
                    admitted.append(n)

            ts = [threading.Thread(target=w, args=(n,)) for n in range(16)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(len(admitted), 1, type(inbox).__name__)
            if hasattr(inbox, "close"):
                inbox.close()


# =============================================================================
# X0.3 -- crash consistency
# =============================================================================
_KILL_FILE = r"""
import os, sys
sys.path.insert(0, {root!r})
from src.xstate_statemachine.persistence import FileStore
s = FileStore({d!r})
os.replace = lambda *a, **k: os._exit(9)
s.save("k", '{{"new": true}}')
"""

_KILL_SQLITE = r"""
import os, sys
sys.path.insert(0, {root!r})
from src.xstate_statemachine.persistence import SQLiteStore
s = SQLiteStore({d!r})
with s.lock("k"):
    s.save("k", '{{"new": true}}')
    os._exit(9)
"""


class TestX03Crash(_TmpDir):
    def _kill(self, script: str, d: str) -> None:
        code = script.format(root=str(ROOT), d=d)
        r = subprocess.run(
            [sys.executable, "-c", code], cwd=str(ROOT), timeout=60
        )
        self.assertEqual(r.returncode, 9)

    def test_filestore_kill9_mid_replace_keeps_old_record(self) -> None:
        d = str(self.tmp / "fs")
        FileStore(d).save("k", '{"old": true}')
        self._kill(_KILL_FILE, d)
        s = FileStore(d)
        self.assertEqual(s.load("k").snapshot, '{"old": true}')
        self.assertEqual(s.load("k").version, 1)
        self.assertEqual(s.save("k", "{}", expected_version=1), 2)
        self.assertEqual(s.list_keys(), ["k"])  # temp file is not a key

    def test_sqlite_kill9_mid_transaction_keeps_old_record(self) -> None:
        d = str(self.tmp / "s.db")
        s0 = SQLiteStore(d)
        s0.save("k", '{"old": true}')
        s0.close()
        self._kill(_KILL_SQLITE, d)
        s = SQLiteStore(d)
        self.assertEqual(s.load("k").snapshot, '{"old": true}')
        s.close()

    def test_disk_full_raises_oserror_and_old_record_intact(self) -> None:
        s = FileStore(self.tmp / "fs")
        s.save("k", '{"old": true}')
        full = OSError(errno.ENOSPC, "No space left on device")
        with mock.patch("os.fsync", side_effect=full):
            with self.assertRaises(OSError) as cm:
                s.save("k", '{"new": true}')
        self.assertEqual(cm.exception.errno, errno.ENOSPC)
        self.assertEqual(s.load("k").snapshot, '{"old": true}')
        leftovers = [p for p in os.listdir(s.directory) if ".tmp-" in p]
        self.assertEqual(leftovers, [])


# =============================================================================
# X0.4 -- safe deserialisation + caps
# =============================================================================
class TestX04Deserialisation(_TmpDir):
    def _poison_file(self, s: FileStore, data: bytes) -> None:
        s.save("k", "{}")
        (s.directory / "k.xsm.json").write_bytes(data)

    def test_filestore_cap_applies_before_parse(self) -> None:
        # REGRESSION: the whole file was read and `json.loads`-ed before
        #   `_check_size` ran.
        s = FileStore(self.tmp / "fs", max_snapshot_bytes=1000)
        self._poison_file(s, b" " * (8 * 1024 * 1024))
        with mock.patch("json.loads") as loads:
            t0 = time.perf_counter()
            with self.assertRaises(SnapshotTooLargeError):
                s.load("k")
            self.assertLess(time.perf_counter() - t0, 1.0)
        loads.assert_not_called()

    def test_filestore_deep_nesting_is_corrupt_not_recursionerror(
        self,
    ) -> None:
        # REGRESSION: RecursionError escaped `except XStateMachineError`.
        s = FileStore(self.tmp / "fs")
        self._poison_file(s, b"[" * 100_000 + b"]" * 100_000)
        with self.assertRaises(SnapshotCorruptError):
            s.load("k")

    def test_filestore_non_utf8_is_corrupt(self) -> None:
        # REGRESSION: UnicodeDecodeError escaped.
        s = FileStore(self.tmp / "fs")
        self._poison_file(s, b"\xff\xfe\x00{")
        with self.assertRaises(SnapshotCorruptError):
            s.load("k")

    def test_sqlite_blob_row_is_corrupt(self) -> None:
        # REGRESSION: a BLOB row raised AttributeError inside the codec.
        db = self.tmp / "s.db"
        s = SQLiteStore(db)
        s.save("k", "{}")
        c = sqlite3.connect(str(db))
        c.execute("UPDATE statecharts SET snapshot = ?", (b"\xff\xfe",))
        c.commit()
        c.close()
        with self.assertRaises(SnapshotCorruptError):
            s.load("k")
        s.close()

    def test_sqlite_oversized_row_refused_on_load(self) -> None:
        db = self.tmp / "s.db"
        s = SQLiteStore(db, max_snapshot_bytes=100)
        s.save("k", "{}")
        c = sqlite3.connect(str(db))
        c.execute("UPDATE statecharts SET snapshot = ?", (" " * 2_000_000,))
        c.commit()
        c.close()
        with self.assertRaises(SnapshotTooLargeError):
            s.load("k")
        s.close()

    def test_from_snapshot_deep_nesting_is_library_error(self) -> None:
        # REGRESSION: RecursionError from `json.loads` in `from_snapshot`.
        m = wallet()
        with self.assertRaises(XStateMachineError):
            SyncInterpreter.from_snapshot("[" * 100_000 + "]" * 100_000, m)

    def test_from_snapshot_spaces_blob_is_library_error(self) -> None:
        with self.assertRaises(XStateMachineError):
            SyncInterpreter.from_snapshot(" " * 2_000_000, wallet())

    def test_wrong_expected_hash_refused(self) -> None:
        i = SyncInterpreter(wallet()).start()
        blob = i.get_snapshot()
        i.stop()
        with self.assertRaises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(
                blob, wallet(), expected_machine_hash="0" * 64
            )

    def test_dunder_keys_restore_as_plain_data(self) -> None:
        i = SyncInterpreter(wallet()).start()
        snap = json.loads(i.get_snapshot())
        i.stop()
        snap["context"]["evil"] = {
            "__class__": "os.system",
            "__reduce__": ["os.system", ["echo pwned"]],
        }
        r = SyncInterpreter.from_snapshot(json.dumps(snap), wallet())
        self.assertIs(type(r.context["evil"]), dict)
        self.assertEqual(r.context["evil"]["__class__"], "os.system")


# =============================================================================
# X0.5 -- redaction, file modes, keys, forget
# =============================================================================
class TestX05Redaction(unittest.TestCase):
    def test_nested_lists_and_case(self) -> None:
        v = {
            "Authorization": "Bearer x",
            "headers": [{"AUTHORIZATION": "y"}, {"x-api-key": "z"}],
            "Password": 1,
            "password": 2,
            "note": "my password is hunter2",
        }
        out = redact(v)
        self.assertEqual(out["Authorization"], "***")
        self.assertEqual(out["headers"][0]["AUTHORIZATION"], "***")
        self.assertEqual(out["headers"][1]["x-api-key"], "***")  # REGRESSION
        self.assertEqual((out["Password"], out["password"]), ("***", "***"))
        # 📝 Key denylist only: secrets INSIDE string values pass through.
        self.assertEqual(out["note"], "my password is hunter2")
        self.assertEqual(v["Authorization"], "Bearer x")  # pure

    def test_user_denylist_spelled_with_hyphen_still_matches(self) -> None:
        # 🐛 Review M1 (fixed): normalising only the data-side key broke a
        #    user `redact_keys=("x-custom-token",)` -- both sides now agree.
        out = redact(
            {"X-Custom-Token": "s", "x_custom_token": "t", "other": "u"},
            keys=("x-custom-token",),
        )
        self.assertEqual(out["X-Custom-Token"], "***")
        self.assertEqual(out["x_custom_token"], "***")
        self.assertEqual(out["other"], "u")


class TestX05Store(_TmpDir):
    @unittest.skipIf(os.name != "posix", "POSIX file modes; NTFS uses ACLs")
    def test_file_modes(self) -> None:
        s = FileStore(self.tmp / "fs")
        s.save("k", "{}")
        self.assertEqual(os.stat(s.directory).st_mode & 0o777, 0o700)
        rec = s.directory / "k.xsm.json"
        self.assertEqual(os.stat(rec).st_mode & 0o777, 0o600)

    def test_validate_key_rejects(self) -> None:
        for bad in ("", "\x00", "a\x00b", "x" * 10_000, None, b"k"):
            with self.subTest(key=repr(bad)[:12]):
                with self.assertRaises(InvalidKeyError):
                    validate_key(bad)  # type: ignore[arg-type]

    def test_filestore_path_keys(self) -> None:
        s = FileStore(self.tmp / "fs")
        for bad in ("..", ".", "/", "\\", "a/b", "a\\b", "../x"):
            with self.subTest(key=bad):
                with self.assertRaises(InvalidKeyError):
                    s.save(bad, "{}")
        # Opaque, encoded, contained in the directory:
        ok = ["C:", "C:x", "con", "a%2Fb", "é", "é", "‮"]
        for k in ok:
            s.save(k, json.dumps(k))
        self.assertEqual(sorted(s.list_keys()), sorted(ok))
        for k in ok:  # no collision: %2F vs '/', NFC vs NFD
            self.assertEqual(json.loads(s.load(k).snapshot), k)
        for name in os.listdir(s.directory):
            self.assertNotIn(":", name)

    def test_sqlite_forget_erases_every_table(self) -> None:
        # REGRESSION: the shared `transitions` table survived forget().
        db = self.tmp / "s.db"
        store = SQLiteStore(db)
        log = SQLiteLog(store)
        dl = Deadline("m.s", 1, time.time() + 60, 60000, "after.60000.m.s")
        store.save("k", "{}", deadlines=[dl])
        p = TransitionLogPlugin(log, machine_id=lambda i: "k")
        i = SyncInterpreter(wallet()).use(p).start()
        i.send("CREDIT", amount=1)
        i.stop()
        self.assertTrue(log.read("k"))
        out = store.forget("k")
        self.assertEqual(out["snapshots"], 1)
        self.assertEqual(out["deadlines"], 1)
        self.assertGreaterEqual(out["log_entries"], 1)
        c = sqlite3.connect(str(db))
        for table, col in (
            ("statecharts", "key"),
            ("deadlines", "key"),
            ("transitions", "machine_id"),
        ):
            n = c.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} = 'k'"
            ).fetchone()[0]
            self.assertEqual(n, 0, table)
        c.close()
        store.close()

    def test_filestore_forget_leaves_no_file(self) -> None:
        s = FileStore(self.tmp / "fs")
        s.save("k", "{}")
        with s.lock("k"):
            pass
        s.forget("k")
        self.assertEqual(
            [n for n in os.listdir(s.directory) if n.startswith("k")], []
        )


# =============================================================================
# X0.9 -- durable timers
# =============================================================================
TIMER = {
    "id": "r",
    "initial": "waiting",
    "context": {"fired": 0},
    "states": {
        "waiting": {"after": {"5000": {"target": "done", "actions": "n"}}},
        "done": {"type": "final"},
    },
}


def _n(i: Any, c: Any, e: Any, a: Any) -> None:
    c["fired"] += 1


def timer_machine() -> Any:
    return create_machine(TIMER, logic=MachineLogic(actions={"n": _n}))


class TestX09Timers(_TmpDir):
    def _seed(self, store: Any, key: str = "k") -> None:
        with persisted(
            store, key, timer_machine(), clock=SimulatedClock(wall_start=0)
        ):
            pass  # due at wall 5.0

    def test_two_workers_fire_each_deadline_once(self) -> None:
        db = self.tmp / "s.db"
        seed = SQLiteStore(db)
        for n in range(4):
            self._seed(seed, f"k{n}")
        seed.close()
        totals: List[int] = []
        barrier = threading.Barrier(2)

        def worker() -> None:
            st = SQLiteStore(db)
            sc = DueTimerScanner(
                st, lambda k: timer_machine(), lock=PessimisticLock()
            )
            barrier.wait()
            totals.append(sc.run_once(now=10.0))
            st.close()

        ts = [threading.Thread(target=worker) for _ in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sum(totals), 4)
        st = SQLiteStore(db)
        for n in range(4):
            snap = json.loads(st.load(f"k{n}").snapshot)
            self.assertEqual(snap["context"]["fired"], 1)
        st.close()

    def test_clock_jump_backwards_fires_nothing_keeps_deadline(
        self,
    ) -> None:
        store = SQLiteStore(self.tmp / "s.db")
        self._seed(store)
        sc = DueTimerScanner(store, lambda k: timer_machine())
        self.assertEqual(sc.run_once(now=-1e9), 0)
        self.assertEqual(len(store.load("k").deadlines), 1)
        self.assertEqual(sc.run_once(now=10.0), 1)
        store.close()

    def test_stale_lower_entry_seq_deadline_is_not_fired(self) -> None:
        store = SQLiteStore(self.tmp / "s.db")
        self._seed(store)
        rec = store.load("k")
        (live,) = rec.deadlines
        stale = Deadline(
            live.state_id,
            live.entry_seq - 1,
            1.0,
            live.delay_ms,
            live.event_type,
        )
        store.save(
            "k",
            rec.snapshot,
            expected_version=rec.version,
            deadlines=[stale, live],
        )
        sc = DueTimerScanner(store, lambda k: timer_machine())
        sc.run_once(now=3.0)  # only the stale one is "due"
        snap = json.loads(store.load("k").snapshot)
        self.assertEqual(snap["context"]["fired"], 0)
        self.assertEqual(snap["state_ids"], ["r.waiting"])
        store.close()

    def test_orphan_deadline_after_migration_fails_loudly(self) -> None:
        store = SQLiteStore(self.tmp / "s.db")
        v1 = {**TIMER, "version": "1"}
        m1 = create_machine(v1, logic=MachineLogic(actions={"n": _n}))
        with persisted(store, "k", m1, clock=SimulatedClock(wall_start=0)):
            pass
        v2 = {
            "id": "r",
            "version": "2",
            "initial": "hold",
            "context": {"fired": 0},
            "states": {"hold": {}, "done": {"type": "final"}},
        }
        mig = SnapshotMigrator()
        mig.add(
            "1",
            "2",
            lambda b: {
                **b,
                "state_ids": ["r.hold"],
                "configuration": ["r", "r.hold"],
            },
        )
        sc = DueTimerScanner(store, lambda k: create_machine(v2), migrator=mig)
        self.assertEqual(sc.run_once(now=10.0), 0)
        self.assertEqual([k for k, _ in sc.last_result.errors], ["k"])
        self.assertEqual(len(store.load("k").deadlines), 1)  # not dropped
        store.close()


# =============================================================================
# X0.10 -- schema lifecycle
# =============================================================================
class TestX010Schema(_TmpDir):
    def test_filestore_newer_format_refused_with_upgrade_message(
        self,
    ) -> None:
        s = FileStore(self.tmp / "fs")
        s.save("k", "{}")
        p = s.directory / "k.xsm.json"
        rec = json.loads(p.read_text("utf-8"))
        for fmt in (2, 10**30, "2", None):
            with self.subTest(fmt=fmt):
                p.write_text(json.dumps({**rec, "format": fmt}), "utf-8")
                with self.assertRaises(SnapshotCorruptError) as cm:
                    s.load("k")
                if isinstance(fmt, int):
                    self.assertIn("Upgrade", str(cm.exception))

    def test_sqlite_newer_schema_refused(self) -> None:
        db = self.tmp / "s.db"
        SQLiteStore(db).close()
        c = sqlite3.connect(str(db))
        c.execute("UPDATE xsm_schema SET version = 99")
        c.commit()
        c.close()
        with self.assertRaises(StoreError) as cm:
            SQLiteStore(db)
        self.assertIn("Upgrade", str(cm.exception))

    def test_sqlite_reopen_is_idempotent(self) -> None:
        db = self.tmp / "s.db"
        s = SQLiteStore(db)
        s.save("k", "{}")
        s.close()
        for _ in range(2):
            s = SQLiteStore(db)
            self.assertEqual(s.load("k").version, 1)
            s.close()
        c = sqlite3.connect(str(db))
        rows = c.execute("SELECT version FROM xsm_schema").fetchall()
        c.close()
        self.assertEqual(rows, [(1,)])
