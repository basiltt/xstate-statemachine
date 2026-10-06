# src/xstate_statemachine/contrib/starlette/_probes.py
"""Health / readiness routes for `StatechartRegistry` (split out of
`registry.py` to keep it under the file-size budget)."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from ._http import problem


class _ProbesMixin:
    started: bool
    draining: bool
    scanner: Any
    _astore: Any
    residents: Any

    # -- probes ----------------------------------------------------------------
    def health_route(self, path: str = "/_xsm/health") -> Route:
        """Liveness: 200 while the process can answer."""

        async def health(request: Request) -> Response:
            return JSONResponse({"status": "ok"})

        return Route(path, health, methods=["GET"])

    def ready_route(self, path: str = "/_xsm/ready") -> Route:
        """Readiness: 200 once `lifespan` started, the store answers and we
        are not draining; else a 503 problem."""

        async def ready(request: Request) -> Response:
            if not self.started or self.draining:
                return problem(503, "Not Ready")
            probe = getattr(self._astore, "health", None)
            if probe is not None:
                try:
                    info = await probe()
                except Exception as exc:  # noqa: BLE001
                    return problem(
                        503, "Store unavailable", error=type(exc).__name__
                    )
                if isinstance(info, dict) and info.get("ok") is False:
                    return problem(503, "Store unavailable")
            return JSONResponse(
                {
                    "status": "ready",
                    "residents": self.residents,
                    "timers": self.scanner is not None,
                }
            )

        return Route(path, ready, methods=["GET"])
