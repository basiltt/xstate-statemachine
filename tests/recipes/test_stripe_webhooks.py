# tests/recipes/test_stripe_webhooks.py
"""Stripe recipe: signature verification, mapping, idempotency, both
framework endpoints -- against recorded fixture payloads."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Tuple

import pytest

from .conftest import RECIPES, load_recipe, requires

sw = load_recipe("stripe_webhooks", "stripe_webhooks")
FIXTURES = RECIPES / "stripe_webhooks" / "fixtures"
SECRET = "whsec_test_recipe"
NOW = 1_735_700_000.0  # inside every fixture's window


def fixture(name: str) -> bytes:
    # 📝 Signatures are over EXACT bytes: read binary, never re-serialize.
    return (FIXTURES / f"{name}.json").read_bytes().strip()


def signed(name: str, ts: float = NOW, secret: str = SECRET) -> Tuple:
    body = fixture(name)
    return body, sw.sign(body, secret, int(ts))


@pytest.fixture
def env(tmp_path: Path) -> Any:
    from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

    store = SQLiteStore(tmp_path / "s.db")
    yield {
        "secret": SECRET,
        "store": store,
        "inbox": MemoryInbox(),
        "machine": sw.build_machine(),
        "now": NOW,
    }
    store.close()


def deliver(env: Any, body: bytes, header: str) -> Tuple[int, Any]:
    return sw.handle_webhook(body, header, **env)


class TestSignature:
    def test_valid_signature_parses(self) -> None:
        body, header = signed("invoice_paid")
        event = sw.verify_signature(body, header, SECRET, now=NOW)
        assert event["id"] == "evt_1PaidA"

    def test_forged_signature_is_rejected(self, env: Any) -> None:
        body, _ = signed("invoice_paid")
        forged = sw.sign(body, "whsec_attacker", int(NOW))
        status, out = deliver(env, body, forged)
        assert status == 400 and out["error"] == "invalid_signature"
        assert env["store"].load("subscription.sub_123") is None

    def test_tampered_body_is_rejected(self) -> None:
        body, header = signed("invoice_paid")
        with pytest.raises(sw.SignatureError, match="mismatch"):
            sw.verify_signature(
                body.replace(b"2000", b"1"), header, SECRET, now=NOW
            )

    def test_stale_timestamp_is_rejected(self, env: Any) -> None:
        body, header = signed("invoice_paid", ts=NOW - 301)
        status, out = deliver(env, body, header)
        assert status == 400 and "tolerance" in out["detail"]

    def test_future_timestamp_is_rejected(self) -> None:
        body, header = signed("invoice_paid", ts=NOW + 301)
        with pytest.raises(sw.SignatureError, match="tolerance"):
            sw.verify_signature(body, header, SECRET, now=NOW)

    @pytest.mark.parametrize("header", ["", "v1=abc", "t=x,v1=abc"])
    def test_malformed_header_is_rejected(self, header: str) -> None:
        with pytest.raises(sw.SignatureError):
            sw.verify_signature(b"{}", header, SECRET, now=NOW)

    def test_rotated_secret_second_v1_matches(self) -> None:
        body, header = signed("invoice_paid")
        old = sw.sign(body, "whsec_old", int(NOW)).split(",")[1]
        event = sw.verify_signature(
            body, f"{header.split(',')[0]},{old},{header.split(',')[1]}",
            SECRET, now=NOW,
        )  # fmt: skip
        assert event["type"] == "invoice.paid"

    def test_default_now_is_wall_clock(self) -> None:
        body, header = signed("invoice_paid", ts=time.time())
        assert sw.verify_signature(body, header, SECRET)["id"]

    def test_sdk_path_is_soft(self) -> None:
        body, header = signed("invoice_paid", ts=time.time())
        assert sw.verify_with_sdk(body, header, SECRET)["id"] == "evt_1PaidA"
        with pytest.raises(sw.SignatureError):
            sw.verify_with_sdk(body, header, "whsec_wrong")


class TestLifecycle:
    def test_full_lifecycle_from_recorded_fixtures(self, env: Any) -> None:
        states = []
        for name in (
            "invoice_paid",
            "invoice_payment_failed",
            "subscription_deleted",
        ):
            status, out = deliver(env, *signed(name))
            assert status == 200, out
            states.append(out["state"])
        assert states == ["active", "past_due", "canceled"]
        rec = env["store"].load("subscription.sub_123")
        ctx = json.loads(rec.snapshot)["context"]
        assert ctx["failures"] == 1 and ctx["last_invoice"] == "in_1A"

    def test_unmapped_event_type_is_ignored_with_200(self, env: Any) -> None:
        status, out = deliver(env, *signed("customer_created"))
        assert (status, out) == (200, {"ignored": "customer.created"})

    def test_same_event_id_replays_exactly_once(self, env: Any) -> None:
        deliver(env, *signed("invoice_paid"))
        deliver(env, *signed("invoice_payment_failed"))
        first = env["store"].load("subscription.sub_123")
        # Stripe retries evt_2FailB: same id, fresh signature/timestamp
        status, out = deliver(env, *signed("invoice_payment_failed", NOW + 5))
        assert status == 200 and out["duplicate"] is True
        again = env["store"].load("subscription.sub_123")
        ctx = json.loads(again.snapshot)["context"]
        assert ctx["failures"] == 1  # NOT 2
        assert out["state"] == "past_due"
        assert again.version >= first.version


def _client_pair(kind: str, env: Any) -> Any:
    now = lambda: NOW  # noqa: E731
    kw = {k: env[k] for k in ("secret", "store", "inbox")}
    if kind == "fastapi":
        from fastapi.testclient import TestClient

        app = load_recipe("stripe_webhooks", "app_fastapi")
        return TestClient(app.create_app(now=now, **kw))
    app = load_recipe("stripe_webhooks", "app_flask")
    return app.create_app(now=now, **kw).test_client()


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("fastapi", marks=requires("fastapi", "httpx")),
        pytest.param("flask", marks=requires("flask")),
    ],
)
class TestEndpoints:
    def post(self, client: Any, name: str, header: Any = None) -> Any:
        body, good = signed(name)
        headers = {
            "Stripe-Signature": header or good,
            "Content-Type": "application/json",
        }
        if hasattr(client, "application"):  # flask test client
            r = client.post("/webhooks/stripe", data=body, headers=headers)
            return r.status_code, r.get_json()
        r = client.post("/webhooks/stripe", content=body, headers=headers)
        return r.status_code, r.json()

    def test_happy_path_and_replay(self, kind: str, env: Any) -> None:
        c = _client_pair(kind, env)
        status, body = self.post(c, "invoice_paid")
        assert status == 200 and body["state"] == "active"
        status, body = self.post(c, "invoice_paid")
        assert status == 200 and body["duplicate"] is True

    def test_forged_is_400(self, kind: str, env: Any) -> None:
        c = _client_pair(kind, env)
        status, _ = self.post(c, "invoice_paid", header="t=1735700000,v1=00")
        assert status == 400
