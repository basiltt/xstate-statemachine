# tests/persistence/test_battle_261_inbox_failures.py
"""#261 battle part B: inbox backend failure injection at every plugin call
site, TTL / clock semantics, key / scope contracts, leaks and cost.

unittest only (no pytest-asyncio).
"""

from __future__ import annotations

import asyncio
import gc
import os
import random
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from src.xstate_statemachine import (
    Event,
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import StoreError
from src.xstate_statemachine.persistence import (
    IdempotencyInFlightError,
    IdempotencyPlugin,
    MemoryInbox,
    MemoryStore,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
    persisted,
)
from src.xstate_statemachine.persistence import idempotency as idem
from src.xstate_statemachine.persistence.idempotency import (
    InboxEntry,
    PROCESSED_RING_SIZE,
    _expiry,
    fingerprint,
    validate_idempotency_key,
)

LIB = "xstate_statemachine"

CFG: Dict[str, Any] = {
    "id": "wallet",
    "initial": "open",
    "context": {"credits": 0},
    "states": {"open": {"on": {"CREDIT": {"actions": "add"}}}},
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["credits"] += e.payload.get("amount", 1)


def machine() -> Any:
    return create_machine(CFG, logic=MachineLogic(actions={"add": _add}))


class FaultyInbox:
    """Delegates to a real inbox; ``fail_next[op] = Exc`` raises once."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.fail_next: Dict[str, BaseException] = {}
        self.fail_always: Dict[str, BaseException] = {}
        self.calls: List[str] = []

    def _go(self, op: str) -> None:
        self.calls.append(op)
        exc = self.fail_next.pop(op, None) or self.fail_always.get(op)
        if exc is not None:
            raise exc

    def get(self, *a: Any, **k: Any) -> Any:
        self._go("get")
        return self.inner.get(*a, **k)

    def claim(self, *a: Any, **k: Any) -> Any:
        self._go("claim")
        return self.inner.claim(*a, **k)

    def mark(self, *a: Any, **k: Any) -> Any:
        self._go("mark")
        return self.inner.mark(*a, **k)

    def release(self, *a: Any, **k: Any) -> Any:
        self._go("release")
        return self.inner.release(*a, **k)

    def purge_expired(self, *a: Any, **k: Any) -> Any:
        self._go("purge")
        return self.inner.purge_expired(*a, **k)

    def forget(self, *a: Any, **k: Any) -> Any:
        self._go("forget")
        return self.inner.forget(*a, **k)


class ErrCollector(PluginBase[Any]):
    def __init__(self) -> None:
        self.errors: List[Any] = []

    def on_plugin_error(self, *args: Any, **kw: Any) -> None:
        self.errors.append(args)


class FakeClock:
    def __init__(self, t: float) -> None:
        self.t = t

    def time(self) -> float:
        return self.t


def _plugin(inbox: Any, **kw: Any) -> IdempotencyPlugin:
    kw.setdefault("principal", lambda e: "acct")
    return IdempotencyPlugin(inbox, **kw)


def _leak_ceiling() -> int:
    tracer = sys.gettrace() is not None or (
        hasattr(sys, "monitoring")
        and sys.monitoring.get_tool(sys.monitoring.COVERAGE_ID) is not None
    )
    return 6_000_000 if tracer else 256 * 1024


def _lib_bytes(snap: Any) -> int:
    stats = snap.filter_traces(
        [tracemalloc.Filter(True, f"*{LIB}*")]
    ).statistics("filename")
    return sum(s.size for s in stats)


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._closers: List[Any] = []
        self.addCleanup(self._close_all)

    def _close_all(self) -> None:
        for c in self._closers:
            try:
                c.close()
            except Exception:
                pass

    def sqlite_inbox(self, name: str = "inbox.db") -> SQLiteInbox:
        ib = SQLiteInbox(Path(self.tmp) / name)
        self._closers.append(ib)
        return ib

    def inboxes(self) -> List[Any]:
        return [MemoryInbox(), self.sqlite_inbox()]

    def run_one(self, inbox: Any, **kw: Any):
        col = ErrCollector()
        it = SyncInterpreter(machine()).use(col).use(_plugin(inbox, **kw))
        it.start()
        return it, col


# -----------------------------------------------------------------------------
# Backend failure at every plugin call site
# -----------------------------------------------------------------------------
class TestBackendFailures(_Base):
    EXCS = [
        StoreError("dead"),
        OSError("disk gone"),
        sqlite3.OperationalError("database is locked"),
    ]

    def test_get_raises_admits_event_fail_open(self) -> None:
        """A DEAD inbox admits the event (duplicates run) -- fail-open.
        This is the DEFAULT (`on_inbox_error="admit"`): availability over
        dedup, documented in persistence.md and security.md X0.2."""
        for exc in self.EXCS:
            with self.subTest(exc=type(exc).__name__):
                fb = FaultyInbox(MemoryInbox())
                it, col = self.run_one(fb, on_inbox_error="admit")
                it.send("CREDIT", wait=True, idempotency_key="k", amount=1)
                fb.fail_always["get"] = exc
                r = it.send("CREDIT", wait=True, idempotency_key="k", amount=1)
                # duplicate was NOT refused: machine ran twice
                self.assertFalse(r.duplicate)
                self.assertTrue(r.changed)
                self.assertEqual(it.context["credits"], 2)
                self.assertTrue(col.errors)  # but reported

    def test_refuse_mode_never_runs_the_action_on_a_dead_inbox(self) -> None:
        """🛡️ Battle #261 (integration): `on_inbox_error="refuse"` -- the
        receipt carries `InboxUnavailableError` (HTTP 503), the action did
        NOT run, nothing is claimed. Both `get` and `claim` failing; every
        infrastructure error class."""
        from src.xstate_statemachine.persistence import (
            InboxUnavailableError,
        )
        from src.xstate_statemachine.receipts import receipt_to_status

        for site in ("get", "claim"):
            for exc in self.EXCS:
                with self.subTest(site=site, exc=type(exc).__name__):
                    fb = FaultyInbox(MemoryInbox())
                    it, col = self.run_one(fb, on_inbox_error="refuse")
                    fb.fail_always[site] = exc
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key="k", amount=1
                    )
                    self.assertIsInstance(r.error, InboxUnavailableError)
                    self.assertEqual(r.error.key, "k")
                    self.assertIs(r.error.cause, exc)
                    self.assertTrue(r.duplicate)  # "did not run" shape
                    self.assertFalse(r.changed)
                    self.assertEqual(receipt_to_status(r), 503)
                    self.assertEqual(it.context["credits"], 0)
                    # the plugin's OWN refusals are not masked by refuse mode
                    fb.fail_always.pop(site)
                    it.send("CREDIT", wait=True, idempotency_key="k", amount=1)
                    r2 = it.send(
                        "CREDIT", wait=True, idempotency_key="k", amount=2
                    )
                    self.assertEqual(
                        type(r2.error).__name__, "IdempotencyMismatchError"
                    )

    def test_refuse_mode_async_parity(self) -> None:
        from src.xstate_statemachine import Interpreter
        from src.xstate_statemachine.persistence import (
            InboxUnavailableError,
        )

        async def go() -> Any:
            fb = FaultyInbox(MemoryInbox())
            fb.fail_always["get"] = StoreError("dead")
            it = await (
                Interpreter(machine())
                .use(_plugin(fb, on_inbox_error="refuse"))
                .start()
            )
            r = await it.send(
                "CREDIT", wait=True, idempotency_key="k", amount=1
            )
            credits = it.context["credits"]
            await it.stop()
            return r, credits

        r, credits = asyncio.run(go())
        self.assertIsInstance(r.error, InboxUnavailableError)
        self.assertEqual(credits, 0)

    def test_on_inbox_error_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            _plugin(MemoryInbox(), on_inbox_error="ignore")

    def test_claim_raises_admits_event_without_protection(self) -> None:
        for exc in self.EXCS:
            with self.subTest(exc=type(exc).__name__):
                fb = FaultyInbox(MemoryInbox())
                it, col = self.run_one(fb, on_inbox_error="admit")
                fb.fail_next["claim"] = exc
                r = it.send("CREDIT", wait=True, idempotency_key="k", amount=1)
                self.assertFalse(r.duplicate)
                self.assertIsNone(r.error)
                self.assertEqual(it.context["credits"], 1)
                self.assertTrue(col.errors)
                # nothing was claimed, so no entry exists
                (
                    self.assertIsNone(fb.inner.get(*self._only(fb.inner)))
                    if len(getattr(fb.inner, "_rows", {}))
                    else None
                )

    @staticmethod
    def _only(inner: Any) -> Any:
        return next(iter(inner._rows))

    def test_mark_raises_leaves_inflight_with_bounded_expiry(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                fb = FaultyInbox(base)
                it, col = self.run_one(fb, ttl_s=100)
                fb.fail_next["mark"] = OSError("mark failed")
                r1 = it.send(
                    "CREDIT", wait=True, idempotency_key="m", amount=3
                )
                self.assertTrue(r1.changed)
                self.assertTrue(col.errors)
                scope = idem.IdempotencyPlugin.scope_for(
                    it.plugin_obj if False else _plugin(fb), it, Event("X")
                )
                e = base.get(scope, "m")
                self.assertIsNotNone(e)
                self.assertIsNone(e.receipt_json)  # in flight
                # claim stamped an expiry => a crashed worker is bounded by ttl
                self.assertIsNotNone(e.expires_at)
                self.assertLess(e.expires_at - time.time(), 101)
                # replay in same interpreter: ring repairs it, answers dup
                r2 = it.send(
                    "CREDIT", wait=True, idempotency_key="m", amount=3
                )
                self.assertTrue(r2.duplicate)
                self.assertEqual(it.context["credits"], 3)

    def test_inflight_without_ring_is_409_until_ttl_then_fresh(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                it, _ = self.run_one(base, ttl_s=1)
                pl = _plugin(base)
                scope = pl.scope_for(it, Event("X"))
                base.claim(scope, "w", "fp-x", ttl_s=1)  # crashed worker
                r = it.send("CREDIT", wait=True, idempotency_key="w", amount=1)
                # fingerprint differs -> mismatch (422) not 409; use the
                # real fingerprint to see the in-flight answer

                fp = fingerprint(Event("CREDIT", {"amount": 1}))
                base.release(scope, "w")
                base.claim(scope, "w", fp, ttl_s=1)
                r = it.send("CREDIT", wait=True, idempotency_key="w", amount=1)
                self.assertIsInstance(r.error, IdempotencyInFlightError)
                self.assertEqual(it.context["credits"], 0)
                time.sleep(1.1)
                r = it.send("CREDIT", wait=True, idempotency_key="w", amount=1)
                self.assertIsNone(r.error)
                self.assertEqual(it.context["credits"], 1)

    def test_inflight_with_ttl_none_never_expires(self) -> None:
        """Documented bound: an in-flight claim lives ttl_s; with
        ttl_s=None a crashed worker blocks the key forever."""
        ib = MemoryInbox()
        ib.claim("s", "k", "fp", ttl_s=None)
        e = ib.get("s", "k")
        self.assertIsNone(e.expires_at)
        self.assertEqual(ib.purge_expired(now=1e18), 0)
        self.assertFalse(ib.claim("s", "k", "fp", ttl_s=None))

    def test_purge_raises_is_not_swallowed_by_inbox_but_contained_by_caller(
        self,
    ) -> None:
        fb = FaultyInbox(MemoryInbox())
        fb.fail_next["purge"] = OSError("x")
        with self.assertRaises(OSError):
            fb.purge_expired()
        self.assertEqual(fb.purge_expired(), 0)  # healthy again
        # the plugin never purges on the hot path: a send is unaffected
        fb.fail_always["purge"] = OSError("x")
        it, col = self.run_one(fb)
        r = it.send("CREDIT", wait=True, idempotency_key="p", amount=1)
        self.assertTrue(r.changed)
        self.assertFalse(col.errors)
        self.assertNotIn("purge", fb.calls[2:])

    def test_forget_raises_surfaces_to_caller(self) -> None:
        fb = FaultyInbox(MemoryInbox())
        fb.fail_next["forget"] = StoreError("x")
        with self.assertRaises(StoreError):
            fb.forget("s")
        self.assertEqual(fb.forget("s"), 0)

    def test_release_failure_on_stop_is_suppressed(self) -> None:
        fb = FaultyInbox(MemoryInbox())
        it, _ = self.run_one(fb)
        pl = it._plugins[-1]
        pl = getattr(pl, "wrapped", pl)
        pl._pending[1] = ("s", "k")
        fb.fail_always["release"] = OSError("x")
        it.stop()  # must not raise

    def test_buffered_flush_failure_partial_marks(self) -> None:
        """Flush raises for entry 2 of 3: marks 1 is written, 3 is NOT
        (flush aborts at the first failure); 2 and 3 stay in flight -- the
        conservative-duplicate window (ring repairs on replay)."""
        base = MemoryInbox()
        fb = FaultyInbox(base)
        pl = _plugin(fb)
        pl.buffer_marks = True
        it = SyncInterpreter(machine()).use(pl).start()
        for k in ("a", "b", "c"):
            it.send("CREDIT", wait=True, idempotency_key=k, amount=1)
        # 📝 buffers are per `persisted()` session (#261 A fix); outside
        #    any block the session token is None -- one bucket of 3
        self.assertEqual(sum(len(v) for v in pl._buffered.values()), 3)
        scope = pl.scope_for(it, Event("X"))
        real_mark = base.mark
        n = {"i": 0}

        def flaky(*a: Any, **k: Any) -> None:
            n["i"] += 1
            if n["i"] == 2:
                raise OSError("flush fail")
            real_mark(*a, **k)

        with mock.patch.object(base, "mark", flaky):
            with self.assertRaises(OSError):
                pl.flush_marks()
        self.assertIsNotNone(base.get(scope, "a").receipt_json)
        self.assertIsNone(base.get(scope, "b").receipt_json)
        self.assertIsNone(base.get(scope, "c").receipt_json)
        # replay of the unmarked ones: ring says processed -> duplicate
        for k in ("b", "c"):
            r = it.send("CREDIT", wait=True, idempotency_key=k, amount=1)
            self.assertTrue(r.duplicate)
        self.assertEqual(it.context["credits"], 3)

    def test_buffered_flush_failure_via_persisted_marks_all_or_raises(
        self,
    ) -> None:
        store = SQLiteStore(Path(self.tmp) / "s.db")
        self._closers.append(store)
        inbox = SQLiteInbox(store)
        pl = _plugin(inbox)
        with persisted(
            store, "w1", machine(), lock=PessimisticLock(), plugins=[pl]
        ) as w:
            w.send("CREDIT", wait=True, idempotency_key="x1", amount=1)
            w.send("CREDIT", wait=True, idempotency_key="x2", amount=1)
        scope = pl.scope_for(
            type(
                "I", (), {"machine": machine(), "store_key": "w1", "id": "i"}
            )(),
            Event("X"),
        )
        self.assertIsNotNone(inbox.get(scope, "x1").receipt_json)
        self.assertIsNotNone(inbox.get(scope, "x2").receipt_json)

    def test_entry_receipt_shapes_never_raise_from_hook(self) -> None:
        for base in self.inboxes():
            for rj in (None, "", "{not json", "[]", "null", '{"x":1}'):
                with self.subTest(base=type(base).__name__, rj=rj):
                    it, col = self.run_one(base)
                    pl = _plugin(base)
                    scope = pl.scope_for(it, Event("X"))

                    fp = fingerprint(Event("CREDIT", {"amount": 1}))
                    base.claim(scope, "z", fp, ttl_s=None)
                    if rj is not None:
                        base.mark(scope, "z", rj, ttl_s=None)
                    # must never raise out of send
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key="z", amount=1
                    )
                    self.assertIsNotNone(r)
                    if rj in ("", "{not json", "[]", "null", '{"x":1}'):
                        # corrupt receipt -> hook error contained, admitted
                        # or typed; never an escaped JSONDecodeError
                        self.assertTrue(
                            col.errors or r.error is not None or r.duplicate
                        )


# -----------------------------------------------------------------------------
# TTL and clock
# -----------------------------------------------------------------------------
class TestTTL(_Base):
    def _patched(self, clock: FakeClock):
        return mock.patch.object(idem, "time", clock)

    def test_ttl_window_and_same_answer_promise(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                clk = FakeClock(1_000_000.0)
                with self._patched(clk):
                    it, _ = self.run_one(base, ttl_s=1)
                    r1 = it.send(
                        "CREDIT", wait=True, idempotency_key="t", amount=1
                    )
                    clk.t += 0.5
                    r2 = it.send(
                        "CREDIT", wait=True, idempotency_key="t", amount=1
                    )
                    self.assertTrue(r2.duplicate)
                    self.assertEqual(it.context["credits"], 1)
                    clk.t += 1.0  # t=1.5 past ttl (marked at 0 => exp 1.0)
                    r3 = it.send(
                        "CREDIT", wait=True, idempotency_key="t", amount=1
                    )
                    self.assertFalse(r3.duplicate)
                    self.assertEqual(it.context["credits"], 2)
                    # old receipt gone: a replay now sees the NEW receipt
                    r4 = it.send(
                        "CREDIT", wait=True, idempotency_key="t", amount=1
                    )
                    self.assertTrue(r4.duplicate)
                    self.assertEqual(it.context["credits"], 2)
                    self.assertEqual(r4.state_ids, r3.state_ids)
                    del r1

    def test_ttl_none_never_expires(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                clk = FakeClock(1.0)
                with self._patched(clk):
                    it, _ = self.run_one(base, ttl_s=None)
                    it.send("CREDIT", wait=True, idempotency_key="n", amount=1)
                    clk.t = 1e12
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key="n", amount=1
                    )
                    self.assertTrue(r.duplicate)
                    self.assertEqual(base.purge_expired(now=1e15), 0)

    def test_ttl_zero_every_send_is_fresh(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                clk = FakeClock(50.0)
                with self._patched(clk):
                    it, _ = self.run_one(base, ttl_s=0)
                    for _ in range(3):
                        r = it.send(
                            "CREDIT", wait=True, idempotency_key="z", amount=1
                        )
                        self.assertFalse(r.duplicate)
                    self.assertEqual(it.context["credits"], 3)

    def test_invalid_ttl_rejected_at_construction(self) -> None:
        for bad in (-1, -0.001, float("nan"), "7", True):
            with self.subTest(ttl=bad):
                with self.assertRaises(ValueError):
                    _plugin(MemoryInbox(), ttl_s=bad)
        _plugin(MemoryInbox(), ttl_s=float("inf"))  # forever: allowed
        _plugin(MemoryInbox(), ttl_s=0)

    def test_clock_backwards_does_not_purge_early(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                clk = FakeClock(1_000_000.0)
                with self._patched(clk):
                    it, _ = self.run_one(base, ttl_s=3600)
                    it.send("CREDIT", wait=True, idempotency_key="b", amount=1)
                    clk.t -= 3600  # NTP step back 1h
                    self.assertEqual(base.purge_expired(), 0)
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key="b", amount=1
                    )
                    self.assertTrue(r.duplicate)
                    self.assertEqual(it.context["credits"], 1)

    def test_clock_forwards_past_ttl_purges(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                clk = FakeClock(1_000_000.0)
                with self._patched(clk):
                    it, _ = self.run_one(base, ttl_s=3600)
                    it.send("CREDIT", wait=True, idempotency_key="f", amount=1)
                    clk.t += 3601
                    self.assertEqual(base.purge_expired(), 1)

    def test_expiry_special_values(self) -> None:
        inf, nan = float("inf"), float("nan")
        self.assertEqual(_expiry(10, inf), inf)
        self.assertEqual(_expiry(inf, 5.0), inf)
        self.assertTrue(_expiry(10, nan) != _expiry(10, nan))  # nan
        self.assertIsNone(_expiry(None, inf))
        # nan expiry reads as expired (never blocks a key forever)
        ib = MemoryInbox()
        ib._rows[("s", "k")] = InboxEntry("fp", None, nan)
        self.assertIsNone(ib.get("s", "k"))

    def test_sqlite_purge_cost_scales_with_expired_rows(self) -> None:
        ib = self.sqlite_inbox()
        conn = ib._conn()
        plan = conn.execute(
            "EXPLAIN QUERY PLAN DELETE FROM inbox WHERE expires_at IS NOT "
            "NULL AND expires_at <= ?",
            (1.0,),
        ).fetchall()
        self.assertIn("inbox_exp", " ".join(str(r) for r in plan))
        t0 = time.perf_counter()
        self.assertEqual(ib.purge_expired(now=1e15), 0)
        empty = time.perf_counter() - t0
        with ib._store._tx(conn, immediate=True):
            conn.executemany(
                "INSERT INTO inbox VALUES (?,?,?,?,?)",
                [("s", f"k{i}", "fp", "{}", 1.0) for i in range(10_000)],
            )
        t0 = time.perf_counter()
        self.assertEqual(ib.purge_expired(now=2.0), 10_000)
        full = time.perf_counter() - t0
        print(
            f"\n[261B] sqlite purge: 0 expired {empty * 1e3:.2f} ms; "
            f"10k expired {full * 1e3:.1f} ms"
        )
        self.assertLess(empty, 0.25)
        self.assertLess(full, 10.0)


# -----------------------------------------------------------------------------
# Key / scope contracts
# -----------------------------------------------------------------------------
class TestKeyScope(_Base):
    def test_validate_hostile_keys_typed(self) -> None:
        bad = [
            "",
            "x" * 256,
            "a\x00b",
            "a‮b",
            "a\ud800b",
            None,
            b"abc",
            5,
            1.5,
            ["a"],
            "line\nbreak",
            " " * 0,
            "café",
        ]
        for k in bad:
            with self.subTest(key=repr(k)[:20]):
                with self.assertRaises(ValueError):
                    validate_idempotency_key(k)

    def test_max_length_boundary_and_contract_is_ascii_only(self) -> None:
        # contract: <= 255 printable ASCII (NOT 200 + unicode)
        self.assertEqual(validate_idempotency_key("k" * 255), "k" * 255)
        with self.assertRaises(ValueError):
            validate_idempotency_key("k" * 256)
        with self.assertRaises(ValueError):
            validate_idempotency_key("ü")

    def test_case_sensitive_and_byte_exact_roundtrip(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                it, _ = self.run_one(base)
                for k in ("A", "a", "k" * 255, "x y", "%25", "a/b", "'; --"):
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key=k, amount=1
                    )
                    self.assertFalse(r.duplicate, k)
                self.assertEqual(it.context["credits"], 7)
                for k in ("A", "a", "k" * 255, "x y", "%25", "a/b", "'; --"):
                    r = it.send(
                        "CREDIT", wait=True, idempotency_key=k, amount=1
                    )
                    self.assertTrue(r.duplicate, k)
                self.assertEqual(it.context["credits"], 7)

    def test_hostile_key_refused_with_typed_receipt(self) -> None:
        it, col = self.run_one(MemoryInbox())
        for k in ("a\x00b", "x" * 300, "café"):
            r = it.send("CREDIT", wait=True, idempotency_key=k, amount=1)
            self.assertIsInstance(r.error, ValueError)
            self.assertTrue(r.duplicate)
        self.assertEqual(it.context["credits"], 0)

    def test_scope_persisted_vs_inmemory_and_two_inmemory_share(self) -> None:
        pl = _plugin(MemoryInbox())
        m = machine()
        mem1 = SyncInterpreter(m).start()
        mem2 = SyncInterpreter(m).start()
        ev = Event("X")
        # footgun: same machine, both in-memory -> interpreter ids may
        # differ, so assert what the scope actually keys on
        s1, s2 = pl.scope_for(mem1, ev), pl.scope_for(mem2, ev)
        self.assertEqual(s1.endswith("/" + mem1.id), True)
        if mem1.id == mem2.id:
            self.assertEqual(s1, s2)  # shared inbox scope (the footgun)
        store = MemoryStore()
        with persisted(store, "order:1", m) as p:
            sp = pl.scope_for(p, ev)
        self.assertTrue(sp.endswith("/order:1"))
        self.assertNotEqual(sp, s1)

    def test_two_inmemory_same_machine_share_scope_when_same_id(self) -> None:
        """Documented footgun: with an explicit instance_key (or equal
        ids) two interpreters of one machine dedupe each other's keys."""
        inbox = MemoryInbox()
        pl = _plugin(inbox, instance_key=lambda i: "shared")
        a = SyncInterpreter(machine()).use(pl).start()
        b = SyncInterpreter(machine()).use(pl).start()
        a.send("CREDIT", wait=True, idempotency_key="k", amount=1)
        r = b.send("CREDIT", wait=True, idempotency_key="k", amount=1)
        self.assertTrue(r.duplicate)
        self.assertEqual(b.context["credits"], 0)

    def test_forget_exact_scope(self) -> None:
        for base in self.inboxes():
            with self.subTest(base=type(base).__name__):
                for s in ("s1", "s2", "s3"):
                    for k in ("a", "b"):
                        base.claim(s, k, "fp", ttl_s=None)
                        base.mark(s, k, "{}", ttl_s=None)
                self.assertEqual(base.forget("s2"), 2)
                self.assertEqual(base.forget("s2"), 0)
                self.assertEqual(base.forget("missing"), 0)
                self.assertIsNone(base.get("s2", "a"))
                for s in ("s1", "s3"):
                    for k in ("a", "b"):
                        self.assertIsNotNone(base.get(s, k))
                # prefix is not a wildcard
                self.assertEqual(base.forget("s"), 0)
                self.assertEqual(base.forget("%"), 0)

    def test_store_forget_does_not_erase_inbox_rows(self) -> None:
        store = SQLiteStore(Path(self.tmp) / "shared.db")
        self._closers.append(store)
        inbox = SQLiteInbox(store)
        pl = _plugin(inbox)
        with persisted(
            store, "w9", machine(), lock=PessimisticLock(), plugins=[pl]
        ) as w:
            w.send("CREDIT", wait=True, idempotency_key="e", amount=1)
            scope = pl.scope_for(w, Event("X"))
        self.assertIsNotNone(inbox.get(scope, "e"))
        store.forget("w9")
        self.assertIsNotNone(inbox.get(scope, "e"))  # documented
        self.assertEqual(inbox.forget(scope), 1)

    def test_tables_coexist_and_reopen(self) -> None:
        path = Path(self.tmp) / "co.db"
        store = SQLiteStore(path)
        inbox = SQLiteInbox(store)
        inbox.claim("s", "k", "fp", ttl_s=None)
        store.close()
        store2 = SQLiteStore(path)
        self._closers.append(store2)
        inbox2 = SQLiteInbox(store2)  # idempotent schema creation
        self.assertIsNotNone(inbox2.get("s", "k"))
        names = {
            r[0]
            for r in store2._conn().execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertIn("inbox", names)
        self.assertTrue(len(names) >= 2)

    def test_sqlite_inbox_on_foreign_file_is_typed_error(self) -> None:
        p = Path(self.tmp) / "foreign.db"
        p.write_bytes(b"this is not a sqlite database " * 50)
        with self.assertRaises((StoreError, sqlite3.DatabaseError)) as cm:
            SQLiteInbox(p)
        self.assertIsNotNone(cm.exception)
        # a foreign sqlite DB with an incompatible `inbox` table
        q = Path(self.tmp) / "other.db"
        c = sqlite3.connect(str(q))
        c.execute("CREATE TABLE inbox (x INTEGER)")
        c.commit()
        c.close()
        try:
            ib = SQLiteInbox(q)
            self._closers.append(ib)
        except (StoreError, sqlite3.Error):
            return
        with self.assertRaises((StoreError, sqlite3.Error)):
            ib.claim("s", "k", "fp", ttl_s=None)

    def test_memory_inbox_thread_safety(self) -> None:
        ib = MemoryInbox()
        keys = [f"k{i}" for i in range(200)]
        claimed: List[str] = []
        errors: List[BaseException] = []
        lock = threading.Lock()

        def worker(seed: int) -> None:
            rnd = random.Random(seed)
            try:
                for _ in range(1000):
                    k = rnd.choice(keys)
                    if ib.claim("s", k, "fp", ttl_s=None):
                        with lock:
                            claimed.append(k)
                        ib.mark("s", k, "{}", ttl_s=None)
                    ib.get("s", k)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        ts = [threading.Thread(target=worker, args=(n,)) for n in range(32)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(claimed), len(set(claimed)))  # one winner each
        self.assertEqual(len(ib), len(set(claimed)))


# -----------------------------------------------------------------------------
# Leaks & perf
# -----------------------------------------------------------------------------
class TestLeaksPerf(_Base):
    def _sends(self, it: Any, n: int, start: int, unique: bool) -> None:
        for i in range(start, start + n):
            it.send(
                "CREDIT",
                idempotency_key=f"k{i}" if unique else "same",
                amount=1,
            )

    def _measure(self, inbox: Any, unique: bool, n: int = 10_000) -> Any:
        it = SyncInterpreter(machine()).use(_plugin(inbox, ttl_s=60)).start()
        self._sends(it, 200, 0, unique)
        gc.collect()
        tracemalloc.start()
        try:
            self._sends(it, n // 2, 1000, unique)
            gc.collect()
            half = _lib_bytes(tracemalloc.take_snapshot())
            self._sends(it, n // 2, 1000 + n, unique)
            gc.collect()
            full = _lib_bytes(tracemalloc.take_snapshot())
        finally:
            tracemalloc.stop()
        return it, half, full

    def test_same_key_is_flat(self) -> None:
        ib = MemoryInbox()
        _, half, full = self._measure(ib, unique=False)
        self.assertLess(full - half, _leak_ceiling())
        self.assertEqual(len(ib), 1)

    def test_unique_keys_grow_linearly_and_purge_reclaims(self) -> None:
        ib = MemoryInbox()
        _, half, full = self._measure(ib, unique=True)
        grown = full - half
        n_half = 5_000
        print(f"\n[261B] memory inbox: {grown / n_half:.0f} B/entry")
        # it MUST grow, roughly by the entries (>= 100 B each)
        self.assertGreater(grown, n_half * 100)
        # but not absurdly (< 2 KB each)
        self.assertLess(grown, n_half * 2048)
        self.assertGreaterEqual(len(ib), 10_000)
        gc.collect()
        tracemalloc.start()
        try:
            probe = [object() for _ in range(0)]
            del probe
            removed = ib.purge_expired(now=time.time() + 3600)
            gc.collect()
        finally:
            tracemalloc.stop()
        self.assertGreaterEqual(removed, 10_000)
        self.assertEqual(len(ib), 0)
        self.assertEqual(len(ib._rows), 0)

    def test_sqlite_unique_keys_file_size_and_purge(self) -> None:
        ib = self.sqlite_inbox("big.db")
        pl = _plugin(ib, ttl_s=60)
        it = SyncInterpreter(machine()).use(pl).start()
        for i in range(10_000):
            it.send("CREDIT", idempotency_key=f"u{i}", amount=1)
        path = Path(self.tmp) / "big.db"
        grown = path.stat().st_size
        rows = ib._conn().execute("SELECT COUNT(*) FROM inbox").fetchone()[0]
        self.assertEqual(rows, 10_000)
        removed = ib.purge_expired(now=time.time() + 3600)
        self.assertEqual(removed, 10_000)
        # reclaim: rows gone; file may keep free pages (document), but a
        # re-fill must REUSE them rather than grow again
        for i in range(10_000):
            ib.claim("s", f"r{i}", "fp", ttl_s=60)
        refilled = path.stat().st_size
        print(
            f"\n[261B] sqlite inbox 10k rows: {grown / 1e6:.2f} MB; after "
            f"purge+refill {refilled / 1e6:.2f} MB"
        )
        self.assertLess(refilled, grown * 1.3)

    def test_ring_is_bounded(self) -> None:
        ib = MemoryInbox()
        it = SyncInterpreter(machine()).use(_plugin(ib, ttl_s=60)).start()
        for i in range(100_000 // 10):  # 10k sends; ring checked per send
            it.send("CREDIT", idempotency_key=f"r{i}", amount=1)
            if i % 1000 == 0:
                self.assertLessEqual(
                    len(it.context["__xsm_processed_ids__"]),
                    PROCESSED_RING_SIZE,
                )
        self.assertEqual(
            len(it.context["__xsm_processed_ids__"]), PROCESSED_RING_SIZE
        )
        # direct bound with 100k distinct keys through the helpers
        pl = _plugin(ib)
        fake = type("I", (), {"context": {}})()
        for i in range(100_000):
            ring = pl._ring(fake)
            ring.append(f"s|{i}")
            pl._store_ring(fake, ring)
        self.assertEqual(
            len(fake.context["__xsm_processed_ids__"]), PROCESSED_RING_SIZE
        )

    def test_per_send_cost_report(self) -> None:
        n = 3000
        bare = SyncInterpreter(machine()).start()
        t0 = time.perf_counter()
        for _ in range(n):
            bare.send("CREDIT", amount=1)
        t_bare = (time.perf_counter() - t0) / n
        res = {}
        for name, ib in (
            ("memory", MemoryInbox()),
            ("sqlite", self.sqlite_inbox("perf.db")),
        ):
            it = SyncInterpreter(machine()).use(_plugin(ib)).start()
            t0 = time.perf_counter()
            for i in range(n):
                it.send("CREDIT", idempotency_key=f"p{i}", amount=1)
            res[name] = (time.perf_counter() - t0) / n
        print(
            f"\n[261B] per-send: bare {t_bare * 1e6:.0f} us; plugin+memory "
            f"{res['memory'] * 1e6:.0f} us; plugin+sqlite "
            f"{res['sqlite'] * 1e6:.0f} us"
        )
        self.assertLess(res["memory"], 0.01)


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("PYTHONHASHSEED", "0")
    unittest.main()
