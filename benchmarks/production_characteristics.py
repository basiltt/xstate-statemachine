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
# 🤖 #246: the same run can emit ONE JSON object (``--json`` to stdout,
# ``--json-file PATH`` to a file) carrying the host description and every
# measured number, so a CI job can assert a gate (``lateness_ms < 100``)
# on its own target hardware instead of scraping the human table. The
# host block is what the guide's "Measured on" line is pasted from.
#
# Usage:  python benchmarks/production_characteristics.py [--quick]
#             [--json | --json-file PATH]
# -----------------------------------------------------------------------------
"""Measure throughput scaling and `after` timer error under load."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import statistics
import sys
import time
from typing import Any, Dict, List, Optional

from xstate_statemachine import Interpreter, MachineLogic, create_machine
from xstate_statemachine import __version__ as LIBRARY_VERSION

logging.disable(logging.CRITICAL)

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


async def section_throughput(quick: bool, out: bool) -> List[Dict[str, float]]:
    """Best-of-3 aggregate throughput at N = 1, 10, 100, 1000."""
    rows: List[Dict[str, float]] = []
    if out:
        print(
            "\n§1 Throughput (aggregate ev/s across N concurrent interpreters)"
        )
        print(f"{'N':>6} {'aggregate ev/s':>16} {'per-interpreter ev/s':>22}")
    for n in (1, 10, 100, 1000):
        events = max(20, (2000 if quick else 20000) // n)
        best = max([await aggregate_throughput(n, events) for _ in range(3)])
        rows.append(
            {"n": n, "aggregate_ev_s": best, "per_interpreter_ev_s": best / n}
        )
        if out:
            print(f"{n:>6} {best:>16,.0f} {best / n:>22,.1f}")
    return rows


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


async def timer_error_ms(busy: int, quick: bool) -> float:
    """Median lateness (ms) of a 10 ms `after` while *busy* machines churn."""
    stamps: List[float] = []

    def stamp(
        interp: Any, ctx: Dict[str, Any], event: Any, action: Any
    ) -> None:
        stamps.append(time.perf_counter())

    workers = [await Interpreter(machine()).start() for _ in range(busy)]
    stop = asyncio.Event()

    async def churn(i: Any) -> None:
        while not stop.is_set():
            await i.send("T")
            await asyncio.sleep(0)

    churners = [asyncio.create_task(churn(w)) for w in workers]
    samples: List[float] = []
    for _ in range(5 if quick else 15):
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


async def section_timers(quick: bool, out: bool) -> List[Dict[str, float]]:
    """Median `after: 10` lateness with 0, 10, 100, 500 busy machines."""
    rows: List[Dict[str, float]] = []
    if out:
        print(
            "\n§2 `after: 10` lateness (median ms beyond the 10 ms deadline)"
        )
        print(f"{'busy machines':>14} {'lateness ms':>12}")
    for busy in (0, 10, 100, 500):
        late = await timer_error_ms(busy, quick)
        rows.append({"busy_machines": busy, "lateness_ms": late})
        if out:
            print(f"{busy:>14} {late:>+12.1f}")
    return rows


# -----------------------------------------------------------------------------
def host_info() -> Dict[str, Any]:
    """The host description the guide's "Measured on" line is pasted from."""
    return {
        "library_version": LIBRARY_VERSION,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
        "method": (
            "trivial single-action macrostep, tracemalloc OFF, "
            "throughput best-of-3, lateness median"
        ),
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure throughput scaling and `after` timer error."
    )
    parser.add_argument(
        "--quick", action="store_true", help="fewer events / samples"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit one JSON object to stdout instead of the tables (#246)",
    )
    parser.add_argument(
        "--json-file",
        metavar="PATH",
        help="write the JSON object to PATH (tables still print)",
    )
    return parser.parse_args(argv)


async def run(quick: bool, out: bool) -> Dict[str, Any]:
    """Run both sections; return the machine-readable result."""
    host = host_info()
    if out:
        print(f"Python {host['python_version']} on {host['platform']}")
        print(f"Processor: {host['processor']}")
        print(f"Method: {host['method']}")
    result: Dict[str, Any] = {
        "host": host,
        "quick": quick,
        "throughput": await section_throughput(quick, out),
        "timer_lateness_ms": await section_timers(quick, out),
    }
    if out:
        print(
            "\nThese are order-of-magnitude figures for THIS host; "
            "your macrostep cost sets your budget."
        )
    return result


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = asyncio.run(run(args.quick, out=not args.json))
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    if args.json_file:
        with open(args.json_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
            fh.write("\n")


if __name__ == "__main__":
    main()
