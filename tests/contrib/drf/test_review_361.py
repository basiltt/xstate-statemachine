# tests/contrib/drf/test_review_361.py
"""#361 review fixes on the web surfaces: H1 (clients cannot set send()'s
own options), H2 (actor_id cannot be forged), M3 (the inbox follows the
row's database), M4 (stream/ re-checks access)."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice(db: Any) -> Any:
    U = get_user_model()
    u = U.objects.create_user("alice", password="p")
    u.user_permissions.add(Permission.objects.get(codename="view_order"))
    return U.objects.get(pk=u.pk)


def _client(u: Any) -> APIClient:
    c = APIClient()
    c.force_authenticate(u)
    return c


@pytest.mark.parametrize(
    "key,value",
    [
        ("lock", "none"),
        ("using", "other"),
        ("plugins", []),
        ("actor", 1),
        ("actor_id", 999),
        ("reason", "forged"),
        ("wait", False),
        ("idempotency_key", "k"),
        ("payload", {}),
    ],
)
def test_reserved_keys_are_422_on_every_route(alice, key, value) -> None:
    from shop.models import Order

    o = Order.objects.create()
    c = _client(alice)
    for url, body in (
        (f"/api/orders/{o.pk}/inc/", {key: value}),
        (f"/api/orders/{o.pk}/send/", {"type": "INC", key: value}),
    ):
        r = c.post(url, body, format="json")
        assert r.status_code == 422, (url, r.content)
        assert r.json()["error"] == "ReservedKeyError"
        assert r.json()["keys"] == [key]
    o.refresh_from_db()
    assert o.statechart_version == 0  # nothing ran


def test_model_send_takes_data_as_a_mapping(db) -> None:
    """H1 at the source: data given as payload= cannot become an option."""
    from shop.models import Order

    o = Order.objects.create()
    r = o.send("INC", payload={"lock": "none", "using": "nowhere"})
    assert r.changed
    assert o.machine.context["count"] == 1


def test_actor_id_is_always_the_real_actor(db, alice) -> None:
    """H2: a caller-supplied actor_id never survives."""
    from shop.models import Order

    seen = {}

    from xstate_statemachine.contrib.django.signals import post_transition

    def rec(sender: Any, **kw: Any) -> None:
        seen["actor_id"] = kw["event"].payload.get("actor_id")

    post_transition.connect(rec, weak=False)
    try:
        o = Order.objects.create()
        o.send("INC", actor=alice, payload={"actor_id": 999})
        assert seen["actor_id"] == alice.pk
        o.send("INC", actor_id=999)  # no actor: the forged id is dropped
        assert seen["actor_id"] is None
    finally:
        post_transition.disconnect(rec)


@pytest.mark.django_db(databases=["default", "other"])
def test_inbox_follows_the_rows_database(alice) -> None:
    """M3: the claim/mark land on the database the row lives on."""
    from shop.api import OrderViewSet
    from shop.models import Order

    o = Order.objects.using("other").create()
    inbox = OrderViewSet()._xsm_inbox(o)
    assert inbox.using == "other"
    assert OrderViewSet()._xsm_inbox(Order.objects.create()).using == (
        "default"
    )
    r = o.send("INC", using="other", plugins=[], payload={})
    assert r.changed


def test_stream_stops_when_access_is_revoked(alice) -> None:
    """M4: a deactivated user's stream ends with a 403 frame."""
    from shop.api import OrderViewSet
    from shop.models import Order

    o = Order.objects.create()
    OrderViewSet.xsm_stream_max_s = 5
    OrderViewSet.xsm_stream_poll_s = 0.01
    OrderViewSet.xsm_stream_recheck_every = 2
    try:
        r = _client(alice).get(f"/api/orders/{o.pk}/stream/")
        it = iter(r.streaming_content)
        assert b"event: state" in next(it)
        type(alice).objects.filter(pk=alice.pk).update(is_active=False)
        rest = b"".join(it).decode()
    finally:
        OrderViewSet.xsm_stream_max_s = 300.0
        OrderViewSet.xsm_stream_poll_s = 0.5
        OrderViewSet.xsm_stream_recheck_every = 10
    assert rest.endswith('event: error\ndata: {"status":403}\n\n')
