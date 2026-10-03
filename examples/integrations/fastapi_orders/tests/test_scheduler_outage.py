# examples/integrations/fastapi_orders/tests/test_scheduler_outage.py
"""#264 battle scenario: the scheduler process is down for three hours.

A production team recognises this one. Two thousand orders check out
over an afternoon; each arms a 15-minute payment timeout, and a few
hundred pay with a flaky card and arm a retry backoff. The ONE scheduler
process (`python app.py --role scheduler`) dies at 14:00 and nobody
notices until 17:00. When it comes back it must:

* fire every matured deadline **exactly once**, in deadline order, even
  though thousands are overdue and `limit=` batches the work over several
  ticks (earliest first -- a 3-hour-late timeout before a 1-minute-late
  one);
* report how late it was (`ScanResult.max_lag_s` is the alert);
* leave orders whose deadline has NOT matured alone (a 17:10 timeout is
  not a 17:00 timeout);
* stay correct when, in the panic, an operator starts a SECOND scheduler
  against the same store (the lock makes "exactly one" an operational
  recommendation, not a correctness requirement);
* and after a crash *between* firing and saving, re-fire -- at least
  once -- without a torn record.

Everything runs offline: the gateway is faked (`logic.py`), time is
injected into the scanner (`now=`), and the web tier is `TestClient`.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
from xstate_statemachine import PluginBase  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
)

ANN = {"x-customer": "ann"}
FIFTEEN_MIN = 900.0
THREE_HOURS = 3 * 3600.0
N_ORDERS = 400  # 📝 2 000 in the story; 400 keeps the suite under a minute
N_FLAKY = 40


class Fires(PluginBase):
    """Count timer-driven transitions per key, thread-safely."""

    def __init__(self) -> None:
        self.by_key: Dict[str, int] = {}
        self.events: List[str] = []
        self._lock = threading.Lock()

    def on_transition(
        self, interp: Any, from_states: Any, to_states: Any, transition: Any
    ) -> None:
        ev = str(getattr(transition, "event", "") or "")
        if not ev.startswith("after."):
            return
        with self._lock:
            self.by_key[interp.store_key] = (
                self.by_key.get(interp.store_key, 0) + 1
            )
            self.events.append(f"{interp.store_key}:{ev}")


def post(client: Any, order: str, event: str, body: Any = None) -> Any:
    return client.post(
        f"/orders/{order}/events/{event}", json=body, headers=ANN
    )


def state(client: Any, order: str) -> Any:
    return client.get(f"/orders/{order}", headers=ANN).json()["state"]


@pytest.fixture
def afternoon(tmp_path: Any) -> Dict[str, Any]:
    """400 orders checked out between 14:00 and 16:59 (one every ~27 s),
    40 of them paid with a flaky card (a retry backoff armed). The
    scheduler is down the whole time: no scan runs."""
    db = str(tmp_path / "orders.db")
    store = SQLiteStore(db)
    reg = orders.build_registry(store, SQLiteInbox(store))
    app = orders.create_app(reg, email=lambda *a: None, debug=False)
    t_down = time.time()  # 14:00
    with TestClient(app) as c:
        for i in range(N_ORDERS):
            o = f"o{i:04d}"
            post(c, o, "ADD_ITEM", {"sku": "tea", "qty": 1})
            post(c, o, "CHECKOUT")
            if i < N_FLAKY:
                assert (
                    post(c, o, "PAY", {"card_token": "tok_flaky"}).json()[
                        "state"
                    ]
                    == "retrying"
                )
    # 📝 Re-anchor every deadline to a staggered checkout time so the
    #    backlog has a real ORDER to it: order i checked out at
    #    14:00 + i * 27 s. (The requests above all ran "now"; the store
    #    is rewritten the way the afternoon would have left it.)
    import sqlite3

    con = sqlite3.connect(db)
    for i in range(N_ORDERS):
        key = f"order.o{i:04d}"
        shift = i * 27.0
        con.execute(
            "UPDATE deadlines SET due_at_wall = due_at_wall + ? WHERE key = ?",
            (shift, key),
        )
    con.commit()
    con.close()
    return {"db": db, "store": store, "reg": reg, "app": app, "t_down": t_down}


def test_scheduler_back_after_three_hours_drains_in_deadline_order(
    afternoon: Dict[str, Any],
) -> None:
    store, reg, app, t0 = (
        afternoon[k] for k in ("store", "reg", "app", "t_down")
    )
    fires = Fires()
    # 📝 `limit=100` with 400 keys: several ticks. Pre-#264-battle the
    #    limit capped the keys SCANNED (always the same first 100 by key
    #    order), so after one tick the other 300 matured timers never
    #    fired at all. The limit must cap the keys WOKEN per tick,
    #    earliest deadline first.
    scanner = orders.build_scanner(
        reg, plugins=[*reg.plugins, fires], limit=100
    )
    now = t0 + THREE_HOURS  # 17:00

    # Which deadlines are matured at 17:00? Every timeout armed before
    # 16:45 (i * 27 s + 900 s <= 10 800 s -> i <= 366) plus every retry
    # backoff (seconds). The rest are live and must be left alone.
    due_timeouts = {
        f"order.o{i:04d}"
        for i in range(N_FLAKY, N_ORDERS)
        if i * 27.0 + FIFTEEN_MIN <= THREE_HOURS
    }
    due_retries = {f"order.o{i:04d}" for i in range(N_FLAKY)}
    expected_due = due_timeouts | due_retries
    not_yet = {f"order.o{i:04d}" for i in range(N_ORDERS)} - expected_due
    assert not_yet, "the story needs some orders whose timeout is still live"

    # ⏰ Drain. `limit=100` means several ticks; each tick must take the
    #    EARLIEST matured deadlines, so the first tick is the oldest
    #    orders and the lag metric is the full outage.
    ticks: List[Any] = []
    while True:
        r = scanner.scan(now)
        ticks.append(r)
        assert r.errors == [], r.errors
        if r.woken == 0:
            break
        assert len(ticks) < 20, "drain did not converge"
    # the oldest matured deadline is a retry backoff armed seconds after
    # 14:00 -- so the first tick reports (almost) the whole outage
    assert ticks[0].max_lag_s == pytest.approx(THREE_HOURS, abs=60.0)
    assert ticks[0].max_lag_s > THREE_HOURS - FIFTEEN_MIN

    first_tick_keys = {e.split(":")[0] for e in fires.events[: ticks[0].woken]}
    oldest = {f"order.o{i:04d}" for i in range(N_FLAKY, N_FLAKY + 100)}
    # the retry backoffs (seconds old at 14:00) are older than any timeout
    assert first_tick_keys <= (oldest | due_retries), sorted(
        first_tick_keys - oldest - due_retries
    )[:5]

    # ✅ exactly once per matured deadline; nothing not-yet touched
    assert set(fires.by_key) == expected_due
    assert set(fires.by_key.values()) == {1}
    for key in sorted(not_yet)[:3]:
        rec = store.load(key)
        assert rec is not None and rec.deadlines, key
    assert sum(t.woken for t in ticks) == len(expected_due)

    with TestClient(app) as c:
        assert state(c, "o0100") == "expired"
        assert state(c, "o0005") == "paid"  # flaky: retried and succeeded
        live = sorted(not_yet)[0].split(".", 1)[1]
        assert state(c, live) == "awaitingPayment"
    # 🔁 a second full drain at the same instant is a no-op
    assert scanner.scan(now).woken == 0


@pytest.mark.parametrize(
    "lock",
    [None, PessimisticLock(timeout=30)],
    ids=["optimistic", "pessimistic"],
)
def test_two_schedulers_by_accident_still_fire_exactly_once(
    afternoon: Dict[str, Any], lock: Any
) -> None:
    """The README says run exactly ONE scheduler. If an operator starts
    two, correctness must not depend on that advice.

    What "exactly once" means here (the guarantee the library states):
    each deadline is COMMITTED once -- the record's version advances by
    exactly one and the state is the fired one. Under `OptimisticLock`
    the loser has already run the transition in memory (actions
    included) before its save is refused with `ConflictError`, which the
    scanner counts as `skipped_stale`; so `on_transition` can fire twice
    per key while the commit is once. Under `PessimisticLock` the second
    scanner's re-read under the lock finds the deadline gone and nothing
    runs twice. Side effects are therefore AT-LEAST-once under the
    optimistic strategy: make timer actions idempotent or use the
    pessimistic one. Either way: no `errors` noise.
    """
    store, reg, t0 = afternoon["store"], afternoon["reg"], afternoon["t_down"]
    versions_before = {
        k: store.load(k).version for k in store.list_keys(prefix="order.")
    }
    fires = Fires()
    a = orders.build_scanner(reg, plugins=[*reg.plugins, fires], lock=lock)
    b = orders.build_scanner(reg, plugins=[*reg.plugins, fires], lock=lock)
    now = t0 + THREE_HOURS
    results: Dict[str, Any] = {}

    def run(name: str, sc: Any) -> None:
        total, stale = 0, 0
        errs: List[Any] = []
        for _ in range(30):
            r = sc.scan(now)
            total += r.woken
            stale += r.skipped_stale
            errs.extend(r.errors)
            if r.woken == 0 and r.due == 0:
                break
        results[name] = (total, stale, errs)

    ta = threading.Thread(target=run, args=("a", a))
    tb = threading.Thread(target=run, args=("b", b))
    ta.start()
    tb.start()
    ta.join(180)
    tb.join(180)
    assert not ta.is_alive() and not tb.is_alive()
    assert results["a"][2] == [] and results["b"][2] == [], (
        results["a"][2][:2],
        results["b"][2][:2],
    )
    # ✅ COMMITTED exactly once: every fired key's version is +1
    fired_keys = set(fires.by_key)
    for key in fired_keys:
        assert store.load(key).version == versions_before[key] + 1, key
    woken = results["a"][0] + results["b"][0]
    assert woken == len(fired_keys)  # one commit per fired key
    in_memory_doubles = sum(1 for n in fires.by_key.values() if n > 1)
    if lock is None:
        # optimistic: the losers ran in memory; the race decides how many
        assert results["a"][1] + results["b"][1] >= in_memory_doubles
    else:
        assert in_memory_doubles == 0, "pessimistic must not run twice"
    assert scanner_idle(a, now) and scanner_idle(b, now)


def scanner_idle(sc: Any, now: float) -> bool:
    r = sc.scan(now)
    return r.woken == 0 and r.due == 0 and r.errors == []


def test_crash_between_fire_and_save_refires_at_least_once(
    afternoon: Dict[str, Any], monkeypatch: Any
) -> None:
    """At-least-once: a scanner that fires a timer and dies before the
    save leaves the deadline in place; the next tick fires it again.
    The record is never torn (it is the OLD record until the save)."""
    store, reg, t0 = afternoon["store"], afternoon["reg"], afternoon["t_down"]
    key = f"order.o{N_FLAKY + 10:04d}"
    before = store.load(key)
    fires = Fires()
    scanner = orders.build_scanner(
        reg, plugins=[*reg.plugins, fires], prefix=key
    )
    now = t0 + THREE_HOURS

    # 💥 the "crash": the store's save raises once, AFTER the transition
    #    ran in memory
    real_save = store.save
    boom = {"armed": True}

    def crashing_save(*a: Any, **kw: Any) -> Any:
        if boom["armed"]:
            boom["armed"] = False
            raise RuntimeError("process killed before save")
        return real_save(*a, **kw)

    monkeypatch.setattr(store, "save", crashing_save)
    r1 = scanner.scan(now)
    assert r1.woken == 0 and len(r1.errors) == 1
    mid = store.load(key)
    assert (mid.version, mid.snapshot) == (before.version, before.snapshot)
    assert mid.deadlines == before.deadlines  # still due

    r2 = scanner.scan(now)
    assert r2.woken == 1 and r2.errors == []
    after = store.load(key)
    assert after.version == before.version + 1
    assert json.loads(after.snapshot)["state_ids"] == ["order.expired"]
    assert fires.by_key[key] == 2  # fired twice in memory, committed once
    assert scanner.scan(now).woken == 0
