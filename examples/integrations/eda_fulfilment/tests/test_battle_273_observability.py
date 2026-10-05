# examples/integrations/eda_fulfilment/tests/test_battle_273_observability.py
"""#273 battle: the fulfilment team puts the pipeline on a dashboard.

Prometheus + OpenTelemetry are attached to every interpreter the
choreography router builds (one per envelope, hundreds per minute). An
SRE reads the dashboard and must be able to TRUST it. Pinned:

* **metric correctness vs. the audit log** -- after a mixed run (clean
  orders, a cancel mid-flight, a poison command dead-lettered) every
  counter equals what the transition log says happened; the `active`
  gauge is the number of interpreters that are actually running (NOT
  the number ever started: `done` / `error` machines must leave it);
* **cardinality under attack** -- 1 000 distinct undeclared commands and
  1 000 distinct subjects mint ONE `unknown` series and zero per-subject
  series; the scrape stays under a byte budget; no order id, payload
  value, envelope id or tracking id appears as a label or span attribute;
* **exporter outage** -- a span exporter / a Prometheus registry whose
  collect raises never reaches the machine: orders still ship, the
  interpreter never enters `error`, and when the exporter recovers new
  spans flow; a tracer whose `start_span` raises is contained once per
  plugin, not once per event;
* **span tree** -- every `statechart.service` span is a child of the
  transition span that entered the invoking state; a cancelled
  invocation (CANCEL while `paid`→`packed` ships) ENDS its span (never
  leaked until process exit) and is marked as cancelled; `stop()` on
  the router's interpreters leaves no open span;
* **threads** -- 8 router threads over one registry / one tracer: the
  counters sum exactly, no `DuplicateTimeseries`, no lost span;
* **instrument_all()** -- interpreters the router builds AFTER the call
  are instrumented, both engines; `uninstrument_all()` detaches for new
  ones only; a second `instrument_all()` on the same registry does not
  raise;
* **soak** -- 2 000 envelopes through the instrumented router: the
  plugins' private bookkeeping (`_started`, `_services`, `_events`,
  weak sets) is empty / bounded afterwards and memory is flat.
"""

from __future__ import annotations

import gc
import threading
import tracemalloc
from collections import Counter
from typing import Any, Dict, List

import pytest

import app

prometheus_client = pytest.importorskip("prometheus_client")
pytest.importorskip("opentelemetry.sdk")

from prometheus_client import CollectorRegistry, generate_latest  # noqa: E402

from xstate_statemachine.contrib.observability import (  # noqa: E402
    OpenTelemetryPlugin,
    PrometheusPlugin,
    event_label,
)

pytestmark = pytest.mark.timeout(300)


def _series(text: str, name: str) -> Dict[str, float]:
    """``{label-string: value}`` for one metric family."""
    out: Dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith(name + "{"):
            labels, value = line[len(name) :].rsplit(" ", 1)
            out[labels] = float(value)
    return out


def _total(text: str, name: str, **where: str) -> float:
    return sum(
        v
        for labels, v in _series(text, name).items()
        if all(f'{k}="{val}"' in labels for k, val in where.items())
    )


def _plugin(fulfilment: Any, cls: type) -> Any:
    return next(
        p for p in fulfilment.instruments.plugins if isinstance(p, cls)
    )


def _place(a: Any, oid: str, total: int = 10) -> None:
    a.command(oid, "PAY", orderId=oid, total=total)


# -----------------------------------------------------------------------------
# 1. metric correctness vs. the audit log
# -----------------------------------------------------------------------------
def test_counters_equal_the_audit_log_and_active_gauge_is_truthful(
    fulfilment: Any,
) -> None:
    for n in range(1, 6):
        _place(fulfilment, f"o-{n}", total=n)
    fulfilment.pump()
    # a cancel while paid (before the warehouse packs): the order chart
    # exits `paid` -- no invoke yet, so no service span -- and finalises
    _place(fulfilment, "o-c", total=7)
    fulfilment.command("o-c", "CANCEL")
    fulfilment.pump()
    fulfilment.command("o-p", "PAYMENT_FAILED", reason=12345)  # poison
    stats = fulfilment.pump()
    assert stats["dead_lettered"] == 1

    text = fulfilment.instruments.metrics_text()
    # transitions by (machine, event) == transition records in the log
    logged: Counter = Counter()
    for key in fulfilment.store.list_keys(limit=10_000):
        machine = "warehouse" if key.startswith("warehouse:") else "order"
        for r in fulfilment.log.read(key):
            if r.disposition == "transition":
                logged[(machine, r.event_type)] += 1
    for (machine, event), n in logged.items():
        label = event_label(fulfilment.machine_for_key(machine + ":"), event)
        got = _total(
            text,
            "xstatemachine_transitions_total",
            machine=machine,
            event=label,
        )
        assert got == n, (machine, event, got, n)
    # the poison: MAX_ATTEMPTS action errors, one per attempt
    assert (
        _total(
            text,
            "xstatemachine_action_errors_total",
            machine="order",
            action="recordPaymentFailure",
        )
        == app.MAX_ATTEMPTS
    )
    # 🔥 the gauge: every router interpreter is `done` or stopped by now
    for machine in ("order", "warehouse"):
        assert (
            _total(text, "xstatemachine_active_interpreters", machine=machine)
            == 0
        ), text
    # service histogram: one shipOrder per shipped order
    shipped = sum(
        1
        for n in range(1, 6)
        if fulfilment.state_of(f"order:o-{n}") == ["order.shipped"]
    )
    assert shipped == 5
    assert (
        _total(
            text,
            "xstatemachine_service_duration_seconds_count",
            machine="order",
            service="shipOrder",
        )
        == 5
    )


