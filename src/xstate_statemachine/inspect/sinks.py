# src/xstate_statemachine/inspect/sinks.py
# -----------------------------------------------------------------------------
# 🚰 Inspector sinks -- where protocol messages go (stdlib only)
# -----------------------------------------------------------------------------
#   MemorySink      a list; tests and in-process tooling
#   JsonLinesSink   one message per line; created 0600 (X0.7); replayable
#   SseSink         `http.server` on loopback: `/` (page), `/app.js`,
#                   `/events` (Server-Sent Events), `/messages` (JSON)
#
# 🔐 X0.7 web hardening for `SseSink` (it streams every event and whatever
#    context you allow-listed -- treat it as a data-exfiltration endpoint):
#      * binds 127.0.0.1 by default; a non-loopback host REQUIRES an
#        explicit token (constructor refuses otherwise);
#      * a `secrets.token_urlsafe(32)` token, compared with
#        `hmac.compare_digest`; accepted as `?token=` ONLY on the first page
#        load, which answers 303 + an HttpOnly SameSite=Strict cookie so the
#        token does not stay in the address bar / history / Referer; API
#        calls use the cookie or `Authorization: Bearer` / `X-XSM-Token`;
#      * loopback binds check `Host` (DNS rebinding) and every request with
#        an `Origin` must be same-origin (or allow-listed);
#      * a strict CSP on the page; no inline script.
# -----------------------------------------------------------------------------
"""Sinks for the live inspector."""

from __future__ import annotations

import hmac
import json
import os
import queue
import secrets
import threading
from collections import deque
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Iterator, List, Optional, Union
from urllib.parse import parse_qs, urlsplit

from ._page import APP_JS, INDEX_HTML

__all__ = [
    "MemorySink",
    "JsonLinesSink",
    "SseSink",
    "read_jsonl",
    "LOOPBACK_HOSTS",
    "COOKIE_NAME",
]

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
COOKIE_NAME = "xsm_inspect"
_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' "
    "'unsafe-inline'; connect-src 'self'; img-src 'self' data:; "
    "frame-src https://stately.ai; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)


class MemorySink:
    """Collects messages in ``messages``."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def send(self, message: Dict[str, Any]) -> None:
        with self._lock:
            self.messages.append(message)


class JsonLinesSink:
    """Append each message as one JSON line to *path*.

    The file is created with mode ``0o600`` (owner read/write only) --
    it holds every event the machine saw. An existing file is appended to
    and its mode is left alone.
    """

    def __init__(self, path: Union[str, "os.PathLike[str]"]) -> None:
        self.path = Path(path)
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(str(self.path), flags, 0o600)
        self._fh = os.fdopen(fd, "a", encoding="utf-8", newline="\n")
        self._lock = threading.Lock()

    def send(self, message: Dict[str, Any]) -> None:
        line = json.dumps(message, default=str, separators=(",", ":"))
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()

    def close(self) -> None:
        with self._lock:
            if not self._fh.closed:
                self._fh.close()

    def __enter__(self) -> "JsonLinesSink":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def read_jsonl(path: Union[str, "os.PathLike[str]"]) -> Iterator[Dict]:
    """Yield the messages of a `JsonLinesSink` recording (blank lines and
    non-object lines are skipped)."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _is_loopback(host: str) -> bool:
    return host in LOOPBACK_HOSTS or host.startswith("127.")


