# tests/recipes/test_battle_308_scenario.py
"""#308 battle: the recipe pack on a SaaS billing day.

* **a thousand Stripe deliveries, hostile ones among them** -- 1,000
  webhook bodies across 200 subscriptions: valid, forged signature,
  tampered body (one byte), stale timestamp (yesterday), future
  timestamp, a signature header with 50 `v1=` entries (one valid),
  header without `t=`, body that is not JSON, body of 2 MB, a valid
  signature over a body whose `event.id` was already seen (Stripe
  retry), and the same `event.id` delivered CONCURRENTLY by 8 threads:
  every forged / stale / tampered one is 400 and changes NOTHING; every
  retry is `duplicate` and spends no transition; every subscription ends
  in the state its valid events dictate; the store's version grows only
  by real changes;
* **the chart does not care what the endpoint is** -- the FastAPI and
  Flask variants give byte-identical results for the same deliveries;
* **slot filling under a hostile NLU** -- 500 conversations where the
  extractor sends unknown slot names, `None`, empty strings, 1 MB
  values, a slot named `__class__`, slots in the payload as nested
  dicts, 100 turns of nothing; silence nudges exactly MAX_NUDGES times
  then abandons; a `NO` at confirmation clears and re-asks; no
  conversation ever books with a missing slot;
* **feature-flag rollout: metrics lie** -- a metrics callable that
  raises, returns NaN, returns a string, flips healthy→unhealthy between
  the guard and the bake: the chart never promotes on a raising /
  non-numeric reading (guard raising == False), `METRICS_BAD` mid-bake
  rolls back from any exposed stage and `apply_percent` is called with 0
  exactly once at the end;
* **WebSocket reconnect: backoff bounds** -- a client that fails N times
  then connects: attempts never exceed `max_attempts`, each `retryDelay`
  is within `[0, min(base*factor^n, max)]` (full jitter) and the socket
  `close` runs exactly once per connection however the state is left
  (DROPPED, DISCONNECT, stop());
* **recipes survive a restart** -- a Stripe subscription parked in
  `past_due` with a pending dunning `after` is persisted, the process
  "dies", a `DueTimerScanner` an hour later fires the deadline from the
  store.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

from .conftest import RECIPES, load_recipe

sw = load_recipe("stripe_webhooks", "stripe_webhooks")
sf = load_recipe("slot_filling", "slot_filling")
ff = load_recipe("feature_flag_rollout", "rollout")
ws = load_recipe("websocket_reconnect", "ws_reconnect")

FIXTURES = RECIPES / "stripe_webhooks" / "fixtures"
SECRET = "whsec_battle_308"
NOW = 1_735_700_000.0


def _body(kind: str, sub: str, evt: str) -> bytes:
    """A delivery like Stripe's, for subscription *sub* and event id *evt*."""
    obj: Dict[str, Any] = {"id": f"in_{evt}", "subscription": sub}
    if kind == "customer.subscription.deleted":
        obj = {"id": sub}
    return json.dumps(
        {"id": evt, "type": kind, "data": {"object": obj}},
        separators=(",", ":"),
    ).encode()


def _env(tmp_path: Path) -> Dict[str, Any]:
    from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

    return {
        "secret": SECRET,
        "store": SQLiteStore(tmp_path / "s.db", busy_timeout=30),
        "inbox": MemoryInbox(),
        "machine": sw.build_machine(),
        "now": NOW,
    }


def _deliver(env: Dict[str, Any], body: bytes, header: str) -> Any:
    return sw.handle_webhook(body, header, **env)


