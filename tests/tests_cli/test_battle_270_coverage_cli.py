# tests/tests_cli/test_battle_270_coverage_cli.py
"""#270 battle (adversary B): `xsm coverage FILE [--plain] [--fail-under N]`."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _doc(**over: Any) -> Dict[str, Any]:
    machine = {
        "machine": "café",
        "key": "k1",
        "states": {
            "visited": 1,
            "total": 2,
            "percent": 50.0,
            "unvisited": ["café.naïve→état"],
        },
        "transitions": {
            "hit": 0,
            "total": 1,
            "percent": 0.0,
            "unhit": [{"from": "café.a", "label": "GO", "to": "café.b"}],
        },
    }
    doc: Dict[str, Any] = {"version": 1, "machines": [machine]}
    doc.update(over)
    return doc


def _cli(*args: str, encoding: str = "utf-8") -> Any:
    env = {**os.environ, "PYTHONIOENCODING": encoding}
    env.pop("PYTHONUTF8", None)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "coverage", *args],
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
        timeout=120,
    )


@pytest.fixture
def report(tmp_path: pathlib.Path) -> pathlib.Path:
    from xstate_statemachine.coverage import reports_from_json

    p = tmp_path / "cov.json"
    p.write_text(json.dumps(_doc()), encoding="utf-8")
    reports_from_json(p.read_text("utf-8"))  # the schema this file pins
    return p


@pytest.mark.parametrize("value", ["nan", "inf", "101", "-1", "abc"])
def test_bad_fail_under_is_exit_2(report: pathlib.Path, value: str) -> None:
    r = _cli(str(report), "--fail-under", value)
    assert r.returncode == 2, r.stderr
    assert "percentage" in r.stderr and "Traceback" not in r.stderr


def test_fail_under_float(report: pathlib.Path) -> None:
    assert _cli(str(report), "--plain", "--fail-under", "49.5").returncode == 1
    assert _cli(str(report), "--plain", "--fail-under", "0").returncode == 0


def test_unicode_on_cp1252(report: pathlib.Path) -> None:
    for extra in (["--plain"], []):
        r = _cli(str(report), *extra, encoding="cp1252")
        assert r.returncode == 0, r.stderr
        assert "Traceback" not in r.stderr
        assert "caf" in r.stdout


def test_version_9_is_one_line_exit_1(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "v9.json"
    p.write_text(json.dumps(_doc(version=9)), encoding="utf-8")
    r = _cli(str(p), "--plain")
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "version" in (r.stdout + r.stderr).lower()


def test_empty_machines(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"version": 1, "machines": []}), "utf-8")
    r = _cli(str(p), "--plain")
    assert r.returncode == 0
    assert "no machines" in r.stdout + r.stderr


def test_empty_machines_with_gate_fails(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"version": 1, "machines": []}), "utf-8")
    assert _cli(str(p), "--plain", "--fail-under", "90").returncode == 1


def test_json_passthrough_round_trips(report: pathlib.Path) -> None:
    r = _cli(str(report), "--json")
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["version"] == 1 and doc["machines"][0]["key"] == "k1"


def test_help() -> None:
    r = _cli("--help")
    assert r.returncode == 0
    assert "--fail-under" in r.stdout and "report_file" in r.stdout


def test_missing_file_one_line(tmp_path: pathlib.Path) -> None:
    r = _cli(str(tmp_path / "nope.json"), "--plain")
    assert r.returncode == 1 and "Traceback" not in r.stderr
