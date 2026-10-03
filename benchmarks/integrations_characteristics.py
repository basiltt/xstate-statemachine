"""Reproducible integration performance measurements for issue #307.

Each result is the median of seven timed repetitions in microseconds. Send
measurements time 10,000 completed events per repetition; stores and imports
are timed one round-trip at a time. ``--quick`` is for checking the harness,
not for recording a baseline.
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import importlib.util
import json
import logging
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine import __version__ as LIBRARY_VERSION  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    AuditPlugin,
    IdempotencyPlugin,
    MemoryInbox,
    MemoryLog,
    MemoryStore,
    SNAPSHOT_VERSION,
    SQLiteStore,
    apersisted,
    as_async,
    persisted,
)

REPETITIONS = 7
EVENTS = 10_000
SNAPSHOTS = 1_000
# 📝 #307 battle test: was 100. At 100 a whole `persisted_sqlite_*` row
#    lasted ~0.12 s, so one background I/O burst covered all seven samples
#    and the median could not reject it (5 local runs: sync CV 47 %, one
#    run 2.4x high). 500 spreads each row over ~0.6-2 s; a burst now hits
#    a minority of samples and the p50 discards it.
ROUND_TRIPS = 500
MULTIPLIER = 1.25
ROWS = (
    "import_clean",
    "import_with_extras",
    "persisted_memory_sync",
    "persisted_memory_async",
    "persisted_sqlite_sync",
    "persisted_sqlite_async",
    "plugins_sync",
    "plugins_async",
    "hooks_empty_sync",
    "hooks_empty_async",
    "validator_sync",
    "validator_async",
    "snapshot_get_sync",
    "snapshot_restore_sync",
    "snapshot_get_async",
    "snapshot_restore_async",
    "snapshot_restore_migrated_sync",
    "shortest_paths",
    "fastapi_router",
    "timer_scan_sqlite_100k",
)


def _metric(samples: List[float], **details: Any) -> Dict[str, Any]:
    if len(samples) != REPETITIONS:
        raise ValueError(f"expected {REPETITIONS} repetitions")
    return {
        "p50_us": round(statistics.median(samples), 3),
        "n": len(samples),
        **details,
    }


def _cpu_name() -> str:
    # 📝 On Linux `platform.processor()` is just the architecture; the model
    #    name lives in /proc/cpuinfo.
    if Path("/proc/cpuinfo").is_file():
        with open("/proc/cpuinfo", encoding="utf-8") as cpuinfo:
            for line in cpuinfo:
                if line.startswith("model name"):
                    return line.partition(":")[2].strip()
    name = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "")
    return name or "unknown"


def runner_info() -> Dict[str, Any]:
    return {
        "label": os.environ.get("XSM_PERF_RUNNER", "local"),
        "os": platform.system(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": _cpu_name(),
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
        "library_version": LIBRARY_VERSION,
    }


def _import_once(with_extras: bool) -> float:
    code = "import sys, time\n"
    if not with_extras:
        # 📝 Keep interpreter startup identical; hide installed extras only.
        code += (
            "sys.path[:] = [p for p in sys.path if 'site-packages' "
            "not in p.lower() and 'dist-packages' not in p.lower()]\n"
        )
    code += (
        f"sys.path.insert(0, {str(SRC)!r})\n"
        "start = time.perf_counter_ns()\n"
        "import xstate_statemachine\n"
        "print(time.perf_counter_ns() - start)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return int(proc.stdout.strip().splitlines()[-1]) / 1000


def benchmark_import_clean() -> Dict[str, Any]:
    """Import core with site-packages disabled, excluding process startup."""
    return _metric([_import_once(False) for _ in range(REPETITIONS)])


def benchmark_import_with_extras() -> Optional[Dict[str, Any]]:
    """Import core with both shipped extras installed but never imported."""
    if any(
        importlib.util.find_spec(extra) is None
        for extra in ("redis", "pydantic")
    ):
        return None
    return _metric([_import_once(True) for _ in range(REPETITIONS)])


def _machine(fields: int = 1, validator: Any = None) -> Any:
    def bump(
        interp: Any, context: Dict[str, int], event: Any, action: Any
    ) -> None:
        context["f0"] += 1

    config = {
        "id": "perf",
        "initial": "a",
        "context": {f"f{index}": 0 for index in range(fields)},
        "states": {
            "a": {"on": {"T": {"target": "b", "actions": "bump"}}},
            "b": {"on": {"T": {"target": "a", "actions": "bump"}}},
        },
    }
    return create_machine(
        config,
        logic=MachineLogic(actions={"bump": bump}),
        context_validator=validator,
    )


def _prometheus() -> Any:
    """A real `PrometheusPlugin` on a private registry, or ``None`` when
    `[observability]` is not installed (#273)."""
    if importlib.util.find_spec("prometheus_client") is None:
        return None
    from prometheus_client import CollectorRegistry

    from xstate_statemachine.contrib.observability import PrometheusPlugin

    return PrometheusPlugin(registry=CollectorRegistry())


def _plugins() -> Any:
    log = MemoryLog()
    attached: List[Any] = [
        IdempotencyPlugin(MemoryInbox(), principal=lambda event: "p"),
        AuditPlugin(log),
    ]
    prom = _prometheus()
    if prom is not None:
        attached.append(prom)
    return tuple(attached), log


def _send_sync(
    events: int,
    *,
    fields: int = 1,
    validator: Any = None,
    plugins: bool = False,
    keyed: bool = False,
) -> Dict[str, Any]:
    machine = _machine(fields, validator)
    samples = []
    for repetition in range(REPETITIONS):
        interp = SyncInterpreter(machine)
        attached, log = _plugins() if plugins else ((), None)
        for plugin in attached:
            interp.use(plugin)
        interp.start()
        try:
            if keyed:
                interp.send("T", wait=True, idempotency_key="warm")
            else:
                interp.send("T", wait=True)
            start = time.perf_counter_ns()
            for index in range(events):
                if keyed:
                    interp.send(
                        "T",
                        wait=True,
                        idempotency_key=f"{repetition}-{index}",
                    )
                else:
                    interp.send("T", wait=True)
            samples.append((time.perf_counter_ns() - start) / (1000 * events))
            if interp.context["f0"] != events + 1:
                raise RuntimeError("sync benchmark did not process all events")
            if log is not None and len(log) != events + 1:
                raise RuntimeError("sync audit log missed an event")
        finally:
            interp.stop()
    return _metric(samples, events_per_rep=events)


def _send_async(
    events: int,
    *,
    fields: int = 1,
    validator: Any = None,
    plugins: bool = False,
    keyed: bool = False,
) -> Dict[str, Any]:
    machine = _machine(fields, validator)

    async def collect() -> List[float]:
        samples = []
        for repetition in range(REPETITIONS):
            interp = Interpreter(machine)
            attached, log = _plugins() if plugins else ((), None)
            for plugin in attached:
                interp.use(plugin)
            await interp.start()
            try:
                if keyed:
                    await interp.send("T", wait=True, idempotency_key="warm")
                else:
                    await interp.send("T", wait=True)
                start = time.perf_counter_ns()
                for index in range(events):
                    if keyed:
                        await interp.send(
                            "T",
                            wait=True,
                            idempotency_key=f"{repetition}-{index}",
                        )
                    else:
                        await interp.send("T", wait=True)
                samples.append(
                    (time.perf_counter_ns() - start) / (1000 * events)
                )
                if interp.context["f0"] != events + 1:
                    raise RuntimeError(
                        "async benchmark did not process all events"
                    )
                if log is not None and len(log) != events + 1:
                    raise RuntimeError("async audit log missed an event")
            finally:
                await interp.stop()
        return samples

    return _metric(asyncio.run(collect()), events_per_rep=events)


def _persisted_sync(store: Any) -> Dict[str, Any]:
    machine = _machine()
    with persisted(store, "sample", machine):
        pass
    samples = []
    for index in range(REPETITIONS):
        start = time.perf_counter_ns()
        for _ in range(ROUND_TRIPS):
            with persisted(store, "sample", machine) as interp:
                interp.send("T")
        samples.append((time.perf_counter_ns() - start) / (1000 * ROUND_TRIPS))
        if interp.context["f0"] != (index + 1) * ROUND_TRIPS:
            raise RuntimeError("sync persisted round-trip lost an event")
    return _metric(samples, round_trips_per_rep=ROUND_TRIPS)


def _persisted_async(store: Any) -> Dict[str, Any]:
    machine = _machine()
    adapter = as_async(store)

    async def collect() -> List[float]:
        try:
            async with apersisted(adapter, "sample", machine):
                pass
            samples = []
            for index in range(REPETITIONS):
                start = time.perf_counter_ns()
                for _ in range(ROUND_TRIPS):
                    async with apersisted(
                        adapter, "sample", machine
                    ) as interp:
                        await interp.send("T", wait=True)
                samples.append(
                    (time.perf_counter_ns() - start) / (1000 * ROUND_TRIPS)
                )
                if interp.context["f0"] != (index + 1) * ROUND_TRIPS:
                    raise RuntimeError(
                        "async persisted round-trip lost an event"
                    )
            return samples
        finally:
            if isinstance(store, SQLiteStore):
                # 🧹 SQLite's connection belongs to the adapter's worker.
                await adapter._run(store.close)

    try:
        return _metric(asyncio.run(collect()), round_trips_per_rep=ROUND_TRIPS)
    finally:
        adapter.close()


def benchmark_persisted_memory_sync() -> Dict[str, Any]:
    return _persisted_sync(MemoryStore())


TIMER_KEYS = 100_000
TIMER_DUE = 100


def benchmark_timer_scan_sqlite_100k() -> Dict[str, Any]:
    """`DueTimerScanner.due_keys` + ONE fire over 100 000 SQLite records
    of which 100 are due (#264 battle).

    📝 Before the indexed `SQLiteStore.due_keys` the scanner loaded every
    record per tick. Each repetition fires a DIFFERENT one of the 100 due
    keys (``limit=1``), so all seven measure a 93-100-due index.
    """
    from xstate_statemachine import SimulatedClock, SyncInterpreter
    from xstate_statemachine.persistence import DueTimerScanner

    machine = create_machine(
        {
            "id": "t",
            "initial": "w",
            "states": {"w": {"after": {"1000": "d"}}, "d": {}},
        }
    )
    with tempfile.TemporaryDirectory() as directory:
        store = SQLiteStore(Path(directory) / "timers.sqlite")
        try:
            interp = SyncInterpreter(
                machine, clock=SimulatedClock(wall_start=0)
            ).start()
            blob, (dl,) = interp.get_snapshot(), interp.pending_deadlines()
            interp.stop()
            late = type(dl)(dl.state_id, 1, 1e12, dl.delay_ms, dl.event_type)
            conn = store._conn()
            conn.execute("BEGIN")
            for i in range(TIMER_KEYS):
                store.save(
                    f"t{i:06d}",
                    blob,
                    deadlines=(dl if i < TIMER_DUE else late,),
                )
            conn.execute("COMMIT")
            scanner = DueTimerScanner(store, lambda k: machine, limit=1)
            samples = []
            for _ in range(REPETITIONS):
                start = time.perf_counter_ns()
                due = scanner.due_keys(10.0)
                woken = scanner.run_once(now=10.0)
                samples.append((time.perf_counter_ns() - start) / 1000)
                if len(due) != 1 or woken != 1:
                    raise RuntimeError("timer scan did not fire one key")
            return _metric(samples, keys=TIMER_KEYS, due=TIMER_DUE)
        finally:
            store.close()


def benchmark_persisted_memory_async() -> Dict[str, Any]:
    return _persisted_async(MemoryStore())


def benchmark_persisted_sqlite_sync() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        store = SQLiteStore(Path(directory) / "perf.sqlite")
        try:
            return _persisted_sync(store)
        finally:
            store.close()


def benchmark_persisted_sqlite_async() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        store = SQLiteStore(Path(directory) / "perf.sqlite")
        try:
            return _persisted_async(store)
        finally:
            store.close()


def benchmark_plugins_sync(events: int) -> Dict[str, Any]:
    bare = _send_sync(events, keyed=True)
    measured = _send_sync(events, keyed=True, plugins=True)
    measured["bare_p50_us"] = bare["p50_us"]
    measured["overhead_pct"] = round(
        100 * (measured["p50_us"] / bare["p50_us"] - 1), 1
    )
    return measured


def benchmark_plugins_async(events: int) -> Dict[str, Any]:
    bare = _send_async(events, keyed=True)
    measured = _send_async(events, keyed=True, plugins=True)
    measured["bare_p50_us"] = bare["p50_us"]
    measured["overhead_pct"] = round(
        100 * (measured["p50_us"] / bare["p50_us"] - 1), 1
    )
    return measured


def benchmark_hooks_empty_sync(events: int) -> Dict[str, Any]:
    """The current no-plugin send path, including both hook seams."""
    return _send_sync(events)


def benchmark_hooks_empty_async(events: int) -> Dict[str, Any]:
    return _send_async(events)


def _validator() -> Callable[[Dict[str, int]], None]:
    from pydantic import create_model

    from xstate_statemachine.contrib.pydantic import context_model

    model = create_model(
        "PerformanceContext",
        **{f"f{index}": (int, ...) for index in range(20)},
    )
    return context_model(model)


def benchmark_validator_sync(events: int) -> Dict[str, Any]:
    bare = _send_sync(events, fields=20)
    measured = _send_sync(events, fields=20, validator=_validator())
    measured["bare_p50_us"] = bare["p50_us"]
    measured["over_bare_us"] = round(measured["p50_us"] - bare["p50_us"], 3)
    return measured


def benchmark_validator_async(events: int) -> Dict[str, Any]:
    bare = _send_async(events, fields=20)
    measured = _send_async(events, fields=20, validator=_validator())
    measured["bare_p50_us"] = bare["p50_us"]
    measured["over_bare_us"] = round(measured["p50_us"] - bare["p50_us"], 3)
    return measured


def _fifty_states() -> Any:
    return create_machine(
        {
            "id": "fifty",
            "initial": "s0",
            "states": {
                f"s{index}": {"on": {"T": f"s{(index + 1) % 50}"}}
                for index in range(50)
            },
        }
    )


def _snapshot_sync(kind: str, count: int) -> Dict[str, Any]:
    machine = _fifty_states()
    interp = SyncInterpreter(machine).start()
    try:
        snapshot = interp.get_snapshot()
        if json.loads(snapshot)["version"] != SNAPSHOT_VERSION:
            raise RuntimeError("snapshot benchmark is not using layout v4")
        samples = []
        for _ in range(REPETITIONS):
            start = time.perf_counter_ns()
            for _ in range(count):
                if kind == "get":
                    interp.get_snapshot()
                else:
                    SyncInterpreter.from_snapshot(snapshot, machine)
            samples.append((time.perf_counter_ns() - start) / (1000 * count))
        return _metric(samples, operations_per_rep=count)
    finally:
        interp.stop()


def _snapshot_async(kind: str, count: int) -> Dict[str, Any]:
    machine = _fifty_states()

    async def collect() -> List[float]:
        interp = await Interpreter(machine).start()
        try:
            snapshot = interp.get_snapshot()
            if json.loads(snapshot)["version"] != SNAPSHOT_VERSION:
                raise RuntimeError("snapshot benchmark is not using layout v4")
            samples = []
            for _ in range(REPETITIONS):
                start = time.perf_counter_ns()
                for _ in range(count):
                    if kind == "get":
                        interp.get_snapshot()
                    else:
                        Interpreter.from_snapshot(snapshot, machine)
                samples.append(
                    (time.perf_counter_ns() - start) / (1000 * count)
                )
            return samples
        finally:
            await interp.stop()

    return _metric(asyncio.run(collect()), operations_per_rep=count)


def benchmark_snapshot_get_sync(count: int) -> Dict[str, Any]:
    return _snapshot_sync("get", count)


def benchmark_snapshot_restore_sync(count: int) -> Dict[str, Any]:
    return _snapshot_sync("restore", count)


def _fifty_states_v(version: str) -> Any:
    return create_machine(
        {
            "id": "fifty",
            "version": version,
            "initial": "s0",
            "states": {
                f"s{index}": {"on": {"T": f"s{(index + 1) % 50}"}}
                for index in range(50)
            },
        }
    )


def benchmark_snapshot_restore_migrated_sync(count: int) -> Dict[str, Any]:
    """#263 battle: restore a 50-state blob through a 1-hop migration.

    Compare with `snapshot_restore_sync`; the extra is one deep copy of
    the decoded blob plus the (trivial) step.
    """
    from xstate_statemachine.persistence import SnapshotMigrator

    old, new = _fifty_states_v("1.0"), _fifty_states_v("2.0")
    interp = SyncInterpreter(old).start()
    try:
        snapshot = interp.get_snapshot()
    finally:
        interp.stop()
    migrator = SnapshotMigrator()
    migrator.add("1.0", "2.0", lambda blob: blob)
    samples = []
    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        for _ in range(count):
            SyncInterpreter.from_snapshot(snapshot, new, migrator=migrator)
        samples.append((time.perf_counter_ns() - start) / (1000 * count))
    return _metric(samples, operations_per_rep=count)


def benchmark_snapshot_get_async(count: int) -> Dict[str, Any]:
    return _snapshot_async("get", count)


def benchmark_snapshot_restore_async(count: int) -> Dict[str, Any]:
    return _snapshot_async("restore", count)


SHORTEST_PATHS_CHART = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "savage.json"
)