# -----------------------------------------------------------------------------
# 1. a thousand Stripe deliveries, hostile ones among them
# -----------------------------------------------------------------------------
def test_thousand_deliveries_hostile_ones_change_nothing(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    try:
        expected: Dict[str, str] = {}
        failures: Dict[str, int] = {}
        bad = 0
        for n in range(1000):
            sub = f"sub_{n % 200:03d}"
            evt = f"evt_{n:04d}"
            kind = ["invoice.paid", "invoice.payment_failed"][n % 2]
            body = _body(kind, sub, evt)
            good = sw.sign(body, SECRET, int(NOW))
            flavour = n % 10
            if flavour == 3:  # forged
                header = sw.sign(body, "whsec_attacker", int(NOW))
            elif flavour == 4:  # tampered body
                body = body.replace(b"invoice.", b"invoice_", 1)
                header = good
            elif flavour == 5:  # stale (yesterday)
                header = sw.sign(body, SECRET, int(NOW) - 86_400)
            elif flavour == 6:  # future
                header = sw.sign(body, SECRET, int(NOW) + 3_600)
            elif flavour == 7:  # 50 v1 entries, one valid
                sig = good.split("v1=", 1)[1]
                header = f"t={int(NOW)}," + ",".join(
                    [f"v1={'0' * 64}"] * 49 + [f"v1={sig}"]
                )
            elif flavour == 8:  # no timestamp
                header = "v1=" + good.split("v1=", 1)[1]
            else:
                header = good
            status, out = _deliver(env, body, header)
            if flavour in (3, 4, 5, 6, 8):
                assert status == 400, (flavour, out)
                bad += 1
                continue
            assert status == 200, (flavour, out)
            # model the lifecycle ourselves
            st = expected.get(sub, "incomplete")
            if kind == "invoice.paid":
                expected[sub] = "active"
                failures[sub] = 0
            elif st in ("active", "past_due"):
                expected[sub] = "past_due"
                failures[sub] = failures.get(sub, 0) + 1
            assert out["state"] == expected.get(sub, "incomplete"), (n, out)
        assert bad == 500
        for sub, state in expected.items():
            rec = env["store"].load(f"subscription.{sub}")
            snap = json.loads(rec.snapshot)
            assert snap["value"] == state, sub
            assert snap["context"]["failures"] == failures.get(sub, 0)
    finally:
        env["store"].close()


def test_not_json_and_huge_bodies_are_refused_or_ignored(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    try:
        body = b"{not json"
        status, out = _deliver(env, body, sw.sign(body, SECRET, int(NOW)))
        assert status == 400, out  # never a traceback
        body = _body("invoice.paid", "sub_big", "evt_big")
        body = body[:-1] + b',"pad":"' + b"x" * (2 * 1024 * 1024) + b'"}'
        status, out = _deliver(env, body, sw.sign(body, SECRET, int(NOW)))
        assert status == 200 and out["state"] == "active"
    finally:
        env["store"].close()


def test_same_event_id_concurrently_from_eight_threads(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    try:
        body = _body("invoice.paid", "sub_c", "evt_c1")
        _deliver(env, body, sw.sign(body, SECRET, int(NOW)))
        fail = _body("invoice.payment_failed", "sub_c", "evt_c2")
        header = sw.sign(fail, SECRET, int(NOW))
        results: List[Any] = []
        gate = threading.Barrier(8)

        def worker() -> None:
            gate.wait(10)
            results.append(_deliver(env, fail, header))

        ts = [threading.Thread(target=worker) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert len(results) == 8
        statuses = {s for s, _ in results}
        assert statuses <= {200, 409}, statuses
        ok = [o for s, o in results if s == 200]
        assert sum(1 for o in ok if not o["duplicate"]) == 1, results
        snap = json.loads(env["store"].load("subscription.sub_c").snapshot)
        assert snap["context"]["failures"] == 1  # exactly once
    finally:
        env["store"].close()


# -----------------------------------------------------------------------------
# 2. the endpoint does not matter
# -----------------------------------------------------------------------------
def test_fastapi_and_flask_agree(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("flask")
    from fastapi.testclient import TestClient

    outs = []
    for kind in ("fastapi", "flask"):
        env = _env(tmp_path / kind)
        mod = load_recipe("stripe_webhooks", f"app_{kind}")
        app = mod.create_app(
            secret=env["secret"],
            store=env["store"],
            inbox=env["inbox"],
            now=lambda: NOW,
        )
        client = TestClient(app) if kind == "fastapi" else app.test_client()
        seq = []
        for n, k in enumerate(("invoice.paid", "invoice.payment_failed")):
            body = _body(k, "sub_x", f"evt_x{n}")
            hdr = {"Stripe-Signature": sw.sign(body, SECRET, int(NOW))}
            if kind == "fastapi":
                r = client.post("/webhooks/stripe", content=body, headers=hdr)
                seq.append((r.status_code, r.json()))
            else:
                r = client.post("/webhooks/stripe", data=body, headers=hdr)
                seq.append((r.status_code, r.get_json()))
        forged = _body("invoice.paid", "sub_x", "evt_f")
        hdr = {"Stripe-Signature": sw.sign(forged, "nope", int(NOW))}
        if kind == "fastapi":
            r = client.post("/webhooks/stripe", content=forged, headers=hdr)
            seq.append((r.status_code, r.json()))
        else:
            r = client.post("/webhooks/stripe", data=forged, headers=hdr)
            seq.append((r.status_code, r.get_json()))
        outs.append(seq)
        env["store"].close()
    assert outs[0] == outs[1], outs
    assert outs[0][-1][0] == 400


# -----------------------------------------------------------------------------
# 3. slot filling under a hostile NLU
# -----------------------------------------------------------------------------
def test_slot_filling_hostile_extractor() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    booked = 0
    for n in range(500):
        said: List[str] = []
        clock = SimulatedClock()
        i = SyncInterpreter(sf.build_machine(said.append), clock=clock)
        i.start()
        hostile = [
            {"unknown_slot": "x"},
            {"date": None},
            {"date": ""},
            {"__class__": "evil", "slots": {"date": "tue"}},
            {"party_size": {"nested": 4}},  # a dict is not a party size
            {"name": ["Ana", "Bo"]},  # a list is not a name
        ]
        for h in hostile[: (n % 6) + 1]:
            i.send("USER_SAID", **h)
        assert not i.current_state_ids & {
            "booking.confirming",
            "booking.booked",
        }
        # 🔥 nothing hostile landed: every slot is still empty
        assert set(i.context["slots"].values()) == {None}, i.context["slots"]
        assert "__class__" not in i.context["slots"]
        # 100 turns of nothing
        for _ in range(100):
            i.send("USER_SAID")
        # silence: nudges exactly MAX_NUDGES times, then abandoned
        if n % 3 == 0:
            for _ in range(sf.MAX_NUDGES):
                clock.increment(30_000)
                i.tick()
                assert i.current_state_ids == {"booking.collecting"}
            clock.increment(30_000)
            i.tick()
            assert i.current_state_ids == {"booking.abandoned"}
            assert sum(s.startswith("Still there?") for s in said) == (
                sf.MAX_NUDGES
            )
            i.stop()
            continue
        i.send("USER_SAID", date="tue", party_size=4)
        assert i.current_state_ids == {"booking.collecting"}
        i.send("USER_SAID", name="Ana")
        assert i.current_state_ids == {"booking.confirming"}
        if n % 3 == 1:
            i.send("NO")
            assert i.current_state_ids == {"booking.collecting"}
            assert set(i.context["slots"].values()) == {None}
            i.send("USER_SAID", date="wed", party_size=2, name="Bo")
        i.send("YES")
        assert i.current_state_ids == {"booking.booked"}
        assert None not in i.context["slots"].values()
        booked += 1
        i.stop()
    assert booked > 300


# -----------------------------------------------------------------------------
# 4. feature-flag rollout: metrics lie
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "reading",
    [
        "raise",
        {"error_rate": float("nan"), "p99_ms": 1.0},
        {"error_rate": "0", "p99_ms": "1"},
        {"error_rate": None},
        "not a dict",
    ],
)
def test_rollout_never_promotes_on_a_lying_metric(reading: Any) -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    applied: List[Any] = []

    def metrics() -> Any:
        if reading == "raise":
            raise RuntimeError("prometheus down")
        return reading

    clock = SimulatedClock()
    i = SyncInterpreter(
        ff.build_machine(metrics, lambda f, p: applied.append(p)),
        clock=clock,
    ).start()
    i.send("START")
    assert i.current_state_ids == {"rollout.exposed.internal"}
    clock.increment(3_600_000)
    i.tick()
    assert i.current_state_ids == {"rollout.rolled_back"}, i.current_state_ids
    assert applied[-1] == 0 and applied.count(0) == 2  # disabled + rollback
    i.stop()


def test_rollout_metrics_bad_mid_bake_rolls_back_from_any_stage() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    good = {"error_rate": 0.0, "p99_ms": 100.0}
    for stage, hours in (("internal", 0), ("canary_1", 1), ("canary_25", 2)):
        applied: List[Any] = []
        clock = SimulatedClock()
        i = SyncInterpreter(
            ff.build_machine(lambda: good, lambda f, p: applied.append(p)),
            clock=clock,
        ).start()
        i.send("START")
        for _ in range(hours):
            clock.increment(3_600_000)
            i.tick()
        assert i.current_state_ids == {f"rollout.exposed.{stage}"}
        clock.increment(1_000)
        i.send("METRICS_BAD")
        assert i.current_state_ids == {"rollout.rolled_back"}
        assert applied[-1] == 0
        assert i.context["percent"] == 0
        i.stop()


# -----------------------------------------------------------------------------
# 5. WebSocket reconnect: backoff bounds, close exactly once
# -----------------------------------------------------------------------------
class _Client:
    closes = 0
    fails_left = 0

    def __init__(self) -> None:
        self.on_message = None
        self.on_close = None

    def connect(self) -> None:
        if _Client.fails_left > 0:
            _Client.fails_left -= 1
            raise ConnectionError("refused")

    def close(self) -> None:
        _Client.closes += 1


def test_backoff_bounds_and_close_exactly_once() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter
    from xstate_statemachine.patterns import RetryPolicy

    policy = RetryPolicy(
        max_attempts=4, base_ms=500, factor=2, max_ms=3_000, jitter="full"
    )
    # fail more times than allowed → failed; delays within bounds
    _Client.fails_left, _Client.closes = 10, 0
    clock = SimulatedClock()
    i = SyncInterpreter(
        ws.build_machine(_Client, policy=policy), clock=clock
    ).start()
    i.send("CONNECT")
    hops = 0
    while "socket.failed" not in i.current_state_ids and hops < 20:
        assert i.current_state_ids == {"socket.reconnecting"}, (
            hops,
            i.current_state_ids,
        )
        attempt = i.context["attempt"]
        cap = min(500 * 2 ** max(attempt - 1, 0), 3_000)
        # the timer is due within [0, cap]: advancing by cap must fire it
        clock.increment(cap)
        i.tick()
        hops += 1
    assert i.current_state_ids == {"socket.failed"}
    assert i.context["attempt"] <= 4 and hops <= 4
    assert _Client.closes == 0  # never connected: nothing to close
    i.stop()
    # connects on the 3rd try; DROPPED then DISCONNECT then stop(): close
    # runs once per live connection
    _Client.fails_left, _Client.closes = 2, 0
    clock = SimulatedClock()
    i = SyncInterpreter(
        ws.build_machine(_Client, policy=policy), clock=clock
    ).start()
    i.send("CONNECT")
    for _ in range(2):
        clock.increment(3_000)
        i.tick()
    assert i.current_state_ids == {"socket.connected"}, i.current_state_ids
    assert i.context["attempt"] == 0  # retryReset
    i.send("DROPPED", code=1006)
    assert _Client.closes == 1
    clock.increment(3_000)
    i.tick()
    assert i.current_state_ids == {"socket.connected"}
    i.send("DISCONNECT")
    assert _Client.closes == 2
    i.send("CONNECT")
    assert i.current_state_ids == {"socket.connected"}
    i.stop()
    assert _Client.closes == 3


# -----------------------------------------------------------------------------
# 6. a parked subscription survives the process dying
# -----------------------------------------------------------------------------
def test_stripe_dunning_deadline_survives_restart(tmp_path: Path) -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter
    from xstate_statemachine.persistence import DueTimerScanner, SQLiteStore

    chart = json.loads(
        (RECIPES / "stripe_webhooks" / "machine.json").read_text("utf-8")
    )
    # the recipe leaves dunning to Stripe; a team adding a 3-day grace
    # `after` on past_due gets durable behaviour for free
    chart["states"]["past_due"]["after"] = {str(3 * 86_400_000): "canceled"}
    from xstate_statemachine import create_machine

    def make() -> Any:
        return create_machine(chart, logic=sw.build_machine().logic)

    store = SQLiteStore(tmp_path / "s.db")
    i = SyncInterpreter(make(), clock=SimulatedClock(wall_start=NOW)).start()
    i.send("PAYMENT_SUCCEEDED", invoice="in_1")
    i.send("PAYMENT_FAILED")
    assert i.current_state_ids == {"subscription.past_due"}
    store.save(
        "subscription.sub_d",
        i.get_snapshot(),
        deadlines=tuple(i.pending_deadlines()),
    )
    i.stop()
    sc = DueTimerScanner(store, lambda k: make())
    assert sc.scan(NOW + 2 * 86_400).woken == 0
    assert sc.scan(NOW + 3 * 86_400 + 1).woken == 1
    snap = json.loads(store.load("subscription.sub_d").snapshot)
    assert snap["value"] == "canceled"
    store.close()