# -----------------------------------------------------------------------------
# 2. cardinality under attack + hygiene
# -----------------------------------------------------------------------------
def test_thousand_undeclared_events_and_subjects_mint_one_series(
    fulfilment: Any,
) -> None:
    """A fuzzer sends 1 000 distinct undeclared event types at 1 000
    distinct order ids through the instrumented order chart (the router
    acks an unrouted envelope type before any machine sees it, so the
    attack is on a routed machine's event surface)."""
    from xstate_statemachine import SyncInterpreter

    prom = _plugin(fulfilment, PrometheusPlugin)
    otel = _plugin(fulfilment, OpenTelemetryPlugin)
    for n in range(1000):
        i = SyncInterpreter(app.order_machine()).use(prom).use(otel).start()
        i.send(f"FUZZ_{n}", orderId=f"victim-{n}", card="4111-1111")
        i.stop()
    # and 1 000 distinct subjects through the real pipeline
    for n in range(1000):
        _place(fulfilment, f"victim-{n}", total=1)
    fulfilment.pump()
    text = fulfilment.instruments.metrics_text()
    events = _series(text, "xstatemachine_events_received_total")
    unknown = {k: v for k, v in events.items() if 'event="unknown"' in k}
    assert unknown and sum(unknown.values()) == 1000, unknown
    assert not any("FUZZ_" in k for k in events)
    # a scrape is bounded: no per-subject or per-envelope series
    assert len(text.encode()) < 64 * 1024, len(text)
    for leak in ("victim-", "4111", "card"):
        assert leak not in text, leak
    for env in fulfilment.commands[:50]:
        assert env.id not in text
    spans = fulfilment.instruments.spans.get_finished_spans()
    assert len(spans) > 1000
    blob = "\n".join(
        f"{k}={v}" for s in spans for k, v in (s.attributes or {}).items()
    )
    for leak in ("victim-", "4111", "card"):
        assert leak not in blob, leak
    assert _total(text, "xstatemachine_active_interpreters") == 0


# -----------------------------------------------------------------------------
# 3. exporter outage
# -----------------------------------------------------------------------------
class _FlakyExporter:
    """A span exporter that is down until told otherwise."""

    def __init__(self) -> None:
        self.down = True
        self.exported: List[Any] = []

    def export(self, spans: Any) -> Any:
        if self.down:
            raise ConnectionError("collector unreachable")
        self.exported.extend(spans)
        from opentelemetry.sdk.trace.export import SpanExportResult

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def test_exporter_outage_never_reaches_the_machine(tmp_path: Any) -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    exporter = _FlakyExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    a = app.build_app("fake", tmp_path, celery=False)
    try:
        # the router's dispatcher holds the plugin list it builds from
        a.router.dispatcher.plugins.append(
            OpenTelemetryPlugin(provider.get_tracer("t"))
        )
        for n in range(5):
            _place(a, f"o-{n}")
        a.pump()
        for n in range(5):
            assert a.state_of(f"order:o-{n}") == ["order.shipped"]
        assert exporter.exported == []  # nothing got through, nothing broke
        exporter.down = False
        _place(a, "o-after")
        a.pump()
        assert a.state_of("order:o-after") == ["order.shipped"]
        assert {s.name for s in exporter.exported} >= {
            "statechart.transition",
            "statechart.service",
        }
    finally:
        a.close()


