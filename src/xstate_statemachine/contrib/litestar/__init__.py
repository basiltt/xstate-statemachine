# src/xstate_statemachine/contrib/litestar/__init__.py
# -----------------------------------------------------------------------------
# ⭐ [litestar] -- XStatePlugin, Provide() dependency, statechart Controller
# -----------------------------------------------------------------------------
# 🏛️ Litestar speaks ASGI, so the `[starlette]` registry, HTTP mapping and
#    streaming are reused as-is; this package only ADAPTS AT THE EDGE:
#    a Litestar `Request` is viewed as a Starlette `Request` over the same
#    scope/receive, and a Starlette response is converted to a Litestar
#    `Response` / `Stream`. One registry, one set of semantics.
#
# 🔐 Security posture (docs/_guide/security.md): X0.1 authorize required +
#    state-only GET; X0.2 Idempotency-Key scoped to the registry principal;
#    X0.7 JSON-only bounded bodies, problem+json without exception text.
# -----------------------------------------------------------------------------
"""Litestar integration.

Install with ``pip install "xstate-statemachine[litestar]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("litestar", "litestar", "starlette")

from ..starlette import (  # noqa: E402
    StatechartRegistry,
    allow_all,
    problem,
    problem_for_exception,
    receipt_to_status,
)
from ._edge import ReceiptResponse  # noqa: E402
from .controller import create_statechart_controller  # noqa: E402
from .plugin import XStatePlugin, get_interpreter  # noqa: E402

__all__ = [
    "ReceiptResponse",
    "StatechartRegistry",
    "XStatePlugin",
    "allow_all",
    "create_statechart_controller",
    "get_interpreter",
    "problem",
    "problem_for_exception",
    "receipt_to_status",
]