def benchmark_shortest_paths() -> Optional[Dict[str, Any]]:
    """Full `shortest_paths` exploration of one corpus chart (#269).

    📝 `savage.json` is the largest Stately chart that both loads (the
    larger `AtmScenario.json` is rejected by the build-time validator)
    and explores in milliseconds. `addressFields.json` -- 8 parallel
    regions, 3,456 configurations, ~54 s -- is a combinatorial-explosion
    case reported by `benchmarks/scaling.py`, not a budget row.
    """
    if not SHORTEST_PATHS_CHART.is_file():
        return None
    from xstate_statemachine import shortest_paths
    from xstate_statemachine.testing_utils import stub_logic

    config = json.loads(SHORTEST_PATHS_CHART.read_text(encoding="utf-8"))
    machine = create_machine(config, logic=stub_logic(config))
    configurations = len(shortest_paths(machine))
    samples = []
    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        shortest_paths(machine)
        samples.append((time.perf_counter_ns() - start) / 1000)
    return _metric(
        samples, chart=SHORTEST_PATHS_CHART.name, configurations=configurations
    )


def benchmark_fastapi_router() -> None:
    """Reserved for the later phase that ships the FastAPI router."""
    return None


PLUGINS_NOTE = "IdempotencyPlugin + AuditPlugin + PrometheusPlugin (#273)"
NO_PROMETHEUS_NOTE = (
    "IdempotencyPlugin + AuditPlugin; install [observability] to include "
    "PrometheusPlugin"
)


