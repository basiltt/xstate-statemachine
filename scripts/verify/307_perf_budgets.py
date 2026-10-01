"""Verify issue #307: import purity, seven-sample budgets and harness rows."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    benchmark = subprocess.run(
        [
            sys.executable,
            str(ROOT / "benchmarks" / "integrations_characteristics.py"),
            "--quick",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    report = json.loads(benchmark.stdout)
    sys.path.insert(0, str(ROOT))
    from benchmarks.integrations_characteristics import (
        MULTIPLIER,
        REPETITIONS,
        ROWS,
    )
    from benchmarks.perf_gate import verdicts

    assert report["quick"] and set(report["results"]) == set(ROWS)
    assert report["results"]["fastapi_router"] is None
    shortest = report["results"]["shortest_paths"]
    assert shortest is not None and shortest["configurations"] > 0
    for row, value in report["results"].items():
        if value is not None:
            assert value["n"] == REPETITIONS and value["p50_us"] > 0, row

    budgets = json.loads(
        (ROOT / "benchmarks" / "budgets.json").read_text(encoding="utf-8")
    )
    assert set(budgets["budgets"]) == set(ROWS)
    assert budgets["multiplier"] == MULTIPLIER
    for row, value in budgets["budgets"].items():
        if value is not None:
            expected = round(value["baseline_p50_us"] * MULTIPLIER, 3)
            assert value["budget_p50_us"] == expected, row

    # 📝 The relative gate must produce a verdict for this (quick, local)
    #    run -- a broken speed factor would raise here.
    gate = verdicts(
        {
            r: (v["p50_us"] if v else None)
            for r, v in report["results"].items()
        },
        budgets["gate"]["reference_us"],
    )
    assert gate["speed_factor"] > 0
    print(
        f"relative gate speed factor on this machine: {gate['speed_factor']}"
    )

    scaling = subprocess.run(
        [sys.executable, str(ROOT / "benchmarks" / "scaling.py"), "--quick"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    print(scaling.stdout)
    assert scaling.returncode == 0, scaling.stdout + scaling.stderr

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_import_surface.py",
            "tests/test_perf_gate.py",
            "tests/test_perf_budgets.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        check=True,
    )
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
