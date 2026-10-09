"""#287 battle (adversary B): the CLI on the agent charts, as an operator.

`xsm inspect` / `diagram` / `docs` / `simulate --events` on the shipped
TOOL_LOOP chart and the support-bot example, offline (no model is
called: `simulate` stubs services, so `awaiting_model` never resolves
unless a guard is forced).
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
from contextlib import redirect_stderr, redirect_stdout
from typing import List, Tuple

import pytest

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHARTS = [
    ROOT / "src/xstate_statemachine/contrib/agents/charts/tool_loop.json",
    ROOT / "examples/integrations/agents_support_bot/machine.json",
]


def _run(argv: List[str]) -> Tuple[int, str, str]:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                main()
                code = 0
            except SystemExit as exc:
                code = int(exc.code or 0)
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


@pytest.mark.parametrize("chart", CHARTS, ids=lambda p: p.name)
@pytest.mark.parametrize("cmd", ["inspect", "diagram", "docs", "validate"])
def test_read_only_commands_succeed_without_traceback(chart, cmd):
    code, out, err = _run([cmd, str(chart)])
    assert code == 0, err
    assert "Traceback" not in out + err


@pytest.mark.parametrize("chart", CHARTS, ids=lambda p: p.name)
def test_simulate_drives_the_human_gate_offline(chart):
    # Arrange: force the model turn to "propose a side-effect tool"
    # Act
    code, out, err = _run(
        [
            "simulate",
            str(chart),
            "--json",
            "--events",
            "START,HUMAN_REJECTED",
        ]
    )
    # Assert: START parks in awaiting_human (stubbed guards are truthy),
    # HUMAN_REJECTED goes back through the budget gate
    assert code == 0, err
    data = json.loads(out)
    labels = [h.get("label") for h in data["history"]]
    assert "START" in labels and "HUMAN_REJECTED" in labels
    assert "Traceback" not in err


@pytest.mark.parametrize("chart", CHARTS, ids=lambda p: p.name)
def test_simulate_start_reaches_awaiting_human(chart):
    code, out, err = _run(["simulate", str(chart), "--json", "-e", "START"])
    assert code == 0, err
    assert json.loads(out)["value"] == "awaiting_human"


def test_missing_chart_is_one_line_not_a_traceback(tmp_path):
    code, out, err = _run(["inspect", str(tmp_path / "nope.json")])
    assert code != 0
    assert "Traceback" not in out + err
