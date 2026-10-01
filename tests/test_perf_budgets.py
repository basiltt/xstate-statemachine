"""Opt-in performance budgets for issue #307.

Two layers, both driven by ``benchmarks/budgets.json``:

* **The gate** (`test_relative_budget`) -- hardware-independent. Every row
  is compared against ``gate.reference_us`` scaled by this run's own speed
  factor (``benchmarks/perf_gate.py``), so it asserts on *every* nightly
  whatever CPU GitHub allocates. A row fails when it is more than
  ``gate.tolerance`` x its hardware-adjusted reference.
* **The report** (`test_absolute_budget_report`) -- the original absolute
  microsecond budgets, which only mean something on the CPU they were
  recorded on. On any other CPU they are a per-row skip naming both CPUs.

🏛️ #307 battle test: the absolute budgets used to *be* the gate. Three
consecutive nightlies landed on three CPU models and two of them skipped
all 18 rows, so the gate was enforced one night in three. See the design
note at the top of ``benchmarks/perf_gate.py`` for the rejected options.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

if os.environ.get("XSM_PERF") != "1":
    pytest.skip("set XSM_PERF=1 to run timing tests", allow_module_level=True)

from benchmarks.integrations_characteristics import (  # noqa: E402
    MULTIPLIER,
    REPETITIONS,
    ROWS,
    run,
)
from benchmarks.perf_gate import (  # noqa: E402
    IMPORT_SPEED_EXPONENT,
    RELATIVE_TOLERANCE,
    failure_message,
    verdicts,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"


@pytest.fixture(scope="module")
def budgets() -> Dict[str, Any]:
    return json.loads(
        (BENCHMARKS / "budgets.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def measured(budgets: Dict[str, Any]) -> Dict[str, Any]:
    result = run()
    p50 = _p50s(result)
    result["gate"] = verdicts(p50, budgets["gate"]["reference_us"])
    (BENCHMARKS / "last_run.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def _p50s(report: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        row: (value["p50_us"] if value else None)
        for row, value in report["results"].items()
    }


def _minor(version: str) -> str:
    return ".".join(version.split(".")[:2])


def _require_extras(row: str) -> None:
    """Skip a row whose measurement needs an extra that is not installed."""
    if row == "import_with_extras":
        pytest.importorskip("redis")
        pytest.importorskip("pydantic")
    if row.startswith("validator_"):
        pytest.importorskip("pydantic")


def test_budget_file_and_run_are_complete(
    budgets: Dict[str, Any], measured: Dict[str, Any]
) -> None:
    assert set(budgets["budgets"]) == set(ROWS)
    assert set(measured["results"]) == set(ROWS)
    assert set(budgets["gate"]["reference_us"]) == set(ROWS)
    assert budgets["multiplier"] == MULTIPLIER
    assert budgets["gate"]["tolerance"] == RELATIVE_TOLERANCE
    assert budgets["gate"]["import_speed_exponent"] == IMPORT_SPEED_EXPONENT
    for row in ROWS:
        limit = budgets["budgets"][row]
        actual = measured["results"][row]
        if actual is not None:
            assert actual["n"] == REPETITIONS, row
        if limit is not None:
            assert limit["budget_p50_us"] == pytest.approx(
                limit["baseline_p50_us"] * MULTIPLIER, abs=0.001
            ), row


@pytest.mark.parametrize("row", ROWS)
def test_relative_budget(
    row: str, budgets: Dict[str, Any], measured: Dict[str, Any]
) -> None:
    """The gate: every row, every CPU, against its hardware-adjusted reference."""
    gate = budgets["gate"]
    runner = measured["runner"]
    platform_key = [runner["os"], _minor(runner["python_version"])]
    if platform_key != gate["platform"]:
        # 📝 The *shape* of the profile (which rows are cheap relative to
        #    others) depends on OS and CPython minor, not on the CPU: on
        #    Windows a cold import is ~1.5x heavier relative to a send than
        #    on Linux, and 3.14 changes the plugin rows. The speed factor
        #    cancels CPU speed only; the nightly is always Linux/3.13.
        pytest.skip(
            f"{row}: relative reference is for {' / Python '.join(gate['platform'])}; "
            f"this run is {' / Python '.join(platform_key)}"
        )
    verdict = measured["gate"]["rows"][row]
    if verdict["status"] == "no_reference":
        pytest.skip(f"{row}: {budgets['notes'].get(row, 'no reference')}")
    if verdict["status"] == "not_measured":
        _require_extras(row)
        pytest.fail(f"{row}: not measured although it has a reference")
    assert verdict["status"] == "pass", failure_message(
        row, verdict, measured["runner"]["cpu"]
    )


@pytest.mark.parametrize("row", ROWS)
def test_absolute_budget_report(
    row: str, budgets: Dict[str, Any], measured: Dict[str, Any]
) -> None:
    """Secondary: absolute µs budgets, asserted only on the recording CPU."""
    limit = budgets["budgets"][row]
    if limit is None:
        pytest.skip(f"{row}: {budgets['notes'].get(row, 'no budget')}")
    reference = budgets["runner"]
    runner = measured["runner"]
    if runner["cpu"] != reference["cpu"] or _minor(
        runner["python_version"]
    ) != _minor(reference["python_version"]):
        pytest.skip(
            f"{row}: absolute budget recorded on {reference['cpu']} "
            f"(Python {reference['python_version']}); this runner is "
            f"{runner['cpu']} (Python {runner['python_version']}) -- "
            "the relative gate covers it"
        )
    actual = measured["results"][row]
    if actual is None:
        _require_extras(row)
        pytest.fail(f"{row}: required extra unavailable on reference runner")
    p50 = actual["p50_us"]
    budget = limit["budget_p50_us"]
    assert p50 <= budget, (
        f"{row}: measured p50 {p50:.3f} us exceeds absolute "
        f"budget {budget:.3f} us on {runner['label']} ({runner['cpu']})"
    )
