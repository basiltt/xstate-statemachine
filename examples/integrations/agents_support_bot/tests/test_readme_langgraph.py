# examples/integrations/agents_support_bot/tests/test_readme_langgraph.py
"""The README's "Drop the bot into a LangGraph graph" block runs (#288)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("langgraph")

HERE = Path(__file__).resolve().parents[1]


def _langgraph_block() -> str:
    text = (HERE / "README.md").read_text(encoding="utf-8")
    section = text[text.index("## Drop the bot into a LangGraph graph") :]
    match = re.search(r"```python\n(.*?)```", section, re.S)
    assert match, "no python block in the LangGraph section"
    return match.group(1)


def test_readme_langgraph_block_runs(capsys: pytest.CaptureFixture) -> None:
    # 🚀 run the block exactly as a newcomer would paste it
    exec(compile(_langgraph_block(), "README.md", "exec"), {})
    out = capsys.readouterr().out.split()
    # ✅ parked first, refunded exactly once after approval
    assert out == ["awaiting_human", "done", "1"], out
