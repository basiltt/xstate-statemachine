# tests/contrib/django/test_model.py
"""#280: `StatechartField`, `StatechartModelMixin`, lookups, locking."""

from __future__ import annotations

import json
import threading
from typing import Any, List

import pytest
from django.core.management import call_command
from django.db import connection, connections, transaction

from xstate_statemachine.contrib.django.fields import StatechartField
from xstate_statemachine.exceptions import ConflictError, SnapshotTooLargeError

pytestmark = pytest.mark.django_db


def _order():
    from shop.models import Order

    return Order


class TestFieldAndMigrations:
    def test_siblings_are_real_fields(self) -> None:
        names = {f.name for f in _order()._meta.get_fields()}
        assert {
            "statechart",
            "statechart_state",
            "statechart_state_ids",
            "statechart_version",
            "statechart_machine_version",
        } <= names
        f = _order()._meta.get_field("statechart_state")
        assert f.db_index is True

    def test_makemigrations_is_stable(self) -> None:
        # A second run finds nothing: the shipped migrations list the
        # siblings and the field does not add them twice (X0.10).
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)

    def test_deconstruct_round_trips(self) -> None:
        f = StatechartField(max_snapshot_bytes=1000, state_max_length=64)
        name, path, args, kw = f.deconstruct()
        assert path.endswith("fields.StatechartField")
        assert kw == {"max_snapshot_bytes": 1000, "state_max_length": 64}
        g = StatechartField(*args, **kw)
        assert g.deconstruct()[3] == kw
        assert StatechartField().deconstruct()[3] == {}
        with pytest.raises(ValueError):
            StatechartField(max_snapshot_bytes=0)

    def test_size_cap_on_write(self, order: Any) -> None:
        f = _order()._meta.get_field("statechart")
        old = f.max_snapshot_bytes
        f.max_snapshot_bytes = 64
        try:
            with pytest.raises(SnapshotTooLargeError):
                order.send("INC")
        finally:
            f.max_snapshot_bytes = old

    def test_size_cap_on_read(self, order: Any) -> None:
        f = _order()._meta.get_field("statechart")
        f.max_snapshot_bytes = 64
        try:
            with pytest.raises(SnapshotTooLargeError):
                _order().objects.get(pk=order.pk)
        finally:
            f.max_snapshot_bytes = 1024 * 1024

    def test_non_dict_rejected(self) -> None:
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            _order().objects.create(statechart=[1, 2])