class SseSink:
    """Serve messages over Server-Sent Events on a stdlib HTTP server.

    Args:
        host: Bind address; ``127.0.0.1`` by default.
        port: ``0`` picks a free port (read it back from `port`).
        token: Access token. Generated when omitted -- but a non-loopback
            *host* requires you to pass one explicitly.
        allowed_origins: Extra ``Origin`` values accepted besides
            same-origin (e.g. a dev UI on another port).
        history: How many past messages a newly connected client replays.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        *,
        token: Optional[str] = None,
        allowed_origins: Iterable[str] = (),
        history: int = 1000,
    ) -> None:
        if not _is_loopback(host) and not token:
            raise ValueError(
                f"refusing to serve the inspector on non-loopback host "
                f"{host!r} without an explicit token (X0.7)"
            )
        self.host = host
        self.token = token or secrets.token_urlsafe(32)
        self.allowed_origins = frozenset(allowed_origins)
        self._history: Deque[Dict[str, Any]] = deque(maxlen=history)
        self._clients: List["queue.Queue[Optional[str]]"] = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer((host, port), self._handler())
        self._server.daemon_threads = True
        self.port: int = self._server.server_address[1]
        self._thread: Optional[threading.Thread] = None
        self._seq = 0

    # -- lifecycle --------------------------------------------------------
    def start(self) -> "SseSink":
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="xsm-inspector-sse",
                daemon=True,
            )
            self._thread.start()
        return self

    def close(self) -> None:
        with self._lock:
            clients, self._clients = self._clients, []
        for q in clients:
            q.put(None)
        if self._thread is not None:
            self._server.shutdown()
            self._thread.join(timeout=5)
            self._thread = None
        self._server.server_close()

    def __enter__(self) -> "SseSink":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def url(self) -> str:
        """The first-load URL (carries the token once; see module notes)."""
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}/?token={self.token}"

    # -- sink -------------------------------------------------------------
    def send(self, message: Dict[str, Any]) -> None:
        with self._lock:
            self._seq += 1
            self._history.append(message)
            frame = (
                f"id: {self._seq}\n"
                f"data: {json.dumps(message, default=str)}\n\n"
            )
            clients = list(self._clients)
        for q in clients:
            q.put(frame)

    @property
    def messages(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    # -- security checks --------------------------------------------------
    def token_ok(self, candidate: Optional[str]) -> bool:
        if not candidate:
            return False
        return hmac.compare_digest(
            candidate.encode("utf-8"), self.token.encode("utf-8")
        )

    def host_ok(self, host_header: Optional[str]) -> bool:
        if not _is_loopback(self.host):
            return True  # the token is the control on a public bind
        if not host_header:
            return False
        name = (
            host_header.rsplit(":", 1)[0]
            if "]" not in host_header
            else (host_header.split("]")[0].lstrip("["))
        )
        return _is_loopback(name)

    def origin_ok(self, origin: Optional[str], host: Optional[str]) -> bool:
        if origin is None:
            return True  # non-browser client (curl, http.client)
        if origin in self.allowed_origins:
            return True
        return bool(host) and origin == f"http://{host}"

    # -- HTTP -------------------------------------------------------------
    def _handler(self) -> type:
        sink = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "xsm-inspector"
            sys_version = ""

            def log_message(self, fmt: str, *args: Any) -> None:
                return  # silence the default stderr access log

            def _deny(self, code: int, text: str) -> None:
                body = text.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _presented_token(self) -> Optional[str]:
                auth = self.headers.get("Authorization", "")
                if auth.lower().startswith("bearer "):
                    return auth[7:].strip()
                hdr = self.headers.get("X-XSM-Token")
                if hdr:
                    return hdr.strip()
                raw = self.headers.get("Cookie")
                if raw:
                    jar: SimpleCookie = SimpleCookie()
                    try:
                        jar.load(raw)
                    except Exception:  # noqa: BLE001 -- bad cookie = none
                        return None
                    if COOKIE_NAME in jar:
                        return jar[COOKIE_NAME].value
                return None

            def do_GET(self) -> None:  # noqa: N802 -- stdlib name
                host = self.headers.get("Host")
                if not sink.host_ok(host):
                    return self._deny(421, "misdirected request (Host)")
                if not sink.origin_ok(self.headers.get("Origin"), host):
                    return self._deny(403, "cross-origin request refused")
                parts = urlsplit(self.path)
                query = parse_qs(parts.query)
                if parts.path == "/" and "token" in query:
                    return self._first_load(query["token"][0])
                if not sink.token_ok(self._presented_token()):
                    return self._deny(401, "inspector token required")
                if parts.path == "/":
                    return self._static(INDEX_HTML, "text/html")
                if parts.path == "/app.js":
                    return self._static(APP_JS, "text/javascript")
                if parts.path == "/messages":
                    body = json.dumps(sink.messages, default=str).encode()
                    return self._static(body, "application/json")
                if parts.path == "/events":
                    return self._stream()
                return self._deny(404, "not found")

            def _first_load(self, token: str) -> None:
                if not sink.token_ok(token):
                    return self._deny(401, "inspector token required")
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/")
                self.send_header(
                    "Set-Cookie",
                    f"{COOKIE_NAME}={sink.token}; HttpOnly; "
                    "SameSite=Strict; Path=/",
                )
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _static(self, body: bytes, ctype: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Security-Policy", _CSP)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _stream(self) -> None:
                q: "queue.Queue[Optional[str]]" = queue.Queue()
                with sink._lock:
                    backlog = list(sink._history)
                    sink._clients.append(q)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                try:
                    for msg in backlog:
                        self.wfile.write(
                            f"data: {json.dumps(msg, default=str)}\n\n".encode()
                        )
                    self.wfile.flush()
                    while True:
                        try:
                            frame = q.get(timeout=15)
                        except queue.Empty:
                            frame = ": keep-alive\n\n"
                        if frame is None:
                            return
                        self.wfile.write(frame.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionError, OSError):
                    return
                finally:
                    with sink._lock:
                        if q in sink._clients:
                            sink._clients.remove(q)

        return Handler
