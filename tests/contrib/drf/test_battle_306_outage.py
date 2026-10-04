# tests/contrib/drf/test_battle_306_outage.py
"""Battle #306 (agent B): a DRF viewset whose ``xsm_inbox`` is a
`RedisInbox` -- a Redis outage answers 503 with no exception text and the
keyed event is NEVER admitted undeduplicated (the snapshot lives in the
ORM, so the store is fine; only the inbox is down)."""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

pytestmark = pytest.mark.django_db

SECRET = "Error 111 connecting to 10.0.0.7:6379 -- s3cr3t-host"


def _client() -> Any:
    pytest.importorskip("redis")
    url = os.environ.get("XSM_REDIS_URL")
    if url:
        import redis

        return redis.Redis.from_url(url)
    fakeredis = pytest.importorskip("fakeredis")
    return fakeredis.FakeRedis()


def test_inbox_outage_is_503_not_admitted(db: Any) -> None:
    import redis
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient
    from shop import api
    from shop.models import Order

    from xstate_statemachine.contrib.redis import RedisInbox

    prefix = f"t-{uuid.uuid4().hex[:8]}"
    inbox = RedisInbox(_client(), prefix=prefix)

    def down(*a: Any, **kw: Any) -> Any:
        raise redis.ConnectionError(SECRET)

    for name in ("_claim", "_get", "_mark", "_release"):
        setattr(inbox, name, down)
    user = get_user_model().objects.create_superuser("root", password="p")
    order = Order.objects.create(title="o")
    c = APIClient()
    c.force_authenticate(user)
    old = api.OrderViewSet.xsm_inbox
    api.OrderViewSet.xsm_inbox = inbox
    try:
        r = c.post(
            f"/api/orders/{order.pk}/inc/",
            {"n": 1},
            format="json",
            HTTP_IDEMPOTENCY_KEY="k-1",
        )
    finally:
        api.OrderViewSet.xsm_inbox = old
    assert r.status_code == 503, r.content
    text = r.content.decode().lower()
    for leak in ("s3cr3t", "10.0.0.7", "traceback", "error 111"):
        assert leak not in text, text
    order.refresh_from_db()
    assert order.machine.context.get("count", 0) == 0  # never admitted
