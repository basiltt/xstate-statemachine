# tests/contrib/channels/test_channels.py
"""#283: `StatechartConsumer` over `WebsocketCommunicator`."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission

from xstate_statemachine.contrib.channels import (
    WS_POLICY_VIOLATION,
    live_consumers,
)

pytestmark = pytest.mark.django_db(transaction=True)


def _setup() -> Any:
    from shop.models import Order

    U = get_user_model()
    u = U.objects.create_user("watcher", password="p")
    u.user_permissions.add(Permission.objects.get(codename="view_order"))
    u = U.objects.get(pk=u.pk)
    nobody = U.objects.create_user("nobody", password="p")
    return u, nobody, Order.objects.create()


def _comm(path: str, user: Any) -> WebsocketCommunicator:
    from shop.ws import websocket_urlpatterns

    from channels.routing import URLRouter

    comm = WebsocketCommunicator(URLRouter(websocket_urlpatterns), path)
    comm.scope["user"] = user  # what AuthMiddlewareStack would set
    return comm


def test_snapshot_send_broadcast_and_no_leak() -> None:
    user, _, order = _setup()

    async def go() -> None:
        a = _comm(f"/ws/orders/{order.pk}/", user)
        b = _comm(f"/ws/orders/{order.pk}/", user)
        ok, _ = await a.connect()
        assert ok
        snap = await a.receive_json_from()
        assert snap["kind"] == "snapshot" and snap["state"] == "draft"
        assert snap["available_events"] == ["CANCEL", "INC", "SUBMIT"]
        assert "context" not in snap  # X0.1
        ok, _ = await b.connect()
        assert ok
        await b.receive_json_from()  # b's snapshot
        assert live_consumers() == 2
        await a.send_json_to({"type": "SUBMIT"})
        receipt = await a.receive_json_from()
        assert receipt["kind"] == "receipt" and receipt["changed"] is True
        assert receipt["status"] == 200
        pushed_a = await a.receive_json_from()
        pushed_b = await b.receive_json_from()
        for msg in (pushed_a, pushed_b):
            assert msg["kind"] == "transition" and msg["event"] == "SUBMIT"
            assert msg["version"] == 1
            assert "legal" in msg["state"]["review"]
        await a.send_json_to({"type": "xsm.ping"})
        assert (await a.receive_json_from())["kind"] == "pong"
        await a.disconnect()
        await b.disconnect()
        assert live_consumers() == 0

    asyncio.run(go())
    order.refresh_from_db()
    assert order.matches("order.review")


def test_hundred_connect_disconnect_cycles_leave_nothing() -> None:
    user, _, order = _setup()

    async def go() -> None:
        before = len(asyncio.all_tasks())
        for _ in range(100):
            c = _comm(f"/ws/orders/{order.pk}/", user)
            ok, _ = await c.connect()
            assert ok
            await c.receive_json_from()
            await c.disconnect()
        assert live_consumers() == 0
        await asyncio.sleep(0)
        assert len(asyncio.all_tasks()) <= before

    asyncio.run(go())


def test_unauthenticated_and_unauthorised_close_1008() -> None:
    user, nobody, order = _setup()

    async def go() -> None:
        for who, path in (
            (AnonymousUser(), f"/ws/orders/{order.pk}/"),
            (nobody, f"/ws/orders/{order.pk}/"),  # no view permission
            (user, "/ws/orders/999999/"),  # no such row
        ):
            c = _comm(path, who)
            ok, code = await c.connect()
            assert not ok and code == WS_POLICY_VIOLATION
        # no user in the scope at all (no AuthMiddlewareStack)
        from shop.ws import websocket_urlpatterns

        from channels.routing import URLRouter

        c = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/orders/{order.pk}/"
        )
        ok, code = await c.connect()
        assert not ok and code == WS_POLICY_VIOLATION
        assert live_consumers() == 0

    asyncio.run(go())


def test_errors_and_permission_guard() -> None:
    from shop.models import Approval

    U = get_user_model()
    viewer = U.objects.create_user("viewer", password="p")
    viewer.user_permissions.add(
        Permission.objects.get(codename="view_approval")
    )
    viewer = U.objects.get(pk=viewer.pk)
    a = Approval.objects.create()

    async def go() -> None:
        c = _comm(f"/ws/approvals/{a.pk}/", viewer)
        ok, _ = await c.connect()
        assert ok
        snap = await c.receive_json_from()
        assert "APPROVE" not in snap["available_events"]
        await c.send_json_to({"type": "APPROVE"})
        err = await c.receive_json_from()
        assert err == {
            "kind": "error",
            "type": "about:blank",
            "title": "Forbidden",
            "status": 403,
            "error": "PermissionDenied",
        }
        await c.send_json_to({"type": "NOPE"})
        assert (await c.receive_json_from())["status"] == 422
        await c.send_json_to({"no": "type"})
        assert (await c.receive_json_from())["status"] == 422
        await c.send_json_to({"type": "COMMENT", "payload": [1]})
        assert (await c.receive_json_from())["status"] == 422
        await c.send_json_to({"type": "COMMENT", "payload": {"text": "hi"}})
        r = await c.receive_json_from()
        assert r["kind"] == "receipt" and r["changed"] is True
        await c.disconnect()

    asyncio.run(go())
    assert database_sync_to_async  # imported for the module under test


def test_heartbeat_pings() -> None:
    from shop.ws import OrderConsumer

    user, _, order = _setup()
    OrderConsumer.heartbeat_s = 0.05
    try:

        async def go() -> None:
            c = _comm(f"/ws/orders/{order.pk}/", user)
            await c.connect()
            await c.receive_json_from()
            assert (await c.receive_json_from(timeout=2))["kind"] == "ping"
            await c.disconnect()
            assert live_consumers() == 0

        asyncio.run(go())
    finally:
        OrderConsumer.heartbeat_s = 15.0
