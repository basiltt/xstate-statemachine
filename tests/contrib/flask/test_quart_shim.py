# tests/contrib/flask/test_quart_shim.py
"""#285: the Quart shim runs the same route table on Flask's async twin
(skipped when Quart is not installed -- the CI flask cell installs it)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("flask")

quart = pytest.importorskip("quart")

from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryInbox,
    MemoryLog,
    MemoryStore,
)

from .conftest import ORDER, order_machine  # noqa: E402


def make(**kw: Any) -> Any:
    from src.xstate_statemachine.contrib.flask import allow_all
    from src.xstate_statemachine.contrib.flask.quart import (
        QuartXState,
        create_quart_statechart_blueprint,
    )

    authorize = kw.pop("authorize", allow_all)
    xsm = QuartXState()
    xsm.register("order", order_machine(), authorize=authorize)
    app = quart.Quart(__name__)
    if kw.get("inbox") is not None:
        kw.setdefault("principal", lambda r: r.headers.get("X-User", "u"))
    xsm.init_app(app, store=kw.pop("store", MemoryStore()), **kw)
    app.register_blueprint(
        create_quart_statechart_blueprint(xsm, "order", "/orders")
    )
    app.xsm = xsm  # type: ignore[attr-defined]
    return app


def run(coro: Any) -> Any:
    return asyncio.run(coro)


class TestQuartRoutes:
    def test_status_matrix(self) -> None:
        async def go() -> None:
            c = make().test_client()
            r = await c.get("/orders/1")
            assert (await r.get_json())["state"] == "cart"
            r = await c.post("/orders/1/send", json={"type": "CHECKOUT"})
            assert r.status_code == 409
            r = await c.post("/orders/1/send", json={"type": "ADD", "n": 2})
            assert r.status_code == 200
            assert (await r.get_json())["changed"] is True
            r = await c.post("/orders/1/events/CHECKOUT", json={})
            assert r.status_code == 200
            r = await c.post("/orders/1/send", json={"type": "BOOM"})
            assert r.status_code == 500
            assert b"secret internals" not in await r.get_data()
            r = await c.post(
                "/orders/1/send",
                data="x",
                headers={"Content-Type": "text/plain"},
            )
            assert r.status_code == 415
            r = await c.post("/orders/1/send", json={"no": "type"})
            assert r.status_code == 400
            r = await c.get("/orders/1/send")
            assert r.status_code == 405
            r = await c.get("/orders/1/events")
            assert (await r.get_json())["declared"][0] == "ADD"
            r = await c.get("/orders/schema/diagram.mmd")
            assert (await r.get_data()).startswith(b"stateDiagram")
            r = await c.get("/orders/1/history")
            assert r.status_code == 404
            r = await c.get("/orders/1/stream?once=1")
            assert b"event: snapshot" in await r.get_data()

        run(go())

    def test_403_async_authorizer(self) -> None:
        async def deny(req: Any, **kw: Any) -> bool:
            return False

        async def go() -> None:
            c = make(authorize=deny).test_client()
            r = await c.post("/orders/1/send", json={"type": "ADD"})
            assert r.status_code == 403

        run(go())

    def test_idempotency_and_history(self) -> None:
        async def go() -> None:
            app = make(inbox=MemoryInbox(), log=MemoryLog())
            c = app.test_client()
            h = {"Idempotency-Key": "k", "X-User": "a"}
            r1 = await c.post(
                "/orders/1/send", json={"type": "ADD", "n": 1}, headers=h
            )
            r2 = await c.post(
                "/orders/1/send", json={"type": "ADD", "n": 1}, headers=h
            )
            assert (await r2.get_json())["duplicate"] is True
            r3 = await c.post(
                "/orders/1/send", json={"type": "ADD", "n": 9}, headers=h
            )
            assert r1.status_code == 200 and r3.status_code == 422
            items = (await (await c.get("/orders/1/history")).get_json())[
                "items"
            ]
            assert [i["event_type"] for i in items] == ["ADD"]

        run(go())

    def test_async_with_act(self) -> None:
        async def go() -> int:
            app = make()
            async with app.app_context():
                for _ in range(3):
                    async with app.xsm.act("order", "7") as i:
                        await i.send("ADD", wait=True)
                return int(
                    json.loads(
                        app.extensions["xstate"].store.load("order.7").snapshot
                    )["context"]["items"]
                )

        assert run(go()) == 3

    def test_register_requires_authorize(self) -> None:
        from src.xstate_statemachine.contrib.flask.quart import QuartXState

        with pytest.raises(TypeError, match="X0.1"):
            QuartXState().register("o", ORDER)
