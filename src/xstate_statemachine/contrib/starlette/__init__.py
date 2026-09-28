# src/xstate_statemachine/contrib/starlette/__init__.py
# -----------------------------------------------------------------------------
# 🌐 [starlette] -- registry, Receipt → HTTP, Idempotency-Key, SSE/WebSocket
# -----------------------------------------------------------------------------
# 🏛️ FastAPI and Litestar are ASGI/Starlette-shaped, so the registry, HTTP
#    semantics and streaming are built ONCE here, framework-neutral;
#    `[fastapi]` (#276) and `[litestar]` (#278) add only their idioms.
#
# 📝 Everything builds on core seams that already exist:
#      * `persistence.apersisted` (#260) -- create → act → persist → discard
#      * `IdempotencyPlugin` + inboxes (#261) -- principal-scoped dedup
#      * `DueTimerScanner` (#264) -- persisted `after` deadlines
#      * `Receipt` (#39/#153/#261) -- the per-event outcome → HTTP status
#
# 🔐 Security posture (docs/_guide/security.md): X0.1 authorize required,
#    state-only bodies; X0.2 principal-scoped Idempotency-Key; X0.7 JSON
#    only, Origin/Host checks, problem+json without exception text;
#    X0.11/12 bounded residents, connections and shutdown drain.
# -----------------------------------------------------------------------------
"""Starlette integration.

Install with ``pip install "xstate-statemachine[starlette]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("starlette", "starlette")

from ._http import (  # noqa: E402
    BadRequestError,
    ForbiddenError,
    HTTPProblemError,
    PayloadTooLargeError,
    ReceiptResponse,
    UnsupportedMediaTypeError,
    idempotency_key_from,
    json_body,
    problem,
    problem_for_exception,
    receipt_body,
    receipt_to_status,
    status_for_exception,
)
from .inspector import mount_inspector  # noqa: E402
from .registry import StatechartRegistry, allow_all  # noqa: E402
from .streaming import transition_stream, websocket_endpoint  # noqa: E402

__all__ = [
    "BadRequestError",
    "ForbiddenError",
    "HTTPProblemError",
    "PayloadTooLargeError",
    "ReceiptResponse",
    "StatechartRegistry",
    "UnsupportedMediaTypeError",
    "allow_all",
    "idempotency_key_from",
    "json_body",
    "mount_inspector",
    "problem",
    "problem_for_exception",
    "receipt_body",
    "receipt_to_status",
    "status_for_exception",
    "transition_stream",
    "websocket_endpoint",
]
