# tests/persistence/test_battle_263_cli_stores_scaling.py
"""#263 battle, part B: `xsm snapshots`, the stores' `machine_version`,
scaling of `--stale`, failure injection, X0 re-verification.

Every test is Arrange / Act / Assert. The part-A file owns migration
semantics; this one owns the ops surface (CLI + stores).
"""

from __future__ import annotations

import contextlib
import errno
import io
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional
from unittest import mock

import pytest

from src.xstate_statemachine import SyncInterpreter, create_machine
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands import snapshots as cli
from src.xstate_statemachine.exceptions import (
    InvalidKeyError,
    SnapshotCorruptError,
    StoreError,
    XStateMachineError,
)
from src.xstate_statemachine.persistence import (
    FileStore,
    MachineVersionMismatchError,
    MemoryStore,
    SnapshotMigrator,
    SQLiteStore,
    persisted,
)
from src.xstate_statemachine.persistence.store import (
    MAX_MACHINE_VERSION_LENGTH,
)

ROOT = Path(__file__).resolve().parents[2]
PII = "PII-4111-1111-1111-1111"
V1 = {
    "id": "o",
    "version": "1.0",
    "initial": "a",
    "context": {"card": PII},
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}
V2 = {**V1, "version": "2.0"}
BLOB = json.dumps(
    {"status": "active", "state_ids": ["o.a"], "context": {"card": PII}}
)


# -----------------------------------------------------------------------------
# 🧰 helpers
# -----------------------------------------------------------------------------
def _url(kind: str, path: Path) -> str:
    return f"{kind}:///" + str(path).replace("\\", "/")


def _chart(tmp_path: Path, cfg: Dict[str, Any], name: str = "m.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return str(p)


def _run_cli(
    *args: str, cwd: Optional[Path] = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "snapshots", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd or ROOT),
        timeout=120,
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT / "src"),
            "PYTHONIOENCODING": "utf-8",
        },
    )


def _in_proc(**kw: Any) -> Dict[str, Any]:
    """Run `run_snapshots(as_json=True)` in-process; return the JSON."""
    buf = io.StringIO()
    reset_console()  # 📝 the console binds sys.stdout when built
    with contextlib.redirect_stdout(buf):
        cli.run_snapshots(as_json=True, **kw)
    reset_console()
    return json.loads(buf.getvalue())


@contextlib.contextmanager
def _count_loads(monkeypatch: Any) -> Iterator[Dict[str, int]]:
    counter = {"load": 0}
    real_open = cli.open_store

    def opener(url: str, **kw: Any) -> Any:
        store = real_open(url, **kw)
        real_load = store.load

        def load(key: str) -> Any:
            counter["load"] += 1
            return real_load(key)

        store.load = load
        return store

    monkeypatch.setattr(cli, "open_store", opener)
    yield counter


def _fill(store: Any, n: int, stale_every: int) -> None:
    for i in range(n):
        label = "1.0" if i % stale_every == 0 else "2.0"
        store.save(f"k{i:06}", BLOB, machine_version=label)


