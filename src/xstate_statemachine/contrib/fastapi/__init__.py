# src/xstate_statemachine/contrib/fastapi/__init__.py
# -----------------------------------------------------------------------------
# ⚡ [fastapi] -- Depends(get_interpreter), StatechartRouter, OpenAPI
# -----------------------------------------------------------------------------
# 🏛️ A chart already declares its public surface -- events, payload models,
#    states -- so the REST API and its OpenAPI document are GENERATED from
#    it. Everything stateful is `[starlette]`'s `StatechartRegistry`
#    (re-exported here): FastAPI adds typed bodies, `Depends` and the
#    schema, never a second registry or a second HTTP mapping.
#
# 🔐 Security posture (docs/_guide/security.md): X0.1 authorize required +
#    state-only GET; X0.2 Idempotency-Key scoped to the `actor` dependency's
#    principal (never the body); X0.7 JSON-only bounded bodies,
#    problem+json without exception text.
# -----------------------------------------------------------------------------
"""FastAPI integration.

Install with ``pip install "xstate-statemachine[fastapi]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("fastapi", "fastapi", "starlette", "pydantic")

from ..starlette import (  # noqa: E402
    IdempotencyNotConfiguredError,
    ReceiptResponse,
    StatechartRegistry,
    allow_all,
    problem,
    problem_for_exception,
    receipt_to_status,
)
from ._models import Problem, ReceiptModel, StateModel  # noqa: E402
from .app import compose_lifespan, instrument_app  # noqa: E402
from .router import (  # noqa: E402
    StatechartRouter,
    bounded_route_class,
    get_interpreter,
)

__all__ = [
    "IdempotencyNotConfiguredError",
    "Problem",
    "ReceiptModel",
    "ReceiptResponse",
    "StateModel",
    "StatechartRegistry",
    "StatechartRouter",
    "allow_all",
    "bounded_route_class",
    "compose_lifespan",
    "get_interpreter",
    "instrument_app",
    "problem",
    "problem_for_exception",
    "receipt_to_status",
]
