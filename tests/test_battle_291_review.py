# tests/test_battle_291_review.py
"""#291 independent review -- regressions.

* **R1/R2** the two competitor-drift checks are nightly-only (skip on a
  pull request without `XSM_COMPARISON_DRIFT=1`), and the CI nightly job
  runs them;
* **R4** `run.py --db <existing directory>` is one `error:` line and
  exit 2, never a `StoreError` traceback;
* **R5** `run.py --trace <unwritable path>` is one `error:` line and exit
  2 -- never a silent run with zero usage;
* **R3** the scenario's `tomllib` uses are skip-guarded for 3.9 / 3.10.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "integrations" / "agents_support_bot"


def _run(*args: str, tmp: Path) -> subprocess.CompletedProcess:
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYTHONWARNINGS="ignore",  # third-party DeprecationWarnings on stderr
    )
    env["XSM_SUPPORT_BOT_DB"] = str(tmp / "ok.db")
    env["XSM_SUPPORT_BOT_TRACE"] = str(tmp / "ok.jsonl")
    return subprocess.run(
        [sys.executable, "run.py", "--fake", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        cwd=str(EXAMPLE),
    )


def test_r1_drift_checks_skip_without_the_nightly_flag() -> None:
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYTHONWARNINGS="ignore",  # third-party DeprecationWarnings on stderr
    )
    env.pop("XSM_COMPARISON_DRIFT", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "tests" / "test_battle_291_a.py"),
            "-k",
            "checked_date_is_recent or installed_langgraph_major",
            "-q",
            "-rs",
            "-p",
            "no:cacheprovider",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout[-1500:]
    assert re.search(r"\d+ skipped", proc.stdout), proc.stdout[-500:]
    assert "passed" not in proc.stdout.splitlines()[-1]


def test_r2_nightly_job_runs_the_drift_checks() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    job = ci.split("  comparisons:", 1)[1].split("\n  # ---", 1)[0]
    assert "XSM_COMPARISON_DRIFT" in job
    assert "tests/test_battle_291_a.py" in job
    assert "langgraph" in job  # the major-version check needs it installed
    for slug in ("vs-langgraph", "vs-burr", "vs-statelyai-agent"):
        page = (ROOT / "docs/_guide/comparisons" / f"{slug}.md").read_text(
            "utf-8"
        )
        assert "nightly" in page and "fails the build" not in page, slug


def test_r4_db_pointing_at_a_directory_is_one_line(tmp_path: Path) -> None:
    d = tmp_path / "adir"
    d.mkdir()
    out = _run("--db", str(d), tmp=tmp_path)
    assert out.returncode == 2, (out.returncode, out.stderr[-800:])
    assert "Traceback" not in out.stderr
    err = [ln for ln in out.stderr.splitlines() if ln.strip()]
    assert len(err) == 1 and err[0].startswith("error: cannot open"), err


def test_r5_unwritable_trace_is_one_line_not_a_silent_run(
    tmp_path: Path,
) -> None:
    blocker = tmp_path / "blk"
    blocker.write_text("i am a file", encoding="utf-8")
    out = _run("--trace", str(blocker / "t.jsonl"), tmp=tmp_path)
    assert out.returncode == 2, (out.returncode, out.stdout[-500:])
    assert "usage:" not in out.stdout  # the run never started
    err = [ln for ln in out.stderr.splitlines() if ln.strip()]
    assert len(err) == 1 and err[0].startswith("error: cannot open"), err


def test_r3_tomllib_is_skip_guarded_in_the_scenario() -> None:
    text = (ROOT / "tests" / "test_battle_291_scenario.py").read_text("utf-8")
    assert "import tomllib" not in text
    assert 'pytest.importorskip("tomllib")' in text
