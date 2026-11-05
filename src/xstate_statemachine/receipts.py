# src/xstate_statemachine/receipts.py
# -----------------------------------------------------------------------------
# 🧾 Receipt codec -- one JSON shape and one HTTP-status mapping (#305)
# -----------------------------------------------------------------------------
# 🏛️ Why in core: every web integration (Django #275, Flask #283, Starlette
#    #285, DRF ...) turns a `Receipt` into a response, and the idempotency
#    inbox (#261) CACHES receipts so a retried webhook gets the same answer.
#    If each adapter invented its own JSON, a cached receipt would have no
#    defined form and Django would have to import the Starlette extra to
#    share one. So the shape lives here, zero-dependency, and adapters
#    only choose the transport.
#
# 📝 `error` is serialised as `{"type", "message"}` -- the exception's
#    class name and `str()`. NEVER pickled, never `repr()`'d with arguments
#    that might contain secrets (X0 baseline #303: no `pickle`, no
#    reconstruction of arbitrary types on read). `receipt_from_json`
#    rebuilds it as a `ReceiptError` carrying both strings, so
#    `receipt.error is not None` keeps meaning "it did not run cleanly".
# -----------------------------------------------------------------------------
"""`Receipt` ⇄ JSON and `Receipt` → HTTP status."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from .events import Receipt

__all__ = [
    "ReceiptError",
    "receipt_to_status",
    "receipt_to_json",
    "receipt_from_json",
    "STATUS_OK",
    "STATUS_ACCEPTED",
    "STATUS_NO_OP",
    "STATUS_NOT_MODIFIED_OK",
    "STATUS_CONFLICT",
    "STATUS_ERROR",
    "STATUS_UNPROCESSABLE",
    "STATUS_UNAVAILABLE",
]

#: HTTP statuses `receipt_to_status` returns. Named so adapters and tests
#: cite the rule, not the number.
STATUS_OK = 200  # transition taken
STATUS_NO_OP = 200  # no handler in this state: a clean no-op
#: Historical spelling of `STATUS_NO_OP`: it is a 200, NOT an HTTP 304.
STATUS_NOT_MODIFIED_OK = STATUS_NO_OP
STATUS_ACCEPTED = 202  # deferred by `onUnhandled: "defer"` -- held, not run
STATUS_CONFLICT = 409  # a guard refused it: the request conflicts with state
STATUS_ERROR = 500  # an action / target / chain error while processing
STATUS_UNPROCESSABLE = 422  # idempotency key reused with a different payload
STATUS_UNAVAILABLE = 503  # the idempotency inbox itself failed (refuse mode)
#: `error` class names that are the CLIENT's fault, not processing
#: failures (#261). Matched by name so this module stays free of a
#: `persistence` import; the receipt codec preserves the name.
_CLIENT_ERROR_STATUS = {
    "IdempotencyMismatchError": STATUS_UNPROCESSABLE,
    "IdempotencyInFlightError": STATUS_CONFLICT,
    # 🛡️ Battle #261: `on_inbox_error="refuse"` -- the dedup store is
    #    down, the action did NOT run; the client should retry later.
    "InboxUnavailableError": STATUS_UNAVAILABLE,
    # 🏁 An event for an instance that already finished (or was stopped):
    #    the transition can no longer happen. Refused like a guard, not a
    #    server fault. Both engines report it on the receipt (#123 parity;
    #    the sync engine used to return None and the Flask blueprint
    #    answered a POST to a finished order with a 500).
    "InterpreterStoppedError": STATUS_CONFLICT,
}


class ReceiptError(Exception):
    """The `error` of a receipt rebuilt from JSON.

    Only the original's class name and message survive the round trip,
    by design. ``type`` is the original exception class name.
    """

    def __init__(self, type: str, message: str) -> None:
        super().__init__(message)
        self.type = type
        self.message = message

    def __reduce__(self) -> Tuple[Any, ...]:
        """Rebuild from ``(type, message)`` so it survives pickling (RU-11)."""
        return (ReceiptError, (self.type, self.message))

    def __repr__(self) -> str:  # pragma: no cover - diagnostic
        return f"ReceiptError(type={self.type!r}, message={self.message!r})"


def receipt_to_status(receipt: Receipt) -> int:
    """Map a receipt to an HTTP status code.

    Precedence, most severe first -- the order matters because a receipt
    can carry several flags (a duplicate of an errored delivery is still
    an error):

    | Receipt                       | Status | Meaning                    |
    |:------------------------------|:------:|:---------------------------|
    | ``error`` is a key mismatch   |  422   | idempotency key reused     |
    | ``error`` is key in flight    |  409   | first delivery still running |
    | ``error`` is inbox unavailable|  503   | dedup store down (refuse mode) |
    | ``error`` is instance stopped |  409   | already finished / stopped |
    | ``error is not None`` (other) |  500   | processing failed          |
    | ``deferred``                  |  202   | held for a later state     |
    | ``denied``                    |  409   | a guard refused it         |
    | ``changed``                   |  200   | transition taken           |
    | none of the above             |  200   | not handled here; no-op    |

    ``duplicate`` does not change the status: the cached receipt already
    describes the ORIGINAL outcome, and a retry must get the same answer.
    """
    if receipt.error is not None:
        return _error_status(receipt.error)
    if receipt.deferred:
        return STATUS_ACCEPTED
    if receipt.denied:
        return STATUS_CONFLICT
    return STATUS_OK if receipt.changed else STATUS_NO_OP


def _error_status(err: BaseException) -> int:
    """HTTP status for a receipt's *err*, matching by class name.

    🏛️ A rebuilt `ReceiptError` only has the original NAME, so names are
    the common currency. For a live exception the whole MRO is walked, so a
    subclass of ``IdempotencyMismatchError`` keeps the parent's 422 instead
    of degrading to 500.

    Args:
        err: The receipt's error (live or rebuilt).

    Returns:
        The mapped status, `STATUS_ERROR` when no name matches.
    """
    if isinstance(err, ReceiptError):
        names: Tuple[str, ...] = (err.type,)
    else:
        names = tuple(c.__name__ for c in type(err).__mro__)
    for name in names:
        status = _CLIENT_ERROR_STATUS.get(str(name))
        if status is not None:
            return status
    return STATUS_ERROR


def _error_to_json(
    err: Optional[BaseException], include_message: bool = True
) -> Optional[Dict[str, str]]:
    """Serialise a receipt error as ``{"type", "message"}``.

    Args:
        err: The error, or ``None``.
        include_message: ``False`` blanks the message (type only).

    Returns:
        The JSON-ready dict, or ``None`` when there is no error.
    """
    if err is None:
        return None
    if isinstance(err, ReceiptError):
        name, message = err.type, err.message
    else:
        name, message = type(err).__name__, str(err)
    return {"type": name, "message": message if include_message else ""}


def receipt_to_json(
    receipt: Receipt, *, include_messages: bool = True
) -> Dict[str, Any]:
    """The stable JSON form of a receipt (a plain dict; ``json.dumps`` it).

    ``state_ids`` is a SORTED list so two receipts for the same outcome
    serialise identically -- a cache key or an ETag can be built from it.

    ⚠️ The error MESSAGE is ``str(exception)`` and may echo request data
    (a gateway error carrying a card number). The default keeps it because
    the idempotency cache must replay the original answer faithfully; a
    caller that puts the JSON in front of an untrusted client (an HTTP
    response body) should pass ``include_messages=False`` and send only the
    error ``type``.

    Args:
        receipt: The receipt to serialise.
        include_messages: Keep each error's message (default). ``False``
            writes an empty message.

    Returns:
        A JSON-serialisable dict.
    """
    return {
        "state_ids": sorted(receipt.state_ids),
        "changed": bool(receipt.changed),
        "error": _error_to_json(receipt.error, include_messages),
        "deferred": bool(receipt.deferred),
        "denied": bool(receipt.denied),
        "duplicate": bool(receipt.duplicate),
    }


def receipt_from_json(data: Mapping[str, Any]) -> Receipt:
    """Rebuild a `Receipt` from `receipt_to_json` output.

    Validates shape and raises ``ValueError`` on a malformed record rather
    than letting a bare ``KeyError`` / ``TypeError`` escape -- a cached
    receipt comes from a store, i.e. from outside the process boundary.
    """
    if not isinstance(data, Mapping):
        raise ValueError(
            f"receipt record must be an object, got {type(data).__name__}"
        )
    ids = data.get("state_ids")
    if not isinstance(ids, (list, tuple)) or not all(
        isinstance(s, str) for s in ids
    ):
        raise ValueError("receipt 'state_ids' must be a list of strings")
    err_rec = data.get("error")
    error: Optional[BaseException] = None
    if err_rec is not None:
        if (
            not isinstance(err_rec, Mapping)
            or not isinstance(err_rec.get("type"), str)
            or not isinstance(err_rec.get("message"), str)
        ):
            raise ValueError(
                'receipt \'error\' must be null or {"type", "message"} '
                "strings"
            )
        error = ReceiptError(err_rec["type"], err_rec["message"])
    flags = {}
    for key in ("changed", "deferred", "denied", "duplicate"):
        val = data.get(key, False)
        if not isinstance(val, bool):
            raise ValueError(f"receipt '{key}' must be a boolean")
        flags[key] = val
    return Receipt(
        state_ids=frozenset(ids),
        changed=flags["changed"],
        error=error,
        deferred=flags["deferred"],
        denied=flags["denied"],
        duplicate=flags["duplicate"],
    )
