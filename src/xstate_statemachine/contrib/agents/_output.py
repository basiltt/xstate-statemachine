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
from typing import Dict, Any, Callable, Mapping, Optional, Tuple, get_args

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
        # 📝 #289 review (3): a `field_serializer` raising or non-UTF-8
        #    bytes failed HERE, outside the try, and stopped the machine.
        return True, obj.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001 -- hostile reply, see below
        # 🔥 #289 battle (A): a validator raising TypeError/RuntimeError,
        #    a custom parser raising KeyError, or 100k-deep nesting
        #    (RecursionError) escaped into `outputValid`/`retryOutput` and
        #    STOPPED the machine. Any failure is "did not validate"; the
        #    detail names the exception type only (its message may quote
        #    the reply). CancelledError is BaseException -- not caught.
        if isinstance(exc, ValidationError):
            return False, _validation_detail(model, exc)
        if isinstance(exc, json.JSONDecodeError):
            return False, "not valid JSON"
        return False, f"output rejected ({type(exc).__name__})"


# 📝 pydantic error types whose `msg` embeds the user's own exception text
#    (a `field_validator` raising `ValueError(f"bad {v}")` quotes the value).
_USER_MSG_TYPES = frozenset({"value_error", "assertion_error"})


def _field_names(model: Any) -> "set[str]":
    """Every field name declared on *model* and the BaseModels nested in
    its annotations -- the only `loc` strings safe to echo (a dict-typed
    field's `loc` carries the MODEL's keys, which are reply content)."""
    names: "set[str]" = set()
    seen: "set[Any]" = set()
    todo = [model]
    while todo:
        m = todo.pop()
        if m in seen or not (isinstance(m, type) and issubclass(m, BaseModel)):
            continue
        seen.add(m)
        for name, field in m.model_fields.items():
            names.add(name)
            if field.alias:
                names.add(field.alias)
            stack = [field.annotation]
            while stack:
                ann = stack.pop()
                if isinstance(ann, type) and issubclass(ann, BaseModel):
                    todo.append(ann)
                else:
                    stack.extend(get_args(ann))
    return names


def _validation_detail(model: Any, exc: ValidationError) -> str:
    """Field paths and pydantic's error TYPE / message, never the reply.

    🔥 #289 review (1): `e["msg"]` of a custom validator and `loc` parts
    under a dict-typed field both quoted the model's values; a reply
    `{"m": {"<injected>": 1}}` echoed the injected key into the retry
    prompt and `context["error"]`. Non-field `loc` strings become `*`,
    custom-validator messages become their fixed type.
    """
    allowed = _field_names(model)
    parts = []
    for e in exc.errors(include_input=False, include_url=False):
        loc = ".".join(
            (
                str(p)
                if isinstance(p, int) or p in allowed or p == "__root__"
                else "*"
            )
            for p in e["loc"]
        )
        kind = str(e.get("type") or "invalid")
        msg = kind if kind in _USER_MSG_TYPES else str(e.get("msg") or kind)
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or "did not validate"


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