def _clean(benchmark: Callable[..., Any], *args: Any) -> Any:
    """Run one row from a collected heap, GC still off while it times.

    🏛️ #307 battle test: `run()` disables the cyclic GC for the whole run
    so a collection never lands inside a timed loop -- but that also let
    every earlier row's cycles (interpreters, event loops, SQLite
    connections) pile up uncollected. Five local runs showed the four
    allocation-heavy `persisted_*` rows at 11-25 % CV with one run 25-60 %
    high on all four at once, while within-run samples stayed within 8 %:
    a heap-state effect, not timer noise. Collecting *between* rows keeps
    the timed sections GC-free and gives every row the same starting heap.
    """
    gc.collect()
    return benchmark(*args)


def run(quick: bool = False) -> Dict[str, Any]:
    events = 1_000 if quick else EVENTS
    snapshots = 100 if quick else SNAPSHOTS
    results: Dict[str, Any] = {}
    plugins_note = PLUGINS_NOTE if _prometheus() else NO_PROMETHEUS_NOTE
    notes = {
        "plugins_sync": plugins_note,
        "plugins_async": plugins_note,
        "hooks_empty_sync": "no-plugin send path; no historical 0.10.x runtime in this run",
        "hooks_empty_async": "no-plugin send path; no historical 0.10.x runtime in this run",
        "snapshot_get_sync": "v4; historical v3 runtime not present",
        "snapshot_restore_sync": "v4; historical v3 runtime not present",
        "snapshot_get_async": "v4; historical v3 runtime not present",
        "snapshot_restore_async": "v4; historical v3 runtime not present",
        "snapshot_restore_migrated_sync": "#263 battle: 1-hop SnapshotMigrator; no budget until the reference runner records one",
        "shortest_paths": "savage.json (largest loadable corpus chart); no budget until a nightly records one",
        "fastapi_router": "FastAPI router is not shipped yet",
    }
    logger = logging.getLogger("xstate_statemachine")
    previous_level = logger.level
    logger.setLevel(logging.CRITICAL)
    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        results["import_clean"] = _clean(benchmark_import_clean)
        results["import_with_extras"] = _clean(benchmark_import_with_extras)
        if results["import_with_extras"] is None:
            notes["import_with_extras"] = "install [redis,pydantic] to measure"
        results["hooks_empty_sync"] = _clean(
            benchmark_hooks_empty_sync, events
        )
        results["hooks_empty_async"] = _clean(
            benchmark_hooks_empty_async, events
        )
        for name, benchmark in (
            ("persisted_memory_sync", benchmark_persisted_memory_sync),
            ("persisted_memory_async", benchmark_persisted_memory_async),
            ("persisted_sqlite_sync", benchmark_persisted_sqlite_sync),
            ("persisted_sqlite_async", benchmark_persisted_sqlite_async),
        ):
            results[name] = _clean(benchmark)
            engine = "async" if name.endswith("_async") else "sync"
            bare = results[f"hooks_empty_{engine}"]["p50_us"]
            results[name]["over_bare_us"] = round(
                results[name]["p50_us"] - bare, 3
            )
        results["plugins_sync"] = _clean(benchmark_plugins_sync, events)
        results["plugins_async"] = _clean(benchmark_plugins_async, events)
        if importlib.util.find_spec("pydantic") is None:
            results["validator_sync"] = None
            results["validator_async"] = None
            notes["validator_sync"] = "install [pydantic] to measure"
            notes["validator_async"] = "install [pydantic] to measure"
        else:
            results["validator_sync"] = _clean(
                benchmark_validator_sync, events
            )
            results["validator_async"] = _clean(
                benchmark_validator_async, events
            )
        for name, snap in (
            ("snapshot_get_sync", benchmark_snapshot_get_sync),
            ("snapshot_restore_sync", benchmark_snapshot_restore_sync),
            ("snapshot_get_async", benchmark_snapshot_get_async),
            ("snapshot_restore_async", benchmark_snapshot_restore_async),
            (
                "snapshot_restore_migrated_sync",
                benchmark_snapshot_restore_migrated_sync,
            ),
        ):
            results[name] = _clean(snap, snapshots)
        results["shortest_paths"] = _clean(benchmark_shortest_paths)
        results["timer_scan_sqlite_100k"] = _clean(
            benchmark_timer_scan_sqlite_100k
        )
        results["fastapi_router"] = benchmark_fastapi_router()
    finally:
        logger.setLevel(previous_level)
        if was_enabled:
            gc.enable()
    if set(results) != set(ROWS):
        raise RuntimeError("benchmark rows are incomplete")
    return {
        "runner": runner_info(),
        "quick": quick,
        "results": {row: results[row] for row in ROWS},
        "notes": notes,
    }


