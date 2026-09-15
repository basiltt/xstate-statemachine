# benchmarks/production_characteristics.py
# -----------------------------------------------------------------------------
# 📏 Reproducible measurements behind docs/_guide/production-characteristics.md
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision (#53, #56): the guide quotes numbers for the
# throughput budget and `after` timer error. Numbers without the script that
# produced them are folklore; this file IS the method. Run it on your own
# hardware and trust your figures over ours. Deliberately dependency-free
# and short enough to read in one sitting.
#
# Usage:  python benchmarks/production_characteristics.py [--quick]
# -----------------------------------------------------------------------------
"""Measure throughput scaling and `after` timer error under load."""

from __future__ import annotations

import asyncio
import logging
import platform
import statistics
import sys
import time
from typing import Any, Dict, List

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)
QUICK = "--quick" in sys.argv

# A trivial single-action macrostep: the cheapest realistic event.
PING: Dict[str, Any] = {
    "id": "ping",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"T": {"target": "b", "actions": ["bump"]}}},
        "b": {"on": {"T": {"target": "a", "actions": ["bump"]}}},
    },
}


def bump(interp: Any, ctx: Dict[str, Any], event: Any, action: Any) -> None:
    ctx["n"] += 1


def machine() -> Any:
    return create_machine(PING, logic=MachineLogic(actions={"bump": bump}))


# -----------------------------------------------------------------------------
# §1 Throughput is a per-process budget
# -----------------------------------------------------------------------------
async def aggregate_throughput(n_machines: int, events_each: int) -> float:
    """Aggregate events/second across *n_machines* driven concurrently."""
    interps = [await Interpreter(machine()).start() for _ in range(n_machines)]

    async def drive(i: Any) -> None:
        for _ in range(events_each):
            await i.send("T")
        # Wait until the machine has actually processed everything.
        while i.context["n"] < events_each:
            await asyncio.sleep(0)

    t0 = time.perf_counter()
    await asyncio.gather(*(drive(i) for i in interps))
    elapsed = time.perf_counter() - t0
    for i in interps:
        await i.stop()
    return n_machines * events_each / elapsed


async def section_throughput() -> None:
    print("\n§1 Throughput (aggregate ev/s across N concurrent interpreters)")
    print(f"{'N':>6} {'aggregate ev/s':>16} {'per-interpreter ev/s':>22}")
    for n in (1, 10, 100, 1000):
        events = max(20, (2000 if QUICK else 20000) // n)
        best = max(
            [await aggregate_throughput(n, events) for _ in range(3)]
        )
        print(f"{n:>6} {best:>16,.0f} {best / n:>22,.1f}")


# -----------------------------------------------------------------------------
# §2 `after` timers under load
# -----------------------------------------------------------------------------
TIMER: Dict[str, Any] = {
    "id": "timer",
    "initial": "wait",
    "context": {"fired_at": None},
    "states": {
        "wait": {"after": {"10": "fired"}},
        "fired": {"entry": ["stamp"]},
    },
}


async def timer_error_ms(busy: int) -> float:
    """Median lateness (ms) of a 10 ms `after` while *busy* machines churn."""
    stamps: List[float] = []

    def stamp(interp: Any, ctx: Dict[str, Any], event: Any, action: Any) -> None:
        stamps.append(time.perf_counter())

    workers = [await Interpreter(machine()).start() for _ in range(busy)]
    stop = asyncio.Event()

    async def churn(i: Any) -> None:
        while not stop.is_set():
            await i.send("T")
            await asyncio.sleep(0)

    churners = [asyncio.create_task(churn(w)) for w in workers]
    samples: List[float] = []
    for _ in range(5 if QUICK else 15):
        stamps.clear()
        t = Interpreter(
            create_machine(TIMER, logic=MachineLogic(actions={"stamp": stamp}))
        )
        t0 = time.perf_counter()
        await t.start()
        while not stamps:
            await asyncio.sleep(0)
        samples.append((stamps[0] - t0) * 1000 - 10.0)
        await t.stop()
    stop.set()
    for c in churners:
        c.cancel()
    for w in workers:
        await w.stop()
    return statistics.median(samples)


async def section_timers() -> None:
    print("\n§2 `after: 10` lateness (median ms beyond the 10 ms deadline)")
    print(f"{'busy machines':>14} {'lateness ms':>12}")
    for busy in (0, 10, 100, 500):
        print(f"{busy:>14} {await timer_error_ms(busy):>+12.1f}")


# -----------------------------------------------------------------------------
async def main() -> None:
    print(f"Python {platform.python_version()} on {platform.platform()}")
    print(f"Processor: {platform.processor() or 'unknown'}")
    print("Method: trivial single-action macrostep, tracemalloc OFF, best-of-3")
    await section_throughput()
    await section_timers()
    print(
        "\nThese are order-of-magnitude figures for THIS host; "
        "your macrostep cost sets your budget."
    )


if __name__ == "__main__":
    asyncio.run(main())
