# src/xstate_statemachine/contrib/fastapi/_models.py
# -----------------------------------------------------------------------------
# 🧾 OpenAPI-facing models: problem, state, receipt, the /send body union
# -----------------------------------------------------------------------------
# 🏛️ These models DESCRIBE what `[starlette]`'s helpers already emit
#    (`state_body`, `receipt_body`, `problem`). Handlers keep returning
#    those helpers' `JSONResponse`s -- the models exist so `app.openapi()`
#    documents the real wire shapes, never to re-serialise them.
#
# 📝 No `from __future__ import annotations` here: `create_model` and the
#    dynamic `Annotated[Union[...], Field(discriminator=...)]` must be real
#    objects, not strings FastAPI would try to resolve in our globals.
# -----------------------------------------------------------------------------
"""Response / problem / request-body models for the OpenAPI schema."""

from typing import Any, Dict, List, Literal, Optional, Sequence, Type, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

from ..pydantic.events import EventModel
from ..starlette._http import declared_events

__all__ = [
    "EventsModel",
    "Problem",
    "ReceiptModel",
    "StateModel",
    "send_body_type",
    "user_events",
]


class Problem(BaseModel):
    """RFC 9457 ``application/problem+json`` (X0.7: no exception text)."""

    model_config = ConfigDict(extra="allow")

    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    error: Optional[str] = Field(
        None, description="Exception class name (never its message)."
    )


class StateModel(BaseModel):
    """``GET /{id}`` -- state only unless a `context_serializer` is set."""

    model_config = ConfigDict(extra="allow")

    state: Any
    state_ids: List[str]
    available_events: List[str]
    machine_version: Optional[str] = None
    context: Optional[Any] = None


class ReceiptModel(StateModel):
    """The `ReceiptResponse` body of both POST routes."""

    changed: bool
    denied: bool
    deferred: bool
    duplicate: bool
    error: Optional[str] = None


class DeclaredEvent(BaseModel):
    type: str
    json_schema: Optional[Dict[str, Any]] = Field(None, alias="schema")


class EventsModel(BaseModel):
    """``GET /{id}/events``: what `can()` accepts now + what is declared."""

    available: List[str]
    declared: List[DeclaredEvent]


def user_events(machine: Any) -> List[str]:
    """Declared, client-sendable event names (sorted, deterministic)."""
    return declared_events(machine)


def send_body_type(
    name: str, machine: Any, models: Sequence[Type[EventModel]]
) -> Any:
    """The request-body type of ``POST /{id}/send``.

    With *models*: a discriminated union on ``type`` (one model -> the
    model itself). Without: the deterministic fallback
    ``{type: Literal[<declared events>], payload: dict}`` (review
    amendment) so the OpenAPI document is stable.
    """
    if models:
        if len(models) == 1:
            return models[0]
        # 💡 The router passes `Body(discriminator="type")`: FastAPI drops
        #    an `Annotated[..., Field(discriminator=)]` next to `Body()`.
        return Union[tuple(models)]  # type: ignore[valid-type]
    events = user_events(machine)
    etype: Any = Literal[tuple(events)] if events else str  # type: ignore
    # 🔥 battle #276-b: `"".join(capitalised "_" parts)` mapped `a_b` and
    #    `aB` to the same `ABEvent`; pydantic then emitted two schemas
    #    named `xstate_statemachine__contrib__...__ABEvent__1/__2` -- an
    #    unstable, leaky component name in every generated SDK. Keep every
    #    alnum char and spell the rest `_` (registry names are unique).
    safe = "".join(c if c.isalnum() else "_" for c in name)
    title = safe[:1].upper() + safe[1:]
    return create_model(
        f"{title}Event",
        __config__=ConfigDict(extra="forbid"),
        type=(etype, ...),
        payload=(Dict[str, Any], Field(default_factory=dict)),
    )


PROBLEM_CONTENT = {
    "application/problem+json": {
        "schema": {"$ref": "#/components/schemas/Problem"}
    }
}


def problem_responses(*statuses: int) -> Dict[Union[int, str], Any]:
    """``responses=`` entries documenting *statuses* as problem+json."""
    return {
        s: {"model": Problem, "content": PROBLEM_CONTENT} for s in statuses
    }
