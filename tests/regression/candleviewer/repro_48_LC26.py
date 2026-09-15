"""LC-26 repro: `after` timers degrade catastrophically under event-loop load.

`after` deadlines are plain `asyncio.sleep` tasks scheduled on the same loop
that drains every interpreter's event queue. They therefore inherit the
loop's scheduling latency: a 10 ms timer measured against N busy
interpreters fires hundreds of milliseconds late, and the absolute error is
roughly independent of the nominal delay -- the signature of event-loop
starvation rather than of clock granularity.

Exit code 1 if the loaded-case error exceeds the tolerance.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

DELAYS_MS = (10, 100)
LOAD = 100
SAMPLES = 15
TOLERANCE_MS = 50.0


def timer_machine(delay_ms: int):
    cfg = {
        "id": f"t{delay_ms}",
        "initial": "wait",
        "context": {"fired_at": 0.0},
        "states": {
            "wait": {"after": {delay_ms: {"target": "fired"}}},
            "fired": {"entry": ["stamp"], "type": "final"},
        },
    }

    def stamp(i, c, e, a):  # noqa: ANN001
        c["fired_at"] = time.perf_counter()

    return create_machine(cfg, logic=MachineLogic(actions={"stamp": stamp}))


BUSY_CFG = {
    "id": "b",
    "initial": "s",
    "context": {"n": 0},
    "states": {"s": {"on": {"P": {"actions": ["bump"]}}}},
}


def bump(i, c, e, a):  # noqa: ANN001
    c["n"] += 1


async def measure(delay_ms: int) -> float:
    errs = []
    for _ in range(SAMPLES):
        interp = Interpreter(timer_machine(delay_ms))
        t0 = time.perf_counter()
        await interp.start()
        deadline = t0 + delay_ms / 1000.0 + 10.0
        while interp.context["fired_at"] == 0.0:
            if time.perf_counter() > deadline:
                break
            await asyncio.sleep(0.0005)
        fired = interp.context["fired_at"]
        await interp.stop()
        if fired:
            errs.append(((fired - t0) - delay_ms / 1000.0) * 1000.0)
    return statistics.median(errs) if errs else float("nan")


async def churn(interp, stop: asyncio.Event) -> None:  # noqa: ANN001
    while not stop.is_set():
        for _ in range(20):
            await interp.send("P")
        await asyncio.sleep(0)


async def scenario(load: int) -> dict:
    stop = asyncio.Event()
    busy, tasks = [], []
    for _ in range(load):
        m = create_machine(BUSY_CFG, logic=MachineLogic(actions={"bump": bump}))
        busy.append(await Interpreter(m).start())
    tasks = [asyncio.create_task(churn(b, stop)) for b in busy]
    out = {d: await measure(d) for d in DELAYS_MS}
    stop.set()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    for b in busy:
        await b.stop()
    return out


async def main() -> int:
    idle = await scenario(0)
    loaded = await scenario(LOAD)
    ok = True
    for d in DELAYS_MS:
        print(f"OBSERVED {d:>4} ms timer, idle loop        = {idle[d]:+9.1f} ms error")
        print(f"OBSERVED {d:>4} ms timer, {LOAD} busy actors = {loaded[d]:+9.1f} ms error")
        if loaded[d] > TOLERANCE_MS:
            ok = False
    print(f"EXPECTED every case within +{TOLERANCE_MS:.0f} ms of nominal")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
