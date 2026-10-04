# tests/contrib/redis/test_battle_306_outage.py
"""Battle #306 (agent B): a Redis outage on every web route, every
adapter -- 503 problem body without exception text, liveness 200,
readiness 503, ONE warning line per request (no traceback), and a full
``logger.exception`` still for an unknown 500.

Each adapter is skipped when its extra is missing. The outage is a client
whose every command raises ``redis.ConnectionError`` -- what redis-py
raises when the server is gone."""

from __future__ import annotations

import logging
from typing import Any, Iterator

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("redis")

SECRET = "Error 111 connecting to 10.0.0.7:6379 -- s3cr3t-host"


class Dead:
    """Wraps a client; while ``down`` every command raises."""

    def __init__(self, client: Any) -> None:
        import redis

        self.client = client
        self.down = False
        self.err = redis.ConnectionError(SECRET)
        for name in ("execute_command", "evalsha", "eval"):
            orig = getattr(client, name)
            setattr(client, name, self._wrap(orig))
        self._pipeline = client.pipeline
        client.pipeline = self._wrap(client.pipeline)

    def _wrap(self, fn: Any) -> Any:
        def call(*a: Any, **kw: Any) -> Any:
            if self.down:
                raise self.err
            return fn(*a, **kw)

        return call


@pytest.fixture
def dead(r: Any, prefix: str) -> Iterator[Dead]:
    d = Dead(r)
    yield d
    d.down = False  # let the prefix fixture clean up


def _assert_clean_503(status: int, text: str) -> None:
    assert status == 503, (status, text)
    low = text.lower()
    for leak in ("s3cr3t", "10.0.0.7", "traceback", "error 111"):
        assert leak not in low, text


# =============================================================================
# Starlette / FastAPI
# =============================================================================
def _starlette_app(dead: Dead, prefix: str) -> Any:
    pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from src.xstate_statemachine.contrib.redis import (
        AsyncRedisStore,
        RedisInbox,
    )
    from src.xstate_statemachine.contrib.starlette import (
        StatechartRegistry,
        allow_all,
    )
    from tests.contrib.starlette._support import build_app, counter_machine

    from .conftest import _aclient

    astore = AsyncRedisStore(_aclient(dead.client), prefix=prefix)
    _wrap_async(astore.r, dead)
    reg = StatechartRegistry(
        astore,
        inbox=RedisInbox(dead.client, prefix=prefix),
        principal=lambda req: "ann",
    )
    reg.register("counter", counter_machine(), authorize=allow_all)
    return build_app(reg, name="counter")


def _wrap_async(client: Any, dead: Dead) -> None:
    for name in ("execute_command", "evalsha", "eval"):
        orig = getattr(client, name)

        def make(fn: Any) -> Any:
            async def call(*a: Any, **kw: Any) -> Any:
                if dead.down:
                    raise dead.err
                return await fn(*a, **kw)

            return call

        setattr(client, name, make(orig))


class TestStarlette:
    def test_every_route_is_a_clean_503(
        self, dead: Dead, prefix: str, caplog: Any
    ) -> None:
        pytest.importorskip("starlette")
        from starlette.testclient import TestClient

        app = _starlette_app(dead, prefix)
        with TestClient(app) as c:
            assert c.post("/m/k1/events/INC", json={}).status_code == 200
            dead.down = True
            caplog.clear()
            with caplog.at_level(logging.WARNING):
                for hdr in ({}, {"Idempotency-Key": "i-1"}):
                    r = c.post("/m/k1/events/INC", json={}, headers=hdr)
                    _assert_clean_503(r.status_code, r.text)
                    assert r.headers["content-type"].startswith(
                        "application/problem+json"
                    )
                r = c.get("/m/k1/stream")
                _assert_clean_503(r.status_code, r.text)
                assert c.get("/_xsm/health").status_code == 200
                r = c.get("/_xsm/ready")
                _assert_clean_503(r.status_code, r.text)
            dead.down = False
            assert c.post("/m/k1/events/INC", json={}).status_code == 200
        warned = [x for x in caplog.records if x.levelno >= logging.WARNING]
        assert all(x.exc_info is None for x in warned), [
            x.getMessage() for x in warned
        ]
        assert all(x.levelno == logging.WARNING for x in warned)

    def test_unknown_500_still_logs_a_traceback(
        self, dead: Dead, prefix: str, caplog: Any
    ) -> None:
        pytest.importorskip("starlette")
        from starlette.testclient import TestClient

        app = _starlette_app(dead, prefix)
        import redis

        with TestClient(app) as c:
            dead.err = redis.ResponseError("WRONGTYPE " + SECRET)
            dead.down = True
            with caplog.at_level(logging.WARNING):
                r = c.post("/m/k1/events/INC", json={})
            assert r.status_code == 500 and "s3cr3t" not in r.text
        assert any(x.exc_info for x in caplog.records), caplog.text


def test_fastapi_router_get_and_send(dead: Dead, prefix: str) -> None:
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.xstate_statemachine.contrib.fastapi import (
        StatechartRouter,
        instrument_app,
    )
    from src.xstate_statemachine.contrib.redis import AsyncRedisStore
    from src.xstate_statemachine.contrib.starlette import (
        StatechartRegistry,
        allow_all,
    )
    from tests.contrib.starlette._support import counter_machine

    from .conftest import _aclient

    astore = AsyncRedisStore(_aclient(dead.client), prefix=prefix)
    _wrap_async(astore.r, dead)
    reg = StatechartRegistry(astore)
    reg.register("counter", counter_machine(), authorize=allow_all)
    app = FastAPI()
    app.include_router(StatechartRouter(reg, "counter"))
    instrument_app(app, reg)
    with TestClient(app) as c:
        dead.down = True
        for method, url, kw in (
            ("get", "/counter/k1", {}),
            ("post", "/counter/k1/send", {"json": {"type": "INC"}}),
            ("post", "/counter/k1/events/INC", {"json": {}}),
            ("get", "/counter/k1/events", {}),
            ("get", "/counter/k1/stream", {}),
        ):
            r = getattr(c, method)(url, **kw)
            _assert_clean_503(r.status_code, r.text)
        assert c.get("/_xsm/health").status_code == 200
        r = c.get("/_xsm/ready")
        _assert_clean_503(r.status_code, r.text)


# =============================================================================
# Flask
# =============================================================================
def test_flask_every_route_is_a_clean_503(
    dead: Dead, prefix: str, caplog: Any
) -> None:
    pytest.importorskip("flask")
    from src.xstate_statemachine.contrib.redis import RedisInbox, RedisStore
    from tests.contrib.flask.conftest import make_app

    store = RedisStore(dead.client, prefix=prefix)
    app = make_app(store, inbox=RedisInbox(dead.client, prefix=prefix))
    c = app.test_client()
    assert c.post("/orders/o1/send", json={"type": "ADD"}).status_code < 300
    dead.down = True
    with caplog.at_level(logging.WARNING):
        for method, url, kw in (
            ("get", "/orders/o1", {}),
            ("post", "/orders/o1/send", {"json": {"type": "ADD"}}),
            (
                "post",
                "/orders/o1/send",
                {
                    "json": {"type": "ADD"},
                    "headers": {"Idempotency-Key": "i1"},
                },
            ),
            ("get", "/orders/o1/events", {}),
            ("get", "/orders/o1/stream", {}),
        ):
            r = getattr(c, method)(url, **kw)
            _assert_clean_503(r.status_code, r.get_data(as_text=True))
    warned = [x for x in caplog.records if x.levelno >= logging.WARNING]
    assert all(x.exc_info is None for x in warned), caplog.text
