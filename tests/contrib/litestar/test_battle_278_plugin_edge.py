"""#278 battle (adversary A): the plugin, `Provide`, the controller and
the Litestar <-> Starlette edge adapters.

Every read is bounded (`bounded`, TestClient timeouts)."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import unquote
from typing import Any, Dict, List, Optional

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    SQLiteStore,
)

from ..conftest import requires_extra
from ..starlette._support import RawSSE, RawWS, bounded

pytestmark = [requires_extra("litestar"), pytest.mark.timeout(300)]
pytest.importorskip("litestar")
httpx = pytest.importorskip("httpx")

from litestar import Litestar, Request, Response, get, post  # noqa: E402
from litestar.exceptions import HTTPException  # noqa: E402
from litestar.testing import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.litestar import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    XStatePlugin,
    create_statechart_controller,
    get_interpreter,
)
from src.xstate_statemachine.contrib.litestar._edge import (  # noqa: E402
    to_litestar,
    to_starlette,
)

CFG = {
    "id": "o",
    "initial": "open",
    "context": {"n": 0, "note": ""},
    "states": {
        "open": {
            "on": {
                "ADD": {"actions": "add"},
                "SECRET": {"target": "done"},
                "LATER": {"target": "done"},
                "BOOM": {"actions": "boom"},
            }
        },
        "done": {},
    },
}


def _add(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["n"] += 1
    ctx["note"] = str((e.payload or {}).get("note", ""))


def _boom(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    raise RuntimeError("password=hunter2")


def _machine() -> Any:
    return create_machine(
        CFG, logic=MachineLogic(actions={"add": _add, "boom": _boom})
    )


def _authorize(conn: Any, *, name: str, key: str, event: Any) -> bool:
    return event != "SECRET" and key != "forbidden"


def _registry(store: Any = None, **kw: Any) -> StatechartRegistry:
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register("o", _machine(), authorize=_authorize)
    return reg


def _app(reg: Any, *extra: Any, **ctl: Any) -> Litestar:
    return Litestar(
        route_handlers=[
            create_statechart_controller(reg, "o", path="/o", **ctl),
            *extra,
        ],
        plugins=[XStatePlugin(reg)],
        logging_config=None,
        debug=False,
    )


def _ctx(reg: Any, key: str) -> Dict[str, Any]:
    """The STORED context (what a save committed), read synchronously."""
    rec = reg.store.load(reg.store_key("o", key))
    return {"n": 0} if rec is None else json.loads(rec.snapshot)["context"]


# -----------------------------------------------------------------------------
# 1. edge adapters
# -----------------------------------------------------------------------------
def test_to_starlette_sees_a_body_litestar_already_read() -> None:
    reg = _registry()

    @post("/raw/{id:str}", status_code=200)
    async def raw(request: Request, id: str) -> Any:  # noqa: A002
        await request.json()  # Litestar consumed the stream
        return to_litestar(
            await reg.send_event(to_starlette(request), "o", id, "ADD")
        )

    with TestClient(_app(reg, raw)) as c:
        r = c.post("/raw/k1", json={"note": "hello"})
        assert r.status_code == 200, r.text
        assert _ctx(reg, "k1")["note"] == "hello"


def test_problem_responses_keep_problem_json_media_type() -> None:
    reg = _registry()
    with TestClient(_app(reg)) as c:
        r = c.post("/o/k/send", json={"type": "SECRET"})
        assert r.status_code == 403
        assert r.headers["content-type"].startswith("application/problem+json")
        assert int(r.headers["content-length"]) == len(r.content)


@pytest.mark.parametrize("spec", ["2.0", "2.4"])
def test_sse_disconnect_releases_the_slot(spec: str) -> None:
    reg = _registry(heartbeat_s=0.05)
    app = _app(reg)

    async def go() -> None:
        async with _lifespan(app):
            s = RawSSE(app, "/o/k/stream")
            orig_open = s.open

            async def open_with_spec() -> int:
                real = s.app

                async def app2(scope: Any, rcv: Any, snd: Any) -> None:
                    scope["asgi"]["spec_version"] = spec
                    await real(scope, rcv, snd)

                s.app = app2
                return await orig_open()

            assert await open_with_spec() == 200
            assert (await s.next_event())[1] == "snapshot"
            assert reg.connections("o", "k") == 1
            await s.close()
            for _ in range(100):
                if not reg.connections("o", "k"):
                    break
                await asyncio.sleep(0.01)
            assert reg.connections("o", "k") == 0
            assert reg.subscribers.count() == 0

    asyncio.run(go())


class _lifespan:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __aenter__(self) -> None:
        self.cm = self.app.lifespan()  # type: ignore[attr-defined]
        await self.cm.__aenter__()

    async def __aexit__(self, *a: Any) -> None:
        await self.cm.__aexit__(*a)


# -----------------------------------------------------------------------------
# 2. get_interpreter (Provide)
# -----------------------------------------------------------------------------
def test_provide_two_dependencies_one_key_share_one_act() -> None:
    reg = _registry()
    deps = {
        "a": get_interpreter(reg, "o"),
        "b": get_interpreter(reg, "o"),
    }

    @post("/two/{id:str}", dependencies=deps, status_code=200)
    async def two(a: Any, b: Any) -> Dict[str, Any]:
        await a.send("ADD", wait=True)
        await b.send("ADD", wait=True)
        return {"same": a is b}

    with TestClient(_app(reg, two)) as c:
        r = c.post("/two/k")
        assert r.status_code == 200, r.text
        assert r.json() == {"same": True}
        assert _ctx(reg, "k")["n"] == 2


def test_provide_idempotency_key_validated_and_stamped() -> None:
    reg = _registry(inbox=MemoryInbox(), principal=lambda c: "p")

    @post("/add/{id:str}", dependencies={"o": get_interpreter(reg, "o")})
    async def add(o: Any) -> Response:
        return ReceiptResponse(o, await o.send("ADD", wait=True))

    with TestClient(_app(reg, add)) as c:
        h = {"Idempotency-Key": "k-1"}
        assert c.post("/add/k", headers=h).status_code == 200
        r2 = c.post("/add/k", headers=h)
        assert r2.status_code == 200 and r2.json()["duplicate"] is True
        assert _ctx(reg, "k")["n"] == 1
        bad = c.post("/add/k", headers={"Idempotency-Key": "x" * 10_000})
        assert bad.status_code == 400
    reg2 = _registry()

    @post("/add/{id:str}", dependencies={"o": get_interpreter(reg2, "o")})
    async def add2(o: Any) -> Response:
        return ReceiptResponse(o, await o.send("ADD", wait=True))

    with TestClient(_app(reg2, add2)) as c:
        r = c.post("/add/k", headers={"Idempotency-Key": "k"})
        assert r.status_code == 501, r.text
        assert _ctx(reg2, "k")["n"] == 0


def test_provide_saves_before_the_response_and_on_plain_dict() -> None:
    reg = _registry()
    order: List[str] = []
    real_save = reg.store.save

    def save(*a: Any, **kw: Any) -> Any:
        order.append("save")
        return real_save(*a, **kw)

    reg.store.save = save  # type: ignore[method-assign]

    @post("/d/{id:str}", dependencies={"o": get_interpreter(reg, "o")})
    async def d(o: Any) -> Dict[str, Any]:
        await o.send("ADD", wait=True)
        order.append("return")
        return {"ok": True}

    with TestClient(_app(reg, d)) as c:
        r = c.post("/d/k")
        order.append("client")
        assert r.status_code == 201 and r.json() == {"ok": True}
        assert order == ["return", "save", "client"]
        assert _ctx(reg, "k")["n"] == 1


def test_provide_http_exception_kept_and_change_discarded() -> None:
    reg = _registry()

    @post("/t/{id:str}", dependencies={"o": get_interpreter(reg, "o")})
    async def tea(o: Any) -> None:
        await o.send("ADD", wait=True)
        raise HTTPException(status_code=418, detail="teapot")

    with TestClient(_app(reg, tea)) as c:
        assert c.post("/t/k").status_code == 418
        assert _ctx(reg, "k")["n"] == 0


def test_key_not_found_is_a_problem_outside_the_controller() -> None:
    reg = _registry()
    dep = {"o": get_interpreter(reg, "o", create_if_missing=False)}

    @get("/x/{id:str}", dependencies=dep)
    async def x(o: Any) -> Dict[str, Any]:
        return {}

    app = Litestar(
        route_handlers=[x], plugins=[XStatePlugin(reg)], logging_config=None
    )
    with TestClient(app) as c:
        r = c.get("/x/nope")
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/problem+json")


# -----------------------------------------------------------------------------
# 3. XStatePlugin
# -----------------------------------------------------------------------------
def test_plugin_twice_runs_the_lifespan_once() -> None:
    reg = _registry()
    calls: List[int] = []
    real = reg.lifespan

    def counted(app: Any) -> Any:
        calls.append(1)
        return real(app)

    reg.lifespan = counted  # type: ignore[method-assign]
    app = Litestar(
        route_handlers=[],
        plugins=[
            XStatePlugin(reg),
            XStatePlugin(reg, health_path=None, ready_path=None),
        ],
        logging_config=None,
    )
    with TestClient(app):
        pass
    assert calls == [1]


def test_plugin_dependency_name_collision_is_loud() -> None:
    from litestar.di import Provide

    reg = _registry()

    def mine() -> str:
        return "mine"

    with pytest.raises(ValueError, match="dependency_prefix"):
        Litestar(
            route_handlers=[],
            dependencies={"o": Provide(mine, sync_to_thread=False)},
            plugins=[XStatePlugin(reg, dependencies=True)],
            logging_config=None,
        )
    app = Litestar(
        route_handlers=[],
        dependencies={"o": Provide(mine, sync_to_thread=False)},
        plugins=[XStatePlugin(reg, dependencies=True, dependency_prefix="x")],
        logging_config=None,
    )
    assert "xo" in app.dependencies and "o" in app.dependencies


def test_probe_path_collision_is_loud() -> None:
    reg = _registry()

    @get("/_xsm/health")
    async def h() -> str:
        return "mine"

    with pytest.raises(Exception):
        Litestar(
            route_handlers=[h],
            plugins=[XStatePlugin(reg)],
            logging_config=None,
        )


def test_user_body_models_untouched_by_the_schema_plugin() -> None:
    import msgspec

    class Mine(msgspec.Struct):
        x: int

    assert not XStatePlugin.is_plugin_supported_type(Mine)


# -----------------------------------------------------------------------------
# 4. controller
# -----------------------------------------------------------------------------
def test_chunked_oversized_body_is_not_buffered_whole() -> None:
    reg = _registry(max_body_bytes=1024)
    app = _app(reg)
    pulled: List[int] = []

    async def go() -> int:
        chunks = [b"x" * 1024] * 64
        sent: List[Dict[str, Any]] = []

        async def receive() -> Dict[str, Any]:
            if not chunks:
                return {"type": "http.disconnect"}
            pulled.append(1)
            return {
                "type": "http.request",
                "body": chunks.pop(),
                "more_body": bool(chunks),
            }

        async def send(m: Dict[str, Any]) -> None:
            sent.append(m)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/o/k/send",
            "raw_path": b"/o/k/send",
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"t"),
                (b"content-type", b"application/json"),
            ],
            "client": ("127.0.0.1", 1),
            "server": ("t", 80),
        }
        async with _lifespan(app):
            await bounded(app(scope, receive, send))
        return int(sent[0]["status"])

    assert asyncio.run(go()) == 413
    assert len(pulled) <= 3


@pytest.mark.parametrize("key", ["a%2Fb", "caf%C3%A9", "%E2%9C%93"])
def test_odd_keys_round_trip(key: str) -> None:
    reg = _registry()
    with TestClient(_app(reg)) as c:
        assert c.post(f"/o/{key}/send", json={"type": "ADD"}).status_code in (
            200,
            404,
        )
        r = c.get(f"/o/{key}")
        if r.status_code == 200:
            assert _ctx(reg, unquote(key))["n"] == 1


def test_create_if_missing_false_is_404_everywhere() -> None:
    reg = _registry()
    app = _app(reg, create_if_missing=False)
    with TestClient(app) as c:
        for r in (
            c.get("/o/nope"),
            c.get("/o/nope/events"),
            c.post("/o/nope/send", json={"type": "ADD"}),
            c.post("/o/nope/events/ADD"),
            c.get("/o/nope/stream"),
        ):
            assert r.status_code == 404, (r.request.url, r.text)

    async def ws() -> Dict[str, Any]:
        async with _lifespan(app):
            w = RawWS(app, "/o/nope/ws")
            return await w.open()

    first = asyncio.run(ws())
    assert (first["type"], first.get("code")) == ("websocket.close", 1008)


def test_ws_close_codes_reach_the_client() -> None:
    reg = _registry()
    app = _app(reg)

    async def go() -> List[int]:
        codes = []
        async with _lifespan(app):
            w = RawWS(app, "/o/forbidden/ws")
            m = await w.open()
            codes.append(m.get("code"))
            w2 = RawWS(app, "/o/k/ws")
            assert (await w2.open())["type"] == "websocket.accept"
            await w2.recv_json()
        # lifespan shutdown -> 1001
        while True:
            m2 = await bounded(w2.out.get())
            if m2["type"] == "websocket.close":
                codes.append(m2["code"])
                break
        await w2.close()
        return codes

    assert asyncio.run(go()) == [1008, 1001]


def test_fifty_concurrent_sends_on_sqlite(tmp_path: Any) -> None:
    reg = _registry(SQLiteStore(str(tmp_path / "s.db")))
    app = _app(reg)

    async def go() -> List[int]:
        async with _lifespan(app):
            t = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=t, base_url="http://t", timeout=30
            ) as c:
                rs = await asyncio.gather(
                    *[
                        c.post("/o/k/send", json={"type": "ADD"})
                        for _ in range(50)
                    ]
                )
                final = {"context": _ctx(reg, "k")}
        codes = [r.status_code for r in rs]
        assert final["context"]["n"] == codes.count(200)
        return codes

    codes = asyncio.run(go())
    assert set(codes) <= {200, 409} and 200 in codes


# -----------------------------------------------------------------------------
# 5. exceptions
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("debug", [False, True])
def test_action_error_and_validation_do_not_leak(debug: bool) -> None:
    reg = _registry()
    app = Litestar(
        route_handlers=[create_statechart_controller(reg, "o", path="/o")],
        plugins=[XStatePlugin(reg)],
        logging_config=None,
        debug=debug,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/o/k/send", json={"type": "BOOM"})
        assert "hunter2" not in r.text and "Traceback" not in r.text
        v = c.post("/o/k/send", json={"type": "NOPE", "payload": "zzsecret"})
        assert v.status_code in (400, 422), v.text
        assert "zzsecret" not in v.text and "Traceback" not in v.text


# -----------------------------------------------------------------------------
# 6. parity with FastAPI (#276)
# -----------------------------------------------------------------------------
def _parity_cases() -> List[Any]:
    j = {"content-type": "application/json"}
    return [
        ("unknown", "/o/k/send", b'{"type":"NOPE"}', j),
        ("denied", "/o/k/send", b'{"type":"SECRET"}', j),
        ("not-enabled", "/o/k2/events/LATER", b"", {}),
        ("413", "/o/k/send", b'{"type":"ADD","x":"' + b"y" * 4096 + b'"}', j),
        ("415", "/o/k/send", b'{"type":"ADD"}', {"content-type": "text/x"}),
        ("501", "/o/k/send", b'{"type":"ADD"}', {**j, "idempotency-key": "z"}),
        ("403-key", "/o/forbidden/send", b'{"type":"ADD"}', j),
    ]


def _title(r: Any) -> Optional[str]:
    if not r.headers.get("content-type", "").endswith("json"):
        return None
    return (r.json() or {}).get("title")


def _parity(reg: Any, cases: List[Any], **kw: Any) -> List[Any]:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as FTC

    from src.xstate_statemachine.contrib.fastapi import StatechartRouter

    fa = FastAPI()
    fa.include_router(StatechartRouter(reg, "o", prefix="/o", **kw))
    rows: List[Any] = []
    with TestClient(_app(reg, **kw)) as lc, FTC(fa) as fc:
        for label, path, body, h in cases:
            pair = []
            for c in (lc, fc):
                c.post("/o/k2/send", json={"type": "LATER"})
                pair.append(c.post(path, content=body, headers=h))
            a, b = pair
            rows.append(
                (label, a.status_code, b.status_code, _title(a), _title(b))
            )
    return rows


def test_parity_with_fastapi() -> None:
    """Same requests, same registry: identical status AND problem title."""
    pytest.importorskip("fastapi")
    j = {"content-type": "application/json"}
    idem = {**j, "idempotency-key": "same"}
    rows = _parity(_registry(max_body_bytes=1024), _parity_cases())
    reg2 = _registry(
        max_body_bytes=1024, inbox=MemoryInbox(), principal=lambda c: "p"
    )
    rows += _parity(
        reg2,
        [("duplicate", "/o/k3/send", b'{"type":"ADD"}', idem)],
    )
    rows += _parity(
        _registry(),
        [
            ("404-send", "/o/nope/send", b'{"type":"ADD"}', j),
            ("404-event", "/o/nope/events/ADD", b"", {}),
        ],
        create_if_missing=False,
    )
    diff = [r for r in rows if r[1] != r[2] or r[3] != r[4]]
    assert not diff, diff
    got = {r[0]: r[1] for r in rows}
    assert got["unknown"] == 422 and got["404-send"] == 404
    assert got["duplicate"] == 200 and got["501"] == 501
