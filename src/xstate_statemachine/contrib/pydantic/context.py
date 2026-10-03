# src/xstate_statemachine/contrib/pydantic/context.py
"""Typed context: `context_model()` builds a `context_validator` (#266)."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ...context_keys import is_private_context_key

from ...exceptions import XStateMachineError
from ...plugins import PluginBase

__all__ = [
    "ContextValidationError",
    "PydanticCodec",
    "TypedContextPlugin",
    "context_model",
    "context_of",
    "typed_context",
]

M = TypeVar("M", bound=BaseModel)


class ContextValidationError(XStateMachineError):
    """The context does not satisfy its model.

    Raised by the validator `context_model()` builds. When it fires after
    an action the engine treats it as an **action error**
    (`actionErrorPolicy` applies; ``"rollback"`` restores the previous
    context), so the machine never holds an invalid context. Carries the
    pydantic error.

    Attributes:
        model: The context model class.
        cause: The `pydantic.ValidationError`.
        errors: ``cause.errors()`` -- dicts with ``loc`` / ``msg`` / ``type``.
    """

    def __init__(self, model: Type[BaseModel], cause: ValidationError) -> None:
        self.model = model
        self.cause = cause
        self.errors = cause.errors()
        paths = ", ".join(
            ".".join(str(p) for p in e.get("loc", ())) or "<root>"
            for e in self.errors
        )
        first = self.errors[0].get("msg", "") if self.errors else ""
        super().__init__(
            f"context does not satisfy {model.__name__} "
            f"({cause.error_count()} error(s) at {paths}): {first}"
        )


def _validate_into(
    model: Type[BaseModel], ctx: Any, write_back: bool
) -> BaseModel:
    if not isinstance(ctx, dict):
        raise TypeError(
            f"context must be a dict for {model.__name__}, got "
            f"{type(ctx).__name__}"
        )
    # 🏛️ #265 battle (review CRITICAL): keys with the LIBRARY-PRIVATE
    #    prefix (`_xsm_`, see `PRIVATE_CONTEXT_PREFIX`) are the library's
    #    bookkeeping that rides in the snapshot -- the dead-letter error
    #    chain is the first. They are not the user's domain and a model
    #    with `extra="forbid"` must not reject the context because of
    #    them: every later action's validation would fail and, under
    #    `actionErrorPolicy: "rollback"`, the machine could never move
    #    again. Validate the user's keys only; `write_back` never touches
    #    private keys (the model does not declare them).
    visible = {k: v for k, v in ctx.items() if not is_private_context_key(k)}
    try:
        instance = model.model_validate(visible)
    except ValidationError as exc:
        raise ContextValidationError(model, exc) from exc
    if write_back:
        # 🏛️ The interpreter owns a plain dict (actions mutate it in
        #    place); the model is a LENS on it, not a replacement. Write
        #    the model's defaults and coerced values back so `ctx["total"]`
        #    is a Decimal and a key the chart omitted exists -- keys the
        #    model does not declare are left untouched.
        for name in model.model_fields:
            ctx[name] = getattr(instance, name)
    return instance


def context_model(
    model: Type[M], *, write_back: bool = True
) -> Callable[[Dict[str, Any]], None]:
    """Build a ``context_validator`` for `create_machine()` from *model*.

    ::

        class OrderContext(BaseModel):
            items: list[str] = []
            total: Decimal = Decimal(0)
            currency: Literal["USD", "EUR"] = "USD"

        machine = create_machine(
            cfg, logic=logic, context_validator=context_model(OrderContext)
        )

    The engine calls it after any action that changed ``context``. It
    raises `ContextValidationError` -- an action error, so
    ``actionErrorPolicy: "rollback"`` restores the previous context. With
    *write_back* (default) the model's defaults and coerced values are
    written into the live dict. Pair with `TypedContextPlugin` (or
    `typed_context`) so the INITIAL context is validated too.
    """
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(
            "context_model() needs a pydantic BaseModel subclass, got "
            f"{model!r}"
        )

    def _validate(ctx: Any) -> None:
        _validate_into(model, ctx, write_back)

    _validate.__name__ = f"validate_{model.__name__}"
    _validate.__xsm_context_model__ = model  # type: ignore[attr-defined]
    return _validate


def typed_context(model: Type[M], config: Dict[str, Any]) -> Dict[str, Any]:
    """*config* with its ``"context"`` validated and completed by *model*
    (defaults written in, values coerced), so the machine's initial context
    satisfies the model before the first event. Raises
    `ContextValidationError`. Does not mutate *config*."""
    raw = config.get("context") or {}
    if callable(raw):  # a context factory: nothing static to check
        return dict(config)
    ctx = dict(raw)
    _validate_into(model, ctx, True)
    out = dict(config)
    out["context"] = ctx
    return out


def context_of(interpreter: Any, model: Type[M]) -> M:
    """A typed view of ``interpreter.context`` -- a fresh
    ``model.model_validate(ctx)`` each call. The dict stays the source of
    truth; mutate it through actions, not through this instance."""
    return model.model_validate(interpreter.context)


class TypedContextPlugin(PluginBase[Any]):
    """Validate (and write back) the context when an interpreter starts --
    fresh OR restored from a snapshot.

    🏛️ `context_validator` runs after actions; nothing in core runs it on
    the initial or restored context. A snapshot round-trips `Decimal` as
    a string (`json.dumps(default=str)`), so a restored machine would hand
    its first action a ``"9.5"``. This plugin re-validates on
    `on_interpreter_start`, coercing values back to their model types and
    refusing an invalid context loudly. Attach it wherever you use
    `context_model`; `persisted(..., plugins=[TypedContextPlugin(Model)])`.
    """

    def __init__(self, model: Type[BaseModel]) -> None:
        self.model = model

    def on_interpreter_start(self, interpreter: Any) -> None:
        _validate_into(self.model, interpreter.context, True)


class PydanticCodec:
    """A store `SnapshotCodec` that serialises ``context`` through the
    model's JSON mode (`Decimal` → exact string, `datetime` → ISO 8601,
    enums → values) instead of the engine's ``default=str`` fallback, so
    nothing is lost at rest. Restoring the rich types is the job of
    `TypedContextPlugin` (values come back from JSON as strings/numbers
    that ``model_validate`` accepts). ``decode`` is the identity.
    """

    def __init__(self, model: Type[BaseModel]) -> None:
        self.model = model

    def encode(self, snapshot: str) -> str:
        blob = json.loads(snapshot)
        ctx = blob.get("context")
        if isinstance(ctx, dict):
            try:
                instance = self.model.model_validate(ctx)
            except ValidationError:
                return snapshot  # not ours to fix; store as-is
            typed = instance.model_dump(mode="json")
            for k, v in ctx.items():
                typed.setdefault(k, v)
            blob["context"] = typed
        return json.dumps(blob, default=str)

    def decode(self, data: str) -> str:
        return data
