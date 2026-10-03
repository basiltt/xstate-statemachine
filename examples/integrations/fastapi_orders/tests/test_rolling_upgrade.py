# examples/integrations/fastapi_orders/tests/test_rolling_upgrade.py
"""#263 battle scenario: deploy chart v2 while v1 orders are mid-flight.

A v1 deployment persists orders at every interesting point -- in the
cart, checked out with a live 15-minute timeout, in `retrying` with a live
backoff deadline, paid, shipped. Then the v2 workers and the v2 scheduler
take over the same store. Nothing is rewritten in bulk: each stale order
is migrated the first time a v2 process touches it, re-saved at label
"2", and never migrated twice -- also when 50 requests race on one stale
order. `xsm snapshots --stale` is the drain list before and after.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from typing import Any, Dict, List

import pytest

pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
from migrations import V1_PAYING, V2_AUTHORISING  # noqa: E402
from xstate_statemachine import SyncInterpreter  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    MachineVersionMismatchError,
    SQLiteInbox,
    SQLiteStore,
    persisted,
    save_interpreter,
)

ANN = {"x-customer": "ann"}
FIFTEEN_MIN = 900


def post(client: Any, order: str, event: str, body: Any = None) -> Any:
    return client.post(
        f"/orders/{order}/events/{event}", json=body, headers=ANN
    )


def state(client: Any, order: str) -> Dict[str, Any]:
    return client.get(f"/orders/{order}", headers=ANN).json()


def labels(store: SQLiteStore) -> Dict[str, str]:
    return {
        k.split(".", 1)[1]: store.load(k).machine_version
        for k in store.list_keys(prefix="order.")
    }


def xsm_stale(db: str, chart: str) -> List[str]:
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "snapshots",
            "--store",
            "sqlite:///" + db.replace("\\", "/"),
            chart,
            "--stale",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return sorted(r["key"] for r in json.loads(out.stdout)["snapshots"])


# -----------------------------------------------------------------------------
# 🏗️ A v1 deployment leaves orders at every interesting point
# -----------------------------------------------------------------------------
@pytest.fixture
def v1_world(tmp_path: Any, monkeypatch: Any) -> Dict[str, Any]:
    monkeypatch.setenv("XSM_ORDERS_RETRY_BASE_MS", "2000")
    db = str(tmp_path / "orders.db")
    store = SQLiteStore(db)
    reg1 = orders.build_registry(store, SQLiteInbox(store), chart="1")
    app1 = orders.create_app(reg1, email=lambda *a: None, debug=False)
    t0 = time.time()
    with TestClient(app1) as c:
        post(c, "cart", "ADD_ITEM", {"sku": "mug", "qty": 1})
        for o in ("waiting", "retrying", "paid", "shipped"):
            post(c, o, "ADD_ITEM", {"sku": "tea", "qty": 2})
            post(c, o, "CHECKOUT")
        # a live backoff deadline: tok_flaky fails the first attempt
        r = post(c, "retrying", "PAY", {"card_token": "tok_flaky"})
        assert r.json()["state"] == "retrying"
        post(c, "paid", "PAY", {"card_token": "tok_ok"})
        post(c, "shipped", "PAY", {"card_token": "tok_ok"})
        post(c, "shipped", "FULFIL")
        post(c, "shipped", "PACKED")
        assert post(c, "shipped", "LABEL_PRINTED").json()["state"] == "shipped"
    # 📝 An order whose v1 process died MID-CHARGE: the snapshot says
    #    `paying` and the invoke is gone. Written directly, the way a
    #    crashed worker leaves it (the request path never persists an
    #    in-flight invoke). `paying` has no `after`, so the record carries
    #    no deadlines -- a deadline for a state that is not active is a
    #    contradiction the restore refuses (`StateNotFoundError`), and
    #    rightly: a silently dropped SLA is what durable timers prevent.
    with persisted(
        store, "order.midcharge", reg1.machine_for_store_key("order.x")
    ) as i:
        i.send("ADD_ITEM", sku="kettle", qty=1)
        i.send("CHECKOUT")
    rec = store.load("order.midcharge")
    blob = json.loads(rec.snapshot)
    blob["state_ids"] = [V1_PAYING]
    blob["configuration"] = ["order", V1_PAYING]
    blob["deadlines"] = []
    blob["context"]["card_token"] = "tok_ok"
    store.save(
        "order.midcharge",
        json.dumps(blob),
        expected_version=rec.version,
        machine_version="1",
        deadlines=[],
    )
    assert set(labels(store).values()) == {"1"}
    return {"db": db, "store": store, "t0": t0}


# -----------------------------------------------------------------------------
# 🚀 v2 takes over
# -----------------------------------------------------------------------------
def test_v2_without_migrator_refuses_loudly(v1_world: Dict[str, Any]) -> None:
    """The default policy: a v2 worker WITHOUT the migrator does not
    half-restore a v1 order -- the request is a typed 409/500 problem,
    the stored record is untouched."""
    store = v1_world["store"]
    reg2 = orders.build_registry(
        store, SQLiteInbox(store), chart="2", migrator=None
    )
    before = store.load("order.paid")
    with TestClient(
        orders.create_app(reg2, email=lambda *a: None, debug=False),
        raise_server_exceptions=False,
    ) as c:
        r = c.get("/orders/paid", headers=ANN)
        assert r.status_code in (409, 500)
        assert "MachineVersionMismatchError" in r.text
        assert "card_token" not in r.text and "tok_ok" not in r.text
    after = store.load("order.paid")
    assert (after.version, after.machine_version) == (
        before.version,
        before.machine_version,
    )


def test_rolling_upgrade_migrates_lazily_once_per_order(
    v1_world: Dict[str, Any],
) -> None:
    db, store, t0 = v1_world["db"], v1_world["store"], v1_world["t0"]
    v2_chart = str(orders.chart_path("2"))
    stale_before = xsm_stale(db, v2_chart)
    assert len(stale_before) == 6  # every v1 order is on the drain list

    reg2 = orders.build_registry(store, SQLiteInbox(store), chart="2")
    app2 = orders.create_app(reg2, email=lambda *a: None, debug=False)
    scanner = orders.build_scanner(reg2)

    with TestClient(app2) as c:
        # 👀 a READ shows the migrated view but writes nothing: the label
        #    stays "1" (a GET must never mutate the store)
        assert state(c, "cart")["state"] == "cart"
        assert state(c, "cart")["context"]["total_cents"] == 1200
        assert labels(store)["cart"] == "1"
        # ✍️ the first WRITE migrates and re-saves at the new label
        assert post(c, "cart", "ADD_ITEM", {"sku": "tea", "qty": 1}).is_success
        assert labels(store)["cart"] == "2"
        # 💳 the mid-charge order lands in v2's authorising step; the
        #    (idempotent) charge is re-attempted when the instance is
        #    next driven -- here by the scheduler's wake below, or any
        #    write. Read-only it is simply reported in its new place.
        assert state(c, "midcharge")["state"] == {"payment": "authorising"}
        # ✅ paid / shipped: a label-only change, state preserved
        assert state(c, "paid")["state"] == "paid"
        assert state(c, "shipped")["state"] == "shipped"
        assert state(c, "paid")["context"]["charge_id"]
        # ⏰ the live deadlines survived the migration: the scheduler
        #    (a v2 process) wakes the retry and the timeout, and the
        #    wake IS a write -- those two are re-saved at "2".
        assert labels(store)["retrying"] == "1"
        woke = scanner.scan(t0 + 60)
        assert woke.errors == [] and woke.woken >= 1
        assert state(c, "retrying")["state"] == "paid"
        assert labels(store)["retrying"] == "2"
        woke = scanner.scan(t0 + FIFTEEN_MIN + 1)
        assert woke.errors == []
        assert state(c, "waiting")["state"] == "expired"
        assert labels(store)["waiting"] == "2"
        # 📝 `hot` was checked out in v1 too, so the timeout scan above
        #    expired it along with `waiting` -- correct, and it leaves no
        #    stale order to race on. Make a FRESH v1 record for the race.
        _write_v1_checked_out(store, "order.hot", orders.build_machine("1"))
        assert labels(store)["hot"] == "1"
        # 🔥 50 concurrent PAYs on a STALE order: one migration commits,
        #    one charge, the rest 409 -- same contract as on a fresh order.
        step_calls = _count_step_calls(reg2)
        results = asyncio.run(_race(app2, "hot", 50))
        changed = [
            r for r in results if r.status_code == 200 and r.json()["changed"]
        ]
        assert len(changed) == 1, sorted(
            (r.status_code, r.text[:160]) for r in results
        )[:3]
        assert {r.status_code for r in results} <= {200, 409}
        assert state(c, "hot")["state"] == "paid"
        assert 1 <= step_calls() <= 50
        # 🧹 drain the rest with a no-op write each (what an ops script
        #    does with the --stale list)
        for key in xsm_stale(db, v2_chart):
            order = key.split(".", 1)[1]
            if state(c, order)["state"] == {"payment": "authorising"}:
                continue  # midcharge: driven by its own charge below
            post(c, order, "CANCEL", {"reason": "drain"})
    # 💳 the mid-charge order: migrated into `payment.authorising` with the
    #    invoke DORMANT (the v1 process died in it). That is the general
    #    "crashed mid-invoke" case, not a versioning one: a v2 operator
    #    restores it with `restart_services=True`, the idempotent charge
    #    re-runs, capture follows, and the re-save lands at "2".
    rec = store.load("order.midcharge")
    assert rec.machine_version == "1"
    v2 = reg2.machine_for_store_key("order.x")
    i = SyncInterpreter.from_snapshot(
        rec.snapshot, v2, migrator=reg2.migrator, restart_services=True
    )
    assert i.has_dormant_invocations
    i.start()
    try:
        assert i.current_state_ids == {"order.paid"}
        assert i.context["currency"] == "USD" and i.context["charge_id"]
    finally:
        i.stop()
    save_interpreter(store, "order.midcharge", i, expected_version=rec.version)
    assert set(labels(store).values()) == {"2"}
    assert xsm_stale(db, v2_chart) == []
    # a v2 blob into the OLD chart is refused -- the dual-read window
    # must carry the migrator on the readers first
    with pytest.raises(MachineVersionMismatchError):
        with persisted(
            store, "order.paid", orders.build_machine("1"), lock=None
        ):
            pass


def _write_v1_checked_out(store: Any, key: str, machine_v1: Any) -> None:
    """A v1 record in `awaitingPayment` -- what a v1 worker leaves behind."""
    with persisted(store, key, machine_v1, lock=None) as i:
        i.send("ADD_ITEM", sku="tea", qty=2)
        i.send("CHECKOUT")
    assert store.load(key).machine_version == "1"


def _count_step_calls(registry: Any) -> Any:
    """Wrap the registered 1->2 step to count invocations."""
    mig = registry.migrator
    key = ("order", "1", "2")
    original = mig._steps[key]
    calls = [0]

    def counting(blob: Dict[str, Any]) -> Dict[str, Any]:
        calls[0] += 1
        return original(blob)

    mig._steps[key] = counting
    return lambda: calls[0]


async def _race(app: Any, order: str, n: int) -> List[Any]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://t", timeout=60
    ) as client:

        async def one() -> Any:
            return await client.post(
                f"/orders/{order}/events/PAY",
                json={"card_token": "tok_ok"},
                headers=ANN,
            )

        return await asyncio.wait_for(
            asyncio.gather(*(one() for _ in range(n))), 120
        )


def test_v2_chart_validates_and_authorise_capture_flow(tmp_path: Any) -> None:
    """The v2 chart on its own: authorise -> capture -> paid, and the
    retry path from a failed authorisation."""
    store = SQLiteStore(str(tmp_path / "v2.db"))
    reg2 = orders.build_registry(store, SQLiteInbox(store), chart="2")
    scanner = orders.build_scanner(reg2)
    with TestClient(
        orders.create_app(reg2, email=lambda *a: None, debug=False)
    ) as c:
        post(c, "o", "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, "o", "CHECKOUT")
        r = post(c, "o", "PAY", {"card_token": "tok_ok"})
        assert r.json()["state"] == "paid"
        assert r.json()["context"]["charge_id"].startswith("ch_")
        post(c, "f", "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, "f", "CHECKOUT")
        assert (
            post(c, "f", "PAY", {"card_token": "tok_flaky"}).json()["state"]
            == "retrying"
        )
        assert scanner.scan(time.time() + 60).woken == 1
        assert state(c, "f")["state"] == "paid"
    assert V2_AUTHORISING  # imported symbol is the v2 leaf used above
