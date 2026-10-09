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
from typing import Any, Callable, Mapping, Optional, Tuple

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
        obj = getattr(importlib.import_module(mod), attr)
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
    except (ValueError, ValidationError) as exc:
        if isinstance(exc, ValidationError):
            detail = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors(include_input=False, include_url=False)
            )
        else:
            detail = "not valid JSON"
        return False, detail
    return True, obj.model_dump(mode="json")
