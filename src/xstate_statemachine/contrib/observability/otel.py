# src/xstate_statemachine/contrib/observability/otel.py
# -----------------------------------------------------------------------------
# 🔭 OpenTelemetryPlugin -- one span per processed event (#273)
# -----------------------------------------------------------------------------
# 🏛️ The per-event span opens in `on_event_received` and closes in
#    `on_event_processed` (#304), the one hook that knows the OUTCOME
#    (changed / denied / deferred / error). Guard evaluations become span
#    events; action/guard/service errors and chain trips are recorded with
#    `record_exception`; each invoked service gets a child span.
#
# 📝 There is no official OTel semantic convention for state machines;
#    the `statechart.*` attribute namespace is ours and documented in
#    docs/_guide/integration-observability.md.
#
# 🔒 X0.6: no payloads, no instance keys (`interpreter.id`), no correlation
#    ids as attributes by default. `statechart.machine_id` is the CHART id.
#    Event types pass through the chart allow-list (`unknown` fallback).
#    `record_context=True` adds a `redact()`-ed JSON context attribute.
# -----------------------------------------------------------------------------
"""OpenTelemetry tracing plugin."""

from __future__ import annotations

import json
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from opentelemetry import trace
from opentelemetry.trace import Link, Status, StatusCode

from ...plugins import DEFAULT_REDACT_KEYS, PluginBase, redact
from ._hygiene import event_label

__all__ = ["OpenTelemetryPlugin", "agent_span_exporter", "TRACER_NAME"]

#: Instrumentation scope name used when no tracer is passed.
TRACER_NAME = "xstate_statemachine"

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def _parse_traceparent(value: Any) -> Optional[trace.SpanContext]:
    """W3C ``traceparent`` → a remote `SpanContext`, or ``None``."""
    if not isinstance(value, str):
        return None
    m = _TRACEPARENT.match(value.strip().lower())
    if not m:
        return None
    trace_id, span_id = int(m.group(1), 16), int(m.group(2), 16)
    if trace_id == 0 or span_id == 0:
        return None
    return trace.SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=True,
        trace_flags=trace.TraceFlags(int(m.group(3), 16)),
    )


def _incoming_traceparent(event: Any) -> Optional[str]:
    """``traceparent`` from the payload or ``payload["headers"]``."""
    payload = getattr(event, "payload", None)
    if not isinstance(payload, dict):
        return None
    if "traceparent" in payload:
        return payload.get("traceparent")
    headers = payload.get("headers")
    if isinstance(headers, dict):
        return headers.get("traceparent")
    return None


def _leaf_ids(states: Any) -> List[str]:
    return sorted(str(getattr(s, "id", s)) for s in states or ())


