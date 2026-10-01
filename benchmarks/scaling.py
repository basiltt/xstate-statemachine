"""Big-O sweeps for the runtime (issue #307 battle test, report-only).

Each sweep times one operation at three sizes and asserts only the *shape*
of the curve -- a ratio between the largest and a smaller size -- never an
absolute number, so the result means the same thing on any CPU. Run in the
nightly ``perf`` job; ``scaling.json`` is uploaded next to ``last_run.json``.

    python benchmarks/scaling.py [--quick] [--json-file PATH]

Exit status is 1 when a shape check fails (a super-linear finding).

🏛️ Every measurement is the **minimum** of ``REPETITIONS`` timed batches,
not the median: a sweep compares sizes within one process seconds apart,
so the floor (the cost with no scheduler interference) is the quantity
whose ratio means something. The integration budgets use p50 because they
compare *across* nights, where the typical run is the honest statistic.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from benchmarks.integrations_characteristics import runner_info  # noqa: E402
from xstate_statemachine import (  # noqa: E402
    SyncInterpreter,
    create_machine,
    shortest_paths,
)
from xstate_statemachine.persistence import (  # noqa: E402
    MemoryStore,
    persisted,
)
from xstate_statemachine.testing_utils import stub_logic  # noqa: E402

REPETITIONS = 5
SEND_EVENTS = 2_000
SNAPSHOT_OPS = 200
STORE_OPS = 200
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
# 📝 Charts whose full shortest_paths exploration finishes in well under a
#    second. `addressFields.json` (8 parallel regions, 3,456 configurations)
#    takes ~54 s and is reported separately at a capped depth -- see the
#    "graph exploration" finding on production-characteristics.md.
SHORTEST_PATH_CHARTS = ("savage.json", "hiLoGame.json", "car_sales.json")
EXPLOSIVE_CHART = "addressFields.json"


def _best_us(fn: Callable[[], None], ops: int) -> float:
    """Minimum per-operation cost over ``REPETITIONS`` batches (µs)."""
    fn()  # 📝 warm-up: lazy caches, first-touch allocations
    best = float("inf")
    for _ in range(REPETITIONS):
        gc.collect()
        start = time.perf_counter_ns()
        fn()
        best = min(best, (time.perf_counter_ns() - start) / 1000 / ops)
    return round(best, 3)


# -----------------------------------------------------------------------------
# 🏗️ Machine shapes
# -----------------------------------------------------------------------------
def flat(states: int, keys: int = 1) -> Dict[str, Any]:
    """A ring of *states*; ``T`` toggles between the first two only."""
    body: Dict[str, Any] = {f"s{i}": {} for i in range(states)}
    body["s0"] = {"on": {"T": "s1"}} if states > 1 else {"on": {"T": "s0"}}
    if states > 1:
        body["s1"] = {"on": {"T": "s0"}}
    return {
        "id": "flat",
        "initial": "s0",
        "context": {f"k{i}": i for i in range(keys)},
        "states": body,
    }


def nested(depth: int) -> Dict[str, Any]:
    """Two leaves at the bottom of a *depth*-deep chain; ``T`` toggles."""
    leaf: Dict[str, Any] = {
        "initial": "a",
        "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}},
    }
    for level in range(depth - 1):
        leaf = {"initial": f"n{level}", "states": {f"n{level}": leaf}}
    return {"id": "nested", **leaf}


def parallel(regions: int) -> Dict[str, Any]:
    """*regions* orthogonal toggles; ``T`` is handled by region 0 only."""
    states = {
        f"r{i}": {
            "initial": "a",
            "states": {
                "a": {"on": {"T": "b"}} if i == 0 else {},
                "b": {"on": {"T": "a"}} if i == 0 else {},
            },
        }
        for i in range(regions)
    }
    return {"id": "par", "type": "parallel", "states": states}


# -----------------------------------------------------------------------------
# ⏱️ Operations
# -----------------------------------------------------------------------------
def send_cost(config: Dict[str, Any], events: int) -> float:
    interp = SyncInterpreter(create_machine(config)).start()
    try:
        return _best_us(
            lambda: [interp.send("T") for _ in range(events)] and None,
            events,
        )
    finally:
        interp.stop()


def snapshot_costs(config: Dict[str, Any], ops: int) -> Tuple[float, float]:
    machine = create_machine(config)
    interp = SyncInterpreter(machine).start()
    try:
        blob = interp.get_snapshot()
        get = _best_us(
            lambda: [interp.get_snapshot() for _ in range(ops)] and None, ops
        )
        restore = _best_us(
            lambda: [
                SyncInterpreter.from_snapshot(blob, machine)
                for _ in range(ops)
            ]
            and None,
            ops,
        )
        return get, restore
    finally:
        interp.stop()


def store_cost(instances: int, ops: int) -> float:
    """`persisted()` round-trip on one key of a store holding *instances*."""
    machine = create_machine(flat(2))
    store = MemoryStore()
    for i in range(instances):
        with persisted(store, f"i{i}", machine):
            pass

    def batch() -> None:
        for _ in range(ops):
            with persisted(store, "i0", machine) as interp:
                interp.send("T")

    return _best_us(batch, ops)


def paths_cost(chart: str, max_depth: int = 50) -> Dict[str, Any]:
    cfg = json.loads((CORPUS / chart).read_text(encoding="utf-8"))
    machine = create_machine(cfg, logic=stub_logic(cfg))
    start = time.perf_counter_ns()
    paths = shortest_paths(machine, max_depth=max_depth)
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    return {
        "chart": chart,
        "max_depth": max_depth,
        "configurations": len(paths),
        "ms": round(elapsed_ms, 1),
        "ms_per_configuration": round(elapsed_ms / max(1, len(paths)), 3),
    }


# -----------------------------------------------------------------------------
# 📐 Sweeps and shape checks
# -----------------------------------------------------------------------------
def _sweep(
    name: str,
    sizes: List[int],
    measure: Callable[[int], float],
    low: float,
    high: float,
    expect: str,
    ratio_of: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    points = {str(size): measure(size) for size in sizes}
    big, small = ratio_of or (sizes[-1], sizes[0])
    ratio = round(points[str(big)] / points[str(small)], 3)
    return {
        "name": name,
        "unit": "us/op",
        "points": points,
        "check": f"{big}/{small} ratio in [{low}, {high}] ({expect})",
        "ratio": ratio,
        "ok": low <= ratio <= high,
    }


def run(quick: bool = False) -> Dict[str, Any]:
    events = SEND_EVENTS // 10 if quick else SEND_EVENTS
    snaps = SNAPSHOT_OPS // 10 if quick else SNAPSHOT_OPS
    stores = STORE_OPS // 10 if quick else STORE_OPS
    logger = logging.getLogger("xstate_statemachine")
    previous = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        sweeps = [
            _sweep(
                "send_vs_total_states",
                [1, 50, 500],
                lambda n: send_cost(flat(n), events),
                0.0,
                3.0,
                "flat: send must not scale with total state count",
            ),
            _sweep(
                "send_vs_nesting_depth",
                [1, 5, 20],
                lambda n: send_cost(nested(n), events),
                0.0,
                20.0 * 1.5,
                "at most linear in the depth of the exited/entered chain",
            ),
            _sweep(
                "send_vs_parallel_regions",
                [1, 4, 16],
                lambda n: send_cost(parallel(n), events),
                0.0,
                16.0 * 1.5,
                "at most linear in active regions",
            ),
            _sweep(
                "send_vs_context_keys",
                [1, 100, 10_000],
                lambda n: send_cost(flat(2, keys=n), events),
                0.0,
                3.0,
                "flat: an action-free send must not touch context",
            ),
            _sweep(
                "get_snapshot_vs_context_keys",
                [1, 100, 10_000],
                lambda n: snapshot_costs(flat(2, keys=n), snaps)[0],
                50.0,
                200.0,
                "linear in context keys",
                ratio_of=(10_000, 100),
            ),
            _sweep(
                "from_snapshot_vs_context_keys",
                [1, 100, 10_000],
                lambda n: snapshot_costs(flat(2, keys=n), snaps)[1],
                50.0,
                200.0,
                "linear in context keys",
                ratio_of=(10_000, 100),
            ),
            _sweep(
                "get_snapshot_vs_states",
                [1, 50, 500],
                lambda n: snapshot_costs(flat(n), snaps)[0],
                0.0,
                3.0,
                "flat: snapshot holds the active configuration, not the chart",
            ),
            _sweep(
                "from_snapshot_vs_states",
                [1, 50, 500],
                lambda n: snapshot_costs(flat(n), snaps)[1],
                0.0,
                3.0,
                "flat: restore resolves active ids, not the whole chart",
            ),
            _sweep(
                "persisted_vs_store_instances",
                [1, 100, 10_000],
                lambda n: store_cost(n, stores),
                0.0,
                3.0,
                "flat: MemoryStore is a dict lookup",
            ),
        ]
        paths = [paths_cost(chart) for chart in SHORTEST_PATH_CHARTS]
        depth_curve = [
            paths_cost(EXPLOSIVE_CHART, max_depth=d)
            for d in ((2, 3, 4) if quick else (3, 4, 5, 6))
        ]
    finally:
        logger.setLevel(previous)
    return {
        "runner": runner_info(),
        "quick": quick,
        "sweeps": sweeps,
        "shortest_paths": paths,
        "shortest_paths_depth_curve": depth_curve,
        "ok": all(sweep["ok"] for sweep in sweeps),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--json-file", metavar="PATH")
    args = parser.parse_args(argv)
    report = run(args.quick)
    if args.json_file:
        Path(args.json_file).write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    for sweep in report["sweeps"]:
        points = "  ".join(f"{k}:{v}" for k, v in sweep["points"].items())
        mark = "ok " if sweep["ok"] else "BAD"
        print(f"{mark} {sweep['name']:<32} {points}  ratio {sweep['ratio']}")
    for entry in (
        report["shortest_paths"] + report["shortest_paths_depth_curve"]
    ):
        print(
            f"    shortest_paths {entry['chart']:<20} depth "
            f"{entry['max_depth']:>2} {entry['configurations']:>5} configs "
            f"{entry['ms']:>9} ms ({entry['ms_per_configuration']} ms/config)"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
