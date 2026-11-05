# src/xstate_statemachine/contrib/flask/_http.py
# -----------------------------------------------------------------------------
# 🌐 HTTP semantics for the WSGI side: problems, JSON bodies, receipt bodies
# -----------------------------------------------------------------------------
# 🏛️ Framework-neutral on purpose: nothing here imports Flask, so the Quart
#    shim reuses every rule unchanged. The Receipt → status mapping is the
#    CORE one (`xstate_statemachine.receipts.receipt_to_status`, #305) -- the
#    Starlette extra's table is not imported, so `[flask]` never drags
#    Starlette in.
#
# 🔐 X0.7: JSON-only bodies (415), a size cap (413), RFC 9457 problems that
#    carry a fixed TITLE and the exception CLASS name -- never ``str(exc)``.
# -----------------------------------------------------------------------------
"""Problems, bounded JSON bodies and receipt bodies (internal)."""

from __future__ import annotations

import json
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
)

from ...exceptions import (
    ConflictError,
    InterpreterStoppedError,
    InvalidEventError,
    InvalidEventPayloadError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotTooLargeError,
    StoreUnavailableError,
    SnapshotDriftError,
    UnknownEventError,
    XStateMachineError,
)
from ...persistence.helpers import KeyNotFoundError
from ...persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    validate_idempotency_key,
    validate_principal,
)
from ...context_keys import (
    public_context as _public_context,
)  # 🔑 #265: no `_xsm_*` keys in API bodies

logger = logging.getLogger(__name__)

__all__ = [
    "BadRequestError",
    "DEFAULT_BODY_TIMEOUT_S",
    "ForbiddenError",
    "HTTPProblemError",
    "IDEMPOTENCY_HEADER",
    "IdempotencyNotConfiguredError",
    "MethodNotAllowedError",
    "PROBLEM_MEDIA_TYPE",
    "PayloadTooLargeError",
    "RESERVED_SEND_KEYS",
    "RequestTimeoutError",
    "ReservedKeyError",
    "UnauthenticatedError",
    "UnprocessableBodyError",
    "UnsupportedMediaTypeError",
    "available_events",
    "declared_events",
    "history_args",
    "history_items",
    "idempotency_key_from_header",
    "log_problem",
    "mapped_exceptions",
    "parse_json_body",
    "principal_or_401",
    "problem_body",
    "problem_for_exception",
    "receipt_body",
    "refuse_reserved_send_keys",
    "state_body",
    "status_for_exception",
]

IDEMPOTENCY_HEADER = "Idempotency-Key"
PROBLEM_MEDIA_TYPE = "application/problem+json"
_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")


class HTTPProblemError(XStateMachineError):
    """A request-level refusal with a fixed status and title."""

    status = 400
    title = "Bad Request"

    def __init__(self, title: Optional[str] = None) -> None:
        if title is not None:
            self.title = title
        super().__init__(self.title)


class BadRequestError(HTTPProblemError):
    """The request is malformed (HTTP 400)."""

    pass


class ForbiddenError(HTTPProblemError):
    """`authorize` returned a falsy value (X0.1)."""

    status = 403
    title = "Forbidden"


class UnauthenticatedError(HTTPProblemError):
    """The `principal=` callable did not identify a caller (X0.1/X0.2).

    🔐 Battle #303 review H1: `str(principal)` turned `None` into the
    string `"None"` and pooled every anonymous caller into one
    idempotency scope. The core rule is `validate_principal`; a
    failure is the client's problem (401), never a shared scope.
    """

    status = 401
    title = "Unauthenticated"


def principal_or_401(value: Any) -> str:
    """Run the core principal rule; map a refusal to a 401 problem."""
    try:
        return validate_principal(value)
    except ValueError as exc:
        raise UnauthenticatedError(str(exc)) from exc


class MethodNotAllowedError(HTTPProblemError):
    """A state-changing call made from a safe method (``GET``)."""

    status = 405
    title = "State-changing request must not use a safe method"


class PayloadTooLargeError(HTTPProblemError):
    """The request body exceeds the size limit (HTTP 413)."""

    status = 413
    title = "Request body too large"


class UnsupportedMediaTypeError(HTTPProblemError):
    """The request body is not ``application/json`` (HTTP 415)."""

    status = 415
    title = "Request body must be application/json"


class RequestTimeoutError(HTTPProblemError):
    """The request body did not arrive in time (HTTP 408, safe to retry)."""

    status = 408
    title = "Request Timeout"


#: Longest a Quart request body may take to arrive (review CW-11).
DEFAULT_BODY_TIMEOUT_S = 30.0


class IdempotencyNotConfiguredError(HTTPProblemError):
    """🔥 review CW-03: an ``Idempotency-Key`` on an app WITHOUT an inbox
    was silently ignored -- 200 and every retry re-ran the event. A
    promise the server cannot keep is refused (501), as on Starlette."""

    status = 501
    title = "Idempotency-Key not supported: no idempotency inbox configured"


