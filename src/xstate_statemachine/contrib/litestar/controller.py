# src/xstate_statemachine/contrib/litestar/controller.py
# -----------------------------------------------------------------------------
# 🛣️ create_statechart_controller -- the C2 route table as a Controller
# -----------------------------------------------------------------------------
# 🏛️ Same routes as `[fastapi]`'s StatechartRouter; every handler delegates
#    to the `[starlette]` registry through the `_edge` adapters.
#
# 🧷 Bodies: with pydantic `EventModel`s the `/send` body is a RootModel
#    over the discriminated union (Litestar/msgspec cannot decode a bare
#    union of several models); without pydantic models it is a msgspec
#    Struct ``{type: Literal[<declared>], payload: dict}``. Either way the
#    OpenAPI schema is generated and deterministic.
#
# 📝 No `from __future__ import annotations`: Litestar resolves handler
#    annotations, which here are dynamically built types.
# -----------------------------------------------------------------------------
"""`create_statechart_controller()`."""

from typing import Any, Callable, Dict, List, Literal, Optional, Sequence

import msgspec
from litestar import Controller, Request, Response, get, post, websocket
from litestar.connection import WebSocket
from litestar.exceptions import ValidationException

from ..starlette._http import (
    HTTPProblemError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    declared_events,
    problem,
    problem_for_exception,
)
from ..starlette.streaming import transition_stream, websocket_endpoint
from ._edge import to_litestar, to_starlette

__all__ = ["create_statechart_controller"]


def _ident(etype: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in etype).lower()


def _models_for(machine: Any, event_models: Optional[Sequence[Any]]) -> List:
    if event_models:
        return list(event_models)
    try:
        from ..pydantic.events import models_of
    except Exception:  # noqa: BLE001 -- pydantic is optional here
        return []
    return list(models_of(machine.event_schemas))


def _body_type(name: str, machine: Any, models: List[Any]) -> Any:
    title = "".join(p[:1].upper() + p[1:] for p in name.split("_"))
    if models:
        from typing import Annotated, Union

        from pydantic import Field, RootModel

        union: Any = (
            models[0]
            if len(models) == 1
            else Annotated[
                Union[tuple(models)],  # type: ignore[valid-type]
                Field(discriminator="type"),
            ]
        )
        body = type(f"{title}Event", (RootModel[union],), {})
        # 💡 `XStatePlugin` documents this as the bare discriminated union
        #    (the wire shape), not as `{root: ...}`.
        body.__xsm_union__ = tuple(models)  # type: ignore[attr-defined]
        return body
    events = declared_events(machine)
    etype: Any = Literal[tuple(events)] if events else str  # type: ignore
    return msgspec.defstruct(
        f"{title}Event",
        [("type", etype), ("payload", Dict[str, Any], {})],
        forbid_unknown_fields=True,
    )


def _split(body: Any) -> "tuple[str, Dict[str, Any]]":
    """``(event_type, payload)`` from either body flavour."""
    root = getattr(body, "root", None)
    if root is not None:
        return str(root.type), root.model_dump(mode="python", exclude={"type"})
    return str(body.type), dict(body.payload)


def _validation_problem(request: Any, exc: ValidationException) -> Any:
    extra = exc.extra if isinstance(exc.extra, list) else []
    errors = [
        {"key": str(e.get("key", "")), "source": str(e.get("source", ""))}
        for e in extra
        if isinstance(e, dict)
    ]
    return to_litestar(
        problem(422, "Request validation failed", errors=errors)
    )


def _http_problem(request: Any, exc: Exception) -> Any:
    return to_litestar(problem_for_exception(exc))


def _json_guard(limit: int) -> Callable[..., Any]:
    async def before(request: Request) -> None:  # type: ignore[type-arg]
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise PayloadTooLargeError()
        raw = await request.body()
        if len(raw) > limit:
            raise PayloadTooLargeError()
        if raw.strip():
            ctype = request.headers.get("content-type", "")
            if ctype.split(";", 1)[0].strip().lower() != "application/json":
                raise UnsupportedMediaTypeError(
                    "Request body must be application/json"
                )

    return before


