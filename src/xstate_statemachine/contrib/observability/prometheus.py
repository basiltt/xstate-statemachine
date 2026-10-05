# src/xstate_statemachine/contrib/observability/prometheus.py
# -----------------------------------------------------------------------------
# 📈 PrometheusPlugin -- counters, histograms and gauges (#273)
# -----------------------------------------------------------------------------
# 🏛️ Metric objects are created ONCE per `CollectorRegistry` and shared by
#    every plugin instance pointed at it, so `instrument_all()` plus a
#    hand-attached plugin never trips "Duplicated timeseries".
#
# 🔒 X0.6: every label value goes through the chart allow-list
#    (`event_label`, state ids come from the chart) AND a per-dimension
#    `LabelGuard` (`max_label_values`, overflow → ``other``). No payloads,
#    interpreter ids or correlation ids are ever labels.
#
# ⏱️ `queue_depth` has no hook (the inbox is engine-private), so it is a
#    POLLING collector: at scrape time it reads `interpreter.queue_depth`
#    from a weak set of live interpreters. Battle #273: `active_interpreters`
#    is polled the same way (count of `status == "running"`) -- a counter
#    decremented only in `on_interpreter_stop` drifted upward forever for
#    machines that finished (`done`) or failed (`error`) without `stop()`,
#    and for interpreters garbage-collected while running.
# -----------------------------------------------------------------------------
"""Prometheus metrics plugin."""

from __future__ import annotations

import threading
import time
import weakref
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple

from prometheus_client import REGISTRY, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily

from ...plugins import PluginBase
from ._hygiene import LabelGuard, event_label

__all__ = ["PrometheusPlugin", "METRIC_PREFIX"]

METRIC_PREFIX = "xstatemachine"

_METRICS: "weakref.WeakKeyDictionary[Any, Dict[bool, Dict[str, Any]]]" = (
    weakref.WeakKeyDictionary()
)
_METRICS_LOCK = threading.Lock()


class _QueueDepthCollector:
    """Scrape-time collector: ``queue_depth`` (sum) and
    ``active_interpreters`` (count of running) per machine, from a weak
    set of every interpreter that ever started under this registry."""

    def __init__(self, machine_label: bool) -> None:
        self.machine_label = machine_label
        self.interpreters: "weakref.WeakSet[Any]" = weakref.WeakSet()
        self.guard: Optional[LabelGuard] = None

    def describe(self) -> Iterator[Any]:
        yield self._family()
        yield self._active_family()

    def _family(self) -> GaugeMetricFamily:
        return GaugeMetricFamily(
            f"{METRIC_PREFIX}_queue_depth",
            "Events waiting in running interpreters' inboxes (polled).",
            labels=["machine"] if self.machine_label else [],
        )

    def _active_family(self) -> GaugeMetricFamily:
        return GaugeMetricFamily(
            f"{METRIC_PREFIX}_active_interpreters",
            "Interpreters currently running (polled at scrape time).",
            labels=["machine"] if self.machine_label else [],
        )

    def collect(self) -> Iterator[Any]:
        fam = self._family()
        act = self._active_family()
        totals: Dict[str, int] = {}
        running: Dict[str, int] = {}
        # every machine id ever seen keeps a (possibly 0) sample so a
        # dashboard sees the series drop, not vanish
        seen: Dict[str, None] = {}
        for interp in list(self.interpreters):
            try:
                key = str(interp.machine.id) if self.machine_label else ""
                seen.setdefault(key)
                if getattr(interp, "status", None) != "running":
                    continue
                running[key] = running.get(key, 0) + 1
                depth = int(interp.queue_depth)
            except Exception:  # noqa: BLE001 -- a scrape never raises
                continue
            totals[key] = totals.get(key, 0) + depth
        for key in sorted(seen):
            labels = [key] if self.machine_label else []
            fam.add_metric(labels, totals.get(key, 0))
            act.add_metric(labels, running.get(key, 0))
        yield fam
        yield act


