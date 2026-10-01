"""Deterministic tests of the hardware-independent perf gate (#307).

No timing here -- these run in the default job. They pin the two
properties the gate exists for, on the three real nightly profiles
recorded in ``benchmarks/budgets.json``:

* a uniform hardware shift (any CPU, 0.5x to 2x) never fails, and
* a 1.5x regression in any single row always fails, naming row,
  measured value, budget and CPU.

Plus the ratchet rules on ``budgets.json`` itself.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from benchmarks.integrations_characteristics import MULTIPLIER, ROWS
from benchmarks.perf_gate import (
    IMPORT_SPEED_EXPONENT,
    RELATIVE_TOLERANCE,
    failure_message,
    fit_reference,
    hardware_scale,
    speed_factor,
    verdicts,
)

ROOT = Path(__file__).resolve().parents[1]
BUDGETS_PATH = ROOT / "benchmarks" / "budgets.json"
BUDGETS: Dict[str, Any] = json.loads(BUDGETS_PATH.read_text(encoding="utf-8"))
REFERENCE: Dict[str, Optional[float]] = BUDGETS["gate"]["reference_us"]
PROFILES: Dict[str, Dict[str, Optional[float]]] = {
    cpu: entry["p50_us"] for cpu, entry in BUDGETS["cpu_baselines"].items()
}
GATED = [row for row in ROWS if REFERENCE.get(row) is not None]


def _shift(
    profile: Dict[str, Optional[float]], factor: float
) -> Dict[str, Any]:
    return {
        row: (None if v is None else v * hardware_scale(row, factor))
        for row, v in profile.items()
    }


# -----------------------------------------------------------------------------
# 🧮 The gate itself
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("cpu", sorted(PROFILES))
def test_every_recorded_cpu_passes_the_gate(cpu: str) -> None:
    # Act
    result = verdicts(PROFILES[cpu], REFERENCE)

    # Assert
    failing = {
        row: v["relative"]
        for row, v in result["rows"].items()
        if v["status"] == "fail"
    }
    assert failing == {}, f"{cpu}: {failing}"


@pytest.mark.parametrize("factor", [0.5, 0.8, 1.33, 2.0, 2.4])
@pytest.mark.parametrize("cpu", sorted(PROFILES))
def test_uniform_hardware_shift_passes(cpu: str, factor: float) -> None:
    # Arrange
    shifted = _shift(PROFILES[cpu], factor)

    # Act
    result = verdicts(shifted, REFERENCE)

    # Assert
    assert result["speed_factor"] == pytest.approx(
        factor * speed_factor(PROFILES[cpu], REFERENCE), rel=1e-3
    )
    assert all(v["status"] != "fail" for v in result["rows"].values())


@pytest.mark.parametrize("row", GATED)
@pytest.mark.parametrize("cpu", sorted(PROFILES))
def test_single_row_regression_of_1_5x_fails(cpu: str, row: str) -> None:
    # Arrange -- a 1.5x regression in one row, on a 2x slower machine
    regressed = _shift(PROFILES[cpu], 2.0)
    regressed[row] *= 1.5

    # Act
    verdict = verdicts(regressed, REFERENCE)["rows"][row]

    # Assert
    assert verdict["status"] == "fail", (cpu, row, verdict)


def test_failure_message_names_row_measured_budget_and_cpu() -> None:
    # Arrange
    cpu = sorted(PROFILES)[0]
    regressed = dict(PROFILES[cpu])
    regressed["hooks_empty_sync"] *= 1.5  # type: ignore[operator]
    verdict = verdicts(regressed, REFERENCE)["rows"]["hooks_empty_sync"]

    # Act
    message = failure_message("hooks_empty_sync", verdict, cpu)

    # Assert
    assert message.startswith("hooks_empty_sync: measured p50 ")
    assert f"{verdict['measured_us']:.3f} us" in message
    budget = verdict["expected_us"] * verdict["tolerance"]
    assert f"budget {budget:.3f} us" in message
    assert message.endswith(f"on {cpu}")


def test_blind_spot_boundary_is_half_the_core_rows() -> None:
    """📝 Documented limit (independent review): the median absorbs a
    regression that hits ≥ 7 of the 14 core rows at 1.5x -- and already
    dilutes one that hits 5-6 (some of them pass). Pin both so a change
    to the row set or the statistic is noticed. Measured on all three
    recorded CPUs: k=7 catches 0; k=5-6 catches 3-6 of them."""
    from benchmarks.perf_gate import speed_rows

    core = speed_rows(REFERENCE)
    assert len(core) == 14
    for cpu, profile in PROFILES.items():
        order = sorted(core, key=lambda r: profile[r] / REFERENCE[r])  # type: ignore[operator]

        def caught(k: int) -> int:
            regressed = dict(profile)
            for row in order[:k]:
                regressed[row] *= 1.5  # type: ignore[operator]
            rows = verdicts(regressed, REFERENCE)["rows"]
            return sum(rows[r]["status"] == "fail" for r in order[:k])

        # One lone row is always caught (the common case).
        assert caught(1) == 1, cpu
        # Half the rows together: the median moves with them, none caught.
        assert caught(7) == 0, cpu
        # In between the gate is partial, never silent.
        assert 1 <= caught(5) <= 5, cpu


def test_first_dispatch_profile_fails_one_row_then_confirms_pass() -> None:
    """🎯 The real first dispatch (run 36929316771, EPYC 9V74): speed factor
    0.984, `persisted_sqlite_async` 422.0 us -> relative 1.269, all other
    rows 0.9-1.15x. The gate must flag that row and nothing else; the
    confirm step (`tests/test_perf_budgets.py::_remeasure`) then clears
    it if a second reading is inside tolerance."""
    from benchmarks.perf_gate import hardware_scale

    cpu = "AMD EPYC 9V74 80-Core Processor"
    first = {r: v * 0.984 for r, v in PROFILES[cpu].items() if v}
    first["persisted_sqlite_async"] = 422.006
    result = verdicts(first, REFERENCE)
    rows = result["rows"]
    assert result["speed_factor"] == pytest.approx(0.984, abs=0.01)
    assert rows["persisted_sqlite_async"]["status"] == "fail"
    assert rows["persisted_sqlite_async"]["relative"] == pytest.approx(
        1.269, abs=0.02
    )
    others = [v for r, v in rows.items() if r != "persisted_sqlite_async"]
    assert all(v["status"] != "fail" for v in others)
    # A second reading at the historical 9V74 value is inside tolerance.
    second = PROFILES[cpu]["persisted_sqlite_async"]
    expected = REFERENCE["persisted_sqlite_async"] * hardware_scale(  # type: ignore[operator]
        "persisted_sqlite_async", result["speed_factor"]
    )
    assert second / expected < 1.25  # type: ignore[operator]


def test_rows_without_reference_are_reported_not_gated() -> None:
    # Act
    result = verdicts(PROFILES[sorted(PROFILES)[0]], REFERENCE)

    # Assert
    for row in ROWS:
        if REFERENCE[row] is None:
            assert result["rows"][row] == {"status": "no_reference"}


def test_speed_factor_refuses_a_run_with_too_few_rows() -> None:
    with pytest.raises(ValueError, match="comparable rows"):
        speed_factor({"hooks_empty_sync": 1.0}, REFERENCE)


def test_reference_is_reproducible_from_the_recorded_profiles() -> None:
    # Arrange
    anchor = PROFILES[BUDGETS["gate"]["reference_cpu"]]

    # Act
    fitted = fit_reference(PROFILES.values(), anchor)

    # Assert -- the committed reference is exactly what the data gives
    for row in ROWS:
        if REFERENCE[row] is None:
            continue
        assert fitted[row] == pytest.approx(REFERENCE[row], rel=1e-3), row


def test_gate_constants_match_the_budget_file() -> None:
    gate = BUDGETS["gate"]
    assert gate["method"] == "relative"
    assert gate["tolerance"] == RELATIVE_TOLERANCE == MULTIPLIER
    assert gate["import_speed_exponent"] == IMPORT_SPEED_EXPONENT
    assert set(gate["reference_us"]) == set(ROWS)
    assert gate["reference_cpu"] == BUDGETS["runner"]["cpu"]
    for cpu, entry in BUDGETS["cpu_baselines"].items():
        assert entry["perf_run"] in gate["fitted_from_runs"], cpu
        assert set(entry["p50_us"]) == set(ROWS), cpu


# -----------------------------------------------------------------------------
# 🔒 Ratchet discipline on budgets.json
# -----------------------------------------------------------------------------
def test_every_null_budget_has_a_note() -> None:
    for row in ROWS:
        if BUDGETS["budgets"][row] is None:
            assert BUDGETS["notes"].get(row), row
        if REFERENCE[row] is None:
            assert BUDGETS["notes"].get(row), row


def _previous_budgets() -> Dict[str, Any]:
    git = shutil.which("git")
    if git is None or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    proc = subprocess.run(
        [git, "show", "HEAD~1:benchmarks/budgets.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip("no previous budgets.json in git history (shallow clone?)")
    return json.loads(proc.stdout)  # type: ignore[no-any-return]


def _increase_is_justified(row: str) -> bool:
    """An increase must carry a note naming the perf run it came from.

    📝 Review L: "perf run on 3.13" used to count. A GitHub Actions run
    id is an 8+-digit number; require exactly that.
    """
    import re

    note = str(BUDGETS["notes"].get(row, ""))
    return re.search(r"perf run \d{8,}", note) is not None


def test_baselines_only_go_down_unless_a_note_names_a_perf_run() -> None:
    # Arrange
    previous = _previous_budgets()

    # Act -- compare like with like: absolute budgets only on the same CPU,
    #        relative references always (they are CPU-independent).
    raised = []
    same_cpu = (
        previous.get("runner", {}).get("cpu") == BUDGETS["runner"]["cpu"]
    )
    for row in ROWS:
        old = (previous.get("budgets") or {}).get(row)
        new = BUDGETS["budgets"].get(row)
        if same_cpu and old and new:
            if new["baseline_p50_us"] > old["baseline_p50_us"] + 1e-9:
                raised.append(row)
        old_ref = (previous.get("gate") or {}).get("reference_us", {}).get(row)
        new_ref = REFERENCE.get(row)
        if old_ref is not None and new_ref is not None and new_ref > old_ref:
            raised.append(row)

    # Assert
    unjustified = sorted({r for r in raised if not _increase_is_justified(r)})
    assert unjustified == [], (
        "budgets.json raised a baseline without a notes entry naming the "
        f"perf run it was re-recorded from: {unjustified}"
    )