class TestMixin:
    def test_create_initialises_snapshot(self, order: Any) -> None:
        assert order.state == "order.draft"
        assert order.state_ids == ["order.draft"]
        assert order.statechart["machine_version"] == "1"
        assert order.statechart_machine_version == "1"
        assert order.statechart_version == 0
        assert order.available_events == ["CANCEL", "INC", "SUBMIT"]
        assert order.can("SUBMIT") and not order.can("PAY")

    def test_send_persists_and_returns_receipt(self, order: Any) -> None:
        r = order.send("SUBMIT")
        assert r.changed and not r.denied
        assert order.matches("order.review")
        assert (
            order.state
            == "order.review.finance.pending,order.review.legal.pending"
        )
        fresh = _order().objects.get(pk=order.pk)
        assert fresh.state_ids == [
            "order.review.finance.pending",
            "order.review.legal.pending",
        ]
        assert fresh.statechart_version == 1
        assert fresh.available_events == ["FINANCE_OK", "LEGAL_OK", "RESET"]

    def test_parallel_done_and_guard(self, order: Any) -> None:
        order.send("SUBMIT")
        order.send("LEGAL_OK")
        order.send("FINANCE_OK")
        assert order.state == "order.approved"
        r = order.send("PAY", amount=0)
        assert r.denied and not r.changed
        r = order.send("PAY", amount=5)
        assert r.changed and order.state == "order.paid"
        assert order.machine.context["total"] == 5

    def test_lookups(self, order: Any) -> None:
        Order = _order()
        other = Order.objects.create()
        order.send("SUBMIT")
        assert list(Order.objects.filter(statechart__state="order.draft")) == [
            other
        ]
        assert set(
            Order.objects.filter(
                statechart__state__in=["order.draft", "x"]
            ).values_list("pk", flat=True)
        ) == {other.pk}
        assert list(Order.objects.in_state("order.review")) == [order]
        assert list(Order.objects.in_state("order.review.legal.pending")) == [
            order
        ]
        assert set(Order.objects.in_state("order.draft", "order.review")) == {
            order,
            other,
        }
        # A prefix that is not a whole id segment does not match.
        assert list(Order.objects.in_state("order.rev")) == []
        assert list(Order.objects.in_state("order.draf")) == []
        with pytest.raises(ValueError):
            Order.objects.in_state()

    def test_in_state_is_injection_safe(self, order: Any) -> None:
        Order = _order()
        evil = "a'); DROP TABLE shop_order;--"
        assert list(Order.objects.in_state(evil)) == []
        assert list(Order.objects.filter(statechart__state=evil)) == []
        assert Order.objects.count() == 1  # the table is still there

    def test_plain_save_does_not_roll_state_back(self, order: Any) -> None:
        stale = _order().objects.get(pk=order.pk)
        order.send("SUBMIT")
        stale.title = "renamed"
        stale.save()
        fresh = _order().objects.get(pk=order.pk)
        assert fresh.title == "renamed"
        assert fresh.matches("order.review")

    def test_unsaved_row_is_saved_on_send(self) -> None:
        o = _order()(title="new")
        o.send("SUBMIT")
        assert o.pk is not None and o.matches("order.review")

    def test_bad_lock_mode(self, order: Any) -> None:
        with pytest.raises(ValueError):
            order.send("SUBMIT", lock="bogus")

    def test_optimistic_conflict_and_retry(self, order: Any) -> None:
        from xstate_statemachine.contrib.django.mixin import send_with_retry

        a = _order().objects.get(pk=order.pk)
        b = _order().objects.get(pk=order.pk)
        a.send("INC", lock="optimistic")
        with pytest.raises(ConflictError) as ei:
            b.send("INC", lock="optimistic")
        assert ei.value.expected == 0 and ei.value.actual == 1
        r = send_with_retry(b, "INC")
        assert r.changed
        assert b.machine.context["count"] == 2  # nothing lost

    def test_retry_exhaustion_reports_attempts(self, order: Any) -> None:
        from xstate_statemachine.contrib.django.mixin import send_with_retry

        stale = _order().objects.get(pk=order.pk)

        def always_conflict(*a: Any, **k: Any) -> Any:
            raise ConflictError("k", 0, 1)

        stale.send = always_conflict  # type: ignore[method-assign]
        with pytest.raises(ConflictError) as ei:
            send_with_retry(stale, "INC", retries=2)
        assert ei.value.attempts == 3
        with pytest.raises(ValueError):
            send_with_retry(stale, "INC", retries=-1)

    def test_lock_none_is_last_writer_wins(self, order: Any) -> None:
        stale = _order().objects.get(pk=order.pk)
        order.send("INC")
        stale.send("INC", lock="none")  # no conflict: overwrote
        assert _order().objects.get(pk=order.pk).machine.context["count"] == 1

    def test_rollback_leaves_nothing(self, order: Any) -> None:
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                order.send("SUBMIT")
                raise RuntimeError("boom")
        assert _order().objects.get(pk=order.pk).state == "order.draft"

    def test_machine_version_mismatch_and_migrator(self, order: Any) -> None:
        from xstate_statemachine.exceptions import SnapshotDriftError
        from xstate_statemachine.persistence import SnapshotMigrator

        Order = _order()
        snap = dict(order.statechart)
        snap["machine_version"] = "0"
        Order.objects.filter(pk=order.pk).update(statechart=snap)
        o = Order.objects.get(pk=order.pk)
        with pytest.raises(SnapshotDriftError):
            o.send("SUBMIT")
        mig = SnapshotMigrator()
        mig.register("0", "1")(lambda s: s)
        Order.statechart_migrator = mig
        try:
            assert o.send("SUBMIT").changed
        finally:
            Order.statechart_migrator = None

    def test_forget(self, order: Any) -> None:
        order.send("SUBMIT")
        order.send("LEGAL_OK")
        order.send("FINANCE_OK")  # approved: one deadline row
        counts = order.forget_statechart()
        assert counts["snapshots"] == 1 and counts["deadlines"] == 1
        fresh = _order().objects.get(pk=order.pk)
        assert fresh.statechart is None and fresh.state is None

    def test_resolve_machine_errors(self) -> None:
        from xstate_statemachine.contrib.django._machine import (
            import_string,
            resolve_machine,
        )

        with pytest.raises(TypeError):
            resolve_machine(None)
        with pytest.raises(TypeError):
            resolve_machine(42)
        with pytest.raises(FileNotFoundError):
            resolve_machine("nope/missing.json")
        assert import_string("json:dumps") is json.dumps
        assert import_string("json.dumps") is json.dumps


