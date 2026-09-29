# src/xstate_statemachine/contrib/litestar/plugin.py
# -----------------------------------------------------------------------------
# 🧩 XStatePlugin -- lifespan, `Provide` dependency, probes, problem mapping
# -----------------------------------------------------------------------------
"""`XStatePlugin` (an `InitPluginProtocol`) and `get_interpreter`."""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Callable, Optional

from litestar import Request, Response, get
from litestar.config.app import AppConfig
from litestar.di import Provide
from litestar.plugins import InitPluginProtocol, OpenAPISchemaPluginProtocol

from ...exceptions import XStateMachineError
from ...persistence.helpers import KeyNotFoundError
from ..starlette._http import problem_for_exception, status_for_exception
from ._edge import to_litestar, to_starlette

__all__ = ["XStatePlugin", "get_interpreter"]

logger = logging.getLogger(__name__)


def get_interpreter(
    registry: Any,
    name: str,
    *,
    key: Any = "id",
    create_if_missing: bool = True,
) -> Provide:
    """``Provide(...)`` yielding a started interpreter inside `act()`.

    ::

        @post("/orders/{order_id:str}/pay",
              dependencies={"order": get_interpreter(reg, "order",
                                                     key="order_id")})
        async def pay(order: Any) -> Response: ...

    Saved with ``expected_version`` when the handler returns, NOT saved
    when it raises. Runs `authorize` with ``event=None``; the principal is
    the registry's ``principal(conn)`` (X0.2). *key* is a path-parameter
    name or ``(request) -> str``.
    """
    key_of: Callable[[Any], Any] = (
        key if callable(key) else (lambda r: r.path_params[key])
    )

    async def interpreter_dependency(
        request: Request,  # type: ignore[type-arg]
    ) -> AsyncGenerator[Any, None]:
        conn = to_starlette(request)
        k = str(key_of(request))
        await registry.authorize(conn, name, k, None)
        if not create_if_missing and not await registry.exists(name, k):
            raise KeyNotFoundError(k)
        principal = registry._principal_of(conn)
        async with registry.act(name, k, principal=principal) as interp:
            yield interp

    return Provide(interpreter_dependency)


def _problem_handler(request: Any, exc: Exception) -> Any:
    if status_for_exception(exc) >= 500:
        logger.error("🔥 %s on %s", type(exc).__name__, request.url.path)
    return to_litestar(problem_for_exception(exc))


class XStatePlugin(InitPluginProtocol, OpenAPISchemaPluginProtocol):
    """Register a `StatechartRegistry` on a Litestar app.

    ``Litestar(route_handlers=[...], plugins=[XStatePlugin(registry)])``

    * appends ``registry.lifespan`` to the app's lifespan (timer scanner,
      resident drain, subscriber close);
    * mounts ``GET health_path`` / ``ready_path`` probes;
    * maps every `XStateMachineError` escaping a handler to
      ``application/problem+json`` (a save conflict → 409);
    * documents a controller's ``/send`` body as the discriminated union
      of its event models (``oneOf`` + ``discriminator: type``);
    * with *dependencies=True*, adds one app-level dependency per machine:
      ``{dependency_prefix}{name}`` → `get_interpreter(registry, name,
      key=key_param)`.
    """

    def __init__(
        self,
        registry: Any,
        *,
        dependencies: bool = False,
        key_param: str = "id",
        dependency_prefix: str = "",
        health_path: Optional[str] = "/_xsm/health",
        ready_path: Optional[str] = "/_xsm/ready",
    ) -> None:
        self.registry = registry
        self.dependencies = dependencies
        self.key_param = key_param
        self.dependency_prefix = dependency_prefix
        self.health_path = health_path
        self.ready_path = ready_path

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return isinstance(value, type) and hasattr(value, "__xsm_union__")

    def to_openapi_schema(
        self, field_definition: Any, schema_creator: Any
    ) -> Any:
        from litestar.openapi.spec import Discriminator, Schema
        from litestar.typing import FieldDefinition

        models = field_definition.annotation.__xsm_union__
        refs = [
            schema_creator.for_field_definition(
                FieldDefinition.from_annotation(m)
            )
            for m in models
        ]
        if len(refs) == 1:
            return refs[0]
        return Schema(
            one_of=refs, discriminator=Discriminator(property_name="type")
        )

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        reg = self.registry
        app_config.lifespan.append(reg.lifespan)
        app_config.exception_handlers.setdefault(
            XStateMachineError, _problem_handler
        )
        if self.dependencies:
            for name in reg.machines:
                app_config.dependencies[f"{self.dependency_prefix}{name}"] = (
                    get_interpreter(reg, name, key=self.key_param)
                )
        if self.health_path:
            health = reg.health_route(self.health_path).endpoint

            @get(self.health_path, include_in_schema=False)
            async def xsm_health(request: Request) -> Response:  # type: ignore[type-arg]
                return to_litestar(await health(to_starlette(request)))

            app_config.route_handlers.append(xsm_health)
        if self.ready_path:
            ready = reg.ready_route(self.ready_path).endpoint

            @get(self.ready_path, include_in_schema=False)
            async def xsm_ready(request: Request) -> Response:  # type: ignore[type-arg]
                return to_litestar(await ready(to_starlette(request)))

            app_config.route_handlers.append(xsm_ready)
        return app_config