def measure_row(row: str, quick: bool = False) -> Dict[str, Any]:
    """One row, exactly as `run()` measures it (same args, GC off, clean heap).

    🎯 Used by the gate to CONFIRM a failing row before going red: a
    genuine regression reproduces on a second reading, an I/O burst on a
    shared runner does not. Single-row only; the `over_bare_us` /
    `overhead_pct` cross-row fields are not recomputed.
    """
    events = 1_000 if quick else EVENTS
    snapshots = 100 if quick else SNAPSHOTS
    dispatch: Dict[str, Tuple[Callable[..., Any], Tuple[Any, ...]]] = {
        "import_clean": (benchmark_import_clean, ()),
        "import_with_extras": (benchmark_import_with_extras, ()),
        "hooks_empty_sync": (benchmark_hooks_empty_sync, (events,)),
        "hooks_empty_async": (benchmark_hooks_empty_async, (events,)),
        "persisted_memory_sync": (benchmark_persisted_memory_sync, ()),
        "persisted_memory_async": (benchmark_persisted_memory_async, ()),
        "persisted_sqlite_sync": (benchmark_persisted_sqlite_sync, ()),
        "persisted_sqlite_async": (benchmark_persisted_sqlite_async, ()),
        "plugins_sync": (benchmark_plugins_sync, (events,)),
        "plugins_async": (benchmark_plugins_async, (events,)),
        "validator_sync": (benchmark_validator_sync, (events,)),
        "validator_async": (benchmark_validator_async, (events,)),
        "snapshot_get_sync": (benchmark_snapshot_get_sync, (snapshots,)),
        "snapshot_restore_sync": (
            benchmark_snapshot_restore_sync,
            (snapshots,),
        ),
        "snapshot_get_async": (benchmark_snapshot_get_async, (snapshots,)),
        "snapshot_restore_async": (
            benchmark_snapshot_restore_async,
            (snapshots,),
        ),
        "snapshot_restore_migrated_sync": (
            benchmark_snapshot_restore_migrated_sync,
            (snapshots,),
        ),
        "shortest_paths": (benchmark_shortest_paths, ()),
        "timer_scan_sqlite_100k": (benchmark_timer_scan_sqlite_100k, ()),
    }
    if row not in dispatch:
        raise KeyError(f"{row!r} is not a re-measurable row")
    fn, args = dispatch[row]
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        result = _clean(fn, *args)
    finally:
        if was_enabled:
            gc.enable()
    if result is None:
        raise RuntimeError(f"{row}: not measurable in this environment")
    return result


