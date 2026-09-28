# src/xstate_statemachine/contrib/starlette/inspector.py
# -----------------------------------------------------------------------------
# 🔎 mount_inspector -- dev-only hook; the sink ships with #274 (B7)
# -----------------------------------------------------------------------------
# 🔐 An inspector streams every event and context of every machine: it is a
#    data-exfiltration endpoint by design, so it REFUSES to mount unless the
#    caller says `debug=True` explicitly. Until B7's `WebSocketSink` lands
#    the mounted route answers 501 -- loudly, never an empty success.
# -----------------------------------------------------------------------------
"""`mount_inspector()` (debug-only)."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from ._http import problem

__all__ = ["mount_inspector"]


def mount_inspector(
    app: Any,
    registry: Any,
    path: str = "/_xsm/inspect",
    *,
    debug: bool = False,
) -> None:
    """Mount the live inspector at *path* -- only when ``debug=True``.

    Raises:
        RuntimeError: ``debug`` is not ``True``.
    """
    if debug is not True:
        raise RuntimeError(
            "mount_inspector() exposes every event and context; it refuses "
            "to mount unless debug=True (never in production)."
        )

    async def inspect(request: Request) -> Response:
        return problem(
            501,
            "Not Implemented",
            "inspector sink ships with #274",
        )

    app.router.routes.append(Route(path, inspect, methods=["GET"]))
