# examples/recipes/stripe_webhooks/stripe_webhooks.py
# -----------------------------------------------------------------------------
# 💳 Stripe webhooks -> a persisted subscription statechart (#308)
# -----------------------------------------------------------------------------
# 🏛️ Three rules, in order, before the machine sees anything:
#    1. VERIFY: `Stripe-Signature` is HMAC-SHA256 over "<t>.<raw body>" with
#       the endpoint secret. Compare in constant time, and refuse a
#       timestamp outside the tolerance window (a captured request replayed
#       tomorrow is an attack, not a retry).
#    2. MAP: `event.type` -> a machine event. Unknown types are answered 200
#       and ignored -- Stripe retries anything that is not 2xx.
#    3. DEDUPLICATE + PERSIST: `event.id` is the idempotency key
#       (`IdempotencyPlugin`), and `persisted()` loads, sends and saves the
#       subscription under one optimistic version check.
# 💡 Framework-free on purpose: the FastAPI and Flask endpoints are thin
#    wrappers around `handle_webhook`.
# -----------------------------------------------------------------------------
"""Verify, map, deduplicate and persist a Stripe webhook delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine import receipt_to_status
from xstate_statemachine.persistence import IdempotencyPlugin, persisted

HERE = Path(__file__).resolve().parent
#: Stripe's own default tolerance for `construct_event`.
TOLERANCE_S = 300
EVENT_MAP = {
    "invoice.paid": "PAYMENT_SUCCEEDED",
    "invoice.payment_succeeded": "PAYMENT_SUCCEEDED",
    "invoice.payment_failed": "PAYMENT_FAILED",
    "customer.subscription.deleted": "CANCELED",
}


class SignatureError(ValueError):
    """The delivery is not provably from Stripe -- answer 400."""


def sign(body: bytes, secret: str, timestamp: int) -> str:
    """The header Stripe would send (tests and fixtures use this)."""
    mac = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    )
    return f"t={timestamp},v1={mac.hexdigest()}"


def verify_signature(
    body: bytes,
    header: str,
    secret: str,
    *,
    now: Optional[float] = None,
    tolerance_s: int = TOLERANCE_S,
) -> Dict[str, Any]:
    """Return the parsed event, or raise `SignatureError`."""
    parts: Dict[str, list] = {}
    for item in (header or "").split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        ts = int(parts["t"][0])
    except (KeyError, ValueError):
        raise SignatureError("no timestamp in Stripe-Signature") from None
    if abs((time.time() if now is None else now) - ts) > tolerance_s:
        raise SignatureError("timestamp outside the tolerance window")
    expected = sign(body, secret, ts).split("v1=", 1)[1]
    # 🔐 constant time, and ANY of the v1 signatures may match (rotation)
    if not any(hmac.compare_digest(expected, s) for s in parts.get("v1", [])):
        raise SignatureError("signature mismatch")
    return json.loads(body)


def verify_with_sdk(body: bytes, header: str, secret: str) -> Dict:
    """Same contract via the official SDK, when it is installed (soft).
    Uses the wall clock, so tests with recorded timestamps use the stdlib
    `verify_signature` above."""
    try:
        import stripe  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - SDK optional
        return verify_signature(body, header, secret)
    try:
        event = stripe.Webhook.construct_event(body, header, secret)
    except Exception as exc:  # stripe.SignatureVerificationError
        raise SignatureError(type(exc).__name__) from None
    return dict(event.to_dict())


def build_machine() -> Any:
    def record_payment(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["failures"] = 0
        ctx["last_invoice"] = e.payload.get("invoice")

    def record_failure(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["failures"] += 1

    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    logic = MachineLogic(
        actions={
            "recordPayment": record_payment,
            "recordFailure": record_failure,
        }
    )
    return create_machine(config, logic=logic)


def subscription_id(event: Dict[str, Any]) -> str:
    obj = event["data"]["object"]
    return str(obj.get("subscription") or obj["id"])


def handle_webhook(
    body: bytes,
    header: str,
    *,
    secret: str,
    store: Any,
    inbox: Any,
    machine: Any,
    now: Optional[float] = None,
) -> Tuple[int, Dict[str, Any]]:
    """``(http_status, json_body)`` for one delivery. Never raises for a
    bad signature -- that is a 400, not a crash."""
    try:
        event = verify_signature(body, header, secret, now=now)
    except SignatureError as exc:
        return 400, {"error": "invalid_signature", "detail": str(exc)}
    kind = EVENT_MAP.get(event.get("type", ""))
    if kind is None:
        return 200, {"ignored": event.get("type")}
    plugin = IdempotencyPlugin(inbox, principal=lambda e: "stripe")
    key = f"subscription.{subscription_id(event)}"
    obj = event["data"]["object"]
    with persisted(store, key, machine, plugins=[plugin]) as sub:
        receipt = sub.send(
            kind, id=event["id"], invoice=obj.get("id"), wait=True
        )
        value = sub.value
    return receipt_to_status(receipt), {
        "state": value,
        "changed": receipt.changed,
        "duplicate": receipt.duplicate,
    }
