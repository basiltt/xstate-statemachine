# src/xstate_statemachine/cli/web_validation.py
# -----------------------------------------------------------------------------
# 🌐 Generation-time verification for the web companions
# -----------------------------------------------------------------------------
# `verify_generated(strict=False)` already proves the output PARSES. For the
# `pydantic-models` / `fastapi-router` companions that is not enough to trust
# a file whose whole point is to be imported by a web app, so -- when the
# extra is installed -- we go further, the same way the `pytest` scaffold
# records from the real engine:
#
#   * pydantic-models: import it; one `EventModel` per declared event;
#   * fastapi-router: import it (with the models module beside it, when it
#     is emitted in the same run), mount on a throwaway `FastAPI()`,
#     `app.openapi()` must succeed and list one route per declared event.
#
# An extra that is not installed is a NOTE, never a failure: the generator
# must work on a machine that will deploy the code elsewhere.
#
# 🛡️ Execution goes through `validation.exec_generated`, the single marked
#    `exec` (X0.2): only the generator's own freshly emitted output runs.
# -----------------------------------------------------------------------------
"""Import / mount / OpenAPI checks for generated web companions."""

from __future__ import annotations

import importlib.util
from typing import Dict, List, Optional, Tuple

from .validation import exec_generated

#: template -> module that must be importable to go beyond `ast.parse`.
REQUIRES = {"pydantic-models": "pydantic", "fastapi-router": "fastapi"}

#: Modules the generated code imports, loaded before it runs (see below).
_PRELOAD = {
    "pydantic-models": ("xstate_statemachine.contrib.pydantic",),
    "fastapi-router": (
        "fastapi.routing",
        "xstate_statemachine.contrib.pydantic",
        "xstate_statemachine.contrib.fastapi",
        "xstate_statemachine.persistence",
    ),
}


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):  # pragma: no cover -- broken env
        return False


def verify_web_companion(
    template: str,
    code: str,
    *,
    expected_events: int,
    siblings: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], Optional[str]]:
    """Returns ``(problems, note)``; *note* explains a skipped check."""
    need = REQUIRES.get(template)
    if need is None:
        return [], None
    if not _installed(need):
        return [], (
            f"{template}: `{need}` is not installed -- verified syntax only "
            f'(pip install "xstate-statemachine[{need}]" for the full check)'
        )
    problems: List[str] = []
    # 📝 Import the extra HERE, before the sandboxed exec: `exec_generated`
    #    drops every module first imported inside it, so a framework first
    #    imported by the generated code would be re-imported afterwards as
    #    a second copy whose classes the mounted routes are not instances of.
    importlib.import_module(need)
    for extra in _PRELOAD[template]:
        try:
            importlib.import_module(extra)
        except ImportError:  # reported by the exec below, with context
            pass
    module = exec_generated(code, template, problems, siblings=siblings)
    if module is None:
        return problems, None
    if template == "pydantic-models":
        n = len(getattr(module, "EVENT_MODELS", ()))
        if n != expected_events:
            problems.append(
                f"generated models declare {n} event model(s), "
                f"chart declares {expected_events}"
            )
        return problems, None
    return _check_router(module, expected_events), None


def _check_router(module: object, expected_events: int) -> List[str]:
    from fastapi import FastAPI

    router = getattr(module, "router", None)
    if router is None:
        return ["generated router module defines no `router`"]
    app = FastAPI()
    try:
        app.include_router(router)
        spec = app.openapi()
    except Exception as exc:  # noqa: BLE001 -- reported, not swallowed
        return [f"mounting the router failed: {type(exc).__name__}: {exc}"]
    routes = [
        p
        for p in spec.get("paths", {})
        if "/events/" in p and "{event}" not in p
    ]
    if len(routes) != expected_events:
        return [
            f"OpenAPI lists {len(routes)} event route(s), chart declares "
            f"{expected_events}"
        ]
    return []
