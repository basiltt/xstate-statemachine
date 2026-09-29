# tests/contrib/sqlalchemy/test_sqlalchemy_stores.py
"""#284 part 2: store specifics -- the async twin on aiosqlite, schema
versioning (X0.10), `forget()` cascading to the log (X0.5), inbox marks
committing with the save (X0.3), the deadline index, a DATABASE_URL-gated
Postgres smoke test."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("sqlalchemy")

from sqlalchemy import update  # noqa: E402

from src.xstate_statemachine import Interpreter  # noqa: E402
from src.xstate_statemachine.exceptions import (  # noqa: E402
    ConflictError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotTooLargeError,
    StoreError,
)
from src.xstate_statemachine.persistence import (  # noqa: E402
    AuditPlugin,
    Deadline,
    DueTimerScanner,
    IdempotencyPlugin,
    PessimisticLock,
    apersisted,
    persisted,
)
from tests.persistence import test_durable_timers as _timers  # noqa: E402
from tests.persistence import test_store_contract as _store  # noqa: E402

from .conftest import make_store  # noqa: E402


class TestSchema:
    def test_idempotent_and_versioned(self, tmp_path: Any) -> None:
        from sqlalchemy.orm import sessionmaker

        from src.xstate_statemachine.contrib.sqlalchemy import (
            SCHEMA_VERSION,
            SQLAlchemyStore,
        )

        s = make_store(tmp_path)
        again = SQLAlchemyStore(sessionmaker(s._engine))  # no error
        assert again.health()["schema_version"] == SCHEMA_VERSION
        sc = s.tables.schema
        with s._engine.begin() as conn:
            conn.execute(update(sc).values(version=SCHEMA_VERSION + 1))
        with pytest.raises(StoreError, match="newer"):
            SQLAlchemyStore(sessionmaker(s._engine))
        with pytest.raises(StoreError, match="newer"):
            SQLAlchemyStore(sessionmaker(s._engine), create_tables=False)
        s._engine.dispose()

    def test_health_and_bad_args(self, store: Any) -> None:
        h = store.health()
        assert h["ok"] and h["dialect"] and h["keys"] == 0
        from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

        with pytest.raises(ValueError):
            SQLAlchemyStore(lambda: None, lock_ttl_s=0)

    def test_health_reports_failure_without_text(self, store: Any) -> None:
        store._engine.dispose()
        store.tables.snapshots.name  # sanity
        broken = store.tables.snapshots
        store.tables = store.tables.__class__(
            store.tables.metadata,
            broken.to_metadata(
                type(store.tables.metadata)(), name="no_such_table"
            ),
            *store.tables.all()[2:],
            store.tables.schema,
        )
        h = store.health()
        assert h == {
            "ok": False,
            "backend": "sqlalchemy",
            "error": "OperationalError",
        }


class TestSharedTransaction:
    def test_forget_cascades_to_log(self, store: Any) -> None:
        from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyLog

        log = SQLAlchemyLog(store)
        m = _store.machine()
        with persisted(store, "k1", m, plugins=[AuditPlugin(log)]) as i:
            i.send("GO")
        store.save(
            "k1",
            store.load("k1").snapshot,
            deadlines=[Deadline("o.a", 1, 1.0, 5, "after.5.o.a")],
        )
        assert len(log.read("k1")) == 1
        counts = store.forget("k1")
        assert counts == {
            "snapshots": 1,
            "deadlines": 1,
            "locks": 0,
            "log_entries": 1,
        }
        assert log.read("k1") == [] and store.load("k1") is None

    def test_mark_and_audit_roll_back_with_a_failed_save(self, store: Any):
        """Under `PessimisticLock` the lease IS a transaction: a conflict
        at save time leaves no snapshot bump, no inbox mark, no log row."""
        from src.xstate_statemachine.contrib.sqlalchemy import (
            SQLAlchemyInbox,
            SQLAlchemyLog,
        )

        inbox, log = SQLAlchemyInbox(store), SQLAlchemyLog(store)
        m = _store.machine()
        with persisted(store, "k", m):
            pass
        idem = IdempotencyPlugin(inbox, principal=lambda e: "p")
        audit = AuditPlugin(log)
        real_save = store._save_raw

        def conflicting_save(key: str, *a: Any) -> int:
            # 📝 The fenced save fails as if a writer that ignored the
            #    lease had bumped the version (SQLite serialises writers,
            #    so a real concurrent writer would just wait on us).
            real_save(key, *a)
            raise ConflictError(key, 1, 2)

        store._save_raw = conflicting_save
        with pytest.raises(ConflictError):
            with persisted(
                store, "k", m, lock=PessimisticLock(), plugins=[idem, audit]
            ) as i:
                i.send("GO", idempotency_key="e1")
        store._save_raw = real_save
        assert store.load("k").version == 1  # the write rolled back too
        assert inbox.get("p/o/k", "e1") is None
        assert log.read("k") == []
        # and the happy path commits all three together
        with persisted(
            store, "k", m, lock=PessimisticLock(), plugins=[idem, audit]
        ) as i:
            i.send("GO", idempotency_key="e1")
        assert inbox.get("p/o/k", "e1").receipt_json is not None
        assert [r.event_type for r in log.read("k")] == ["GO"]

    def test_lease_expires_and_is_reclaimed(self, tmp_path: Any) -> None:
        s = make_store(tmp_path, lock_ttl_s=0.05)
        with s._fresh() as conn:
            from src.xstate_statemachine.contrib.sqlalchemy import _ops

            assert _ops.try_lock(conn, s.tables, s.tables.snapshots.name,
                                 "k", "dead", 0.05)  # fmt: skip
        with pytest.raises(LockTimeoutError):
            with s.lock("k", timeout=0):
                pass
        time.sleep(0.1)
        with s.lock("k", timeout=1):
            with s.lock("k", timeout=1):  # re-entrant on this thread
                pass
        s._engine.dispose()

    def test_due_keys_index_drives_the_scanner(self, tmp_path: Any) -> None:
        m = _timers.machine(
            {
                **_timers.CFG,
                "states": {
                    **_timers.CFG["states"],
                    "waiting": {
                        "after": {
                            "3600000": {
                                "target": "reminded",
                                "actions": "note",
                            }
                        }
                    },
                },
            }
        )
        s = make_store(tmp_path)
        with persisted(s, "u1", m):
            pass
        now = time.time()
        assert s.due_keys(now) == []
        assert [k for k, _ in s.due_keys(now + 3601)] == ["u1"]
        sc = DueTimerScanner(s, lambda k: m)
        assert sc.run_once(now=now + 3601) == 1
        with persisted(s, "u1", m) as i:
            assert i.current_state_ids == {"r.reminded"}
        assert s.due_keys(now + 99999) == []
        s._engine.dispose()


# -----------------------------------------------------------------------------
# ⚡ AsyncSQLAlchemyStore on aiosqlite
# -----------------------------------------------------------------------------
def _astore(tmp_path: Any, **kw: Any) -> Any:
    pytest.importorskip("aiosqlite")
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from src.xstate_statemachine.contrib.sqlalchemy import (
        AsyncSQLAlchemyStore,
    )

    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'a.db'}")
    s = AsyncSQLAlchemyStore(async_sessionmaker(eng), **kw)
    s._engine = eng  # type: ignore[attr-defined]
    return s


class TestAsyncStore:
    def test_contract(self, tmp_path: Any) -> None:
        async def go() -> None:
            s = _astore(tmp_path)
            try:
                blob = _store.snapshot_of(1)
                assert await s.load("k") is None
                assert await s.save("k", blob, expected_version=0) == 1
                with pytest.raises(ConflictError):
                    await s.save("k", blob, expected_version=0)
                d = Deadline("o.a", 1, 5.0, 5, "after.5.o.a")
                assert await s.save("k", blob, deadlines=[d]) == 2
                rec = await s.load("k")
                assert rec.snapshot == blob and rec.deadlines == (d,)
                assert await s.due_keys(10.0) == [("k", 5.0)]
                async with s.lock("k", timeout=1):
                    with pytest.raises(LockTimeoutError):
                        async with s.lock("k", timeout=0.05):
                            pass
                assert await s.list_keys(prefix="k") == ["k"]
                assert (await s.health())["ok"] is True
                assert (await s.forget("k"))["snapshots"] == 1
                assert await s.delete("k") is False
                with pytest.raises(InvalidKeyError):
                    await s.load("")
                with pytest.raises(TypeError):
                    await s.save("k", b"x")  # type: ignore[arg-type]
                with pytest.raises(ValueError):
                    await s.save("k", blob, expected_version=-1)
                with pytest.raises(ValueError):
                    await s.list_keys(limit=-1)
                with pytest.raises(ValueError):
                    s.lock("k", timeout=-1)
                s.max_snapshot_bytes = 16
                with pytest.raises(SnapshotTooLargeError):
                    await s.save("k", blob)
            finally:
                await s._engine.dispose()

        asyncio.run(go())

    def test_drives_async_interpreter_with_apersisted(self, tmp_path):
        async def go() -> int:
            s = _astore(tmp_path)
            try:
                m = _store.machine()
                for _ in range(3):
                    async with apersisted(s, "k", m) as i:
                        assert isinstance(i, Interpreter)
                        await i.send("GO", wait=True)
                async with apersisted(s, "k", m) as i:
                    return int(i.context["n"])
            finally:
                await s._engine.dispose()

        assert asyncio.run(go()) == 3

    def test_bad_args(self) -> None:
        from src.xstate_statemachine.contrib.sqlalchemy import (
            AsyncSQLAlchemyStore,
        )

        with pytest.raises(ValueError):
            AsyncSQLAlchemyStore(None, max_snapshot_bytes=0)
        with pytest.raises(ValueError):
            AsyncSQLAlchemyStore(None, lock_ttl_s=0)


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
    reason="set DATABASE_URL=postgresql+<driver>://... to run on Postgres",
)
def test_postgres_round_trip(tmp_path: Any) -> None:  # pragma: no cover
    s = make_store(tmp_path)
    blob = _store.snapshot_of(2)
    assert s.save("pg", blob, expected_version=0) == 1
    assert s.load("pg").snapshot == blob
    with pytest.raises(ConflictError):
        s.save("pg", blob, expected_version=0)
    s.forget("pg")
