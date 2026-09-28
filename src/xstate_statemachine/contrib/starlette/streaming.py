# src/xstate_statemachine/contrib/starlette/streaming.py
# -----------------------------------------------------------------------------
# 📡 SSE `transition_stream` + WebSocket endpoint
# -----------------------------------------------------------------------------
# 🏛️ Both are views over the registry's in-process `_Subscribers` fan-out:
#    `act()` publishes after a committed save. Neither holds a resident, so
#    a disconnect can never orphan an actor (X0.12); WebSocket sends go
#    through `act()` like any HTTP request.
#
# 🔐 X0.7: `Origin` must be same-origin (vs `Host`) or allow-listed; the
#    authorizer runs on connect (event=None) and per WebSocket event.
#    Refusals: HTTP 403 problem / WebSocket close 1008.
# -----------------------------------------------------------------------------
"""`transition_stream()` (SSE) and `websocket_endpoint()` (WebSocket)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional, Type

from starlette.endpoints import WebSocketEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.websockets import WebSocket

from ._fanout import CLOSED
from ._http import ForbiddenError, problem, problem_for_exception, receipt_body

logger = logging.getLogger(__name__)

__all__ = ["transition_stream", "websocket_endpoint"]

WS_POLICY_VIOLATION = 1008
WS_TRY_AGAIN_LATER = 1013


def _sse(event: str, data: Dict[str, Any], seq: Optional[int] = None) -> bytes:
    lines = []
    if seq is not None:
        lines.append(f"id: {seq}")
    lines.append(f"event: {event}")
    lines.append("data: " + json.dumps(data, separators=(",", ":")))
    return ("\n".join(lines) + "\n\n").encode("utf-8")


async def transition_stream(
    registry: Any, name: str, key: str, request: Request
) -> Response:
    """``text/event-stream`` of one instance.

    Emits ``event: snapshot`` on connect, then ``event: transition`` once
    per CHANGED receipt committed by `registry.act()` in THIS process,
    ``id:`` = a per-instance increasing sequence. A ``: heartbeat``
    comment every `registry.heartbeat_s`. Refusals are problem responses:
    403 (origin / authorize), 429 (``max_connections_per_key``).
    """
    if not registry.origin_allowed(request):
        return problem(403, "Origin not allowed")
    try:
        await registry.authorize(request, name, key, None)
        snapshot = await registry.peek(name, key)
    except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
        return problem_for_exception(exc)
    if not registry.try_open_connection(name, key):
        return problem(429, "Too many connections for this instance")
    sub = registry.subscribers.subscribe(name, str(key))
    seq0 = registry.subscribers.seq(name, str(key))

    async def body() -> AsyncIterator[bytes]:
        try:
            yield _sse("snapshot", snapshot, seq0)
            while True:
                try:
                    item = await asyncio.wait_for(
                        sub.queue.get(), timeout=registry.heartbeat_s
                    )
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        return
                    yield b": heartbeat\n\n"
                    continue
                if item is CLOSED:
                    return
                seq, data = item
                yield _sse("transition", data, seq)
        finally:
            registry.subscribers.unsubscribe(sub)
            registry.close_connection(name, key)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def websocket_endpoint(
    registry: Any, name: str, *, key_param: str = "key"
) -> Type[WebSocketEndpoint]:
    """A `WebSocketEndpoint` subclass for machine *name*.

    Mount with ``WebSocketRoute("/ws/{key}", websocket_endpoint(reg, "p"))``.
    Protocol: on connect the server sends ``{"kind": "snapshot", ...}``;
    the client sends ``{"type": "EVENT", "payload": {...}}`` and gets
    ``{"kind": "receipt", ...}`` (or ``{"kind": "error", "status", ...}``);
    committed transitions from any client arrive as
    ``{"kind": "transition", "seq": n, ...}``. A ``{"kind": "ping"}`` is
    sent every `registry.heartbeat_s`. Close codes: 1008 origin /
    authorize refused, 1013 too many connections.
    """

    class StatechartWebSocketEndpoint(WebSocketEndpoint):
        encoding = "json"

        async def on_connect(self, websocket: WebSocket) -> None:
            key = str(websocket.path_params[key_param])
            self._key = key
            self._sub: Any = None
            self._pump: Optional["asyncio.Task[None]"] = None
            self._opened = False
            if not registry.origin_allowed(websocket):
                await websocket.close(code=WS_POLICY_VIOLATION)
                return
            try:
                await registry.authorize(websocket, name, key, None)
                snapshot = await registry.peek(name, key)
            except ForbiddenError:
                await websocket.close(code=WS_POLICY_VIOLATION)
                return
            if not registry.try_open_connection(name, key):
                await websocket.close(code=WS_TRY_AGAIN_LATER)
                return
            self._opened = True
            await websocket.accept()
            self._sub = registry.subscribers.subscribe(name, key)
            await websocket.send_json({"kind": "snapshot", **snapshot})
            self._pump = asyncio.ensure_future(self._push(websocket))

        async def _push(self, websocket: WebSocket) -> None:
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(
                            self._sub.queue.get(), timeout=registry.heartbeat_s
                        )
                    except asyncio.TimeoutError:
                        await websocket.send_json({"kind": "ping"})
                        continue
                    if item is CLOSED:
                        await websocket.close()
                        return
                    seq, data = item
                    await websocket.send_json(
                        {"kind": "transition", "seq": seq, **data}
                    )
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 -- socket gone
                return

        async def on_receive(self, websocket: WebSocket, data: Any) -> None:
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("type"), str)
                or not isinstance(data.get("payload", {}), dict)
            ):
                await websocket.send_json(
                    {"kind": "error", "status": 422, "title": "Bad message"}
                )
                return
            etype = data["type"]
            try:
                await registry.authorize(websocket, name, self._key, etype)
                principal = registry._principal_of(websocket)
                async with registry.act(
                    name, self._key, principal=principal
                ) as interp:
                    receipt = await interp.send(
                        etype, wait=True, **data.get("payload", {})
                    )
                    body = receipt_body(
                        interp,
                        receipt,
                        context_serializer=getattr(
                            interp, "_xsm_context_serializer", None
                        ),
                    )
            except ForbiddenError:
                await websocket.close(code=WS_POLICY_VIOLATION)
                return
            except Exception as exc:  # noqa: BLE001 -- mapped, not leaked
                resp = problem_for_exception(exc)
                await websocket.send_json(
                    {"kind": "error", **json.loads(bytes(resp.body))}
                )
                return
            await websocket.send_json({"kind": "receipt", **body})

        async def on_disconnect(
            self, websocket: WebSocket, close_code: int
        ) -> None:
            if self._pump is not None:
                self._pump.cancel()
                try:
                    await self._pump
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
                self._pump = None
            if self._sub is not None:
                registry.subscribers.unsubscribe(self._sub)
                self._sub = None
            if self._opened:
                registry.close_connection(name, self._key)
                self._opened = False

    StatechartWebSocketEndpoint.__name__ = f"StatechartWebSocket_{name}"
    return StatechartWebSocketEndpoint
