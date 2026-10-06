"""#277 battle (A): multi-process defects, against REAL worker processes.

* **charges across processes** -- 4 workers × 200 PAYs at one order:
  the fake gateway (logging every call to ``XSM_GATEWAY_LOG``, since the
  workers are separate processes) is hit exactly once, with and without
  an ``Idempotency-Key``; only 200 / 409;
* **two schedulers by accident** -- the payment timeout still fires once;
* **no ``--role init``** -- 4 workers racing an empty file all come up,
  serve, and the file ends in WAL (a loser used to fall back to the
  rollback journal for its lifetime);
* **fleet cycles** -- start → burst → stop × N: no request slower than
  5 s, no orphan worker, the temp dir is removable. Skipped on Windows:
  there a worker's event loop can block inside ``accept()`` on the
  listening socket uvicorn shares into N processes (non-blocking or not),
  freezing every request that worker already accepted until the NEXT new
  connection -- the long-standing "one request stalls to the client
  timeout" (reproduced with a no-op ASGI app, 7 of 25 fleets, and with
  bare sockets; not this library);
* **/metrics** is served (in-process, `PrometheusPlugin`).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")
httpx = pytest.importorskip("httpx")

import loadtest  # noqa: E402

pytestmark = [
    pytest.mark.timeout(600),
    pytest.mark.skipif(
        os.environ.get("XSM_SKIP_PROCESS_TESTS") == "1",
        reason="process-spawning tests disabled",
    ),
]

HERE = Path(__file__).resolve().parents[1]
WORKERS = int(os.environ.get("XSM_BATTLE_277_WORKERS", "4"))
CUSTOMER = {"x-customer": "battle-a"}
# see test_battle_277_fleet.WINDOWS_UVICORN_STALL: a 200-request burst at
# N Windows workers can park one request on a frozen accept() -- not ours
WINDOWS_UVICORN_STALL = pytest.mark.skipif(
    sys.platform == "win32" and WORKERS > 1,
    reason="uvicorn --workers N on Windows: shared-socket accept() stall",
)
STALL_S = 5.0


class Fleet:
    def __init__(self, tmp: Path, workers: int = WORKERS) -> None:
        self.tmp = tmp
        self.workers = workers
        self.env = dict(os.environ)
        self.env.pop("XSM_REDIS_URL", None)
        self.env["XSM_ORDERS_DB"] = str(tmp / "orders.db")
        self.env["XSM_GATEWAY_LOG"] = str(tmp / "gateway.log")
        self.env["PYTHONUTF8"] = "1"
        self.port = loadtest.free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.web: Any = None
        self.schedulers: List[Any] = []

    def init(self) -> None:
        subprocess.run(
            [sys.executable, "app.py", "--role", "init"],
            cwd=str(HERE),
            env=self.env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def start_web(self) -> None:
        self.web = loadtest.start_server(self.port, self.workers, self.env)
        loadtest.wait_healthy(self.base, self.web, timeout_s=60)

    def start_scheduler(self, interval_s: float = 0.2) -> None:
        self.schedulers.append(
            subprocess.Popen(
                [sys.executable, "app.py", "--role", "scheduler"]
                + ["--interval", str(interval_s)],
                cwd=str(HERE),
                env=self.env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )

    def stop(self) -> None:
        for proc in [self.web, *self.schedulers]:
            if proc is not None and proc.poll() is None:
                loadtest.stop_server(proc)
        self.web, self.schedulers = None, []

    def gateway_calls(self, order: str) -> int:
        log = self.tmp / "gateway.log"
        if not log.exists():
            return 0
        lines = log.read_text("utf-8").splitlines()
        return sum(1 for ln in lines if ln.endswith(f"order.{order}"))


@pytest.fixture
def fleet() -> Any:
    tmp = Path(tempfile.mkdtemp(prefix="xsm-277a-"))
    f = Fleet(tmp)
    try:
        yield f
    finally:
        f.stop()
        shutil.rmtree(tmp, ignore_errors=True)


async def _post(
    ac: Any, order: str, event: str, body: Any = None, **h: str
) -> Tuple[int, Dict[str, Any], float]:
    t0 = time.perf_counter()
    r = await ac.post(
        f"/orders/{order}/events/{event}", json=body, headers={**CUSTOMER, **h}
    )
    try:
        data = r.json()
    except ValueError:
        data = {}
    return r.status_code, data, time.perf_counter() - t0


def _client(base: str, n: int) -> Any:
    limits = httpx.Limits(max_connections=n, max_keepalive_connections=n)
    return httpx.AsyncClient(base_url=base, timeout=60.0, limits=limits)


async def _pay_burst(
    base: str, order: str, n: int, key: Optional[str]
) -> List[Tuple[int, Dict[str, Any], float]]:
    async with _client(base, n) as ac:
        await _post(ac, order, "ADD_ITEM", {"sku": "tea", "qty": 1})
        await _post(ac, order, "CHECKOUT")
        h = {"Idempotency-Key": key} if key else {}
        body = {"card_token": "tok_ok"}
        return list(
            await asyncio.gather(
                *[_post(ac, order, "PAY", body, **h) for _ in range(n)]
            )
        )


# -----------------------------------------------------------------------------
# 1. exactly one gateway call across processes
# -----------------------------------------------------------------------------
@WINDOWS_UVICORN_STALL
@pytest.mark.parametrize("with_key", [False, True])
def test_one_gateway_call_across_worker_processes(
    fleet: Fleet, with_key: bool
) -> None:
    fleet.init()
    fleet.start_web()
    order = f"chg-{int(with_key)}-{int(time.time() * 1000)}"
    key = f"pay-{order}" if with_key else None
    results = asyncio.run(_pay_burst(fleet.base, order, 200, key))
    codes = {s for s, _, _ in results}
    assert codes <= {200, 409}, codes
    changed = [b for s, b, _ in results if s == 200 and b.get("changed")]
    # 📝 with a key, replays echo the ORIGINAL receipt (changed=True,
    #    duplicate=True); exactly one is the first-time commit
    first = [b for b in changed if not b.get("duplicate")]
    assert len(first) == 1, len(first)
    assert fleet.gateway_calls(order) == 1


# -----------------------------------------------------------------------------
# 2. two schedulers started by accident
# -----------------------------------------------------------------------------
def test_two_scheduler_processes_fire_the_deadline_once(fleet: Fleet) -> None:
    fleet.env["XSM_PAYMENT_TIMEOUT_MS"] = "1000"
    fleet.init()
    fleet.start_web()
    orders = [f"exp2-{i}-{int(time.time() * 1000)}" for i in range(10)]

    async def arm() -> None:
        async with _client(fleet.base, 10) as ac:
            for o in orders:
                assert (
                    await _post(ac, o, "ADD_ITEM", {"sku": "tea", "qty": 1})
                )[0] == 200
                assert (await _post(ac, o, "CHECKOUT"))[0] == 200

    asyncio.run(arm())
    fleet.start_scheduler(0.05)
    fleet.start_scheduler(0.05)
    deadline = time.monotonic() + 30
    states: Dict[str, str] = {}
    while time.monotonic() < deadline:
        states = {
            o: httpx.get(f"{fleet.base}/orders/{o}", headers=CUSTOMER).json()[
                "state"
            ]
            for o in orders
        }
        if set(states.values()) == {"expired"}:
            break
        time.sleep(0.3)
    assert set(states.values()) == {"expired"}, states
    time.sleep(1.0)  # a second scheduler's late save would land now
    from xstate_statemachine.persistence import SQLiteStore

    store = SQLiteStore(fleet.env["XSM_ORDERS_DB"])
    try:
        versions = [store.load(f"order.{o}").version for o in orders]
    finally:
        store.close()
    assert versions == [3] * len(orders)  # ADD, CHECKOUT, ONE expiry


# -----------------------------------------------------------------------------
# 3. no `--role init`
# -----------------------------------------------------------------------------
@WINDOWS_UVICORN_STALL
def test_workers_without_init_all_serve_and_the_file_is_wal(
    fleet: Fleet,
) -> None:
    fleet.start_web()  # 🔥 no fleet.init(): N workers race the empty file
    order = f"noinit-{int(time.time() * 1000)}"

    async def go() -> List[int]:
        async with _client(fleet.base, 40) as ac:
            rs = await asyncio.gather(
                *[
                    _post(
                        ac,
                        f"{order}-{i}",
                        "ADD_ITEM",
                        {"sku": "tea", "qty": 1},
                    )
                    for i in range(40)
                ]
            )
            return [s for s, _, _ in rs]

    assert set(asyncio.run(go())) == {200}
    conn = sqlite3.connect(fleet.env["XSM_ORDERS_DB"])
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode == "wal"


# -----------------------------------------------------------------------------
# 4. fleet cycles: no stall, no leak
# -----------------------------------------------------------------------------
def _python_children_of(pid: int) -> int:
    if sys.platform != "win32":
        out = subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True
        ).stdout
        return len(out.split())
    out = subprocess.run(
        [
            "wmic",
            "process",
            "where",
            f"ParentProcessId={pid}",
            "get",
            "ProcessId",
        ],
        capture_output=True,
        text=True,
    ).stdout
    return len([x for x in out.split() if x.isdigit()])


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows: a uvicorn worker loop can block in accept() on the "
    "shared listen socket (no-op ASGI app: 7 of 25 fleets) -- not ours",
)
def test_fleet_cycles_have_no_stall_and_leave_nothing_behind() -> None:
    cycles = int(os.environ.get("XSM_BATTLE_277_CYCLES", "5"))
    worst = 0.0
    for c in range(cycles):
        tmp = Path(tempfile.mkdtemp(prefix="xsm-277a-cyc-"))
        f = Fleet(tmp)
        f.init()
        f.start_web()
        sup = f.web.pid
        try:
            rs = asyncio.run(_pay_burst(f.base, f"cyc{c}", 200, None))
            worst = max(worst, max(t for _, _, t in rs))
            assert {s for s, _, _ in rs} <= {200, 409}
        finally:
            f.stop()
        assert _python_children_of(sup) == 0  # no orphan worker
        shutil.rmtree(tmp)  # 🔥 raises if a process still holds the DB
    assert worst < STALL_S, worst


# -----------------------------------------------------------------------------
# 5. /metrics
# -----------------------------------------------------------------------------
def test_metrics_endpoint_counts_transitions(tmp_path: Path) -> None:
    pytest.importorskip("prometheus_client")
    from fastapi.testclient import TestClient

    import app as app_module
    from app import build_registry, create_app
    from xstate_statemachine.persistence import SQLiteStore

    store = SQLiteStore(tmp_path / "m.db")
    try:
        from xstate_statemachine.persistence import SQLiteInbox

        a = create_app(build_registry(store, SQLiteInbox(store)))
        with TestClient(a) as c:
            c.post(
                "/orders/m1/events/ADD_ITEM",
                json={"sku": "tea", "qty": 1},
                headers=CUSTOMER,
            )
            r = c.get("/metrics")
        assert r.status_code == 200
        assert 'event="ADD_ITEM"' in r.text
        assert app_module.add_metrics_route  # documented hook
    finally:
        store.close()
