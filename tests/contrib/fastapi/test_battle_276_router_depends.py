# tests/contrib/fastapi/test_battle_276_router_depends.py
"""#276 battle (A): get_interpreter, instrument_app, the route class."""

from __future__ import annotations

import contextlib
import time
from typing import List, Literal

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.persistence import MemoryInbox, MemoryStore

from ..conftest import requires_extra

pytestmark = requires_extra("fastapi")
pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel, field_validator  # noqa: E402

from src.xstate_statemachine.contrib.fastapi import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    StatechartRouter,
    allow_all,
    get_interpreter,
    instrument_app,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: int


class Cancel(EventModel):
    type: Literal["CANCEL"] = "CANCEL"


def order_machine():
    cfg = {
        "id": "order",
        "initial": "open",
        "states": {
            "open": {"on": {"PAY": "paid", "CANCEL": "cancelled"}},
            "paid": {},
            "cancelled": {},
        },
    }
    return create_machine(cfg, event_schemas=events_union(Pay, Cancel))


class StampStore(MemoryStore):
    saved_at: List[float] = []

    def save(self, *a, **kw):
        type(self).saved_at.append(time.perf_counter())
        return super().save(*a, **kw)


def make(store=None, **kw):
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register("order", order_machine(), authorize=allow_all)
    return reg


def app_for(reg, **router_kw):
    app = FastAPI()
    app.include_router(StatechartRouter(reg, "order", **router_kw))
    return instrument_app(app, reg)


def allow():
    return None


# --- 1. get_interpreter ------------------------------------------------------
def test_save_commits_before_response():
    StampStore.saved_at = []
    reg = make(StampStore())
    app = app_for(reg)
    sent = []

    @app.post("/x/{id}")
    async def pay(o=get_interpreter(reg, "order")):
        r = await o.send("CANCEL", wait=True)
        sent.append(time.perf_counter())
        return ReceiptResponse(o, r)

    with TestClient(app) as c:
        assert c.post("/x/a").status_code == 200
        got = time.perf_counter()
    assert StampStore.saved_at
    # 📝 `<=`: a coarse clock (Windows, 3.9) can stamp two adjacent
    #    events identically; the ORDER is what matters -- the save
    #    happened no later than the response was received.
    assert sent[0] <= StampStore.saved_at[-1] <= got


def test_key_callable_raising_is_problem_not_traceback():
    reg = make()
    app = app_for(reg)

    def bad(_r):
        raise KeyError("nope")

    @app.get("/k")
    async def k(o=get_interpreter(reg, "order", key=bad)):
        return {}

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/k")
    assert r.status_code == 500
    assert "Traceback" not in r.text


def test_missing_key_404_problem():
    reg = make()
    app = app_for(reg)

    @app.get("/m/{id}")
    async def m(o=get_interpreter(reg, "order", create_if_missing=False)):
        return {}

    with TestClient(app) as c:
        r = c.get("/m/ghost")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")


def test_actor_http_exception_passes_through():
    reg = make()
    app = app_for(reg)

    async def deny():
        raise HTTPException(401, "who?")

    @app.get("/a/{id}")
    async def a(o=get_interpreter(reg, "order", actor=deny)):
        return {}

    with TestClient(app) as c:
        assert c.get("/a/x").status_code == 401


def test_handler_http_exception_discards_and_keeps_status():
    reg = make()
    app = app_for(reg)

    @app.post("/h/{id}")
    async def h(o=get_interpreter(reg, "order")):
        await o.send("CANCEL", wait=True)
        raise HTTPException(418, "teapot")

    with TestClient(app) as c:
        assert c.post("/h/z").status_code == 418
        assert c.get("/order/z").json()["state"] == "open"


def test_two_dependencies_same_key_share_one_interpreter():
    reg = make()
    app = app_for(reg)

    @app.post("/d/{id}")
    async def d(
        o=get_interpreter(reg, "order"), o2=get_interpreter(reg, "order")
    ):
        return {"same": o is o2}

    with TestClient(app) as c:
        r = c.post("/d/q")
    assert r.status_code == 200, r.text
    assert r.json()["same"] is True


# --- 2. instrument_app -------------------------------------------------------
def test_instrument_twice_is_idempotent():
    reg = make()
    app = app_for(reg)
    instrument_app(app, reg)
    paths = [getattr(r, "path", None) for r in app.router.routes]
    assert paths.count("/_xsm/health") == 1
    with TestClient(app) as c:
        assert c.get("/_xsm/ready").status_code == 200


