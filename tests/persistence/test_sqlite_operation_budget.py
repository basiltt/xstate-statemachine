"""🧪 Bound SQLite store operations by executed work, not runner latency.

One deadline per record exposes the historical missing ``deadlines_key``
index. Healthy indexed CRUD and a limited listing use a small, fixed number
of SQLite VM instructions; full scans at 2,000 rows exceed this allowance.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator

import pytest

from src.xstate_statemachine.persistence import (
    Deadline,
    SQLiteStore,
    StoreError,
)

_SNAPSHOT = '{"context":{"value":1}}'
_UPDATED_SNAPSHOT = '{"context":{"value":2}}'
_DEADLINE = Deadline("t.active", 1, 1e9, 1000, "after.1000.t.active")
_UPDATED_DEADLINE = Deadline("t.active", 2, 2e9, 1000, "after.1000.t.active")
_TEMP_KEY = "temporary-budget-probe"


@contextmanager
def sqlite_operation_budget(
    store: SQLiteStore, *, max_steps: int = 1000
) -> Iterator[Dict[str, int]]:
    """Measure real SQL instructions and abort excessive work immediately.

    The test owns this connection, which must have no existing progress
    handler. The budget is independent of record count, filesystem cost,
    coverage instrumentation and scheduling. A successful block must execute
    SQL, so an inactive probe cannot silently pass. An unrelated exception
    is preserved even when it occurs before the first SQL instruction.
    """
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    if not isinstance(store, SQLiteStore):
        raise TypeError("SQLite operation budget requires SQLiteStore")

    counts = {"sqlite_instructions": 0}
    steps = 0
    completed = False
    connection = store._conn()

    def progress() -> int:
        nonlocal steps
        steps += 1
        counts["sqlite_instructions"] = steps
        return int(steps > max_steps)

    connection.set_progress_handler(progress, 1)
    try:
        yield counts
        completed = True
    finally:
        # 🛡️ Restore first; SQLiteStore can wrap SQLITE_INTERRUPT, and a
        # caller can catch it. Neither may hide an exceeded work budget.
        connection.set_progress_handler(None, 0)
        counts["sqlite_instructions"] = steps
        assert (
            steps <= max_steps
        ), f"SQLite instruction budget exceeded: {steps} > {max_steps}"
        if completed:
            assert steps > 0, "SQLite budget observed no SQL instructions"


@pytest.fixture(params=["memory", "file"])
def store(
    request: pytest.FixtureRequest, tmp_path: Any
) -> Iterator[SQLiteStore]:
    """Exercise the same guard on in-memory and real WAL-backed stores."""
    target = ":memory:" if request.param == "memory" else tmp_path / "store.db"
    instance = SQLiteStore(target)
    try:
        yield instance
    finally:
        instance.close()


def _fill(store: SQLiteStore, size: int) -> str:
    for index in range(size):
        store.save(
            f"key-{index:06d}",
            _SNAPSHOT,
            machine_version="v1",
            deadlines=(_DEADLINE,),
        )
    return f"key-{size // 2:06d}"


def _operation(store: SQLiteStore, operation: str, key: str) -> Any:
    if operation == "save":
        return store.save(
            key,
            _UPDATED_SNAPSHOT,
            expected_version=1,
            machine_version="v2",
            deadlines=(_UPDATED_DEADLINE,),
        )
    if operation == "load":
        return store.load(key)
    if operation == "list10":
        return store.list_keys(limit=10)
    assert operation == "save+delete"
    version = store.save(
        _TEMP_KEY, _SNAPSHOT, expected_version=0, deadlines=(_DEADLINE,)
    )
    return version, store.delete(_TEMP_KEY)


def _long_query(connection: sqlite3.Connection) -> int:
    """A bounded query that exceeds the operation budget if still installed."""
    row = connection.execute(
        "WITH RECURSIVE numbers(n) AS "
        "(SELECT 1 UNION ALL SELECT n + 1 FROM numbers WHERE n < 500) "
        "SELECT SUM(n) FROM numbers"
    ).fetchone()
    return int(row[0])


def _assert_handler_removed(
    store: SQLiteStore, counts: Dict[str, int]
) -> None:
    before = counts.copy()
    assert _long_query(store._conn()) == 125_250
    assert counts == before


@pytest.mark.parametrize("size", [1, 100, 2000])
@pytest.mark.parametrize(
    "operation", ["save", "load", "list10", "save+delete"]
)
def test_budget_preserves_store_results_at_all_sizes(
    store: SQLiteStore, size: int, operation: str
) -> None:
    key = _fill(store, size)
    with sqlite_operation_budget(store) as counts:
        result = _operation(store, operation, key)
    assert 0 < counts["sqlite_instructions"] <= 1000
    if operation == "save":
        assert result == 2
    elif operation == "load":
        assert result.key == key and result.version == 1
        assert result.snapshot == _SNAPSHOT
        assert result.deadlines == (_DEADLINE,)
    elif operation == "list10":
        assert result == [f"key-{index:06d}" for index in range(min(10, size))]
    else:
        assert result == (1, True)
    record = store.load(key)
    assert record is not None
    assert record.version == (2 if operation == "save" else 1)
    assert record.snapshot == (
        _UPDATED_SNAPSHOT if operation == "save" else _SNAPSHOT
    )
    assert record.machine_version == ("v2" if operation == "save" else "v1")
    expected = _UPDATED_DEADLINE if operation == "save" else _DEADLINE
    assert record.deadlines == (expected,)
    assert store.load(_TEMP_KEY) is None
    connection = store._conn()
    for table in ("statecharts", "deadlines"):
        assert (
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            == size
        )
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM deadlines WHERE key = ?", (_TEMP_KEY,)
        ).fetchone()[0]
        == 0
    )
    _assert_handler_removed(store, counts)


@pytest.mark.parametrize("operation", ["save", "load", "save+delete"])
def test_budget_rejects_the_missing_deadline_index(
    store: SQLiteStore, operation: str
) -> None:
    key = _fill(store, 2000)
    store._conn().execute("DROP INDEX deadlines_key")
    with pytest.raises(
        AssertionError, match="SQLite instruction budget exceeded"
    ):
        with sqlite_operation_budget(store) as counts:
            _operation(store, operation, key)
    assert counts["sqlite_instructions"] > 1000
    assert not store._conn().in_transaction
    assert store.load(key).version == 1
    assert store.load(_TEMP_KEY) is None
    _assert_handler_removed(store, counts)


def test_budget_rejects_materializing_all_keys_before_slicing(
    store: SQLiteStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fill(store, 2000)

    def unbounded_list(prefix: str, limit: int) -> Any:
        rows = (
            store._conn()
            .execute(
                "SELECT key FROM statecharts WHERE substr(key, 1, ?) = ? "
                "ORDER BY key",
                (len(prefix), prefix),
            )
            .fetchall()
        )
        return [row[0] for row in rows][:limit]

    monkeypatch.setattr(store, "_list_keys_raw", unbounded_list)
    # 📝 The mutation returns exactly the right answer; the work guard,
    # rather than a changed result, must expose the full-store scan.
    assert store.list_keys(limit=10) == [
        f"key-{index:06d}" for index in range(10)
    ]
    with pytest.raises(
        AssertionError, match="SQLite instruction budget exceeded"
    ):
        with sqlite_operation_budget(store) as counts:
            store.list_keys(limit=10)
    assert counts["sqlite_instructions"] > 1000
    _assert_handler_removed(store, counts)


@pytest.mark.parametrize("handling", ["raw", "wrapped", "swallowed"])
def test_interrupt_cannot_hide_excess_work(
    store: SQLiteStore, handling: str
) -> None:
    with pytest.raises(
        AssertionError, match="SQLite instruction budget exceeded"
    ):
        with sqlite_operation_budget(store, max_steps=20) as counts:
            try:
                _long_query(store._conn())
            except sqlite3.OperationalError as error:
                if handling == "raw":
                    raise
                if handling == "wrapped":
                    raise StoreError("wrapped interruption") from error
                # Even modifying the exposed report cannot hide the private
                # count after a caller swallows SQLITE_INTERRUPT.
                counts["sqlite_instructions"] = 0
    assert counts["sqlite_instructions"] > 20
    _assert_handler_removed(store, counts)


@pytest.mark.parametrize("execute_sql", [False, True])
def test_unrelated_exception_is_preserved_and_handler_removed(
    store: SQLiteStore, execute_sql: bool
) -> None:
    with pytest.raises(RuntimeError, match="caller failed"):
        with sqlite_operation_budget(store) as counts:
            if execute_sql:
                assert store._conn().execute("SELECT 1").fetchone()[0] == 1
            raise RuntimeError("caller failed")
    assert (counts["sqlite_instructions"] > 0) is execute_sql
    _assert_handler_removed(store, counts)


def test_sql_error_is_preserved_and_handler_removed(
    store: SQLiteStore,
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        with sqlite_operation_budget(store) as counts:
            store._conn().execute("SELECT * FROM missing_table")
    _assert_handler_removed(store, counts)


@pytest.mark.parametrize("disable_handler", [False, True])
def test_empty_or_inactive_probe_cannot_pass(
    store: SQLiteStore, disable_handler: bool
) -> None:
    with pytest.raises(AssertionError, match="observed no SQL instructions"):
        with sqlite_operation_budget(store) as counts:
            if disable_handler:
                store._conn().set_progress_handler(None, 0)
                assert store._conn().execute("SELECT 1").fetchone()[0] == 1
    assert counts == {"sqlite_instructions": 0}
    _assert_handler_removed(store, counts)


@pytest.mark.parametrize("max_steps", [0, -1, True, 1.5])
def test_budget_rejects_invalid_allowance(
    store: SQLiteStore, max_steps: Any
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        with sqlite_operation_budget(store, max_steps=max_steps):
            pytest.fail("invalid budget reached the measured block")


def test_budget_rejects_other_backends() -> None:
    with pytest.raises(TypeError, match="requires SQLiteStore"):
        with sqlite_operation_budget(object()):  # type: ignore[arg-type]
            pytest.fail("unsupported backend reached the measured block")
