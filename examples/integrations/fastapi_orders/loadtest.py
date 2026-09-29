# examples/integrations/fastapi_orders/loadtest.py
# -----------------------------------------------------------------------------
# 🔥 200 concurrent PAYs at ONE order across N uvicorn workers
# -----------------------------------------------------------------------------
# 🏛️ Plain asyncio + httpx, no locust. A Python launcher starts uvicorn
#    (`subprocess.Popen([sys.executable, "-m", "uvicorn", ...])` -- no fork,
#    no `& sleep 3`, works on Windows) and polls `/_xsm/health` until it
#    answers. Two rounds hit one order each:
#
#      * without Idempotency-Key -- the CHART is the guard: after `paid`
#        a second PAY is not handled (200 unchanged); racing saves lose
#        the version check (409).
#      * with one shared Idempotency-Key -- the INBOX is the guard too:
#        replays answer `duplicate` (200) or `in flight` (409).
#
#    Either way exactly ONE receipt may say `changed=True`. Exit 1 if not.
# -----------------------------------------------------------------------------
"""Load test: exactly one successful PAY under N workers."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

HERE = Path(__file__).resolve().parent
HEALTH = "/_xsm/health"
CUSTOMER = {"x-customer": "loadtest"}


# -----------------------------------------------------------------------------
# 🚀 Launcher
# -----------------------------------------------------------------------------
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def start_server(
    port: int, workers: int, env: Dict[str, str]
) -> "subprocess.Popen[bytes]":
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    if workers > 1:
        # 💡 Windows: uvicorn's multiprocess supervisor uses spawn -- fine.
        cmd += ["--workers", str(workers)]
    return subprocess.Popen(cmd, cwd=str(HERE), env=env)


def wait_healthy(
    base: str, proc: "subprocess.Popen[bytes]", timeout_s: float = 30.0
) -> None:
    """Poll `/_xsm/health` until 200, the process dies, or timeout."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited with {proc.returncode}")
        try:
            if httpx.get(base + HEALTH, timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"{base}{HEALTH} not healthy after {timeout_s}s")


def stop_server(proc: "subprocess.Popen[bytes]") -> None:
    if sys.platform == "win32":
        # ⚠️ TerminateProcess kills only the supervisor; its spawned
        #    workers would survive (holding the port and our stdout).
        #    Kill the whole tree.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        proc.terminate()  # SIGTERM: uvicorn stops its workers gracefully
    try:
        proc.wait(15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(5)


# -----------------------------------------------------------------------------
# 🔫 One round
# -----------------------------------------------------------------------------
async def prepare(client: httpx.AsyncClient, order: str) -> None:
    for event, body in (
        ("ADD_ITEM", {"sku": "tea", "qty": 1}),
        ("CHECKOUT", None),
    ):
        r = await client.post(
            f"/orders/{order}/events/{event}", json=body, headers=CUSTOMER
        )
        r.raise_for_status()


async def fire(
    client: httpx.AsyncClient, order: str, idem: Optional[str]
) -> Tuple[int, Dict[str, Any], float]:
    headers = dict(CUSTOMER)
    if idem is not None:
        headers["Idempotency-Key"] = idem
    t0 = time.perf_counter()
    r = await client.post(
        f"/orders/{order}/events/PAY",
        json={"card_token": "tok_ok"},
        headers=headers,
    )
    return r.status_code, r.json(), time.perf_counter() - t0


def classify(status: int, body: Dict[str, Any]) -> str:
    if status == 409:
        return "409"
    if status != 200:
        return f"other-{status}"
    if body.get("duplicate"):
        return "duplicate"
    return "changed" if body.get("changed") else "unchanged"


async def run_round(
    base: str, order: str, n: int, idem: Optional[str]
) -> Dict[str, Any]:
    limits = httpx.Limits(max_connections=n, max_keepalive_connections=n)
    async with httpx.AsyncClient(
        base_url=base, timeout=60.0, limits=limits
    ) as client:
        await prepare(client, order)
        results = await asyncio.gather(
            *(fire(client, order, idem) for _ in range(n))
        )
        final = (await client.get(f"/orders/{order}", headers=CUSTOMER)).json()
    kinds = Counter(classify(s, b) for s, b, _ in results)
    lat = sorted(t * 1000 for _, _, t in results)
    p95 = lat[max(0, int(round(0.95 * len(lat))) - 1)]
    return {
        "round": "with key" if idem else "no key",
        "kinds": kinds,
        "p50": statistics.median(lat),
        "p95": p95,
        "final": final.get("state"),
    }


def violations(res: Dict[str, Any], n: int) -> List[str]:
    k = res["kinds"]
    out = []
    if k["changed"] != 1:
        out.append(f"{res['round']}: {k['changed']} changed receipts (want 1)")
    allowed = {"changed", "unchanged", "duplicate", "409"}
    stray = {x: c for x, c in k.items() if x not in allowed}
    if stray:
        out.append(f"{res['round']}: unexpected responses {stray}")
    if sum(k.values()) != n:
        out.append(f"{res['round']}: {sum(k.values())} responses, want {n}")
    if res["final"] != "paid":
        out.append(f"{res['round']}: final state {res['final']!r}")
    return out


def print_table(rows: List[Dict[str, Any]], workers: int, n: int) -> None:
    print(f"\nworkers={workers} requests/round={n}")
    head = (
        f"{'round':<10}{'changed':>8}{'unchanged':>10}{'duplicate':>10}"
        f"{'409':>6}{'p50 ms':>9}{'p95 ms':>9}  final"
    )
    print(head)
    print("-" * len(head))
    for r in rows:
        k = r["kinds"]
        print(
            f"{r['round']:<10}{k['changed']:>8}{k['unchanged']:>10}"
            f"{k['duplicate']:>10}{k['409']:>6}{r['p50']:>9.1f}"
            f"{r['p95']:>9.1f}  {r['final']}"
        )


# -----------------------------------------------------------------------------
# 🏁 Main
# -----------------------------------------------------------------------------
def run_all(
    args: argparse.Namespace, port: int, base: str, tmp: str
) -> List[Dict[str, Any]]:
    env = dict(os.environ)
    env.pop("XSM_REDIS_URL", None)
    env["XSM_ORDERS_DB"] = str(Path(tmp) / "orders.db")
    # 🧱 Schema + WAL switch once, before N workers open the file.
    subprocess.run(
        [sys.executable, "app.py", "--role", "init"],
        cwd=str(HERE),
        env=env,
        check=True,
    )
    proc = start_server(port, args.workers, env)
    try:
        wait_healthy(base, proc)
        stamp = str(int(time.time() * 1000))
        return [
            asyncio.run(run_round(base, f"lt-{stamp}-a", args.requests, None)),
            asyncio.run(
                run_round(base, f"lt-{stamp}-b", args.requests, f"pay-{stamp}")
            ),
        ]
    finally:
        stop_server(proc)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args(argv)

    port = args.port or free_port()
    base = f"http://127.0.0.1:{port}"
    # 💡 rmtree(ignore_errors): Windows may hold the WAL files a moment
    #    after the workers exit.
    tmp = tempfile.mkdtemp(prefix="xsm-orders-")
    try:
        rows = run_all(args, port, base, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print_table(rows, args.workers, args.requests)
    problems = [v for r in rows for v in violations(r, args.requests)]
    for p in problems:
        print("VIOLATION:", p)
    print("OK" if not problems else "FAILED")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