def _build(registry: Any, machine_label: bool) -> Dict[str, Any]:
    m = ["machine"] if machine_label else []
    p = METRIC_PREFIX
    kw = {"registry": registry}
    qd = _QueueDepthCollector(machine_label)
    registry.register(qd)
    return {
        "transitions": Counter(
            f"{p}_transitions",
            "Transitions taken.",
            m + ["from_state", "to_state", "event"],
            **kw,
        ),
        "transition_duration": Histogram(
            f"{p}_transition_duration_seconds",
            "Wall time to process one event (received -> settled).",
            m,
            **kw,
        ),
        "events": Counter(
            f"{p}_events_received",
            "Events that entered the machine, by disposition.",
            m + ["event", "disposition"],
            **kw,
        ),
        "guards": Counter(
            f"{p}_guard_evaluations",
            "Guard evaluations.",
            m + ["guard", "result"],
            **kw,
        ),
        "guard_errors": Counter(
            f"{p}_guard_errors", "Guards that raised.", m + ["guard"], **kw
        ),
        "action_errors": Counter(
            f"{p}_action_errors", "Actions that raised.", m + ["action"], **kw
        ),
        "service_duration": Histogram(
            f"{p}_service_duration_seconds",
            "Invoked service duration.",
            m + ["service"],
            **kw,
        ),
        "service_errors": Counter(
            f"{p}_service_errors",
            "Invoked services that failed.",
            m + ["service"],
            **kw,
        ),
        "chain_trips": Counter(
            f"{p}_chain_trips", "Runaway-chain budget trips.", m, **kw
        ),
        "queue_depth": qd,
    }