class OpenTelemetryPlugin(PluginBase[Any]):
    """Emit OpenTelemetry spans for event processing and services.

    Args:
        tracer: A `Tracer`; defaults to
            ``trace.get_tracer("xstate_statemachine")`` (the global
            provider, so configure the SDK first).
        span_per: ``"event"`` (default) -- one ``statechart.transition``
            span per processed event; ``"transition"`` -- the same, plus
            a ``statechart.microstep`` child span per transition taken.
        record_context: Add ``statechart.context`` (``redact()``-ed JSON)
            to each event span. Off by default (X0.6).
        redact: Extra key substrings to redact, on top of the defaults.
    """

    def __init__(
        self,
        tracer: Any = None,
        *,
        span_per: str = "event",
        record_context: bool = False,
        redact: Sequence[str] = (),
    ) -> None:
        if span_per not in ("event", "transition"):
            raise ValueError(
                f"span_per must be 'event' or 'transition', got {span_per!r}"
            )
        self.tracer = tracer or trace.get_tracer(TRACER_NAME)
        self.span_per = span_per
        self.record_context = record_context
        self.redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS + tuple(
            k.lower() for k in redact
        )
        self._lock = threading.Lock()
        #: id(interp) -> stack of (event, span, actions)
        self._events: Dict[int, List[Tuple[Any, Any, List[str]]]] = {}
        #: (id(interp), invoke id) -> span
        self._services: Dict[Tuple[int, str], Any] = {}

    # -- helpers ----------------------------------------------------------
    def _current(self, interp: Any) -> Optional[Tuple[Any, Any, List[str]]]:
        stack = self._events.get(id(interp))
        return stack[-1] if stack else None

    def _record_error(self, interp: Any, error: BaseException, **attrs: Any):
        cur = self._current(interp)
        if cur is None:
            return
        span = cur[1]
        span.record_exception(error, attributes=attrs or None)
        span.set_status(Status(StatusCode.ERROR, type(error).__name__))

    # -- event span -------------------------------------------------------
    def on_event_received(self, interpreter: Any, event: Any) -> None:
        machine = interpreter.machine
        links = []
        ctx = _parse_traceparent(_incoming_traceparent(event))
        if ctx is not None:
            links.append(Link(ctx, {"statechart.link": "traceparent"}))
        span = self.tracer.start_span(
            "statechart.transition",
            links=links,
            attributes={
                "statechart.machine_id": str(machine.id),
                "statechart.event.type": event_label(
                    machine, getattr(event, "type", None)
                ),
                "statechart.from": _leaf_ids(interpreter.current_state_ids),
            },
        )
        with self._lock:
            self._events.setdefault(id(interpreter), []).append(
                (event, span, [])
            )

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        cur = self._current(interpreter)
        if cur is not None:
            cur[2].append(str(getattr(action, "type", action)))

    def on_guard_evaluated(
        self, interpreter: Any, guard_name: str, event: Any, result: bool
    ) -> None:
        cur = self._current(interpreter)
        if cur is not None:
            cur[1].add_event(
                "guard_evaluated",
                {"guard.name": str(guard_name), "guard.result": bool(result)},
            )

    def on_transition(
        self, interpreter: Any, from_states: Any, to_states: Any, transition
    ) -> None:
        if self.span_per != "transition":
            return
        cur = self._current(interpreter)
        parent = cur[1] if cur is not None else None
        ctx = trace.set_span_in_context(parent) if parent else None
        target = getattr(transition, "resolved_target", None)
        span = self.tracer.start_span(
            "statechart.microstep",
            context=ctx,
            attributes={
                "statechart.machine_id": str(interpreter.machine.id),
                "statechart.source": str(transition.source.id),
                "statechart.target": str(
                    getattr(target, "id", transition.source.id)
                ),
            },
        )
        span.end()

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            stack = self._events.get(id(interpreter))
            if not stack:
                return
            idx = next(
                (
                    i
                    for i in range(len(stack) - 1, -1, -1)
                    if stack[i][0] is event
                ),
                len(stack) - 1,
            )
            _, span, actions = stack.pop(idx)
            if not stack:
                self._events.pop(id(interpreter), None)
        span.set_attribute("statechart.to", sorted(receipt.state_ids))
        span.set_attribute("statechart.changed", bool(receipt.changed))
        span.set_attribute("statechart.denied", bool(receipt.denied))
        span.set_attribute("statechart.deferred", bool(receipt.deferred))
        span.set_attribute("statechart.actions", actions)
        if self.record_context:
            span.set_attribute(
                "statechart.context",
                json.dumps(
                    redact(interpreter.context, self.redact_keys),
                    default=str,
                    sort_keys=True,
                ),
            )
        if receipt.error is not None:
            span.record_exception(receipt.error)
            span.set_status(
                Status(StatusCode.ERROR, type(receipt.error).__name__)
            )
        span.end()

    # -- errors -----------------------------------------------------------
    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        self._record_error(
            interpreter,
            error,
            **{"statechart.action": str(getattr(action, "type", action))},
        )

    def on_guard_error(
        self, interpreter: Any, guard_name: str, event: Any, error
    ) -> None:
        self._record_error(
            interpreter, error, **{"statechart.guard": str(guard_name)}
        )

    def on_chain_budget_exceeded(
        self, interpreter: Any, error: BaseException, event: Any
    ) -> None:
        self._record_error(interpreter, error)

    # -- services ---------------------------------------------------------
    def on_service_start(self, interpreter: Any, invocation: Any) -> None:
        cur = self._current(interpreter)
        ctx = trace.set_span_in_context(cur[1]) if cur is not None else None
        span = self.tracer.start_span(
            "statechart.service",
            context=ctx,
            attributes={
                "statechart.machine_id": str(interpreter.machine.id),
                "service.src": str(getattr(invocation, "src", "")),
            },
        )
        with self._lock:
            self._services[(id(interpreter), str(invocation.id))] = span

    def _end_service(self, interpreter: Any, invocation: Any, error=None):
        with self._lock:
            span = self._services.pop(
                (id(interpreter), str(invocation.id)), None
            )
        if span is None:
            return
        if error is not None:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, type(error).__name__))
        span.end()

    def on_service_done(
        self, interpreter: Any, invocation: Any, result: Any
    ) -> None:
        self._end_service(interpreter, invocation)

    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._end_service(interpreter, invocation, error)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        """End anything still open so no span leaks past the actor."""
        with self._lock:
            stack = self._events.pop(id(interpreter), [])
            services = [k for k in self._services if k[0] == id(interpreter)]
            spans = [self._services.pop(k) for k in services]
        for _, span, _a in stack:
            span.end()
        for span in spans:
            span.end()


def agent_span_exporter(
    tracer: Any = None,
) -> Callable[[Dict[str, Any]], None]:
    """An ``on_span`` callable for `AgentTracePlugin` (``[agents]``).

    Each agent trace record becomes one OpenTelemetry span named
    ``gen_ai.<operation>`` carrying the record's ``gen_ai.*`` fields
    (token counts, model, tool name) as attributes. Content fields exist
    only when the tracer was built with ``record_content=True`` and are
    already ``redact()``-ed there. Pass it as
    ``AgentTracePlugin(on_span=agent_span_exporter())`` or simply
    ``AgentTracePlugin(on_span="otel")``.
    """
    tr = tracer or trace.get_tracer(TRACER_NAME)

    def _on_span(record: Dict[str, Any]) -> None:
        attrs: Dict[str, Any] = {}
        for key, value in record.items():
            if key.startswith("gen_ai.") or key in ("kind", "cost_usd"):
                if isinstance(value, (str, bool, int, float)):
                    attrs[key] = value
                elif isinstance(value, list) and all(
                    isinstance(v, str) for v in value
                ):
                    attrs[key] = value
                elif value is not None:
                    attrs[key] = json.dumps(value, default=str)
        name = f"gen_ai.{record.get('gen_ai.operation.name', 'step')}"
        tr.start_span(name, attributes=attrs).end()

    return _on_span
