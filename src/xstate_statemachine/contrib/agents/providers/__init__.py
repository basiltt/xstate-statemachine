# src/xstate_statemachine/contrib/agents/providers/__init__.py
# -----------------------------------------------------------------------------
# 🔌 Provider adapters -- SDK objects in, `ModelResponse` out
# -----------------------------------------------------------------------------
# 🏛️ The SDKs are SOFT imports: nothing here imports `openai` or
#    `anthropic` at module level, and the `[agents]` extra never pins them.
#    Each factory imports its SDK only to fail early with a
#    `MissingExtraError` naming the exact `pip install`, and the mapping
#    functions work on plain attribute/dict access so they can be
#    contract-tested against recorded JSON fixtures with no SDK present.
# -----------------------------------------------------------------------------
"""Adapters for provider SDKs (soft imports)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ....exceptions import MissingExtraError

__all__ = ["require_sdk", "field", "price"]


def require_sdk(module: str) -> None:
    """Raise `MissingExtraError` unless *module* imports."""
    try:
        __import__(module)
    except ImportError as exc:
        err = MissingExtraError(
            "agents",
            module,
            hint=f"The provider SDK is separate: " f"pip install {module}",
        )
        raise err from exc


def field(obj: Any, name: str, default: Any = None) -> Any:
    """``obj.name`` or ``obj[name]`` -- SDK objects and fixtures alike."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def price(
    prices: Optional[Mapping[str, float]], tokens_in: int, tokens_out: int
) -> float:
    """Cost in USD from ``{"input_per_mtok": .., "output_per_mtok": ..}``.

    Providers do not return cost; the caller supplies its price sheet.
    ``None`` → ``0.0`` (cost budgets then only see what you price).
    """
    if not prices:
        return 0.0
    return (
        tokens_in * float(prices.get("input_per_mtok", 0.0))
        + tokens_out * float(prices.get("output_per_mtok", 0.0))
    ) / 1_000_000.0
