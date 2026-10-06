"""#277 battle (A): a request body that never arrives is a bounded 408.

Root cause of the multi-worker load-test stall on Windows: uvicorn's
default worker loop there occasionally accepted a connection and never
delivered its body, and nothing in the registry or the FastAPI route
class bounded the body read -- the handler (and the client) waited
forever. `body_timeout_s` bounds it: a 408 problem, the worker moves on.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine.persistence import MemoryStore

from ..conftest import requires_extra
from ._support import build_app, counter_machine

pytestmark = requires_extra("starlette")
pytest.importorskip("starlette")

from src.xstate_statemachine.contrib.starlette import (  # noqa: E402
    RequestTimeoutError,
    StatechartRegistry,
    allow_all,
    json_body,
)


async def _post_without_body(app: Any, path: str) -> List[Dict[str, Any]]:
    """POST whose headers arrive but whose body never does."""
    sent: List[Dict[str, Any]] = []
    never = asyncio.Event()

    async def receive() -> Dict[str, Any]:
        await never.wait()  # 🔥 the body is never delivered
        return {"type": "http.disconnect"}  # pragma: no cover

    async def send(msg: Dict[str, Any]) -> None:
        sent.append(msg)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"2"),
            (b"host", b"test"),
        ],
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    await asyncio.wait_for(app(scope, receive, send), 5.0)
    return sent


def _status(sent: List[Dict[str, Any]]) -> int:
    return int(next(m for m in sent if m["type"].endswith("start"))["status"])


def _body(sent: List[Dict[str, Any]]) -> Dict[str, Any]:
    raw = b"".join(m.get("body", b"") for m in sent if "body" in m)
    return json.loads(raw)


def test_send_event_with_a_body_that_never_arrives_is_408() -> None:
    reg = StatechartRegistry(MemoryStore(), body_timeout_s=0.2)
    reg.register("counter", counter_machine(), authorize=allow_all)
    app = build_app(reg, name="counter")
    sent = asyncio.run(_post_without_body(app, "/m/k1/events/INC"))
    assert _status(sent) == 408
    assert _body(sent)["error"] == "RequestTimeoutError"
    # 📝 nothing was saved for the timed-out request
    assert reg.store.load("counter.k1") is None


def test_json_body_timeout_raises_request_timeout() -> None:
    from starlette.requests import Request

    async def go() -> None:
        async def receive() -> Dict[str, Any]:
            await asyncio.Event().wait()
            return {}  # pragma: no cover

        req = Request(
            {
                "type": "http",
                "method": "POST",
                "headers": [(b"content-type", b"application/json")],
            },
            receive,
        )
        with pytest.raises(RequestTimeoutError):
            await json_body(req, timeout_s=0.05)

    asyncio.run(go())


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf")])
def test_body_timeout_must_be_positive_and_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="body_timeout_s"):
        StatechartRegistry(MemoryStore(), body_timeout_s=bad)


def test_fastapi_route_class_bounds_the_body_read() -> None:
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from src.xstate_statemachine.contrib.fastapi import StatechartRouter

    reg = StatechartRegistry(MemoryStore(), body_timeout_s=0.2)
    reg.register("counter", counter_machine(), authorize=allow_all)
    app = FastAPI()
    app.include_router(StatechartRouter(reg, "counter"))
    sent = asyncio.run(_post_without_body(app, "/counter/k1/events/INC"))
    assert _status(sent) == 408
    assert _body(sent)["error"] == "RequestTimeoutError"
