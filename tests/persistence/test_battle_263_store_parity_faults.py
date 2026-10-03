# tests/persistence/test_battle_263_store_parity_faults.py
"""#263 battle, part B (continued): `machine_version` parity across every
store, failure injection on the versioned record, and the stress run.

Split from `test_battle_263_cli_stores_scaling.py` to stay < 800 lines.
"""

from __future__ import annotations

import errno
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterator
from unittest import mock

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.exceptions import (
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
V1 = {
    "id": "o",
    "version": "1.0",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}
V2 = {**V1, "version": "2.0"}
BLOB = '{"status":"active","state_ids":["o.a"],"context":{}}'


# -----------------------------------------------------------------------------
# 🧰 store factories -- one per backend, each skipped without its extra
# -----------------------------------------------------------------------------
def _sqlalchemy(tmp: Path) -> Any:
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

    eng = create_engine(f"sqlite:///{tmp / 'sa.db'}", future=True)
    return SQLAlchemyStore(sessionmaker(eng))


def _redis(tmp: Path) -> Any:
    fakeredis = pytest.importorskip("fakeredis")
    from src.xstate_statemachine.contrib.redis import RedisStore

    return RedisStore(
        fakeredis.FakeRedis(server=fakeredis.FakeServer()),
        prefix=f"t-{uuid.uuid4().hex[:8]}",
    )


FACTORIES: Dict[str, Callable[[Path], Any]] = {
    "memory": lambda p: MemoryStore(),
    "file": lambda p: FileStore(p / "f"),
    "sqlite": lambda p: SQLiteStore(p / "s.db"),
    "sqlalchemy": _sqlalchemy,
    "redis": _redis,
}


@pytest.fixture(params=sorted(FACTORIES))
def store(request: Any, tmp_path: Path) -> Iterator[Any]:
    s = FACTORIES[request.param](tmp_path)
    yield s
    getattr(s, "close", lambda: None)()


# -----------------------------------------------------------------------------
# 3️⃣ parity
# -----------------------------------------------------------------------------
class TestLabelParity:
    @pytest.mark.parametrize(
        "label, expect",
        [
            ("", ""),
            (None, ""),
            ("1.0", "1.0"),
            ("a\nb", "a\nb"),
            ("é😀‮", "é😀‮"),
            ("x" * MAX_MACHINE_VERSION_LENGTH, "x" * 255),
        ],
        ids=["empty", "none", "plain", "newline", "unicode", "at-limit"],
    )
    def test_round_trips_identically(
        self, store: Any, label: Any, expect: str
    ) -> None:
        store.save("k", BLOB, machine_version=label)

        assert store.load("k").machine_version == expect

    @pytest.mark.parametrize(
        "label",
        ["x" * 10_000, "x" * 256, "a\x00b"],
        ids=["10kB", "256", "nul"],
    )
    def test_unstorable_label_is_value_error_everywhere(
        self, store: Any, label: str
    ) -> None:
        # 🔥 Before: Memory/File/SQLite kept 10 kB and NUL; SQLAlchemy and
        #    Django columns are VARCHAR(255) (a driver DataError on
        #    Postgres), and Postgres rejects NUL. One rule now, at the call.
        with pytest.raises(ValueError, match="machine_version"):
            store.save("k", BLOB, machine_version=label)

        assert store.load("k") is None

    @pytest.mark.parametrize("bad", [1, 1.0, ["1"], b"1"])
    def test_non_str_label_is_type_error(self, store: Any, bad: Any) -> None:
        with pytest.raises(TypeError):
            store.save("k", BLOB, machine_version=bad)


@pytest.mark.parametrize("kind", ["sqlalchemy", "redis"])
def test_async_stores_apply_the_same_label_rule(
    tmp_path: Path, kind: str
) -> None:
    # 📝 The async SQLAlchemy/Redis stores skipped `check_save_args`.
    import asyncio

    if kind == "sqlalchemy":
        pytest.importorskip("aiosqlite")
        from sqlalchemy.ext.asyncio import (
            async_sessionmaker,
            create_async_engine,
        )

        from src.xstate_statemachine.contrib.sqlalchemy import (
            AsyncSQLAlchemyStore,
        )

        eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'a.db'}")
        s: Any = AsyncSQLAlchemyStore(async_sessionmaker(eng))
    else:
        fakeredis = pytest.importorskip("fakeredis")
        from src.xstate_statemachine.contrib.redis import AsyncRedisStore

        s = AsyncRedisStore(fakeredis.FakeAsyncRedis(), prefix="t")

    async def go() -> None:
        with pytest.raises(ValueError):
            await s.save("k", BLOB, machine_version="x" * 300)
        with pytest.raises(TypeError):
            await s.save("k", BLOB, machine_version=7)  # type: ignore

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 4️⃣ failure injection on the versioned record
# -----------------------------------------------------------------------------
def _saved(kind: str, tmp: Path) -> Any:
    s = FACTORIES[kind](tmp)
    with persisted(s, "k", create_machine(V1)):
        pass
    return s


