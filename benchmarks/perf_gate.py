"""Hardware-independent performance gate for issue #307.

The nightly ``perf`` job lands on whichever CPU GitHub allocates. Three
consecutive nightlies ran on three different models (AMD EPYC 9V74, 7763,
9V45) and measured the same code up to 2.4x apart, so an absolute
microsecond budget is only meaningful on the CPU it was recorded on --
which the old gate handled by skipping, i.e. it gated one night in three.

This module turns one run into a verdict that does not depend on the CPU:

1. ``speed_factor`` -- the **median** over the core rows of
   ``measured / reference``. A uniformly 2x slower machine has a speed
   factor of exactly 2.
2. ``relative`` -- ``measured / (reference * speed_factor)`` per row. A
   machine shift cancels; a regression in one row barely moves the median,
   so it shows up almost undiluted in that row's relative value.
3. A row fails when its relative value exceeds the tolerance.

Pure functions, stdlib only, no timing: the deterministic unit tests in
``tests/test_perf_gate.py`` run in the default job.

🏛️ Design decision (#307 battle test). Three candidates were evaluated
against the three real nightly artifacts:

* **Ratio to one reference row** (``row / hooks_empty_sync``). Rejected:
  a single noisy denominator moves every verdict at once, and the
  cross-CPU spread of the ratios was still 1.5x (snapshot rows) to 1.66x
  (imports) -- wider than any useful tolerance.
* **Per-CPU baseline table** auto-recording a new CPU's first run.
  Rejected as the *gate*: a nightly cannot commit its own baseline, so a
  new CPU is unenforced until someone edits the file, and GitHub kept
  adding models. Worse, the same EPYC 9V74 measured every row 25-30 %
  above its own baseline in run 36659646069, so absolute numbers drift
  even on matching silicon. Kept as the secondary, report-only
  ``cpu_baselines`` table and as the evidence the reference is fitted to.
* **Calibration probe** (time a fixed pure-Python loop, divide by it).
  Rejected: a synthetic loop exercises a different mix (no allocation,
  no dict churn, no asyncio, no SQLite) than the rows it would normalise,
  so it would not track their hardware sensitivity; the rows themselves
  are a far better probe. The median-of-ratios *is* a calibration probe
  built from the real workload, robust to any one row regressing.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, Iterable, List, Mapping, Optional

# 📝 One run on one CPU is fitted to the others with at most 1.14x
#    residual on the core rows (3 EPYC models), while a 1.5x regression
#    in any one core row measures at least 1.28x -- 1.25 separates them,
#    and matches the long-standing ``MULTIPLIER``.
RELATIVE_TOLERANCE = 1.25
# ⚠️ Import rows time a cold subprocess import -- filesystem, page cache
#    and unmarshalling, not the interpreter hot path. Across the three
#    EPYC models they tracked the core speed factor only as its square
#    root (fitted exponent 0.46 / 0.48), so their expected value is
#    ``reference * factor ** 0.5``. They stay out of the speed factor.
IMPORT_SPEED_EXPONENT = 0.5
# 📝 Minimum rows for a meaningful median; below it the run is broken.
MIN_SPEED_ROWS = 5


def is_import_row(row: str) -> bool:
    """Whether *row* times a cold subprocess import."""
    return row.startswith("import_")


def hardware_scale(row: str, factor: float) -> float:
    """How much slower *row* is expected to be on a *factor*-slower CPU."""
    if is_import_row(row):
        return float(factor**IMPORT_SPEED_EXPONENT)
    return factor


def speed_rows(reference: Mapping[str, Optional[float]]) -> List[str]:
    """Rows that contribute to the speed factor (core, with a reference)."""
    return sorted(
        row
        for row, value in reference.items()
        if value is not None and not is_import_row(row)
    )


def speed_factor(
    measured: Mapping[str, Optional[float]],
    reference: Mapping[str, Optional[float]],
) -> float:
    """Median of ``measured / reference`` over the shared core rows.

    Raises:
        ValueError: If fewer than ``MIN_SPEED_ROWS`` rows are comparable.
    """
    ratios = [
        measured[row] / reference[row]  # type: ignore[operator]
        for row in speed_rows(reference)
        if measured.get(row) is not None
    ]
    if len(ratios) < MIN_SPEED_ROWS:
        raise ValueError(
            f"only {len(ratios)} comparable rows; need {MIN_SPEED_ROWS}"
        )
    return statistics.median(ratios)


def fit_reference(
    runs: Iterable[Mapping[str, Optional[float]]],
    anchor: Mapping[str, Optional[float]],
    iterations: int = 5,
) -> Dict[str, Optional[float]]:
    """Consensus per-row reference across runs on different hardware.

    Each run is divided by its own speed factor, the geometric mean is
    taken per row, and the result is rescaled so *anchor* (the run the
    absolute budgets were recorded on) has speed factor 1.0 -- the
    reference then reads as microseconds on that CPU.
    """
    runs = list(runs)
    rows = [row for row, value in anchor.items() if value is not None]
    reference: Dict[str, Optional[float]] = {
        row: statistics.geometric_mean([run[row] for run in runs])  # type: ignore[misc]
        for row in rows
    }
    for _ in range(iterations):
        factors = [speed_factor(run, reference) for run in runs]
        reference = {
            row: statistics.geometric_mean(
                [
                    run[row] / hardware_scale(row, f)  # type: ignore[operator]
                    for run, f in zip(runs, factors)
                ]
            )
            for row in rows
        }
    scale = speed_factor(anchor, reference)
    fitted: Dict[str, Optional[float]] = {
        row: round(value * hardware_scale(row, scale), 3)  # type: ignore[operator]
        for row, value in reference.items()
    }
    for row, value in anchor.items():
        if value is None:
            fitted[row] = None
    return fitted


def verdicts(
    measured: Mapping[str, Optional[float]],
    reference: Mapping[str, Optional[float]],
) -> Dict[str, Any]:
    """Relative verdict for every row of *reference*.

    Returns:
        ``{"speed_factor": f, "rows": {row: {...}}}``. Each row carries
        ``status`` (``"pass"`` / ``"fail"`` / ``"no_reference"`` /
        ``"not_measured"``) and, when compared, ``measured_us``,
        ``expected_us`` (reference x speed factor), ``relative`` and
        ``tolerance``.
    """
    factor = speed_factor(measured, reference)
    rows: Dict[str, Dict[str, Any]] = {}
    for row, ref in reference.items():
        actual = measured.get(row)
        if ref is None:
            rows[row] = {"status": "no_reference"}
            continue
        if actual is None:
            rows[row] = {"status": "not_measured"}
            continue
        expected = ref * hardware_scale(row, factor)
        relative = actual / expected
        limit = RELATIVE_TOLERANCE
        rows[row] = {
            "status": "pass" if relative <= limit else "fail",
            "measured_us": round(actual, 3),
            "expected_us": round(expected, 3),
            "relative": round(relative, 3),
            "tolerance": limit,
        }
    return {"speed_factor": round(factor, 4), "rows": rows}


def failure_message(row: str, verdict: Mapping[str, Any], cpu: str) -> str:
    """One line naming row, measured, budget and CPU.

    When the row was re-measured to confirm (see the gate test), both
    readings are shown so a borderline row is diagnosable from the log.
    """
    budget = verdict["expected_us"] * verdict["tolerance"]
    confirm = (
        f" [confirmed: first reading {verdict['first_measured_us']:.3f} us "
        f"= {verdict['first_relative']:.2f}x, re-measured alone]"
        if verdict.get("remeasured")
        else ""
    )
    return (
        f"{row}: measured p50 {verdict['measured_us']:.3f} us is "
        f"{verdict['relative']:.2f}x the hardware-adjusted reference "
        f"{verdict['expected_us']:.3f} us (budget {budget:.3f} us = "
        f"x{verdict['tolerance']}) on {cpu}{confirm}"
    )
