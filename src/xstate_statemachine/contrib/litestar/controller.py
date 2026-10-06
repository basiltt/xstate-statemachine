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

import re
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence

import msgspec
from litestar import Controller, Request, Response, get, post, websocket
from litestar.connection import WebSocket
from litestar.exceptions import ValidationException

from .._openapi import ident as _ident
from .._openapi import operation_ids
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


#: Most validation errors listed in one 422 problem body (as `[fastapi]`).
MAX_VALIDATION_ERRORS = 50
_UNKNOWN_FIELD = re.compile(r"unknown field `([^`]{1,64})`")


class Problem(msgspec.Struct, kw_only=True):
    """RFC 9457 problem body (what every non-2xx answer carries)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    error: Optional[str] = None
    errors: Optional[List[Dict[str, str]]] = None
    errors_total: Optional[int] = None


class StateBody(msgspec.Struct, kw_only=True):
    """``GET /{id}`` -- state only; ``context`` exists only when the
    registry has a `context_serializer` (X0.1: never promised fields)."""

    state: Any
    state_ids: List[str]
    available_events: List[str]
    machine_version: Optional[str] = None
    context: Optional[Any] = None


class ReceiptBody(StateBody, kw_only=True):
    """The `ReceiptResponse` body of both POST routes."""

    changed: bool
    denied: bool
    deferred: bool
    duplicate: bool
    error: Optional[str] = None


class DeclaredEvent(msgspec.Struct):
    type: str
    schema: Optional[Dict[str, Any]] = None


class EventsBody(msgspec.Struct):
    """``GET /{id}/events``."""

    available: List[str]
    declared: List[DeclaredEvent]


def _ok(container: Any) -> Dict[int, Any]:
    """🔥 battle #278-b: the handlers return a bare `Response`, so 200 was
    documented as ``schema: {}`` -- an SDK got no types. Typed like the
    `[fastapi]` router's StateModel / ReceiptModel / EventsModel."""
    from litestar.openapi.datastructures import ResponseSpec

    return {
        200: ResponseSpec(
            data_container=container,
            description="OK",
            generate_examples=False,
        )
    }


def _problem_responses(*statuses: int) -> Dict[int, Any]:
    """🔥 battle #278: Litestar's document listed only 200 / 400 for every
    route -- 409 (denied / conflict), 422, 401, 403, 404, 413, 415, 501
    and 503, all of which the routes answer, were undocumented."""
    from litestar.openapi.datastructures import ResponseSpec
    from litestar.openapi.spec import Example

    return {
        code: ResponseSpec(
            data_container=Problem,
            description=_REASONS.get(code, "Problem"),
            media_type="application/problem+json",
            # 🔥 battle #278-b: Litestar generated RANDOM msgspec examples
            #    for `Problem` (``"title": "JIgNZYFc..."``) -- the served
            #    document changed on every start. The example is pinned.
            generate_examples=False,
            examples=[
                Example(
                    summary="problem",
                    value={
                        "type": "about:blank",
                        "title": _REASONS.get(code, "Problem"),
                        "status": code,
                    },
                )
            ],
        )
        for code in statuses
    }


_REASONS = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    413: "Content Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Content",
    429: "Too Many Requests",
    501: "Not Implemented",
    503: "Service Unavailable",
}
_SEND_STATUSES = (400, 401, 403, 404, 409, 413, 415, 422, 501, 503)
_READ_STATUSES = (400, 401, 403, 404, 503)


def _models_for(machine: Any, event_models: Optional[Sequence[Any]]) -> List:
    if event_models:
        return list(event_models)
    try:
        from ..pydantic.events import models_of
    except Exception:  # noqa: BLE001 -- pydantic is optional here
        return []
    return list(models_of(machine.event_schemas))


def _title(name: str) -> str:
    """🔥 battle #278-b: ``a_b`` and ``aB`` both became ``AB`` -- two
    controllers' ``/send`` bodies shared ONE component (``ABEvent``), so
    one route documented the other machine's events. Same rule as the
    `[fastapi]` fallback: keep every alnum char, spell the rest ``_``."""
    safe = "".join(c if c.isalnum() else "_" for c in name)
    return safe[:1].upper() + safe[1:]