# -----------------------------------------------------------------------------
# 1️⃣ `--stale` scaling
# -----------------------------------------------------------------------------
class TestStaleScaling:
    N = 10_000

    @pytest.mark.parametrize("kind", ["sqlite", "file"])
    def test_stale_reads_labels_not_blobs(
        self, tmp_path: Path, monkeypatch: Any, kind: str
    ) -> None:
        # 📝 Before the battle every key was `load()`-ed (blob read +
        #    decoded) just to compare a label the store keeps beside it.
        target = tmp_path / ("s.db" if kind == "sqlite" else "fs")
        store = (
            SQLiteStore(target)
            if kind == "sqlite"
            else FileStore(target, fsync=False)
        )
        _fill(store, self.N, stale_every=100)
        getattr(store, "close", lambda: None)()
        chart = _chart(tmp_path, V2)

        with _count_loads(monkeypatch) as counter:
            t0 = time.perf_counter()
            out = _in_proc(
                store_url=_url(kind, target), json_file=chart, stale=True
            )
            wall = time.perf_counter() - t0

        assert out["total"] == self.N // 100 == out["count"]
        assert counter["load"] == self.N // 100  # only the rows shown
        if kind == "sqlite":
            assert wall < 2.0, wall

    def test_stale_scans_past_the_limit(self, tmp_path: Path) -> None:
        # 🔥 `--limit` used to cap the keys SCANNED: a stale key past the
        #    first 1000 was silently missing from the drain list.
        store = SQLiteStore(tmp_path / "s.db")
        for i in range(1500):
            store.save(f"k{i:05}", BLOB, machine_version="2.0")
        store.save("zz-late", BLOB, machine_version="1.0")
        store.close()

        out = _in_proc(
            store_url=_url("sqlite", tmp_path / "s.db"),
            json_file=_chart(tmp_path, V2),
            stale=True,
        )

        assert [r["key"] for r in out["snapshots"]] == ["zz-late"]

    def test_limit_truncation_is_reported(self, tmp_path: Path) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        _fill(store, 50, stale_every=1)
        store.close()

        out = _in_proc(
            store_url=_url("sqlite", tmp_path / "s.db"),
            json_file=_chart(tmp_path, V2),
            stale=True,
            limit=10,
        )

        assert (out["count"], out["total"], out["truncated"]) == (
            10,
            50,
            True,
        )

    def test_third_party_store_without_list_versions_still_works(
        self, monkeypatch: Any
    ) -> None:
        # 💡 Duck-typed fallback: a store with only the Protocol surface.
        inner = MemoryStore()
        inner.save("a", BLOB, machine_version="1.0")
        inner.save("b", BLOB, machine_version="2.0")

        class Plain:
            load = staticmethod(inner.load)
            list_keys = staticmethod(inner.list_keys)

        pairs = cli._label_pairs(Plain(), "", 10)

        assert pairs == [("a", "1.0"), ("b", "2.0")]

    @pytest.mark.parametrize(
        "make",
        [
            lambda p: MemoryStore(),
            lambda p: FileStore(p / "f"),
            lambda p: SQLiteStore(p / "s.db"),
        ],
        ids=["memory", "file", "sqlite"],
    )
    def test_list_versions_matches_load(
        self, tmp_path: Path, make: Callable[[Path], Any]
    ) -> None:
        store = make(tmp_path)
        labels = {"a": "", "b": "1.0", "c": "é😀\u202e", "d\n": "a\nb"}
        for k, mv in labels.items():
            store.save(k, BLOB, machine_version=mv)

        got = store.list_versions(prefix="", limit=10)

        assert got == sorted(labels.items())
        assert store.list_versions(prefix="b", limit=10) == [("b", "1.0")]
        assert store.list_versions(limit=1) == [("a", "")]

    def test_file_header_read_is_not_fooled_by_key_text(
        self, tmp_path: Path
    ) -> None:
        # 🛡️ The header parse walks JSON members; a key that CONTAINS the
        #    text `"machine_version":"9"` must not be read as the label.
        store = FileStore(tmp_path / "f")
        key = 'x","machine_version":"9'
        store.save(key, BLOB, machine_version="1.0")

        assert store.list_versions() == [(key, "1.0")]

    def test_file_old_layout_record_falls_back_to_full_read(
        self, tmp_path: Path
    ) -> None:
        # 📝 Records written before the battle put the label AFTER the
        #    blob; the header read gives up and the validated read decides.
        store = FileStore(tmp_path / "f")
        store.save("k", BLOB, machine_version="1.0")
        path = next((tmp_path / "f").glob("*.xsm.json"))
        rec = json.loads(path.read_text(encoding="utf-8"))
        old = {k: rec[k] for k in ("format", "key", "snapshot", "version")}
        old.update(machine_version="1.0", updated_at=rec["updated_at"])
        path.write_text(json.dumps(old), encoding="utf-8")

        assert store.list_versions() == [("k", "1.0")]


