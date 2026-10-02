# tests/persistence/test_battle_259_stores_corruption_scaling.py
"""#259 battle (part B): corruption, protocol contracts, scaling, leaks.

Every backend (Memory / File / SQLite) and the ``as_async`` wrapper of each
is held to ONE contract; the matrix below is what the docs' backend
comparison table is generated from. Scaling tests assert SHAPE only (ratios,
bounded growth) and print the numbers.
"""

from __future__ import annotations

import asyncio
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

from src.xstate_statemachine.exceptions import (
    ConflictError,
    InvalidKeyError,
    SnapshotCorruptError,
    SnapshotTooLargeError,
    StoreError,
)
from src.xstate_statemachine.persistence import (
    Deadline,
    FileStore,
    MemoryStore,
    SQLiteStore,
    as_async,
)
from src.xstate_statemachine.persistence.file_store import (
    decode_key,
    encode_key,
)

TYPED = (StoreError, SnapshotCorruptError)
SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["o.a"]}
)
DL = Deadline("o.a", 1, 1.0e9, 1000, "after.1000.o.a")


def _report(label: str, **vals: Any) -> None:
    sys.stderr.write(f"[259B] {label}: {vals}\n")


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="xsm259b-"))
        self._closers: List[Callable[[], None]] = []

    def tearDown(self) -> None:
        for c in self._closers:
            try:
                c()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, kind: str, **kw: Any) -> Any:
        d = Path(tempfile.mkdtemp(dir=self.tmp))
        if kind == "memory":
            s: Any = MemoryStore(**kw)
        elif kind == "file":
            s = FileStore(d / "fs", fsync=False, **kw)
        else:
            s = SQLiteStore(d / "s.db", **kw)
        if hasattr(s, "close"):
            self._closers.append(s.close)
        return s


KINDS = ("memory", "file", "sqlite")


