"""#287 E1 / #290 E4: `AgentTracePlugin` -- gen_ai.* JSONL, no content by
default, redaction when content is on, the `on_span` seam."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pytest

from ..conftest import requires_extra
from .conftest import weather_tools

pytestmark = requires_extra("agents")
pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    AgentTracePlugin,
    FakeModel,
    load_chart,
    run_agent_sync,
)

SCRIPT = [
    {"tool": "get_weather", "args": {"city": "Kochi"}},
    {"text": "PRIVATE ANSWER", "usage": {"cost_usd": 0.01}},
]


def _run(trace: AgentTracePlugin, chart: Any = None, script=SCRIPT) -> Any:
    reg, _ = weather_tools()
    return run_agent_sync(
        chart,
        model=FakeModel(script, is_async=False, name="fake-1"),
        tools=reg,
        prompt="PRIVATE PROMPT",
        tracer=trace,
        plugins=[trace],
    )


class TestTrace:
    def test_gen_ai_fields_and_no_content(self) -> None:
        buf = io.StringIO()
        trace = AgentTracePlugin(buf, clock=lambda: 1.0)
        _run(trace)
        lines = [json.loads(x) for x in buf.getvalue().splitlines()]
        assert lines == trace.records
        calls = [r for r in lines if r["kind"] == "model_call"]
        assert len(calls) == 2
        assert calls[0]["gen_ai.usage.input_tokens"] == 10
        assert calls[0]["gen_ai.usage.output_tokens"] == 5
        assert calls[0]["gen_ai.request.model"] == "fake-1"
        assert calls[0]["gen_ai.operation.name"] == "chat"
        assert calls[0]["gen_ai.response.tool_calls"] == ["get_weather"]
        assert calls[0]["state"] == ["toolLoop.awaiting_model"]
        tools = [r for r in lines if r["kind"] == "tool_call"]
        assert tools[0]["gen_ai.tool.name"] == "get_weather"
        blob = buf.getvalue()
        for secret in ("PRIVATE", "Kochi", "sk-LEAK"):
            assert secret not in blob
        kinds = {r["kind"] for r in lines}
        assert {"agent_start", "transition", "agent_end"} <= kinds

    def test_record_content_is_redacted(self) -> None:
        trace = AgentTracePlugin(record_content=True)
        _run(trace)
        blob = json.dumps(trace.records)
        assert "PRIVATE ANSWER" in blob and "PRIVATE PROMPT" in blob
        assert "sk-LEAK" not in blob and "***" in blob

    def test_totals(self) -> None:
        trace = AgentTracePlugin()
        _run(trace)
        t = trace.totals()
        assert t["total"]["turns"] == 2
        assert t["total"]["cost_usd"] == pytest.approx(0.01)
        assert list(t["agents"]) == ["toolLoop"]

    def test_denial_is_traced(self) -> None:
        chart = load_chart()
        chart["states"]["awaiting_model"]["meta"]["tools"] = ["*"]
        chart["states"]["awaiting_tool"]["meta"]["tools"] = ["get_weather"]
        chart["states"]["awaiting_model"]["invoke"]["onDone"].pop(0)
        trace = AgentTracePlugin()
        _run(trace, chart, script=[{"tool": "secret"}])
        denied = [r for r in trace.records if r["kind"] == "tool_denied"]
        assert denied[0]["gen_ai.tool.name"] == "secret"
        assert "allow-list" in denied[0]["reason"]

    def test_sinks_path_and_callable(self, tmp_path) -> None:
        path = tmp_path / "t.jsonl"
        got: List[Dict[str, Any]] = []
        _run(AgentTracePlugin(str(path)))
        _run(AgentTracePlugin(got.append))
        assert path.read_text(encoding="utf-8").count("\n") == len(got)

    def test_on_span_seam_is_contained(self) -> None:
        seen: List[str] = []

        def span(rec: Dict[str, Any]) -> None:
            seen.append(rec["kind"])
            raise RuntimeError("exporter down")

        res = _run(AgentTracePlugin(on_span=span))
        assert res.final_state.endswith("done") and "model_call" in seen

    def test_error_hook(self) -> None:
        trace = AgentTracePlugin()
        trace.on_error(
            type("I", (), {"id": "x", "parent": None})(), KeyError()
        )
        assert trace.records[-1]["reason"] == "KeyError"