class PrometheusPlugin(PluginBase[Any]):
    """Export state-machine metrics to a `prometheus_client` registry.

    Args:
        registry: A `CollectorRegistry` (default: the global ``REGISTRY``).
        labels: Base label set; ``("machine",)`` (default) labels every
            series with the chart id, ``()`` drops it.
        max_label_values: Cardinality cap per label dimension; the
            overflow bucket is ``other`` (X0.6).
        clock: ``() -> float`` seconds, for durations (``time.perf_counter``).
    """

    def __init__(
        self,
        registry: Any = None,
        *,
        labels: Sequence[str] = ("machine",),
        max_label_values: int = 100,
        clock: Any = None,
    ) -> None:
        unknown = set(labels) - {"machine"}
        if unknown:
            raise ValueError(f"unsupported base labels: {sorted(unknown)}")
        self.registry = registry if registry is not None else REGISTRY
        self.machine_label = "machine" in labels
        self.guard = LabelGuard(max_label_values)
        self.clock = clock or time.perf_counter
        with _METRICS_LOCK:
            per_registry = _METRICS.setdefault(self.registry, {})
            if self.machine_label not in per_registry:
                # 🔥 battle #273: two plugins with DIFFERENT base label
                #    sets on one registry cannot share metric names
                #    (`DuplicateTimeseries` on the second). Refuse with
                #    a message instead of a prometheus_client error.
                if per_registry:
                    other = next(iter(per_registry))
                    raise ValueError(
                        "PrometheusPlugin: this registry already has "
                        f"metrics with labels={('machine',) if other else ()}; "
                        "one label set per registry (pass another "
                        "CollectorRegistry)"
                    )
                per_registry[self.machine_label] = _build(
                    self.registry, self.machine_label
                )
            metrics = per_registry[self.machine_label]
        self.m = metrics
        self._lock = threading.Lock()
        self._started: Dict[int, float] = {}
        self._unhandled: Dict[int, bool] = {}
        #: (id(interp), invoke id) -> (started, owning state id)
        self._services: Dict[Tuple[int, str], Tuple[float, str]] = {}

    # -- helpers ----------------------------------------------------------
    def _base(self, interp: Any) -> Tuple[str, ...]:
        if not self.machine_label:
            return ()
        return (self.guard("machine", interp.machine.id),)

    def _l(self, dim: str, value: Any) -> str:
        return self.guard(dim, value)

    # -- lifecycle --------------------------------------------------------
    def on_interpreter_start(self, interpreter: Any) -> None:
        # the collector polls `status` at scrape time (see header)
        self.m["queue_depth"].interpreters.add(interpreter)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        self._forget(interpreter)

    def on_done(self, interpreter: Any, output: Any) -> None:
        self._forget(interpreter)

    def on_error(self, interpreter: Any, error: BaseException) -> None:
        self._forget(interpreter)

    def _forget(self, interpreter: Any) -> None:
        """Drop per-interpreter bookkeeping on any terminal status
        (battle #273: `done` / `error` reap without `on_interpreter_stop`,
        so timers for in-flight events / services were left behind)."""
        key = id(interpreter)
        with self._lock:
            self._started.pop(key, None)
            self._unhandled.pop(key, None)
            for k in [k for k in self._services if k[0] == key]:
                self._services.pop(k, None)

    # -- events -----------------------------------------------------------
    def on_event_received(self, interpreter: Any, event: Any) -> None:
        self._started[id(interpreter)] = self.clock()

    def on_unhandled_event(
        self, interpreter: Any, event: Any, active: Any, disposition: str
    ) -> None:
        self._unhandled[id(interpreter)] = True

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        key = id(interpreter)
        self._drop_cancelled_services(interpreter)
        started = self._started.pop(key, None)
        unhandled = self._unhandled.pop(key, False)
        base = self._base(interpreter)
        if started is not None:
            self.m["transition_duration"].labels(*base).observe(
                max(0.0, self.clock() - started)
            )
        if receipt.duplicate:
            disposition = "duplicate"
        elif receipt.deferred:
            disposition = "deferred"
        elif receipt.denied:
            disposition = "denied"
        elif unhandled:
            disposition = "unhandled"
        else:
            disposition = "handled"
        ev = self._l(
            "event",
            event_label(interpreter.machine, getattr(event, "type", None)),
        )
        self.m["events"].labels(*base, ev, disposition).inc()

    def on_event_dropped(
        self, interpreter: Any, event: Any, reason: str
    ) -> None:
        ev = self._l(
            "event",
            event_label(interpreter.machine, getattr(event, "type", None)),
        )
        self.m["events"].labels(*self._base(interpreter), ev, "dropped").inc()

    def on_transition(
        self, interpreter: Any, from_states: Any, to_states: Any, transition
    ) -> None:
        target = getattr(transition, "resolved_target", None)
        src = transition.source.id
        self.m["transitions"].labels(
            *self._base(interpreter),
            self._l("from_state", src),
            self._l("to_state", getattr(target, "id", src)),
            self._l(
                "event", event_label(interpreter.machine, transition.event)
            ),
        ).inc()

    # -- guards / actions / chain ------------------------------------------
    def on_guard_evaluated(
        self, interpreter: Any, guard_name: str, event: Any, result: bool
    ) -> None:
        self.m["guards"].labels(
            *self._base(interpreter),
            self._l("guard", guard_name),
            "true" if result else "false",
        ).inc()

    def on_guard_error(
        self, interpreter: Any, guard_name: str, event: Any, error: Any
    ) -> None:
        self.m["guard_errors"].labels(
            *self._base(interpreter), self._l("guard", guard_name)
        ).inc()

    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        self.m["action_errors"].labels(
            *self._base(interpreter),
            self._l("action", getattr(action, "type", action)),
        ).inc()

    def on_chain_budget_exceeded(
        self, interpreter: Any, error: BaseException, event: Any
    ) -> None:
        self.m["chain_trips"].labels(*self._base(interpreter)).inc()

    # -- services ---------------------------------------------------------
    def on_service_start(self, interpreter: Any, invocation: Any) -> None:
        owner = str(getattr(getattr(invocation, "source", None), "id", ""))
        with self._lock:
            self._services[(id(interpreter), str(invocation.id))] = (
                self.clock(),
                owner,
            )

    def _service_end(self, interpreter: Any, invocation: Any) -> None:
        with self._lock:
            entry = self._services.pop(
                (id(interpreter), str(invocation.id)), None
            )
        if entry is None:
            return
        self.m["service_duration"].labels(
            *self._base(interpreter),
            self._l("service", getattr(invocation, "src", "")),
        ).observe(max(0.0, self.clock() - entry[0]))

    def _drop_cancelled_services(self, interpreter: Any) -> None:
        """battle #273: a service whose owning state was exited is
        cancelled with no hook; drop its timer (a cancelled service is
        neither a completion nor a failure -- it is simply not observed)."""
        key = id(interpreter)
        with self._lock:
            mine = [(k, v) for k, v in self._services.items() if k[0] == key]
        if not mine:
            return
        active: set = set()
        for sid in interpreter.current_state_ids:
            parts = str(sid).split(".")
            for n in range(1, len(parts) + 1):
                active.add(".".join(parts[:n]))
        with self._lock:
            for k, (_t, owner) in mine:
                if owner and owner not in active:
                    self._services.pop(k, None)

    def on_service_done(
        self, interpreter: Any, invocation: Any, result: Any
    ) -> None:
        self._service_end(interpreter, invocation)

    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._service_end(interpreter, invocation)
        self.m["service_errors"].labels(
            *self._base(interpreter),
            self._l("service", getattr(invocation, "src", "")),
        ).inc()
