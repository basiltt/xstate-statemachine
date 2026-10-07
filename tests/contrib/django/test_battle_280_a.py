# tests/contrib/django/test_battle_280_a.py
"""#280 battle, adversary A: locking, lock-error mapping, lock="none",
deleted rows, multi-DB, asend fan-in, SQL injection -- on SQLite and,
with ``DATABASE_URL=postgresql://...``, on a real Postgres."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, List

import pytest
from django.db import (
    OperationalError,
    connection,
    connections,
    transaction,
)

from xstate_statemachine.contrib.django import _locking, mixin
from xstate_statemachine.exceptions import ConflictError, LockTimeoutError

pytestmark = pytest.mark.django_db

PG = connection.vendor == "postgresql"
needs_pg = pytest.mark.skipif(not PG, reason="needs Postgres row locks")


class _PgError(Exception):
    def __init__(self, msg: str, sqlstate: str) -> None:
        super().__init__(msg)
        self.sqlstate = sqlstate


def _wrapped(msg: str, sqlstate: Any = None) -> OperationalError:
    exc = OperationalError(msg)
    if sqlstate is not None:
        exc.__cause__ = _PgError(msg, sqlstate)
    return exc


# -----------------------------------------------------------------------------
# 1. lock-error classification
# -----------------------------------------------------------------------------
class TestIsLockError:
    @pytest.mark.parametrize(
        "msg",
        [
            'relation "locked_orders" does not exist',
            "no such table: locked_orders",
            "column busy_flag does not exist",
        ],
    )
    def test_table_names_are_not_lock_errors(self, msg: str) -> None:
        assert not _locking._is_lock_error(OperationalError(msg))

    @pytest.mark.parametrize(
        "msg",
        [
            "database is locked",
            "database table is locked",
            "database is busy",
            "Lock wait timeout exceeded; try restarting transaction",
            "canceling statement due to lock timeout",
        ],
    )
    def test_driver_phrases_are_lock_errors(self, msg: str) -> None:
        assert _locking._is_lock_error(OperationalError(msg))

    @pytest.mark.parametrize("state", ["55P03", "40P01", "40001"])
    def test_sqlstate_is_trusted(self, state: str) -> None:
        assert _locking._is_lock_error(_wrapped("whatever text", state))

    def test_sqlstate_overrides_phrase(self) -> None:
        # 42P01 undefined_table, even though the text says "locked"
        assert not _locking._is_lock_error(
            _wrapped('relation "locked" does not exist', "42P01")
        )


# -----------------------------------------------------------------------------
# 2. optimistic: a row deleted mid-send is not a conflict
# -----------------------------------------------------------------------------
def test_optimistic_send_on_deleted_row_is_does_not_exist() -> None:
    from shop.models import Counter

    c = Counter.objects.create()
    Counter.objects.filter(pk=c.pk).delete()
    with pytest.raises(Counter.DoesNotExist):
        c.send("BUMP", lock="optimistic")
    with pytest.raises(Counter.DoesNotExist):
        mixin.send_with_retry(c, "BUMP", retries=3)
    with pytest.raises(Counter.DoesNotExist):
        c.send("BUMP", lock="pessimistic")


def test_optimistic_stale_is_still_a_conflict() -> None:
    from shop.models import Counter

    c = Counter.objects.create()
    Counter.objects.get(pk=c.pk).send("BUMP")
    with pytest.raises(ConflictError):
        c.send("BUMP", lock="optimistic")


# -----------------------------------------------------------------------------
# 3. lock="none": last writer wins, but the version never goes backwards
# -----------------------------------------------------------------------------
def test_lock_none_never_rolls_the_version_back() -> None:
    from shop.models import Counter

    c = Counter.objects.create()
    stale = Counter.objects.get(pk=c.pk)
    for _ in range(4):
        Counter.objects.get(pk=c.pk).send("BUMP")
    assert Counter.objects.get(pk=c.pk).statechart_version == 4
    stale.send("BUMP", lock="none")
    fresh = Counter.objects.get(pk=c.pk)
    # 📝 last-writer-wins on the snapshot (n=1, documented) ...
    assert fresh.machine.context["n"] == 1
    # ... but the fence moved FORWARD: an optimistic writer that read
    #    v2..v4 must still lose.
    assert fresh.statechart_version == 5
    assert stale.statechart_version == 5
    assert fresh.state == stale.state == "counter.on"


# -----------------------------------------------------------------------------
# 4. multi-DB: side rows land with the row
# -----------------------------------------------------------------------------
@pytest.mark.django_db(databases=["default", "other"])
@pytest.mark.skipif(PG, reason="the 'other' alias is SQLite-only")
def test_row_on_other_alias_keeps_deadlines_and_audit_there() -> None:
    from shop.models import Approval, Order
    from xstate_statemachine.contrib.django.models import (
        StatechartDeadline,
        TransitionLog,
    )

    o = Order.objects.using("other").create(title="x")
    o.send("SUBMIT")
    assert o._state.db == "other"
    a = Approval.objects.using("other").create()
    with transaction.atomic(using="default"):
        a.send("NOTE", payload={"text": "hi"})
    assert Order.objects.using("default").filter(pk=o.pk).count() == 0
    dl = StatechartDeadline.objects
    assert dl.using("default").count() == 0
    assert dl.using("other").count() >= 0
    assert TransitionLog.objects.using("default").count() == 0
    assert TransitionLog.objects.using("other").count() >= 1


# -----------------------------------------------------------------------------
# 5. asend fan-in
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_fifty_concurrent_asend_on_one_row() -> None:
    from shop.models import Counter

    c = Counter.objects.create()
    pk = c.pk

    rows = [Counter.objects.get(pk=pk) for _ in range(50)]

    async def main() -> List[Any]:
        from asgiref.sync import sync_to_async

        out = await asyncio.gather(*(r.asend("BUMP") for r in rows))
        # 📝 every asend ran on ONE thread-sensitive worker: it holds one
        #    connection (no request cycle closes it outside ASGI) ...
        opened = await sync_to_async(_open_aliases, thread_sensitive=True)()
        await sync_to_async(connections.close_all, thread_sensitive=True)()
        return [out, opened]

    t0 = time.monotonic()
    receipts, opened = asyncio.run(main())
    assert time.monotonic() - t0 < 60
    assert opened == ["default"]  # ... exactly one, no per-send leak
    assert all(r.changed for r in receipts)
    fresh = Counter.objects.get(pk=pk)
    assert fresh.machine.context["n"] == 50
    assert fresh.statechart_version == 50


def _open_aliases() -> List[str]:
    return [c.alias for c in connections.all() if c.connection is not None]


# -----------------------------------------------------------------------------
# 6. update_fields / bulk paths
# -----------------------------------------------------------------------------
def test_update_fields_title_only_keeps_state() -> None:
    from shop.models import Order

    o = Order.objects.create(title="a")
    stale = Order.objects.get(pk=o.pk)
    o.send("SUBMIT")
    stale.title = "b"
    stale.save(update_fields=["title"])
    fresh = Order.objects.get(pk=o.pk)
    assert fresh.title == "b"
    assert fresh.statechart_version == 1
    assert fresh.state == o.state


# -----------------------------------------------------------------------------
# 8. SQL injection / wildcard literals
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "sid", ["a'); DROP TABLE shop_order;--", "%", "_", "order.%", "o_der"]
)
def test_in_state_is_literal(sid: str) -> None:
    from shop.models import Order

    Order.objects.create()
    assert list(Order.objects.in_state(sid)) == []
    assert Order.objects.filter(statechart_state=sid).count() == 0
    assert Order.objects.count() == 1


# -----------------------------------------------------------------------------
# 1. Postgres: real lock_timeout and a real deadlock
# -----------------------------------------------------------------------------
@needs_pg
@pytest.mark.django_db(transaction=True)
def test_pg_lock_timeout_is_lock_timeout_error() -> None:
    from shop.models import Counter

    c = Counter.objects.create()
    held, release = threading.Event(), threading.Event()

    def holder() -> None:
        try:
            with transaction.atomic():
                Counter.objects.select_for_update().get(pk=c.pk)
                held.set()
                release.wait(30)
        finally:
            connections.close_all()

    t = threading.Thread(target=holder)
    t.start()
    try:
        assert held.wait(30)
        with connection.cursor() as cur:
            cur.execute("SET lock_timeout = '200ms'")
        with pytest.raises(LockTimeoutError) as ei:
            c.send("BUMP")
        assert ei.value.timeout == pytest.approx(0.2)
        with connection.cursor() as cur:
            cur.execute("SET lock_timeout = 0")
    finally:
        release.set()
        t.join(30)
    c.refresh_from_db()
    c.send("BUMP")
    assert Counter.objects.get(pk=c.pk).statechart_version == 1


@needs_pg
@pytest.mark.django_db(transaction=True)
def test_pg_deadlock_is_lock_timeout_and_retried() -> None:
    from shop.models import Counter

    a, b = Counter.objects.create(), Counter.objects.create()
    barrier = threading.Barrier(2)
    caught: List[BaseException] = []

    def tx(first: Any, second: Any) -> None:
        try:
            with transaction.atomic():
                type(first).objects.get(pk=first.pk).send("BUMP")
                barrier.wait(10)
                type(second).objects.get(pk=second.pk).send("BUMP")
        except BaseException as exc:  # noqa: BLE001
            caught.append(exc)
        finally:
            connections.close_all()

    ts = [
        threading.Thread(target=tx, args=(a, b)),
        threading.Thread(target=tx, args=(b, a)),
    ]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    # PG aborts exactly one of the two (40P01) -> retryable
    assert len(caught) == 1, caught
    assert isinstance(caught[0], LockTimeoutError), caught
    for row in (a, b):
        mixin.send_with_retry(row, "BUMP", lock="pessimistic")
    assert Counter.objects.get(pk=a.pk).machine.context["n"] == 2
    assert Counter.objects.get(pk=b.pk).machine.context["n"] == 2
