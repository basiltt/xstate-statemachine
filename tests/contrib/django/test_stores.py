# tests/contrib/django/test_stores.py
"""#280: `DjangoStore` extras and `DjangoModelStore` (the scanner's view)."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from xstate_statemachine.exceptions import ConflictError, MissingExtraError
from xstate_statemachine.persistence import Deadline, DueTimerScanner

pytestmark = pytest.mark.django_db


def test_store_due_keys_health_and_namespaces() -> None:
    from xstate_statemachine.contrib.django import DjangoStore

    a, b = DjangoStore("a"), DjangoStore("b")
    d = Deadline("o.a", 1, 100.0, 5, "after.5.o.a")
    a.save("k1", "{}", deadlines=[d])
    a.save("k2", "{}", deadlines=[Deadline("o.a", 1, 50.0, 5, "x")])
    b.save("k1", "{}")
    assert a.due_keys(120.0) == [("k2", 50.0), ("k1", 100.0)]
    assert a.due_keys(60.0) == [("k2", 50.0)]
    assert b.due_keys(1e12) == []
    assert a.list_keys() == ["k1", "k2"] and b.list_keys() == ["k1"]
    h = a.health()
    assert h["ok"] and h["backend"] == "django" and h["keys"] == 2
    with a.transaction():
        assert a.save("k1", "{}") == 2
    with pytest.raises(ValueError):
        DjangoStore("")
    with pytest.raises(ValueError):
        DjangoStore("x", lock_ttl_s=0)


def test_list_keys_prefix_is_case_sensitive() -> None:
    from xstate_statemachine.contrib.django import DjangoStore

    s = DjangoStore("cs")
    s.save("Order-1", "{}")
    s.save("order-2", "{}")
    s.save("a%b", "{}")
    assert s.list_keys(prefix="order-") == ["order-2"]
    assert s.list_keys(prefix="a%") == ["a%b"]
    assert s.list_keys(prefix="a_") == []


def test_model_store_round_trip_and_scanner(order: Any) -> None:
    from shop.models import Order

    from xstate_statemachine.contrib.django import DjangoModelStore

    order.send("SUBMIT")
    order.send("LEGAL_OK")
    order.send("FINANCE_OK")
    store = DjangoModelStore(Order)
    key = str(order.pk)
    rec = store.load(key)
    assert rec is not None and rec.version == 3 and rec.machine_version == "1"
    assert [d.event_type for d in rec.deadlines] == [
        "after.60000.order.approved"
    ]
    assert store.list_keys() == [key]
    assert store.load("999999") is None
    with pytest.raises(ConflictError):
        store.save(key, rec.snapshot, expected_version=1)
    with pytest.raises(ConflictError):
        store.save("999999", rec.snapshot)
    with pytest.raises(NotImplementedError):
        store.delete(key)
    # The stock scanner fires the matured deadline through this view.
    scanner = DueTimerScanner(
        store, lambda k: Order().statechart_machine_node()
    )
    assert scanner.run_once(now=time.time() + 3600) == 1
    fresh = Order.objects.get(pk=order.pk)
    assert fresh.state == "order.expired" and fresh.statechart_version == 4
    assert store.forget(key)["deadlines"] == 0
    assert store.forget("999999") == {"snapshots": 0, "deadlines": 0}
    with store.lock(key):
        pass


def test_model_store_saves_refresh_denormalised_columns(order: Any) -> None:
    from shop.models import Order

    from xstate_statemachine.contrib.django import DjangoModelStore

    store = DjangoModelStore(Order)
    rec = store.load(str(order.pk))
    snap = json.loads(rec.snapshot)
    snap["state_ids"] = ["order.cancelled"]
    snap["configuration"] = ["order", "order.cancelled"]
    assert store.save(str(order.pk), json.dumps(snap), expected_version=0) == 1
    assert Order.objects.get(pk=order.pk).state == "order.cancelled"


def test_lazy_package_surface() -> None:
    import xstate_statemachine.contrib.django as dj

    assert dj.StatechartField.__name__ == "StatechartField"
    assert "DjangoStore" in dj.__all__
    with pytest.raises(AttributeError):
        dj.nope  # noqa: B018
    assert issubclass(MissingExtraError, ImportError)
