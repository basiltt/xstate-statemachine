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

    assert report["quick"] and set(report["results"]) == set(ROWS)
    assert report["results"]["shortest_paths"] is None
    assert report["results"]["fastapi_router"] is None
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

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_import_surface.py",
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
