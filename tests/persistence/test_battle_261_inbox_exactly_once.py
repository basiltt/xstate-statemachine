# tests/persistence/test_battle_261_inbox_exactly_once.py
"""Battle #261 part A: the inbox's EXACTLY-ONCE claim under crash and
concurrency.

The guarantee under attack (docs/_guide/guarantees.md): "The state
transition for an idempotency-keyed event: Exactly once" -- i.e. the
action must never run twice with a committed save, and a replay must
never serve another scope's receipt.

Real kills: a child process runs one keyed event inside `persisted()` /
`apersisted()` and `os._exit(9)`s at an injected point of the three-step
dance (claim -> save -> mark). The parent restarts on the same database
and redelivers the SAME payload, then (on a copy of the post-kill files)
a DIFFERENT payload with the same key.
"""

from __future__ import annotations

import asyncio
import faulthandler
import json
import logging
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import unittest
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
    receipt_to_status,
)
from src.xstate_statemachine.persistence import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    IdempotencyPlugin,
    MemoryInbox,
    MemoryStore,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
    apersisted,
    fingerprint,
    persisted,
)
from src.xstate_statemachine.persistence.idempotency import (
    PROCESSED_AT_KEY,
    PROCESSED_RING_SIZE,
    InboxEntry,
)
from src.xstate_statemachine.receipts import ReceiptError

ROOT = pathlib.Path(__file__).resolve().parents[2]
WATCHDOG_S = 60
CHILD_TIMEOUT_S = 30
SCOPE = "acct/wallet/w1"

CFG = {
    "id": "wallet",
    "initial": "open",
    "context": {"credits": 0},
    "states": {
        "open": {
            "on": {
                "CREDIT": {"actions": "add"},
                "BOOM": {"target": "broken", "actions": "boom"},
                "NOPE": {"target": "broken", "guard": "never"},
            }
        },
        "broken": {"on": {"FIX": "open"}},
    },
}


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("kaput: card declined")


def make_machine(effects: Optional[List[int]] = None, hook: Any = None):
    def add(i: Any, c: Any, e: Any, a: Any) -> None:
        c["credits"] += e.payload["amount"]
        if effects is not None:
            effects.append(e.payload["amount"])
        if hook is not None:
            hook(i, c, e)

    return create_machine(
        CFG,
        logic=MachineLogic(
            actions={"add": add, "boom": _boom},
            guards={"never": lambda c, e: False},
        ),
    )


def plugin(inbox: Any, **kw: Any) -> IdempotencyPlugin:
    kw.setdefault("principal", lambda e: "acct")
    return IdempotencyPlugin(inbox, **kw)


def outcome(r: Any) -> str:
    """Classify a keyed send's receipt."""
    if isinstance(r.error, IdempotencyInFlightError):
        return "409"
    if isinstance(r.error, IdempotencyMismatchError):
        return "422"
    if r.duplicate:
        return "duplicate"
    return "admitted"


def committed_credits(store: Any, key: str = "w1") -> int:
    rec = store.load(key)
    return 0 if rec is None else json.loads(rec.snapshot)["context"]["credits"]


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        faulthandler.dump_traceback_later(WATCHDOG_S, exit=True)
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="b261_"))
        self._closers: List[Any] = []

    def tearDown(self) -> None:
        faulthandler.cancel_dump_traceback_later()
        for c in reversed(self._closers):
            try:
                c()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sqlite(self, path: pathlib.Path, **kw: Any) -> SQLiteStore:
        s = SQLiteStore(path, **kw)
        self._closers.append(s.close)
        return s


# =============================================================================
# 💀 Real kills: claim -> save -> mark
# =============================================================================
CHILD = r"""
import asyncio, json, os, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine import create_machine, MachineLogic
from src.xstate_statemachine.persistence import (
    IdempotencyPlugin, MemoryInbox, PessimisticLock, SQLiteInbox,
    SQLiteStore, apersisted, persisted)

def add(i, c, e, a):
    c["credits"] += e.payload["amount"]
    with open(args["effects"], "a") as f:
        f.write("ran\n")

m = create_machine(args["cfg"], logic=MachineLogic(
    actions={"add": add, "boom": lambda *a: None},
    guards={"never": lambda c, e: False}))
store = SQLiteStore(args["db"])
inbox = SQLiteInbox(store) if args["inbox"] == "sqlite" else MemoryInbox()
p = IdempotencyPlugin(inbox, principal=lambda e: "acct")
point = args["point"]

def die():
    os._exit(9)

if point == "after_claim":
    real_claim = inbox.claim
    def claim(*a, **k):
        real_claim(*a, **k)
        die()
    inbox.claim = claim
elif point in ("before_save", "after_save"):
    real_save = store.save
    def save(*a, **k):
        if point == "before_save":
            die()
        real_save(*a, **k)
        die()
    store.save = save
elif point == "after_mark":
    real_mark = inbox.mark
    def mark(*a, **k):
        real_mark(*a, **k)
        die()
    inbox.mark = mark
lock = PessimisticLock(timeout=5) if args["lock"] == "pess" else None
if args["engine"] == "sync":
    with persisted(store, "w1", m, plugins=[p], lock=lock) as i:
        i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
else:
    async def go():
        async with apersisted(store, "w1", m, plugins=[p], lock=lock) as i:
            await i.send("CREDIT", wait=True, idempotency_key="evt_1",
                         amount=10)
    asyncio.run(go())
sys.exit(3)  # the kill point was never reached
"""