def _migrator() -> SnapshotMigrator:
    mig = SnapshotMigrator()
    mig.add("1.0", "2.0", lambda b: b)
    return mig


class TestCorruptLabel:
    @pytest.mark.parametrize(
        "bad", [1, [1], {"a": 1}, 1e308, float("nan"), None, True]
    )
    def test_file_record_label_type_confusion(
        self, tmp_path: Path, bad: Any
    ) -> None:
        s = _saved("file", tmp_path)
        path = next((tmp_path / "f").glob("*.xsm.json"))
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec["machine_version"] = bad
        path.write_text(json.dumps(rec), encoding="utf-8")

        with pytest.raises(SnapshotCorruptError):
            with persisted(s, "k", create_machine(V2)):
                pass
        with pytest.raises(SnapshotCorruptError):
            s.list_versions()

    # 📝 TEXT affinity turns 1 / 1e308 into the str "1" / "1e+308" --
    #    a valid (if odd) label. Only a BLOB is a non-str label.
    @pytest.mark.parametrize("bad", [b"1.0", b"\x00\xff"])
    def test_sqlite_row_label_type_confusion(
        self, tmp_path: Path, bad: Any
    ) -> None:
        s = _saved("sqlite", tmp_path)
        s.close()
        con = sqlite3.connect(tmp_path / "s.db")
        con.execute("UPDATE statecharts SET machine_version = ?", (bad,))
        con.commit()
        con.close()
        s = SQLiteStore(tmp_path / "s.db")

        with pytest.raises(SnapshotCorruptError):
            s.load("k")
        with pytest.raises(SnapshotCorruptError):
            s.list_versions()

    def test_every_byte_of_blob_label_mutated(self, tmp_path: Path) -> None:
        # 💡 Mutate each byte of `"1.0"` inside the stored blob: every
        #    outcome is a restore, a version mismatch or a typed error.
        s = _saved("memory", tmp_path)
        rec = s.load("k")
        marker = '"machine_version": "1.0"'
        if marker not in rec.snapshot:
            marker = '"machine_version":"1.0"'
        start = rec.snapshot.index(marker) + len(marker) - 5
        outcomes = set()
        for pos in range(5):
            for byte in ("\x00", '"', "\\", "x", "9", "ÿ"):
                text = (
                    rec.snapshot[: start + pos]
                    + byte
                    + rec.snapshot[start + pos + 1 :]
                )
                s2 = MemoryStore()
                s2.save("k", text, machine_version="1.0")
                try:
                    with persisted(s2, "k", create_machine(V2)):
                        outcomes.add("ok")
                except MachineVersionMismatchError:
                    outcomes.add("mismatch")
                except XStateMachineError:
                    outcomes.add("typed")

        assert outcomes <= {"ok", "mismatch", "typed"}
        assert "mismatch" in outcomes


