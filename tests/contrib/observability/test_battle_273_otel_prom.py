"""Battle #273 (adversary A): OpenTelemetry / Prometheus plugin defects."""

from __future__ import annotations

import json
import threading

import pytest

from .conftest import pytestmark  # noqa: F401  (skip without the extra)

pytest.importorskip("opentelemetry.sdk.trace")
pytest.importorskip("prometheus_client")


def _tracer():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


def _run_with_context(context):
    from src.xstate_statemachine import SyncInterpreter, create_machine
    from src.xstate_statemachine.contrib.observability import (
        OpenTelemetryPlugin,
    )

    tracer, exp = _tracer()
    m = create_machine(
        {
            "id": "c",
            "initial": "a",
            "context": context,
            "states": {"a": {"on": {"T": "a"}}},
        }
    )
    plugin = OpenTelemetryPlugin(tracer, record_context=True)
    i = SyncInterpreter(m).use(plugin)
    i.start()
    i.send("T")
    i.stop()
    return plugin, [
        s for s in exp.get_finished_spans() if s.name.endswith("transition")
    ]


class _Session:
    def __repr__(self) -> str:
        return "Session(password=hunter2)"


def test_record_context_never_exports_repr_or_bytes_of_opaque_values():
    _, spans = _run_with_context(
        {"handle": _Session(), "raw": b"token=abc", "n": [{"pin": 1}]}
    )
    text = spans[-1].attributes["statechart.context"]
    assert "hunter2" not in text and "abc" not in text
    data = json.loads(text)
    assert data["handle"] == "<_Session>"
    assert data["raw"] == "<bytes>"


def test_record_context_with_mixed_key_types_still_ends_the_span():
    plugin, spans = _run_with_context({"by_id": {1: "x", "k": 2}})
    assert spans, "span popped but never ended"
    assert json.loads(spans[-1].attributes["statechart.context"])
    assert plugin._events == {}


def test_nested_secrets_are_redacted_at_depth():
    _, spans = _run_with_context(
        {"a": [{"b": {"card_number": "4111", "Access-Token": "t"}}]}
    )
    text = spans[-1].attributes["statechart.context"]
    assert "4111" not in text and '"t"' not in text


@pytest.mark.parametrize(
    "value,ok",
    [
        ("ff-" + "a" * 32 + "-" + "b" * 16 + "-01", False),
        ("00-" + "0" * 32 + "-" + "b" * 16 + "-01", False),
        ("00-" + "a" * 32 + "-" + "0" * 16 + "-01", False),
        ("00-" + "a" * 64 + "-" + "b" * 16 + "-01", False),
        ("00-" + "A" * 32 + "-" + "B" * 16 + "-01", True),
    ],
)
def test_traceparent_parsing(value, ok):
    from src.xstate_statemachine.contrib.observability.otel import (
        _parse_traceparent,
    )

    assert (_parse_traceparent(value) is not None) is ok


def test_nested_raise_spans_are_sequential_and_durations_not_doubled():
    from prometheus_client import CollectorRegistry

    from src.xstate_statemachine import SyncInterpreter, create_machine
    from src.xstate_statemachine.contrib.observability import (
        OpenTelemetryPlugin,
        PrometheusPlugin,
    )

    raise_inner = {"type": "xstate.raise", "params": {"event": {"type": "IN"}}}
    m = create_machine(
        {
            "id": "n",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"actions": [raise_inner]}, "IN": "b"}},
                "b": {},
            },
        }
    )
    tracer, exp = _tracer()
    reg = CollectorRegistry()
    i = SyncInterpreter(m).use(OpenTelemetryPlugin(tracer))
    i.use(PrometheusPlugin(reg))
    i.start()
    i.send("GO")
    i.stop()
    spans = [s for s in exp.get_finished_spans()]
    assert [s.attributes["statechart.event.type"] for s in spans] == [
        "GO",
        "IN",
    ]
    # one observation per settled event (GO + IN), never nested
    assert reg.get_sample_value(
        "xstatemachine_transition_duration_seconds_count", {"machine": "n"}
    ) == pytest.approx(2.0)


def test_sixteen_threads_share_plugins_exactly_and_scrapes_never_raise():
    from prometheus_client import CollectorRegistry

    from src.xstate_statemachine import SyncInterpreter, create_machine
    from src.xstate_statemachine.contrib.observability import (
        OpenTelemetryPlugin,
        PrometheusPlugin,
    )

    m = create_machine(
        {
            "id": "t",
            "initial": "a",
            "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}},
        }
    )
    reg = CollectorRegistry()
    prom = PrometheusPlugin(reg)
    tracer, _ = _tracer()
    otel = OpenTelemetryPlugin(tracer)
    errors: list = []
    done = threading.Event()

    def worker():
        try:
            i = SyncInterpreter(m).use(prom).use(otel)
            i.start()
            for _ in range(200):
                i.send("T")
            i.stop()
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    def scraper():
        while not done.is_set():
            try:
                list(prom.m["queue_depth"].collect())
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

    s = threading.Thread(target=scraper)
    s.start()
    ts = [threading.Thread(target=worker) for _ in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    done.set()
    s.join()
    assert errors == []
    labels = {"machine": "t", "from_state": "t.a", "to_state": "t.b"}
    assert reg.get_sample_value(
        "xstatemachine_transitions_total", dict(labels, event="T")
    ) == pytest.approx(16 * 100)
    assert prom._started == {} and prom._unhandled == {}
    assert otel._events == {} and otel._services == {}


def test_label_guard_never_exceeds_cap_under_contention():
    from src.xstate_statemachine.contrib.observability._hygiene import (
        LabelGuard,
    )

    g = LabelGuard(10)
    barrier = threading.Barrier(16)

    def hit(n):
        barrier.wait()
        for k in range(50):
            g("d", f"{n}-{k}")

    ts = [threading.Thread(target=hit, args=(n,)) for n in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(g._seen["d"]) == 10