# -----------------------------------------------------------------------------
# 2️⃣ CLI contract
# -----------------------------------------------------------------------------
class TestCliContract:
    def _store(self, tmp_path: Path, labels: Dict[str, str]) -> str:
        store = SQLiteStore(tmp_path / "s.db")
        for k, mv in labels.items():
            store.save(k, BLOB, machine_version=mv)
        store.close()
        return _url("sqlite", tmp_path / "s.db")

    def test_fail_if_stale_exit_codes(self, tmp_path: Path) -> None:
        url = self._store(tmp_path, {"old": "1.0", "new": "2.0"})
        chart = _chart(tmp_path, V2)

        listing = _run_cli("--store", url, chart, "--stale")
        gate = _run_cli("--store", url, chart, "--fail-if-stale", "--json")
        clean = _run_cli(
            "--store", url, _chart(tmp_path, V1, "v1.json"), "--fail-if-stale"
        )

        assert listing.returncode == 0  # a listing, not a gate
        assert gate.returncode == cli.EXIT_STALE
        assert json.loads(gate.stdout)["count"] == 1
        # V1 chart: "new" (2.0) is stale against it -> still exit 1
        assert clean.returncode == cli.EXIT_STALE

    def test_fail_if_stale_zero_when_drained(self, tmp_path: Path) -> None:
        url = self._store(tmp_path, {"new": "2.0"})

        out = _run_cli("--store", url, _chart(tmp_path, V2), "--fail-if-stale")

        assert out.returncode == 0 and "no stale snapshots" in out.stdout

    @pytest.mark.parametrize(
        "labels",
        [
            {},
            {"one": "1.0"},
            {"\u202ertl-é😀": "1.0", "line\nbreak": "1.0\n2.0"},
        ],
        ids=["empty", "one", "unicode-newline"],
    )
    def test_json_is_valid_json(
        self, tmp_path: Path, labels: Dict[str, str]
    ) -> None:
        url = self._store(tmp_path, labels)

        out = _run_cli("--store", url, "--json")

        data = json.loads(out.stdout)
        assert out.returncode == 0
        assert {r["key"] for r in data["snapshots"]} == set(labels)

    def test_nul_key_refused_at_save(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidKeyError):
            SQLiteStore(tmp_path / "s.db").save("a\x00b", BLOB)

    def test_plain_output_keeps_newline_key_on_one_row(
        self, tmp_path: Path
    ) -> None:
        # 🛡️ A key with "\n" split one row in two -- and could forge a
        #    fake row (`"x\nfake-key  1  2.0"`) in a human's drain list.
        url = self._store(tmp_path, {"evil\nFAKE-ROW": "1.0"})

        out = _run_cli("--store", url, "--plain")

        lines = [ln for ln in out.stdout.splitlines() if "FAKE-ROW" in ln]
        assert len(lines) == 1 and "evil\\nFAKE-ROW" in lines[0]

    @pytest.mark.parametrize(
        "content",
        ['{"foo": 1}', "[1, 2]", "not json", '{"id": "x", "states": 5}'],
        ids=["no-id", "array", "garbage", "bad-states"],
    )
    def test_non_machine_json_is_exit_2_no_traceback(
        self, tmp_path: Path, content: str
    ) -> None:
        url = self._store(tmp_path, {"k": "1.0"})
        bad = tmp_path / "bad.json"
        bad.write_text(content, encoding="utf-8")

        out = _run_cli("--store", url, str(bad), "--stale")

        assert out.returncode == cli.EXIT_USAGE
        assert "Traceback" not in out.stderr
        assert "error:" in out.stderr

    def test_store_url_forms(self, tmp_path: Path) -> None:
        url = self._store(tmp_path, {"k": "1.0"})

        # 📝 SQLAlchemy convention: `///rel`, `////abs` (or `///C:/abs`).
        #    The relative form is resolved against the CLI's cwd, so run it
        #    FROM tmp_path: `os.path.relpath(tmp, ROOT)` has no answer when
        #    the two are on different drives (GitHub's Windows runners put
        #    the checkout on D: and TEMP on C:).
        absolute = _run_cli("--store", url, "--json")
        relative = _run_cli(
            "--store", "sqlite:///s.db", "--json", cwd=tmp_path
        )

        assert json.loads(absolute.stdout)["count"] == 1
        assert json.loads(relative.stdout)["count"] == 1

    @pytest.mark.parametrize(
        "url, needle",
        [
            ("memory://", "memory://"),
            ("redis://x", "unsupported store URL"),
            ("sqlite:///{t}/missing.db", "no such database file"),
            ("file:///{t}/missing-dir", "no such directory"),
        ],
    )
    def test_meaningless_or_missing_store_refused(
        self, tmp_path: Path, url: str, needle: str
    ) -> None:
        # 📝 Before: memory:// and a typo'd path both answered "store is
        #    empty", exit 0 -- and the typo CREATED an empty database.
        t = str(tmp_path).replace("\\", "/")

        out = _run_cli("--store", url.format(t=t))

        assert out.returncode == cli.EXIT_USAGE and needle in out.stderr
        assert not (tmp_path / "missing.db").exists()
        assert not (tmp_path / "missing-dir").exists()

    def test_unreadable_store_is_typed_exit(self, tmp_path: Path) -> None:
        # 💡 A corrupt database file stands in for an unreadable store.
        (tmp_path / "junk.db").write_bytes(b"not a sqlite database" * 100)

        out = _run_cli("--store", _url("sqlite", tmp_path / "junk.db"))

        assert out.returncode == cli.EXIT_USAGE
        assert "Traceback" not in out.stderr

    def test_versionless_chart_finds_nothing_stale(
        self, tmp_path: Path
    ) -> None:
        # 🏛️ Agrees with restore: a chart with no version never
        #    mismatches; an unlabelled record cannot be checked.
        url = self._store(tmp_path, {"a": "1.0", "b": ""})
        unversioned = {k: v for k, v in V2.items() if k != "version"}

        none = _in_proc(
            store_url=url,
            json_file=_chart(tmp_path, unversioned),
            stale=True,
        )
        v2 = _in_proc(
            store_url=url,
            json_file=_chart(tmp_path, V2, "v2.json"),
            stale=True,
        )

        assert none["count"] == 0
        assert [r["key"] for r in v2["snapshots"]] == ["a"]

    def test_unlabelled_record_restores_under_v2_so_not_stale(
        self, tmp_path: Path
    ) -> None:
        # ✅ The CLI's "not stale" claim for "" is the restore behaviour.
        store = MemoryStore()
        i = SyncInterpreter(create_machine(V1)).start()
        blob = json.loads(i.get_snapshot())
        i.stop()
        blob.pop("machine_version", None)
        store.save("k", json.dumps(blob), machine_version="")

        with persisted(store, "k", create_machine(V2)) as restored:
            assert restored.current_state_ids == {"o.a"}

    def test_json_never_contains_context(self, tmp_path: Path) -> None:
        # 🛡️ X0.5: rows carry key/version/labels/state -- never context.
        url = self._store(tmp_path, {"k": "1.0"})

        out = _run_cli("--store", url, _chart(tmp_path, V2), "--json")

        assert PII not in out.stdout
        row = json.loads(out.stdout)["snapshots"][0]
        assert "context" not in row and "snapshot" not in row