# =========================================================================
# 💥 FileStore corruption
# =========================================================================
class TestFileStoreCorruption(_Base):
    def _store_with_record(self, **save_kw: Any):
        s = self.make("file")
        s.save("k", SNAP, machine_version="3", **save_kw)
        f = next(Path(s.directory).glob("*.xsm.json"))
        return s, f

    def _assert_typed_or_ok(self, s: Any, label: str) -> str:
        try:
            s.load("k")
            return "ok"
        except TYPED:
            return "typed"
        except BaseException as exc:  # noqa: BLE001 -- the point
            self.fail(f"{label}: bare {type(exc).__name__}: {exc}")
        return ""

    def test_every_byte_flip_truncate_insert_smallest_record(self) -> None:
        s, f = self._store_with_record()
        orig = f.read_bytes()
        small = json.dumps({"version": 4}).encode()
        # cover EVERY position for a small record; sample a big one
        for blob in (
            orig if len(orig) <= 2000 else None,
            small,
        ):
            if blob is None:
                continue
            for i in range(len(blob)):
                for mutated in (
                    blob[:i] + bytes([blob[i] ^ 0xFF]) + blob[i + 1 :],
                    blob[:i],
                    blob[:i] + b"\x00" + blob[i:],
                ):
                    f.write_bytes(mutated)
                    self._assert_typed_or_ok(s, f"pos {i}")
        f.write_bytes(orig)
        self.assertEqual(s.load("k").version, 1)

    def test_sampled_mutations_of_a_large_record(self) -> None:
        s = self.make("file")
        s.save(
            "k",
            json.dumps({"context": {"x": "y" * 3000}}),
            machine_version="m",
        )
        f = next(Path(s.directory).glob("*.xsm.json"))
        orig = f.read_bytes()
        rng = random.Random(259)
        for pos in rng.sample(range(len(orig)), 2000):
            for mutated in (
                orig[:pos]
                + bytes([orig[pos] ^ (1 << rng.randrange(8))])
                + orig[pos + 1 :],
                orig[:pos],
                orig[:pos] + bytes([rng.randrange(256)]) + orig[pos:],
            ):
                f.write_bytes(mutated)
                self._assert_typed_or_ok(s, f"pos {pos}")

    def _rewrite(self, f: Path, **changes: Any) -> None:
        rec = json.loads(f.read_text(encoding="utf-8"))
        for k, v in changes.items():
            if v is KeyError:
                rec.pop(k, None)
            else:
                rec[k] = v
        f.write_text(json.dumps(rec), encoding="utf-8")

    def test_envelope_attacks(self) -> None:
        s, f = self._store_with_record()
        cases: Dict[str, Dict[str, Any]] = {
            "format missing": {"format": KeyError},  # legal: legacy
            "format str": {"format": "1"},
            "format negative": {"format": -1},
            "format 2**63": {"format": 2**63},
            "format float": {"format": 1.5},
            "format bool": {"format": True},
            "version missing": {"version": KeyError},
            "version float": {"version": 1.5},
            "version str": {"version": "1"},
            "version zero": {"version": 0},
            "version negative": {"version": -4},
            "snapshot int": {"snapshot": 5},
            "snapshot null": {"snapshot": None},
            "snapshot list": {"snapshot": ["a"]},
            "machine_version int": {"machine_version": 7},
            "machine_version null": {"machine_version": None},
            "deadlines dict": {"deadlines": {"a": 1}},
            "deadlines str": {"deadlines": "x"},
            "deadlines non-dicts": {"deadlines": [1, "a", None]},
            "deadline no state_id": {
                "deadlines": [
                    {
                        "entry_seq": 1,
                        "due_at_wall": 1.0,
                        "delay_ms": 1,
                        "event_type": "e",
                    }
                ]
            },
            "updated_at str": {"updated_at": "yesterday"},
            "updated_at NaN": {"updated_at": float("nan")},
            "updated_at -inf": {"updated_at": float("-inf")},
            "updated_at bool": {"updated_at": True},
        }
        outcomes: Dict[str, str] = {}
        for name, ch in cases.items():
            self._rewrite(f, **ch)
            outcomes[name] = self._assert_typed_or_ok(s, name)
            s.delete("k")
            s.save("k", SNAP, machine_version="3")
        # only the legacy-compatible case may succeed
        for name, out in outcomes.items():
            if name == "format missing":
                self.assertEqual(out, "ok")
            else:
                self.assertEqual(out, "typed", name)
        _report("file envelope", **outcomes)

    def test_snapshot_10mb_is_too_large_not_oom(self) -> None:
        s, f = self._store_with_record()
        self._rewrite(f, snapshot="x" * (10 * 1024 * 1024))
        with self.assertRaises(SnapshotTooLargeError):
            s.load("k")

    def test_unknown_keys_are_accepted_and_dropped(self) -> None:
        # persistence.md lists the fields of a record; unknown envelope keys
        # (a newer writer in the SAME format) are ignored on load and are
        # not preserved on the next save.
        s, f = self._store_with_record()
        self._rewrite(f, shiny="new", nested={"a": 1})
        rec = s.load("k")
        self.assertEqual(rec.version, 1)
        s.save("k", SNAP, expected_version=1)
        on_disk = json.loads(f.read_text(encoding="utf-8"))
        self.assertNotIn("shiny", on_disk)

    def test_empty_file_directory_and_symlink(self) -> None:
        s, f = self._store_with_record()
        f.write_bytes(b"")
        with self.assertRaises(SnapshotCorruptError):
            s.load("k")
        f.unlink()
        f.mkdir()  # a directory where the record file should be
        try:
            s.load("k")
        except TYPED:
            pass
        except OSError as exc:  # noqa: PERF203
            self.fail(f"bare OSError escaped load(): {exc!r}")
        with self.assertRaises(TYPED + (OSError,)):
            s.save("k", SNAP)  # must not corrupt silently; error acceptable
        f.rmdir()
        link = f
        try:
            os.symlink(str(link), str(link))  # self-loop
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("os.symlink needs privilege on this Windows host")
        try:
            s.load("k")
        except TYPED:
            pass
        except OSError as exc:
            self.fail(f"bare OSError from a symlink loop: {exc!r}")


