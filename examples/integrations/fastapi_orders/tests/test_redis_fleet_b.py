# examples/integrations/fastapi_orders/tests/test_redis_fleet_b.py
"""#306 battle scenario, part 2 (agent B): what a fleet over ONE Redis
does at the seams between hosts.

* **2-host Idempotency-Key race** -- host A is mid-charge when host B
  replays the same key: B gets ``409 IdempotencyInFlightError`` (never a
  second charge), and once A commits, a replay anywhere is the ORIGINAL
  receipt marked ``duplicate``.
* **SSE across hosts** -- SSE fan-out is per process (documented in
  *FastAPI → Troubleshooting*). A stream on host B does NOT see a commit
  made on host A; a reconnect's ``snapshot`` event (a fresh `peek` per
  connection) does. Pinned so the limitation cannot silently change.
* **two scanner processes** on one Redis -- every deadline is COMMITTED
  once (version +1); optimistic losers are ``skipped_stale``, pessimistic
  ones find the deadline gone. Mirrors
  ``test_scheduler_outage.py::test_two_schedulers_by_accident_still_fire_exactly_once``.
* **dead letters** -- the Redis wiring keeps them in a per-process
  `MemoryDeadLetterStore`: `xsm dlq` cannot see them and another worker
  does not either. Pinned, and documented in the README.

Offline on fakeredis by default; ``XSM_REDIS_URL`` runs it live.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any, Dict, List

import httpx
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("redis")
pytest.importorskip("fakeredis")

import app as orders  # noqa: E402
import logic  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from test_redis_fleet import ANN, Fleet, post, state  # noqa: E402

from xstate_statemachine.patterns import MemoryDeadLetterStore  # noqa: E402
from xstate_statemachine.persistence import PessimisticLock  # noqa: E402
from xstate_statemachine.plugins import PluginBase  # noqa: E402

pytestmark = pytest.mark.timeout(300)


def _ready(c: Any, order: str, token: str = "tok_ok") -> None:
    post(c, order, "ADD_ITEM", {"sku": "tea", "qty": 1})
    post(c, order, "CHECKOUT")


# -----------------------------------------------------------------------------
# 1. host A is mid-charge, host B replays the key
# -----------------------------------------------------------------------------
def test_replay_on_host_b_while_host_a_charges() -> None:
    f = Fleet(2)
    try:
        with TestClient(f.apps[0]) as c:
            _ready(c, "race")
        in_charge, release = threading.Event(), threading.Event()
        real = logic.charge_card
        calls: List[int] = []

        def slow_charge(i: Any, ctx: Any, e: Any, **kw: Any) -> Any:
            calls.append(1)
            in_charge.set()
            release.wait(10)
            return real(i, ctx, e, **kw)

        m_a = f.registries[0].machine_for_store_key("order.race")
        m_a.logic.services["chargeCard"] = slow_charge
        hdr = {"Idempotency-Key": "pay-race"}
        out: Dict[str, Any] = {}

        def host_a() -> None:
            with TestClient(f.apps[0]) as c:
                out["a"] = post(
                    c, "race", "PAY", {"card_token": "tok_ok"}, **hdr
                )

        ta = threading.Thread(target=host_a)
        ta.start()
        assert in_charge.wait(10)
        with TestClient(f.apps[1]) as c:
            mid = post(c, "race", "PAY", {"card_token": "tok_ok"}, **hdr)
        # ⏳ A holds the claim: B is told "in flight", nothing runs on B
        assert mid.status_code == 409, mid.text
        assert mid.json()["error"] == "IdempotencyInFlightError"
        release.set()
        ta.join(30)
        assert out["a"].status_code == 200 and out["a"].json()["changed"]
        with TestClient(f.apps[1]) as c:
            again = post(c, "race", "PAY", {"card_token": "tok_ok"}, **hdr)
            assert again.status_code == 200, again.text
            assert again.json()["duplicate"] is True
            assert again.json()["state"] == "paid"
            # 🔐 a different body under the same key is refused, on any host
            bad = post(c, "race", "PAY", {"card_token": "tok_other"}, **hdr)
            assert bad.status_code == 422
        assert len(calls) == 1 and len(f.emails) == 1
    finally:
        f.close()


# -----------------------------------------------------------------------------
# 2. SSE on host B, commit on host A
# -----------------------------------------------------------------------------
def test_sse_on_host_b_does_not_see_host_a_commit_until_reconnect() -> None:
    """At the fan-out seam the SSE endpoint reads from: a subscriber on
    host B's registry gets nothing for host A's commit; a fresh `peek`
    (what every new SSE connection sends as its ``snapshot`` event) sees
    it. (httpx' ASGI transport buffers a whole streaming body, so the
    seam is driven directly.)"""
    f = Fleet(2)
    try:
        with TestClient(f.apps[0]) as c:
            _ready(c, "sse")
        reg_a, reg_b = f.registries

        async def scenario() -> Any:
            sub_a = reg_a.subscribers.subscribe("order", "sse")
            sub_b = reg_b.subscribers.subscribe("order", "sse")
            t = httpx.ASGITransport(app=f.apps[0])
            async with httpx.AsyncClient(
                transport=t, base_url="http://t"
            ) as c:
                r = await c.post(
                    "/orders/sse/events/PAY",
                    json={"card_token": "tok_ok"},
                    headers=ANN,
                )
                assert r.status_code == 200, r.text
            got_a = await asyncio.wait_for(sub_a.queue.get(), 2)
            await asyncio.sleep(0.2)
            peek = await reg_b.peek("order", "sse")
            return got_a, sub_b.queue.qsize(), peek

        got_a, pending_b, peek = asyncio.run(scenario())
        assert got_a[1]["state"] == "paid"  # host A's own subscribers: yes
        assert pending_b == 0  # 📝 host B's: nothing (per-process fan-out)
        assert peek["state"] == "paid"  # a reconnect's snapshot: yes
    finally:
        f.close()


# -----------------------------------------------------------------------------
# 3. two scanner processes on one Redis
# -----------------------------------------------------------------------------
class _Fires(PluginBase):
    def __init__(self) -> None:
        self.by_key: Dict[str, int] = {}
        self._lock = threading.Lock()

    def on_transition(self, i: Any, a: Any, b: Any, t: Any) -> None:
        if str(getattr(t, "event", "") or "").startswith("after."):
            with self._lock:
                self.by_key[i.store_key] = self.by_key.get(i.store_key, 0) + 1


@pytest.mark.parametrize("pessimistic", [False, True])
def test_two_scanners_on_redis_commit_each_deadline_once(
    pessimistic: bool,
) -> None:
    lock = PessimisticLock(timeout=10.0) if pessimistic else None
    f = Fleet(2, lock=lock) if lock else Fleet(2)
    try:
        n = 60
        with TestClient(f.apps[0]) as c:
            for i in range(n):
                _ready(c, f"s{i:02d}")
        store = f.store
        before = {
            k: store.load(k).version for k in store.list_keys(prefix="order.")
        }
        fires = _Fires()
        scanners = [
            orders.build_scanner(reg, plugins=[*reg.plugins, fires], limit=10)
            for reg in f.registries
        ]
        now = time.time() + 20 * 60  # past every 15-minute timeout
        results: Dict[int, Any] = {}

        def run(idx: int) -> None:
            woken = stale = 0
            errs: List[Any] = []
            for _ in range(40):
                r = scanners[idx].scan(now=now)
                woken, stale = woken + r.woken, stale + r.skipped_stale
                errs.extend(r.errors)
                if r.woken == 0 and r.due == 0:
                    break
            results[idx] = (woken, stale, errs)

        ts = [threading.Thread(target=run, args=(i,)) for i in (0, 1)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(180)
        assert results[0][2] == [] and results[1][2] == [], results
        for key, v in before.items():
            assert store.load(key).version == v + 1, key  # committed once
        assert results[0][0] + results[1][0] == n
        doubles = sum(1 for k in fires.by_key.values() if k > 1)
        if pessimistic:
            assert doubles == 0  # the loser re-read under the lock
        else:
            assert results[0][1] + results[1][1] >= doubles
        assert store.due_keys(now, limit=1000) == []
        with TestClient(f.apps[1]) as c:
            assert state(c, "s00")["state"] == "expired"
    finally:
        f.close()


# -----------------------------------------------------------------------------
# 4. dead letters under the Redis wiring are per process
# -----------------------------------------------------------------------------
def test_redis_dead_letters_are_per_process_memory() -> None:
    """`build_dead_letter_store` gives Redis deployments a
    `MemoryDeadLetterStore`: the worker that exhausted the retries holds
    the record, its peers and `xsm dlq` (which reads a URL) do not. The
    README says to wire a `BrokerDeadLetterSink` for Redis; this pins why."""
    f = Fleet(2)
    try:
        assert all(
            isinstance(r.dead_letters, MemoryDeadLetterStore)
            for r in f.registries
        )
        with TestClient(f.apps[0]) as c:
            _ready(c, "dl")
            post(c, "dl", "PAY", {"card_token": "tok_declined"})
        sc = orders.build_scanner(f.registries[0])
        now = time.time()
        for step in range(1, 8):
            sc.scan(now=now + step * 120)
        with TestClient(f.apps[1]) as c:
            assert state(c, "dl")["state"] == "paymentFailed"
        on_a = f.registries[0].dead_letters
        on_b = f.registries[1].dead_letters
        assert len(list(on_a.list())) == 1
        assert list(on_b.list()) == []  # host B cannot triage it
        assert not f.keys("*dlq*") and not f.keys("*dead*")  # not in Redis
        rec = list(on_a.list())[0]
        assert "s3cr3t" not in json.dumps(rec, default=str)
    finally:
        f.close()
