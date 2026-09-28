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
      handler (e.g. a `get_interpreter` save conflict) to problem+json.

    Returns *app*.
    """
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
    return app