def _body_type(name: str, machine: Any, models: List[Any]) -> Any:
    title = _title(name)
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
        # 🔥 battle #278-b: by_alias -- the engine re-validates with the
        #    same model, which only knows the ALIAS (an aliased field was
        #    a 422 on a valid body; the #276 fix, ported).
        return str(root.type), root.model_dump(
            mode="python", by_alias=True, exclude={"type"}
        )
    return str(body.type), dict(body.payload)


def _validation_problem(request: Any, exc: ValidationException) -> Any:
    """422 problem listing WHERE the body is wrong, never a value.

    🔥 battle #278-b: an unknown top-level key was reported as
    ``{"key": "data"}`` (msgspec names the whole body); the offending key
    is now named. Litestar's ``message`` is dropped -- it can quote input.
    At most `MAX_VALIDATION_ERRORS` entries, plus ``errors_total``.
    """
    raw = exc.extra if isinstance(exc.extra, list) else []
    raw = [e for e in raw if isinstance(e, dict)]
    errors = []
    for e in raw[:MAX_VALIDATION_ERRORS]:
        key = str(e.get("key", ""))
        hit = _UNKNOWN_FIELD.search(str(e.get("message", "")))
        if hit:
            key = hit.group(1)
        errors.append({"key": key, "source": str(e.get("source", ""))})
    extra: Dict[str, Any] = {}
    if len(raw) > MAX_VALIDATION_ERRORS:
        extra["errors_total"] = len(raw)
    return to_litestar(
        problem(422, "Request validation failed", errors=errors, **extra)
    )


def _http_problem(request: Any, exc: Exception) -> Any:
    return to_litestar(problem_for_exception(exc))


