# examples/integrations/fastapi_orders/logic.py
# -----------------------------------------------------------------------------
# 🧠 Actions, guards and services for the order chart
# -----------------------------------------------------------------------------
# 🏛️ Rules every piece of logic here follows (see the guide's "Side
#    effects" section): actions are FAST and IDEMPOTENT -- they only touch
#    `context`; the one slow, failure-prone thing (charging a card) is an
#    `invoke`d service, so a failure is an `onError` transition the chart
#    models, retried by `RetryPolicy`. The service is a plain `def` so both
#    engines can run it: the async `Interpreter` in the web workers and the
#    `SyncInterpreter` the `DueTimerScanner` uses to wake retries.
# -----------------------------------------------------------------------------
"""Order logic: catalogue, fake payment gateway, `RetryPolicy` wiring."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

from xstate_statemachine import MachineLogic
from xstate_statemachine.patterns import CircuitBreaker, RetryPolicy

#: 💡 A tiny fixed catalogue: prices are the server's, never the client's.
CATALOGUE: Dict[str, int] = {"tea": 450, "mug": 1200, "kettle": 3900}
DEFAULT_UNIT_CENTS = 999

#: Card tokens the fake gateway treats specially (demo + tests).
DECLINED_TOKEN = "tok_declined"  # every attempt fails → paymentFailed
FLAKY_TOKEN = "tok_flaky"  # the first attempt fails, the retry succeeds
#: 🔌 #265: the whole GATEWAY is down (not one card). Every charge raises
#:    `GatewayDown` until `GATEWAY.up = True` again -- the outage drill.
OUTAGE_TOKEN = "tok_outage"


class GatewayError(Exception):
    """The fake gateway refused the charge."""


class GatewayDown(GatewayError):
    """The gateway is unreachable (an outage, not a decline)."""


class _Gateway:
    """Process-wide switch for the outage drill (tests flip it)."""

    up: bool = True
    calls: int = 0  # how many times the real gateway was actually hit


GATEWAY = _Gateway()


def retry_policy() -> RetryPolicy:
    """3 attempts, exponential backoff without jitter (reproducible)."""
    base_ms = float(os.environ.get("XSM_ORDERS_RETRY_BASE_MS", "2000"))
    return RetryPolicy(max_attempts=3, base_ms=base_ms, jitter="none")


def _breaker_factory() -> CircuitBreaker:
    # 🏛️ #265: ONE breaker per process in front of the gateway. When the
    #    provider is down, every order's charge fails fast with
    #    `CircuitOpenError` instead of each burning a slow network timeout
    #    -- and the chart's `onError` → `retrying` path still runs, so the
    #    order backs off and (after the cooldown lets a probe through and
    #    the gateway answers) recovers on its own. Thresholds are small so
    #    the drill is readable; tune for your provider's SLA.
    return CircuitBreaker(
        failure_threshold=int(os.environ.get("XSM_ORDERS_CB_THRESHOLD", "3")),
        cooldown_ms=float(os.environ.get("XSM_ORDERS_CB_COOLDOWN_MS", "5000")),
        half_open_max_calls=1,
        name="paymentGateway",
        exceptions=(GatewayDown,),  # a DECLINE is not a provider failure
    )


GATEWAY_BREAKER: CircuitBreaker = _breaker_factory()


def reset_gateway_breaker(clock: Any = None) -> CircuitBreaker:
    """Tests: a fresh breaker (optionally on a `SimulatedClock`)."""
    global GATEWAY_BREAKER
    GATEWAY_BREAKER.close()
    GATEWAY_BREAKER = CircuitBreaker(
        failure_threshold=3,
        cooldown_ms=5000,
        half_open_max_calls=1,
        name="paymentGateway",
        exceptions=(GatewayDown,),
        clock=clock,
    )
    return GATEWAY_BREAKER


# -----------------------------------------------------------------------------
# 🎬 Actions -- fast, context-only, idempotent
# -----------------------------------------------------------------------------
def add_item(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    sku, qty = str(e.payload["sku"]), int(e.payload["qty"])
    unit = CATALOGUE.get(sku, DEFAULT_UNIT_CENTS)
    items = [dict(x) for x in ctx.get("items", [])]
    items.append({"sku": sku, "qty": qty, "unit_cents": unit})
    ctx["items"] = items
    ctx["total_cents"] = sum(x["qty"] * x["unit_cents"] for x in items)


def store_card(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["card_token"] = str(e.payload["card_token"])


def record_charge(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    data = getattr(e, "data", None) or {}
    ctx["charge_id"] = data.get("charge_id")


def record_cancel(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["cancel_reason"] = e.payload.get("reason", "customer request")


# -----------------------------------------------------------------------------
# 🛡️ Guards
# -----------------------------------------------------------------------------
def has_items(ctx: Dict[str, Any], e: Any) -> bool:
    return bool(ctx.get("items"))


# -----------------------------------------------------------------------------
# 💳 Service -- the fake payment gateway
# -----------------------------------------------------------------------------
def charge_card(i: Any, ctx: Dict[str, Any], e: Any) -> Dict[str, Any]:
    """Charge ``ctx["card_token"]``; deterministic by token.

    ``tok_declined`` always raises (→ ``onError`` → retry → after the
    last attempt, ``paymentFailed``). ``tok_flaky`` raises on the first
    attempt only. Anything else succeeds. The charge id is derived from
    the order and the attempt, so a replayed charge is recognisable --
    what a real gateway's idempotency key gives you.
    """
    token = str(ctx.get("card_token") or "")
    attempt = int(ctx.get("attempt", 0))

    def hit_gateway() -> Dict[str, Any]:
        GATEWAY.calls += 1
        if not GATEWAY.up or token == OUTAGE_TOKEN:
            raise GatewayDown("gateway unreachable")
        if token == DECLINED_TOKEN:
            raise GatewayError("card declined")
        if token == FLAKY_TOKEN and attempt == 0:
            raise GatewayError("gateway timeout")
        seed = f"{getattr(i, 'store_key', '')}:{ctx.get('total_cents')}"
        digest = hashlib.sha256(seed.encode()).hexdigest()[:12]
        return {
            "charge_id": f"ch_{digest}",
            "amount_cents": ctx["total_cents"],
        }

    # ⚡ Through the breaker: while it is open the call is refused in
    #    microseconds (`CircuitOpenError` -- the chart's `onError` catches
    #    any exception, so no subclassing is needed), the gateway is never
    #    touched, and the order still takes the retry path. The error
    #    propagates as-is, so a dead letter's chain shows "circuit open"
    #    distinctly from "declined".
    return GATEWAY_BREAKER.call(hit_gateway)


def capture_charge(i: Any, ctx: Dict[str, Any], e: Any) -> Dict[str, Any]:
    """v2 chart only: capture the authorised charge. Deterministic:
    succeeds whenever an authorisation exists."""
    if not ctx.get("charge_id"):
        raise GatewayError("nothing to capture")
    return {"captured": ctx["charge_id"]}


def build_logic() -> MachineLogic:
    own = MachineLogic(
        actions={
            "addItem": add_item,
            "storeCard": store_card,
            "recordCharge": record_charge,
            "recordCancel": record_cancel,
        },
        guards={"hasItems": has_items},
        # 📝 `captureCharge` is only referenced by machine_v2.json; an
        #    unused service is fine, a missing one is a config error.
        services={"chargeCard": charge_card, "captureCharge": capture_charge},
    )
    # 🔁 `retryDelay` / `retryCanRetry` / `retryBump` / `retryReset`.
    return retry_policy().logic().merge(own)