def run_child(args: Dict[str, Any]) -> int:
    proc = subprocess.Popen(
        [sys.executable, "-c", CHILD, json.dumps(args)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _out, err = proc.communicate(timeout=CHILD_TIMEOUT_S)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
    if proc.returncode != 9:
        raise AssertionError(
            f"child exited {proc.returncode}, expected the injected kill: "
            f"{err.decode(errors='replace')[-2000:]}"
        )
    return proc.returncode


#: The MEASURED crash-window table (after the battle fixes):
#: (point, inbox, lock) -> (same payload, different payload, effects runs)
EXPECTED = {
    # SQLiteInbox sharing the SQLiteStore file, default OptimisticLock:
    # the claim commits on its own, so a kill before the save leaves an
    # in-flight claim nobody releases -> 409 until the TTL.
    ("after_claim", "sqlite", "opt"): ("409", "422", 0),
    ("before_save", "sqlite", "opt"): ("409", "422", 1),
    ("after_save", "sqlite", "opt"): ("duplicate", "422", 1),
    ("after_mark", "sqlite", "opt"): ("duplicate", "422", 1),
    # PessimisticLock: claim, save and mark share one transaction; a kill
    # anywhere rolls all of it back -> the redelivery is a first delivery.
    ("after_claim", "sqlite", "pess"): ("admitted", "admitted", 0),
    ("before_save", "sqlite", "pess"): ("admitted", "admitted", 1),
    ("after_save", "sqlite", "pess"): ("admitted", "admitted", 1),
    ("after_mark", "sqlite", "pess"): ("admitted", "admitted", 1),
    # MemoryInbox dies with the process; the restart sees an empty inbox.
    # Before the save nothing was persisted (first delivery); after it the
    # snapshot's ring evidence answers (the battle fix).
    ("after_claim", "memory", "opt"): ("admitted", "admitted", 0),
    ("before_save", "memory", "opt"): ("admitted", "admitted", 1),
    ("after_save", "memory", "opt"): ("duplicate", "422", 1),
    ("after_mark", "memory", "opt"): ("duplicate", "422", 1),
}


class TestRealKill(_Base):
    def _kill_then_restart(
        self, point: str, inbox_kind: str, lock: str, engine: str
    ) -> None:
        db = self.tmp / "s.db"
        effects = self.tmp / "effects.log"
        run_child(
            {
                "root": str(ROOT),
                "db": str(db),
                "effects": str(effects),
                "inbox": inbox_kind,
                "point": point,
                "lock": lock,
                "engine": engine,
                "cfg": CFG,
            }
        )
        child_runs = (
            len(effects.read_text().splitlines()) if effects.exists() else 0
        )
        # A copy of the post-kill files for the different-payload attack.
        alt = self.tmp / "alt"
        alt.mkdir()
        for suffix in ("", "-wal", "-shm"):
            src = pathlib.Path(str(db) + suffix)
            if src.exists():
                shutil.copy(src, alt / ("s.db" + suffix))
        same_exp, diff_exp, runs_exp = EXPECTED[(point, inbox_kind, lock)]
        self.assertEqual(child_runs, runs_exp, "effects before the kill")

        got_same, credits_same, runs_same = self._redeliver(
            db, inbox_kind, engine, amount=10
        )
        got_diff, credits_diff, _ = self._redeliver(
            alt / "s.db", inbox_kind, engine, amount=11
        )
        self.assertEqual(
            (got_same, got_diff),
            (same_exp, diff_exp),
            f"{point}/{inbox_kind}/{lock}/{engine}",
        )
        # 🔐 The exactly-once line: the committed state reflects the
        #    event ONCE whatever the kill point (409 = not yet, retried
        #    by the client after the TTL/lease; never twice).
        expect_committed = 0 if same_exp == "409" else 10
        self.assertEqual(credits_same, expect_committed)
        if same_exp == "admitted":
            self.assertEqual(runs_same, 1)
        else:
            self.assertEqual(runs_same, 0)
        self.assertEqual(
            credits_diff, 11 if diff_exp == "admitted" else expect_committed
        )

    def _redeliver(
        self, db: pathlib.Path, inbox_kind: str, engine: str, amount: int
    ) -> Tuple[str, int, int]:
        store = self.sqlite(db)
        inbox = SQLiteInbox(store) if inbox_kind == "sqlite" else MemoryInbox()
        effects: List[int] = []
        m = make_machine(effects)
        p = plugin(inbox)
        if engine == "sync":
            with persisted(store, "w1", m, plugins=[p]) as i:
                r = i.send(
                    "CREDIT", wait=True, idempotency_key="evt_1", amount=amount
                )
        else:

            async def go() -> Any:
                async with apersisted(store, "w1", m, plugins=[p]) as i:
                    return await i.send(
                        "CREDIT",
                        wait=True,
                        idempotency_key="evt_1",
                        amount=amount,
                    )

            r = asyncio.run(go())
        return outcome(r), committed_credits(store), len(effects)

    # -- sync, SQLiteInbox shared, OptimisticLock -------------------------
    def test_sqlite_kill_after_claim(self) -> None:
        self._kill_then_restart("after_claim", "sqlite", "opt", "sync")

    def test_sqlite_kill_before_save(self) -> None:
        self._kill_then_restart("before_save", "sqlite", "opt", "sync")

    def test_sqlite_kill_after_save_before_mark(self) -> None:
        self._kill_then_restart("after_save", "sqlite", "opt", "sync")

    def test_sqlite_kill_after_mark(self) -> None:
        self._kill_then_restart("after_mark", "sqlite", "opt", "sync")

    # -- sync, SQLiteInbox shared, PessimisticLock (one transaction) ------
    def test_pessimistic_kill_after_claim_rolls_back(self) -> None:
        self._kill_then_restart("after_claim", "sqlite", "pess", "sync")

    def test_pessimistic_kill_before_save_rolls_back(self) -> None:
        self._kill_then_restart("before_save", "sqlite", "pess", "sync")

    def test_pessimistic_kill_after_save_rolls_back(self) -> None:
        self._kill_then_restart("after_save", "sqlite", "pess", "sync")

    def test_pessimistic_kill_after_mark_rolls_back(self) -> None:
        self._kill_then_restart("after_mark", "sqlite", "pess", "sync")

    # -- sync, MemoryInbox (cannot survive the kill) -----------------------
    def test_memory_kill_after_claim(self) -> None:
        self._kill_then_restart("after_claim", "memory", "opt", "sync")

    def test_memory_kill_before_save(self) -> None:
        self._kill_then_restart("before_save", "memory", "opt", "sync")

    def test_memory_kill_after_save_caught_by_ring_evidence(self) -> None:
        """🐛 CRITICAL regression: the restart's inbox is EMPTY, the
        snapshot says processed; the action used to run a second time on
        top of the committed save."""
        self._kill_then_restart("after_save", "memory", "opt", "sync")

    def test_memory_kill_after_mark_caught_by_ring_evidence(self) -> None:
        self._kill_then_restart("after_mark", "memory", "opt", "sync")

    # -- async engine parity (apersisted) -----------------------------------
    def test_async_sqlite_kill_after_claim(self) -> None:
        self._kill_then_restart("after_claim", "sqlite", "opt", "async")

    def test_async_sqlite_kill_after_save(self) -> None:
        self._kill_then_restart("after_save", "sqlite", "opt", "async")

    def test_async_memory_kill_after_save(self) -> None:
        self._kill_then_restart("after_save", "memory", "opt", "async")

    def test_async_memory_kill_after_mark(self) -> None:
        self._kill_then_restart("after_mark", "memory", "opt", "async")


# =============================================================================
# 🧵 Concurrency beyond 16-threads-one-key
# =============================================================================
CLAIM_CHILD = r"""
import json, os, sys, time
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine.persistence import SQLiteInbox
inbox = SQLiteInbox(args["db"], busy_timeout=20)
open(args["ready"], "w").close()
deadline = time.time() + 20
while not os.path.exists(args["go"]):
    if time.time() > deadline:
        sys.exit(4)
    time.sleep(0.005)
won = [k for k in range(args["n"])
       if inbox.claim("s", "k%d" % k, "fp", ttl_s=None)]
print(json.dumps(won))
"""


class TestConcurrency(_Base):
    def test_16_threads_x_16_keys_scope_isolation(self) -> None:
        """16 instances x the SAME 16 key names, interleaved, one shared
        plugin + SQLiteInbox: every instance credits each key once and a
        full redelivery is all duplicates."""
        store = self.sqlite(self.tmp / "s.db", busy_timeout=20)
        inbox = SQLiteInbox(store)
        p = plugin(inbox)
        m = make_machine()
        errors: List[BaseException] = []
        barrier = threading.Barrier(16)

        def worker(n: int, amount: int) -> None:
            try:
                barrier.wait(timeout=10)
                for attempt in range(50):
                    try:
                        with persisted(store, f"w{n}", m, plugins=[p]) as i:
                            for k in range(16):
                                i.send(
                                    "CREDIT",
                                    idempotency_key=f"k{(k + n) % 16}",
                                    amount=amount,
                                )
                        return
                    except Exception:  # noqa: BLE001 - lock contention
                        if attempt == 49:
                            raise
                        time.sleep(0.01)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        for amount in (1, 1):  # first delivery, then a full redelivery
            ts = [
                threading.Thread(target=worker, args=(n, amount))
                for n in range(16)
            ]
            for t in ts:
                t.start()
            for t in ts:
                t.join(timeout=40)
            self.assertFalse(errors, errors[:3])
        for n in range(16):
            self.assertEqual(committed_credits(store, f"w{n}"), 16, n)
            for k in range(16):
                e = inbox.get(f"acct/wallet/w{n}", f"k{k}")
                self.assertIsNotNone(e)
                self.assertIsNotNone(e.receipt_json)

    def test_two_processes_claim_is_atomic(self) -> None:
        """`SQLiteInbox.claim` is SELECT + INSERT OR REPLACE inside BEGIN
        IMMEDIATE: the write lock is taken BEFORE the read, so two
        processes racing the same 150 keys never both win one."""
        db = self.tmp / "inbox.db"
        SQLiteInbox(db).close()
        go = self.tmp / "go"
        procs = []
        try:
            for n in range(2):
                ready = self.tmp / f"ready{n}"
                procs.append(
                    (
                        ready,
                        subprocess.Popen(
                            [
                                sys.executable,
                                "-c",
                                CLAIM_CHILD,
                                json.dumps(
                                    {
                                        "root": str(ROOT),
                                        "db": str(db),
                                        "ready": str(ready),
                                        "go": str(go),
                                        "n": 150,
                                    }
                                ),
                            ],
                            cwd=str(ROOT),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        ),
                    )
                )
            deadline = time.time() + CHILD_TIMEOUT_S
            while not all(r.exists() for r, _ in procs):
                self.assertLess(time.time(), deadline, "children not ready")
                time.sleep(0.01)
            go.touch()
            won: List[List[int]] = []
            for _ready, proc in procs:
                out, err = proc.communicate(timeout=CHILD_TIMEOUT_S)
                self.assertEqual(proc.returncode, 0, err.decode()[-1500:])
                won.append(json.loads(out.decode().strip().splitlines()[-1]))
        finally:
            for _r, proc in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
        a, b = set(won[0]), set(won[1])
        self.assertEqual(a & b, set())
        self.assertEqual(a | b, set(range(150)))

    def _purge_mid_event(self, inbox: Any) -> None:
        effects: List[int] = []

        def purge(i: Any, c: Any, e: Any) -> None:
            if e.payload.get("purge"):
                inbox.purge_expired(now=time.time() + 10**9)

        m = make_machine(effects, hook=purge)
        i = SyncInterpreter(m).use(plugin(inbox)).start()
        r1 = i.send(
            "CREDIT", wait=True, idempotency_key="k", amount=5, purge=True
        )
        self.assertFalse(r1.duplicate)
        r2 = i.send(
            "CREDIT", wait=True, idempotency_key="k", amount=5, purge=True
        )
        i.stop()
        # 🐛 SQLite's mark was an UPDATE of a purged row: a silent no-op,
        #    and the redelivery ran the action AGAIN. MemoryInbox re-
        #    inserted with fingerprint "" -> the redelivery got a bogus 422.
        self.assertEqual(outcome(r2), "duplicate")
        self.assertEqual(effects, [5])

    def test_ttl_purge_between_claim_and_mark_sqlite(self) -> None:
        self._purge_mid_event(SQLiteInbox(self.tmp / "i.db"))

    def test_ttl_purge_between_claim_and_mark_memory(self) -> None:
        self._purge_mid_event(MemoryInbox())

    def test_buffered_marks_are_per_session_sync(self) -> None:
        """🐛 CRITICAL regression: `_buffered` was ONE list for every
        persisted() block sharing the plugin. Block B's post-save flush
        wrote block A's mark; A then crashed before its save, and every
        redelivery of A's event was answered "duplicate" -- the receipt
        promised an effect that was never persisted."""
        store = self.sqlite(self.tmp / "s.db")
        inbox = SQLiteInbox(store)
        p = plugin(inbox)
        m = make_machine()
        inside, gate = threading.Event(), threading.Event()
        seen: Dict[str, Any] = {}

        def block_a() -> None:
            try:
                with persisted(store, "A", m, plugins=[p]) as i:
                    i.send("CREDIT", idempotency_key="ka", amount=5)
                    seen["a_buffering"] = p.buffer_marks
                    inside.set()
                    gate.wait(10)
                    raise RuntimeError("A dies before its save")
            except RuntimeError:
                seen["a_died"] = True

        t = threading.Thread(target=block_a)
        t.start()
        self.assertTrue(inside.wait(10))
        seen["outside_buffering"] = p.buffer_marks
        with persisted(store, "B", m, plugins=[p]) as i:
            i.send("CREDIT", idempotency_key="kb", amount=1)
        mid = inbox.get("acct/wallet/A", "ka")
        gate.set()
        t.join(10)
        self.assertEqual(
            seen,
            {"a_buffering": True, "outside_buffering": False, "a_died": True},
        )
        self.assertIsNone(mid.receipt_json)  # still in flight, NOT marked
        self.assertIsNone(inbox.get("acct/wallet/A", "ka"))  # released
        with persisted(store, "A", m, plugins=[p]) as i:
            r = i.send("CREDIT", wait=True, idempotency_key="ka", amount=5)
        self.assertEqual(outcome(r), "admitted")
        self.assertEqual(committed_credits(store, "A"), 5)
        self.assertEqual(committed_credits(store, "B"), 1)

    def test_buffered_marks_are_per_session_async(self) -> None:
        """Same attack on one event loop: two `apersisted` blocks
        interleaved by `gather` share the plugin (contextvars per task)."""
        store = self.sqlite(self.tmp / "s.db")
        inbox = SQLiteInbox(store)
        p = plugin(inbox)
        m = make_machine()

        async def go() -> Any:
            a_in, b_done = asyncio.Event(), asyncio.Event()
            mid: Dict[str, Any] = {}

            async def a() -> None:
                with self.assertRaises(RuntimeError):
                    async with apersisted(store, "A", m, plugins=[p]) as i:
                        await i.send(
                            "CREDIT", wait=True, idempotency_key="ka", amount=5
                        )
                        a_in.set()
                        await b_done.wait()
                        mid["ka"] = inbox.get("acct/wallet/A", "ka")
                        raise RuntimeError("A dies before its save")

            async def b() -> None:
                await a_in.wait()
                async with apersisted(store, "B", m, plugins=[p]) as i:
                    await i.send(
                        "CREDIT", wait=True, idempotency_key="kb", amount=1
                    )
                b_done.set()

            await asyncio.wait_for(asyncio.gather(a(), b()), 20)
            async with apersisted(store, "A", m, plugins=[p]) as i:
                r = await i.send(
                    "CREDIT", wait=True, idempotency_key="ka", amount=5
                )
            return mid["ka"], r

        mid, r = asyncio.run(go())
        self.assertIsNone(mid.receipt_json)
        self.assertEqual(outcome(r), "admitted")
        self.assertEqual(committed_credits(store, "A"), 5)

    def test_stop_releases_only_its_own_claims(self) -> None:
        """🐛 Stopping interpreter B released interpreter A's live claim
        (the plugin's `_pending` was cleared wholesale)."""
        inbox = MemoryInbox()
        p = plugin(inbox)
        m = make_machine()
        ia = SyncInterpreter(m).use(p).start()
        ib = SyncInterpreter(m).use(p).start()
        ev = SimpleNamespace(
            type="CREDIT", payload={"idempotency_key": "k", "amount": 1}
        )
        self.assertIsNone(p.on_before_send(ia, ev))
        scope_a = p.scope_for(ia, ev)
        ib.stop()
        self.assertIsNotNone(inbox.get(scope_a, "k"))  # A's claim survives
        ia.stop()
        self.assertIsNone(inbox.get(scope_a, "k"))  # released by its owner

    def test_async_pessimistic_shared_sqlite_inbox_refuses_not_admits(
        self,
    ) -> None:
        """`apersisted(lock=PessimisticLock())` holds the SQLite write lock
        on the adapter's worker thread; the inbox's claim runs on the loop
        thread's connection and cannot get it. 🐛 It used to raise inside
        the (fail-open) hook -> admitted with NO claim and no mark, so
        every redelivery ran again on a committed save. Now: a loud
        refusal (`LockTimeoutError`, 500) and nothing runs."""
        store = self.sqlite(self.tmp / "s.db", busy_timeout=0.2)
        inbox = SQLiteInbox(store)
        effects: List[int] = []
        m = make_machine(effects)
        p = plugin(inbox)

        async def go() -> List[Any]:
            out = []
            for _ in range(2):
                async with apersisted(
                    store,
                    "w1",
                    m,
                    plugins=[p],
                    lock=PessimisticLock(timeout=5),
                ) as i:
                    out.append(
                        await i.send(
                            "CREDIT", wait=True, idempotency_key="k", amount=3
                        )
                    )
            return out

        rs = asyncio.run(go())
        for r in rs:
            self.assertEqual(type(r.error).__name__, "LockTimeoutError")
            self.assertEqual(receipt_to_status(r), 500)
        self.assertEqual(effects, [])
        self.assertEqual(committed_credits(store), 0)


# =============================================================================
# 💍 The in-snapshot ring vs inbox truth
# =============================================================================
class TestRingVsInbox(_Base):
    def _process(self, store: Any, inbox: Any, **kw: Any) -> None:
        with persisted(store, "w1", make_machine(), plugins=[plugin(inbox)]):
            pass
        with persisted(
            store, "w1", make_machine(), plugins=[plugin(inbox, **kw)]
        ) as i:
            i.send("CREDIT", idempotency_key="evt_1", amount=10)

    def _send(self, store: Any, inbox: Any, amount: int = 10, **kw: Any):
        effects: List[int] = []
        with persisted(
            store, "w1", make_machine(effects), plugins=[plugin(inbox, **kw)]
        ) as i:
            r = i.send(
                "CREDIT", wait=True, idempotency_key="evt_1", amount=amount
            )
        return outcome(r), effects

    def test_ring_processed_inbox_in_flight_different_payload_is_422(
        self,
    ) -> None:
        store = MemoryStore()
        inbox = MemoryInbox()
        self._process(store, inbox)
        inbox._rows[(SCOPE, "evt_1")] = InboxEntry(
            inbox.get(SCOPE, "evt_1").fingerprint, None, None
        )  # the mark "never happened"
        self.assertEqual(self._send(store, inbox, amount=99), ("422", []))
        self.assertEqual(self._send(store, inbox), ("duplicate", []))
        self.assertIsNotNone(inbox.get(SCOPE, "evt_1").receipt_json)

    def test_ring_empty_inbox_processed_answers_from_inbox(self) -> None:
        store = MemoryStore()
        inbox = MemoryInbox()
        self._process(store, inbox)
        rec = store.load("w1")
        snap = json.loads(rec.snapshot)
        snap["context"].pop("__xsm_processed_ids__")
        snap["context"].pop(PROCESSED_AT_KEY)
        store.save("w1", json.dumps(snap))
        self.assertEqual(self._send(store, inbox), ("duplicate", []))

    def test_ring_evicted_inbox_still_has_key(self) -> None:
        store = MemoryStore()
        inbox = MemoryInbox()
        self._process(store, inbox)
        with persisted(
            store, "w1", make_machine(), plugins=[plugin(inbox)]
        ) as i:
            for n in range(PROCESSED_RING_SIZE + 1):
                i.send("CREDIT", idempotency_key=f"x{n}", amount=0)
            ctx = i.context
            self.assertNotIn(f"{SCOPE}|evt_1", ctx["__xsm_processed_ids__"])
            # evidence is bounded with the ring
            self.assertEqual(len(ctx[PROCESSED_AT_KEY]), PROCESSED_RING_SIZE)
        self.assertEqual(self._send(store, inbox), ("duplicate", []))

    def test_ring_evicted_and_inbox_lost_readmits_documented_limit(
        self,
    ) -> None:
        """The net is the last 64 keys: a key evicted from the ring AND
        lost from a non-durable inbox is a first delivery again."""
        store = MemoryStore()
        self._process(store, MemoryInbox())
        with persisted(
            store, "w1", make_machine(), plugins=[plugin(MemoryInbox())]
        ) as i:
            for n in range(PROCESSED_RING_SIZE + 1):
                i.send("CREDIT", idempotency_key=f"x{n}", amount=0)
        self.assertEqual(self._send(store, MemoryInbox()), ("admitted", [10]))

    def test_ring_evidence_respects_ttl(self) -> None:
        """Evidence older than the TTL is a genuine expiry: re-admitted,
        exactly as the inbox's own TTL would (guarantees.md, ring is not
        a second inbox)."""
        store = MemoryStore()
        self._process(store, MemoryInbox(), ttl_s=0.05)
        time.sleep(0.1)
        self.assertEqual(
            self._send(store, MemoryInbox(), ttl_s=0.05), ("admitted", [10])
        )

    def test_pre_evidence_snapshot_keeps_old_behaviour(self) -> None:
        """A snapshot written before this fix has the ring but no
        evidence map: an empty inbox re-admits, as it always did."""
        store = MemoryStore()
        self._process(store, MemoryInbox())
        snap = json.loads(store.load("w1").snapshot)
        snap["context"].pop(PROCESSED_AT_KEY)
        store.save("w1", json.dumps(snap))
        self.assertEqual(self._send(store, MemoryInbox()), ("admitted", [10]))


# =============================================================================
# 🔏 Fingerprint edge cases
# =============================================================================
def ev(payload: Dict[str, Any], type_: str = "CREDIT") -> Any:
    return SimpleNamespace(type=type_, payload=payload)


class TestFingerprint(_Base):
    def test_nested_key_order_is_canonical(self) -> None:
        a = {"x": {"b": 1, "a": [1, {"q": 1, "p": 2}]}, "y": 2}
        b = {"y": 2, "x": {"a": [1, {"p": 2, "q": 1}], "b": 1}}
        self.assertEqual(fingerprint(ev(a)), fingerprint(ev(b)))

    def test_list_order_matters(self) -> None:
        self.assertNotEqual(
            fingerprint(ev({"l": [1, 2]})), fingerprint(ev({"l": [2, 1]}))
        )

    def test_float_one_vs_int_one_differ(self) -> None:
        """Documented: ``1.0`` and ``1`` canonicalise differently, so a
        client that re-serialises an amount as float gets a 422."""
        self.assertNotEqual(
            fingerprint(ev({"amount": 1})), fingerprint(ev({"amount": 1.0}))
        )
        i = SyncInterpreter(make_machine()).use(plugin(MemoryInbox())).start()
        i.send("CREDIT", wait=True, idempotency_key="k", amount=1)
        r = i.send("CREDIT", wait=True, idempotency_key="k", amount=1.0)
        i.stop()
        self.assertEqual(receipt_to_status(r), 422)

    def test_key_fields_custom_and_missing(self) -> None:
        kf = ("a",)
        self.assertEqual(
            fingerprint(ev({"a": 1, "b": 2}), key_fields=kf),
            fingerprint(ev({"b": 2}), key_fields=kf),
        )
        # the default key fields are now part of the fingerprint
        self.assertNotEqual(
            fingerprint(ev({"b": 2, "id": 1}), key_fields=kf),
            fingerprint(ev({"b": 2, "id": 2}), key_fields=kf),
        )

    def test_type_is_part_of_fingerprint(self) -> None:
        self.assertNotEqual(fingerprint(ev({}, "A")), fingerprint(ev({}, "B")))

    def test_non_json_values_use_str_and_dedupe(self) -> None:
        """`datetime` / `Decimal` / bytes do not crash: canonical JSON
        uses ``str()``. Measured consequence: ``Decimal('1.0')`` and
        ``Decimal('1.00')`` differ."""
        when = datetime(2026, 1, 1, tzinfo=timezone.utc)
        fp = fingerprint(ev({"t": when, "d": Decimal("1.0"), "b": b"x"}))
        self.assertEqual(
            fp, fingerprint(ev({"t": when, "d": Decimal("1.0"), "b": b"x"}))
        )
        self.assertNotEqual(
            fingerprint(ev({"d": Decimal("1.0")})),
            fingerprint(ev({"d": Decimal("1.00")})),
        )
        effects: List[int] = []
        i = SyncInterpreter(make_machine(effects)).use(plugin(MemoryInbox()))
        i.start()
        for _ in range(2):
            r = i.send(
                "CREDIT", wait=True, idempotency_key="k", amount=1, t=when
            )
        i.stop()
        self.assertTrue(r.duplicate)
        self.assertEqual(effects, [1])

    def test_uncanonicalisable_payload_is_refused_not_admitted(self) -> None:
        """🐛 ``{1: .., "a": ..}`` makes ``sort_keys`` raise TypeError in
        the hook; fail-open ADMITTED it with no claim, so every
        redelivery ran the action again. Now a typed refusal."""
        effects: List[int] = []
        i = SyncInterpreter(make_machine(effects)).use(plugin(MemoryInbox()))
        i.start()
        rs = [
            i.send(
                "CREDIT",
                wait=True,
                idempotency_key="k",
                amount=1,
                meta={1: "x", "y": 2},
            )
            for _ in range(2)
        ]
        i.stop()
        self.assertEqual(effects, [])
        for r in rs:
            self.assertIsInstance(r.error, ValueError)
            self.assertIn("cannot be fingerprinted", str(r.error))

    def test_one_megabyte_payload_is_cheap(self) -> None:
        big = {"blob": "x" * (1 << 20), "n": list(range(1000))}
        t0 = time.perf_counter()
        fingerprint(ev(big))
        self.assertLess(time.perf_counter() - t0, 1.0)

    def test_unicode_nfc_vs_nfd_differ(self) -> None:
        """Measured, not normalised: the same visible string in NFC and
        NFD is a DIFFERENT payload (422 on reuse). Undocumented; noted."""
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        self.assertNotEqual(nfc, nfd)
        self.assertNotEqual(
            fingerprint(ev({"s": nfc})), fingerprint(ev({"s": nfd}))
        )


# =============================================================================
# 🧾 Receipt replay fidelity
# =============================================================================
class TestReplayFidelity(_Base):
    def _twice(self, m: Any, etype: str, **payload: Any) -> Tuple[Any, Any]:
        i = SyncInterpreter(m).use(plugin(MemoryInbox())).start()
        r1 = i.send(etype, wait=True, idempotency_key="k", **payload)
        r2 = i.send(etype, wait=True, idempotency_key="k", **payload)
        i.stop()
        return r1, r2

    def test_errored_receipt_replays_same_error_and_status(self) -> None:
        r1, r2 = self._twice(make_machine(), "BOOM")
        self.assertIsInstance(r1.error, RuntimeError)
        self.assertIsInstance(r2.error, ReceiptError)
        self.assertEqual(r2.error.type, "RuntimeError")
        self.assertEqual(r2.error.message, "kaput: card declined")
        self.assertTrue(r2.duplicate)
        self.assertEqual(receipt_to_status(r1), receipt_to_status(r2))
        self.assertEqual(receipt_to_status(r2), 500)
        self.assertEqual(r1.state_ids, r2.state_ids)

    def test_denied_receipt_replays_409(self) -> None:
        r1, r2 = self._twice(make_machine(), "NOPE")
        self.assertTrue(r1.denied and r2.denied and r2.duplicate)
        self.assertEqual(
            (receipt_to_status(r1), receipt_to_status(r2)), (409, 409)
        )

    def test_deferred_receipt_replays_202(self) -> None:
        cfg = {
            "id": "d",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {
                "a": {"on": {"LATER": "c"}},
                "c": {"on": {"WAIT_FOR_ME": "a"}},
            },
        }
        r1, r2 = self._twice(create_machine(cfg), "WAIT_FOR_ME")
        self.assertTrue(r1.deferred and r2.deferred and r2.duplicate)
        self.assertEqual(
            (receipt_to_status(r1), receipt_to_status(r2)), (202, 202)
        )

    def test_fifty_state_ids_round_trip(self) -> None:
        cfg = {
            "id": "p",
            "type": "parallel",
            "on": {"GO": {"actions": "noop"}},
            "states": {
                f"r{n}": {"initial": "s", "states": {"s": {}}}
                for n in range(50)
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(actions={"noop": lambda *a: None})
        )
        r1, r2 = self._twice(m, "GO")
        self.assertEqual(len(r1.state_ids), 50)
        self.assertEqual(r1.state_ids, r2.state_ids)
        self.assertTrue(r2.duplicate)

    def test_corrupt_cached_receipt_is_conservative_duplicate(self) -> None:
        """🐛 A hand-edited cached receipt made `receipt_from_json` raise
        ValueError in the (fail-open) hook: the event was ADMITTED and the
        action ran again. The key WAS processed; answer a duplicate."""
        for bad in ('{"bad": 1}', "{truncated", "[]", '"str"'):
            with self.subTest(bad=bad):
                effects: List[int] = []
                inbox = MemoryInbox()
                p = plugin(inbox)
                i = SyncInterpreter(make_machine(effects)).use(p).start()
                i.send("CREDIT", wait=True, idempotency_key="k", amount=1)
                scope = p.scope_for(i, None)
                e = inbox.get(scope, "k")
                inbox._rows[(scope, "k")] = InboxEntry(
                    e.fingerprint, bad, e.expires_at
                )
                with self.assertLogs(
                    "src.xstate_statemachine.persistence.idempotency",
                    logging.WARNING,
                ):
                    r = i.send(
                        "CREDIT", wait=True, idempotency_key="k", amount=1
                    )
                i.stop()
                self.assertEqual(outcome(r), "duplicate")
                self.assertIsNone(r.error)
                self.assertEqual(effects, [1])

    def test_inbox_failure_refuses_not_admits(self) -> None:
        class Broken(MemoryInbox):
            def get(self, scope: str, key: str) -> Any:
                raise OSError("inbox down")

        effects: List[int] = []
        i = SyncInterpreter(make_machine(effects)).use(plugin(Broken()))
        i.start()
        r = i.send("CREDIT", wait=True, idempotency_key="k", amount=1)
        i.stop()
        self.assertIsInstance(r.error, OSError)
        self.assertEqual(receipt_to_status(r), 500)
        self.assertEqual(effects, [])


# =============================================================================
# ⚖️ Cross-engine batch / threadsafe paths
# =============================================================================
class TestEnginePaths(_Base):
    def test_send_events_same_key_twice_in_one_batch_sync(self) -> None:
        """Measured: the batch intercepts every event BEFORE processing
        any, so the second sees the first's claim IN FLIGHT -> refused
        (409-shaped, silently: `send_events` returns nothing)."""
        effects: List[int] = []
        inbox = MemoryInbox()
        i = SyncInterpreter(make_machine(effects)).use(plugin(inbox)).start()
        e = {"type": "CREDIT", "idempotency_key": "k", "amount": 2}
        i.send_events([dict(e), dict(e)])
        r = i.send("CREDIT", wait=True, idempotency_key="k", amount=2)
        i.stop()
        self.assertEqual(effects, [2])
        self.assertEqual(outcome(r), "duplicate")

    def test_send_events_same_key_twice_in_one_batch_async(self) -> None:
        effects: List[int] = []

        async def go() -> Any:
            i = (
                await Interpreter(make_machine(effects))
                .use(plugin(MemoryInbox()))
                .start()
            )
            e = {"type": "CREDIT", "idempotency_key": "k", "amount": 2}
            await i.send_events([dict(e), dict(e)])
            await asyncio.sleep(0.1)  # let the loop process the batch
            r = await i.send(
                "CREDIT", wait=True, idempotency_key="k", amount=2
            )
            await i.stop()
            return r

        r = asyncio.run(go())
        self.assertEqual(effects, [2])
        self.assertEqual(outcome(r), "duplicate")

    def test_send_threadsafe_claims_at_drain_on_owner_thread(self) -> None:
        effects: List[int] = []
        inbox = MemoryInbox()
        p = plugin(inbox)
        i = SyncInterpreter(make_machine(effects)).use(p).start()
        scope = p.scope_for(i, None)
        for _ in range(2):
            t = threading.Thread(
                target=i.send_threadsafe,
                args=("CREDIT",),
                kwargs={"idempotency_key": "k", "amount": 4},
            )
            t.start()
            t.join(5)
        self.assertIsNone(inbox.get(scope, "k"))  # nothing claimed yet
        i.tick()
        i.stop()
        self.assertEqual(effects, [4])
        self.assertIsNotNone(inbox.get(scope, "k").receipt_json)


# =============================================================================
# 🔐 Principal + scope round trip
# =============================================================================
class TestScopeRoundTrip(_Base):
    PARTS = [
        "plain",
        "a/b",
        "a%2Fb",
        "a%b",
        "x|y",
        "ünï-☃-𝄞",
        "p" * 200,
        "%/|" * 60,
    ]

    def _scopes(self) -> Dict[Tuple[str, str], str]:
        m = make_machine()
        i = SyncInterpreter(m)
        out = {}
        for principal in self.PARTS:
            for inst in self.PARTS:
                p = IdempotencyPlugin(
                    MemoryInbox(),
                    principal=lambda e, pr=principal: pr,
                    instance_key=lambda _i, k=inst: k,
                )
                out[(principal, inst)] = p.scope_for(i, None)
        return out

    def test_scopes_are_injective(self) -> None:
        scopes = self._scopes()
        self.assertEqual(len(set(scopes.values())), len(scopes))

    def _forget_exactly(self, inbox: Any) -> None:
        scopes = self._scopes()
        for s in scopes.values():
            self.assertTrue(inbox.claim(s, "k", "fp", ttl_s=None))
            inbox.mark(s, "k", "{}", ttl_s=None)
        victim = scopes[("a/b", "x|y")]
        self.assertEqual(inbox.forget(victim), 1)
        for s in scopes.values():
            got = inbox.get(s, "k")
            if s == victim:
                self.assertIsNone(got)
            else:
                self.assertIsNotNone(got, s)
                self.assertEqual(got.fingerprint, "fp")

    def test_forget_erases_exactly_one_scope_memory(self) -> None:
        self._forget_exactly(MemoryInbox())

    def test_forget_erases_exactly_one_scope_sqlite(self) -> None:
        inbox = SQLiteInbox(self.tmp / "i.db")
        self._closers.append(inbox.close)
        self._forget_exactly(inbox)

    def test_cross_scope_replay_never_served(self) -> None:
        """Principal "a/b" + instance "c" vs principal "a" + instance
        "b/c": a receipt cached under one is never a replay for the
        other."""
        inbox = SQLiteInbox(self.tmp / "i.db")
        self._closers.append(inbox.close)
        effects: List[int] = []
        m = make_machine(effects)
        for principal, inst in (("a/b", "c"), ("a", "b/c")):
            p = IdempotencyPlugin(
                inbox,
                principal=lambda e, pr=principal: pr,
                instance_key=lambda _i, k=inst: k,
            )
            i = SyncInterpreter(m).use(p).start()
            r = i.send("CREDIT", wait=True, idempotency_key="k", amount=1)
            i.stop()
            self.assertEqual(outcome(r), "admitted")
        self.assertEqual(effects, [1, 1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