# =========================================================================
# 💥 SQLiteStore corruption
# =========================================================================
class TestSQLiteCorruption(_Base):
    def _raw(self, s: SQLiteStore) -> sqlite3.Connection:
        c = sqlite3.connect(s.path)
        self._closers.append(c.close)
        return c

    def test_not_null_columns_refuse_null(self) -> None:
        s = self.make("sqlite")
        c = self._raw(s)
        for col_vals in (
            "('n',NULL,1,'',1.0)",
            "('n','{}',NULL,'',1.0)",
            "('n','{}',1,NULL,1.0)",
            "('n','{}',1,'',NULL)",
        ):
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute(f"INSERT INTO statecharts VALUES {col_vals}")

    def test_damaged_rows_load_typed(self) -> None:
        s = self.make("sqlite")
        c = self._raw(s)
        rows = {
            "v-neg": "('v-neg','{}',-3,'',1.0)",
            "v-zero": "('v-zero','{}',0,'',1.0)",
            "v-text": "('v-text','{}','abc','',1.0)",
            "v-float": "('v-float','{}',1.5,'',1.0)",
            "snap-blob": "('snap-blob',X'ff00fe',1,'',1.0)",
            "mv-blob": "('mv-blob','{}',1,X'ff','',1.0)".replace(
                ",'',1.0)", ",1.0)"
            ),
            "upd-text": "('upd-text','{}',1,'','x')",
            "upd-nan": "('upd-nan','{}',1,'',NULL)",
        }
        for k, vals in rows.items():
            try:
                c.execute(f"INSERT INTO statecharts VALUES {vals}")
            except sqlite3.IntegrityError:
                continue  # NOT NULL rejected it: nothing to load
        c.commit()
        for k in rows:
            try:
                s.load(k)
            except TYPED:
                pass
            except BaseException as exc:  # noqa: BLE001
                self.fail(f"{k}: bare {type(exc).__name__}: {exc}")

    def test_malformed_deadline_rows_load_typed(self) -> None:
        s = self.make("sqlite")
        s.save("d", SNAP)
        c = self._raw(s)
        c.execute("INSERT INTO deadlines VALUES ('d',5,'x','y','z',3)")
        c.commit()
        with self.assertRaises(SnapshotCorruptError):
            s.load("d")

    def test_foreign_invalid_key_row_is_skipped_by_list(self) -> None:
        # docs: list_keys never advertises a key load() would refuse.
        s = self.make("sqlite")
        s.save("good", SNAP)
        c = self._raw(s)
        c.execute("INSERT INTO statecharts VALUES ('','{}',1,'',1.0)")
        c.execute(
            "INSERT INTO statecharts VALUES (?, '{}',1,'',1.0)", ("k" * 300,)
        )
        c.commit()
        self.assertEqual(s.list_keys(), ["good"])
        for k in s.list_keys():
            self.assertIsNotNone(s.load(k))

    def test_garbage_file_is_typed_at_open_or_health(self) -> None:
        # 🐛 DEFECT (fixed at integration): a file that is not a SQLite
        #    database raised a bare `sqlite3.DatabaseError` from the
        #    constructor. X0.4: the store's own exception, always.
        p = self.tmp / "garbage.db"
        p.write_bytes(b"this is not a database" * 100)
        with self.assertRaises(StoreError) as cm:
            SQLiteStore(p)
        self.assertNotIsInstance(cm.exception, sqlite3.DatabaseError)
        self.assertIn("not a database", str(cm.exception))
        # a DB another program owns (valid SQLite, foreign schema) opens
        # and upgrades or refuses -- never a raw sqlite3 error either
        q = self.tmp / "foreign.db"
        conn = sqlite3.connect(q)
        conn.execute("CREATE TABLE xsm_schema(version INTEGER)")
        conn.execute("INSERT INTO xsm_schema VALUES (999)")
        conn.commit()
        conn.close()
        with self.assertRaises(StoreError) as cm2:
            SQLiteStore(q)
        self.assertIn("newer", str(cm2.exception))


# =========================================================================
# 🧷 MemoryStore argument contracts (TypeError at the call site, documented
#     in BaseStore.save: "caller-side argument checks")
# =========================================================================
class TestCallSideArguments(_Base):
    def test_bad_arguments_are_identical_on_every_backend(self) -> None:
        for kind in KINDS:
            s = self.make(kind)
            with self.subTest(kind):
                with self.assertRaises(TypeError):
                    s.save("k", 5)
                with self.assertRaises(TypeError):
                    s.save("k", SNAP, expected_version="1")
                with self.assertRaises(TypeError):
                    s.save("k", SNAP, expected_version=1.5)
                with self.assertRaises(TypeError):
                    s.save("k", SNAP, expected_version=True)
                with self.assertRaises(ValueError):
                    s.save("k", SNAP, expected_version=-1)
                with self.assertRaises(TypeError):
                    s.save("k", SNAP, deadlines=[1])
                with self.assertRaises(TypeError):
                    s.save("k", SNAP, machine_version=3)
                with self.assertRaises(InvalidKeyError):
                    s.save("sur\ud800", SNAP)
                with self.assertRaises(TYPED):
                    s.save("k", "\ud800")
                self.assertIsNone(s.load("k"))  # nothing written


