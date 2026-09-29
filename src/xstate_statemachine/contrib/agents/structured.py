# src/xstate_statemachine/contrib/agents/structured.py
# -----------------------------------------------------------------------------
# 🧾 structured_output -- per-state schemas on top of E1's RETRY_OUTPUT (#289)
# -----------------------------------------------------------------------------
# 🏛️ E1 (`core.py`) already owns the mechanism: the `outputValid` guard
#    validates the final reply against `output_model=` or the active
#    state's `meta.output_model`, `retryOutput` re-prompts with the
#    pydantic error (field names, never values) as `RETRY_OUTPUT`, and
#    `canRetryOutput` sends exhaustion to `error`. This module is the thin
#    public wrapper -- it does NOT add a second validation path:
#
#      * `structured_output(Model, retries=2)` → the `agent_logic` keyword
#        arguments that switch it on (``Model=None`` = per-state schemas
#        from `meta.output_model`);
#      * the reply is parsed with instructor's JSON extractor when
#        `instructor` is installed (prose around the JSON, last object
#        wins), else strict JSON -- the "raw JSON" path always works;
#      * `validate_structured()` validates one value (text, dict, or a
#        pydantic-ai native result) the same way, for use outside a chart.
# -----------------------------------------------------------------------------
"""Structured output per state: the public face of `RETRY_OUTPUT`."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import BaseModel

from .core import _parse_json_text, _resolve_model, _validate_output
from .messages import AgentConfigError

__all__ = [
    "instructor_available",
    "json_parser",
    "structured_output",
    "validate_structured",
]


def instructor_available() -> bool:
    """``True`` when `instructor`'s JSON extractor can be imported."""
    try:
        from instructor.utils import extract_json_from_codeblock  # noqa: F401
    except ImportError:
        return False
    return True


def _instructor_parse(text: str) -> Any:
    from instructor.utils import extract_json_from_codeblock

    return json.loads(extract_json_from_codeblock(text))


def json_parser(use_instructor: Optional[bool] = None) -> Callable[[str], Any]:
    """The reply-text → JSON parser `structured_output` installs.

    ``None`` = instructor when installed, else strict; ``True`` requires
    instructor (`AgentConfigError` if absent); ``False`` = strict JSON.
    """
    if use_instructor is None:
        use_instructor = instructor_available()
    elif use_instructor and not instructor_available():
        raise AgentConfigError(
            "use_instructor=True but instructor is not installed: "
            "pip install instructor"
        )
    return _instructor_parse if use_instructor else _parse_json_text


def structured_output(
    model_cls: Any = None,
    *,
    retries: int = 2,
    use_instructor: Optional[bool] = None,
) -> Dict[str, Any]:
    """`agent_logic` keyword arguments for validated structured output.

    ::

        logic = agent_logic(model, tools, **structured_output(Weather))

    Args:
        model_cls: A pydantic model (or ``"module:Model"``) every final
            reply must match; ``None`` → each state's ``meta.output_model``
            decides (per-state schemas).
        retries: ``RETRY_OUTPUT`` re-prompts before the agent ends in
            ``error`` with ``kind: "output"``. Each retry is a model turn
            and counts against every budget.
        use_instructor: See `json_parser`.
    """
    if (
        not isinstance(retries, int)
        or isinstance(retries, bool)
        or retries < 0
    ):
        raise AgentConfigError("retries must be an int >= 0")
    if model_cls is not None:
        _resolve_model(model_cls)  # fail loudly now, not at the first reply
    return {
        "output_model": model_cls,
        "max_output_retries": retries,
        "output_parser": json_parser(use_instructor),
    }


def validate_structured(
    model_cls: Any, value: Any, *, use_instructor: Optional[bool] = None
) -> Tuple[bool, Any]:
    """``(ok, dumped_value_or_error_detail)`` for one reply.

    *value* may be reply text, an already-parsed dict, or a pydantic
    model instance (pydantic-ai's native structured result).
    """
    model = _resolve_model(model_cls)
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if not isinstance(value, str):
        value = json.dumps(value)
    return _validate_output(model, value, json_parser(use_instructor))
