"""OpenTelemetry + Prometheus plugins (#273)."""

from __future__ import annotations

import asyncio
import time

import pytest

from .conftest import pytestmark  # noqa: F401  (skip without the extra)

otel_sdk = pytest.importorskip("opentelemetry.sdk.trace")


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


def _wait(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return cond()


# =============================================================================
# OpenTelemetry
# =============================================================================
class TestOpenTelemetry:
    def test_span_per_event_attributes_and_service_child(
        self, machine_factory
    ):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()
        i = SyncInterpreter(machine_factory()).use(OpenTelemetryPlugin(tracer))
        i.start()
        i.send("PAY")
        assert _wait(lambda: "shop.paid" in i.current_state_ids)
        i.send("DENY")  # unhandled in `paid`
        i.stop()
        spans = exp.get_finished_spans()
        names = [s.name for s in spans]
        assert "statechart.service" in names
        pay = next(
            s
            for s in spans
            if s.name == "statechart.transition"
            and s.attributes["statechart.event.type"] == "PAY"
        )
        a = pay.attributes
        assert a["statechart.machine_id"] == "shop"
        assert tuple(a["statechart.from"]) == ("shop.idle",)
        assert tuple(a["statechart.to"]) == ("shop.paying",)
        assert a["statechart.changed"] is True
        assert a["statechart.denied"] is False
        assert a["statechart.deferred"] is False
        ev = [e for e in pay.events if e.name == "guard_evaluated"]
        assert ev and ev[0].attributes["guard.name"] == "canPay"
        assert ev[0].attributes["guard.result"] is True
        svc = next(s for s in spans if s.name == "statechart.service")
        assert svc.attributes["service.src"] == "charge"
        assert svc.parent is not None
        assert svc.parent.span_id == pay.context.span_id
        # X0.6: no interpreter id, no context by default
        for s in spans:
            assert "statechart.context" not in (s.attributes or {})
            for v in (s.attributes or {}).values():
                assert "card_number" not in str(v)

    def test_denied_and_errors_are_recorded(self, machine_factory):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()
        i = SyncInterpreter(machine_factory(charge_fails=True)).use(
            OpenTelemetryPlugin(tracer)
        )
        i.start()
        i.send("DENY")
        i.send("BOOM")
        i.send("PAY")
        assert _wait(lambda: "shop.failed" in i.current_state_ids)
        i.stop()
        spans = exp.get_finished_spans()
        by_type = {}
        for s in spans:
            if s.name == "statechart.transition":
                by_type.setdefault(s.attributes["statechart.event.type"], s)
        assert by_type["DENY"].attributes["statechart.denied"] is True
        boom = by_type["BOOM"]
        assert any(e.name == "exception" for e in boom.events)
        assert boom.status.status_code.name == "ERROR"
        svc = next(s for s in spans if s.name == "statechart.service")
        assert svc.status.status_code.name == "ERROR"
        assert any(e.name == "exception" for e in svc.events)

    def test_traceparent_payload_header_becomes_a_link(self, machine_factory):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()
        i = SyncInterpreter(machine_factory()).use(OpenTelemetryPlugin(tracer))
        i.start()
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        i.send("DENY", headers={"traceparent": tp})
        i.send("DENY", traceparent="garbage")
        i.stop()
        spans = [
            s
            for s in exp.get_finished_spans()
            if s.name == "statechart.transition"
        ]
        linked = [s for s in spans if s.links]
        assert len(linked) == 1
        ctx = linked[0].links[0].context
        assert format(ctx.trace_id, "032x") == tp[3:35]
        assert ctx.is_remote

    def test_unknown_event_type_is_not_an_attribute_value(
        self, machine_factory
    ):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()
        i = SyncInterpreter(machine_factory()).use(
            OpenTelemetryPlugin(tracer, record_context=True)
        )
        i.start()
        i.send("USER_42_SECRET")
        i.stop()
        types = {
            s.attributes["statechart.event.type"]
            for s in exp.get_finished_spans()
        }
        assert "USER_42_SECRET" not in types and "unknown" in types
        ctx = [
            s.attributes["statechart.context"]
            for s in exp.get_finished_spans()
            if "statechart.context" in s.attributes
        ]
        assert ctx and all('"***"' in c for c in ctx)
        assert all("4111" not in c for c in ctx)

    def test_span_per_transition_adds_microsteps(self, machine_factory):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()
        i = SyncInterpreter(machine_factory()).use(
            OpenTelemetryPlugin(tracer, span_per="transition")
        )
        i.start()
        i.send("RESET")
        i.send("PAY")
        i.stop()
        micro = [
            s
            for s in exp.get_finished_spans()
            if s.name == "statechart.microstep"
        ]
        assert any(
            s.attributes["statechart.target"] == "shop.paying" for s in micro
        )
        with pytest.raises(ValueError):
            OpenTelemetryPlugin(tracer, span_per="bogus")

    def test_async_engine(self, machine_factory):
        from src.xstate_statemachine import Interpreter
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        tracer, exp = _tracer()

        async def run():
            i = Interpreter(machine_factory()).use(OpenTelemetryPlugin(tracer))
            await i.start()
            await i.send("PAY", wait=True)
            for _ in range(100):
                if "shop.paid" in i.current_state_ids:
                    break
                await asyncio.sleep(0.01)
            await i.stop()

        asyncio.run(run())
        names = [s.name for s in exp.get_finished_spans()]
        assert "statechart.service" in names
        assert names.count("statechart.transition") >= 2

    def test_agent_span_exporter(self):
        from src.xstate_statemachine.contrib.observability import (
            agent_span_exporter,
        )

        tracer, exp = _tracer()
        on_span = agent_span_exporter(tracer)
        on_span(
            {
                "kind": "model_call",
                "gen_ai.operation.name": "chat",
                "gen_ai.usage.input_tokens": 3,
                "gen_ai.response.tool_calls": ["get_weather"],
                "usage": {"x": 1},
                "agent_id": "never-an-attribute",
            }
        )
        (span,) = exp.get_finished_spans()
        assert span.name == "gen_ai.chat"
        assert span.attributes["gen_ai.usage.input_tokens"] == 3
        assert "agent_id" not in span.attributes


# =============================================================================
# Prometheus
# =============================================================================
def _scrape(reg) -> str:
    from prometheus_client import generate_latest

    return generate_latest(reg).decode()


class TestPrometheus:
    def test_every_metric_after_a_scripted_run(self, machine_factory):
        from prometheus_client import CollectorRegistry

        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
        )

        reg = CollectorRegistry()
        i = SyncInterpreter(machine_factory(charge_fails=True)).use(
            PrometheusPlugin(registry=reg)
        )
        i.start()
        i.send("DENY")
        i.send("BOOM")
        i.send("NOPE")
        i.send("PAY")
        assert _wait(lambda: "shop.failed" in i.current_state_ids)
        out = _scrape(reg)
        i.stop()
        for name in (
            "xstatemachine_transitions_total{",
            "xstatemachine_transition_duration_seconds_bucket{",
            "xstatemachine_events_received_total{",
            "xstatemachine_guard_evaluations_total{",
            "xstatemachine_action_errors_total{",
            "xstatemachine_service_duration_seconds_bucket{",
            "xstatemachine_service_errors_total{",
            "xstatemachine_active_interpreters{",
            "xstatemachine_queue_depth{",
        ):
            assert name in out, name
        # guard_errors / chain_trips have no series yet but are declared
        assert "# TYPE xstatemachine_guard_errors_total counter" in out
        assert "# TYPE xstatemachine_chain_trips_total counter" in out
        assert (
            'xstatemachine_transitions_total{event="PAY",'
            'from_state="shop.idle",machine="shop",to_state="shop.paying"}'
            in out
        )
        assert 'disposition="unhandled"' in out
        assert 'disposition="denied"' in out
        assert 'event="unknown"' in out and "NOPE" not in out
        assert 'guard="never",machine="shop",result="false"' in out
        assert 'action="explode"' in out
        assert 'service="charge"' in out
        assert 'xstatemachine_active_interpreters{machine="shop"} 1.0' in out
        after = _scrape(reg)
        assert 'xstatemachine_active_interpreters{machine="shop"} 0.0' in after

    def test_cardinality_guard_with_1000_event_names(self):
        from prometheus_client import CollectorRegistry

        from src.xstate_statemachine import SyncInterpreter, create_machine
        from src.xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
        )

        events = {f"E{n}": {} for n in range(1000)}
        m = create_machine(
            {"id": "wide", "initial": "a", "states": {"a": {"on": events}}}
        )
        reg = CollectorRegistry()
        i = SyncInterpreter(m).use(
            PrometheusPlugin(registry=reg, max_label_values=50)
        )
        i.start()
        for n in range(1000):
            i.send(f"E{n}")
        out = _scrape(reg)
        i.stop()
        series = [
            ln
            for ln in out.splitlines()
            if ln.startswith("xstatemachine_events_received_total{")
        ]
        assert len(series) <= 51
        assert any('event="other"' in s for s in series)

    def test_shared_registry_two_plugins_and_no_machine_label(
        self, machine_factory
    ):
        from prometheus_client import CollectorRegistry

        from src.xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
        )

        reg = CollectorRegistry()
        a = PrometheusPlugin(registry=reg)
        b = PrometheusPlugin(registry=reg)  # no Duplicated timeseries
        assert a.m is b.m
        reg2 = CollectorRegistry()
        PrometheusPlugin(registry=reg2, labels=())
        with pytest.raises(ValueError):
            PrometheusPlugin(registry=reg2, labels=("instance",))

    def test_queue_depth_is_polled_on_the_async_engine(self, machine_factory):
        from prometheus_client import CollectorRegistry

        from src.xstate_statemachine import Interpreter
        from src.xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
        )

        reg = CollectorRegistry()

        async def run():
            i = Interpreter(machine_factory()).use(
                PrometheusPlugin(registry=reg)
            )
            await i.start()
            await i.send("PAY", wait=True)
            text = _scrape(reg)
            await i.stop()
            return text

        out = asyncio.run(run())
        assert 'xstatemachine_queue_depth{machine="shop"}' in out
        assert "xstatemachine_transitions_total{" in out


