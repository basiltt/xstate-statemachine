# src/xstate_statemachine/contrib/fastapi/router.py
# -----------------------------------------------------------------------------
# 🛣️ StatechartRouter -- a chart's public surface as an APIRouter + OpenAPI
# -----------------------------------------------------------------------------
# 🏛️ Every handler DELEGATES: sends go through `registry.send_event`
#    (authorize → Idempotency-Key → act() → ReceiptResponse / problem),
#    reads through `registry.peek`, streams through `transition_stream` and
#    `websocket_endpoint`. This module adds only FastAPI idioms: typed
#    bodies, `Depends`, operation ids and the OpenAPI response table.
#
# 🔐 X0.1 authorize runs on every route; X0.2 the principal comes from the
#    `actor` dependency, never the body; X0.7 bodies are JSON-only and
#    bounded, validation failures are problem+json listing only the field
#    location and error type (pydantic messages can echo the input).
#
# 📝 No `from __future__ import annotations`: handler annotations are the
#    dynamically built body types, which must be evaluated at `def` time.
# -----------------------------------------------------------------------------
"""`StatechartRouter` and `get_interpreter`."""

import inspect
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from fastapi import APIRouter, Body, Depends, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.params import Depends as DependsParam
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, PlainTextResponse, Response

from ...persistence.helpers import KeyNotFoundError
from ..pydantic.events import models_of
from ..starlette._http import (
    HTTPProblemError,
    IdempotencyNotConfiguredError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    idempotency_key_from,
    problem,
    problem_for_exception,
)
from ..starlette.streaming import transition_stream, websocket_endpoint
from ._models import (
    EventsModel,
    ReceiptModel,
    StateModel,
    problem_responses,
    send_body_type,
    user_events,
)

__all__ = ["StatechartRouter", "get_interpreter"]

_HAS_DEP_SCOPE = "scope" in inspect.signature(DependsParam.__init__).parameters
_SEND_RESPONSES: Dict[Any, Any] = {
    200: {"model": ReceiptModel, "description": "Receipt"},
    202: {"model": ReceiptModel, "description": "Deferred"},
    **problem_responses(403, 404, 409, 413, 415, 422, 500),
}


# -----------------------------------------------------------------------------
# 🧱 Route class: JSON-only bounded bodies + problem+json validation errors
# -----------------------------------------------------------------------------
def bounded_route_class(registry: Any) -> type:
    """The route class `StatechartRouter` uses, for routes you add BESIDE it.

    A hand-written route (the orders example's ``PAY`` with
    ``BackgroundTasks``) is otherwise outside the X0.7 envelope: FastAPI
    parses a 1 MB body and answers ``422`` instead of ``413``, and a
    ``text/plain`` body is not ``415``. ::

        extra = APIRouter(route_class=bounded_route_class(registry))
        @extra.post("/orders/{id}/events/PAY")
        async def pay(...): ...
        app.include_router(extra)

    📝 #266 battle (B): found by posting 1 MB to every POST route of the
    orders app's OpenAPI document.
    """
    return _problem_route_class(registry.max_body_bytes)


def _problem_route_class(max_body_bytes: int) -> type:
    class StatechartRoute(APIRoute):
        def get_route_handler(self) -> Callable[[Request], Any]:
            handler = super().get_route_handler()

            async def route(request: Request) -> Response:
                try:
                    if request.method in ("POST", "PUT", "PATCH"):
                        await _bounded_json(request, max_body_bytes)
                    return await handler(request)
                except RequestValidationError as exc:
                    return _validation_problem(exc)
                except HTTPProblemError as exc:
                    return problem_for_exception(exc)

            return route

    return StatechartRoute