class TestDiskFull:
    def test_file_store_enospc_on_migrated_resave(
        self, tmp_path: Path
    ) -> None:
        # 🔥 ENOSPC escaped as a bare OSError (outside
        #    `except XStateMachineError`); now a StoreError that is still
        #    an OSError with errno. The 1.0 record stands.
        s = _saved("file", tmp_path)

        def full(*_a: Any) -> None:
            raise OSError(errno.ENOSPC, "No space left on device")

        with mock.patch(
            "src.xstate_statemachine.persistence.file_store.os.fsync", full
        ):
            with pytest.raises(StoreError) as info:
                with persisted(
                    s, "k", create_machine(V2), migrator=_migrator()
                ):
                    pass

        assert isinstance(info.value, OSError)
        assert info.value.errno == errno.ENOSPC
        assert s.load("k").machine_version == "1.0"
        assert not list((tmp_path / "f").glob(".tmp-*"))

    def test_sqlite_disk_full_is_store_error(self, tmp_path: Path) -> None:
        s = _saved("sqlite", tmp_path)
        real = s._conn

        class Full:
            def __init__(self, c: Any) -> None:
                self._c = c

            def execute(self, sql: str, *a: Any) -> Any:
                if sql.lstrip().upper().startswith(("UPDATE", "INSERT")):
                    raise sqlite3.OperationalError("database or disk is full")
                return self._c.execute(sql, *a)

            def __getattr__(self, n: str) -> Any:
                return getattr(self._c, n)

        with mock.patch.object(s, "_conn", lambda: Full(real())):
            with pytest.raises(StoreError):
                with persisted(
                    s, "k", create_machine(V2), migrator=_migrator()
                ):
                    pass

        assert s.load("k").machine_version == "1.0"


_KILL = textwrap.dedent("""
    import os, sys
    sys.path.insert(0, {root!r})
    from src.xstate_statemachine import create_machine
    from src.xstate_statemachine.persistence import (
        FileStore, SnapshotMigrator, persisted)
    from src.xstate_statemachine.persistence import file_store as fs
    V2 = {v2!r}
    s = FileStore({d!r})
    mig = SnapshotMigrator(); mig.add("1.0", "2.0", lambda b: b)
    real = fs._replace
    def die(src, dst):
        if {after!r}:
            real(src, dst)
        os._exit(9)
    fs._replace = die
    with persisted(s, "k", create_machine(V2), migrator=mig):
        pass
    """)


@pytest.mark.parametrize("after", [False, True], ids=["pre-rename", "post"])
def test_kill_9_during_migrated_save_is_old_or_new(
    tmp_path: Path, after: bool
) -> None:
    # 🏛️ FileStore has ONE durable write per save (temp + fsync +
    #    os.replace); a kill either side of the rename leaves exactly the
    #    1.0 or the complete 2.0 record, never a torn one.
    _saved("file", tmp_path)
    code = _KILL.format(
        root=str(ROOT), v2=V2, d=str(tmp_path / "f"), after=after
    )

    proc = subprocess.run([sys.executable, "-c", code], timeout=60)
    rec = FileStore(tmp_path / "f").load("k")

    assert proc.returncode == 9
    assert rec.machine_version == ("2.0" if after else "1.0")
    assert json.loads(rec.snapshot)["machine_version"] == rec.machine_version


# -----------------------------------------------------------------------------
# 7️⃣ stress -- opt-in: `XSM_STRESS=1 pytest -m stress`
# -----------------------------------------------------------------------------
@pytest.mark.stress
@pytest.mark.skipif(
    not os.environ.get("XSM_STRESS"), reason="stress run: set XSM_STRESS=1"
)
def test_stress_100k_alternating_labels_then_stale(tmp_path: Path) -> None:
    psutil = pytest.importorskip("psutil")
    from src.xstate_statemachine.cli.commands import snapshots as cli

    n = 100_000
    s = SQLiteStore(tmp_path / "s.db")
    t0 = time.perf_counter()
    with s.transaction() if hasattr(s, "transaction") else _null():
        for i in range(n):
            s.save(f"k{i % 20_000:05}", BLOB, machine_version=f"{i % 2}.0")
    saves = time.perf_counter() - t0
    s.close()
    chart = tmp_path / "m.json"
    chart.write_text(json.dumps({**V1, "version": "1.0"}), encoding="utf-8")

    t1 = time.perf_counter()
    pairs = cli._label_pairs(
        cli.open_store("sqlite:///" + str(tmp_path / "s.db")), "", 2**62
    )
    stale = time.perf_counter() - t1
    rss = psutil.Process().memory_info().rss

    print(f"saves={saves:.1f}s stale={stale:.3f}s rss={rss / 2**20:.0f}MiB")
    assert len(pairs) == 20_000 and stale < 2.0


class _null:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *a: Any) -> None:
        return None
