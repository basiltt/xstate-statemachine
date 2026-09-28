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

from typing import Any, Dict, Mapping, Optional

from .events import Receipt

__all__ = [
    "ReceiptError",
    "receipt_to_status",
    "receipt_to_json",
    "receipt_from_json",
    "STATUS_OK",
    "STATUS_ACCEPTED",
    "STATUS_NOT_MODIFIED_OK",
    "STATUS_CONFLICT",
    "STATUS_ERROR",
    "STATUS_UNPROCESSABLE",
]

#: HTTP statuses `receipt_to_status` returns. Named so adapters and tests
#: cite the rule, not the number.
STATUS_OK = 200  # transition taken
STATUS_NOT_MODIFIED_OK = 200  # no handler in this state: a clean no-op
STATUS_ACCEPTED = 202  # deferred by `onUnhandled: "defer"` -- held, not run
STATUS_CONFLICT = 409  # a guard refused it: the request conflicts with state
STATUS_ERROR = 500  # an action / target / chain error while processing
STATUS_UNPROCESSABLE = 422  # idempotency key reused with a different payload
#: `error` class names that are the CLIENT's fault, not processing
#: failures (#261). Matched by name so this module stays free of a
#: `persistence` import; the receipt codec preserves the name.
_CLIENT_ERROR_STATUS = {
    "IdempotencyMismatchError": STATUS_UNPROCESSABLE,
    "IdempotencyInFlightError": STATUS_CONFLICT,
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
    | ``error is not None`` (other) |  500   | processing failed          |
    | ``deferred``                  |  202   | held for a later state     |
    | ``denied``                    |  409   | a guard refused it         |
    | ``changed``                   |  200   | transition taken           |
    | none of the above             |  200   | not handled here; no-op    |

    ``duplicate`` does not change the status: the cached receipt already
    describes the ORIGINAL outcome, and a retry must get the same answer.
    """
    if receipt.error is not None:
        err = receipt.error
        name = getattr(err, "type", None) or type(err).__name__
        return _CLIENT_ERROR_STATUS.get(str(name), STATUS_ERROR)
    if receipt.deferred:
        return STATUS_ACCEPTED
    if receipt.denied:
        return STATUS_CONFLICT
    return STATUS_OK if receipt.changed else STATUS_NOT_MODIFIED_OK


def _error_to_json(err: Optional[BaseException]) -> Optional[Dict[str, str]]:
    if err is None:
        return None
    if isinstance(err, ReceiptError):
        return {"type": err.type, "message": err.message}
    return {"type": type(err).__name__, "message": str(err)}


def receipt_to_json(receipt: Receipt) -> Dict[str, Any]:
    """The stable JSON form of a receipt (a plain dict; ``json.dumps`` it).

    ``state_ids`` is a SORTED list so two receipts for the same outcome
    serialise identically -- a cache key or an ETag can be built from it.
    """
    return {
        "state_ids": sorted(receipt.state_ids),
        "changed": bool(receipt.changed),
        "error": _error_to_json(receipt.error),
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
