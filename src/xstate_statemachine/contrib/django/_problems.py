# src/xstate_statemachine/contrib/django/_problems.py
# -----------------------------------------------------------------------------
# 🌐 RFC 9457 problems + receipt bodies for the Django web surfaces
# -----------------------------------------------------------------------------
# 🏛️ Framework-neutral (no DRF / Channels import) so [drf] and [channels]
#    share one table. Status of a RECEIPT is the core ``receipts`` table
#    (#305) -- the same FastAPI / Flask / Starlette answer; this module only
#    adds the mapping for EXCEPTIONS raised around a send.
#
# 🔐 X0.7: a problem carries a fixed title and the exception CLASS name --
#    never ``str(exc)``.
# -----------------------------------------------------------------------------
"""Problems and receipt bodies (internal)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...exceptions import (
    ConflictError,
    InvalidEventError,
    InvalidEventPayloadError,
    LockTimeoutError,
    StoreUnavailableError,
    SnapshotDriftError,
    UnknownEventError,
)
from ...persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
)

__all__ = [
    "IDEMPOTENCY_HEADER",
    "PROBLEM_MEDIA_TYPE",
    "problem_body",
    "problem_for_exception",
    "receipt_fields",
]

IDEMPOTENCY_HEADER = "Idempotency-Key"
PROBLEM_MEDIA_TYPE = "application/problem+json"

_TABLE: Tuple[Tuple[type, int, str], ...] = (
    (IdempotencyMismatchError, 422, "Idempotency key reused"),
    (UnknownEventError, 422, "Unknown event"),
    (InvalidEventPayloadError, 422, "Invalid event payload"),
    (InvalidEventError, 422, "Invalid event"),
    (SnapshotDriftError, 409, "Machine version mismatch"),
    (IdempotencyInFlightError, 409, "Request in flight"),
    (ConflictError, 409, "Conflict"),
    (LockTimeoutError, 409, "Lock timeout"),
    # 🔌 #306 battle: the backend is down, not the request. Retryable.
    (StoreUnavailableError, 503, "Store unavailable"),
)


def problem_body(
    status: int, title: str, detail: Optional[str] = None, **ext: Any
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"type": "about:blank", "title": title}
    body["status"] = status
    if detail is not None:
        body["detail"] = detail
    body.update(ext)
    return body


def problem_for_exception(exc: BaseException) -> Tuple[int, Dict[str, Any]]:
    """``(status, problem)`` -- 500 "Internal Server Error" if unknown."""
    for cls, status, title in _TABLE:
        if isinstance(exc, cls):
            return status, problem_body(
                status, title, error=type(exc).__name__
            )
    return 500, problem_body(
        500, "Internal Server Error", error=type(exc).__name__
    )


def receipt_fields(receipt: Any) -> Dict[str, Any]:
    """The receipt half of a receipt body (FastAPI ``ReceiptModel``)."""
    return {
        "changed": bool(receipt.changed),
        "denied": bool(receipt.denied),
        "deferred": bool(receipt.deferred),
        "duplicate": bool(receipt.duplicate),
        # 🔐 X0.7: the class name only.
        "error": (
            getattr(receipt.error, "type", None)
            or type(receipt.error).__name__
            if receipt.error is not None
            else None
        ),
    }