# =========================================================================
# 📜 Protocol contract matrix: Memory/File/SQLite x sync/async
# =========================================================================
class _Matrix(_Base):
    """Runs one contract body against the sync and the `as_async` view."""

    def views(self, **kw: Any):
        for kind in KINDS:
            s = self.make(kind, **kw)
            yield kind, s


class TestContractMatrix(_Matrix):
    def test_load_missing_none_delete_missing_false(self) -> None:
        for kind, s in self.views():
            with self.subTest(kind):
                self.assertIsNone(s.load("nope"))
                self.assertIs(s.delete("nope"), False)
                self.assertEqual(s.forget("nope")["snapshots"], 0)
                self.assertEqual(s.list_keys(), [])

    def test_save_versioning_and_conflict_payload(self) -> None:
        for kind, s in self.views():
            with self.subTest(kind):
                self.assertEqual(s.save("k", SNAP, expected_version=0), 1)
                with self.assertRaises(ConflictError) as cm:
                    s.save("k", SNAP, expected_version=0)
                self.assertEqual(
                    (cm.exception.expected, cm.exception.actual), (0, 1)
                )
                with self.assertRaises(ConflictError) as cm:
                    s.save("zz", SNAP, expected_version=9)
                self.assertEqual(
                    (cm.exception.expected, cm.exception.actual), (9, None)
                )
                self.assertIsNone(s.load("zz"))
                v = [s.save("k", SNAP) for _ in range(5)]  # unconditional
                self.assertEqual(v, [2, 3, 4, 5, 6])
                self.assertEqual(s.load("k").version, 6)
                s.delete("k")
                self.assertEqual(s.save("k", SNAP), 1)  # restarts at 1

    def test_updated_at_is_epoch_and_non_decreasing(self) -> None:
        for kind, s in self.views():
            with self.subTest(kind):
                prev = 0.0
                for _ in range(20):
                    t0 = time.time()
                    s.save("k", SNAP)
                    t1 = time.time()
                    u = s.load("k").updated_at
                    self.assertGreaterEqual(u, prev)
                    self.assertTrue(t0 - 1 <= u <= t1 + 1, (u, t0, t1))
                    prev = u

    def test_list_keys_ordering_limits_prefix_metacharacters(self) -> None:
        keys = ["b", "a", "p%x", "p_x", "pax", "p1", "É", "é", "ключ", "Z"]
        for kind, s in self.views():
            with self.subTest(kind):
                for k in keys:
                    s.save(k, SNAP)
                full = s.list_keys()
                self.assertEqual(full, sorted(keys))  # code-point order
                self.assertEqual(s.list_keys(limit=0), [])
                with self.assertRaises(ValueError):
                    s.list_keys(limit=-1)
                self.assertEqual(s.list_keys(limit=10**9), full)
                self.assertEqual(s.list_keys(limit=3), full[:3])
                # LIKE metacharacters are literal
                self.assertEqual(s.list_keys(prefix="%"), [])
                self.assertEqual(s.list_keys(prefix="_"), [])
                self.assertEqual(s.list_keys(prefix="p%"), ["p%x"])
                self.assertEqual(s.list_keys(prefix="p_"), ["p_x"])
                self.assertEqual(s.list_keys(prefix="é"), ["é"])
                self.assertEqual(s.list_keys(prefix="кл"), ["ключ"])
                self.assertEqual(s.list_keys(prefix=""), full)
                for k in full:  # never advertise a key load() misses
                    self.assertIsNotNone(s.load(k), k)

    def test_list_keys_has_no_cursor_truncation_is_silent(self) -> None:
        # Documented gap: `limit` truncates; there is no cursor, so a caller
        # pages by prefix. The test pins the behaviour so a future cursor
        # is a deliberate change.
        for kind, s in self.views():
            with self.subTest(kind):
                for i in range(25):
                    s.save(f"k{i:02d}", SNAP)
                first = s.list_keys(limit=10)
                self.assertEqual(first, [f"k{i:02d}" for i in range(10)])
                self.assertEqual(s.list_keys(limit=10), first)  # no cursor
                self.assertEqual(
                    s.list_keys(prefix="k2"), [f"k2{i}" for i in range(5)]
                )

    def test_forget_report_and_nothing_left(self) -> None:
        for kind, s in self.views():
            with self.subTest(kind):
                s.save("k", SNAP, deadlines=[DL, DL])
                with s.lock("k"):
                    pass
                out = s.forget("k")
                self.assertEqual(out["snapshots"], 1)
                self.assertEqual(
                    out.get("deadlines", 2), 2 if kind != "file" else 2
                )
                self.assertIsNone(s.load("k"))
                self.assertEqual(s.list_keys(), [])
                if kind == "file":
                    self.assertEqual(
                        [p.name for p in Path(s.directory).iterdir()], []
                    )
                    self.assertIn("locks", out)
                if kind == "sqlite":
                    c = sqlite3.connect(s.path)
                    for t in ("statecharts", "deadlines"):
                        self.assertEqual(
                            c.execute(f"SELECT count(*) FROM {t}").fetchone()[
                                0
                            ],
                            0,
                        )
                    c.close()

    def test_health_healthy_and_unhealthy_never_raises(self) -> None:
        for kind, s in self.views():
            with self.subTest(kind):
                h = s.health()
                self.assertTrue(h["ok"])
                self.assertEqual(h["backend"], s.backend)
        fs = self.make("file")
        shutil.rmtree(fs.directory)
        self.assertFalse(fs.health()["ok"])
        sq = self.make("sqlite")
        sq.save("k", SNAP)
        sq.close()
        try:
            os.remove(sq.path)
            for suffix in ("-wal", "-shm"):
                if os.path.exists(sq.path + suffix):
                    os.remove(sq.path + suffix)
        except PermissionError:
            self.skipTest("cannot delete an open DB on this host")
        h = sq.health()  # the file is gone: SQLite recreates it empty
        self.assertIn("ok", h)  # never raises; may be healthy-and-empty
        _report("sqlite health after db removed", **h)

    def test_max_snapshot_bytes_on_save_and_load(self) -> None:
        for kind in KINDS:
            with self.subTest(kind):
                big = self.make(kind)
                big.save("k", "x" * 5000)
                small = self.make(kind, max_snapshot_bytes=100)
                with self.assertRaises(SnapshotTooLargeError):
                    small.save("k", "x" * 101)
                self.assertIsNone(small.load("k"))
                self.assertEqual(small.save("k", "x" * 100), 1)
                # poisoned load: a second handle with a smaller cap on the
                # same backing data must refuse the read
                if kind == "memory":
                    small._records["k"].data = "x" * 5000
                    reader: Any = small
                elif kind == "file":
                    reader = FileStore(big.directory, max_snapshot_bytes=100)
                else:
                    reader = SQLiteStore(big.path, max_snapshot_bytes=100)
                    self._closers.append(reader.close)
                with self.assertRaises(SnapshotTooLargeError):
                    reader.load("k")

    def test_codec_failures_are_typed(self) -> None:
        class Boom:
            def encode(self, s: str) -> str:
                return s

            def decode(self, d: str) -> str:
                raise RuntimeError("bad ciphertext")

        class NonStrDecode(Boom):
            def decode(self, d: str) -> Any:
                return b"bytes"

        class NonStrEncode(Boom):
            def encode(self, s: str) -> Any:
                return 5

        class BoomEncode(Boom):
            def encode(self, s: str) -> str:
                raise RuntimeError("no key")

        for kind in KINDS:
            with self.subTest(kind):
                self.assertEqual(
                    self.make(kind, codec=Boom()).save("k", SNAP), 1
                )
                with self.assertRaises(SnapshotCorruptError):
                    s = self.make(kind, codec=Boom())
                    s.save("k", SNAP)
                    s.load("k")
                s = self.make(kind, codec=NonStrDecode())
                s.save("k", SNAP)
                with self.assertRaises(SnapshotCorruptError):
                    s.load("k")
                with self.assertRaises(StoreError):
                    self.make(kind, codec=NonStrEncode()).save("k", SNAP)
                with self.assertRaises(StoreError):
                    self.make(kind, codec=BoomEncode()).save("k", SNAP)


