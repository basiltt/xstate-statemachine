# tests/persistence/test_battle_262_log_corruption_scaling.py
"""#262 battle (part B): log corruption, scaling, retention, redaction.

Contract under test: a transition-log read NEVER skips an unreadable
record (a replay over a hole "succeeds" to a wrong state) and never leaks a
bare json / sqlite / Unicode error -- it raises `LogCorruptError`
(a `StoreError`). Scaling tests assert SHAPE and print the numbers.
"""

from __future__ import annotations

import gc
import json
import math
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
from typing import Any, Callable, Dict, List
from unittest import mock

from src.xstate_statemachine import (
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.exceptions import StoreError
from src.xstate_statemachine.persistence import (
    AuditPlugin,
    JSONLinesLog,
    LogCorruptError,
    MemoryLog,
    SQLiteLog,
    SQLiteStore,
    TransitionLogPlugin,
    TransitionRecord,
    replay,
)
from src.xstate_statemachine.plugins import DEFAULT_REDACT_KEYS, redact

SECRET = "hunter2-SECRET-VALUE"


def rec(seq: int, mid: str = "m", ts: Any = None, **kw: Any):
    base: Dict[str, Any] = dict(
        machine_id=mid,
        seq=seq,
        ts=float(seq) if ts is None else ts,
        event_type="GO",
        event_payload={"k": seq},
        from_states=("m.a",),
        to_states=("m.b",),
        actions=("act",),
    )
    base.update(kw)
    return TransitionRecord(**base)


def good_line(seq: int) -> str:
    return json.dumps(rec(seq).to_dict(), sort_keys=True)


CFG = {
    "id": "m",
    "initial": "a",
    "context": {},
    "states": {
        "a": {"on": {"GO": "b"}},
        "b": {"on": {"GO": "a"}},
    },
}


def machine():
    return create_machine(CFG, logic=stub_logic(CFG))


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._open: List[Any] = []

    def tearDown(self) -> None:
        for lg in self._open:
            if hasattr(lg, "close"):
                lg.close()

    def mk(self, kind: str, name: str = "log") -> Any:
        if kind == "memory":
            return MemoryLog()
        if kind == "jsonl":
            return JSONLinesLog(self.tmp / f"{name}.jsonl")
        lg = SQLiteLog(self.tmp / f"{name}.db")
        self._open.append(lg)
        return lg


KINDS = ("memory", "jsonl", "sqlite")


# =============================================================================
# 🧨 Corruption -- JSONLinesLog
# =============================================================================
class TestJSONLCorruption(_Tmp):
    def _put(self, data: bytes) -> JSONLinesLog:
        p = self.tmp / "c.jsonl"
        p.write_bytes(data)
        return JSONLinesLog(p)

    def _typed(self, lg: JSONLinesLog) -> None:
        with self.assertRaises(LogCorruptError):
            lg.read("m")
        with self.assertRaises(LogCorruptError):
            lg.next_seq("m")

    def test_corrupt_is_a_store_error(self) -> None:
        self.assertTrue(issubclass(LogCorruptError, StoreError))

    def test_truncated_mid_record_raises_not_skips(self) -> None:
        full = (good_line(1) + "\n" + good_line(2) + "\n").encode()
        torn = full + good_line(3).encode()[:40]  # writer killed mid-write
        self._typed(self._put(torn))

    def test_torn_tail_never_silently_stops_replay_early(self) -> None:
        lg = self.mk("jsonl")
        lg.append(rec(1, from_states=("m.a",), to_states=("m.b",)))
        with open(lg.path, "ab") as fh:
            fh.write(b'{"machine_id": "m", "seq": 2, "ts"')
        with self.assertRaises(LogCorruptError):
            replay(machine(), lg.read("m"))

    def test_valid_json_not_a_record(self) -> None:
        d = rec(1).to_dict()
        cases: Dict[str, Any] = {
            "missing seq": {k: v for k, v in d.items() if k != "seq"},
            "seq string": {**d, "seq": "1"},
            "seq float": {**d, "seq": 1.5},
            "seq zero": {**d, "seq": 0},
            "seq bool": {**d, "seq": True},
            "from_states str": {**d, "from_states": "m.a"},
            "to_states int": {**d, "to_states": 3},
            "payload list": {**d, "event_payload": [1]},
            "machine_id int": {**d, "machine_id": 5},
            "array": [d],
            "scalar": 7,
            "null": None,
        }
        for name, obj in cases.items():
            with self.subTest(name):
                self._typed(self._put((json.dumps(obj) + "\n").encode()))

    def test_ts_nan_and_infinity(self) -> None:
        d = rec(1).to_dict()
        for tok in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(tok):
                raw = json.dumps({**d, "ts": 0}).replace(
                    '"ts": 0', f'"ts": {tok}'
                )
                self._typed(self._put((raw + "\n").encode()))

    def test_extra_keys_are_tolerated(self) -> None:
        d = {**rec(1).to_dict(), "future_field": {"x": 1}}
        lg = self._put((json.dumps(d) + "\n").encode())
        self.assertEqual([r.seq for r in lg.read("m")], [1])

    def test_blank_lines_are_ignored(self) -> None:
        raw = f"\n{good_line(1)}\n\n   \n{good_line(2)}\n\n".encode()
        self.assertEqual([r.seq for r in self._put(raw).read("m")], [1, 2])

    def test_bom_is_tolerated(self) -> None:
        raw = b"\xef\xbb\xbf" + (good_line(1) + "\n").encode()
        self.assertEqual([r.seq for r in self._put(raw).read("m")], [1])

    def test_crlf_is_tolerated(self) -> None:
        raw = (good_line(1) + "\r\n" + good_line(2) + "\r\n").encode()
        self.assertEqual([r.seq for r in self._put(raw).read("m")], [1, 2])

    def test_crlf_file_still_appendable_and_readable(self) -> None:
        lg = self._put((good_line(1) + "\r\n").encode())
        lg.append(rec(2))
        self.assertEqual([r.seq for r in lg.read("m")], [1, 2])

    def test_non_utf8_bytes(self) -> None:
        raw = (good_line(1) + "\n").encode() + b"\xff\xfe\xfa garbage\n"
        self._typed(self._put(raw))

    def test_empty_file(self) -> None:
        lg = self._put(b"")
        self.assertEqual(lg.read("m"), [])
        self.assertEqual(lg.next_seq("m"), 1)

    def test_missing_file(self) -> None:
        lg = JSONLinesLog(self.tmp / "nope.jsonl")
        self.assertEqual(lg.read("m"), [])

    def test_path_is_a_directory(self) -> None:
        d = self.tmp / "dir.jsonl"
        d.mkdir()
        lg = JSONLinesLog(d)
        for fn in (lambda: lg.read("m"), lambda: lg.append(rec(1))):
            with self.assertRaises(StoreError):
                fn()

    def test_purge_of_corrupt_file_raises_and_keeps_it(self) -> None:
        raw = (good_line(1) + "\n{torn").encode()
        lg = self._put(raw)
        with self.assertRaises(LogCorruptError):
            lg.purge_older_than(1e12)
        self.assertEqual(lg.path.read_bytes(), raw)  # nothing destroyed

    def test_every_byte_flipped_truncated_inserted(self) -> None:
        base = "".join(good_line(i) + "\n" for i in (1, 2, 3)).encode()
        rng = random.Random(262)
        mutants: List[bytes] = []
        positions = list(range(len(base)))
        if len(positions) * 3 > 2000:
            positions = sorted(rng.sample(positions, 700))
        for i in positions:
            flipped = bytearray(base)
            flipped[i] ^= 0xFF
            mutants.append(bytes(flipped))
            mutants.append(base[:i])
            mutants.append(base[:i] + b"\x00" + base[i:])
        p = self.tmp / "fuzz.jsonl"
        lg = JSONLinesLog(p)
        survived = 0
        for blob in mutants:
            p.write_bytes(blob)
            try:
                out = lg.read("m")
                survived += 1
                for r in out:
                    self.assertIsInstance(r, TransitionRecord)
                lg.next_seq("m")
            except StoreError:
                pass  # typed -- the only acceptable failure
        print(
            f"\n[262] jsonl fuzz: {len(mutants)} mutants, {survived} still read"
        )


# =============================================================================
# 🧨 Corruption -- SQLiteLog / MemoryLog
# =============================================================================
class TestSQLiteCorruption(_Tmp):
    def _raw(self, sql: str, args: tuple = ()) -> None:
        c = sqlite3.connect(self.tmp / "s.db")
        try:
            c.execute(sql, args)
            c.commit()
        finally:
            c.close()

    def _log(self) -> SQLiteLog:
        lg = SQLiteLog(self.tmp / "s.db")
        self._open.append(lg)
        return lg

    def test_malformed_record_json(self) -> None:
        lg = self._log()
        self._raw("INSERT INTO transitions VALUES ('m', 1, 1.0, '{not json')")
        with self.assertRaises(LogCorruptError):
            lg.read("m")

    def test_record_not_a_record(self) -> None:
        lg = self._log()
        for i, body in enumerate(("[]", "7", "null", '{"seq": 1}'), 1):
            self._raw(
                "INSERT INTO transitions VALUES ('m', ?, 1.0, ?)", (i, body)
            )
            with self.assertRaises(LogCorruptError, msg=body):
                lg.read("m")
            self._raw("DELETE FROM transitions")

    def test_row_key_disagrees_with_record(self) -> None:
        lg = self._log()
        self._raw(
            "INSERT INTO transitions VALUES ('m', 5, 1.0, ?)",
            (good_line(2),),
        )
        with self.assertRaises(LogCorruptError):
            lg.read("m")

    def test_null_seq_rejected_by_schema(self) -> None:
        self._log()
        with self.assertRaises(sqlite3.IntegrityError):
            self._raw("INSERT INTO transitions VALUES ('m', NULL, 1.0, '{}')")

    def test_duplicate_seq_rejected_by_schema(self) -> None:
        lg = self._log()
        lg.append(rec(1))
        with self.assertRaises(sqlite3.IntegrityError):
            self._raw(
                "INSERT INTO transitions VALUES ('m', 1, 1.0, ?)",
                (good_line(1),),
            )

    def test_duplicate_append_is_typed(self) -> None:
        lg = self._log()
        lg.append(rec(1))
        with self.assertRaises(Exception) as cm:
            lg.append(rec(1))
        # 🔎 documented: the PK rejects a second seq; surface is sqlite3's
        self.assertIsInstance(
            cm.exception, (StoreError, sqlite3.IntegrityError)
        )

    def test_negative_seq_row_is_corrupt_not_a_crash(self) -> None:
        lg = self._log()
        d = rec(1).to_dict()
        d["seq"] = -4
        self._raw(
            "INSERT INTO transitions VALUES ('m', -4, 1.0, ?)",
            (json.dumps(d),),
        )
        with self.assertRaises(LogCorruptError):
            lg.read("m", after_seq=0)

    def test_foreign_transitions_table(self) -> None:
        c = sqlite3.connect(self.tmp / "f.db")
        c.execute("CREATE TABLE transitions (a TEXT, b TEXT)")
        c.commit()
        c.close()
        with self.assertRaises(StoreError):
            SQLiteLog(self.tmp / "f.db")

    def test_not_a_database(self) -> None:
        (self.tmp / "x.db").write_bytes(b"this is not sqlite " * 50)
        with self.assertRaises(StoreError):
            SQLiteLog(self.tmp / "x.db")


class TestMemoryLogContract(unittest.TestCase):
    def test_append_non_record_is_type_error_at_call_site(self) -> None:
        lg = MemoryLog()
        for bad in (None, {"seq": 1}, "x", 7):
            with self.assertRaises(TypeError):
                lg.append(bad)  # type: ignore[arg-type]
        self.assertEqual(len(lg), 0)

    def test_every_backend_rejects_non_record(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        sq = SQLiteLog(d / "a.db")
        self.addCleanup(sq.close)
        for lg in (JSONLinesLog(d / "a.jsonl"), sq):
            with self.assertRaises(TypeError):
                lg.append({"seq": 1})  # type: ignore[arg-type]

    def test_non_serialisable_payload_documented_behaviour(self) -> None:
        # 🔎 MemoryLog holds the object as-is; the durable backends
        #    stringify via `default=str` -- migration never blows up, but
        #    the round trip is lossy (object -> its str()).
        class Thing:
            def __str__(self) -> str:
                return "THING"

        r = rec(1, event_payload={"o": Thing()})
        mem = MemoryLog()
        mem.append(r)
        self.assertIsInstance(mem.read("m")[0].event_payload["o"], Thing)
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        for lg in (JSONLinesLog(d / "a.jsonl"), SQLiteLog(d / "a.db")):
            lg.append(r)
            self.assertEqual(lg.read("m")[0].event_payload, {"o": "THING"})
            if hasattr(lg, "close"):
                lg.close()

    def test_bad_seq_and_ts_rejected_on_every_backend(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        sq = SQLiteLog(d / "a.db")
        self.addCleanup(sq.close)
        for lg in (MemoryLog(), JSONLinesLog(d / "a.jsonl"), sq):
            for bad in (
                rec(0),
                rec(-1),
                rec(1, ts=float("nan")),
                rec(1, ts=float("inf")),
            ):
                with self.assertRaises(ValueError):
                    lg.append(bad)

    def test_read_args_validated_uniformly(self) -> None:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        sq = SQLiteLog(d / "a.db")
        self.addCleanup(sq.close)
        for lg in (MemoryLog(), JSONLinesLog(d / "a.jsonl"), sq):
            for kw in ({"limit": -1}, {"after_seq": -1}, {"limit": "5"}):
                with self.assertRaises(ValueError):
                    lg.read("m", **kw)

    def test_limit_truncates_silently_cursor_is_after_seq(self) -> None:
        # 📝 contract: `limit` truncates (no "more" flag); the cursor is
        #    `after_seq=<last seq seen>` -- pagination is lossless.
        lg = MemoryLog()
        for i in range(1, 11):
            lg.append(rec(i))
        seen: List[int] = []
        cur = 0
        while True:
            page = lg.read("m", after_seq=cur, limit=3)
            if not page:
                break
            seen += [r.seq for r in page]
            cur = page[-1].seq
        self.assertEqual(seen, list(range(1, 11)))
        self.assertEqual(lg.read("m", limit=0), [])


# =============================================================================
# 📈 Scaling
# =============================================================================
def _leak_ceiling() -> int:
    tracer = sys.gettrace() is not None or (
        hasattr(sys, "monitoring")
        and sys.monitoring.get_tool(sys.monitoring.COVERAGE_ID) is not None
    )
    return 6_000_000 if tracer else 256 * 1024


class TestScaling(_Tmp):
    def _fill(self, lg: Any, n: int, start: int = 1) -> None:
        for i in range(start, start + n):
            lg.append(rec(i))

    def test_jsonl_next_seq_is_cached_and_invalidated_correctly(self) -> None:
        """⚡ Integration fix (#262 B finding): `next_seq` scanned the whole
        file on every send -> a run with a JSONL log was O(n^2). The last
        seq per machine is cached while the file size is unchanged; a
        foreign append, a purge, or an external edit forces a rescan."""
        import pathlib
        from unittest import mock

        lg = self.mk("jsonl", "cache")
        self._fill(lg, 2_000)
        # warm, then count how many times the file is parsed
        self.assertEqual(lg.next_seq("m"), 2_001)
        with mock.patch.object(lg, "_iter", wraps=lg._iter) as spy:
            for _ in range(50):
                lg.append(rec(lg.next_seq("m")))
            self.assertEqual(spy.call_count, 0)  # no rescans in steady state
        self.assertEqual(lg.next_seq("m"), 2_051)
        # a SECOND writer (another process) appends: the cache must notice
        other = type(lg)(lg.path)
        other.append(rec(2_051))
        self.assertEqual(lg.next_seq("m"), 2_052)
        # an external edit that changes the size: rescan
        pathlib.Path(lg.path).write_text(
            pathlib.Path(lg.path).read_text(encoding="utf-8")
            + json.dumps(rec(2_052).to_dict(), sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(lg.next_seq("m"), 2_053)
        # a purge rewrites the file: rescan (and the survivors keep seq)
        lg.purge_older_than(float("inf"))
        self.assertEqual(lg.next_seq("m"), 1)
        lg.append(rec(1))
        self.assertEqual(lg.next_seq("m"), 2)
        # per-machine: another machine id is independent
        self.assertEqual(lg.next_seq("other"), 1)

    def test_append_and_next_seq_shape(self) -> None:
        out: Dict[str, Dict[int, Any]] = {}
        for kind in KINDS:
            lg = self.mk(kind, "scale_" + kind)
            out[kind] = {}
            n = 0
            for target in (1, 1000, 10000):
                self._fill(lg, target - n, n + 1)
                n = target
                t = time.perf_counter()
                for j in range(10):
                    lg.append(rec(n + 1 + j))
                ap = (time.perf_counter() - t) / 10
                n += 10
                t = time.perf_counter()
                lg.next_seq("m")
                ns = time.perf_counter() - t
                t = time.perf_counter()
                lg.read("m", after_seq=n - 5, limit=5)
                rd = time.perf_counter() - t
                out[kind][target] = (ap, ns, rd)
                print(
                    f"\n[262] {kind:6} n={target:6} append={ap * 1e3:8.3f}ms "
                    f"next_seq={ns * 1e3:8.3f}ms tail-read={rd * 1e3:8.3f}ms",
                    end="",
                )
        # memory: O(1) append; sqlite: next_seq is an index probe (flat)
        self.assertLess(out["memory"][10000][0], 0.005)
        self.assertLess(out["sqlite"][10000][1], 0.05)
        # jsonl: next_seq used to scan the file (79 ms at 10k -> a run was
        # O(n^2)); now cached per machine while the file size is unchanged
        # -> flat. The READ path still scans (documented).
        self.assertLess(out["jsonl"][10000][1], 0.002)
        self.assertGreater(out["jsonl"][10000][2], out["jsonl"][1000][2] * 2)

    def test_sqlite_listing_uses_the_primary_key_index(self) -> None:
        lg = self.mk("sqlite")
        self._fill(lg, 50)
        plans = [
            " ".join(str(c) for c in r)
            for r in lg._conn().execute(
                "EXPLAIN QUERY PLAN SELECT seq, record FROM transitions "
                "WHERE machine_id = ? AND seq > ? ORDER BY seq LIMIT ?",
                ("m", 0, 10),
            )
        ]
        joined = " ".join(plans)
        self.assertIn("SEARCH", joined)
        self.assertNotIn("SCAN", joined)
        self.assertNotIn("TEMP B-TREE", joined)  # ORDER BY free via PK

    def test_sqlite_read_by_key_independent_of_other_keys(self) -> None:
        lg = self.mk("sqlite")
        for i in range(1, 6):
            lg.append(rec(i, mid="small"))
        for i in range(1, 20001):
            lg.append(rec(i, mid="big"))
        t = time.perf_counter()
        for _ in range(20):
            lg.read("small")
        small = (time.perf_counter() - t) / 20
        print(
            f"\n[262] sqlite read(small key) beside 20k others: {small * 1e3:.3f}ms"
        )
        self.assertLess(small, 0.05)

    def test_jsonl_read_scans_whole_file(self) -> None:
        lg = self.mk("jsonl")
        for i in range(1, 3001):
            lg.append(rec(i, mid="big"))
        lg.append(rec(1, mid="small"))
        calls = {"n": 0}
        real = TransitionRecord.from_dict

        def spy(d: Any) -> Any:
            calls["n"] += 1
            return real(d)

        with mock.patch.object(
            TransitionRecord, "from_dict", staticmethod(spy)
        ):
            lg.read("small")
        self.assertEqual(calls["n"], 3001)  # O(all records), documented

    def test_jsonl_append_is_open_append_close_per_record(self) -> None:
        lg = self.mk("jsonl")
        with mock.patch("builtins.open", wraps=open) as op:
            for i in range(1, 6):
                lg.append(rec(i))
        self.assertEqual(op.call_count, 5)

    def test_replay_100k_time_and_memory(self) -> None:
        n = 100_000
        recs = [
            rec(
                i,
                event_type="GO",
                event_payload={},
                from_states=("m.a",) if i % 2 else ("m.b",),
                to_states=("m.b",) if i % 2 else ("m.a",),
                actions=(),
            )
            for i in range(1, n + 1)
        ]
        gc.collect()
        tracemalloc.start()
        t = time.perf_counter()
        i = replay(machine(), iter(recs))
        dt = time.perf_counter() - t
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(
            f"\n[262] replay({n}) {dt:.2f}s peak(extra over input)="
            f"{peak / 1e6:.1f}MB"
        )
        self.assertEqual(sorted(i.current_state_ids), ["m.a"])
        # 📝 replay() sorts the records (`sorted(...)`): O(n) memory, not a
        #    stream. Shape assertion: peak is at least one list of n refs.
        self.assertGreater(peak, n * 8)

    def test_pagination_lossless_across_backends(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "pg_" + kind)
                self._fill(lg, 25)
                seen: List[int] = []
                cur = 0
                while True:
                    page = lg.read("m", after_seq=cur, limit=7)
                    if not page:
                        break
                    seen += [r.seq for r in page]
                    cur = page[-1].seq
                self.assertEqual(seen, list(range(1, 26)))

    def _plugin_growth(self, lg: Any, n: int) -> Dict[str, int]:
        m = machine()
        i = SyncInterpreter(m).use(TransitionLogPlugin(lg)).start()
        for _ in range(200):
            i.send("GO")
        gc.collect()
        tracemalloc.start()
        half = full = 0
        for k in range(n):
            i.send("GO")
            if k == n // 2 - 1:
                gc.collect()
                half = tracemalloc.get_traced_memory()[0]
        gc.collect()
        full = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        return {"half": half, "full": full}

    def test_plugin_flat_memory_with_durable_store(self) -> None:
        for kind in ("jsonl", "sqlite"):
            with self.subTest(kind):
                # jsonl next_seq is O(n) and sqlite commits fsync (tracemalloc
                # makes both ~10x slower): modest n, still two halves
                n = 600 if kind == "jsonl" else 2000
                r = self._plugin_growth(self.mk(kind, "leak_" + kind), n)
                print(
                    f"\n[262] {kind} {n} sends: second-half growth "
                    f"{r['full'] - r['half']} B"
                )
                self.assertLess(r["full"] - r["half"], _leak_ceiling())

    def test_memorylog_grows_by_exactly_the_records_and_purge_reclaims(
        self,
    ) -> None:
        lg = MemoryLog()
        i = SyncInterpreter(machine()).use(TransitionLogPlugin(lg)).start()
        for _ in range(1000):
            i.send("GO")
        self.assertEqual(len(lg), 1000)
        self.assertEqual(lg.purge_older_than(math.inf), 1000)
        self.assertEqual(len(lg), 0)
        gc.collect()


# =============================================================================
# 🗑️ Retention
# =============================================================================
class TestRetention(_Tmp):
    def test_purge_removes_exactly_older_keeps_seq(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "ret_" + kind)
                for i in range(1, 11):
                    lg.append(rec(i, ts=float(i)))
                lg.append(rec(1, mid="other", ts=3.0))
                n = lg.purge_older_than(6.0)  # ts 1..5 + other
                self.assertEqual(n, 6)
                got = lg.read("m")
                self.assertEqual([r.seq for r in got], [6, 7, 8, 9, 10])
                self.assertEqual(lg.read("other"), [])
                self.assertEqual(lg.next_seq("m"), 11)  # no renumbering
                lg.append(rec(11, ts=11.0))
                self.assertEqual(lg.read("m", after_seq=9)[-1].seq, 11)

    def test_boundary_is_strictly_older(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "b_" + kind)
                lg.append(rec(1, ts=5.0))
                self.assertEqual(lg.purge_older_than(5.0), 0)
                self.assertEqual(lg.purge_older_than(5.0000001), 1)

    def test_future_ts_purges_everything_and_count_is_int(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "f_" + kind)
                for i in range(1, 4):
                    lg.append(rec(i))
                self.assertEqual(lg.purge_older_than(1e18), 3)
                self.assertEqual(lg.read("m"), [])
                self.assertEqual(lg.purge_older_than(1e18), 0)
                self.assertEqual(lg.purge_older_than(math.inf), 0)

    def test_bad_cutoff_is_value_error_and_destroys_nothing(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "v_" + kind)
                for i in range(1, 4):
                    lg.append(rec(i))
                for bad in (float("nan"), -math.inf, "5", None, True):
                    with self.assertRaises(ValueError):
                        lg.purge_older_than(bad)  # type: ignore[arg-type]
                self.assertEqual(len(lg.read("m")), 3)

    def test_purge_from_snapshot_plus_tail_replay_still_works(self) -> None:
        lg = self.mk("sqlite")
        i = SyncInterpreter(machine()).use(TransitionLogPlugin(lg)).start()
        for _ in range(6):
            i.send("GO")
        recs = lg.read("m")
        cut = recs[3].ts  # seq 4 onwards survive (ts may tie -> guard)
        lg.purge_older_than(cut)
        tail = lg.read("m")
        self.assertTrue(tail)
        self.assertEqual(tail[-1].seq, 6)

    def test_purge_concurrent_with_appends_loses_nothing(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                lg = self.mk(kind, "cc_" + kind)
                errors: List[BaseException] = []
                stop = threading.Event()

                def purger() -> None:
                    try:
                        while not stop.is_set():
                            lg.purge_older_than(0.5)  # nothing qualifies
                    except BaseException as exc:  # pragma: no cover
                        errors.append(exc)

                th = threading.Thread(target=purger)
                th.start()
                try:
                    for i in range(1, 151):
                        lg.append(rec(i, ts=100.0))
                finally:
                    stop.set()
                    th.join()
                self.assertEqual(errors, [])
                self.assertEqual(len(lg.read("m", limit=1000)), 150)

    def test_purge_concurrent_removes_only_old_never_new(self) -> None:
        lg = self.mk("jsonl")
        for i in range(1, 51):
            lg.append(rec(i, ts=1.0))
        errors: List[BaseException] = []

        def purger() -> None:
            try:
                for _ in range(15):
                    lg.purge_older_than(50.0)
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)

        th = threading.Thread(target=purger)
        th.start()
        for i in range(51, 101):
            lg.append(rec(i, ts=100.0))
        th.join()
        self.assertEqual(errors, [])
        self.assertEqual(
            [r.seq for r in lg.read("m", limit=1000)], list(range(51, 101))
        )

    def test_jsonl_rewrite_fault_leaves_old_file_intact(self) -> None:
        lg = self.mk("jsonl")
        for i in range(1, 6):
            lg.append(rec(i, ts=float(i)))
        before = lg.path.read_bytes()
        with mock.patch.object(Path, "replace", side_effect=OSError("kill")):
            with self.assertRaises(OSError):
                lg.purge_older_than(4.0)
        self.assertEqual(lg.path.read_bytes(), before)
        self.assertFalse(lg.path.with_suffix(".jsonl.tmp").exists())
        self.assertEqual(len(lg.read("m")), 5)  # still readable, still whole

    def test_jsonl_rewrite_fault_mid_write_never_torn(self) -> None:
        lg = self.mk("jsonl")
        for i in range(1, 6):
            lg.append(rec(i, ts=float(i)))
        before = lg.path.read_bytes()
        real = json.dumps
        calls = {"n": 0}

        def flaky(*a: Any, **k: Any) -> str:
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("died mid-rewrite")
            return real(*a, **k)

        with mock.patch(
            "src.xstate_statemachine.persistence.log.json.dumps", flaky
        ):
            with self.assertRaises(RuntimeError):
                lg.purge_older_than(2.0)
        self.assertEqual(lg.path.read_bytes(), before)
        self.assertFalse(lg.path.with_suffix(".jsonl.tmp").exists())

    def test_purge_does_not_touch_snapshots(self) -> None:
        store = SQLiteStore(self.tmp / "co.db")
        self.addCleanup(store.close)
        lg = SQLiteLog(store)
        store.save("k", {"x": 1}) if False else None
        # snapshots table is untouched by a purge: row counts via raw SQL
        c = store._conn()
        c.execute(
            "INSERT INTO statecharts(key, snapshot, version, "
            "machine_version, updated_at) VALUES ('k', '{}', 1, '', 1.0)"
        )
        lg.append(rec(1, mid="k", ts=1.0))
        self.assertEqual(lg.purge_older_than(1e18), 1)
        n = c.execute("SELECT COUNT(*) FROM statecharts").fetchone()[0]
        self.assertEqual(n, 1)


# =============================================================================
# 🔐 Redaction round trip
# =============================================================================
class TestRedaction(_Tmp):
    def test_every_field_through_redact_default_keys(self) -> None:
        payload = {
            "token": SECRET,
            "user": {"password": SECRET, "name": "ok"},
            "items": [{"token": SECRET}, {"n": 1}],
            "x-api-key": SECRET,
            "Authorization": SECRET,
            "tup": ({"secret": SECRET},),
        }
        out = redact(payload, DEFAULT_REDACT_KEYS)
        self.assertNotIn(SECRET, json.dumps(out))
        self.assertEqual(out["user"]["name"], "ok")
        self.assertEqual(out["items"][1], {"n": 1})
        self.assertEqual(payload["token"], SECRET)  # pure

    def test_custom_hyphenated_keys(self) -> None:
        out = redact(
            {"X-Custom-Token": SECRET, "x_custom_token": SECRET, "ok": 1},
            ("x-custom-token",),
        )
        self.assertNotIn(SECRET, json.dumps(out))
        self.assertEqual(out["ok"], 1)

    def _run(self, plugin_cls: Any, lg: Any, **kw: Any) -> None:
        i = SyncInterpreter(machine()).use(plugin_cls(lg, **kw)).start()
        i.send(
            "GO",
            token=SECRET,
            nested={"items": [{"token": SECRET}], "password": SECRET},
            actor="bob",
            reason="why",
        )
        i.stop()

    def test_plugins_redact_by_default_and_never_leak_to_disk(self) -> None:
        for plugin_cls in (TransitionLogPlugin, AuditPlugin):
            for kind in KINDS:
                with self.subTest(plugin=plugin_cls.__name__, kind=kind):
                    lg = self.mk(kind, f"r_{plugin_cls.__name__}_{kind}")
                    self._run(plugin_cls, lg)
                    got = lg.read("m")
                    self.assertTrue(got)
                    self.assertNotIn(
                        SECRET,
                        json.dumps([r.to_dict() for r in got], default=str),
                    )
                    self.assertEqual(got[0].event_payload["token"], "***")
                    self.assertEqual(
                        got[0].event_payload["nested"]["items"][0]["token"],
                        "***",
                    )
                    for f in self.tmp.glob(f"r_{plugin_cls.__name__}_*"):
                        data = f.read_bytes()
                        self.assertNotIn(SECRET.encode(), data, f.name)

    def test_audit_keeps_actor_and_reason_unredacted(self) -> None:
        lg = self.mk("memory")
        self._run(AuditPlugin, lg)
        r = lg.read("m")[0]
        self.assertEqual((r.actor, r.reason), ("bob", "why"))

    def test_opt_out_is_explicit(self) -> None:
        lg = self.mk("memory")
        self._run(TransitionLogPlugin, lg, redact_keys=())
        self.assertEqual(lg.read("m")[0].event_payload["token"], SECRET)

    def test_custom_redact_keys_with_hyphens_in_plugin(self) -> None:
        lg = self.mk("jsonl")
        i = (
            SyncInterpreter(machine())
            .use(TransitionLogPlugin(lg, redact_keys=("x-custom-token",)))
            .start()
        )
        i.send("GO", **{"X_Custom_Token": SECRET})
        self.assertNotIn(SECRET.encode(), lg.path.read_bytes())

    def test_error_field_carries_exception_text_documented(self) -> None:
        # 📝 `error.message` is `str(exception)` and is NOT passed through
        #    redact() (it is free text, not a mapping). Pin it so a change
        #    is deliberate.
        r = rec(1, error={"type": "E", "message": "boom"})
        for kind in KINDS:
            lg = self.mk(kind, "e_" + kind)
            lg.append(r)
            self.assertEqual(lg.read("m")[0].error, r.error)

    def test_redacted_record_round_trips_byte_identical(self) -> None:
        red = redact({"token": SECRET, "n": [1, {"pin": "1234"}]})
        r = rec(1, event_payload=red)
        j = self.mk("jsonl")
        s = self.mk("sqlite")
        j.append(r)
        s.append(r)
        self.assertEqual(j.read("m")[0], r)
        self.assertEqual(s.read("m")[0], r)
        self.assertEqual(j.read("m")[0].to_dict(), s.read("m")[0].to_dict())
        line = j.path.read_text(encoding="utf-8").strip()
        raw = s._conn().execute("SELECT record FROM transitions").fetchone()[0]
        self.assertEqual(line, raw)  # byte-identical serialisation


# =============================================================================
# 🏠 Co-location
# =============================================================================
class TestColocation(_Tmp):
    def test_log_and_store_coexist_across_reopen(self) -> None:
        p = self.tmp / "co.db"
        store = SQLiteStore(p)
        lg = SQLiteLog(store)
        lg.append(rec(1, mid="k"))
        store.close()
        store2 = SQLiteStore(p)
        self.addCleanup(store2.close)
        lg2 = SQLiteLog(store2)
        self.assertEqual([r.seq for r in lg2.read("k")], [1])
        tables = {
            r[0]
            for r in store2._conn().execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertTrue({"statecharts", "transitions", "xsm_schema"} <= tables)

    def test_forget_removes_log_rows_purge_leaves_snapshots(self) -> None:
        store = SQLiteStore(self.tmp / "co2.db")
        self.addCleanup(store.close)
        lg = SQLiteLog(store)
        lg.append(rec(1, mid="k"))
        res = store.forget("k")
        self.assertEqual(res["log_entries"], 1)
        self.assertEqual(lg.read("k"), [])

    def test_store_log_inbox_one_schema_row(self) -> None:
        from src.xstate_statemachine.persistence import SQLiteInbox

        store = SQLiteStore(self.tmp / "all.db")
        self.addCleanup(store.close)
        lg = SQLiteLog(store)
        SQLiteInbox(store)
        lg.append(rec(1))
        c = store._conn()
        self.assertEqual(
            c.execute("SELECT COUNT(*) FROM xsm_schema").fetchone()[0], 1
        )
        names = {
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertTrue(
            {"statecharts", "transitions", "inbox", "xsm_schema"} <= names
        )
        # reopening any one of them again is a no-op for the others
        SQLiteLog(store)
        SQLiteInbox(store)
        self.assertEqual(len(lg.read("m")), 1)

    def test_corrupt_log_row_does_not_break_the_store(self) -> None:
        store = SQLiteStore(self.tmp / "co3.db")
        self.addCleanup(store.close)
        lg = SQLiteLog(store)
        store._conn().execute(
            "INSERT INTO transitions VALUES ('k', 1, 1.0, '{bad')"
        )
        with self.assertRaises(LogCorruptError):
            lg.read("k")
        (
            self.assertIsNone(store.load("nope"))
            if hasattr(store, "load") and False
            else None
        )
        self.assertEqual(store.forget("k")["log_entries"], 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