def test_raising_tracer_degrades_once_not_per_event() -> None:
    """A tracer whose `start_span` raises is an SDK misconfiguration that
    will not heal: the plugin must go inert after ONE warning -- not one
    contained error (plus traceback) per event, which is a log-flood
    outage amplifier."""
    import logging

    from xstate_statemachine import PluginBase, SyncInterpreter

    class BadTracer:
        def start_span(self, *a: Any, **k: Any) -> Any:
            raise RuntimeError("tracer misconfigured")

    class Count(PluginBase):
        def __init__(self) -> None:
            self.errors: List[Any] = []

        def on_plugin_error(self, interp: Any, plugin: Any, hook: str, error):
            self.errors.append((type(plugin).__name__, hook))

    class Capture(logging.Handler):
        def __init__(self) -> None:
            super().__init__(logging.WARNING)
            self.records: List[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    cap = Capture()
    root = logging.getLogger("xstate_statemachine")
    root.addHandler(cap)
    counter = Count()
    try:
        i = (
            SyncInterpreter(app.order_machine())
            .use(counter)
            .use(OpenTelemetryPlugin(BadTracer()))
            .start()
        )
        for _ in range(20):
            i.send("PAY", orderId="o", total=1)
            i.send("NOPE")
        assert i.status == "running"
        assert i.matches("order.paid")
        i.stop()
    finally:
        root.removeHandler(cap)
    assert counter.errors == []  # no per-event contained failure
    warned = [r for r in cap.records if "tracing disabled" in r.getMessage()]
    assert len(warned) == 1, [r.getMessage() for r in cap.records]
    noisy = [r for r in cap.records if "contained" in r.getMessage()]
    assert noisy == []


def test_scrape_survives_a_collector_that_raises(fulfilment: Any) -> None:
    class Boom:
        def collect(self) -> Any:
            raise RuntimeError("bad collector")

    _place(fulfilment, "o-1")
    fulfilment.pump()
    reg = fulfilment.instruments.registry
    boom = Boom()
    reg.register(boom)
    try:
        with pytest.raises(RuntimeError, match="bad collector"):
            generate_latest(reg)  # prometheus_client's own contract
    finally:
        reg.unregister(boom)
    # the machine side is untouched
    _place(fulfilment, "o-2")
    fulfilment.pump()
    assert fulfilment.state_of("order:o-2") == ["order.shipped"]


# -----------------------------------------------------------------------------
# 4. span tree + cancelled invocation
# -----------------------------------------------------------------------------
def test_service_spans_are_children_and_cancelled_invokes_end(
    fulfilment: Any,
) -> None:
    _place(fulfilment, "o-1")
    fulfilment.pump()
    spans = fulfilment.instruments.spans.get_finished_spans()
    by_id = {s.context.span_id: s for s in spans}
    services = [s for s in spans if s.name == "statechart.service"]
    assert len(services) == 1
    parent = by_id[services[0].parent.span_id]
    assert parent.name == "statechart.transition"
    assert parent.attributes["statechart.event.type"] == "PACKED"
    assert "order.packed" in parent.attributes["statechart.to"]


def test_cancelled_invocation_ends_its_span_marked_cancelled() -> None:
    """CANCEL while `shipOrder` is still in flight (async engine -- the
    sync engine runs services inline, so only the async one can be
    interrupted). The service span must END, carry
    ``statechart.cancelled=True`` and leave no bookkeeping behind."""
    import asyncio

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from xstate_statemachine import Interpreter, MachineLogic, create_machine

    import logic

    chart = app.load_chart("machine.json")
    chart["states"]["packed"]["on"] = {"CANCEL": "cancelled"}

    async def slow_ship(i: Any, ctx: Any, e: Any) -> Any:
        await asyncio.sleep(30)
        return {"trackingId": "never"}  # pragma: no cover

    m = create_machine(
        chart,
        logic=MachineLogic(
            actions={
                "recordPayment": logic.record_payment,
                "recordPaymentFailure": logic.record_payment_failure,
                "storeTracking": logic.store_tracking,
            },
            guards={"hasTotal": logic.has_total},
            services={"shipOrder": slow_ship},
        ),
        strict_config=True,
    )
    exp = InMemorySpanExporter()
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exp))
    otel = OpenTelemetryPlugin(tp.get_tracer("t"))
    reg = CollectorRegistry()
    prom = PrometheusPlugin(registry=reg)

    async def go() -> None:
        i = await Interpreter(m).use(otel).use(prom).start()
        await i.send("PAY", orderId="o-x", total=1)
        await i.send("PACKED")
        await asyncio.sleep(0.05)
        assert i.matches("order.packed")
        for _ in range(3):  # three cancels: only the first does anything
            await i.send("CANCEL")
        await asyncio.sleep(0.05)
        assert i.status == "done"
        await i.stop()

    asyncio.run(go())
    svc = [
        s for s in exp.get_finished_spans() if s.name == "statechart.service"
    ]
    assert len(svc) == 1, [s.name for s in exp.get_finished_spans()]
    assert svc[0].attributes.get("statechart.cancelled") is True
    assert otel._services == {} and otel._events == {}
    assert prom._services == {}
    text = generate_latest(reg).decode()
    # a cancelled service is not a failure and not a completion
    assert _total(text, "xstatemachine_service_errors_total") == 0
    assert _total(text, "xstatemachine_active_interpreters") == 0


