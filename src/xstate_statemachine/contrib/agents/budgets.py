# src/xstate_statemachine/contrib/agents/budgets.py
# -----------------------------------------------------------------------------
# 💰 Budgets -- per-agent limits and the guards that enforce them (#287)
# -----------------------------------------------------------------------------
# 🏛️ Budgets are GUARDS on the single way into a model turn
#    (`checking_budget`), so no path reaches the model over budget. The
#    amounts they compare come from provider-reported usage, which is
#    untrusted input: `_spent_tokens` / `_spent_usd` clamp it so a hostile
#    or buggy provider can neither refund a budget (negative counts) nor
#    disable it (NaN). Split out of `core.py` to keep that file < 800 lines.
# -----------------------------------------------------------------------------
"""Agent budgets: `Budget`, `budget_guards` and usage sanitising."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union

from ...machine_logic import MachineLogic
from .messages import AgentConfigError

__all__ = ["Budget", "budget_guards"]


@dataclass(frozen=True)
class Budget:
    """Per-agent limits. ``None`` means "no limit on this axis"."""

    max_tokens: Optional[int] = None
    max_usd: Optional[float] = None
    max_turns: Optional[int] = 10

    def __post_init__(self) -> None:
        # 🔥 #287 battle (A): budgets were never validated -- "20" made
        #    every guard raise, True was a turn limit of 1, NaN refused
        #    every turn. A limit is a non-negative finite number or None.
        for name in ("max_tokens", "max_usd", "max_turns"):
            v = getattr(self, name)
            if v is None:
                continue
            ok = isinstance(v, (int, float)) and not isinstance(v, bool)
            if name != "max_usd":
                ok = ok and isinstance(v, int)
            if not ok or not math.isfinite(v) or v < 0:
                raise AgentConfigError(
                    f"Budget.{name} must be a non-negative "
                    f"{'number' if name == 'max_usd' else 'int'} or None "
                    f"(got {v!r})"
                )

    @classmethod
    def coerce(
        cls, value: Union["Budget", Mapping[str, Any], None]
    ) -> "Budget":
        if value is None:
            return cls()
        if isinstance(value, Budget):
            return value
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise AgentConfigError(f"invalid budgets: {exc}") from None


def budget_guards(
    max_tokens: Optional[int] = None,
    max_usd: Optional[float] = None,
    max_turns: Optional[int] = None,
) -> MachineLogic:
    """``underTokenBudget`` / ``underCostBudget`` / ``underTurnLimit``.

    Each is ``True`` while the SPENT amount is strictly below the limit, so
    a turn is refused once the limit is reached -- the chart checks them on
    the only way into `awaiting_model`.
    """

    def under_tokens(ctx: Dict[str, Any], e: Any) -> bool:
        if max_tokens is None:
            return True
        spent = int(ctx.get("tokens_in", 0)) + int(ctx.get("tokens_out", 0))
        return spent < max_tokens

    def under_cost(ctx: Dict[str, Any], e: Any) -> bool:
        return max_usd is None or float(ctx.get("cost_usd", 0.0)) < max_usd

    def under_turns(ctx: Dict[str, Any], e: Any) -> bool:
        return max_turns is None or int(ctx.get("turns", 0)) < max_turns

    return MachineLogic(
        guards={
            "underTokenBudget": under_tokens,
            "underCostBudget": under_cost,
            "underTurnLimit": under_turns,
        }
    )


#: A usage number past this is treated as "budget exhausted" (fail closed).
_EXHAUSTED = 10**15


def _spent(value: Any, integer: bool) -> Any:
    """One provider-reported usage number, sanitised: negative → 0 (a
    hostile provider cannot REFUND budget), NaN / inf / garbage → a
    budget-exhausting amount (fail closed). Never raises."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        v = math.nan
    if not math.isfinite(v) or v > _EXHAUSTED:
        v = float(_EXHAUSTED)
    v = max(v, 0.0)
    return int(v) if integer else v


def _spent_tokens(value: Any) -> int:
    """A provider-reported token count, clamped and sanitised."""
    return int(_spent(value, True))


def _spent_usd(value: Any) -> float:
    """A reported cost: negative → 0, NaN / inf → budget-exhausting."""
    return float(_spent(value, False))
