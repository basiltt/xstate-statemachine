# src/xstate_statemachine/contrib/pydantic/_scrub.py
"""Strip offending input values from a pydantic `ValidationError` (#266).

🏛️ X0.5: a pydantic error's ``str()`` carries ``input_value=...`` and its
``errors()`` entries carry ``input``. The context and event payloads hold
secrets (a ``card_token`` that failed a type check), and the exception
reaches ``logger.exception`` (action failure), receipts and HTTP problem
bodies. The library therefore never hands out the raw error: it rebuilds
it with ``hide_input=True`` and the input replaced by a placeholder, and
raises ``from None`` so the original is not chained into a traceback.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import ValidationError

#: What replaces a rejected value in ``errors()[i]["input"]``.
REDACTED = "<redacted>"


def scrub(exc: ValidationError) -> ValidationError:
    """A copy of *exc* that carries no input values (loc/type/msg kept)."""
    details: List[Any] = []
    for err in exc.errors(include_url=False, include_input=False):
        detail: Dict[str, Any] = {
            "type": err["type"],
            "loc": err["loc"],
            "input": REDACTED,
        }
        if "ctx" in err:
            detail["ctx"] = err["ctx"]
        details.append(detail)
    try:
        return ValidationError.from_exception_data(
            exc.title, details, hide_input=True
        )
    except Exception:  # noqa: BLE001 -- a custom error type pydantic
        # cannot rebuild (`PydanticCustomError` needs its message
        # template): fall back to a generic, value-free error per loc.
        generic: List[Any] = [
            {
                "type": "value_error",
                "loc": d["loc"],
                "input": REDACTED,
                "ctx": {"error": err_msg},
            }
            for d, err_msg in zip(
                details,
                (e.get("msg", "invalid") for e in exc.errors()),
            )
        ]
        return ValidationError.from_exception_data(
            exc.title, generic, hide_input=True
        )
