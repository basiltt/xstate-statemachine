# src/xstate_statemachine/contrib/fastapi/app.py
# -----------------------------------------------------------------------------
# 🧰 instrument_app -- probes, lifespan composition, problem handlers
# -----------------------------------------------------------------------------
# 🏛️ FastAPI takes `lifespan=` at construction; `compose_lifespan` lets a
#    user keep their own lifespan AND run `registry.lifespan` (timer
#    scanner, resident drain, subscriber close). `instrument_app` swaps the
#    composed lifespan in on an existing app via the router's
#    `lifespan_context`, which is what Starlette actually runs.
# -----------------------------------------------------------------------------
"""`instrument_app()` and `compose_lifespan()`."""

from __future__ import annotations

import contextlib
from typing import Any, AsyncIterator, Callable, Optional

from starlette.requests import Request
from starlette.responses import Response

from ...exceptions import XStateMachineError
from ..starlette._http import problem_for_exception, status_for_exception

__all__ = ["compose_lifespan", "instrument_app"]

Lifespan = Callable[[Any], Any]


def compose_lifespan(registry: Any, inner: Optional[Lifespan] = None) -> Any:
    """A lifespan running `registry.lifespan` around *inner* (if any).

    ``FastAPI(lifespan=compose_lifespan(reg, my_lifespan))``. The registry
    starts first and stops last, so the user's shutdown still has a
    working registry. A state yielded by *inner* is passed through.
    """

    @contextlib.asynccontextmanager
    async def lifespan(app: Any) -> AsyncIterator[Any]:
        async with registry.lifespan(app):
            if inner is None:
                yield None
            else:
                async with inner(app) as state:
                    yield state

    return lifespan


def instrument_app(
    app: Any,
    registry: Any,
    *,
    health_path: str = "/_xsm/health",
    ready_path: str = "/_xsm/ready",
    exception_handlers: bool = True,
) -> Any:
    """Wire *registry* into an existing FastAPI *app*.

    * mounts `registry.health_route` / `ready_route`;
    * wraps the app's current lifespan with `registry.lifespan`
      (call before the app starts);
    * with *exception_handlers*, maps the library's exceptions escaping a
      handler (e.g. a `get_interpreter` save conflict) to problem+json,
      and every `RequestValidationError` -- including those of routes you
      add yourself -- to the same `422` problem (field path + error type,
      never the offending value; X0.7).

    Returns *app*.
    """
    # 🔥 battle #276-a: a second call (e.g. a factory re-run) appended the
    #    probes twice and nested `registry.lifespan` in itself -- startup
    #    ran twice and the inner shutdown drained the registry while the
    #    outer was still "running". Instrumenting is once per registry.
    done = getattr(app.state, "xsm_instrumented", None)
    if done is None:
        done = set()
        app.state.xsm_instrumented = done
    if id(registry) in done:
        return app
    done.add(id(registry))
    app.router.routes.append(registry.health_route(health_path))
    app.router.routes.append(registry.ready_route(ready_path))
    inner = app.router.lifespan_context
    app.router.lifespan_context = compose_lifespan(registry, inner)
    if exception_handlers:

        async def handle(request: Request, exc: Exception) -> Response:
            if status_for_exception(exc) >= 500:
                import logging

                logging.getLogger(__name__).error(
                    "🔥 %s on %s", type(exc).__name__, request.url.path
                )
            return problem_for_exception(exc)

        app.add_exception_handler(XStateMachineError, handle)
        # 🛡️ #266 battle (X0.7): a route the APP adds beside the generated
        #    router (the orders example's `PAY` with BackgroundTasks) fell
        #    back to FastAPI's default 422 body, which echoes the offending
        #    `input` (a card token, a 1 MB string) and its full message.
        #    The router's own routes already answered with the problem
        #    shape (loc + type only); make it app-wide.
        from fastapi.exceptions import RequestValidationError

        from .router import _validation_problem

        async def handle_validation(
            request: Request, exc: Exception
        ) -> Response:
            if not isinstance(exc, RequestValidationError):  # pragma: no cover
                return problem_for_exception(exc)
            return _validation_problem(exc)

        # 📝 reviewer M2: an app that registered its OWN handler for
        #    RequestValidationError before `instrument_app` keeps it -- the
        #    library's value-free 422 is the default, not an override.
        from fastapi.exception_handlers import (
            request_validation_exception_handler as _fastapi_default,
        )

        current = app.exception_handlers.get(RequestValidationError)
        if current is None or current is _fastapi_default:
            app.add_exception_handler(
                RequestValidationError, handle_validation
            )
    return app
