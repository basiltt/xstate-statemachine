# tests/contrib/channels/test_battle_283_b.py
"""#283 battle B: the WebSocket bridge under abuse."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest import mock

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from django.utils.functional import SimpleLazyObject

from xstate_statemachine.contrib.channels import (
    WS_POLICY_VIOLATION,
    StatechartConsumer,
    live_consumers,
)
from xstate_statemachine.contrib.channels import broadcast
from xstate_statemachine.contrib.channels.consumer import (
    _LIVE,
    _concrete_model,
)

from .test_channels import _comm, _setup

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _clean_layer() -> Any:
    get_channel_layer().groups.clear()
    yield


def _layer_groups() -> dict:
    return {k: v for k, v in get_channel_layer().groups.items() if v}


def test_malformed_and_binary_frames_answer_error_and_stay_open() -> None:
    user, _, order = _setup()

    async def go() -> None:
        c = _comm(f"/ws/orders/{order.pk}/", user)
        await c.connect()
        await c.receive_json_from()
        await c.send_to(text_data="{not json")
        err = await c.receive_json_from()
        assert err["kind"] == "error" and err["status"] == 422
        assert err["title"] == "Malformed JSON"
        await c.send_to(bytes_data=b"\x00\x01")
        err = await c.receive_json_from()
        assert err["title"] == "Binary frames are not supported"
        await c.send_json_to({"type": "xsm.ping"})
        assert (await c.receive_json_from())["kind"] == "pong"
        big = {"type": "NOPE", "payload": {"x": "a" * 2**20}}
        await c.send_json_to(big)
        assert (await c.receive_json_from())["status"] == 422
        for _ in range(1000):
            await c.send_json_to({"type": "xsm.ping"})
        for _ in range(1000):
            assert (await c.receive_json_from())["kind"] == "pong"
        await c.disconnect()
        assert live_consumers() == 0 and not _layer_groups()

    asyncio.run(go())


def test_broadcast_from_a_running_loop_is_scheduled_not_raised() -> None:
    user, _, order = _setup()

    async def go() -> None:
        c = _comm(f"/ws/orders/{order.pk}/", user)
        await c.connect()
        await c.receive_json_from()
        # the receiver run on the loop thread (async_to_sync raises there)
        receipt = mock.Mock(changed=True)
        broadcast._on_commit(None, order, mock.Mock(type="X"), receipt)
        msg = await c.receive_json_from(timeout=2)
        assert msg["kind"] == "transition" and msg["event"] == "X"
        await order.asend("SUBMIT")  # asend() from async code
        msg = await c.receive_json_from(timeout=2)
        assert msg["event"] == "SUBMIT"
        assert not broadcast._PENDING
        await c.disconnect()

    asyncio.run(go())


def test_layer_down_never_fails_the_commit(caplog: Any) -> None:
    _, _, order = _setup()
    layer = get_channel_layer()
    with (
        mock.patch.object(
            layer, "group_send", side_effect=ConnectionError("redis down")
        ),
        caplog.at_level(logging.WARNING),
    ):
        r = order.send("SUBMIT")
    assert r.changed
    order.refresh_from_db()
    assert order.matches("order.review")
    assert "could not broadcast SUBMIT" in caplog.text


def test_slow_reader_does_not_block_the_sender() -> None:
    """InMemoryChannelLayer capacity is 100: message 101+ raises
    ChannelFull, which `group_send` swallows -- the sender's commit is
    never hurt (a slow subscriber loses pushes, then reads a snapshot)."""
    _, _, order = _setup()
    layer = get_channel_layer()
    group = broadcast.group_name_for(order)

    async def stall() -> str:
        name = await layer.new_channel()  # a reader that never reads
        await layer.group_add(group, name)
        return name

    name = asyncio.run(stall())
    for _ in range(105):
        order.refresh_from_db()
        order.send("INC")
    assert layer.channels[name].qsize() == layer.capacity
    asyncio.run(layer.group_discard(group, name))


def test_overridden_group_name_still_receives_broadcasts() -> None:
    from shop.models import Order

    class Custom(StatechartConsumer):
        model = Order

        @staticmethod
        def group_name(instance: Any) -> str:
            return f"tenant1.order.{instance.pk}"

    user, _, order = _setup()

    async def go() -> None:
        c = WebsocketCommunicator(Custom.as_asgi(), "/ws/")
        c.scope["user"] = user
        c.scope["url_route"] = {"kwargs": {"pk": order.pk}}
        assert (await c.connect())[0]
        await c.receive_json_from()
        await order.asend("SUBMIT")
        assert (await c.receive_json_from(timeout=2))["event"] == "SUBMIT"
        await c.disconnect()

    try:
        asyncio.run(go())
    finally:
        broadcast._NAMERS.pop(Order, None)


def test_group_name_override_must_be_static() -> None:
    from shop.models import Order

    with pytest.raises(TypeError, match="staticmethod"):

        class Bad(StatechartConsumer):
            model = Order

            def group_name(self, instance: Any) -> str:  # type: ignore
                return "x"


def test_two_hundred_subscribers_five_rounds_leave_nothing() -> None:
    user, _, order = _setup()

    async def go() -> None:
        path = f"/ws/orders/{order.pk}/"
        for _ in range(5):
            comms = [_comm(path, user) for _ in range(200)]
            for c in comms:
                assert (await c.connect())[0]
                await c.receive_json_from()
            assert live_consumers() == 200
            for c in comms:
                await c.disconnect()
            assert live_consumers() == 0
        assert len(_LIVE) == 0 and not _layer_groups()

    asyncio.run(go())


def test_lazy_user_heartbeat_then_revoked_closes_1008() -> None:
    from shop.ws import OrderConsumer

    user, _, order = _setup()
    lazy = SimpleLazyObject(lambda: get_user_model().objects.get(pk=user.pk))
    assert _concrete_model(lazy) is get_user_model()
    assert _concrete_model(AnonymousUser()) is get_user_model()
    OrderConsumer.heartbeat_s = 0.2
    try:

        async def go() -> None:
            c = _comm(f"/ws/orders/{order.pk}/", lazy)
            assert (await c.connect())[0]
            await c.receive_json_from()
            pings = 0
            loop = asyncio.get_running_loop()
            end = loop.time() + 2
            while loop.time() < end:
                msg = await c.receive_json_from(timeout=1)
                pings += msg["kind"] == "ping"
            assert pings >= 5
            await database_sync_to_async(user.user_permissions.clear)()
            await order.asend("SUBMIT")
            while True:
                out = await c.receive_output(timeout=2)
                if out["type"] == "websocket.close":
                    break
            assert out["code"] == WS_POLICY_VIOLATION
            await c.disconnect()  # the server's websocket.disconnect
            assert live_consumers() == 0

        asyncio.run(go())
    finally:
        OrderConsumer.heartbeat_s = 15.0


def test_missing_auth_middleware_is_logged(caplog: Any) -> None:
    from shop.ws import websocket_urlpatterns

    _, _, order = _setup()

    async def go() -> None:
        c = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/orders/{order.pk}/"
        )
        ok, code = await c.connect()
        assert not ok and code == WS_POLICY_VIOLATION

    with caplog.at_level(logging.WARNING):
        asyncio.run(go())
    assert "AuthMiddlewareStack" in caplog.text


@pytest.mark.parametrize(
    "hosts,origin,ok",
    [
        (["*"], b"https://evil.example", True),  # '*' allows EVERY origin
        (["app.example"], b"https://app.example", True),
        (["app.example"], b"https://evil.example", False),
    ],
)
def test_allowed_hosts_origin_validator(
    hosts: Any, origin: bytes, ok: bool
) -> None:
    from channels.security.websocket import AllowedHostsOriginValidator
    from shop.ws import websocket_urlpatterns

    user, _, order = _setup()

    async def go() -> bool:
        app = AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns))
        c = WebsocketCommunicator(
            app, f"/ws/orders/{order.pk}/", headers=[(b"origin", origin)]
        )
        c.scope["user"] = user
        connected, _ = await c.connect()
        if connected:
            await c.disconnect()
        return connected

    with override_settings(ALLOWED_HOSTS=hosts):
        assert asyncio.run(go()) is ok


def test_ensure_broadcaster_is_idempotent() -> None:
    from xstate_statemachine.contrib.django.signals import post_transition

    before = len(post_transition.receivers)
    for _ in range(3):  # autoreload re-imports call it again
        broadcast.ensure_broadcaster()
    assert len(post_transition.receivers) == before
