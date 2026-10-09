# src/xstate_statemachine/contrib/agents/_output.py
# -----------------------------------------------------------------------------
# 🧾 Structured-output helpers shared by `core` and `structured` (#287/#289)
# -----------------------------------------------------------------------------
# 🏛️ Private module: resolving an output model, parsing reply text and
#    validating it. Split out of `core.py` (file-size rule, < 800 lines) so
#    `structured.py` no longer has to import private names from `core`.
#    Validation errors carry field names and messages only, never the
#    rejected input (`include_input=False`) -- it may quote the prompt.
# -----------------------------------------------------------------------------
"""Output-model resolution and validation for agent replies."""

from __future__ import annotations

import importlib
import json
from typing import Dict, Any, Callable, Mapping, Optional, Tuple

from pydantic import BaseModel, ValidationError

from .messages import AgentConfigError

__all__: "list[str]" = []


def _resolve_model(spec: Any) -> Optional[type]:
    if spec is None:
        return None
    if isinstance(spec, type) and issubclass(spec, BaseModel):
        return spec
    if isinstance(spec, str) and ":" in spec:
        mod, _, attr = spec.partition(":")
        # 🔥 #287 battle (A): a bad 'module:Model' leaked a raw
        #    ModuleNotFoundError / AttributeError from inside callModel.
        try:
            obj = getattr(importlib.import_module(mod), attr)
        except (ImportError, AttributeError, ValueError) as exc:
            raise AgentConfigError(
                f"output_model {spec!r} cannot be resolved: {exc}"
            ) from None
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            return obj
    raise AgentConfigError(
        f"output_model must be a pydantic BaseModel or 'module:Model' "
        f"(got {spec!r})"
    )


def _meta_output_model(interp: Any, event: Any) -> Any:
    """``meta.output_model`` of the state hosting this invoke, if any."""
    etype = getattr(event, "type", "") or ""
    if etype.startswith("invoke."):
        node = interp.machine.get_state_by_id(etype[len("invoke.") :])
        if node is not None and (node.meta or {}).get("output_model"):
            return node.meta["output_model"]
    for meta in interp.get_meta().values():
        if isinstance(meta, dict) and meta.get("output_model"):
            return meta["output_model"]
    return None


def _task_of(ctx: Mapping[str, Any]) -> Optional[str]:
    """The task a spawned agent starts on: ``context["task"]`` or
    ``context["input"]["prompt"]``."""
    task = ctx.get("task")
    if not task and isinstance(ctx.get("input"), Mapping):
        task = ctx["input"].get("prompt")
    return str(task) if task else None


def _parse_json_text(text: str) -> Any:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[4:] if t.lower().startswith("json") else t
    return json.loads(t)


def _validate_output(
    model: Optional[type],
    text: str,
    parser: Optional[Callable[[str], Any]] = None,
) -> Tuple[bool, Any]:
    """``(ok, value_or_error_text)``. *parser* turns the reply text into
    the JSON value to validate (default: strict JSON, code fence allowed).
    """
    if model is None:
        return True, text
    try:
        obj = model.model_validate(  # type: ignore[attr-defined]
            (parser or _parse_json_text)(text)
        )
    except Exception as exc:  # noqa: BLE001 -- hostile reply, see below
        # 🔥 #289 battle (A): a validator raising TypeError/RuntimeError,
        #    a custom parser raising KeyError, or 100k-deep nesting
        #    (RecursionError) escaped into `outputValid`/`retryOutput` and
        #    STOPPED the machine. Any failure is "did not validate"; the
        #    detail names the exception type only (its message may quote
        #    the reply). CancelledError is BaseException -- not caught.
        if isinstance(exc, ValidationError):
            detail = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors(include_input=False, include_url=False)
            )
        elif isinstance(exc, ValueError):
            detail = "not valid JSON"
        else:
            detail = f"output rejected ({type(exc).__name__})"
        return False, detail
    return True, obj.model_dump(mode="json")


def _retry_prompt(model: Optional[type], detail: Any) -> Dict[str, Any]:
    """The ``RETRY_OUTPUT`` user message: the validation detail (field
    names and messages only -- never the rejected reply, which may carry
    injected text or PII) and the schema to match."""
    schema = (
        json.dumps(model.model_json_schema())  # type: ignore[attr-defined]
        if model is not None
        else "{}"
    )
    return {
        "role": "user",
        "content": (
            f"RETRY_OUTPUT: your answer did not validate ({detail}). "
            f"Reply with only JSON matching this schema: {schema}"
        ),
    }
