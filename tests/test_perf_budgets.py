"""Opt-in, reference-runner performance budgets for issue #307."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

if os.environ.get("XSM_PERF") != "1":
    pytest.skip("set XSM_PERF=1 to run timing tests", allow_module_level=True)

from benchmarks.integrations_characteristics import (  # noqa: E402
    MULTIPLIER,
    REPETITIONS,
    ROWS,
    run,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"


@pytest.fixture(scope="module")
def budgets() -> Dict[str, Any]:
    return json.loads(
        (BENCHMARKS / "budgets.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def measured() -> Dict[str, Any]:
    result = run()
    (BENCHMARKS / "last_run.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def test_budget_file_and_run_are_complete(
    budgets: Dict[str, Any], measured: Dict[str, Any]
) -> None:
    assert set(budgets["budgets"]) == set(ROWS)
    assert set(measured["results"]) == set(ROWS)
    assert budgets["multiplier"] == MULTIPLIER
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
def test_reference_runner_budget(
    row: str, budgets: Dict[str, Any], measured: Dict[str, Any]
) -> None:
    limit = budgets["budgets"][row]
    if limit is None:
        pytest.skip(f"{row}: integration not shipped in baseline")
    reference = budgets["runner"]
    runner = measured["runner"]
    if (
        runner["label"] != reference["label"]
        or runner["os"] != reference["os"]
        or runner["python_version"].split(".")[:2]
        != reference["python_version"].split(".")[:2]
    ):
        pytest.skip(
            f"{row}: reference runner is {reference['label']} "
            f"({reference['os']}, Python {reference['python_version']}); "
            f"current runner is {runner['label']} "
            f"({runner['os']}, Python {runner['python_version']})"
        )
    actual = measured["results"][row]
    if actual is None:
        if row == "import_with_extras":
            pytest.importorskip("redis")
            pytest.importorskip("pydantic")
        if row.startswith("validator_"):
            pytest.importorskip("pydantic")
        pytest.fail(f"{row}: required extra unavailable on reference runner")
    p50 = actual["p50_us"]
    budget = limit["budget_p50_us"]
    # 📝 Hosted runners are not pinned to one CPU model; name both so a red
    #    nightly can be told apart from a regression.
    assert p50 <= budget, (
        f"{row}: measured p50 {p50:.3f} us exceeds "
        f"budget {budget:.3f} us on {runner['label']} "
        f"({runner['cpu']}; baseline recorded on {reference['cpu']})"
    )