def create_statechart_controller(
    registry: Any,
    name: str,
    *,
    path: Optional[str] = None,
    key_param: str = "id",
    tags: Optional[Sequence[str]] = None,
    event_models: Optional[Sequence[Any]] = None,
    include_diagram: bool = True,
    create_if_missing: bool = True,
    operation_id_prefix: Optional[str] = None,
) -> type:
    """A `Controller` subclass exposing machine *name* of *registry*.

    Routes (``{id}`` is *key_param*): ``GET /{id}``, ``POST /{id}/send``,
    ``POST /{id}/events/<EVENT>`` per declared event, ``GET /{id}/events``,
    ``GET /{id}/diagram.mmd``, ``GET /{id}/stream`` (SSE), ``WS /{id}/ws``.
    Status mapping, idempotency and authorization are the registry's.
    """
    machine = registry.machines[name]
    models = _models_for(machine, event_models)
    by_type = {m.event_type(): m for m in models}
    op = operation_id_prefix or name
    kp = "{" + key_param + ":str}"
    body_t = _body_type(name, machine, models)
    ws_endpoint = websocket_endpoint(registry, name, key_param=key_param)

    def key_of(request: Any) -> str:
        return str(request.path_params[key_param])

    async def guard_read(conn: Any, key: str) -> None:
        await registry.authorize(conn, name, key, None)
        if not create_if_missing and not await registry.exists(name, key):
            from ...persistence.helpers import KeyNotFoundError

            raise KeyNotFoundError(key)

    async def do_send(request: Any, etype: str, payload: Any) -> Any:
        conn = to_starlette(request)
        key = key_of(request)
        if not create_if_missing and not await registry.exists(name, key):
            from ...persistence.helpers import KeyNotFoundError

            return to_litestar(problem_for_exception(KeyNotFoundError(key)))
        resp = await registry.send_event(conn, name, key, etype, payload)
        return to_litestar(resp)

    async def get_state(self: Any, request: Request) -> Response:  # type: ignore[type-arg]
        conn = to_starlette(request)
        key = key_of(request)
        try:
            await guard_read(conn, key)
            body = await registry.peek(name, key)
        except Exception as exc:  # noqa: BLE001
            return to_litestar(problem_for_exception(exc))  # type: ignore
        body["machine_version"] = machine.version or None
        return Response(body)

    async def send(self: Any, request: Request, data: Any) -> Response:  # type: ignore[type-arg]
        etype, payload = _split(data)
        return await do_send(request, etype, payload)  # type: ignore

    send.__annotations__["data"] = body_t

    async def list_events(self: Any, request: Request) -> Response:  # type: ignore[type-arg]
        conn = to_starlette(request)
        key = key_of(request)
        try:
            await guard_read(conn, key)
            available = (await registry.peek(name, key))["available_events"]
        except Exception as exc:  # noqa: BLE001
            return to_litestar(problem_for_exception(exc))  # type: ignore
        declared = [
            {
                "type": e,
                "schema": (
                    by_type[e].model_json_schema() if e in by_type else None
                ),
            }
            for e in declared_events(machine)
        ]
        return Response({"available": available, "declared": declared})

    async def diagram(self: Any, request: Request) -> Response:  # type: ignore[type-arg]
        try:
            await registry.authorize(
                to_starlette(request), name, key_of(request), None
            )
        except Exception as exc:  # noqa: BLE001
            return to_litestar(problem_for_exception(exc))  # type: ignore
        return Response(machine.to_mermaid(), media_type="text/plain")

    async def stream(self: Any, request: Request) -> Any:  # type: ignore[type-arg]
        resp = await transition_stream(
            registry, name, key_of(request), to_starlette(request)
        )
        return to_litestar(resp)

    async def ws(self: Any, socket: WebSocket) -> None:  # type: ignore[type-arg]
        scope: Any = socket.scope
        await ws_endpoint(scope, socket.receive, socket.send)  # type: ignore

    ns: Dict[str, Any] = {
        "path": path if path is not None else f"/{name}",
        "tags": list(tags) if tags else None,
        "before_request": _json_guard(registry.max_body_bytes),
        "exception_handlers": {
            ValidationException: _validation_problem,
            HTTPProblemError: _http_problem,
        },
        "get_state": get(
            f"/{kp}", operation_id=f"{op}_get", summary=f"Current {name}"
        )(get_state),
        "send": post(
            f"/{kp}/send",
            operation_id=f"{op}_send",
            status_code=200,
            summary=f"Send any event to a {name}",
        )(send),
        "list_events": get(
            f"/{kp}/events", operation_id=f"{op}_events", summary="Events"
        )(list_events),
        "stream": get(
            f"/{kp}/stream", operation_id=f"{op}_stream", summary="SSE"
        )(stream),
        "ws": websocket(f"/{kp}/ws")(ws),
    }
    if include_diagram:
        ns["diagram"] = get(
            f"/{kp}/diagram.mmd",
            operation_id=f"{op}_diagram",
            media_type="text/plain",
            summary="Mermaid diagram",
        )(diagram)
    for etype in declared_events(machine):
        attr = f"send_{_ident(etype)}"
        ns[attr] = post(
            f"/{kp}/events/{etype}",
            operation_id=f"{op}_{_ident(etype)}",
            status_code=200,
            summary=f"Send {etype}",
        )(_event_handler(etype, by_type.get(etype), do_send))
    title = "".join(p[:1].upper() + p[1:] for p in name.split("_"))
    return type(f"{title}StatechartController", (Controller,), ns)


def _event_handler(
    etype: str, model: Optional[Any], do_send: Callable[..., Any]
) -> Callable[..., Any]:
    """``POST /{id}/events/<etype>`` with an optional body."""

    async def handler(self: Any, request: Request, data: Any = None) -> Response:  # type: ignore[type-arg]
        if data is None:
            payload: Dict[str, Any] = {}
        elif model is not None:
            payload = data.model_dump(mode="python", exclude={"type"})
        else:
            payload = dict(data)
        return await do_send(request, etype, payload)  # type: ignore

    handler.__annotations__["data"] = (
        Optional[model] if model is not None else Optional[Dict[str, Any]]
    )
    handler.__name__ = f"send_{_ident(etype)}"
    return handler
