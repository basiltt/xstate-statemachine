# src/xstate_statemachine/contrib/_compat.py
# -----------------------------------------------------------------------------
# 🧷 require_extra -- the one way a contrib package declares its dependency
# -----------------------------------------------------------------------------
# 🏛️ Why a helper rather than a bare `import fastapi` at the top of each
#    subpackage: the failure a user hits is "I imported
#    xstate_statemachine.contrib.fastapi and got ModuleNotFoundError:
#    fastapi" -- which reads as OUR bug. `require_extra` turns it into a
#    `MissingExtraError` (also an `ImportError`) whose message is the exact
#    pip command, and records `extra`/`module` for programmatic handling.
#    It also gives `tests/contrib/test_extras_matrix.py` one seam to assert
#    against for every integration.
#
# 📝 Contract used by every subpackage's `__init__.py`:
#
#        from .._compat import require_extra
#        require_extra("fastapi", "fastapi", "starlette")
#
#    Import checks are cheap (`importlib.util.find_spec`), and run once per
#    process because the subpackage module is cached.
# -----------------------------------------------------------------------------
"""Dependency gate for optional integrations."""

from __future__ import annotations

import importlib.util
import math
from typing import Any, Iterable, Optional

from ..exceptions import MissingExtraError

__all__ = [
    "MissingExtraError",
    "extra_available",
    "origin_is_allowed",
    "positive_finite",
    "require_extra",
]


def extra_available(*modules: str) -> bool:
    """``True`` when every top-level *module* can be imported.

    Uses ``find_spec`` so nothing is actually imported -- safe to call from
    a module that must stay light when the dependency is absent.
    """
    try:
        return all(importlib.util.find_spec(m) is not None for m in modules)
    except (ImportError, ValueError):  # pragma: no cover -- broken finder
        return False


def positive_finite(
    name: str, value: Any, *, allow_zero: bool = False
) -> float:
    """Validate a duration / size option at construction time.

    🔥 Review (contrib-web CW-18): ``scanner_interval_s=0`` busy-spun a
    thread and ``max_body_bytes=-1`` answered 413 to every body -- both
    accepted silently. "Silent acceptance is a bug": a bad number fails
    where the registry is built, not on the first request.

    Args:
        name: The option name, for the error message.
        value: The candidate number (``bool`` and non-numbers are refused).
        allow_zero: Accept ``0`` (an option where zero means "off").

    Returns:
        *value* as a ``float``.

    Raises:
        ValueError: If *value* is not a finite number above zero (or at
            least zero with *allow_zero*).
    """
    ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    if ok:
        num = float(value)
        ok = math.isfinite(num) and (num >= 0 if allow_zero else num > 0)
    if not ok:
        bound = ">= 0" if allow_zero else "> 0"
        raise ValueError(f"{name} must be a finite number {bound}")
    return num


def origin_is_allowed(
    origin: Optional[str],
    host: Optional[str],
    allowed: Iterable[str] = (),
) -> bool:
    """X0.7 Origin rule shared by the ASGI and Flask/Quart adapters.

    📝 Review CW-33: the two copies compared host names case-sensitively
    (``Example.com`` vs ``example.com`` was a false refusal) and could
    drift apart. Host names are case-insensitive, so both sides are
    lower-cased here. The scheme is not compared: ``Host`` carries none,
    and a deployment that needs scheme-exact matching lists the full
    origin in ``allowed_origins``.

    Args:
        origin: The ``Origin`` header, or ``None`` (a non-browser client).
        host: The ``Host`` header.
        allowed: Exact origins accepted besides same-origin.

    Returns:
        ``True`` when the request may open a stream.
    """
    if origin is None:
        return True
    if origin in allowed:
        return True
    if not host:
        return False
    bare = origin.split("://", 1)[-1].rstrip("/")
    return bare.lower() == host.lower()


def require_extra(
    extra: str, *modules: str, hint: Optional[str] = None
) -> None:
    """Raise `MissingExtraError` unless every *module* is importable.

    Args:
        extra: The pip extra that provides the modules (``"fastapi"``).
        modules: Top-level module names to check (``"fastapi"``). Defaults
            to ``(extra,)`` when omitted.
        hint: Optional extra sentence appended to the error message (for
            soft dependencies that are not pinned as an extra, e.g.
            ``"or: pip install structlog"``).

    Raises:
        MissingExtraError: naming the first missing module and the extra.
    """
    names = modules or (extra,)
    for name in names:
        # 📝 #306: three failure modes, one typed error. `find_spec` returns
        #    None (not installed), raises ImportError (a finder / import
        #    policy refuses it), or succeeds while the actual import fails
        #    (installed but broken). All three read as OUR bug if they
        #    surface raw from the subpackage's own `import redis`.
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError) as exc:
            raise MissingExtraError(
                extra, name, hint=hint or f"(import refused: {exc})"
            ) from exc
        if spec is None:
            raise MissingExtraError(extra, name, hint=hint)
        try:
            importlib.import_module(name)
        except ImportError as exc:
            raise MissingExtraError(
                extra, name, hint=hint or f"(import failed: {exc})"
            ) from exc