async def _bounded_json(request: Request, limit: int) -> None:
    """Pre-read the body (cached on the request) enforcing X0.7."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise PayloadTooLargeError()
    chunks: List[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise PayloadTooLargeError()
        chunks.append(chunk)
    raw = b"".join(chunks)
    request._body = raw  # starlette's own cache: FastAPI reads it back
    if raw.strip():
        ctype = request.headers.get("content-type", "")
        if ctype.split(";", 1)[0].strip().lower() != "application/json":
            raise UnsupportedMediaTypeError(
                "Request body must be application/json"
            )


#: Most validation errors listed in one 422 problem body.
MAX_VALIDATION_ERRORS = 50


def _validation_problem(exc: RequestValidationError) -> Response:
    # 🔥 battle #276-a: a list of 10 000 bad items produced a 500 KB 422
    #    (one entry per item) -- an amplification lever on a bounded body.
    #    The first MAX_VALIDATION_ERRORS are listed; the total is reported.
    raw = exc.errors()
    errors = [
        {
            "loc": [str(p) for p in e.get("loc", ())],
            "type": str(e.get("type", "")),
        }
        for e in list(raw)[:MAX_VALIDATION_ERRORS]
    ]
    extra: Dict[str, Any] = {}
    if len(raw) > MAX_VALIDATION_ERRORS:
        extra["errors_total"] = len(raw)
    return problem(422, "Request validation failed", errors=errors, **extra)


# -----------------------------------------------------------------------------
# 🪝 Dependencies
# -----------------------------------------------------------------------------
def _default_actor(registry: Any) -> Callable[..., Any]:
    async def actor_from_request(request: Request) -> Optional[str]:
        return registry._principal_of(request)

    return actor_from_request


def _depends(fn: Callable[..., Any]) -> Any:
    # 💡 scope="function" (FastAPI >= 0.121) runs the exit code BEFORE the
    #    response is sent, so a save conflict becomes the response (409).
    if _HAS_DEP_SCOPE:
        return Depends(fn, scope="function")
    return Depends(fn)  # pragma: no cover -- old FastAPI


def get_interpreter(
    registry: Any,
    name: str,
    *,
    key: Any = "id",
    actor: Optional[Callable[..., Any]] = None,
    create_if_missing: bool = True,
) -> Any:
    """A ready-made ``Depends(...)`` yielding a started interpreter.

    Use it directly as the parameter default (it already IS a
    ``Depends``)::

        @app.post("/orders/{order_id}/pay")
        async def pay(order=get_interpreter(reg, "order", key="order_id")):
            return ReceiptResponse(order, await order.send("PAY", wait=True))

    The interpreter lives inside `registry.act()` for the request: saved
    with ``expected_version`` when the handler RETURNS, discarded (not
    saved) when it RAISES. Runs `authorize` with ``event=None``. Errors
    (`ConflictError` → 409, missing key → 404, 403 ...) propagate as the
    library's exceptions; `instrument_app` maps them to problem+json.

    Args:
        key: Path-parameter name, or ``(request) -> str``.
        actor: A FastAPI dependency returning the authenticated principal
            (idempotency scope, X0.2). Defaults to the registry's
            ``principal(conn)``.
        create_if_missing: ``False`` → an unknown key is 404.
    """
    key_of: Callable[[Request], Any] = (
        key if callable(key) else (lambda r: r.path_params[key])
    )
    actor_dep = actor or _default_actor(registry)

    async def interpreter_dependency(
        request: Request, principal: Optional[str] = Depends(actor_dep)
    ) -> Any:
        k = str(key_of(request))
        await registry.authorize(request, name, k, None)
        # 🔥 battle #276: the dependency never looked at `Idempotency-Key`
        #    -- a client sending it on a custom route got no dedup and no
        #    error. The header is validated here (400 malformed, 501 with
        #    no inbox); the HANDLER still has to pass it to `send(...,
        #    idempotency_key=request.state.xsm_idempotency_key)` -- it
        #    is exposed on `request.state` for that.
        idem = idempotency_key_from(request)
        if idem is not None and registry.inbox is None:
            raise IdempotencyNotConfiguredError()
        request.state.xsm_idempotency_key = idem
        if not create_if_missing and not await registry.exists(name, k):
            raise KeyNotFoundError(k)
        # 🔥 battle #276-a: two `get_interpreter(reg, name)` parameters on
        #    one route (e.g. one in a sub-dependency) are DIFFERENT
        #    dependencies to FastAPI, so each opened its own `act()` on the
        #    same key: both loaded version N, the second save was a
        #    self-inflicted 409. The first one opened for (name, key) in a
        #    request owns the save; the others share its interpreter.
        open_acts = getattr(request.state, "xsm_open_acts", None)
        if open_acts is None:
            open_acts = {}
            request.state.xsm_open_acts = open_acts
        if (name, k) in open_acts:
            yield open_acts[(name, k)]
            return
        async with registry.act(name, k, principal=principal) as interp:
            open_acts[(name, k)] = interp
            try:
                yield interp
            finally:
                open_acts.pop((name, k), None)

    return _depends(interpreter_dependency)


# -----------------------------------------------------------------------------
# 🛣️ The router
# -----------------------------------------------------------------------------
def StatechartRouter(  # noqa: N802 -- reads as a class, returns APIRouter
    registry: Any,
    name: str,
    *,
    prefix: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    key_param: str = "id",
    event_models: Optional[Sequence[Any]] = None,
    include_diagram: bool = True,
    create_if_missing: bool = True,
    operation_id_prefix: Optional[str] = None,
    dependencies: Sequence[Any] = (),
    per_event_dependencies: Optional[Mapping[str, Sequence[Any]]] = None,
    actor: Optional[Callable[..., Any]] = None,
) -> APIRouter:
    """An `APIRouter` exposing machine *name* of *registry*.

    Routes (``{id}`` is *key_param*): ``GET /{id}``, ``POST /{id}/send``,
    ``POST /{id}/events/<EVENT>`` (one per declared event),
    ``GET /{id}/events``, ``GET /{id}/diagram.mmd``, ``GET /{id}/stream``
    (SSE) and ``WS /{id}/ws``.

    Args:
        event_models: `EventModel` subclasses; the ``/send`` body becomes a
            discriminated union on ``type``. Defaults to the models behind
            the machine's ``events_union()`` schemas; with none, the body
            is ``{type: Literal[<declared>], payload: {...}}``.
        create_if_missing: ``False`` → ``GET`` / sends on an unknown key
            are 404 instead of starting a fresh instance.
        dependencies: FastAPI dependencies on every route (auth).
        per_event_dependencies: ``{EVENT: [...]}`` added to that event's
            ``/events/EVENT`` route. Such an event is REFUSED on ``/send``
            (403) so the extra gate cannot be bypassed.
        actor: Dependency returning the authenticated principal (X0.2).
    """
    machine = registry.machines[name]
    models: List[Any] = list(event_models or models_of(machine.event_schemas))
    by_type = {m.event_type(): m for m in models}
    gated = dict(per_event_dependencies or {})
    # 🔥 battle #276-a: a gate on a typo'd / undeclared event was silently
    #    dropped -- the author believed an event was protected that the
    #    router never routes. Silent acceptance is a bug: fail at build.
    unknown = sorted(set(gated) - set(user_events(machine)))
    if unknown:
        raise ValueError(
            f"per_event_dependencies names events {unknown} that machine "
            f"{name!r} does not declare"
        )
    op = operation_id_prefix or name
    base = f"/{name}" if prefix is None else prefix
    kp = "{" + key_param + "}"
    actor_dep = actor or _default_actor(registry)
    router = APIRouter(
        prefix=base,
        tags=list(tags) if tags else None,
        dependencies=list(dependencies),
        route_class=_problem_route_class(registry.max_body_bytes),
    )
    KeyPath = Path(..., alias=key_param)  # noqa: N806
    Actor = Depends(actor_dep)  # noqa: N806
    body_type: Any = send_body_type(name, machine, models)
    union_body = len(models) > 1

    def _body() -> Any:
        return Body(..., discriminator="type") if union_body else Body(...)

    async def _guard_read(request: Request, key: str) -> None:
        await registry.authorize(request, name, key, None)
        if not create_if_missing and not await registry.exists(name, key):
            raise KeyNotFoundError(key)

    async def _send(
        request: Request, key: str, etype: str, payload: Any, principal: Any
    ) -> Response:
        try:
            if not create_if_missing and not await registry.exists(name, key):
                raise KeyNotFoundError(key)
        except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
            return problem_for_exception(exc)
        return await registry.send_event(
            request, name, key, etype, payload, principal=principal
        )

    async def get_state(request: Request, key: str = KeyPath) -> Response:
        try:
            await _guard_read(request, key)
            body = await registry.peek(name, key)
        except Exception as exc:  # noqa: BLE001
            return problem_for_exception(exc)
        body["machine_version"] = machine.version or None
        return JSONResponse(body)

    async def send(
        request: Request,
        key: str = KeyPath,
        body: Any = _body(),
        principal: Optional[str] = Actor,
    ) -> Response:
        etype = str(body.type)
        if etype in gated:
            return problem(403, "Use this event's dedicated route")
        if models:
            payload = body.model_dump(mode="python", exclude={"type"})
        else:
            payload = dict(body.payload)
        return await _send(request, key, etype, payload, principal)

    # 💡 The body's REAL type is dynamic; FastAPI reads __annotations__.
    send.__annotations__["body"] = body_type

    async def list_events(request: Request, key: str = KeyPath) -> Response:
        try:
            await _guard_read(request, key)
            available = (await registry.peek(name, key))["available_events"]
        except Exception as exc:  # noqa: BLE001
            return problem_for_exception(exc)
        declared = [
            {
                "type": e,
                "schema": (
                    by_type[e].model_json_schema() if e in by_type else None
                ),
            }
            for e in user_events(machine)
        ]
        return JSONResponse({"available": available, "declared": declared})

    async def diagram(request: Request, key: str = KeyPath) -> Response:
        try:
            await registry.authorize(request, name, key, None)
        except Exception as exc:  # noqa: BLE001
            return problem_for_exception(exc)
        return PlainTextResponse(machine.to_mermaid())

    async def stream(request: Request, key: str = KeyPath) -> Response:
        return await transition_stream(registry, name, key, request)

    reads = problem_responses(403, 404, 500)
    router.add_api_route(
        f"/{kp}",
        get_state,
        methods=["GET"],
        operation_id=f"{op}_get",
        response_model=None,
        responses={200: {"model": StateModel}, **reads},
        summary=f"Current state of a {name}",
    )
    router.add_api_route(
        f"/{kp}/send",
        send,
        methods=["POST"],
        operation_id=f"{op}_send",
        response_model=None,
        responses=_SEND_RESPONSES,
        summary=f"Send any event to a {name}",
    )
    for etype in user_events(machine):
        router.add_api_route(
            f"/{kp}/events/{etype}",
            _event_handler(etype, by_type.get(etype), _send, KeyPath, Actor),
            methods=["POST"],
            operation_id=f"{op}_{_ident(etype)}",
            response_model=None,
            responses=_SEND_RESPONSES,
            dependencies=list(gated.get(etype, ())),
            summary=f"Send {etype}",
        )
    router.add_api_route(
        f"/{kp}/events",
        list_events,
        methods=["GET"],
        operation_id=f"{op}_events",
        response_model=None,
        responses={200: {"model": EventsModel}, **reads},
        summary="Events accepted now, and every declared event",
    )
    if include_diagram:
        router.add_api_route(
            f"/{kp}/diagram.mmd",
            diagram,
            methods=["GET"],
            operation_id=f"{op}_diagram",
            response_class=PlainTextResponse,
            responses=problem_responses(403),
            summary="Mermaid diagram of the chart",
        )
    router.add_api_route(
        f"/{kp}/stream",
        stream,
        methods=["GET"],
        operation_id=f"{op}_stream",
        response_model=None,
        responses={
            200: {"content": {"text/event-stream": {}}},
            **problem_responses(403, 429, 503),
        },
        summary="Server-Sent Events: snapshot, then each transition",
    )
    # 📝 Starlette's plain route: FastAPI's include_router re-prefixes it.
    router.add_websocket_route(
        f"{base}/{kp}/ws",
        websocket_endpoint(registry, name, key_param=key_param),
    )
    return router


def _ident(etype: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in etype).lower()


def _event_handler(
    etype: str,
    model: Optional[type],
    send: Callable[..., Any],
    key_path: Any,
    actor: Any,
) -> Callable[..., Any]:
    """``POST /{id}/events/<etype>`` -- optional body (its model, if any)."""
    if model is not None:

        async def handler(
            request: Request,
            key: str = key_path,
            body: Optional[model] = Body(None),  # type: ignore[valid-type]
            principal: Optional[str] = actor,
        ) -> Response:
            payload: Dict[str, Any] = (
                {}
                if body is None
                else body.model_dump(mode="python", exclude={"type"})
            )
            return await send(request, key, etype, payload, principal)

    else:

        async def handler(  # type: ignore[misc]
            request: Request,
            key: str = key_path,
            body: Optional[Dict[str, Any]] = Body(None),
            principal: Optional[str] = actor,
        ) -> Response:
            return await send(request, key, etype, body or {}, principal)

    handler.__name__ = f"send_{_ident(etype)}"
    return handler
