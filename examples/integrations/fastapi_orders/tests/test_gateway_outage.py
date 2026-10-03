# examples/integrations/fastapi_orders/tests/test_gateway_outage.py
"""#265 battle scenario: the payment provider goes down for ten minutes.

Black Friday, 14:00. The card gateway starts timing out on every call.
Without a breaker, each of the thousand orders that try to pay burns a
full network timeout, the worker pool fills with hung charges, and the
retry loops hammer a provider that is already on fire (the thundering
herd the RetryPolicy's jitter exists to prevent -- but jitter does not
help when EVERY call is doomed). With the breaker:

* after `failure_threshold` consecutive gateway failures the circuit
  OPENS: every further charge fails in microseconds with
  `CircuitOpenError`, the gateway is not touched, and each order still
  takes its chart's `onError` → `retrying` path and backs off;
* orders that exhaust their retries while the outage lasts land in
  `paymentFailed` -- tagged `dead-letter` -- and the `DeadLetterPlugin`
  writes a record whose error chain names the outage (`GatewayDown` /
  `CircuitOpenError`), with the card token REDACTED, into the same
  SQLite file the snapshots live in, so `xsm dlq list` is the triage view;
* after the cooldown the breaker admits exactly ONE probe; if the
  provider is still down the probe fails and the circuit re-opens (no
  herd); when the provider is back the probe succeeds, the circuit
  closes, and the scheduler's next tick drains the retrying orders;
* a dead-lettered order is recovered by `PAY` with the customer's card
  again (the chart's own path) -- the dead letter is then resolved.

Offline: the gateway is `logic.GATEWAY` (a switch), time is a
`SimulatedClock` shared by the breaker and injected into the scanner.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from typing import Any, Dict, List

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
import logic  # noqa: E402
from xstate_statemachine import SimulatedClock  # noqa: E402
from xstate_statemachine.patterns import CircuitOpenError  # noqa: E402
from xstate_statemachine.persistence import (
    SQLiteInbox,
    SQLiteStore,
)  # noqa: E402

ANN = {"x-customer": "ann"}
N = 60  # orders paying during the outage (1 000 in the story)
T0 = 1_700_000_000.0  # the simulated wall clock: 14:00


def post(client: Any, order: str, event: str, body: Any = None) -> Any:
    return client.post(
        f"/orders/{order}/events/{event}", json=body, headers=ANN
    )


def state(client: Any, order: str) -> Any:
    return client.get(f"/orders/{order}", headers=ANN).json()["state"]


@pytest.fixture(autouse=True)
def _quiet_expected_service_errors() -> Any:
    """Every refused charge is logged at ERROR by the engine (correct in
    production: a failed service IS an error). Here they are the point of
    the test and hundreds of them drown a failure; keep the library's
    logger at CRITICAL for this module."""
    lg = logging.getLogger("xstate_statemachine")
    before = lg.level
    lg.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        lg.setLevel(before)


@pytest.fixture
def world(tmp_path: Any, monkeypatch: Any) -> Dict[str, Any]:
    monkeypatch.setenv("XSM_ORDERS_RETRY_BASE_MS", "1000")  # 1 s, 2 s backoff
    clock = SimulatedClock(wall_start=T0)
    breaker = logic.reset_gateway_breaker(clock=clock)
    logic.GATEWAY.up = True
    logic.GATEWAY.calls = 0
    db = str(tmp_path / "orders.db")
    store = SQLiteStore(db)
    reg = orders.build_registry(store, SQLiteInbox(store), clock=clock)
    app = orders.create_app(reg, email=lambda *a: None, debug=False)
    scanner = orders.build_scanner(reg, now=clock.wall_now)
    yield {
        "db": db,
        "store": store,
        "reg": reg,
        "app": app,
        "clock": clock,
        "breaker": breaker,
        "scanner": scanner,
        "dlq": reg.dead_letters,
    }
    logic.GATEWAY.up = True
    breaker.close()


def _drain(
    scanner: Any, clock: Any, *, step_ms: int = 1500, max_steps: int = 12
) -> List[Any]:
    """Advance the simulated clock in steps, scanning each time, until a
    scan finds nothing due. Bounded; returns the ScanResults."""
    out: List[Any] = []
    for _ in range(max_steps):
        clock.increment(step_ms)
        r = scanner.scan(clock.wall_now())
        out.append(r)
        assert r.errors == [], r.errors
    return out


def _checkout_all(c: Any, n: int) -> List[str]:
    ids = [f"o{i:04d}" for i in range(n)]
    for o in ids:
        post(c, o, "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, o, "CHECKOUT")
    return ids


def test_outage_opens_the_breaker_and_spares_the_gateway(
    world: Dict[str, Any],
) -> None:
    c_app, clock, breaker, scanner, store = (
        world[k] for k in ("app", "clock", "breaker", "scanner", "store")
    )
    with TestClient(c_app) as c:
        ids = _checkout_all(c, N)
        logic.GATEWAY.up = False  # 💥 14:00: the provider goes dark
        # every order tries to pay -- the breaker opens after 3 failures
        for o in ids:
            r = post(c, o, "PAY", {"card_token": "tok_ok"})
            assert r.status_code == 200 and r.json()["state"] == "retrying", (
                o,
                r.text,
            )
        assert breaker.state == "open"
        # 🛡️ the gateway was hit exactly `failure_threshold` times, not N
        assert logic.GATEWAY.calls == 3
        assert breaker.opened_count == 1
        # the orders that were refused by the breaker still backed off: the
        # error that reached the chart was CircuitOpenError, not a timeout
        assert all(state(c, o) == "retrying" for o in ids[:5])

        # ⏰ backoffs mature (1 s, then 2 s), the scheduler wakes them: the
        #    circuit is open for its 5 s cooldown, so every retry across
        #    all N orders is refused in microseconds -- the gateway sees NO
        #    further call -- and each refusal still costs attempt += 1.
        #    After 3 attempts every order's retry loop gives up.
        _drain(scanner, clock, max_steps=8)  # 12 s of simulated time
        assert logic.GATEWAY.calls == 3, "the open circuit let a call out"
        outcomes = [state(c, o) for o in ids]
        assert set(outcomes) == {"paymentFailed"}, set(outcomes)
        # 📝 With all traffic exhausted before the cooldown ended, no probe
        #    was ever requested: the breaker is half-open, waiting for the
        #    next caller (probing is driven by demand, not by a timer). The
        #    probe / re-open / recover path is the next test.
        assert breaker.state == "half_open" and breaker.opened_count == 1


def test_dead_letters_name_the_outage_and_redact_the_card(
    world: Dict[str, Any],
) -> None:
    c_app, clock, breaker, scanner, dlq, db = (
        world[k] for k in ("app", "clock", "breaker", "scanner", "dlq", "db")
    )
    with TestClient(c_app) as c:
        ids = _checkout_all(c, 5)
        logic.GATEWAY.up = False
        for o in ids:
            post(c, o, "PAY", {"card_token": "tok_secret_4242"})
        _drain(scanner, clock, max_steps=8)
        assert all(state(c, o) == "paymentFailed" for o in ids)
    records = dlq.list()
    assert {r.machine_id for r in records} >= {
        f"order.{o}" for o in ids
    } or len(records) == 5
    rec = next(r for r in records if r.attempts == 3)
    # 💀 the chain explains the outage: the first failures hit the gateway
    #    (GatewayDown), the later ones were refused by the breaker
    kinds = [e["type"] for e in rec.errors]
    assert "GatewayDown" in kinds or "CircuitOpenError" in kinds, kinds
    assert all(e["source"] == "service" for e in rec.errors)
    assert rec.state_id == "order.paymentFailed"
    # 🔐 X0.1: the card token is in the snapshot's context -- redacted
    blob = json.dumps(rec.to_dict())
    assert "tok_secret_4242" not in blob
    assert rec.snapshot["context"]["card_token"] != "tok_secret_4242"
    # 🧰 the operator's view is the CLI on the same database
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "dlq",
            "--dlq",
            "sqlite:///" + db.replace("\\", "/"),
            "list",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    listed = json.loads(out.stdout)
    rows = (
        listed
        if isinstance(listed, list)
        else listed.get("records", listed.get("dead_letters", []))
    )
    assert len(rows) >= 5
    assert "tok_secret_4242" not in out.stdout


def test_half_open_admits_one_probe_then_recovers(
    world: Dict[str, Any],
) -> None:
    c_app, clock, breaker, scanner = (
        world[k] for k in ("app", "clock", "breaker", "scanner")
    )
    with TestClient(c_app) as c:
        ids = _checkout_all(c, 20)
        logic.GATEWAY.up = False
        for o in ids:
            post(c, o, "PAY", {"card_token": "tok_ok"})
        assert breaker.state == "open" and logic.GATEWAY.calls == 3

        # ⏳ cooldown elapses while the provider is STILL down: exactly one
        #    probe hits the gateway, fails, and the circuit re-opens.
        clock.increment(5001)
        assert breaker.state == "half_open"
        before = logic.GATEWAY.calls
        r = scanner.scan(clock.wall_now())  # wakes every matured retry
        assert r.errors == []
        assert logic.GATEWAY.calls == before + 1, "more than one probe"
        assert breaker.state == "open" and breaker.opened_count == 2

        # ✅ the provider comes back; next cooldown, the probe succeeds and
        #    the circuit closes; the scheduler drains the rest normally.
        logic.GATEWAY.up = True
        clock.increment(5001)
        assert breaker.state == "half_open"
        scanner.scan(clock.wall_now())
        assert breaker.state == "closed"
        for _ in range(4):
            clock.increment(2500)
            scanner.scan(clock.wall_now())
        outcomes = {state(c, o) for o in ids}
        assert outcomes <= {"paid", "paymentFailed"}, outcomes
        assert "paid" in outcomes


def test_failed_order_recovers_by_paying_again(world: Dict[str, Any]) -> None:
    c_app, clock, scanner, dlq = (
        world[k] for k in ("app", "clock", "scanner", "dlq")
    )
    with TestClient(c_app) as c:
        (o,) = _checkout_all(c, 1)
        logic.GATEWAY.up = False
        post(c, o, "PAY", {"card_token": "tok_ok"})
        _drain(scanner, clock, max_steps=8)
        assert state(c, o) == "paymentFailed"
        assert len(dlq.list()) == 1
        logic.GATEWAY.up = True
        logic.reset_gateway_breaker(clock=clock)
        # the chart's own recovery: the customer pays again
        r = post(c, o, "PAY", {"card_token": "tok_ok"})
        assert r.json()["state"] == "paid"
        assert r.json()["context"]["attempt"] == 0  # retryReset


def test_breaker_fails_fast_without_hanging_the_worker_pool(
    world: Dict[str, Any],
) -> None:
    """The point of the breaker under load: 32 threads hit a dark gateway;
    only `failure_threshold` calls reach it, the rest are refused in
    microseconds, none hang."""
    breaker = world["breaker"]
    logic.GATEWAY.up = False
    logic.GATEWAY.calls = 0
    results: List[str] = []
    lk = threading.Lock()
    gate = threading.Barrier(32)

    def worker() -> None:
        gate.wait(10)
        try:
            # `charge_card` goes through `logic.GATEWAY_BREAKER` itself
            logic.charge_card(
                None, {"card_token": "tok_ok", "total_cents": 1}, None
            )
        except CircuitOpenError:
            kind = "open"
        except logic.GatewayDown:
            kind = "down"
        else:
            kind = "ok"
        with lk:
            results.append(kind)

    ts = [threading.Thread(target=worker) for _ in range(32)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    assert all(not t.is_alive() for t in ts)
    assert results.count("ok") == 0
    assert 3 <= logic.GATEWAY.calls <= 32  # racers before the trip
    assert results.count("open") >= 32 - logic.GATEWAY.calls - 1
    assert breaker.state == "open"