class TestDeadlines:
    def test_deadline_row_created_and_cleared(self, order: Any) -> None:
        from xstate_statemachine.contrib.django.models import (
            StatechartDeadline,
        )

        rows = StatechartDeadline.objects.filter(source="shop_order")
        order.send("SUBMIT")
        order.send("LEGAL_OK")
        order.send("FINANCE_OK")
        assert list(rows.values_list("key", "event_type")) == [
            (str(order.pk), "after.60000.order.approved")
        ]
        order.send("INC")  # a self-transition keeps the timer
        assert rows.count() == 1
        order.send("PAY", amount=1)  # leaves `approved`: cleared
        assert rows.count() == 0

    def test_xsm_deadlines_fires_a_matured_timer(self, order: Any) -> None:
        import io
        import time

        order.send("SUBMIT")
        order.send("LEGAL_OK")
        order.send("FINANCE_OK")
        out = io.StringIO()
        call_command("xsm_deadlines", "shop.Order", stdout=out)
        assert "woke 0/0" in out.getvalue()  # not due yet
        call_command(
            "xsm_deadlines", "shop.Order", now=time.time() + 120, stdout=out
        )
        assert "shop.Order: woke 1/1" in out.getvalue()
        fresh = _order().objects.get(pk=order.pk)
        assert fresh.state == "order.expired"
        assert fresh.statechart_version == 4
        from xstate_statemachine.contrib.django.models import (
            StatechartDeadline,
        )

        assert not StatechartDeadline.objects.filter(
            key=str(order.pk)
        ).exists()

    def test_xsm_deadlines_every_model_and_bad_label(self) -> None:
        import io

        from django.core.management.base import CommandError

        out = io.StringIO()
        call_command("xsm_deadlines", stdout=out)
        assert (
            "shop.Order" in out.getvalue()
            and "total woken: 0" in out.getvalue()
        )
        with pytest.raises(CommandError):
            call_command("xsm_deadlines", "nope.Nope")
        with pytest.raises(CommandError):
            call_command("xsm_deadlines", "xsm_django.StatechartLock")


class TestRefreshHelper:
    def test_refresh_columns_after_direct_write(self, order: Any) -> None:
        from xstate_statemachine.contrib.django.migration_helpers import (
            refresh_statechart_columns,
        )

        Order = _order()
        snap = dict(order.statechart)
        snap["state_ids"] = ["order.cancelled"]
        snap["configuration"] = ["order", "order.cancelled"]
        Order.objects.filter(pk=order.pk).update(statechart=snap)
        assert Order.objects.get(pk=order.pk).state == "order.draft"  # stale
        assert refresh_statechart_columns(Order, batch=1) == 1
        assert Order.objects.get(pk=order.pk).state == "order.cancelled"

    def test_refresh_with_migrate_bumps_version(self, order: Any) -> None:
        from xstate_statemachine.contrib.django.migration_helpers import (
            refresh_statechart_columns,
            refresh_statechart_columns_op,
        )

        def rename(s: dict) -> dict:
            s["state_ids"] = ["order.cancelled"]
            return s

        refresh_statechart_columns(_order(), migrate=rename)
        fresh = _order().objects.get(pk=order.pk)
        assert fresh.state == "order.cancelled"
        assert fresh.statechart_version == 1
        with pytest.raises(ValueError):
            refresh_statechart_columns(_order(), batch=0)
        assert refresh_statechart_columns_op("shop", "Order") is not None


# -----------------------------------------------------------------------------
# 🧵 Concurrency: 16 threads x 100 sends on one row
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
class TestConcurrency:
    THREADS = 16
    PER_THREAD = 100

    def _hammer(self, pk: Any, fn: Any) -> List[BaseException]:
        errors: List[BaseException] = []

        def worker() -> None:
            from shop.models import Counter

            try:
                for _ in range(self.PER_THREAD):
                    fn(Counter.objects.get(pk=pk))
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connections.close_all()

        ts = [threading.Thread(target=worker) for _ in range(self.THREADS)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(600)
        return errors

    def test_pessimistic_exactly_1600(self) -> None:
        from shop.models import Counter

        c = Counter.objects.create()
        errors = self._hammer(c.pk, lambda row: row.send("BUMP"))
        assert errors == []
        fresh = Counter.objects.get(pk=c.pk)
        total = self.THREADS * self.PER_THREAD
        assert fresh.machine.context["n"] == total
        assert fresh.statechart_version == total

    def test_optimistic_with_retry_exactly_1600(self) -> None:
        from shop.models import Counter
        from xstate_statemachine.contrib.django.mixin import send_with_retry

        c = Counter.objects.create()
        errors = self._hammer(
            c.pk, lambda row: send_with_retry(row, "BUMP", retries=10_000)
        )
        assert errors == []
        fresh = Counter.objects.get(pk=c.pk)
        assert fresh.machine.context["n"] == self.THREADS * self.PER_THREAD


@pytest.mark.django_db(transaction=True)
def test_asend_runs_the_locked_section_off_the_loop() -> None:
    """Async views: the whole locked section is one sync_to_async call."""
    import asyncio

    from shop.models import Order

    o = Order.objects.create()
    r = asyncio.run(o.asend("SUBMIT"))
    assert r.changed
    connections.close_all()
    assert Order.objects.get(pk=o.pk).matches("order.review")


def test_vendor_is_sqlite_unless_database_url() -> None:
    import os

    if os.environ.get("DATABASE_URL"):
        assert connection.vendor == "postgresql"
    else:
        assert connection.vendor == "sqlite"
