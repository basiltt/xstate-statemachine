# examples/recipes/stripe_webhooks/app_flask.py
"""The Stripe webhook endpoint, Flask flavour.

Run: ``STRIPE_WEBHOOK_SECRET=whsec_... flask --app app_flask run``.
``request.get_data()`` is the raw body the signature covers.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from flask import Flask, jsonify, request

from stripe_webhooks import build_machine, handle_webhook
from xstate_statemachine.persistence import MemoryInbox, SQLiteStore


def create_app(
    *,
    secret: Optional[str] = None,
    store: Any = None,
    inbox: Any = None,
    now: Any = None,
) -> Flask:
    secret = secret or os.environ["STRIPE_WEBHOOK_SECRET"]
    store = store or SQLiteStore(os.environ.get("XSM_DB", "stripe.db"))
    inbox = inbox or MemoryInbox()
    machine = build_machine()
    app = Flask(__name__)

    @app.post("/webhooks/stripe")
    def stripe_webhook() -> Any:
        status, payload = handle_webhook(
            request.get_data(),
            request.headers.get("Stripe-Signature", ""),
            secret=secret,
            store=store,
            inbox=inbox,
            machine=machine,
            now=now() if now else None,
        )
        return jsonify(payload), status

    return app