def _json_guard(limit: int) -> Callable[..., Any]:
    async def before(request: Request) -> None:  # type: ignore[type-arg]
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise PayloadTooLargeError()
        # 🔥 battle #278-a: a chunked body (no content-length) was read
        #    WHOLE into memory before the size check. Stop at limit+1.
        chunks: List[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise PayloadTooLargeError()
            chunks.append(chunk)
        raw = b"".join(chunks)
        request._body = raw  # what `request.body()` / the edge reuse
        request._connection_state.body = raw
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
    exclude_events: Sequence[str] = (),
    guards: Sequence[Any] = (),
    dependencies: Optional[Dict[str, Any]] = None,
) -> type:
    """A `Controller` subclass exposing machine *name* of *registry*.

    Routes (``{id}`` is *key_param*): ``GET /{id}``, ``POST /{id}/send``,
    ``POST /{id}/events/<EVENT>`` per declared event, ``GET /{id}/events``,
    ``GET /{id}/diagram.mmd``, ``GET /{id}/stream`` (SSE), ``WS /{id}/ws``.
    Status mapping, idempotency and authorization are the registry's.

    Args:
        exclude_events: 🔥 battle #278 -- events whose ``/events/<EVENT>``
            route the APP owns (a payment route with a side-effect hook).
            Litestar refuses two handlers on one path, so unlike FastAPI
            the app cannot shadow a generated route; it excludes it here
            and registers its own. Such an event is also REFUSED on
            ``/send`` (403) so the app's route cannot be bypassed -- gate
            it in `registry.authorize` too, which every route goes
            through. Unknown names are a `ValueError`.
        guards: Litestar guards applied to every route of the controller.
        dependencies: Litestar ``Provide`` mapping for every route.
    """
    machine = registry.machines[name]
    models = _models_for(machine, event_models)
    by_type = {m.event_type(): m for m in models}
    excluded = frozenset(exclude_events)
    unknown = sorted(excluded - set(declared_events(machine)))
    if unknown:
        raise ValueError(
            f"exclude_events= names events {name!r} does not declare: "
            f"{unknown}"
        )
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
        if etype in excluded:
            return to_litestar(  # type: ignore[return-value]
                problem(403, "Use this event's dedicated route")
            )
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
        # 🔥 battle #278-a: with create_if_missing=False `/stream` opened
        #    an endless SSE for a key that does not exist (every other
        #    route answered 404).
        try:
            await guard_read(to_starlette(request), key_of(request))
        except Exception as exc:  # noqa: BLE001
            return to_litestar(problem_for_exception(exc))
        resp = await transition_stream(
            registry, name, key_of(request), to_starlette(request)
        )
        return to_litestar(resp)

    async def ws(self: Any, socket: WebSocket) -> None:  # type: ignore[type-arg]
        scope: Any = socket.scope
        # 🔥 battle #278-a: with create_if_missing=False the socket opened
        #    (and a send CREATED the instance). Refused like a denied one.
        if not create_if_missing and not await registry.exists(
            name, str(scope["path_params"][key_param])
        ):
            await socket.close(code=1008)
            return
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
            f"/{kp}",
            operation_id=f"{op}_get",
            summary=f"Current {name}",
            responses={
                **_ok(StateBody),
                **_problem_responses(*_READ_STATUSES),
            },
        )(get_state),
        "send": post(
            f"/{kp}/send",
            operation_id=f"{op}_send",
            status_code=200,
            summary=f"Send any event to a {name}",
            responses={
                **_ok(ReceiptBody),
                **_problem_responses(*_SEND_STATUSES),
            },
        )(send),
        "list_events": get(
            f"/{kp}/events",
            operation_id=f"{op}_events",
            summary="Events",
            responses={
                **_ok(EventsBody),
                **_problem_responses(*_READ_STATUSES),
            },
        )(list_events),
        "stream": get(
            f"/{kp}/stream",
            operation_id=f"{op}_stream",
            summary="SSE",
            responses=_problem_responses(400, 401, 403, 404, 429, 503),
        )(stream),
        "ws": websocket(f"/{kp}/ws")(ws),
    }
    if include_diagram:
        ns["diagram"] = get(
            f"/{kp}/diagram.mmd",
            operation_id=f"{op}_diagram",
            media_type="text/plain",
            summary="Mermaid diagram",
            responses=_problem_responses(401, 403),
        )(diagram)
    if guards:
        ns["guards"] = list(guards)
    if dependencies:
        ns["dependencies"] = dict(dependencies)
    # 🔥 battle #278-b: ids (and attribute names) were `_ident(etype)`:
    #    ``ORDER.PAID``/``ORDER_PAID`` overwrote each other's handler and
    #    an event ``get`` duplicated ``<op>_get`` -- /schema answered 500.
    op_ids = operation_ids(op, declared_events(machine))
    for etype in declared_events(machine):
        if etype in excluded:
            continue
        attr = f"event_{op_ids[etype]}"
        ns[attr] = post(
            f"/{kp}/events/{etype}",
            operation_id=op_ids[etype],
            status_code=200,
            summary=f"Send {etype}",
            responses={
                **_ok(ReceiptBody),
                **_problem_responses(*_SEND_STATUSES),
            },
        )(_event_handler(etype, by_type.get(etype), do_send))
    return type(f"{_title(name)}StatechartController", (Controller,), ns)


def _event_handler(
    etype: str, model: Optional[Any], do_send: Callable[..., Any]
) -> Callable[..., Any]:
    """``POST /{id}/events/<etype>`` with an optional body."""

    async def handler(self: Any, request: Request, data: Any = None) -> Response:  # type: ignore[type-arg]
        if data is None:
            payload: Dict[str, Any] = {}
        elif model is not None:
            payload = data.model_dump(
                mode="python", by_alias=True, exclude={"type"}
            )
        else:
            payload = dict(data)
        return await do_send(request, etype, payload)  # type: ignore

    handler.__annotations__["data"] = (
        Optional[model] if model is not None else Optional[Dict[str, Any]]
    )
    handler.__name__ = f"send_{_ident(etype)}"
    return handler
