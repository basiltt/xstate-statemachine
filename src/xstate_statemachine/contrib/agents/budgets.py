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

__all__ = ["Budget", "budget_guards"]


@dataclass(frozen=True)
class Budget:
    """Per-agent limits. ``None`` means "no limit on this axis"."""

    max_tokens: Optional[int] = None
    max_usd: Optional[float] = None
    max_turns: Optional[int] = 10

    @classmethod
    def coerce(
        cls, value: Union["Budget", Mapping[str, Any], None]
    ) -> "Budget":
        if value is None:
            return cls()
        if isinstance(value, Budget):
            return value
        return cls(**dict(value))


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


def _spent_tokens(value: Any) -> int:
    """A provider-reported token count, clamped to ``>= 0``.

    🔐 Usage numbers come from the provider (or a proxy in front of it):
    a negative count would REFUND the budget, so it is spent as zero.
    """
    return max(0, int(value or 0))


def _spent_usd(value: Any) -> float:
    """A reported cost: negative → 0, NaN → +inf (fail closed).

    📝 NaN would otherwise make every later total NaN; ``inf`` makes the
    cost guard refuse the next turn, which is the honest outcome when the
    spend is unknowable.
    """
    cost = float(value or 0.0)
    if math.isnan(cost):
        return math.inf
    return max(0.0, cost)
