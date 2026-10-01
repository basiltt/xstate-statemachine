# src/xstate_statemachine/contrib/starlette/_http.py
# -----------------------------------------------------------------------------
# 🌐 HTTP semantics: Receipt -> status, problem+json, JSON-only bodies
# -----------------------------------------------------------------------------
# 🏛️ Framework-neutral on purpose: FastAPI (#276) and Litestar (#278) reuse
#    these helpers, so nothing here knows about routing.
#
# 🔐 X0.7: problem responses carry a TITLE and the exception CLASS name,
#    never `str(exc)` -- messages can echo keys, payload fragments or file
#    paths. Bodies must be `application/json` and bounded in size.
# -----------------------------------------------------------------------------
"""Receipt/exception → HTTP mapping and request-body helpers."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse

from ...events import Receipt
from ...exceptions import (
    ConflictError,
    InterpreterStoppedError,
    InvalidEventError,
    InvalidEventPayloadError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotDriftError,
    UnknownEventError,
    XStateMachineError,
)
from ...persistence.helpers import KeyNotFoundError
from ...persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
)
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES
from ...receipts import receipt_to_status as core_receipt_to_status

__all__ = [
    "BadRequestError",
    "ForbiddenError",
    "HTTPProblemError",
    "IDEMPOTENCY_HEADER",
    "PayloadTooLargeError",
    "RESERVED_SEND_KEYS",
    "ReservedKeyError",
    "ReceiptResponse",
    "UnsupportedMediaTypeError",
    "idempotency_key_from",
    "json_body",
    "problem",
    "problem_for_exception",
    "receipt_body",
    "refuse_reserved_send_keys",
    "receipt_to_status",
    "status_for_exception",
]

IDEMPOTENCY_HEADER = "Idempotency-Key"
PROBLEM_MEDIA_TYPE = "application/problem+json"
#: Internal event families never offered to a client as "available".
_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")


# -----------------------------------------------------------------------------
# 🔥 Request-level errors (each knows its status)
# -----------------------------------------------------------------------------
class HTTPProblemError(XStateMachineError):
    """An error that already knows its HTTP status and public title."""

    status = 400
    title = "Bad Request"

    def __init__(self, title: Optional[str] = None) -> None:
        if title is not None:
            self.title = title
        super().__init__(self.title)


class BadRequestError(HTTPProblemError):
    status = 400
    title = "Bad Request"


class ForbiddenError(HTTPProblemError):
    """`authorize` returned a falsy value (X0.1)."""

    status = 403
    title = "Forbidden"


class PayloadTooLargeError(HTTPProblemError):
    status = 413
    title = "Payload Too Large"


class UnsupportedMediaTypeError(HTTPProblemError):
    status = 415
    title = "Unsupported Media Type"


class UnprocessableBodyError(HTTPProblemError):
    status = 422
    title = "Request body must be a JSON object"


class ReservedKeyError(HTTPProblemError):
    """A client body carried a `send()` OPTION name (X0.7).

    🔐 Adapters splat the body into ``send(etype, wait=True, **payload)``:
    ``{"priority": true}`` would jump the queue and ``{"wait": false}``
    crashed the call into a 500. Client data never sets an engine option.
    """

    status = 422
    title = "Reserved key in payload"


#: `send()` keyword options a client body may never carry.
RESERVED_SEND_KEYS = ("wait", "priority")


def refuse_reserved_send_keys(payload: Dict[str, Any]) -> None:
    """Raise `ReservedKeyError` if *payload* names a `send()` option."""
    if any(k in payload for k in RESERVED_SEND_KEYS):
        raise ReservedKeyError()


# -----------------------------------------------------------------------------
# 📜 RFC 9457 problem details
# -----------------------------------------------------------------------------
def problem(
    status: int, title: str, detail: Optional[str] = None, **ext: Any
) -> JSONResponse:
    """An RFC 9457 ``application/problem+json`` response.

    Args:
        status: HTTP status.
        title: Short, fixed, human-readable summary. Never exception text.
        detail: Optional caller-authored explanation.
        **ext: Extension members (e.g. ``machine_version``).
    """
    body: Dict[str, Any] = {"type": "about:blank", "title": title}
    body["status"] = status
    if detail is not None:
        body["detail"] = detail
    body.update(ext)
    return JSONResponse(
        body, status_code=status, media_type=PROBLEM_MEDIA_TYPE
    )


_STATUS_TABLE = (
    (IdempotencyMismatchError, 422, "Idempotency key reused"),
    (UnknownEventError, 422, "Unknown event"),
    (InvalidEventPayloadError, 422, "Invalid event payload"),
    (InvalidEventError, 422, "Invalid event"),
    (SnapshotDriftError, 409, "Machine version mismatch"),
    (IdempotencyInFlightError, 409, "Request in flight"),
    (ConflictError, 409, "Conflict"),
    # 🏁 An event for an instance that has already finished (or been
    #    stopped) is not a server fault: the transition the client asked
    #    for can no longer happen -- the same class of answer as a guard
    #    refusal. Both engines report it on the receipt (sync parity fix).
    (InterpreterStoppedError, 409, "Instance is no longer running"),
    (LockTimeoutError, 409, "Lock timeout"),
    (KeyNotFoundError, 404, "Not Found"),
    (InvalidKeyError, 400, "Invalid key"),
)


def status_for_exception(exc: BaseException) -> int:
    """HTTP status for an exception raised around `act()`; 500 if unknown."""
    if isinstance(exc, HTTPProblemError):
        return exc.status
    for cls, status, _title in _STATUS_TABLE:
        if isinstance(exc, cls):
            return status
    return 500


def problem_for_exception(exc: BaseException) -> JSONResponse:
    """`problem()` for *exc*: fixed title + class name, no exception text."""
    if isinstance(exc, HTTPProblemError):
        return problem(exc.status, exc.title, error=type(exc).__name__)
    ext: Dict[str, Any] = {"error": type(exc).__name__}
    title = "Internal Server Error"
    for cls, _status, cls_title in _STATUS_TABLE:
        if isinstance(exc, cls):
            title = cls_title
            break
    if isinstance(exc, SnapshotDriftError):
        # 💡 The hint a client/operator needs: which version the running
        #    code expects (never the stored blob's contents).
        ext["machine_version"] = getattr(exc, "expected", None)
    return problem(status_for_exception(exc), title, **ext)


# -----------------------------------------------------------------------------
# 🧾 Receipt -> status / body
# -----------------------------------------------------------------------------
def receipt_to_status(
    receipt: Receipt,
    *,
    changed: int = 200,
    unchanged: int = 200,
    denied: int = 409,
    deferred: int = 202,
    duplicate: int = 200,
    error: int = 500,
) -> int:
    """Map a `Receipt` to an HTTP status.

    Precedence: an idempotency refusal (fingerprint mismatch → 422,
    in flight → 409) beats ``duplicate``, which beats ``error``, then
    ``deferred``, ``denied``, ``changed``/``unchanged``.

    📝 Which error classes are CLIENT errors (and their codes) is decided
    once, in the core `receipts` module, so the Flask extra and this one
    can never disagree; the keyword overrides here only rename the
    non-error outcomes.
    """
    err = receipt.error
    if isinstance(err, IdempotencyMismatchError):
        return 422
    if isinstance(err, IdempotencyInFlightError):
        return 409
    if receipt.duplicate:
        return duplicate
    if err is not None:
        core = core_receipt_to_status(receipt)
        return core if core < 500 else error
    if receipt.deferred:
        return deferred
    if receipt.denied:
        return denied
    return changed if receipt.changed else unchanged


def declared_events(machine: Any) -> List[str]:
    """Declared, client-sendable event names (sorted, deterministic)."""
    return sorted(
        e
        for e in machine.known_events
        if not e.startswith(_INTERNAL_PREFIXES) and "*" not in e
    )


def available_events(interp: Any) -> List[str]:
    """User-facing events that would cause a transition right now."""
    return [e for e in declared_events(interp.machine) if interp.can(e)]


def state_body(
    interp: Any, context_serializer: Optional[Callable[[Any], Any]] = None
) -> Dict[str, Any]:
    """``{state, state_ids, available_events[, context]}``.

    🔐 X0.1: context is included ONLY through an explicit serializer.
    """
    body: Dict[str, Any] = {
        "state": interp.value,
        "state_ids": sorted(interp.current_state_ids),
        "available_events": available_events(interp),
    }
    if context_serializer is not None:
        body["context"] = context_serializer(interp.context)
    return body


def receipt_body(
    interp: Any,
    receipt: Receipt,
    *,
    context_serializer: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """The JSON body `ReceiptResponse` sends (also used by WebSockets)."""
    body = state_body(interp, context_serializer)
    body["state_ids"] = sorted(receipt.state_ids)
    body.update(
        changed=receipt.changed,
        denied=receipt.denied,
        deferred=receipt.deferred,
        duplicate=receipt.duplicate,
        # 🔐 X0.7: the class name only -- never str(exc).
        error=(
            type(receipt.error).__name__ if receipt.error is not None else None
        ),
    )
    return body


def ReceiptResponse(  # noqa: N802 -- reads as a response class
    interp: Any,
    receipt: Receipt,
    *,
    context_serializer: Optional[Callable[[Any], Any]] = None,
    status: Optional[int] = None,
) -> JSONResponse:
    """A `JSONResponse` for *receipt*; status from `receipt_to_status`.

    When *context_serializer* is omitted, the serializer the machine was
    registered with (tagged on the interpreter by `act()`) is used.
    """
    if context_serializer is None:
        context_serializer = getattr(interp, "_xsm_context_serializer", None)
    return JSONResponse(
        receipt_body(interp, receipt, context_serializer=context_serializer),
        status_code=receipt_to_status(receipt) if status is None else status,
    )


# -----------------------------------------------------------------------------
# 📥 Request helpers
# -----------------------------------------------------------------------------
def idempotency_key_from(conn: HTTPConnection) -> Optional[str]:
    """The ``Idempotency-Key`` header, or ``None``."""
    value = conn.headers.get(IDEMPOTENCY_HEADER)
    return value if value else None


async def json_body(
    request: Request, *, max_body_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES
) -> Dict[str, Any]:
    """Read a bounded ``application/json`` object body (X0.7).

    An empty body is ``{}``. Raises `UnsupportedMediaTypeError` (415),
    `PayloadTooLargeError` (413) or `UnprocessableBodyError` (422).
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit():
        if int(declared) > max_body_bytes:
            raise PayloadTooLargeError()
        if int(declared) == 0:
            return {}
    ctype = request.headers.get("content-type", "")
    if ctype.split(";", 1)[0].strip().lower() != "application/json":
        raise UnsupportedMediaTypeError(
            "Request body must be application/json"
        )
    chunks: List[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_body_bytes:
            raise PayloadTooLargeError()
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        raise UnprocessableBodyError("Request body is not valid JSON")
    if not isinstance(data, dict):
        raise UnprocessableBodyError()
    return data
