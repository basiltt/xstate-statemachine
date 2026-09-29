# examples/recipes/stripe_webhooks/app_fastapi.py
"""The Stripe webhook endpoint, FastAPI flavour.

Run: ``STRIPE_WEBHOOK_SECRET=whsec_... uvicorn app_fastapi:app``.
The handler reads the RAW body -- the signature is over the exact bytes,
so never let a JSON model parse it first.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from stripe_webhooks import build_machine, handle_webhook
from xstate_statemachine.persistence import MemoryInbox, SQLiteStore


def create_app(
    *,
    secret: Optional[str] = None,
    store: Any = None,
    inbox: Any = None,
    now: Any = None,
) -> FastAPI:
    secret = secret or os.environ["STRIPE_WEBHOOK_SECRET"]
    store = store or SQLiteStore(os.environ.get("XSM_DB", "stripe.db"))
    inbox = inbox or MemoryInbox()
    machine = build_machine()
    app = FastAPI()

    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request) -> JSONResponse:
        body = await request.body()
        status, payload = handle_webhook(
            body,
            request.headers.get("stripe-signature", ""),
            secret=secret,
            store=store,
            inbox=inbox,
            machine=machine,
            now=now() if now else None,
        )
        return JSONResponse(payload, status_code=status)

    return app