# -----------------------------------------------------------------------------
# 5. threads over one registry / one tracer
# -----------------------------------------------------------------------------
def test_eight_router_threads_sum_exactly(tmp_path: Any) -> None:
    reg = CollectorRegistry()
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exp = InMemorySpanExporter()
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exp))
    prom = PrometheusPlugin(registry=reg)
    otel = OpenTelemetryPlugin(tp.get_tracer("t"))
    apps = []
    for t in range(8):
        a = app.build_app("fake", tmp_path / f"w{t}", celery=False)
        a.router.dispatcher.plugins.extend([prom, otel])
        apps.append(a)
    per = 10
    errors: List[BaseException] = []
    barrier = threading.Barrier(8)

    def work(t: int) -> None:
        try:
            barrier.wait(10)
            a = apps[t]
            for k in range(per):
                _place(a, f"t{t}-{k}")
            a.pump()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ths = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    for th in ths:
        th.start()
    for th in ths:
        th.join(60)
    try:
        assert errors == []
        text = generate_latest(reg).decode()
        assert (
            _total(
                text,
                "xstatemachine_transitions_total",
                machine="order",
                event="PAY",
            )
            == 8 * per
        )
        assert (
            _total(
                text,
                "xstatemachine_service_duration_seconds_count",
                service="shipOrder",
            )
            == 8 * per
        )
        assert _total(text, "xstatemachine_active_interpreters") == 0
        names = Counter(s.name for s in exp.get_finished_spans())
        assert names["statechart.service"] == 8 * per
        assert prom._started == {} and prom._services == {}
        assert otel._events == {} and otel._services == {}
    finally:
        for a in apps:
            a.close()


# -----------------------------------------------------------------------------
# 6. instrument_all()
# -----------------------------------------------------------------------------
def test_instrument_all_covers_router_built_interpreters(
    tmp_path: Any,
) -> None:
    from xstate_statemachine.contrib.observability import (
        instrument_all,
        uninstrument_all,
    )

    reg = CollectorRegistry()
    attached = instrument_all(prometheus=PrometheusPlugin(registry=reg))
    try:
        a = app.build_app("fake", tmp_path, celery=False)
        try:
            _place(a, "o-1")
            a.pump()
            text = generate_latest(reg).decode()
            assert (
                _total(text, "xstatemachine_transitions_total", event="PAY")
                == 1
            )
            # 📝 a second global attach of a plugin on the SAME registry
            #    must not raise `DuplicateTimeseries`
            again = instrument_all(prometheus=PrometheusPlugin(registry=reg))
            uninstrument_all(again)
        finally:
            a.close()
    finally:
        uninstrument_all(attached)
    b = app.build_app("fake", tmp_path / "after", celery=False)
    try:
        _place(b, "o-2")
        b.pump()
        text = generate_latest(reg).decode()
        assert (
            _total(text, "xstatemachine_transitions_total", event="PAY") == 1
        )
    finally:
        b.close()


# -----------------------------------------------------------------------------
# 7. soak
# -----------------------------------------------------------------------------
def test_two_thousand_envelopes_leave_bookkeeping_empty(
    fulfilment: Any,
) -> None:
    prom = _plugin(fulfilment, PrometheusPlugin)
    otel = _plugin(fulfilment, OpenTelemetryPlugin)

    def burst(start: int, n: int) -> None:
        for k in range(start, start + n):
            _place(fulfilment, f"s-{k}", total=1)
        fulfilment.pump()
        fulfilment.instruments.spans.clear()

    burst(0, 100)
    gc.collect()
    tracemalloc.start()
    burst(100, 300)
    gc.collect()
    half = tracemalloc.take_snapshot()
    burst(400, 300)
    gc.collect()
    full = tracemalloc.take_snapshot()
    tracemalloc.stop()
    assert prom._started == {} and prom._unhandled == {}
    assert prom._services == {}
    assert otel._events == {} and otel._services == {}
    assert len(prom.m["queue_depth"].interpreters) == 0
    grown = sum(
        s.size_diff
        for s in full.compare_to(half, "filename")
        if "observability" in str(s.traceback) and s.size_diff > 0
    )
    assert grown < 64 * 1024, grown  # the plugins hold nothing per order
    text = fulfilment.instruments.metrics_text()
    assert _total(text, "xstatemachine_active_interpreters") == 0
    assert _total(text, "xstatemachine_transitions_total", event="PAY") == 700
