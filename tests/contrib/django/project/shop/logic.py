# tests/contrib/django/project/shop/logic.py
"""Logic for ``machines/order.json`` (bound by name via LogicLoader)."""

from typing import Any


def inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["count"] = ctx.get("count", 0) + 1


def record(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["total"] = ctx.get("total", 0) + int(e.payload.get("amount", 0))


def positive_amount(ctx: Any, e: Any) -> bool:
    return int(e.payload.get("amount", 0)) > 0