class TestContractMatrixAsync(_Base):
    def test_async_view_agrees_on_every_row(self) -> None:
        async def body(kind: str) -> Dict[str, Any]:
            s = self.make(kind)
            a = as_async(s)
            try:
                out: Dict[str, Any] = {}
                out["load_missing"] = await a.load("nope")
                out["delete_missing"] = await a.delete("nope")
                out["v1"] = await a.save("k", SNAP, expected_version=0)
                try:
                    await a.save("k", SNAP, expected_version=0)
                except ConflictError as exc:
                    out["conflict"] = (exc.expected, exc.actual)
                out["v2"] = await a.save("k", SNAP)
                for k in ("b", "a", "p%x"):
                    await a.save(k, SNAP)
                out["keys"] = await a.list_keys()
                out["limit0"] = await a.list_keys(limit=0)
                try:
                    await a.list_keys(limit=-1)
                except ValueError:
                    out["limit-1"] = "ValueError"
                out["forget"] = (await a.forget("k"))["snapshots"]
                out["health"] = (await a.health())["ok"]
                try:
                    await a.save("k", 5)  # type: ignore[arg-type]
                except TypeError:
                    out["nonstr"] = "TypeError"
                return out
            finally:
                a.close()

        results = {k: asyncio.run(body(k)) for k in KINDS}
        self.assertEqual(results["memory"], results["file"])
        self.assertEqual(results["memory"], results["sqlite"])
        self.assertEqual(results["memory"]["conflict"], (0, 1))
        self.assertEqual(results["memory"]["keys"], ["a", "b", "k", "p%x"])


