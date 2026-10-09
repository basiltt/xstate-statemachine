# examples/integrations/agents_support_bot/tests/test_readme_supervisor.py
"""The README's "Supervisor: many tickets, one budget" block runs (#290)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

HERE = Path(__file__).resolve().parents[1]


def _block() -> str:
    text = (HERE / "README.md").read_text(encoding="utf-8")
    section = text[text.index("## Supervisor: many tickets, one budget") :]
    match = re.search(r"```python\n(.*?)```", section, re.S)
    assert match, "no python block in the Supervisor section"
    return match.group(1)


def test_readme_supervisor_block_runs(capsys: pytest.CaptureFixture) -> None:
    # 🚀 run the block exactly as a newcomer would paste it
    exec(compile(_block(), "README.md", "exec"), {})
    out = capsys.readouterr().out
    assert "supervisor.reporting" in out and "0.04" in out


def test_readme_workers_cannot_refund() -> None:
    # 🛡️ the README's claim: the worker allow-list is lookup_order only
    assert '.get("lookup_order")' in _block()
    assert "refund_order" not in _block()
