"""#275 test helpers: apps, machines and a bounded raw-ASGI driver."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.xstate_statemachine import MachineLogic, create_machine, stub_logic

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
PAYMENT_CFG = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
TIMEOUT = 2.0


def payment_machine():
    return create_machine(PAYMENT_CFG, logic=stub_logic(PAYMENT_CFG))


def counter_machine():
    def inc(i, ctx, e, a):
        ctx["n"] = ctx["n"] + 1

    return create_machine(
        {
            "id": "counter",
            "initial": "on",
            "context": {"n": 0},
            "states": {"on": {"on": {"INC": {"actions": "inc"}}}},
        },
        logic=MachineLogic(actions={"inc": inc}),
    )


def build_app(registry, name="payment"):
    from starlette.applications import Starlette
    from starlette.routing import Route, WebSocketRoute

    from src.xstate_statemachine.contrib.starlette import (
        transition_stream,
        websocket_endpoint,
    )

    async def send(request):
        return await registry.send_event(
            request,
            name,
            request.path_params["key"],
            request.path_params["event"],
        )

    async def stream(request):
        return await transition_stream(
            registry, name, request.path_params["key"], request
        )

    return Starlette(
        routes=[
            Route("/m/{key}/events/{event}", send, methods=["POST"]),
            Route("/m/{key}/stream", stream),
            WebSocketRoute("/ws/{key}", websocket_endpoint(registry, name)),
            registry.health_route(),
            registry.ready_route(),
        ],
        lifespan=registry.lifespan,
    )


async def bounded(aw, timeout: float = TIMEOUT):
    return await asyncio.wait_for(aw, timeout)


class RawSSE:
    """Drive one GET stream against an ASGI app on the CURRENT loop."""

    def __init__(self, app, path: str, headers=()) -> None:
        self.app = app
        self.path = path
        self.headers = [(k.encode(), v.encode()) for k, v in headers]
        self.out: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self._disconnect = asyncio.Event()
        self._sent_request = False
        self.task: Optional["asyncio.Task[None]"] = None
        self.buf = b""

    async def _receive(self):
        if not self._sent_request:
            self._sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self._disconnect.wait()
        return {"type": "http.disconnect"}

    async def _send(self, msg):
        await self.out.put(msg)

    async def open(self) -> int:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")] + self.headers,
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
        }
        self.task = asyncio.ensure_future(
            self.app(scope, self._receive, self._send)
        )
        start = await bounded(self.out.get())
        assert start["type"] == "http.response.start"
        self.status = start["status"]
        return self.status

    async def next_event(self) -> Tuple[Optional[int], str, Any]:
        while b"\n\n" not in self.buf:
            msg = await bounded(self.out.get())
            self.buf += msg.get("body", b"")
        raw, self.buf = self.buf.split(b"\n\n", 1)
        fields: Dict[str, str] = {}
        for line in raw.decode().splitlines():
            if line.startswith(":"):
                return None, "comment", line
            k, _, v = line.partition(": ")
            fields[k] = v
        seq = int(fields["id"]) if "id" in fields else None
        return seq, fields.get("event", ""), json.loads(fields["data"])

    async def body(self) -> bytes:
        chunks = []
        while True:
            msg = await bounded(self.out.get())
            chunks.append(msg.get("body", b""))
            if not msg.get("more_body"):
                return b"".join(chunks)

    async def close(self) -> None:
        self._disconnect.set()
        if self.task is not None:
            await bounded(self.task)


class RawWS:
    """Drive one WebSocket session against an ASGI app on this loop."""

    def __init__(self, app, path: str, headers=()) -> None:
        self.app = app
        self.path = path
        self.headers = [(k.encode(), v.encode()) for k, v in headers]
        self.inbox: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.out: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.task: Optional["asyncio.Task[None]"] = None

    async def open(self) -> Dict[str, Any]:
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")] + self.headers,
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
            "subprotocols": [],
        }
        await self.inbox.put({"type": "websocket.connect"})
        self.task = asyncio.ensure_future(
            self.app(scope, self.inbox.get, self.out.put)
        )
        return await bounded(self.out.get())

    async def recv_json(self) -> Any:
        msg = await bounded(self.out.get())
        assert msg["type"] == "websocket.send", msg
        return json.loads(msg["text"])

    async def send_json(self, data: Any) -> None:
        await self.inbox.put(
            {"type": "websocket.receive", "text": json.dumps(data)}
        )

    async def close(self) -> None:
        await self.inbox.put({"type": "websocket.disconnect", "code": 1000})
        if self.task is not None:
            await bounded(self.task)


def events_of(msgs: List[Any], kind: str) -> List[Any]:
    return [m for m in msgs if m.get("kind") == kind]
