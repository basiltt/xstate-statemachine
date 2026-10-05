# tests/contrib/django/test_battle_264_scanner.py
"""#264 battle (agent B): ``xsm_deadlines`` / `DjangoModelStore` under the
scanner -- exactly-once with 4 threads, and v1 rows woken by a v2 model
through its migrator (the #263 interplay)."""

from __future__ import annotations

import copy
import io
import json
import threading
import time
from pathlib import Path
from typing import Any, List

import pytest
from django.core.management import call_command
from django.db import connections

ORDER_JSON = (
    Path(__file__).resolve().parent / "project/shop/machines/order.json"
)


def _approved_orders(n: int) -> List[Any]:
    from shop.models import Order

    rows = []
    for _ in range(n):
        o = Order.objects.create(title="t")
        for ev in ("SUBMIT", "LEGAL_OK", "FINANCE_OK"):
            o.send(ev)
        rows.append(o)
    return rows


@pytest.mark.django_db(transaction=True)
def test_four_scanner_threads_fire_each_row_exactly_once() -> None:
    from shop.models import Order

    from xstate_statemachine.contrib.django.stores import DjangoModelStore
    from xstate_statemachine.persistence import DueTimerScanner

    rows = _approved_orders(20)
    before = {o.pk: o.statechart_version for o in rows}
    later = time.time() + 120
    results: List[Any] = []
    gate = threading.Barrier(4)

    def worker() -> None:
        try:
            sc = DueTimerScanner(
                DjangoModelStore(Order),
                lambda k: Order().statechart_machine_node(),
            )
            gate.wait(30)
            results.append(sc.scan(later))
        finally:
            connections.close_all()

    ts = [threading.Thread(target=worker) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    assert [e for r in results for e in r.errors] == []
    # 📝 One concurrent pass may leave a row for the NEXT tick: a scanner
    #    that read the due list before a peer's save still finds the row
    #    in flight (SQLite's `database is locked` → `LockTimeoutError` →
    #    `locked`, or the optimistic loser → `skipped_stale`) and the
    #    peer that won may have been counting a different row. The
    #    contract is "exactly once, and converges": drain with one more
    #    tick and assert the TOTAL -- never more than 20 (observed 19/20
    #    on the Coverage runner once).
    woken = sum(r.woken for r in results)
    assert woken <= 20
    if woken < 20:
        sc = DueTimerScanner(
            DjangoModelStore(Order),
            lambda k: Order().statechart_machine_node(),
        )
        woken += sc.scan(later).woken
    assert woken == 20
    for o in Order.objects.filter(pk__in=before):
        assert o.state == "order.expired"
        assert o.statechart_version == before[o.pk] + 1


@pytest.mark.django_db
def test_v1_rows_fire_under_a_v2_model_with_its_migrator(
    monkeypatch: Any,
) -> None:
    from shop.models import Order

    from xstate_statemachine.persistence import SnapshotMigrator

    (row,) = _approved_orders(1)
    v2 = copy.deepcopy(json.loads(ORDER_JSON.read_text("utf-8")))
    v2["version"] = "2"
    v2["context"] = {**v2.get("context", {}), "migrated": False}
    mig = SnapshotMigrator()
    mig.add(
        "1",
        "2",
        lambda b: {**b, "context": {**b["context"], "migrated": True}},
    )
    monkeypatch.setattr(Order, "statechart_machine", v2)
    monkeypatch.setattr(Order, "statechart_migrator", mig)
    monkeypatch.delattr(Order, "_xsm_machine_cache", raising=False)
    out = io.StringIO()
    call_command(
        "xsm_deadlines", "shop.Order", now=time.time() + 120, stdout=out
    )
    assert "shop.Order: woke 1/1" in out.getvalue(), out.getvalue()
    fresh = Order.objects.get(pk=row.pk)
    assert fresh.state == "order.expired"
    assert fresh.machine.context["migrated"] is True