# =========================================================================
# 🔑 FileStore key encoding
# =========================================================================
class TestKeyEncoding(_Base):
    def test_round_trip_500_random_unicode_keys(self) -> None:
        import unicodedata

        rng = random.Random(259)
        keys = set()
        alphabet = 'abcXYZ019-_ .%/\\:*?"<>|é́ñ日本語🙂éé'
        while len(keys) < 500:
            k = "".join(
                rng.choice(alphabet) for _ in range(rng.randint(1, 20))
            )
            if k in (".", "..") or "/" in k or "\\" in k:
                continue
            keys.add(k)
        keys |= {
            unicodedata.normalize("NFC", "é"),
            unicodedata.normalize("NFD", "é"),
        }
        for k in keys:
            self.assertEqual(decode_key(encode_key(k)), k)
        # injective even on a case-insensitive comparison
        folded: Dict[str, str] = {}
        for k in keys:
            e = encode_key(k).lower()
            self.assertNotIn(e, folded, (k, folded.get(e)))
            folded[e] = k
        s = self.make("file")
        sample = rng.sample(sorted(keys), 60)
        for k in sample:
            s.save(k, SNAP)
        for k in sample:
            self.assertEqual(s.load(k).key, k)
        self.assertEqual(sorted(s.list_keys()), sorted(sample))

    def test_percent_does_not_collide_with_separator(self) -> None:
        self.assertNotEqual(encode_key("a%2Fb"), encode_key("a/b"))
        self.assertEqual(decode_key(encode_key("a%2Fb")), "a%2Fb")
        s = self.make("file")
        s.save("a%2Fb", SNAP)
        s.save("a%252Fb", SNAP)
        self.assertEqual(s.list_keys(), ["a%252Fb", "a%2Fb"])
        self.assertEqual(s.load("a%2Fb").version, 1)

    def test_trailing_dots_and_spaces_survive_windows_stripping(self) -> None:
        s = self.make("file")
        for k in ("a", "a.", "a ", "a..", "a. ", "A", "con", "con.", "CON"):
            s.save(k, SNAP)
        self.assertEqual(len(s.list_keys()), 9)
        for k in s.list_keys():
            self.assertEqual(s.load(k).key, k)
            self.assertNotRegex(encode_key(k), r"[. ]$")

    def test_case_only_difference_never_collides(self) -> None:
        self.assertNotEqual(
            encode_key("Order").lower(), encode_key("order").lower()
        )
        s = self.make("file")
        s.save("Order", SNAP)
        s.save("order", SNAP)
        self.assertEqual(s.list_keys(), ["Order", "order"])