def record_baseline(report: Dict[str, Any]) -> Dict[str, Any]:
    if report.get("quick") or set(report.get("results", {})) != set(ROWS):
        raise ValueError("only a complete, non-quick run can set a baseline")
    budgets = {}
    for row in ROWS:
        result = report["results"][row]
        if result is None:
            budgets[row] = None
        else:
            if result["n"] != REPETITIONS or result["p50_us"] <= 0:
                raise ValueError(f"{row}: invalid baseline measurement")
            budgets[row] = {
                "baseline_p50_us": result["p50_us"],
                "budget_p50_us": round(result["p50_us"] * MULTIPLIER, 3),
            }
    return {
        "runner": report["runner"],
        "multiplier": MULTIPLIER,
        "budgets": budgets,
        "notes": report.get("notes", {}),
    }


def _write_json(path: str, data: Dict[str, Any]) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-file", metavar="PATH")
    parser.add_argument("--record-baseline", metavar="PATH")
    parser.add_argument("--from-json", metavar="PATH")
    args = parser.parse_args(argv)
    if args.quick and args.record_baseline:
        parser.error("--quick cannot be used to record a baseline")
    if args.from_json and not args.record_baseline:
        parser.error("--from-json requires --record-baseline")
    if args.from_json:
        report = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        report = run(args.quick)
    if args.record_baseline:
        _write_json(args.record_baseline, record_baseline(report))
    if args.json_file:
        _write_json(args.json_file, report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        runner = report["runner"]
        print(
            f"Python {runner['python_version']} / {runner['os']} / "
            f"{runner['cpu']} ({runner['label']})"
        )
        print(f"{'Measurement':<28} {'p50 (us)':>12} {'n':>4}")
        for row, value in report["results"].items():
            if value is None:
                print(f"{row:<28} {'not shipped / unavailable':>22}")
            else:
                print(f"{row:<28} {value['p50_us']:>12.3f} {value['n']:>4}")
        print("Timings are for this runner; review any baseline change.")


if __name__ == "__main__":
    main()
