"""Verification for group G1b: #269 (`xsm_path`), #270 (coverage), #271
(Hypothesis model-based testing).

    python scripts/verify/G1b_testing.py

Runs against the installed package (``pip install -e ".[testing]"``), in a
throw-away directory, the way a user would: pytest with the plugin loaded
from its entry point, the `xsm` CLI as a subprocess. Plain Python;
Windows-safe (``tempfile``, no shell heredocs). Prints ``ALL OK``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
REFUND = ROOT / "tests" / "contrib" / "testing" / "examples" / "refund.json"

PATHS_TEST = f"""
import pytest

@pytest.mark.xstate_machine({(CORPUS / "AdvancePayment.json").as_posix()!r})
def test_reach(xsm_path, xsm_interp, xsm_clock):
    xsm_path.replay(xsm_interp, xsm_clock)
    assert xsm_interp.current_state_ids == set(xsm_path.final_states)
"""

COVERAGE_TEST = f"""
import pytest
from xstate_statemachine import create_machine, SyncInterpreter

@pytest.mark.xstate_machine({(CORPUS / "AdvancePayment.json").as_posix()!r})
def test_only_submit(xsm_interp, xsm_send_all):
    xsm_send_all(xsm_interp, "SUBMIT")

TOGGLE = {{"id": "toggle", "initial": "off", "states": {{
    "off": {{"on": {{"TOGGLE": "on"}}}},
    "on": {{"on": {{"TOGGLE": "off", "RESET": "off"}}}}}}}}

def test_direct_never_resets():
    i = SyncInterpreter(create_machine(TOGGLE)).start()
    i.send("TOGGLE"); i.send("TOGGLE")
"""

MODEL_TEST = f"""
from hypothesis import settings
from xstate_statemachine.contrib.testing import model_test

TestRefund = model_test(
    {REFUND.as_posix()!r},
    invariants={{"total never negative": lambda i: i.context["total"] >= 0}},
    settings=settings(max_examples=200, database=None, derandomize=True),
)
"""


def step(title: str) -> None:
    print(f"\n== {title}")


def pytest_run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *args,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def xsm(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

        step("1. #269 xsm_path: one case per configuration, readable ids")
        (cwd / "test_paths.py").write_text(PATHS_TEST, encoding="utf-8")
        proc = pytest_run(cwd, "test_paths.py", "-vv")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (
            "test_reach[path[editing->challenge]] PASSED" in proc.stdout
        ), proc.stdout
        print("  ", proc.stdout.strip().splitlines()[-1])
        proc = pytest_run(
            cwd, "test_paths.py", "-vv", "--xsm-path-guards=both"
        )
        assert (
            proc.returncode == 0 and "failure]] PASSED" in proc.stdout
        ), proc.stdout
        assert "4 passed" in proc.stdout, proc.stdout
        proc = pytest_run(cwd, "test_paths.py", "--xsm-full-paths")
        assert proc.returncode == 0, proc.stdout
        print("   --xsm-full-paths:", proc.stdout.strip().splitlines()[-1])

        step("2. #270 --xsm-coverage: summary, gate, JSON, HTML, direct")
        (cwd / "test_cov.py").write_text(COVERAGE_TEST, encoding="utf-8")
        report = cwd / "cov" / "xsmcov.json"
        page = cwd / "cov" / "xsmcov.html"
        proc = pytest_run(
            cwd,
            "test_cov.py",
            "--xsm-coverage",
            "--xsm-coverage-report=term",
            f"--xsm-coverage-report=json:{report}",
            f"--xsm-coverage-report=html:{page}",
            "--xsm-fail-under-state-coverage=100",
        )
        print(proc.stdout)
        assert proc.returncode == 1, "state gate must fail the session"
        assert "---- xstate coverage ----" in proc.stdout
        assert "unhit:     on --RESET--> off" in proc.stdout
        doc = json.loads(report.read_text("utf-8"))
        assert doc["version"] == 1
        assert {m["machine"] for m in doc["machines"]} >= {"toggle"}
        html = page.read_text("utf-8")
        assert "<script" not in html and "http" not in html.split("<body>")[1]
        proc = pytest_run(cwd, "test_cov.py")
        assert proc.returncode == 0 and "xstate coverage" not in proc.stdout

        step("3. #270 xsm coverage CLI (plain, json, --fail-under)")
        out = xsm("coverage", str(report), "--plain")
        assert out.returncode == 0, out.stdout + out.stderr
        assert "unhit      on --RESET--> off" in out.stdout, out.stdout
        print(out.stdout)
        out = xsm("coverage", str(report), "--json")
        assert json.loads(out.stdout)["version"] == 1
        out = xsm("coverage", str(report), "--fail-under", "100", "--plain")
        assert out.returncode == 1, out.stdout

        step(
            "4. #271 model_test finds the seeded REFUND bug, shrinks, replays"
        )
        (cwd / "test_model.py").write_text(MODEL_TEST, encoding="utf-8")
        failing_dir = cwd / "failing"
        proc = pytest_run(
            cwd, "test_model.py", f"--xsm-failing-dir={failing_dir}"
        )
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert "invariant 'total never negative' violated" in proc.stdout
        script = json.loads((failing_dir / "failing.json").read_text("utf-8"))
        print("   minimal sequence:", script)
        assert len(script) <= 4
        out = xsm(
            "simulate",
            str(REFUND),
            "--script",
            str(failing_dir / "failing.json"),
            "--json",
        )
        state = json.loads(out.stdout)
        assert state["context"]["total"] < 0, state
        print("   replayed: total =", state["context"]["total"])

        step("5. the contrib.testing package imports without hypothesis")
        child = (
            "import sys\n"
            "sys.modules['hypothesis'] = None\n"
            "import xstate_statemachine.contrib.testing as t\n"
            "from xstate_statemachine import MissingExtraError\n"
            "try:\n"
            "    t.model_test({'id': 'm', 'initial': 'a', 'states': {'a': {}}})\n"
            "except MissingExtraError as e:\n"
            "    assert '[testing]' in str(e), e\n"
            "    print('   OK', e)\n"
            "else:\n"
            "    raise SystemExit('model_test ran without hypothesis?!')\n"
        )
        subprocess.run([sys.executable, "-c", child], check=True)

    step("6. the group's test files")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/testing",
            "tests/test_coverage.py",
            "tests/test_import_surface.py",
            "tests/test_zero_dependency.py",
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
