# examples/integrations/fastapi_orders/tests/test_redis_fleet.py
"""#306 battle scenario: four workers on two hosts share ONE Redis.

The first question every web user asks -- "I have 4 uvicorn workers on 2
machines; where does the snapshot live?" -- answered with `RedisStore` +
`RedisInbox` behind the orders app, then attacked the way production
attacks it:

* **two hosts, one hot order** -- 200 `PAY`s spread over four registries
  (= four worker processes; each has its own breaker, its own in-memory
  state, nothing shared but Redis): exactly one charge, only 200/409,
  the inbox dedups across workers (a replay on host B of a key first
  seen on host A is `duplicate`);
* **a lock that expires under a slow worker** (`PessimisticLock`,
  `lock_ttl_ms` shorter than the gateway call): the stalled worker's
  save is a `ConflictError`, the fast worker's data wins, nothing is
  lost -- the fencing promise (X0.3) end to end through HTTP;
* **Redis goes away for the length of a failover** -- every request
  during the outage is a clean error (`503`-class, no 500 with a stack
  trace, no half-written order), and the first request after it comes
  back finds the order exactly as it was;
* **the scheduler on Redis** -- `due_keys` from the sorted-set index:
  400 orders, 40 retry deadlines, drained oldest-first in batches;
* **`forget()` after fulfilment** leaves no key behind in the namespace,
  and a key that another tenant's prefix *looks like* (`orders*`) is
  untouched;
* **nothing leaks** -- Redis connections (`CLIENT LIST` / pool size),
  threads and tracemalloc across 2 000 create → act → persist → discard
  cycles are flat.

Offline by default: one `fakeredis.FakeServer` shared by every "worker"
(the same server object, the way one Redis is shared by four processes).
Set ``XSM_REDIS_URL=redis://localhost:6379/15`` for a live Redis (the
outage test then needs ``XSM_REDIS_ADMIN=1`` to issue ``CLIENT PAUSE``).
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
import threading
import time
import tracemalloc
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("redis")
fakeredis = pytest.importorskip("fakeredis")

import app as orders  # noqa: E402
import logic  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from xstate_statemachine.contrib.redis import (  # noqa: E402
    RedisInbox,
    RedisStore,
)
from xstate_statemachine.exceptions import (  # noqa: E402
    ConflictError,
    StoreError,
)
from xstate_statemachine.patterns import MemoryDeadLetterStore  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    OptimisticLock,
    PessimisticLock,
)

pytestmark = pytest.mark.timeout(300)

ANN = {"x-customer": "ann"}
LIVE_URL = os.environ.get("XSM_REDIS_URL")
N_WORKERS = 4
N_PAYS = 200


# -----------------------------------------------------------------------------
# 🧰 one Redis, N workers
# -----------------------------------------------------------------------------
class Fleet:
    """N registries (= N worker processes) over ONE Redis namespace."""

    def __init__(self, n: int, *, lock: Any = None, **store_kw: Any) -> None:
        self.prefix = f"orders-{uuid.uuid4().hex[:8]}"
        self.server = None if LIVE_URL else fakeredis.FakeServer()
        self.clients: List[Any] = []
        self.registries: List[Any] = []
        self.apps: List[Any] = []
        self.emails: List[Any] = []
        for _ in range(n):
            client = self.client()
            store = RedisStore(client, prefix=self.prefix, **store_kw)
            inbox = RedisInbox(client, prefix=self.prefix)
            reg = orders.build_registry(
                store,
                inbox,
                lock=lock or OptimisticLock(),
                dead_letters=MemoryDeadLetterStore(),
            )
            self.registries.append(reg)
            self.apps.append(
                orders.create_app(
                    reg, email=lambda *a: self.emails.append(a), debug=False
                )
            )

    def client(self) -> Any:
        import redis

        c = (
            redis.Redis.from_url(LIVE_URL)
            if LIVE_URL
            else fakeredis.FakeRedis(server=self.server)
        )
        self.clients.append(c)
        return c

    @property
    def store(self) -> RedisStore:
        return self.registries[0].store

    def admin(self) -> Any:
        return self.clients[0]

    def keys(self, pattern: str = "*") -> List[str]:
        return sorted(
            k.decode() if isinstance(k, bytes) else k
            for k in self.admin().scan_iter(match=f"{self.prefix}:{pattern}")
        )

    def close(self) -> None:
        for k in self.admin().scan_iter(match=f"{self.prefix}:*"):
            self.admin().delete(k)
        for c in self.clients:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass


def post(c: Any, order: str, event: str, body: Any = None, **h: str) -> Any:
    return c.post(
        f"/orders/{order}/events/{event}", json=body, headers={**ANN, **h}
    )


def state(c: Any, order: str) -> Dict[str, Any]:
    return c.get(f"/orders/{order}", headers=ANN).json()


async def fan_out(
    apps: List[Any], order: str, n: int, headers: Dict[str, str]
) -> List[httpx.Response]:
    """n PAYs round-robin over the worker apps, all in flight at once."""
    clients = [
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=a),
            base_url="http://t",
            timeout=120,
        )
        for a in apps
    ]
    try:

        async def one(i: int) -> httpx.Response:
            return await clients[i % len(clients)].post(
                f"/orders/{order}/events/PAY",
                json={"card_token": "tok_ok"},
                headers={**ANN, **headers},
            )

        return list(
            await asyncio.wait_for(
                asyncio.gather(*(one(i) for i in range(n))), 240
            )
        )
    finally:
        for c in clients:
            await c.aclose()


@pytest.fixture
def fleet() -> Any:
    f = Fleet(N_WORKERS)
    yield f
    f.close()


# -----------------------------------------------------------------------------
# 1. two hosts, one hot order
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("idem", [None, "pay-fleet"])
def test_four_workers_one_order_exactly_one_charge(
    fleet: Fleet, idem: Optional[str]
) -> None:
    with TestClient(fleet.apps[0]) as c:
        post(c, "hot", "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, "hot", "CHECKOUT")
    headers = {"Idempotency-Key": idem} if idem else {}
    results = asyncio.run(fan_out(fleet.apps, "hot", N_PAYS, headers))
    bodies = [r.json() for r in results if r.status_code == 200]
    changed = [b for b in bodies if b["changed"] and not b["duplicate"]]
    # 💳 exactly one charge across four processes
    assert len(changed) == 1
    assert {r.status_code for r in results} <= {200, 409}
    assert len(fleet.emails) == 1
    with TestClient(fleet.apps[3]) as c:  # another host sees the result
        assert state(c, "hot")["state"] == "paid"
        if idem:
            # 🔁 the inbox is shared: the losers were `duplicate` (the
            #    winner had committed) or `409 in flight` (it had not yet);
            #    a replay on ANOTHER host afterwards is the ORIGINAL receipt
            dup = [b for b in bodies if b["duplicate"]]
            assert len(dup) + sum(r.status_code == 409 for r in results) == (
                N_PAYS - 1
            )
            again = post(
                c, "hot", "PAY", {"card_token": "tok_ok"}, **headers
            ).json()
            assert again["duplicate"] and again["state"] == "paid"
    assert len(fleet.emails) == 1
    rec = fleet.store.load("order.hot")
    assert rec is not None and rec.version >= 3


# -----------------------------------------------------------------------------
# 2. the lock expires under a slow worker: fenced, not lost
# -----------------------------------------------------------------------------
def test_expired_pessimistic_lock_is_fenced_end_to_end() -> None:
    f = Fleet(2, lock=PessimisticLock(timeout=5.0), lock_ttl_ms=150)
    try:
        with TestClient(f.apps[0]) as c:
            post(c, "slow", "ADD_ITEM", {"sku": "tea", "qty": 1})
            post(c, "slow", "CHECKOUT")
        gate = threading.Event()
        released = threading.Event()
        real = logic.charge_card

        def stalled_charge(i: Any, ctx: Any, e: Any, **kw: Any) -> Any:
            # ⏳ worker A holds the lock and stalls past its TTL
            gate.set()
            released.wait(5)
            return real(i, ctx, e, **kw)

        store0 = f.registries[0].store
        machine_a = f.registries[0].machine_for_store_key("order.slow")
        machine_a.logic.services["chargeCard"] = stalled_charge
        out: Dict[str, Any] = {}

        def worker_a() -> None:
            with TestClient(f.apps[0]) as c:
                out["a"] = post(c, "slow", "PAY", {"card_token": "tok_ok"})

        ta = threading.Thread(target=worker_a)
        ta.start()
        assert gate.wait(5)
        # the lock is gone after 150 ms; worker B takes it and pays
        time.sleep(0.3)
        assert store0.r.exists(store0.k.lock("order.slow")) == 0
        with TestClient(f.apps[1]) as c:
            out["b"] = post(c, "slow", "PAY", {"card_token": "tok_ok"})
        released.set()
        ta.join(30)
        assert out["b"].status_code == 200 and out["b"].json()["changed"]
        # 🛡️ A's save hits the version fence: 409, not a silent overwrite
        assert out["a"].status_code == 409, out["a"].text
        with TestClient(f.apps[1]) as c:
            s = state(c, "slow")
        assert s["state"] == "paid"
        rec = store0.load("order.slow")
        assert json.loads(rec.snapshot)["context"]["attempt"] == 0
        assert len(f.emails) == 1
    finally:
        f.close()


# -----------------------------------------------------------------------------
# 3. Redis goes away for the length of a failover
# -----------------------------------------------------------------------------
class _Outage:
    """Make every call on a client raise `redis.ConnectionError` while on."""

    def __init__(self, clients: List[Any]) -> None:
        import redis

        self.err = redis.ConnectionError("Error 111 connecting to redis")
        self.clients = clients
        self.saved: List[Tuple[Any, Any]] = []

    def __enter__(self) -> "_Outage":
        err = self.err
        for c in self.clients:
            orig = c.execute_command

            def boom(*a: Any, **k: Any) -> Any:
                raise err

            self.saved.append((c, orig))
            c.execute_command = boom
            # Lua scripts go through `evalsha` on the client too
            if hasattr(c, "evalsha"):
                self.saved.append((c, ("evalsha", c.evalsha)))
                c.evalsha = boom
        return self

    def __exit__(self, *exc: Any) -> None:
        for c, orig in reversed(self.saved):
            if isinstance(orig, tuple):
                setattr(c, orig[0], orig[1])
            else:
                c.execute_command = orig


def test_redis_outage_is_a_clean_error_and_nothing_is_lost(
    fleet: Fleet,
) -> None:
    with TestClient(fleet.apps[0]) as c:
        post(c, "o1", "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, "o1", "CHECKOUT")
        before = fleet.store.load("order.o1")
        with _Outage(fleet.clients):
            r = post(c, "o1", "PAY", {"card_token": "tok_ok"})
            # 🔌 a dependency outage: 5xx that is NOT a 500-with-traceback
            assert r.status_code in (502, 503), (r.status_code, r.text)
            body = r.text.lower()
            assert "traceback" not in body and "connectionerror" not in body
            g = c.get("/orders/o1", headers=ANN)
            assert g.status_code in (502, 503)
            # liveness stays 200 (the process is alive); readiness is 503
            assert c.get("/_xsm/health").status_code == 200
            assert c.get("/_xsm/ready").status_code == 503
        # 🩹 back: the order is exactly as it was, and PAY works once
        after = fleet.store.load("order.o1")
        assert (after.version, after.snapshot) == (
            before.version,
            before.snapshot,
        )
        assert (
            post(c, "o1", "PAY", {"card_token": "tok_ok"}).json()["state"]
            == "paid"
        )
    assert len(fleet.emails) == 1


def test_store_health_reports_the_outage(fleet: Fleet) -> None:
    assert fleet.store.health()["ok"] is True
    with _Outage(fleet.clients):
        h = fleet.store.health()
    assert h["ok"] is False and "error" in h


# -----------------------------------------------------------------------------
# 4. the scheduler on Redis: due_keys from the index
# -----------------------------------------------------------------------------
def test_scheduler_drains_redis_deadlines_oldest_first(fleet: Fleet) -> None:
    reg = fleet.registries[0]
    n, n_flaky = 120, 20
    with TestClient(fleet.apps[0]) as c:
        for i in range(n):
            o = f"d{i:03d}"
            post(c, o, "ADD_ITEM", {"sku": "tea", "qty": 1})
            post(c, o, "CHECKOUT")
            if i < n_flaky:
                assert (
                    post(c, o, "PAY", {"card_token": "tok_flaky"}).json()[
                        "state"
                    ]
                    == "retrying"
                )
    store = fleet.store
    due = store.due_keys(time.time() + 3600, limit=1000)
    assert len(due) == n  # one soonest deadline per order
    # retry backoffs (seconds) are due before any 15-minute timeout
    assert all(k.startswith("order.d0") for k, _ in due[:n_flaky])
    fired: List[str] = []

    class _Count:
        def on_transition(self, i: Any, a: Any, b: Any, t: Any) -> None:
            fired.append(i.store_key)

    sc = orders.build_scanner(reg, plugins=[_Count()], limit=50)
    now = time.time() + 20 * 60
    ticks = 0
    while True:
        res = sc.scan(now=now)
        ticks += 1
        if res.woken == 0:
            break
        assert ticks < 10
    assert ticks == 4  # 120 / 50 → 3 batches + the empty tick
    assert store.due_keys(now, limit=1000) == []
    with TestClient(fleet.apps[2]) as c:
        assert state(c, "d000")["state"] == "paid"  # retry fired → paid
        assert state(c, "d119")["state"] == "expired"  # timeout fired


# -----------------------------------------------------------------------------
# 5. forget() is total and namespace-safe
# -----------------------------------------------------------------------------
def test_forget_leaves_no_key_and_spares_lookalike_prefix(
    fleet: Fleet,
) -> None:
    other = RedisStore(fleet.client(), prefix=fleet.prefix + "-other")
    other.save("order.x", json.dumps({"k": 1}), expected_version=None)
    with TestClient(fleet.apps[0]) as c:
        post(c, "ship", "ADD_ITEM", {"sku": "tea", "qty": 1})
        post(c, "ship", "CHECKOUT")
        post(c, "ship", "PAY", {"card_token": "tok_ok"})
    assert fleet.keys("snap:order.ship") and fleet.keys("dl:order.ship") == []
    gone = fleet.store.forget("order.ship")
    assert gone and sum(gone.values()) >= 1
    assert fleet.keys("*order.ship*") == []
    assert "order.ship" not in fleet.store.list_keys(prefix="order.")
    assert other.load("order.x") is not None
    assert fleet.store.list_keys() == []  # not the lookalike's keys
    fleet.admin().delete(*other.r.scan_iter(match=f"{other.k.p}:*"))


# -----------------------------------------------------------------------------
# 6. nothing leaks over 2 000 create → act → persist → discard cycles
# -----------------------------------------------------------------------------
def test_two_thousand_cycles_leak_nothing(fleet: Fleet) -> None:
    def cycles(c: Any, n: int, start: int) -> None:
        for i in range(start, start + n):
            o = f"l{i:05d}"
            post(c, o, "ADD_ITEM", {"sku": "tea", "qty": 1})
            post(c, o, "CHECKOUT")
            post(c, o, "PAY", {"card_token": "tok_ok"})
            fleet.store.forget(f"order.{o}")

    pool0 = _pool_size(fleet.store.r)
    threads0 = threading.active_count()
    with TestClient(fleet.apps[1]) as c:
        cycles(c, 200, 0)  # warm up
        gc.collect()
        tracemalloc.start()
        cycles(c, 900, 200)
        gc.collect()
        half = tracemalloc.take_snapshot()
        cycles(c, 900, 1100)
        gc.collect()
        full = tracemalloc.take_snapshot()
        tracemalloc.stop()
    grown = sum(
        s.size_diff
        for s in full.compare_to(half, "filename")
        if s.size_diff > 0
    )
    assert grown < 2 * 1024 * 1024, f"{grown} bytes grew between N/2 and N"
    assert threading.active_count() <= threads0 + 1
    assert _pool_size(fleet.store.r) <= pool0 + 2
    assert fleet.keys("snap:*") == []


def _pool_size(r: Any) -> int:
    pool = getattr(r, "connection_pool", None)
    if pool is None:
        return 0
    return len(getattr(pool, "_available_connections", ())) + len(
        getattr(pool, "_in_use_connections", ())
    )


# -----------------------------------------------------------------------------
# 7. the error types the app layer relies on
# -----------------------------------------------------------------------------
def test_store_errors_are_typed_not_raw_redis(fleet: Fleet) -> None:
    store = fleet.store
    store.save("order.t", json.dumps({"a": 1}), expected_version=None)
    with pytest.raises(ConflictError):
        store.save("order.t", json.dumps({"a": 2}), expected_version=7)
    with _Outage(fleet.clients):
        with pytest.raises(StoreError):
            store.load("order.t")
        with pytest.raises(StoreError):
            store.save("order.t", json.dumps({"a": 3}), expected_version=1)