# =============================================================================
# instrument_all
# =============================================================================
class TestInstrumentAll:
    def test_covers_interpreters_created_after_the_call_both_engines(
        self, machine_factory
    ):
        from prometheus_client import CollectorRegistry

        from src.xstate_statemachine import Interpreter, SyncInterpreter
        from src.xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
            instrument_all,
            uninstrument_all,
        )

        before = SyncInterpreter(machine_factory()).start()
        reg = CollectorRegistry()
        attached = instrument_all(prometheus=PrometheusPlugin(registry=reg))
        try:
            s = SyncInterpreter(machine_factory()).start()
            s.send("RESET")

            async def run():
                a = await Interpreter(machine_factory()).start()
                await a.send("RESET", wait=True)
                await a.stop()

            asyncio.run(run())
            s.stop()
        finally:
            uninstrument_all(attached)
        before.send("RESET")
        before.stop()
        out = _scrape(reg)
        line = next(
            ln
            for ln in out.splitlines()
            if ln.startswith("xstatemachine_events_received_total{")
            and 'event="RESET"' in ln
        )
        assert line.endswith(" 2.0")  # the pre-existing one is not counted

    def test_targets_interpreter_registry_and_discovered(
        self, machine_factory, monkeypatch
    ):
        from src.xstate_statemachine import SyncInterpreter, plugins
        from src.xstate_statemachine.contrib.observability import (
            instrument_all,
        )

        tracer, _ = _tracer()
        seen = []

        class Found:
            pass

        def fake_attach(target, *, allow=None, strict=False):
            seen.append(allow)
            f = Found()
            target.use(f)
            return [f]

        monkeypatch.setattr(plugins, "attach_discovered", fake_attach)
        from src.xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        i = SyncInterpreter(machine_factory())
        out = instrument_all(
            i,
            otel=OpenTelemetryPlugin(tracer),
            discovered=True,
            allow=["x"],
        )
        assert [type(p).__name__ for p in out] == [
            "OpenTelemetryPlugin",
            "Found",
        ]
        assert seen == [["x"]]

        class Reg:
            plugins: list = []

        r = Reg()
        r.plugins = []
        instrument_all(r, otel=OpenTelemetryPlugin(tracer), discovered=True)
        assert [type(p).__name__ for p in r.plugins] == [
            "OpenTelemetryPlugin",
            "Found",
        ]
        with pytest.raises(TypeError):
            instrument_all(object(), otel=OpenTelemetryPlugin(tracer))

    def test_true_flags_build_defaults(self):
        from src.xstate_statemachine.contrib.observability import (
            instrument_all,
            uninstrument_all,
        )

        attached = instrument_all(otel=True)
        try:
            assert type(attached[0]).__name__ == "OpenTelemetryPlugin"
        finally:
            uninstrument_all(attached)


# =============================================================================
# Hygiene helpers
# =============================================================================
def test_label_guard_and_event_label():
    from src.xstate_statemachine import create_machine
    from src.xstate_statemachine.contrib.observability import (
        LabelGuard,
        event_label,
    )

    g = LabelGuard(2)
    assert [g("d", v) for v in ("a", "b", "c", "a")] == [
        "a",
        "b",
        "other",
        "a",
    ]
    with pytest.raises(ValueError):
        LabelGuard(0)
    m = create_machine(
        {"id": "m", "initial": "a", "states": {"a": {"on": {"GO": "a"}}}}
    )
    assert event_label(m, "GO") == "GO"
    assert event_label(m, "after.100.m.a") == "after"
    assert event_label(m, "done.invoke.x:y") == "done"
    assert event_label(m, "___xstate_statemachine_init___") == "xstate.init"
    assert event_label(m, None) == "always"
    assert event_label(m, "EVIL") == "unknown"
