"""`AgentTracePlugin(on_span="otel")` emits real spans (#273 x #287)."""

from __future__ import annotations

import importlib.util

import pytest

from .conftest import pytestmark  # noqa: F401

pytest.importorskip("opentelemetry.sdk.trace")
if importlib.util.find_spec("pydantic") is None:  # pragma: no cover
    pytest.skip("[agents] not installed", allow_module_level=True)


def test_on_span_otel_uses_the_global_provider(monkeypatch):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from src.xstate_statemachine.contrib.agents import AgentTracePlugin

    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    monkeypatch.setattr(
        trace, "get_tracer", lambda *a, **k: provider.get_tracer("t")
    )
    t = AgentTracePlugin(on_span="otel")

    class Interp:
        id = "agent-1"
        parent = None
        current_state_ids = {"a.thinking"}

    t.record(
        Interp(),
        "model_call",
        response={"model": "m", "usage": {"input_tokens": 2}, "text": "x"},
    )
    (span,) = exp.get_finished_spans()
    assert span.name == "gen_ai.chat"
    assert span.attributes["gen_ai.request.model"] == "m"
    assert span.attributes["gen_ai.usage.input_tokens"] == 2
    assert "gen_ai.completion" not in span.attributes  # content off
    with pytest.raises(ValueError):
        AgentTracePlugin(on_span="jaeger")
