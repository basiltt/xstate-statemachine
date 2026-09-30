# src/xstate_statemachine/contrib/starlette/inspector.py
# -----------------------------------------------------------------------------
# 🔎 mount_inspector + WebSocketSink -- the live inspector over WebSocket
#    (#274, B7; the route was reserved by #275)
# -----------------------------------------------------------------------------
# 🔐 An inspector streams every event of every machine the registry runs:
#    a data-exfiltration endpoint by design. So:
#      * it REFUSES to mount unless ``debug=True`` (never in production);
#      * X0.7: a `secrets.token_urlsafe(32)` token compared with
#        `hmac.compare_digest`, presented as a header or the HttpOnly
#        cookie set by the one-time ``GET <path>?token=`` redirect (never a
#        persistent query string on the socket); loopback ``Host`` by
#        default (``allow_remote=True`` to lift it -- the token stays);
#        ``Origin`` checked with the registry's own `origin_allowed`;
#      * context is deny-by-default (``context_allowlist``), exactly as in
#        the core `InspectorPlugin`.
#
# 📡 Wire format: each WebSocket text frame is ONE Stately Inspector
#    protocol message (`@xstate.actor` / `.event` / `.snapshot`) -- the
#    same JSON `@statelyai/inspect`'s `createWebSocketReceiver` parses.
#
# 🏛️ The registry is not forked: the `InspectorPlugin` is appended to
#    `registry.plugins`, which `act()` / `resident()` already attach to
#    every interpreter they build.
# -----------------------------------------------------------------------------
"""`mount_inspector()` (debug-only) and `WebSocketSink`."""

from __future__ import annotations

import asyncio
import hmac
import secrets
import threading
from collections import deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from ...inspect import COOKIE_NAME, InspectorPlugin
from ._http import problem

__all__ = ["mount_inspector", "WebSocketSink"]

WS_POLICY_VIOLATION = 1008
_LOOPBACK = ("127.0.0.1", "localhost", "::1", "testserver")


def _host_name(host: str) -> str:
    if host.startswith("["):
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


class WebSocketSink:
    """Fan protocol messages out to connected WebSocket clients.

    ``send()`` is thread-safe (the sync engine may call it from a timer
    thread); each connection owns an ``asyncio.Queue`` on its own loop.
    New connections replay the last *history* messages first.
    """

    def __init__(
        self, *, token: Optional[str] = None, history: int = 1000
    ) -> None:
        self.token = token or secrets.token_urlsafe(32)
        self._history: Deque[Dict[str, Any]] = deque(maxlen=history)
        self._clients: List[
            Tuple[asyncio.AbstractEventLoop, "asyncio.Queue[Any]"]
        ] = []
        self._lock = threading.Lock()

    def send(self, message: Dict[str, Any]) -> None:
        with self._lock:
            self._history.append(message)
            clients = list(self._clients)
        for loop, q in clients:
            try:
                loop.call_soon_threadsafe(q.put_nowait, message)
            except RuntimeError:  # loop closed -- client is gone
                continue

    @property
    def messages(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def token_ok(self, candidate: Optional[str]) -> bool:
        if not candidate:
            return False
        return hmac.compare_digest(
            candidate.encode("utf-8"), self.token.encode("utf-8")
        )

    def presented_token(self, conn: HTTPConnection) -> Optional[str]:
        auth = conn.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return conn.headers.get("x-xsm-token") or conn.cookies.get(COOKIE_NAME)

    async def serve(self, websocket: WebSocket) -> None:
        """Pump messages to one accepted socket until it disconnects."""
        loop = asyncio.get_running_loop()
        q: "asyncio.Queue[Any]" = asyncio.Queue()
        with self._lock:
            backlog = list(self._history)
            self._clients.append((loop, q))
        try:
            for msg in backlog:
                await websocket.send_json(msg)
            recv = asyncio.ensure_future(websocket.receive())
            while True:
                get = asyncio.ensure_future(q.get())
                done, _ = await asyncio.wait(
                    {get, recv}, return_when=asyncio.FIRST_COMPLETED
                )
                if recv in done:
                    get.cancel()
                    if recv.result().get("type") == "websocket.disconnect":
                        return
                    recv = asyncio.ensure_future(websocket.receive())
                    continue
                await websocket.send_json(get.result())
        except (WebSocketDisconnect, RuntimeError):
            return
        finally:
            with self._lock:
                if (loop, q) in self._clients:
                    self._clients.remove((loop, q))


def mount_inspector(
    app: Any,
    registry: Any,
    path: str = "/_xsm/inspect",
    *,
    debug: bool = False,
    token: Optional[str] = None,
    context_allowlist: Iterable[str] = (),
    include_payloads: bool = False,
    allow_remote: bool = False,
) -> WebSocketSink:
    """Mount the live inspector at *path* -- only when ``debug=True``.

    Routes:
        ``WS  <path>`` -- the protocol stream (token via header/cookie).
        ``GET <path>?token=…`` -- sets the HttpOnly cookie, 303 → *path*.
        ``GET <path>`` -- the recorded backlog as JSON (token required).

    Returns:
        The `WebSocketSink`; read ``.token`` to hand to the developer.

    Raises:
        RuntimeError: ``debug`` is not ``True``.
    """
    if debug is not True:
        raise RuntimeError(
            "mount_inspector() exposes every event and context; it refuses "
            "to mount unless debug=True (never in production)."
        )
    sink = WebSocketSink(token=token)
    registry.plugins.append(
        InspectorPlugin(
            sink,
            context_allowlist=context_allowlist,
            include_payloads=include_payloads,
        )
    )

    def _host_ok(conn: HTTPConnection) -> bool:
        if allow_remote:
            return True
        return _host_name(conn.headers.get("host", "")) in _LOOPBACK

    async def http_view(request: Request) -> Response:
        if not _host_ok(request):
            return problem(421, "Misdirected Request", "loopback only")
        if not registry.origin_allowed(request):
            return problem(403, "Forbidden", "cross-origin request refused")
        once = request.query_params.get("token")
        if once is not None:
            if not sink.token_ok(once):
                return problem(401, "Unauthorized", "inspector token")
            resp = RedirectResponse(path, status_code=303)
            resp.set_cookie(
                COOKIE_NAME,
                sink.token,
                httponly=True,
                samesite="strict",
                path=path,
            )
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Referrer-Policy"] = "no-referrer"
            return resp
        if not sink.token_ok(sink.presented_token(request)):
            return problem(401, "Unauthorized", "inspector token")
        return JSONResponse(
            sink.messages, headers={"Cache-Control": "no-store"}
        )

    async def ws_view(websocket: WebSocket) -> None:
        if (
            not _host_ok(websocket)
            or not registry.origin_allowed(websocket)
            or not sink.token_ok(sink.presented_token(websocket))
        ):
            await websocket.close(code=WS_POLICY_VIOLATION)
            return
        await websocket.accept()
        await sink.serve(websocket)

    app.router.routes.append(Route(path, http_view, methods=["GET"]))
    app.router.routes.append(WebSocketRoute(path, ws_view))
    return sink
