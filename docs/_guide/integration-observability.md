---
title: "Observability integration"
description: "OpenTelemetry spans, Prometheus metrics, structlog / loguru context and Sentry breadcrumbs for every machine -- one line with instrument_all(), telemetry-hygienic by default."
---

# Observability

This library contains failures by design: a raising action is logged and the transition still completes, a raising guard is `False`, an unhandled event is dropped. A long-lived machine should not die because one side effect had a bad day — which also means those failures are **invisible unless you look**. The `[observability]` extra is how you look: every plugin is a thin mapping over the existing hooks, attached to one interpreter with `.use()` or to every interpreter in the process with a single `instrument_all()` call at startup.

## Install

```bash
pip install "xstate-statemachine[observability]"
pip install structlog loguru sentry-sdk   # optional -- soft imports, never pinned
```

`[observability]` pins exactly two packages: `opentelemetry-api>=1.20` and `prometheus-client>=0.17`. You still configure the OpenTelemetry **SDK** (exporter, sampler) yourself — the library only talks to the API, as the OTel project recommends for libraries. structlog, loguru and sentry-sdk are detected when their plugin is constructed; a missing one raises `MissingExtraError` naming the package (`pip install structlog`). Tested versions are in the [compatibility table](#compatibility).

For a complete, runnable app -- `PrometheusPlugin` and `OpenTelemetryPlugin` over two charts in choreography with in-memory exporters, tests that no order id becomes a label, and a test suite -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

## Quick start

<!-- doc-requires: prometheus_client, opentelemetry -->
```python
from prometheus_client import CollectorRegistry, generate_latest

from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine.contrib.observability import (
    PrometheusPlugin, instrument_all, uninstrument_all,
)

machine = create_machine({
    "id": "door", "initial": "closed",
    "states": {"closed": {"on": {"OPEN": "open"}}, "open": {"on": {"CLOSE": "closed"}}},
})

registry = CollectorRegistry()
attached = instrument_all(otel=True, prometheus=PrometheusPlugin(registry=registry))

door = SyncInterpreter(machine).start()      # built AFTER the call -> instrumented
door.send("OPEN")
door.send("KNOCK")                           # undeclared -> label "unknown"
door.stop()

text = generate_latest(registry).decode()
assert 'xstatemachine_transitions_total{event="OPEN",from_state="door.closed"' in text
assert 'disposition="unhandled"' in text and "KNOCK" not in text
uninstrument_all(attached)                   # tests: leave the process as found
```

A Grafana-ready starting point:

```text
# transitions per second, by machine and event
sum by (machine, event) (rate(xstatemachine_transitions_total[5m]))
# share of events nobody handled (misrouted traffic, stale clients)
sum by (machine) (rate(xstatemachine_events_received_total{disposition="unhandled"}[5m]))
  / sum by (machine) (rate(xstatemachine_events_received_total[5m]))
# p95 event-processing latency
histogram_quantile(0.95, sum by (le, machine) (rate(xstatemachine_transition_duration_seconds_bucket[5m])))
# action failures that were contained -- alert on any
sum by (machine, action) (increase(xstatemachine_action_errors_total[15m])) > 0
```

**OTel collector note:** the plugins emit through the global `TracerProvider`. Point the SDK's OTLP exporter at your collector (`OTEL_EXPORTER_OTLP_ENDPOINT`), and let the collector do tail sampling — a busy machine emits one span per event.

## Reference

### `instrument_all(interp_or_app=None, *, otel=False, prometheus=False, structlog=False, loguru=False, sentry=False, discovered=False, allow=None)`

Each flag is `False`, `True` (a default-configured plugin) or a ready plugin instance. The target decides where they go:

| `interp_or_app` | Effect |
|:--|:--|
| `None` (default) | `plugins.register_global()` — every interpreter constructed **afterwards**: both engines, spawned/invoked children, `from_snapshot` restores. Existing interpreters are not touched. |
| an interpreter | `.use()` each plugin. |
| an object with a `plugins` list (e.g. the `[starlette]` `StatechartRegistry`) | appended; the registry attaches them to every interpreter it builds. |

`discovered=True` also attaches entry-point plugins through `plugins.attach_discovered()` ([#296](https://github.com/basiltt/xstate-statemachine/issues/296)); `allow=` narrows them by name. Returns the plugins attached. Anything else raises `TypeError`.

### `uninstrument_all(attached)`

Unregisters a global `instrument_all()` (new interpreters only).

### `OpenTelemetryPlugin(tracer=None, *, span_per="event", record_context=False, redact=())`

One span named `statechart.transition` per processed event, opened in `on_event_received` and closed in `on_event_processed` — the hook that knows the outcome:

| Attribute | Value |
|:--|:--|
| `statechart.machine_id` | the chart id (not the instance) |
| `statechart.event.type` | allow-listed event type (see [Threat model](#threat-model)) |
| `statechart.from` / `statechart.to` | sorted active leaf ids before / after |
| `statechart.changed`, `.denied`, `.deferred` | from the `Receipt` |
| `statechart.actions` | action types executed, in order |
| `statechart.context` | only with `record_context=True`, `redact()`-ed JSON |

Guard evaluations are span events (`guard_evaluated` with `guard.name`, `guard.result`). Action / guard errors, service errors and runaway-chain trips are recorded with `record_exception` and set the span status to `ERROR`. Each invoked service gets a child span `statechart.service` (`service.src`, duration). A `traceparent` in the event payload (or `payload["headers"]`) becomes a span **link** to the remote context; an invalid one is ignored. `span_per="transition"` adds a `statechart.microstep` child span per transition taken.

> 📝 There is no official OpenTelemetry semantic convention for state machines; the `statechart.*` namespace is ours.

### `agent_span_exporter(tracer=None)`

An `on_span` callable for the `[agents]` `AgentTracePlugin`: each trace record becomes a `gen_ai.<operation>` span with its `gen_ai.*` fields. `AgentTracePlugin(on_span="otel")` wires it for you.

### `PrometheusPlugin(registry=None, *, labels=("machine",), max_label_values=100, clock=None)`

| Metric | Type | Labels |
|:--|:--|:--|
| `xstatemachine_transitions_total` | counter | `machine, from_state, to_state, event` |
| `xstatemachine_transition_duration_seconds` | histogram | `machine` — received → settled |
| `xstatemachine_events_received_total` | counter | `machine, event, disposition` (`handled`, `unhandled`, `denied`, `deferred`, `dropped`, `duplicate`) |
| `xstatemachine_guard_evaluations_total` | counter | `machine, guard, result` |
| `xstatemachine_guard_errors_total` | counter | `machine, guard` |
| `xstatemachine_action_errors_total` | counter | `machine, action` |
| `xstatemachine_service_duration_seconds` | histogram | `machine, service` |
| `xstatemachine_service_errors_total` | counter | `machine, service` |
| `xstatemachine_chain_trips_total` | counter | `machine` |
| `xstatemachine_active_interpreters` | gauge | `machine` |
| `xstatemachine_queue_depth` | gauge (polled at scrape) | `machine` |

Metric objects are created once per `CollectorRegistry` and shared, so several plugins on one registry never collide. `labels=()` drops the `machine` label. `queue_depth` has no hook — it is a collector that reads `interpreter.queue_depth` from live interpreters at scrape time.

### `StructlogPlugin()` / `LoguruPlugin(logger=None)`

Bind `machine_id`, `state` (sorted leaf ids), `event` and — when the event payload carries one — `correlation_id` from `on_event_received` until `on_event_processed`, so any log line your **actions** emit carries them. structlog: through `structlog.contextvars` (keep `merge_contextvars` in your processors); loguru: `logger.contextualize()` → `record["extra"]`. Unbound afterwards.

### `SentryPlugin(level="info", *, capture_errors=False, sdk=None)`

A `statechart` breadcrumb per transition (`door.closed -> door.open (OPEN)`). With `capture_errors=True`, action / guard / service errors and chain trips are sent with `capture_exception` and `statechart.*` tags. Works with sentry-sdk 1.x and 2.x.

### `LabelGuard(max_label_values)`, `event_label(machine, event_type)`, `UNKNOWN`, `OTHER`

The hygiene primitives the plugins share, exported for your own exporters.

## Guarantees

> **What this does:** observes every hook without changing behaviour — every plugin is wrapped by the engine's `_SafePlugin`, so an exporter that raises is reported via `on_plugin_error` and the machine keeps running. `instrument_all()` covers every interpreter constructed after the call, on both engines, including children and restores. The hot path pays for `on_event_processed` only when a plugin overrides it (all of these do, by design: it carries the outcome).
>
> **What this does not do:** configure an OTel SDK or exporter; retro-instrument interpreters that already exist; guarantee delivery of telemetry (exporters are best-effort); emit OTel messaging spans for brokers (those arrive with the EDA broker adapters). Per-event overhead is measured in the [performance budgets](../production-characteristics/).
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** your own process; nothing here opens a port. The `/metrics` endpoint, if any, is yours to expose and protect.
>
> **What it exposes (X0.6 telemetry hygiene):** a metrics backend is long-retention and priced by cardinality, so label **values** come from the chart, not from traffic — an event type the machine does not declare is `unknown`, engine events collapse to their family (`after`, `done`, `error`, `xstate`), and every label dimension is capped at `max_label_values` with the overflow bucket `other` (proven with 1,000 distinct event names). **Never** labels or attributes by default: event payloads, context, interpreter ids / store keys, correlation ids. Sentry tags and breadcrumbs carry names only. `correlation_id` is bound as *log context* (per line), never as a metric label.
>
> **You must configure:** your OTel SDK and exporter; `record_context=True` only with a reviewed `redact=` list; `capture_errors=True` only if your Sentry project may receive exception messages (they can echo request data).

## Compatibility

| Package | Python | Tested in CI |
|:--|:--|:--|
| opentelemetry-api 1.20 – latest, prometheus-client 0.17 – latest | 3.9 – 3.14 | ✅ oldest on 3.9, newest on 3.13 ([compatibility](../compatibility/)) |
| structlog / loguru / sentry-sdk (soft) | 3.9 – 3.14 | ✅ latest in the `observability` cell |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[observability]"` | extra not installed | run the command |
| `MissingExtraError: … pip install structlog` | soft dependency missing | install the named package |
| No spans exported | no SDK `TracerProvider` configured | set one up before `instrument_all()` |
| An interpreter has no metrics | it was built before `instrument_all()` | call it at startup, or `.use()` the plugin |
| `event="unknown"` everywhere | events not declared in the chart | declare them in `on:` (or it is traffic you did not expect) |
| Series ending in `"other"` | `max_label_values` reached | raise it deliberately, or reduce label spread |
| structlog lines lack `machine_id` | `merge_contextvars` missing from processors | add `structlog.contextvars.merge_contextvars` |
