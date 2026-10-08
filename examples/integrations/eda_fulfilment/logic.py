"""Actions, guards and the default shipping service for both charts.

Pure and deterministic: every function only reads the event and touches
``context`` -- a retried or redelivered event can safely run them again.
"""

from typing import Any, Dict

from xstate_statemachine import MachineLogic

# -------------------------------------------------------------------------
# 🛡️ Guards
# -------------------------------------------------------------------------


def has_total(ctx: Dict[str, Any], e: Any) -> bool:
    """A payment must carry a positive total."""
    total = (e.payload or {}).get("total", 0)
    return isinstance(total, (int, float)) and total > 0


# -------------------------------------------------------------------------
# ⚙️ Actions
# -------------------------------------------------------------------------


def record_payment(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["orderId"] = e.payload.get("orderId")
    ctx["total"] = e.payload["total"]


def record_payment_failure(
    i: Any, ctx: Dict[str, Any], e: Any, a: Any
) -> None:
    """A PAYMENT_FAILED must say why. A payload whose ``reason`` is not a
    string is a *poison* message: the action raises, the chart's
    ``actionErrorPolicy: "fail"`` turns that into an error receipt, the
    dispatcher retries and finally dead-letters it (X0.8)."""
    reason = (e.payload or {}).get("reason")
    if not isinstance(reason, str):
        raise ValueError(f"PAYMENT_FAILED.reason must be a string: {reason!r}")
    ctx["failure"] = reason


def store_tracking(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    data = e.data if isinstance(e.data, dict) else {}
    ctx["trackingId"] = data.get("trackingId")


# -------------------------------------------------------------------------
# 🚚 Services
# -------------------------------------------------------------------------


def tracking_for(order_id: Any) -> str:
    """Deterministic fake carrier: the tracking id derives from the order."""
    return f"TRK-{order_id}"


def ship_order_inline(i: Any, ctx: Dict[str, Any], e: Any) -> Dict[str, Any]:
    """The in-process shipping service (used when Celery is not wired)."""
    return {"trackingId": tracking_for(ctx.get("orderId"))}


#: 📝 #293 battle: `xsm dlq replay --logic logic` (and `xsm simulate`)
#:    bind the chart's names by auto-discovery -- `shipOrder` must exist
#:    at module level as `ship_order`, or the operator's replay dies with
#:    ImplementationMissingError before it can touch the dead letter.
ship_order = ship_order_inline


def order_logic(ship_service: Any = None) -> MachineLogic:
    return MachineLogic(
        actions={
            "recordPayment": record_payment,
            "recordPaymentFailure": record_payment_failure,
            "storeTracking": store_tracking,
        },
        guards={"hasTotal": has_total},
        services={"shipOrder": ship_service or ship_order_inline},
    )
