# tests/contrib/channels/test_review_361.py
"""#361: H1/H2 over WebSocket (reserved keys refused) and M2 (a revoked
user is re-checked on every push and on the heartbeat)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from xstate_statemachine.contrib.channels import WS_POLICY_VIOLATION

pytestmark = pytest.mark.django_db(transaction=True)


def _setup() -> Any:
    from shop.models import Order

    U = get_user_model()
    users = []
    for name in ("a", "b"):
        u = U.objects.create_user(name, password="p")
        u.user_permissions.add(Permission.objects.get(codename="view_order"))
        users.append(U.objects.get(pk=u.pk))
    return users, Order.objects.create()


def _comm(pk: Any, user: Any) -> WebsocketCommunicator:
    from shop.ws import websocket_urlpatterns

    c = WebsocketCommunicator(
        URLRouter(websocket_urlpatterns), f"/ws/orders/{pk}/"
    )
    c.scope["user"] = user
    return c


def test_reserved_payload_keys_are_refused() -> None:
    (user, _), order = _setup()

    async def go() -> None:
        c = _comm(order.pk, user)
        await c.connect()
        await c.receive_json_from()
        for key in ("lock", "using", "plugins", "actor_id", "reason"):
            await c.send_json_to({"type": "INC", "payload": {key: "x"}})
            err = await c.receive_json_from()
            assert err["kind"] == "error" and err["status"] == 422
            assert err["error"] == "ReservedKeyError" and err["keys"] == [key]
        await c.disconnect()

    asyncio.run(go())
    order.refresh_from_db()
    assert order.statechart_version == 0


def test_revoked_user_is_dropped_on_the_next_push() -> None:
    (watcher, sender), order = _setup()

    async def go() -> None:
        w = _comm(order.pk, watcher)
        s = _comm(order.pk, sender)
        await w.connect()
        await w.receive_json_from()
        await s.connect()
        await s.receive_json_from()
        await database_sync_to_async(
            lambda: type(watcher)
            .objects.filter(pk=watcher.pk)
            .update(is_active=False)
        )()
        await s.send_json_to({"type": "INC"})
        await s.receive_json_from()  # the sender's receipt
        out = await w.receive_output(timeout=2)
        assert out == {"type": "websocket.close", "code": WS_POLICY_VIOLATION}
        await s.disconnect()

    asyncio.run(go())


def test_revoked_user_is_dropped_on_heartbeat() -> None:
    from shop.ws import OrderConsumer

    (user, _), order = _setup()
    OrderConsumer.heartbeat_s = 0.05
    try:

        async def go() -> None:
            c = _comm(order.pk, user)
            await c.connect()
            await c.receive_json_from()
            await database_sync_to_async(
                lambda: user.user_permissions.clear()
            )()
            out = await c.receive_output(timeout=2)
            assert out == {
                "type": "websocket.close",
                "code": WS_POLICY_VIOLATION,
            }

        asyncio.run(go())
    finally:
        OrderConsumer.heartbeat_s = 15.0