class UnprocessableBodyError(HTTPProblemError):
    """The request body is not a JSON object (HTTP 422)."""

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
#: Payload keys the ADAPTER owns: ``idempotency_key`` comes only from the
#: validated header (review CW-04), never from the client's body.
ADAPTER_OWNED_PAYLOAD_KEYS = ("idempotency_key",)


def refuse_reserved_send_keys(payload: Dict[str, Any]) -> None:
    """Raise `ReservedKeyError` if *payload* names a `send()` option or an
    adapter-owned key (``idempotency_key``)."""
    if any(k in payload for k in RESERVED_SEND_KEYS) or any(
        k in payload for k in ADAPTER_OWNED_PAYLOAD_KEYS
    ):
        raise ReservedKeyError()


def idempotency_key_from_header(
    value: Optional[str], *, has_inbox: bool
) -> Optional[str]:
    """The validated ``Idempotency-Key`` header value, or ``None``.

    🔥 Review CW-03: Flask and Quart used to copy the raw header into the
    payload, which skipped both rules the Starlette stack enforces: a
    malformed / over-long key reached the plugin and came back as a
    duplicate-flagged 200 whose event never ran, and with no inbox the
    key was silently ignored so retries re-ran the event.

    Args:
        value: The raw header value (``None`` / empty = no key).
        has_inbox: Whether the app has an idempotency inbox.

    Returns:
        The validated key, or ``None`` when the header is absent.

    Raises:
        BadRequestError: The key is malformed (400).
        IdempotencyNotConfiguredError: There is no inbox (501).
    """
    if not value:
        return None
    try:
        key = validate_idempotency_key(value)
    except ValueError:
        raise BadRequestError("Invalid Idempotency-Key header") from None
    if not has_inbox:
        raise IdempotencyNotConfiguredError()
    return key


def history_args(args: Mapping[str, str]) -> Tuple[int, int]:
    """Parse ``?after=&limit=`` for ``/history``: ``(after, limit)``.

    🔥 Review CW-17b: ``?limit=-1`` passed the ``int()`` check and then
    raised a ValueError from the log store (a 500 with a traceback); a
    negative bound is the client's mistake (400).

    Raises:
        BadRequestError: Not integers, or negative.
    """
    try:
        after = int(args.get("after", 0))
        limit = min(int(args.get("limit", 100)), 1000)
    except ValueError:
        raise BadRequestError("after/limit must be integers") from None
    if after < 0 or limit < 0:
        raise BadRequestError("after/limit must not be negative")
    return after, limit


def history_items(rows: Iterable[Any]) -> List[Dict[str, Any]]:
    """Public view of log rows: every field EXCEPT ``event_payload``.

    🔐 Review CW-06: Flask omitted the payload (it may carry PII or
    secrets; X0.1 state-only bodies) while Quart returned it. One helper
    for both so they cannot drift.
    """
    return [
        {k: v for k, v in rec.to_dict().items() if k != "event_payload"}
        for rec in rows
    ]


def log_problem(exc: BaseException, where: str = "-") -> None:
    """Leave the server-side trace for a problem response.

    A backend outage is ONE warning line (#306: a Redis failover used to
    write a traceback per request); any other 5xx logs with its traceback
    -- the client body carries only the class name (X0.7). 4xx are quiet.

    Args:
        exc: The exception being answered.
        where: ``"<METHOD> <path>"`` or another short label.
    """
    if isinstance(exc, StoreUnavailableError):
        logger.warning("🔌 store unavailable; %s answered 503: %s", where, exc)
    elif status_for_exception(exc) >= 500:
        logger.error(
            "🔥 %s while handling a statechart request (%s)",
            type(exc).__name__,
            where,
            exc_info=exc,
        )


_STATUS_TABLE = (
    (IdempotencyMismatchError, 422, "Idempotency key reused"),
    (UnknownEventError, 422, "Unknown event"),
    (InvalidEventPayloadError, 422, "Invalid event payload"),
    (InvalidEventError, 422, "Invalid event"),
    (SnapshotDriftError, 409, "Machine version mismatch"),
    (IdempotencyInFlightError, 409, "Request in flight"),
    (ConflictError, 409, "Conflict"),
    # 🏁 Review CW-17: an event for a finished / stopped instance is 409
    #    on the Starlette stack; it was a 500 here.
    (InterpreterStoppedError, 409, "Instance is no longer running"),
    (LockTimeoutError, 409, "Lock timeout"),
    # 🍪 #285 battle (A): a context that outgrew its store (SessionStore's
    #    cookie cap) is the request's payload problem, not a server crash.
    (SnapshotTooLargeError, 413, "Snapshot too large"),
    # 🔌 #306 battle: the backend is down, not the request. Retryable.
    (StoreUnavailableError, 503, "Store unavailable"),
    (KeyNotFoundError, 404, "Not Found"),
    (InvalidKeyError, 400, "Invalid key"),
)


