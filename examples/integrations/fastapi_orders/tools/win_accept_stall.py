# examples/integrations/fastapi_orders/tools/win_accept_stall.py
"""Reproduce the Windows `uvicorn --workers N` accept() stall (#277).

A do-nothing ASGI app -- no statechart, no store -- under N worker
processes. Each fleet: start, wait for health, fire a burst of concurrent
POSTs with a body, record the slowest request, stop. A request that
takes longer than ``--stall`` seconds while the rest take ~10 ms is the
stall: the worker that accepted it is blocked inside ``socket.accept()``
on the listening socket uvicorn shares between processes and runs no
code until the NEXT connection arrives. Measured here: 7 of 25 fleets at
4 workers; 0 of 25 at 1 worker.

    python tools/win_accept_stall.py --workers 4 --fleets 25
    python tools/win_accept_stall.py --workers 1 --fleets 25   # control
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent


async def app(scope, receive, send):  # noqa: D103 -- the no-op ASGI app
    if scope["type"] != "http":
        return
    body = b""
    while True:
        msg = await receive()
        body += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"ok"})


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


async def _burst(base: str, n: int) -> float:
    async with httpx.AsyncClient(
        base_url=base,
        timeout=30.0,
        limits=httpx.Limits(max_connections=n),
    ) as ac:

        async def one() -> float:
            t0 = time.perf_counter()
            try:
                await ac.post("/", json={"n": 1})
            except httpx.ReadTimeout:
                return 30.0
            return time.perf_counter() - t0

        return max(await asyncio.gather(*[one() for _ in range(n)]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fleets", type=int, default=25)
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--stall", type=float, default=5.0)
    args = ap.parse_args(argv)
    stalls = 0
    for i in range(args.fleets):
        port = _free_port()
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "win_accept_stall:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ]
        if args.workers > 1:
            cmd += ["--workers", str(args.workers)]
        proc = subprocess.Popen(cmd, cwd=str(HERE))
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    if httpx.get(base + "/", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.1)
            worst = asyncio.run(_burst(base, args.requests))
            hit = worst >= args.stall
            stalls += hit
            print(
                f"fleet {i + 1:>2}: slowest {worst:6.2f}s"
                f"{'  <-- STALL' if hit else ''}"
            )
        finally:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.terminate()
            proc.wait(15)
    print(
        f"\n{stalls} of {args.fleets} fleets stalled (workers={args.workers})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
