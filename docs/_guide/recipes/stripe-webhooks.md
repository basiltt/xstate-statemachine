---
title: "Recipe: Stripe webhooks"
permalink: /guide/stripe-webhooks/
description: "A Stripe subscription lifecycle as a persisted statechart. The webhook endpoint (FastAPI or Flask) verifies Stripe-Signature with constant-time HMAC and a timestamp window, maps event.type to machine events, and uses event.id as the idempotency key."
---

# Recipe: Stripe webhooks

Stripe tells you about a subscription through webhooks. They arrive **at least once**, **out of order under retries**, and from **anyone who knows your URL**. So the endpoint has three jobs before the business logic runs: prove the request came from Stripe, drop duplicates, and make sure a late `invoice.payment_failed` cannot resurrect a canceled subscription. The chart handles the last job. The rest of this page covers the other two.

Files: [`examples/recipes/stripe_webhooks/`](https://github.com/basiltt/xstate-statemachine/tree/main/examples/recipes/stripe_webhooks). The chart is `machine.json`, the logic is `stripe_webhooks.py`, and the two endpoints are `app_fastapi.py` and `app_flask.py`. Recorded payloads are in `fixtures/`.

## The chart

```mermaid
stateDiagram-v2
  [*] --> incomplete
  incomplete --> active: PAYMENT_SUCCEEDED
  active --> past_due: PAYMENT_FAILED
  past_due --> active: PAYMENT_SUCCEEDED
  past_due --> past_due: PAYMENT_FAILED
  incomplete --> canceled: CANCELED
  active --> canceled: CANCELED
  past_due --> canceled: CANCELED
```

`canceled` handles no events. A late `invoice.paid` for a canceled subscription is answered `200` and changes nothing. Stripe stops retrying, and nothing is double-billed. `machine.json` is plain XState JSON, so it imports into the Stately editor unchanged.

Reproduce the lifecycle without Stripe:

```bash
xsm simulate examples/recipes/stripe_webhooks/machine.json --events PAYMENT_SUCCEEDED,PAYMENT_FAILED,PAYMENT_SUCCEEDED,CANCELED
# -> subscription.canceled
```

## Verify, map, deduplicate, persist

Stripe signs `"<timestamp>.<raw body>"` with HMAC-SHA256 under your endpoint secret, and sends `Stripe-Signature: t=<ts>,v1=<hex>`. Checking it takes about fifteen lines of stdlib code. Compare in **constant time** (`hmac.compare_digest`), and **reject a timestamp outside a tolerance window**. Stripe's own default window is 300 s. Without the window, a request captured once can be replayed forever.

This is the whole flow in miniature, runnable as-is:

```python
import hashlib, hmac, json, time
from xstate_statemachine import MachineLogic, create_machine, receipt_to_status
from xstate_statemachine.persistence import IdempotencyPlugin, MemoryInbox, MemoryStore, persisted

SECRET, TOLERANCE_S = "whsec_demo", 300
EVENT_MAP = {"invoice.paid": "PAYMENT_SUCCEEDED", "invoice.payment_failed": "PAYMENT_FAILED",
             "customer.subscription.deleted": "CANCELED"}

def sign(body: bytes, ts: int) -> str:
    return f"t={ts},v1=" + hmac.new(SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()

def verify(body: bytes, header: str, now: float) -> dict:
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    ts = int(parts.get("t", "0"))
    if abs(now - ts) > TOLERANCE_S:
        raise ValueError("stale")
    if not hmac.compare_digest(sign(body, ts).split("v1=")[1], parts.get("v1", "")):
        raise ValueError("forged")
    return json.loads(body)

chart = {"id": "subscription", "initial": "incomplete", "context": {"failures": 0}, "states": {
    "incomplete": {"on": {"PAYMENT_SUCCEEDED": "active"}},
    "active": {"on": {"PAYMENT_FAILED": {"target": "past_due", "actions": "fail"}, "CANCELED": "canceled"}},
    "past_due": {"on": {"PAYMENT_SUCCEEDED": "active", "CANCELED": "canceled"}},
    "canceled": {}}}
def fail(i, ctx, e, a): ctx["failures"] += 1
machine = create_machine(chart, logic=MachineLogic(actions={"fail": fail}))
store, inbox = MemoryStore(), MemoryInbox()

def webhook(body: bytes, header: str) -> int:
    try:
        event = verify(body, header, now=time.time())
    except ValueError:
        return 400
    kind = EVENT_MAP.get(event["type"])
    if kind is None:
        return 200                                   # unknown type: ack, ignore
    dedupe = IdempotencyPlugin(inbox, principal=lambda e: "stripe")
    sub_id = event["data"]["object"]["subscription"]
    with persisted(store, f"subscription.{sub_id}", machine, plugins=[dedupe]) as sub:
        return receipt_to_status(sub.send(kind, id=event["id"], wait=True))

paid = json.dumps({"id": "evt_1", "type": "invoice.paid", "data": {"object": {"subscription": "sub_1"}}}).encode()
failed = json.dumps({"id": "evt_2", "type": "invoice.payment_failed", "data": {"object": {"subscription": "sub_1"}}}).encode()
now = int(time.time())
assert webhook(paid, sign(paid, now)) == 200
assert webhook(failed, sign(failed, now)) == 200
assert webhook(failed, sign(failed, now + 1)) == 200          # Stripe retry: answered from the inbox
assert webhook(paid, sign(paid, now - 600)) == 400            # stale timestamp
assert webhook(paid, "t=%d,v1=%s" % (now, "0" * 64)) == 400   # forged
rec = store.load("subscription.sub_1")
assert json.loads(rec.snapshot)["context"]["failures"] == 1   # the retry did NOT count twice
```

The example module splits this into `verify_signature()`, which also accepts several `v1=` entries during secret rotation, and `handle_webhook()`, which returns `(status, json)` and never raises on bad input. The endpoints stay three lines long. If the official SDK is installed, `verify_with_sdk()` calls `stripe.Webhook.construct_event` instead. That import is soft: the recipe itself needs nothing beyond this library.

## The endpoint: FastAPI and Flask

Both endpoints read the **raw body**. The signature covers the exact bytes, so a JSON model must never parse and re-serialize the body first.

<!-- doc-fragment -->
```python
# app_fastapi.py
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    status, payload = handle_webhook(
        await request.body(), request.headers.get("stripe-signature", ""),
        secret=secret, store=store, inbox=inbox, machine=machine)
    return JSONResponse(payload, status_code=status)

# app_flask.py
@app.post("/webhooks/stripe")
def stripe_webhook():
    status, payload = handle_webhook(
        request.get_data(), request.headers.get("Stripe-Signature", ""),
        secret=secret, store=store, inbox=inbox, machine=machine)
    return jsonify(payload), status
```

(Excerpt; the full files are in the example folder.) Use a `SQLiteInbox(store)` sharing the `SQLiteStore` in production. The inbox mark then commits in the same transaction as the snapshot.

## Guarantees

> **What this does:** a delivery whose signature does not verify under your secret, or whose timestamp is more than 300 s from now (in either direction), is answered `400` and never reaches the store. The comparison is constant-time (`hmac.compare_digest`). A correctly signed body that is not a JSON object, or has no `data.object.id`, is also a `400`, never a `500` that Stripe would retry forever. A redelivered `event.id` is answered from the inbox with the **original** receipt (`duplicate=True`), and the machine does not see it again (**X0.2**, idempotency: the inbox scope is `principal / machine / subscription`). Each delivery is **load → send → save** under an optimistic version check (`persisted()`), so concurrent deliveries for one subscription produce one winner; a loser is answered `409 {"error": "conflict", "detail": "retry the delivery"}` and the update is never lost. Error bodies carry a fixed code, not the exception text (**X0.7**, web hardening).
>
> **One Stripe account per inbox.** The idempotency principal is the constant `"stripe"`, so `event.id` is unique only within one account's event stream; two accounts (or a live and a test secret) sharing one inbox should scope the principal (e.g. `principal=lambda e: f"stripe:{hashlib.sha256(secret.encode()).hexdigest()[:8]}"`). Only a leaked secret could make this matter within one account.
>
> **What this does not do:** Stripe does not guarantee ordering. A `PAYMENT_SUCCEEDED` that overtakes its `PAYMENT_FAILED` is applied in arrival order, and the chart decides what each event means in each state. If you need strict ordering, compare `event.created` in a guard. Nothing retries a `ConflictError` *inside* the request: `handle_webhook` answers `409` and **Stripe** redelivers it later (it retries every non-2xx answer). The example's `MemoryInbox` forgets on restart; use `SQLiteInbox(store)` in production. Side effects in *actions* (emails) are not covered by the inbox. Put them in an outbox or a service.
>
> See [Guarantees](../guarantees/) and [Security](../security/).

<!-- test: tests/recipes/test_stripe_webhooks.py::test_forged_signature_is_rejected -->
<!-- test: tests/recipes/test_stripe_webhooks.py::test_stale_timestamp_is_rejected -->
<!-- test: tests/recipes/test_stripe_webhooks.py::test_future_timestamp_is_rejected -->
<!-- test: tests/recipes/test_battle_308_scenario.py::test_not_json_and_huge_bodies_are_refused_or_ignored -->
<!-- test: tests/recipes/test_stripe_webhooks.py::test_same_event_id_replays_exactly_once -->
<!-- test: tests/recipes/test_battle_308_scenario.py::test_same_event_id_concurrently_from_eight_threads -->
<!-- test: tests/recipes/test_battle_308_b.py::test_stripe_conflict_is_409_with_a_fixed_body -->
<!-- test: tests/recipes/test_battle_308_b.py::test_stripe_error_bodies_never_echo_input -->

## Troubleshooting

| You see | Why | Fix |
|:--|:--|:--|
| `400 {"error": "invalid_signature", "detail": "signature mismatch"}` | Wrong secret (each endpoint in the Dashboard has its own `whsec_…`), or a framework parsed and re-serialized the body before you read it. | Use the endpoint's secret; read the **raw** bytes (`await request.body()`, `request.get_data()`). |
| `400 … "detail": "timestamp outside the tolerance window"` | The server clock is off by more than 300 s, or a captured request is being replayed. | Run NTP. Do not widen `TOLERANCE_S` to make it go away. |
| `400 … "detail": "no timestamp in Stripe-Signature"` | The header is missing or mangled (a proxy dropped it, or you test with `curl` without signing). | Sign test bodies with `sign()` from the example. |
| `400 … "detail": "body is not JSON"` / `"body is not a JSON object"` / `400 {"error": "invalid_event", "detail": "bad event id"}` / `"event has no data.object.id"` / `"data.object.subscription is not an id"` | The body was signed, but it is not a Stripe event (`bad event id`: over 255 chars or not printable ASCII -- the inbox key; `subscription` must be an id string or an expanded object with an `id`). | Nothing to retry: Stripe never sends these. |
| `409 {"error": "conflict", "detail": "retry the delivery"}` | Two deliveries for one subscription raced; the other one saved first. | Expected under load. Stripe redelivers, and the redelivery applies cleanly. |
| `KeyError: 'STRIPE_WEBHOOK_SECRET'` at start-up | `create_app()` reads the secret from the environment and fails loudly when it is unset. | `export STRIPE_WEBHOOK_SECRET=whsec_…` (from `stripe listen` locally). |

## Test it

`tests/recipes/test_stripe_webhooks.py` replays the recorded fixtures through both endpoints. It checks that a **forged signature**, a **tampered body** and a **stale or future timestamp** are rejected, and that the same `event.id` is applied **exactly once**.

Related: [Idempotency](../persistence/#idempotency-the-inbox), [FastAPI](../integration-fastapi/), [Flask](../integration-flask/), [all recipes](../recipes/).
