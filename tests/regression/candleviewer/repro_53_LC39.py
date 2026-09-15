"""LC-39 repro: throughput is a fixed GLOBAL budget, not a per-machine one.

Every `Interpreter` shares one asyncio event loop on one OS thread. Event
processing is therefore interleaved, never parallel: the aggregate number of
events per second across N interpreters is roughly constant (and in fact
decays with N due to scheduling overhead), so the per-machine share is the
global budget divided by N.

This measures aggregate throughput at N = 1, 10, 100 and 500 and fails if
aggregate throughput scales with N by even 2x -- i.e. it fails if the
library does what a reader might reasonably assume.

Exit code 1 if aggregate throughput is flat (the documented-gap behaviour).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

EVENTS = 2000
WARMUP = 200
REPEATS = 3
NS = (1, 10, 100, 500)

CFG = {
    "id": "oms",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {"on": {"TICK": {"target": "idle", "actions": ["bump"]}}},
    },
}


def bump(interpreter, context, event, action_def):  # noqa: ANN001
    context["n"] += 1


def machine():
    return create_machine(CFG, logic=MachineLogic(actions={"bump": bump}))


async def aggregate(n: int) -> float:
    interps = [Interpreter(machine()) for _ in range(n)]
    await asyncio.gather(*(i.start() for i in interps))

    async def drive(i, count):
        for _ in range(count):
            await i.send("TICK")

    # 🔥 Warm up: first-touch costs (import-time lazy work, dict/type caches,
    # asyncio task bookkeeping) otherwise land entirely on the N=1 sample and
    # make the baseline look artificially slow, which swings the ratio.
    await asyncio.gather(*(drive(i, WARMUP) for i in interps))

    t0 = time.perf_counter()
    await asyncio.gather(*(drive(i, EVENTS) for i in interps))
    elapsed = time.perf_counter() - t0
    await asyncio.gather(*(i.stop() for i in interps))
    return (n * EVENTS) / elapsed


async def best_of(n: int, repeats: int = REPEATS) -> float:
    """Take the best of several timings: throughput noise is one-sided, so the
    maximum is the closest estimate of the machine's real capacity."""
    return max([await aggregate(n) for _ in range(repeats)])


async def main() -> int:
    results = {}
    for n in NS:
        results[n] = await best_of(n)
        print(
            f"OBSERVED: N={n:<4} aggregate={results[n]:>9,.0f} ev/s   "
            f"per-machine={results[n] / n:>9,.1f} ev/s"
        )
    base = results[NS[0]]
    top = results[NS[-1]]
    print(
        f"OBSERVED: aggregate scaling factor from N={NS[0]} to N={NS[-1]} "
        f"= {top / base:.2f}x (per-machine share fell "
        f"{base / (top / NS[-1]):,.0f}x)"
    )
    print(
        "EXPECTED (naive reading of the docs): aggregate throughput grows "
        "with N, or the docs state plainly that it does not."
    )
    return 0 if top / base > 2.0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
