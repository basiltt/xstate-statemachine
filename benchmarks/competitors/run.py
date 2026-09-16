"""Cross-library state-machine benchmark harness.

Discovers adapters dynamically under ``adapters/``. Each adapter module
exposes ``LIB_NAME``, ``LIB_VERSION``, ``CAPABILITY_NOTES`` and
``setup_<scenario>()`` factory functions returning a hot ``f(n)`` callable.

Run with: python run.py [--quick] [--scenario S1,S2] [--lib xstate_sync,...]
"""

from __future__ import annotations

import argparse
import gc
import importlib
import json
import pkgutil
import platform
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adapters  # noqa: E402  (must come after sys.path insert)

SCENARIOS: dict[str, int] = {
    "S1": 20_000,
    "S2": 20_000,
    "S3": 20_000,
    "S4": 20_000,
    "S5": 200,
    "S6": 1_000,
    "S7": 200,
    "S8": 20_000,
}

SCENARIO_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

DEFAULT_REPS = 7


@dataclass
class AdapterInfo:
    module_name: str
    lib_name: str
    lib_version: str
    capability_notes: dict[str, str] = field(default_factory=dict)
    module: object = None
    error: Optional[str] = None


def discover_adapters() -> list[AdapterInfo]:
    """Import every module under adapters/ and collect metadata.

    Import errors are tolerated and reported, not raised, so a broken
    adapter under concurrent development doesn't take down the whole run.
    """
    infos: list[AdapterInfo] = []
    for _finder, module_name, is_pkg in pkgutil.iter_modules(
        adapters.__path__
    ):
        if is_pkg or module_name.startswith("__"):
            continue
        full_name = f"adapters.{module_name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as exc:  # noqa: BLE001
            infos.append(
                AdapterInfo(
                    module_name=module_name,
                    lib_name=module_name,
                    lib_version="?",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        lib_name = getattr(mod, "LIB_NAME", module_name)
        lib_version = getattr(mod, "LIB_VERSION", "?")
        notes = getattr(mod, "CAPABILITY_NOTES", {})
        infos.append(
            AdapterInfo(
                module_name=module_name,
                lib_name=lib_name,
                lib_version=lib_version,
                capability_notes=notes,
                module=mod,
            )
        )
    return infos


def get_hot_fn(
    info: AdapterInfo, scenario: str
) -> Optional[Callable[[int], None]]:
    """Call setup_<scenario>() on the adapter module, tolerating absence/None/errors."""
    setup_name = f"setup_{scenario}"
    setup_fn = getattr(info.module, setup_name, None)
    if setup_fn is None:
        return None
    try:
        hot = setup_fn()
    except Exception as exc:  # noqa: BLE001
        info.capability_notes.setdefault(
            scenario, f"setup raised {type(exc).__name__}: {exc}"
        )
        return None
    return hot


def time_hot_fn(hot: Callable[[int], None], n: int, reps: int) -> float:
    """Run hot(n) `reps` times, GC disabled during timing, return median wall time (s)."""
    # Warm up once with a small n to trigger JIT/lazy caches, not counted.
    warm_n = max(1, n // 20)
    hot(warm_n)

    samples: list[float] = []
    for _ in range(reps):
        gc.collect()
        gc.disable()
        try:
            start = time.perf_counter()
            hot(n)
            elapsed = time.perf_counter() - start
        finally:
            gc.enable()
        samples.append(elapsed)
    return statistics.median(samples)


def format_ops_per_s(n: int, median_s: float) -> float:
    if median_s <= 0:
        return float("inf")
    return n / median_s


def collect_env() -> dict:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-library state-machine benchmark harness"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Fast smoke run: R=3, N/10"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Comma-separated scenario ids to run (default: all)",
    )
    parser.add_argument(
        "--lib",
        type=str,
        default=None,
        help="Comma-separated adapter module names to run (default: all discovered)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(HERE / "results.json"),
        help="Path to write results.json",
    )
    args = parser.parse_args()

    reps = 3 if args.quick else DEFAULT_REPS
    scale = 10 if args.quick else 1

    wanted_scenarios = (
        [s.strip() for s in args.scenario.split(",") if s.strip()]
        if args.scenario
        else SCENARIO_ORDER
    )
    for s in wanted_scenarios:
        if s not in SCENARIOS:
            print(
                f"Unknown scenario: {s!r} (known: {', '.join(SCENARIO_ORDER)})",
                file=sys.stderr,
            )
            return 2

    wanted_libs = (
        {lib.strip() for lib in args.lib.split(",") if lib.strip()}
        if args.lib
        else None
    )

    infos = discover_adapters()
    if wanted_libs is not None:
        infos = [
            i
            for i in infos
            if i.module_name in wanted_libs or i.lib_name in wanted_libs
        ]

    for info in infos:
        if info.error:
            print(
                f"[WARN] failed to import adapter {info.module_name!r}: {info.error}",
                file=sys.stderr,
            )

    libs_meta = {i.lib_name: i.lib_version for i in infos if not i.error}

    results: list[dict] = []
    header = f"{'lib':<20} {'scenario':<8} {'n':>8} {'median_s':>12} {'ops_per_s':>14}  note"
    print(header)
    print("-" * len(header))

    for info in infos:
        if info.error or info.module is None:
            continue
        for scenario in wanted_scenarios:
            n = max(1, SCENARIOS[scenario] // scale)
            hot = get_hot_fn(info, scenario)
            note = info.capability_notes.get(scenario, "")
            if hot is None:
                if note == "":
                    note = "not implemented"
                print(
                    f"{info.lib_name:<20} {scenario:<8} {'-':>8} {'-':>12} {'-':>14}  {note}"
                )
                results.append(
                    {
                        "lib": info.lib_name,
                        "scenario": scenario,
                        "n": n,
                        "median_s": None,
                        "ops_per_s": None,
                        "note": note,
                    }
                )
                continue
            try:
                median_s = time_hot_fn(hot, n, reps)
                ops_per_s = format_ops_per_s(n, median_s)
                print(
                    f"{info.lib_name:<20} {scenario:<8} {n:>8} {median_s:>12.6f} {ops_per_s:>14.1f}  {note}"
                )
                results.append(
                    {
                        "lib": info.lib_name,
                        "scenario": scenario,
                        "n": n,
                        "median_s": median_s,
                        "ops_per_s": ops_per_s,
                        "note": note,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                err_note = f"error: {type(exc).__name__}: {exc}"
                print(
                    f"{info.lib_name:<20} {scenario:<8} {n:>8} {'-':>12} {'-':>14}  {err_note}"
                )
                results.append(
                    {
                        "lib": info.lib_name,
                        "scenario": scenario,
                        "n": n,
                        "median_s": None,
                        "ops_per_s": None,
                        "note": err_note,
                    }
                )

    out_payload = {
        **collect_env(),
        "libs": libs_meta,
        "results": results,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