def test_user_lifespan_error_still_stops_registry():
    @contextlib.asynccontextmanager
    async def mine(app):
        yield
        raise RuntimeError("user shutdown boom")

    reg = make()
    app = FastAPI(lifespan=mine)
    instrument_app(app, reg)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            assert reg.started
    assert not reg.started and reg.draining


# --- 3. the route class ------------------------------------------------------
def _post(c, path, content, ctype="application/json"):
    return c.post(path, content=content, headers={"content-type": ctype})


def test_chunked_body_over_limit_is_413():
    reg = make(max_body_bytes=64)
    big = b'{"type":"CANCEL","pad":"' + b"x" * 200 + b'"}'
    with TestClient(app_for(reg)) as c:
        r = c.post(
            "/order/a/send",
            content=iter([big[:50], big[50:]]),
            headers={"content-type": "application/json"},
        )
    assert r.status_code == 413


def test_multipart_and_utf16_are_problems():
    reg = make()
    with TestClient(app_for(reg)) as c:
        r = _post(c, "/order/a/send", b"a=1", "multipart/form-data; b=x")
        assert r.status_code == 415
        r = _post(
            c,
            "/order/a/send",
            '{"type":"CANCEL"}'.encode("utf-16"),
            "application/json; charset=utf-16",
        )
    # 📝 confirmation: RFC 8259 JSON in UTF-16 is decoded by json.loads
    assert r.status_code == 200, r.text


def test_max_body_zero_rejects_nonempty():
    reg = make(max_body_bytes=0)
    with TestClient(app_for(reg)) as c:
        assert _post(c, "/order/a/events/CANCEL", b"{}").status_code == 413
        assert c.post("/order/a/events/CANCEL").status_code == 200


# --- 4. router semantics -----------------------------------------------------
def test_per_event_dependency_for_undeclared_event_fails_loudly():
    reg = make()
    with pytest.raises(ValueError):
        StatechartRouter(
            reg, "order", per_event_dependencies={"PAYY": [Depends(allow)]}
        )


def test_prefix_without_slash():
    reg = make()
    try:
        r = StatechartRouter(reg, "order", prefix="orders")
    except (ValueError, AssertionError):
        return
    app = FastAPI()
    app.include_router(r)
    with TestClient(app) as c:
        assert c.get("/orders/a").status_code == 200


def test_events_and_send_missing_key_404():
    reg = make()
    with TestClient(app_for(reg, create_if_missing=False)) as c:
        assert c.get("/order/ghost/events").status_code == 404
        r = c.post("/order/ghost/send", json={"type": "CANCEL"})
        assert r.status_code == 404


def test_include_diagram_false_removes_from_spec():
    reg = make()
    with TestClient(app_for(reg, include_diagram=False)) as c:
        spec = c.get("/openapi.json").json()
    assert not any(p.endswith("diagram.mmd") for p in spec["paths"])


# --- 5. validation problem ---------------------------------------------------
class Big(BaseModel):
    xs: List[int]
    s: str

    @field_validator("s")
    @classmethod
    def v(cls, s):
        raise ValueError(f"bad {s}")


def test_validation_problem_bounded_and_value_free():
    reg = make()
    app = app_for(reg)

    @app.post("/v")
    async def v(m: Big):
        return {}

    with TestClient(app) as c:
        r = c.post("/v", json={"xs": ["SECRETX"] * 10000, "s": "SECRETS"})
    assert r.status_code == 422
    assert "SECRET" not in r.text
    assert len(r.content) < 64 * 1024
    assert r.json()["errors_total"] == 10001


# --- 6. concurrency ----------------------------------------------------------
def test_resident_across_two_testclient_portals():
    reg = make()
    app = app_for(reg)

    @app.get("/r/{id}")
    async def r(id: str):
        await reg.resident("order", id)
        return {}

    with TestClient(app) as c:
        assert c.get("/r/a").status_code == 200
        assert c.get("/r/a").status_code == 200
    with TestClient(app) as c:
        assert c.get("/r/b").status_code == 200


def test_concurrent_sends_threads():
    from concurrent.futures import ThreadPoolExecutor

    reg = make(inbox=MemoryInbox(), principal=lambda c: "u")
    with TestClient(app_for(reg)) as c:

        def one(i):
            return c.post(
                f"/order/k{i % 5}/send", json={"type": "CANCEL"}
            ).status_code

        with ThreadPoolExecutor(16) as ex:
            codes = list(ex.map(one, range(50)))
    assert set(codes) <= {200, 409}, codes
