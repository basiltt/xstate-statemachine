# src/xstate_statemachine/contrib/observability/__init__.py
# -----------------------------------------------------------------------------
# 🔭 [observability] -- OpenTelemetry, Prometheus, structured logs, Sentry
#    (#273, B6)
# -----------------------------------------------------------------------------
# 🏛️ Every plugin here is a thin mapping over the existing hooks. Failures
#    are contained by design in this library, which makes them invisible
#    unless you look -- these plugins are how you look.
#
# 📝 The extra pins exactly two packages: `opentelemetry-api>=1.20` and
#    `prometheus-client>=0.17`. structlog / loguru / sentry-sdk are SOFT
#    imports: detected when their plugin is constructed, never pinned, and
#    a missing one raises `MissingExtraError` naming the package itself.
#
# 🔒 X0.6 telemetry hygiene: see `_hygiene.py` and
#    docs/_guide/integration-observability.md#threat-model.
# -----------------------------------------------------------------------------
"""Observability plugins.

Install with ``pip install "xstate-statemachine[observability]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("observability", "opentelemetry", "prometheus_client")

from ._hygiene import OTHER, UNKNOWN, LabelGuard, event_label  # noqa: E402
from ._instrument import instrument_all, uninstrument_all  # noqa: E402
from .otel import OpenTelemetryPlugin, agent_span_exporter  # noqa: E402
from .prometheus import PrometheusPlugin  # noqa: E402

__all__ = [
    "LabelGuard",
    "OTHER",
    "OpenTelemetryPlugin",
    "PrometheusPlugin",
    "UNKNOWN",
    "agent_span_exporter",
    "event_label",
    "instrument_all",
    "uninstrument_all",
]
