# tests/test_examples_integrations.py
"""#277: smoke-test every `examples/integrations/*` app.

* Every ``machine.json`` passes ``xsm validate --plain`` (strict config)
  and builds with `stub_logic` -- no extra needed, default job.
* Every example with a ``tests/`` folder runs its own suite in a
  subprocess (the example dir on ``sys.path`` via its conftest). Needs the
  web extras, so it skips cleanly without ``fastapi``; the ``[fastapi]``
  contrib CI cell runs it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.xstate_statemachine import create_machine, stub_logic

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "examples" / "integrations"
MACHINES = sorted(INTEGRATIONS.glob("*/machine.json"))
SUITES = sorted(p.parent for p in INTEGRATIONS.glob("*/tests"))


def _env() -> dict:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        [src, str(ROOT)] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    return env


def test_there_are_integration_examples():
    assert MACHINES, "examples/integrations/*/machine.json disappeared"


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.parent.name)
def test_machine_validates_plain(path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "validate",
            str(path),
            "--plain",
        ],
        capture_output=True,
        text=True,
        env=_env(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.parent.name)
def test_machine_builds_with_stub_logic(path):
    cfg = json.loads(path.read_text("utf-8"))
    machine = create_machine(cfg, logic=stub_logic(cfg), strict_config=True)
    assert machine.id == cfg["id"]


@pytest.mark.parametrize("example", SUITES, ids=lambda p: p.name)
def test_example_suite_passes(example):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(example / "tests"),
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(example),
        capture_output=True,
        text=True,
        env=_env(),
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]