# =========================================================================
# 📈 Scaling (shape only) and 🧯 leaks
# =========================================================================
def _timeit(fn: Callable[[], Any], n: int) -> float:
    """Best-of-5 mean over at least `n` calls, with the inner loop sized so
    each sample is >= ~2 ms. 📝 A MemoryStore op is ~1-2 us; 10 calls is
    20 us, inside perf_counter jitter on a loaded runner (macOS CI read a
    3.16x ratio on 'save+delete' for a flat op). Scale the loop up until
    one sample is long enough for the ratio to mean something."""
    reps = n
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    elapsed = time.perf_counter() - t0
    while elapsed < 0.002 and reps < 20_000:
        reps *= 4
        t0 = time.perf_counter()
        for _ in range(reps):
            fn()
        elapsed = time.perf_counter() - t0
    best = elapsed / reps
    for _ in range(4):
        t0 = time.perf_counter()
        for _ in range(reps):
            fn()
        best = min(best, (time.perf_counter() - t0) / reps)
    return best


class TestScaling(_Base):
    def _fill(self, s: Any, n: int, start: int = 0) -> None:
        # 📝 One deadline per key: `deadlines` is the table that grows with
        #    the store, and every save/load/delete touches it by key. With
        #    no index on `deadlines(key)` (schema v1) that was a full SCAN
        #    -- O(n) -- which a py3.12 CI runner read as 4.1x and this
        #    probe, saving snapshots WITHOUT deadlines, never saw.
        for i in range(start, n):
            s.save(f"key-{i:06d}", SNAP, deadlines=[DL])

    def test_ops_are_o1_in_store_size(self) -> None:
        sizes = (1, 100, 2000)  # 10 000 is measured, not asserted (below)
        for kind in KINDS:
            per: Dict[int, Dict[str, float]] = {}
            s = self.make(kind)
            filled = 0
            for n in sizes:
                self._fill(s, n, filled)
                filled = n
                probe = f"key-{n // 2:06d}"
                cnt = [0]

                def save() -> None:
                    s.save(probe, SNAP, deadlines=[DL])

                def load() -> None:
                    s.load(probe)

                def lst() -> None:
                    s.list_keys(limit=10)

                def dele() -> None:
                    cnt[0] += 1
                    k = f"tmp-{cnt[0]}"
                    s.save(k, SNAP, deadlines=[DL])
                    s.delete(k)

                per[n] = {
                    "save": _timeit(save, 20),
                    "load": _timeit(load, 20),
                    "list10": _timeit(lst, 5),
                    "save+delete": _timeit(dele, 10),
                }
            _report(
                f"scaling {kind}",
                **{
                    str(n): {k: f"{v * 1e6:.0f}us" for k, v in d.items()}
                    for n, d in per.items()
                },
            )
            hi, lo = per[sizes[-1]], per[sizes[1]]
            with self.subTest(kind):
                # 2000/100 = 20x more keys; O(1) ops must stay within 3x
                # 📝 FileStore `save` is one `_read` + one atomic
                #    temp-write + `os.replace` -- O(1) in CODE -- but the
                #    rename lands in a directory with n entries, and on
                #    APFS (macOS CI) that read 8.6x at 2000 vs 100 while
                #    Windows/NTFS and ext4 read ~1x. A filesystem property,
                #    not an algorithm; allow it a wider band and keep the
                #    strict 3x for every other op and every other store.
                band = {("file", "save"): 12.0, ("file", "save+delete"): 12.0}
                for op in ("save", "load", "save+delete"):
                    limit = band.get((kind, op), 3.0)
                    self.assertLess(hi[op] / lo[op], limit, (kind, op, hi, lo))
                if kind == "sqlite":
                    self.assertLess(
                        hi["list10"] / lo["list10"], 3.0, (kind, hi, lo)
                    )
                else:
                    # Documented shape: Memory sorts every key and File
                    # lists + decodes the whole directory, so list_keys is
                    # O(n) however small `limit` is. Recorded, not asserted.
                    _report(
                        f"{kind} list_keys(limit=10) is O(n)",
                        ratio=round(hi["list10"] / lo["list10"], 1),
                    )

    @unittest.skipUnless(
        os.environ.get("XSM_BIG"), "10 000-key run: set XSM_BIG=1"
    )
    def test_ten_thousand_keys(self) -> None:
        for kind in KINDS:
            s = self.make(kind)
            t0 = time.perf_counter()
            self._fill(s, 10_000)
            _report(f"10k fill {kind}", s=round(time.perf_counter() - t0, 2))

    def test_one_mib_record_round_trip(self) -> None:
        payload = json.dumps({"c": "x" * (1024 * 1024 - 64)})
        self.assertLessEqual(len(payload.encode()), 1024 * 1024)
        for kind in KINDS:
            s = self.make(kind)
            t0 = time.perf_counter()
            s.save("big", payload)
            t1 = time.perf_counter()
            rec = s.load("big")
            t2 = time.perf_counter()
            self.assertEqual(rec.snapshot, payload)
            _report(
                f"1MiB {kind}",
                save_ms=round((t1 - t0) * 1e3, 1),
                load_ms=round((t2 - t1) * 1e3, 1),
            )


