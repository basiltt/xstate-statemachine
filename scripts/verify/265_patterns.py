"""Verification for #265 (A8 patterns). `python scripts/verify/265_patterns.py`.

Runs against the installed package. Retry loop through 3 failures then
success; a 4th failure with max_attempts=3 dead-letters with the error
chain and attempts; circuit breaker opens / fast-fails / half-opens on the
simulated clock / closes; 32-thread hammer admits exactly one probe; the
async twin; `xsm inspect` renders the breaker chart.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str) -> None:
    print(f"\n== {name}")


RETRY_CFG = {
    "id": "job",
    "initial": "attempting",
    "context": {"attempt": 0, "token": "secret"},
    "states": {
        "attempting": {
            "invoke": {
                "src": "work",
                "onDone": {"target": "done", "actions": "retryReset"},
                "onError": {"target": "retrying", "actions": "retryBump"},
            }
        },
        "retrying": {
            "after": {
                "retryDelay": [
                    {"guard": "retryCanRetry", "target": "attempting"},
                    {"target": "deadLettered"},
                ]
            }
        },
        "done": {"type": "final"},
        "deadLettered": {"type": "final", "tags": ["dead-letter"]},
    },
}


def main() -> int:
    from xstate_statemachine import (
        MachineLogic,
        SimulatedClock,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.patterns import (
        CIRCUIT_BREAKER_CONFIG,
        CircuitBreaker,
        CircuitOpenError,
        DeadLetterPlugin,
        DeadLetterStore,
        RetryPolicy,
    )

    step("RetryPolicy delays")
    p = RetryPolicy(max_attempts=5, base_ms=100, jitter="none")
    delays = [p.delay_ms(a) for a in range(1, 6)]
    print(delays)
    assert delays == [100, 200, 400, 800, 1600]

    def flaky(n_fail: int):
        calls = {"n": 0}

        def work(i, c, e):  # noqa: ANN001
            calls["n"] += 1
            if calls["n"] <= n_fail:
                raise ConnectionError(f"boom #{calls['n']}")
            return "ok"

        return work, calls

    step("retry loop: 3 failures then success")
    work, calls = flaky(3)
    m = create_machine(
        RETRY_CFG,
        logic=RetryPolicy(max_attempts=5, base_ms=100, jitter="none")
        .logic()
        .merge(MachineLogic(services={"work": work})),
    )
    clk = SimulatedClock()
    i = SyncInterpreter(m, clock=clk).start()
    for _ in range(6):
        clk.increment(100_000)
    print("state:", sorted(i.current_state_ids), "calls:", calls["n"])
    assert i.matches("job.done") and calls["n"] == 4

    step("retry loop: gives up at max_attempts=3 -> dead letter")
    work, calls = flaky(99)
    m = create_machine(
        RETRY_CFG,
        logic=RetryPolicy(max_attempts=3, base_ms=100, jitter="none")
        .logic()
        .merge(MachineLogic(services={"work": work})),
    )
    store = DeadLetterStore()
    clk = SimulatedClock()
    i = SyncInterpreter(m, clock=clk).use(DeadLetterPlugin(store)).start()
    for _ in range(6):
        clk.increment(100_000)
    assert i.matches("job.deadLettered") and calls["n"] == 3
    dl = store.all()[0]
    print(
        "attempts:", dl.attempts, "errors:", [e["message"] for e in dl.errors]
    )
    print("redacted token:", dl.snapshot["context"]["token"])
    assert dl.attempts == 3 and len(dl.errors) == 3
    assert dl.snapshot["context"]["token"] == "***"
    json.loads(dl.to_json())

    step("circuit breaker: open -> fast fail -> half_open -> closed")
    clk = SimulatedClock()
    cb = CircuitBreaker(failure_threshold=2, cooldown_ms=1000, clock=clk)

    def boom() -> None:
        raise RuntimeError("down")

    for _ in range(2):
        try:
            cb.call(boom)
        except RuntimeError:
            pass
    assert cb.state == "open"
    try:
        cb.call(lambda: "x")
        raise SystemExit("should be open")
    except CircuitOpenError:
        print("fast-fail while open OK")
    clk.increment(1001)
    assert cb.state == "half_open"
    print(cb.call(lambda: "recovered"), cb.state)
    assert cb.state == "closed"

    step("32-thread hammer admits exactly one probe")
    clk = SimulatedClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_ms=1000, clock=clk)
    try:
        cb.call(boom)
    except RuntimeError:
        pass
    clk.increment(1001)
    assert cb.state == "half_open"
    gate = threading.Event()
    admitted, rejected = [], []

    def slow() -> str:
        gate.wait(5)
        return "ok"

    def w(n: int) -> None:
        try:
            cb.call(slow)
            admitted.append(n)
        except CircuitOpenError:
            rejected.append(n)

    ts = [threading.Thread(target=w, args=(n,)) for n in range(32)]
    for t in ts:
        t.start()
    gate.set()
    for t in ts:
        t.join(10)
    print("admitted:", len(admitted), "rejected:", len(rejected))
    assert len(admitted) == 1 and len(rejected) == 31
    assert cb.state == "closed"

    step("async twin")

    async def go() -> str:
        aclk = SimulatedClock()
        acb = CircuitBreaker(failure_threshold=1, cooldown_ms=500, clock=aclk)

        async def aboom() -> None:
            raise RuntimeError("down")

        try:
            await acb.acall(aboom)
        except RuntimeError:
            pass
        assert acb.state == "open"
        await aclk.increment(501)

        async def ok() -> str:
            return "ok"

        assert await acb.acall(ok) == "ok"
        return acb.state

    print("async state:", asyncio.run(go()))

    step("xsm inspect renders CIRCUIT_BREAKER_CONFIG")
    tmp = ROOT / "scripts" / "verify" / "_265_cb.json"
    tmp.write_text(json.dumps(CIRCUIT_BREAKER_CONFIG), encoding="utf-8")
    try:
        out = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "inspect",
                str(tmp),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        data = json.loads(out.stdout)
        print(
            "states:", sorted(data["state_kinds"]), "version:", data["version"]
        )
        assert len(data["state_kinds"]) == 3 and data["version"] == "1"
    finally:
        tmp.unlink(missing_ok=True)

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
