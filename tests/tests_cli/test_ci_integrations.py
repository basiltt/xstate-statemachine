# tests/tests_cli/test_ci_integrations.py
"""The pre-commit hooks and the `xsm-check` GitHub Action (#309).

YAML is not stdlib, so the files are read with a tiny line reader that
understands exactly the flat shape they use; the documented commands are
then run for real on the example machine.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".pre-commit-hooks.yaml"
ACTION = ROOT / "action.yml"
SELFTEST = ROOT / ".github" / "workflows" / "xsm-check-selftest.yml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
MACHINE = (
    ROOT / "examples" / "integrations" / "fastapi_orders" / "machine.json"
)
KV = re.compile(r"^(?:- )?\s*([\w-]+):\s*(.*)$")


def _hooks() -> List[Dict[str, str]]:
    hooks: List[Dict[str, str]] = []
    for line in HOOKS.read_text("utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("- "):
            hooks.append({})
        m = KV.match(line)
        if m and hooks:
            hooks[-1][m.group(1)] = m.group(2).strip()
    return hooks


def _xsm(args: List[str]) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _entry_args(hook: Dict[str, str]) -> List[str]:
    parts = shlex.split(hook["entry"])
    assert parts[0] == "xsm", hook
    return parts[1:]


def test_hooks_file_declares_both_hooks() -> None:
    hooks = {h["id"]: h for h in _hooks()}
    assert set(hooks) == {"xsm-validate", "xsm-gt-check"}
    assert hooks["xsm-validate"]["entry"] == "xsm validate --plain"
    assert re.search(hooks["xsm-validate"]["files"], "a/b.machine.json")
    assert re.search(hooks["xsm-validate"]["files"], "x/machine.json")
    assert not re.search(hooks["xsm-validate"]["files"], "package.json")
    assert hooks["xsm-gt-check"]["pass_filenames"] == "false"
    assert "--check" in hooks["xsm-gt-check"]["entry"]
    for h in hooks.values():
        assert h["language"] == "python"


def test_validate_hook_passes_on_the_example_and_fails_on_a_bad_file(
    tmp_path: Path,
) -> None:
    hook = next(h for h in _hooks() if h["id"] == "xsm-validate")
    ok = _xsm(_entry_args(hook) + [str(MACHINE)])
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = tmp_path / "bad.machine.json"
    bad.write_text('{"id": "m", "initial": "nope", "states": {"a": {}}}')
    assert _xsm(_entry_args(hook) + [str(bad)]).returncode == 1


def test_gt_check_hook_detects_drift(tmp_path: Path) -> None:
    hook = next(h for h in _hooks() if h["id"] == "xsm-gt-check")
    gen = [str(MACHINE), "-o", str(tmp_path), "-t", "pythonic-class"]
    assert _xsm(["gt", *gen, "-f", "--plain"]).returncode == 0
    assert _xsm(_entry_args(hook) + gen).returncode == 0
    victim = sorted(tmp_path.glob("*.py"))[0]
    victim.write_text(victim.read_text("utf-8") + "# drift\n", "utf-8")
    assert _xsm(_entry_args(hook) + gen).returncode == 1


def test_action_is_composite_and_pins_setup_python_like_ci() -> None:
    text = ACTION.read_text("utf-8")
    assert "using: composite" in text
    for name in ("files:", "generated-dir:", "python-version:"):
        assert name in text
    pin = re.search(
        r"actions/setup-python@([0-9a-f]{40})", CI.read_text("utf-8")
    )
    assert pin and f"actions/setup-python@{pin.group(1)}" in text
    assert "xsm validate --plain" in text
    assert "xsm gt --check" in text


def test_selftest_workflow_uses_the_action_on_the_example() -> None:
    text = SELFTEST.read_text("utf-8")
    assert "uses: ./" in text
    assert "examples/integrations/fastapi_orders/machine.json" in text
    assert "workflow_dispatch" in text and "pull_request" in text
