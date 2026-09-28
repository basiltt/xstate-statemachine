# tests/persistence/test_file_store.py
"""#259: `FileStore` specifics -- key encoding (X0.9), path-escape refusal,
atomic write under a fault hook, stale-lock reclaim, permissions, listing
ignores foreign files."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Any

import pytest

from src.xstate_statemachine.persistence import (
    FileStore,
    InvalidKeyError,
    LockTimeoutError,
)
from src.xstate_statemachine.persistence.file_store import (
    _WINDOWS_RESERVED,
    decode_key,
    encode_key,
)

SNAP = json.dumps(
    {"version": 4, "status": "running", "context": {}, "state_ids": ["m.a"]}
)


class TestKeyEncoding:
    @pytest.mark.parametrize(
        "key",
        [
            "order-1",
            "Order-1",
            "ORDER",
            "a/b",
            "../etc/passwd",
            "con",
            "CON.txt",
            "nul",
            "spaces here",
            "ünïcödé-🔥",
            "%25",
            "a" * 200,
        ],
    )
    def test_reversible(self, key: str) -> None:
        enc = encode_key(key)
        assert decode_key(enc) == key
        assert "/" not in enc and "\\" not in enc and ".." not in enc
        assert all(c.isalnum() or c in "-_%" for c in enc)

    def test_case_fold_collision_free(self) -> None:
        # On a case-insensitive filesystem these must not share a file.
        a, b = encode_key("Order"), encode_key("order")
        assert a != b
        assert a.lower() != b.lower()

    def test_windows_reserved_names_prefixed(self) -> None:
        # Lower-case device names pass the safe-char filter unchanged, so
        # they need the prefix; upper-case ones are already percent-escaped
        # (and therefore harmless) but must still round-trip.
        for name in ("con", "nul", "com1", "lpt9", "aux"):
            enc = encode_key(name)
            assert enc.startswith("%5f"), (name, enc)
            assert decode_key(enc) == name
        for name in ("CON", "Nul", "aux.json", "con.txt"):
            enc = encode_key(name)
            assert not _WINDOWS_RESERVED.match(enc) or enc.startswith("%5f")
            assert decode_key(enc) == name

    def test_length_bound(self) -> None:
        # 200 non-ASCII chars → up to 200*4*3 = 2400 chars; FileStore keys
        # are validated at 200 code points by the shared rule, and the
        # encoded name for a worst-case ASCII-heavy key stays < 255.
        assert len(encode_key("a" * 200) + ".xsm.json") < 255


class TestPathSafety:
    @pytest.mark.parametrize(
        "bad",
        [
            "..",
            ".",
            "a/b",
            "a\\b",
            "/abs",
            "C:\\x" if sys.platform == "win32" else "/x",
        ],
    )
    def test_rejects_path_like_keys(self, tmp_path: Any, bad: str) -> None:
        store = FileStore(tmp_path / "s")
        with pytest.raises(InvalidKeyError):
            store.save(bad, SNAP)

    def test_files_stay_inside_directory(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s")
        store.save("..%2f..%2fetc", SNAP)  # a key that LOOKS like an escape
        store.save("con", SNAP)
        for p in (tmp_path / "s").iterdir():
            assert p.parent == tmp_path / "s"
        assert sorted(store.list_keys()) == ["..%2f..%2fetc", "con"]
        assert not (tmp_path / "etc").exists()

    @pytest.mark.skipif(os.name != "posix", reason="POSIX modes")
    def test_permissions(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        assert (tmp_path / "s").stat().st_mode & 0o777 == 0o700
        f = next((tmp_path / "s").glob("*.xsm.json"))
        assert f.stat().st_mode & 0o777 == 0o600


class TestAtomicWrite:
    def test_crash_before_replace_leaves_previous_intact(
        self, tmp_path: Any
    ) -> None:
        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        before = store.load("k")

        def crash(tmp: str) -> None:
            # Simulate the process dying between fsync and os.replace.
            raise OSError("simulated crash mid-write")

        store._before_replace_hook = crash
        with pytest.raises(OSError, match="simulated"):
            store.save("k", SNAP.replace("running", "stopped"))
        store._before_replace_hook = None
        after = store.load("k")
        assert after == before  # previous record intact, version unchanged
        # No temp litter left behind.
        assert not list((tmp_path / "s").glob(".tmp-*"))

    def test_corrupt_file_is_typed_error(self, tmp_path: Any) -> None:
        from src.xstate_statemachine.exceptions import SnapshotCorruptError

        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        f = next((tmp_path / "s").glob("*.xsm.json"))
        f.write_text("{not json", encoding="utf-8")
        with pytest.raises(SnapshotCorruptError):
            store.load("k")
        f.write_text(json.dumps({"snapshot": "x"}), encoding="utf-8")
        with pytest.raises(SnapshotCorruptError):
            store.load("k")

    def test_record_carries_format_version_and_refuses_newer(
        self, tmp_path: Any
    ) -> None:
        """X0.10: a per-file FORMAT version, distinct from the record's
        optimistic-locking `version`."""
        from src.xstate_statemachine.exceptions import SnapshotCorruptError
        from src.xstate_statemachine.persistence.file_store import (
            FORMAT_VERSION,
        )

        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        f = next((tmp_path / "s").glob("*.xsm.json"))
        rec = json.loads(f.read_text(encoding="utf-8"))
        assert rec["format"] == FORMAT_VERSION and rec["version"] == 1
        # a pre-`format` record (0.11.0 dev) reads as format 1
        del rec["format"]
        f.write_text(json.dumps(rec), encoding="utf-8")
        assert store.load("k").version == 1
        # a newer format is refused, not guessed at
        rec["format"] = FORMAT_VERSION + 1
        f.write_text(json.dumps(rec), encoding="utf-8")
        with pytest.raises(SnapshotCorruptError, match="newer"):
            store.load("k")

    def test_list_ignores_foreign_and_temp_files(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        (tmp_path / "s" / "README.txt").write_text("x")
        (tmp_path / "s" / ".tmp-abc.xsm.json").write_text("x")
        (tmp_path / "s" / "%zz.xsm.json").write_text("x")  # undecodable
        assert store.list_keys() == ["k"]


class TestLocks:
    def test_stale_lock_is_reclaimed(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s", stale_lock_after=0.05)
        lock_path = store._lock_path("k")
        # A lock file left by a dead pid long ago; no OS lock is held.
        lock_path.write_bytes(b"\x00" + b"999999 1.0\n".ljust(63))
        t0 = time.monotonic()
        with store.lock("k", timeout=2):
            pass
        assert time.monotonic() - t0 < 1.5

    def test_lock_timeout_names_holder(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s", stale_lock_after=60)
        entered, release = threading.Event(), threading.Event()

        def holder() -> None:
            with store.lock("k", timeout=5):
                entered.set()
                release.wait(5)

        t = threading.Thread(target=holder)
        t.start()
        entered.wait(5)
        try:
            with pytest.raises(LockTimeoutError) as ei:
                with store.lock("k", timeout=0.2):
                    pass
            assert str(os.getpid()) in str(ei.value)
        finally:
            release.set()
            t.join(5)

    def test_forget_removes_lock_file(self, tmp_path: Any) -> None:
        store = FileStore(tmp_path / "s")
        store.save("k", SNAP)
        with store.lock("k"):
            pass
        assert store._lock_path("k").exists()
        counts = store.forget("k")
        assert counts == {"snapshots": 1, "locks": 1}
        assert not store._lock_path("k").exists()

    def test_health(self, tmp_path: Any) -> None:
        h = FileStore(tmp_path / "s").health()
        assert h["ok"] and h["backend"] == "file"
