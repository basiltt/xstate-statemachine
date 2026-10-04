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


#: `ctx` keys of pydantic's BUILT-IN error types that describe the RULE,
#: never the input (`max_length`, `expected`, `ge`, ...). Anything else --
#: `error` (a `ValueError`'s text, which usually embeds the value),
#: `reason`, a custom error's template fields -- is dropped.
_SAFE_CTX_KEYS = frozenset(
    {
        "min_length",
        "max_length",
        "ge",
        "gt",
        "le",
        "lt",
        "multiple_of",
        "expected",
        "expected_tags",
        "discriminator",
        "tag",
        "pattern",
        "max_digits",
        "decimal_places",
        "field_type",
        "class_name",
        "actual_length",
        "min_count",
        "max_count",
    }
)
#: Error types whose `ctx` / `msg` is built from the raised exception's
#: text (`raise ValueError(f"bad {v}")`): nothing from them is safe.
_FREE_TEXT_TYPES = frozenset({"value_error", "assertion_error"})


def scrub(exc: ValidationError) -> ValidationError:
    """A copy of *exc* that carries no input values: ``loc`` and ``type``
    are kept; ``ctx`` only for the allow-listed rule keys; free-text
    error types (a `ValueError` from a `field_validator`, a
    `PydanticCustomError` whose template interpolated the value) become a
    fixed, value-free message."""
    details: List[Any] = []
    for err in exc.errors(include_url=False, include_input=False):
        etype = str(err["type"])
        if etype in _FREE_TEXT_TYPES or (
            _KNOWN_TYPES is not None and etype not in _KNOWN_TYPES
        ):
            details.append(
                {
                    "type": "value_error",
                    "loc": err["loc"],
                    "input": REDACTED,
                    "ctx": {"error": "value rejected by a validator"},
                }
            )
            continue
        detail: Dict[str, Any] = {
            "type": etype,
            "loc": err["loc"],
            "input": REDACTED,
        }
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            safe = {k: v for k, v in ctx.items() if k in _SAFE_CTX_KEYS}
            if safe:
                detail["ctx"] = safe
        details.append(detail)
    try:
        return ValidationError.from_exception_data(
            exc.title, details, hide_input=True
        )
    except Exception:  # noqa: BLE001 -- a shape pydantic cannot rebuild
        generic: List[Any] = [
            {
                "type": "value_error",
                "loc": d["loc"],
                "input": REDACTED,
                "ctx": {"error": "value rejected by a validator"},
            }
            for d in details
        ]
        return ValidationError.from_exception_data(
            exc.title, generic, hide_input=True
        )


def _known_types() -> frozenset:
    try:
        from pydantic_core import core_schema  # noqa: F401
        from pydantic_core import ErrorType  # type: ignore[attr-defined]

        return frozenset(getattr(ErrorType, "__args__", ()))
    except Exception:  # noqa: BLE001 -- older pydantic-core: allow all
        return frozenset()


_KNOWN_TYPES_RAW = _known_types()
#: Empty when pydantic-core does not expose `ErrorType` -- then every
#: non-free-text type is kept (with ctx still allow-listed).
_KNOWN_TYPES = _KNOWN_TYPES_RAW if _KNOWN_TYPES_RAW else None  # type: ignore[assignment]