# -----------------------------------------------------------------------------
# 5️⃣ X0: hostile machine-JSON paths and store paths
# -----------------------------------------------------------------------------
class TestHostileInputs:
    def test_directory_as_machine_json(self, tmp_path: Path) -> None:
        url = _url("sqlite", tmp_path / "s.db")
        SQLiteStore(tmp_path / "s.db").close()

        out = _run_cli("--store", url, str(tmp_path), "--stale")

        assert out.returncode == cli.EXIT_USAGE
        assert "is not a file" in out.stderr

    @pytest.mark.skipif(os.name != "nt", reason="NUL device is Windows")
    def test_device_as_machine_json(self, tmp_path: Path) -> None:
        SQLiteStore(tmp_path / "s.db").close()

        out = _run_cli(
            "--store", _url("sqlite", tmp_path / "s.db"), "NUL", "--stale"
        )

        assert out.returncode == cli.EXIT_USAGE

    def test_nesting_bomb_is_bounded(self, tmp_path: Path) -> None:
        # 🔥 Was a RecursionError traceback. A small bomb parses-and-fails
        #    fast; the 100 MB one is refused by size before any read.
        SQLiteStore(tmp_path / "s.db").close()
        url = _url("sqlite", tmp_path / "s.db")
        small = tmp_path / "bomb.json"
        small.write_text("[" * 200_000, encoding="utf-8")
        big = tmp_path / "big.json"
        with open(big, "wb") as fh:
            fh.truncate(cli.MAX_MACHINE_JSON_BYTES + 1)

        t0 = time.perf_counter()
        a = _run_cli("--store", url, str(small), "--stale")
        b = _run_cli("--store", url, str(big), "--stale")

        assert a.returncode == b.returncode == cli.EXIT_USAGE
        assert "Traceback" not in a.stderr + b.stderr
        assert "larger than" in b.stderr
        assert time.perf_counter() - t0 < 30

    def test_dotdot_file_url_resolves_like_a_path(
        self, tmp_path: Path
    ) -> None:
        # 📝 `--store` is an operator-supplied path (same trust as argv);
        #    `..` is resolved by the OS, not refused. Store KEYS are the
        #    untrusted surface -- see the next test.
        (tmp_path / "real").mkdir()
        FileStore(tmp_path / "real").save("k", BLOB, machine_version="1.0")
        url = _url("file", tmp_path / "sub" / ".." / "real")
        (tmp_path / "sub").mkdir()

        assert _in_proc(store_url=url)["count"] == 1

    @pytest.mark.parametrize(
        "key", ["../../etc/passwd", "..\\..\\x", "/abs", "C:\\x", ".."]
    )
    def test_traversal_key_stays_inside_the_store(
        self, tmp_path: Path, key: str
    ) -> None:
        store = FileStore(tmp_path / "f")
        try:
            store.save(key, BLOB)
        except InvalidKeyError:
            return  # refused outright -- fine
        files = [p for p in tmp_path.rglob("*") if p.is_file()]

        assert all((tmp_path / "f") in p.parents for p in files)
        assert store.load(key) is not None

    def test_failing_migration_step_does_not_leak_context(
        self, tmp_path: Path, caplog: Any
    ) -> None:
        # 🛡️ X0.5: a step that raises with the blob in its message must
        #    not get that text into a stored record; the log carries the
        #    error, never the stored blob's context values.
        store = SQLiteStore(tmp_path / "s.db")
        with persisted(store, "k", create_machine(V1)):
            pass
        before = store.load("k")
        mig = SnapshotMigrator()

        def step(blob: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError("step failed")

        mig.add("1.0", "2.0", step)

        with caplog.at_level(logging.DEBUG, logger="xstate_statemachine"):
            with pytest.raises(Exception):
                with persisted(store, "k", create_machine(V2), migrator=mig):
                    pass

        assert store.load("k") == before
        assert PII not in caplog.text