def mapped_exceptions() -> Tuple[type, ...]:
    """Every exception class `problem_for_exception` maps to a non-500
    status -- what the extensions register as app error handlers."""
    return (HTTPProblemError,) + tuple(c for c, _s, _t in _STATUS_TABLE)


def problem_body(
    status: int, title: str, detail: Optional[str] = None, **ext: Any
) -> Dict[str, Any]:
    """An RFC 9457 problem object (serve as ``application/problem+json``)."""
    body: Dict[str, Any] = {"type": "about:blank", "title": title}
    body["status"] = status
    if detail is not None:
        body["detail"] = detail
    body.update(ext)
    return body


def status_for_exception(exc: BaseException) -> int:
    """HTTP status for an exception raised around `act()`; 500 if unknown."""
    if isinstance(exc, HTTPProblemError):
        return exc.status
    for cls, status, _title in _STATUS_TABLE:
        if isinstance(exc, cls):
            return status
    return 500


def problem_for_exception(exc: BaseException) -> Tuple[int, Dict[str, Any]]:
    """``(status, problem)`` for *exc*: fixed title + class name only."""
    if isinstance(exc, HTTPProblemError):
        return exc.status, problem_body(
            exc.status, exc.title, error=type(exc).__name__
        )
    title = "Internal Server Error"
    for cls, _status, cls_title in _STATUS_TABLE:
        if isinstance(exc, cls):
            title = cls_title
            break
    ext: Dict[str, Any] = {"error": type(exc).__name__}
    if isinstance(exc, SnapshotDriftError):
        ext["machine_version"] = getattr(exc, "expected", None)
    status = status_for_exception(exc)
    return status, problem_body(status, title, **ext)


def parse_json_body(
    content_type: Optional[str],
    content_length: Optional[int],
    read: Callable[[int], bytes],
    *,
    max_body_bytes: int,
) -> Dict[str, Any]:
    """A bounded ``application/json`` OBJECT body; empty → ``{}``.

    *read(n)* returns at most *n* bytes of the body. Raises
    `PayloadTooLargeError` (413), `UnsupportedMediaTypeError` (415) or
    `UnprocessableBodyError` (422).
    """
    if content_length is not None and content_length > max_body_bytes:
        raise PayloadTooLargeError()
    raw = read(max_body_bytes + 1)
    if len(raw) > max_body_bytes:
        raise PayloadTooLargeError()
    if not raw.strip():
        return {}
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if ctype != "application/json":
        raise UnsupportedMediaTypeError()
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):
        # 🔥 Review CW-08: deeply nested JSON raised RecursionError (not a
        #    ValueError) and surfaced as a 500.
        raise UnprocessableBodyError(
            "Request body is not valid JSON"
        ) from None
    if not isinstance(data, dict):
        raise UnprocessableBodyError()
    return data


def declared_events(machine: Any) -> List[str]:
    """Declared, client-sendable event names (sorted)."""
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
    """``{state, state_ids, available_events[, context]}`` -- context ONLY
    through an explicit serializer (X0.1)."""
    body: Dict[str, Any] = {
        "state": interp.value,
        "state_ids": sorted(interp.current_state_ids),
        "available_events": available_events(interp),
    }
    if context_serializer is not None:
        body["context"] = context_serializer(_public_context(interp.context))
    return body


def receipt_body(
    interp: Any,
    receipt: Any,
    *,
    context_serializer: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """The JSON body `receipt_response` sends."""
    body = state_body(interp, context_serializer)
    body["state_ids"] = sorted(receipt.state_ids)
    body.update(
        changed=bool(receipt.changed),
        denied=bool(receipt.denied),
        deferred=bool(receipt.deferred),
        duplicate=bool(receipt.duplicate),
        # 🔐 X0.7: the class name only -- never str(exc).
        error=(
            type(receipt.error).__name__ if receipt.error is not None else None
        ),
    )
    return body


def is_idempotency_refusal(receipt: Any) -> bool:
    """Whether *receipt* carries an idempotency refusal (422 / 409)."""
    return isinstance(
        receipt.error, (IdempotencyMismatchError, IdempotencyInFlightError)
    )


def register_problem_handlers(app: Any, handler: Any) -> int:
    """Register *handler* for every mapped exception class on *app*,
    SKIPPING classes the application already handles itself (review
    #285: `register_error_handler` overwrites, and apps register their
    handlers before `init_app` in the factory pattern). Returns the
    number registered."""
    own = app.error_handler_spec.get(None, {}).get(None, {})
    n = 0
    for exc_cls in mapped_exceptions():
        if exc_cls in own:
            continue
        app.register_error_handler(exc_cls, handler)
        n += 1
    return n
