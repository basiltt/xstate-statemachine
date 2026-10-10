# tests/recipes/test_battle_308_review.py
"""#308 independent review -- regressions.

* **R1** a delivery answered 409 (a REAL store conflict between load and
  save) leaves no idempotency mark: Stripe's redelivery is a first
  delivery, not a swallowed `duplicate`;
* **R2** line / paragraph separators (U+2028 / U+2029) are refused as
  slot values like other prompt-breaking characters;
* **R4** an expanded `subscription` object WITHOUT an id (or an empty
  string) is a 400, never a silent per-invoice record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from .conftest import load_recipe

sw = load_recipe("stripe_webhooks", "stripe_webhooks")
sf = load_recipe("slot_filling", "slot_filling")
SECRET = "whsec_review_308"
NOW = 1_735_700_000.0


def _body(kind: str, obj: Any, evt: str) -> bytes:
    return json.dumps(
        {"id": evt, "type": kind, "data": {"object": obj}},
        separators=(",", ":"),
    ).encode()


def _env(tmp_path: Path) -> Any:
    from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

    return {
        "secret": SECRET,
        "store": SQLiteStore(tmp_path / "s.db"),
        "inbox": MemoryInbox(),
        "machine": sw.build_machine(),
        "now": NOW,
    }


def test_r1_real_conflict_is_409_and_leaves_no_mark(tmp_path: Path) -> None:
    env = _env(tmp_path)
    store = env["store"]
    try:
        paid = _body(
            "invoice.paid", {"id": "in_1", "subscription": "sub_r"}, "evt_r1"
        )
        assert (
            sw.handle_webhook(paid, sw.sign(paid, SECRET, int(NOW)), **env)[0]
            == 200
        )
        fail = _body(
            "invoice.payment_failed",
            {"id": "in_2", "subscription": "sub_r"},
            "evt_r2",
        )
        header = sw.sign(fail, SECRET, int(NOW))
        # a concurrent writer bumps the record between our load and save
        real_load = store.load

        def racing_load(key: str) -> Any:
            rec = real_load(key)
            store.save(key, rec.snapshot, expected_version=rec.version)
            return rec

        store.load = racing_load  # type: ignore[method-assign]
        status, out = sw.handle_webhook(fail, header, **env)
        store.load = real_load  # type: ignore[method-assign]
        assert (status, out["error"]) == (409, "conflict"), (status, out)
        snap = json.loads(store.load("subscription.sub_r").snapshot)
        assert snap["value"] == "active"  # nothing applied
        # 🔥 the redelivery is a FIRST delivery, not a duplicate
        status, out = sw.handle_webhook(fail, header, **env)
        assert status == 200 and out["duplicate"] is False, out
        assert out["state"] == "past_due"
    finally:
        store.close()


@pytest.mark.parametrize("ch", ["\u2028", "\u2029", "\n", "\u202e", "\u200b"])
def test_r2_line_separators_are_refused(ch: str) -> None:
    assert not sf.valid_slot_value(f"Bob{ch}Confirm? yes")


@pytest.mark.parametrize("name", ["José", "張偉", "שרה", "Zoë O'Neil"])
def test_r2_real_names_are_accepted(name: str) -> None:
    assert sf.valid_slot_value(name)


@pytest.mark.parametrize(
    "sub", [{"object": "subscription"}, {"id": ""}, {"id": None}, ""]
)
def test_r4_expanded_subscription_without_id_is_400(
    tmp_path: Path, sub: Any
) -> None:
    env = _env(tmp_path)
    try:
        body = _body(
            "invoice.paid", {"id": "in_9", "subscription": sub}, "evt_r9"
        )
        status, out = sw.handle_webhook(
            body, sw.sign(body, SECRET, int(NOW)), **env
        )
        assert status == 400 and out["error"] == "invalid_event", out
        assert env["store"].load("subscription.in_9") is None
    finally:
        env["store"].close()
