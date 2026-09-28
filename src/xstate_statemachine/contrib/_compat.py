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
from typing import Optional

from ..exceptions import MissingExtraError

__all__ = ["MissingExtraError", "require_extra", "extra_available"]


def extra_available(*modules: str) -> bool:
    """``True`` when every top-level *module* can be imported.

    Uses ``find_spec`` so nothing is actually imported -- safe to call from
    a module that must stay light when the dependency is absent.
    """
    try:
        return all(importlib.util.find_spec(m) is not None for m in modules)
    except (ImportError, ValueError):  # pragma: no cover -- broken finder
        return False


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
