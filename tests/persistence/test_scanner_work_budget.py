"""🧪 Deterministic work budgets for the sparse deadline-scanner scale test.

The 100k-record fixture has one deadline per record and only 100 due keys.
Count metadata reads / SQL instructions instead of elapsed time, which also
includes coverage overhead and scheduling delays on shared CI runners.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Union

import pytest

from src.xstate_statemachine.persistence import (
    Deadline,
    DueTimerScanner,
    MemoryStore,
    SQLiteStore,
    StoreError,
)

_Store = Union[MemoryStore, SQLiteStore]
_MISSING = object()
_RECORDS = 200


@contextmanager
def deadline_scan_budget(
    store: _Store,
    monkeypatch: pytest.MonkeyPatch,
    *,
    records: int,
) -> Iterator[Dict[str, int]]:
    """Bound a sparse scan's work and remove instrumentation on every exit.

    MemoryStore may read each stored deadline once (a future index may need
    fewer reads). SQLite may perform a linear metadata scan; this does not
    require a particular query plan. Its instruction allowance has a fixed
    floor for query setup on small fixtures. The SQLite connection belongs
    to the test and must not already have a progress handler installed.

    Args:
        store: Store whose deadline metadata is being scanned.
        monkeypatch: Test-scoped patch manager for the MemoryStore probe.
        records: Number of records, each with one stored deadline.

    Yields:
        Mutable counters for the work performed inside the context.

    Raises:
        AssertionError: The scan exceeds its deterministic work allowance.
    """
    if records < 0:
        raise ValueError("records must be non-negative")

    if isinstance(store, MemoryStore):
        counts = {"deadline_reads": 0}
        with store._guard:
            tracked = {
                id(deadline)
                for record in store._records.values()
                for deadline in record.deadlines
            }

        def read_due_at(deadline: Deadline) -> float:
            # 🛡️ Other stores/background tasks must not consume this budget.
            if id(deadline) in tracked:
                counts["deadline_reads"] += 1
                assert counts["deadline_reads"] <= records, (
                    "deadline metadata read budget exceeded: "
                    f"{counts['deadline_reads']} > {records}"
                )
            return deadline.__dict__["due_at_wall"]

        def write_due_at(deadline: Deadline, value: float) -> None:
            # 📝 Preserve dataclass construction while the probe is active.
            deadline.__dict__["due_at_wall"] = value

        try:
            with monkeypatch.context() as patch:
                patch.setattr(
                    Deadline,
                    "due_at_wall",
                    property(read_due_at, write_due_at),
                    raising=False,
                )
                yield counts
        finally:
            # 🛡️ A caller cannot hide excess work by catching the probe.
            #    Restore the descriptor before reporting a violation.
            assert counts["deadline_reads"] <= records, (
                "deadline metadata read budget exceeded: "
                f"{counts['deadline_reads']} > {records}"
            )
        return

    if not isinstance(store, SQLiteStore):
        raise TypeError(
            "deadline scan budget requires MemoryStore/SQLiteStore"
        )

    counts = {"sqlite_instructions": 0}
    allowance = max(1_000, records * 20)
    interval = 100

    def progress() -> int:
        counts["sqlite_instructions"] += interval
        return int(counts["sqlite_instructions"] > allowance)

    connection = store._conn()
    connection.set_progress_handler(progress, interval)
    try:
        yield counts
    finally:
        # 🛡️ SQLiteStore may wrap SQLITE_INTERRUPT in a typed store error.
        #    Clear the callback before reporting the actual budget failure.
        connection.set_progress_handler(None, 0)
        assert counts["sqlite_instructions"] <= allowance, (
            "SQLite instruction budget exceeded: "
            f"{counts['sqlite_instructions']} > {allowance}"
        )


@pytest.fixture(params=["memory", "sqlite"])
def budget_store(request: pytest.FixtureRequest) -> Iterator[_Store]:
    """Seed a small equivalent of the 100k/100-due scale fixture."""
    store = (
        MemoryStore() if request.param == "memory" else SQLiteStore(":memory:")
    )
    due = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
    late = Deadline("t.w", 1, 1e12, 1000, "after.1000.t.w")
    try:
        for index in range(_RECORDS):
            store.save(
                f"t{index:04d}",
                "{}",
                deadlines=(due if index % 100 == 0 else late,),
            )
        yield store
    finally:
        if isinstance(store, SQLiteStore):
            store.close()


def _expensive_sql(store: SQLiteStore) -> int:
    """Exercise quadratic work cheaply on the small fixture."""
    row = (
        store._conn()
        .execute(
            "SELECT COUNT(*) FROM deadlines AS a CROSS JOIN deadlines AS b"
        )
        .fetchone()
    )
    return int(row[0])


def _assert_restored(
    store: _Store, counts: Dict[str, int], original: Any
) -> None:
    """The original descriptor/callback state survives every context exit."""
    before = counts.copy()
    assert vars(Deadline).get("due_at_wall", _MISSING) is original
    if isinstance(store, SQLiteStore):
        assert _expensive_sql(store) == _RECORDS**2
    else:
        assert DueTimerScanner(store, lambda key: None).due_keys(10.0) == [
            ("t0000", 1.0),
            ("t0100", 1.0),
        ]
    assert counts == before


def test_budget_preserves_results_and_restores_state(
    budget_store: _Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = vars(Deadline).get("due_at_wall", _MISSING)
    scanner = DueTimerScanner(budget_store, lambda key: None)
    with deadline_scan_budget(
        budget_store, monkeypatch, records=_RECORDS
    ) as counts:
        assert scanner.due_keys(10.0) == [("t0000", 1.0), ("t0100", 1.0)]
    assert next(iter(counts.values())) > 0
    _assert_restored(budget_store, counts, original)


def test_memory_budget_rejects_repeated_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    deadline = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
    store.save("t", "{}", deadlines=(deadline,))
    scanner = DueTimerScanner(store, lambda key: None)
    original = vars(Deadline).get("due_at_wall", _MISSING)
    with pytest.raises(AssertionError, match="metadata read budget exceeded"):
        with deadline_scan_budget(store, monkeypatch, records=1) as counts:
            assert scanner.due_keys(10.0) == [("t", 1.0)]
            scanner.due_keys(10.0)
    assert counts == {"deadline_reads": 2}
    assert vars(Deadline).get("due_at_wall", _MISSING) is original
    assert scanner.due_keys(10.0) == [("t", 1.0)]
    assert counts == {"deadline_reads": 2}


def test_memory_budget_preserves_construction_and_existing_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    tracked = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
    store.save("t", "{}", deadlines=(tracked,))
    original = property(lambda deadline: deadline.__dict__["due_at_wall"])
    monkeypatch.setattr(Deadline, "due_at_wall", original, raising=False)
    with deadline_scan_budget(store, monkeypatch, records=1) as counts:
        deadline = Deadline("t.w", 1, 3.5, 1000, "after.1000.t.w")
        assert deadline.due_at_wall == 3.5
        assert tracked.due_at_wall == 1.0
    assert vars(Deadline)["due_at_wall"] is original
    assert deadline.due_at_wall == 3.5
    assert counts == {"deadline_reads": 1}


def test_memory_budget_rejects_swallowed_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    deadline = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
    store.save("t", "{}", deadlines=(deadline,))
    scanner = DueTimerScanner(store, lambda key: None)
    original = vars(Deadline).get("due_at_wall", _MISSING)
    with pytest.raises(AssertionError, match="metadata read budget exceeded"):
        with deadline_scan_budget(store, monkeypatch, records=1) as counts:
            due = scanner.due_keys(10.0)
            with pytest.raises(AssertionError):
                scanner.due_keys(10.0)
            assert due == [("t", 1.0)]
    assert vars(Deadline).get("due_at_wall", _MISSING) is original
    assert scanner.due_keys(10.0) == [("t", 1.0)]
    assert counts == {"deadline_reads": 2}


def test_memory_budget_ignores_unrelated_deadline_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryStore()
    tracked = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
    unrelated = Deadline("t.w", 2, 9.0, 1000, "after.1000.t.w")
    store.save("t", "{}", deadlines=(tracked,))
    with deadline_scan_budget(store, monkeypatch, records=1) as counts:
        for _ in range(10):
            assert unrelated.due_at_wall == 9.0
        assert counts == {"deadline_reads": 0}
        assert DueTimerScanner(store, lambda key: None).due_keys(10.0) == [
            ("t", 1.0)
        ]
        assert counts == {"deadline_reads": 1}


def test_budget_restores_state_after_query_exception(
    budget_store: _Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = vars(Deadline).get("due_at_wall", _MISSING)
    with pytest.raises(RuntimeError, match="query failed"):
        with deadline_scan_budget(
            budget_store, monkeypatch, records=_RECORDS
        ) as counts:
            DueTimerScanner(budget_store, lambda key: None).due_keys(10.0)
            raise RuntimeError("query failed")
    _assert_restored(budget_store, counts, original)


@pytest.mark.parametrize("wrap_error", [False, True])
def test_sqlite_budget_aborts_excess_work_and_restores_callback(
    monkeypatch: pytest.MonkeyPatch, wrap_error: bool
) -> None:
    store = SQLiteStore(":memory:")
    original = vars(Deadline).get("due_at_wall", _MISSING)
    try:
        deadline = Deadline("t.w", 1, 1.0, 1000, "after.1000.t.w")
        for index in range(_RECORDS):
            store.save(str(index), "{}", deadlines=(deadline,))
        with pytest.raises(AssertionError, match="SQLite instruction budget"):
            with deadline_scan_budget(
                store, monkeypatch, records=_RECORDS
            ) as counts:
                try:
                    _expensive_sql(store)
                except sqlite3.OperationalError as exc:
                    if wrap_error:
                        raise StoreError(
                            "wrapped SQLite interruption"
                        ) from exc
                    raise
        assert counts == {"sqlite_instructions": _RECORDS * 20 + 100}
        _assert_restored(store, counts, original)
    finally:
        store.close()


def test_sqlite_query_error_is_preserved_and_callback_is_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteStore(":memory:")
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            with deadline_scan_budget(store, monkeypatch, records=0) as counts:
                store._conn().execute("SELECT * FROM missing_table")
        before = counts.copy()
        row = (
            store._conn()
            .execute(
                "WITH RECURSIVE numbers(n) AS "
                "(SELECT 1 UNION ALL SELECT n + 1 FROM numbers WHERE n < 200) "
                "SELECT SUM(n) FROM numbers"
            )
            .fetchone()
        )
        assert row[0] == 20_100
        assert counts == before
    finally:
        store.close()
