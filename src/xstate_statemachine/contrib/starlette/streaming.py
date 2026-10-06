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
from typing import Any, AsyncIterator, Dict, List, Optional, Type

from starlette.endpoints import WebSocketEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.websockets import WebSocket

from ._fanout import CLOSED, TimerPublisher
from ._http import (
    ForbiddenError,
    problem,
    problem_for_exception,
    receipt_body,
    refuse_reserved_send_keys,
)

logger = logging.getLogger(__name__)

__all__ = ["transition_stream", "websocket_endpoint"]

WS_GOING_AWAY = 1001
WS_POLICY_VIOLATION = 1008
WS_MESSAGE_TOO_BIG = 1009
WS_INTERNAL_ERROR = 1011
WS_TRY_AGAIN_LATER = 1013
_BAD_FRAME = object()
_TOO_BIG = object()


def _attach_timer_fanout(registry: Any) -> None:
    """Make scanner-fired ``after`` transitions reach this process' streams.

    🔥 battle #275: the scanner saves through `persisted()` in a thread and
    never through `act()`, so streams missed every timer transition. The
    publisher goes on the SCANNER's own plugin list (a copy -- `act()`
    already publishes its own receipts, never twice). Idempotent; a
    restarted scanner gets a fresh one.
    """
    scanner = getattr(registry, "scanner", None)
    if scanner is None:
        return
    if any(isinstance(p, TimerPublisher) for p in scanner.plugins):
        return

    def body_of(interp: Any, receipt: Any, name: str) -> Dict[str, Any]:
        reg = registry._reg(name)
        return receipt_body(
            interp, receipt, context_serializer=reg.context_serializer
        )

    scanner.plugins.append(
        TimerPublisher(
            registry.subscribers, asyncio.get_running_loop(), body_of
        )
    )


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
    if registry.draining:
        # 🔥 battle #275: a server in shutdown answered 429 ("too many
        #    connections") -- a client would back off and retry THIS
        #    instance; 503 tells the balancer to go elsewhere.
        return problem(503, "Shutting down")
    if not registry.try_open_connection(name, key):
        return problem(429, "Too many connections for this instance")
    _attach_timer_fanout(registry)
    sub = registry.subscribers.subscribe(name, str(key))
    seq0 = registry.subscribers.seq(name, str(key))
    released: List[bool] = []
    watcher: List["asyncio.Task[None]"] = []

    def release() -> None:
        # 🔥 battle #275: idempotent; runs from the generator's `finally`
        #    AND from the response's -- under ASGI spec >= 2.4 Starlette
        #    raises `ClientDisconnect` out of a failed `send` without ever
        #    closing the generator, so the slot and the subscriber leaked
        #    until GC (`max_connections_per_key` exhausted by dead clients).
        for t in watcher:
            t.cancel()
        if released:
            return
        released.append(True)
        registry.subscribers.unsubscribe(sub)
        registry.close_connection(name, key)

    async def watch_disconnect() -> None:
        # 📡 Spec >= 2.4: nobody else reads `receive()`, so a client that
        #    went away while frames flow was only noticed at the next IDLE
        #    heartbeat (never, under steady traffic). Wake the pump now.
        while (await request.receive())["type"] != "http.disconnect":
            pass
        _offer_closed(sub)

    async def body() -> AsyncIterator[bytes]:
        try:
            if _owns_receive(request):
                watcher.append(asyncio.ensure_future(watch_disconnect()))
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
                try:
                    frame = _sse("transition", data, seq)
                except (TypeError, ValueError):
                    # 🔥 battle #275: a non-JSON body (a `context_serializer`
                    #    returning a datetime ...) killed the stream with a
                    #    bare traceback. Log it and end the stream; the
                    #    client reconnects to a fresh snapshot.
                    logger.exception("📡 SSE frame for %r not JSON", key)
                    return
                yield frame
        finally:
            release()

    return _SSEResponse(
        body(),
        release,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def _owns_receive(request: Request) -> bool:
    """Starlette listens for ``http.disconnect`` itself below ASGI 2.4."""
    raw = str(request.scope.get("asgi", {}).get("spec_version", "2.0"))
    try:
        return tuple(int(p) for p in raw.split(".")[:2]) >= (2, 4)
    except ValueError:
        return False


def _offer_closed(sub: Any) -> None:
    try:
        sub.queue.put_nowait(CLOSED)
    except asyncio.QueueFull:
        pass  # already cut by the fan-out: CLOSED is queued


class _SSEResponse(StreamingResponse):
    def __init__(self, content: Any, release: Any, **kw: Any) -> None:
        super().__init__(content, **kw)
        self._release = release

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release()
            aclose = getattr(self.body_iterator, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:  # noqa: BLE001 -- already torn down
                    pass


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
            except Exception:  # noqa: BLE001 -- never leaked to the peer
                logger.exception("📡 websocket connect failed for %r", key)
                await websocket.close(code=WS_INTERNAL_ERROR)
                return
            if registry.draining:
                # 🔥 battle #275: was 1013 "try again later" -- this
                #    server is going away; 1001 sends the client elsewhere.
                await websocket.close(code=WS_GOING_AWAY)
                return
            if not registry.try_open_connection(name, key):
                await websocket.close(code=WS_TRY_AGAIN_LATER)
                return
            self._opened = True
            try:
                await websocket.accept()
                _attach_timer_fanout(registry)
                self._sub = registry.subscribers.subscribe(name, key)
                await websocket.send_json({"kind": "snapshot", **snapshot})
            except BaseException:
                # 🔥 battle #275: Starlette calls `on_disconnect` only when
                #    `on_connect` RETURNS; a peer gone during accept/the
                #    snapshot leaked its `max_connections_per_key` slot.
                await self.on_disconnect(websocket, WS_INTERNAL_ERROR)
                raise
            self._pump = asyncio.ensure_future(self._push(websocket))

        async def decode(self, websocket: WebSocket, message: Any) -> Any:
            # 🔥 battle #275: Starlette's json decoding closed the socket
            #    (1003) and raised on a non-JSON text frame, and a
            #    non-UTF-8 binary frame crashed `dispatch` outright. A bad
            #    frame is an error frame; the session survives.
            raw = message.get("text")
            if raw is None:
                raw = message.get("bytes") or b""
            if len(raw) > registry.max_body_bytes:
                return _TOO_BIG
            try:
                return json.loads(raw)
            except ValueError:  # JSONDecodeError + UnicodeDecodeError
                return _BAD_FRAME

        async def _reply(self, websocket: WebSocket, frame: Any) -> None:
            try:
                await websocket.send_json(frame)
            except Exception:  # noqa: BLE001 -- peer already gone
                logger.debug("📡 websocket reply dropped (peer gone)")

        async def _push(self, websocket: WebSocket) -> None:
            key = self._key
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
                        # 1001 on shutdown; 1013 when cut for lagging.
                        await websocket.close(
                            code=(
                                WS_GOING_AWAY
                                if registry.draining
                                else WS_TRY_AGAIN_LATER
                            )
                        )
                        return
                    seq, data = item
                    await websocket.send_json(
                        {"kind": "transition", "seq": seq, **data}
                    )
            except asyncio.CancelledError:
                raise
            except (TypeError, ValueError):
                # 🔥 battle #275: an unserialisable frame ended the pump
                #    SILENTLY -- the socket stayed open, receipts still
                #    flowed, pushes never came again. Close it loudly.
                logger.exception("📡 websocket frame for %r not JSON", key)
                try:
                    await websocket.close(code=WS_INTERNAL_ERROR)
                except Exception:  # noqa: BLE001 -- already closed
                    pass
            except Exception:  # noqa: BLE001 -- socket gone
                return

        async def on_receive(self, websocket: WebSocket, data: Any) -> None:
            if data is _TOO_BIG:
                await websocket.close(code=WS_MESSAGE_TOO_BIG)
                return
            if data is _BAD_FRAME:
                await self._reply(
                    websocket,
                    {
                        "kind": "error",
                        "status": 400,
                        "title": "Malformed JSON",
                    },
                )
                return
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("type"), str)
                or not isinstance(data.get("payload", {}), dict)
            ):
                await self._reply(
                    websocket,
                    {"kind": "error", "status": 422, "title": "Bad message"},
                )
                return
            etype = data["type"]
            try:
                await registry.authorize(websocket, name, self._key, etype)
                # 🔐 After authorize (review L1): an unauthorised client
                #    must see 1008, not a 422 that confirms the route.
                refuse_reserved_send_keys(data.get("payload", {}))
                principal = registry._principal_of(websocket)
                async with registry.act(
                    name, self._key, principal=principal
                ) as interp:
                    receipt = await interp.send(
                        etype, wait=True, **data.get("payload", {})
                    )
                    if not receipt.duplicate:  # ⏳ #263 battle, see `act`
                        await interp.await_settled(registry.settle_timeout)
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
                await self._reply(
                    websocket,
                    {"kind": "error", **json.loads(bytes(resp.body))},
                )
                return
            await self._reply(websocket, {"kind": "receipt", **body})

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