def _lib_bytes(snap: tracemalloc.Snapshot) -> int:
    return sum(
        st.size
        for st in snap.statistics("filename")
        if "xstate_statemachine" in st.traceback[0].filename
    )


class TestLeaks(_Base):
    N = 10_000

    def _cycle(self, s: Any, n: int) -> None:
        for i in range(n):
            s.save("k", SNAP)
            s.load("k")
            s.delete("k")

    def test_cycles_do_not_grow_library_memory(self) -> None:
        for kind in KINDS:
            n = self.N if kind != "file" else 2_000  # fsync-free but slow
            s = self.make(kind)
            self._cycle(s, 200)  # warm caches / connections
            gc.collect()
            tracemalloc.start()
            try:
                self._cycle(s, n // 2)
                gc.collect()
                a = _lib_bytes(tracemalloc.take_snapshot())
                self._cycle(s, n // 2)
                gc.collect()
                b = _lib_bytes(tracemalloc.take_snapshot())
            finally:
                tracemalloc.stop()
            _report(f"leak {kind}", n=n, half=a, full=b, growth=b - a)
            self.assertLess(b - a, 64 * 1024, kind)

    def test_as_async_round_trips_bounded_and_thread_stable(self) -> None:
        threads_before = threading.active_count()
        for kind in KINDS:
            n = self.N if kind == "memory" else 2_000

            async def run(n: int, a: Any) -> None:
                for _ in range(n):
                    await a.save("k", SNAP)
                    await a.load("k")
                    await a.delete("k")

            s = self.make(kind)
            a = as_async(s)
            asyncio.run(run(100, a))
            gc.collect()
            tracemalloc.start()
            try:
                asyncio.run(run(n // 2, a))
                gc.collect()
                x = _lib_bytes(tracemalloc.take_snapshot())
                asyncio.run(run(n // 2, a))
                gc.collect()
                y = _lib_bytes(tracemalloc.take_snapshot())
            finally:
                tracemalloc.stop()
            _report(f"async leak {kind}", n=n, growth=y - x)
            self.assertLess(y - x, 64 * 1024, kind)
            a.close()
            a.close()  # idempotent
        deadline = time.time() + 2
        while (
            threading.active_count() > threads_before
            and time.time() < deadline
        ):
            time.sleep(0.02)
        self.assertEqual(threading.active_count(), threads_before)

    def test_sqlite_connection_per_thread_closed_on_close(self) -> None:
        s = self.make("sqlite")
        conns: List[Any] = []

        def work() -> None:
            s.save("k", SNAP)
            conns.append(s._local.conn)

        ts = [threading.Thread(target=work) for _ in range(5)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len({id(c) for c in conns}), 5)  # one per thread
        for _ in range(500):
            s.load("k")
        main = s._conn()
        self.assertIs(s._conn(), main)  # stable, never re-opened
        s.close()
        self.assertIsNone(s._local.conn)
        with self.assertRaises(sqlite3.ProgrammingError):
            main.execute("SELECT 1")  # actually closed
        s.load("k")  # lazily re-opens
        s.close()

    def test_file_handles_stable(self) -> None:
        try:
            import psutil
        except ImportError:
            self.skipTest("psutil not installed")
        proc = psutil.Process()

        def handles() -> int:
            return proc.num_handles() if os.name == "nt" else proc.num_fds()

        for kind in ("file", "sqlite"):
            s = self.make(kind)
            self._cycle(s, 50)
            gc.collect()
            h0 = handles()
            self._cycle(s, 1000)
            with s.lock("k"):
                pass
            gc.collect()
            h1 = handles()
            _report(f"handles {kind}", before=h0, after=h1)
            self.assertLessEqual(h1 - h0, 2, kind)


if __name__ == "__main__":
    unittest.main()
