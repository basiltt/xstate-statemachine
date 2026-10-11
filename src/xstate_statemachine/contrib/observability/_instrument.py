# src/xstate_statemachine/contrib/observability/_instrument.py
# -----------------------------------------------------------------------------
# 🧷 instrument_all() -- one line at startup instruments every interpreter
# -----------------------------------------------------------------------------
# 🏛️ Three targets, one call:
#      * nothing      → `plugins.register_global` (#305): every interpreter
#                       constructed AFTER the call, both engines, children
#                       and `from_snapshot` restores included;
#      * interpreter  → ``interp.use(plugin)`` for each;
#      * registry/app → anything with a ``plugins`` list (the `[starlette]`
#                       `StatechartRegistry`, `persisted()` callers' lists)
#                       gets the plugins appended.
#    ``discovered=True`` also attaches the `xstate_statemachine.plugins`
#    entry points via `plugins.attach_discovered` (#296).
# -----------------------------------------------------------------------------
"""`instrument_all` / `uninstrument_all`."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from ... import plugins as _plugins

__all__ = ["instrument_all", "uninstrument_all"]


class _Collector:
    """Quacks like an interpreter for `attach_discovered`: collects."""

    def __init__(self) -> None:
        self.collected: List[Any] = []

    def use(self, plugin: Any) -> "_Collector":
        self.collected.append(plugin)
        return self


def _use(interp: Any, plugin: Any) -> None:
    """``.use()`` *plugin*; on an ALREADY-running interpreter also replay
    ``on_interpreter_start`` (battle #273-b) -- otherwise a plugin that
    registers the interpreter there (Prometheus' polled gauges) never
    sees it. Dispatched through the engine's own `_SafePlugin` wrapper.

    An instance already attached (e.g. via the global registry) is
    skipped here so `on_interpreter_start` is not replayed for it
    (`use()` itself dedupes by identity since the #273 battle)."""
    attached = getattr(interp, "_plugins", ())
    if any(getattr(p, "wrapped", p) is plugin for p in attached):
        return
    interp.use(plugin)
    if getattr(interp, "status", None) == "running":
        interp._plugins[-1].on_interpreter_start(interp)


def _build(
    *,
    otel: Any,
    prometheus: Any,
    structlog: Any,
    loguru: Any,
    sentry: Any,
) -> List[Any]:
    out: List[Any] = []
    if otel:
        from .otel import OpenTelemetryPlugin

        out.append(otel if otel is not True else OpenTelemetryPlugin())
    if prometheus:
        from .prometheus import PrometheusPlugin

        out.append(
            prometheus if prometheus is not True else PrometheusPlugin()
        )
    if structlog:
        from .logs import StructlogPlugin

        out.append(structlog if structlog is not True else StructlogPlugin())
    if loguru:
        from .logs import LoguruPlugin

        out.append(loguru if loguru is not True else LoguruPlugin())
    if sentry:
        from .sentry import SentryPlugin

        out.append(sentry if sentry is not True else SentryPlugin())
    return out


def instrument_all(
    interp_or_app: Any = None,
    *,
    otel: Any = False,
    prometheus: Any = False,
    structlog: Any = False,
    loguru: Any = False,
    sentry: Any = False,
    discovered: bool = False,
    allow: Optional[Iterable[str]] = None,
) -> List[Any]:
    """Attach observability plugins everywhere with one call.

    Each flag is ``False`` (skip), ``True`` (a default-configured plugin)
    or a ready plugin instance (``prometheus=PrometheusPlugin(registry=r)``).

    Args:
        interp_or_app: ``None`` → the global registry (every interpreter
            built from now on); an interpreter → ``.use()``; an object
            with a ``plugins`` list (e.g. `StatechartRegistry`) → appended.
        discovered: Also attach entry-point plugins
            (``plugins.attach_discovered``); *allow* narrows them by name.

    Returns:
        The plugin instances attached, in order -- keep them to pass to
        `uninstrument_all` in test teardown.
    """
    attached = _build(
        otel=otel,
        prometheus=prometheus,
        structlog=structlog,
        loguru=loguru,
        sentry=sentry,
    )
    if discovered:
        if interp_or_app is not None and hasattr(interp_or_app, "use"):
            found = _plugins.attach_discovered(interp_or_app, allow=allow)
            for p in attached:
                _use(interp_or_app, p)
            return attached + found
        collector = _Collector()
        _plugins.attach_discovered(collector, allow=allow)
        attached += collector.collected
    if interp_or_app is None:
        for p in attached:
            _plugins.register_global(p)
    elif hasattr(interp_or_app, "use"):
        for p in attached:
            _use(interp_or_app, p)
    elif isinstance(getattr(interp_or_app, "plugins", None), list):
        interp_or_app.plugins.extend(attached)
    else:
        raise TypeError(
            "instrument_all() takes None, an interpreter (with .use()) or "
            "an object with a `plugins` list; got "
            f"{type(interp_or_app).__name__}"
        )
    return attached


def uninstrument_all(attached: Iterable[Any]) -> None:
    """Undo a global `instrument_all()` (new interpreters only)."""
    for p in attached:
        _plugins.unregister_global(p)
