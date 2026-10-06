# src/xstate_statemachine/contrib/litestar/_edge.py
# -----------------------------------------------------------------------------
# 🔌 Litestar <-> Starlette adapters (the only framework-specific glue)
# -----------------------------------------------------------------------------
"""Convert requests and responses between Litestar and Starlette."""

from __future__ import annotations

from typing import Any, Dict

from litestar import Response
from litestar.response import Stream
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

__all__ = ["ReceiptResponse", "to_litestar", "to_starlette"]

_DROP = frozenset({"content-type", "content-length"})


def to_starlette(request: Any) -> StarletteRequest:
    """A Starlette view of a Litestar request (same scope and receive).

    The registry's helpers only read headers, path params and -- when no
    payload is passed -- the body stream, so the view is lossless.
    """
    return StarletteRequest(request.scope, request.receive)


def to_litestar(resp: StarletteResponse) -> Any:
    """A Litestar `Response` / `Stream` carrying *resp* unchanged."""
    headers: Dict[str, str] = {
        k: v for k, v in resp.headers.items() if k.lower() not in _DROP
    }
    if isinstance(resp, StreamingResponse):
        return Stream(
            resp.body_iterator,  # type: ignore[arg-type]
            status_code=resp.status_code,
            media_type=resp.media_type,
            headers=headers,
        )
    return Response(
        bytes(resp.body),
        status_code=resp.status_code,
        media_type=resp.media_type,
        headers=headers,
    )


def ReceiptResponse(  # noqa: N802 -- reads as a response class
    interp: Any,
    receipt: Any,
    *,
    context_serializer: Any = None,
    status: Any = None,
) -> Response:
    """A Litestar `Response` for *receipt* (status from `receipt_to_status`).

    🔥 battle #278: `contrib.litestar` re-exported Starlette's
    `ReceiptResponse`, which Litestar cannot return from a handler -- the
    documented ``Provide`` recipe answered 500. This one IS a Litestar
    response; the body and status mapping are the shared ones.
    """
    from ..starlette._http import ReceiptResponse as _starlette

    return to_litestar(
        _starlette(
            interp,
            receipt,
            context_serializer=context_serializer,
            status=status,
        )
    )
