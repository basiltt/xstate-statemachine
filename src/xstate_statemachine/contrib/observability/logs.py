# src/xstate_statemachine/contrib/observability/logs.py
# -----------------------------------------------------------------------------
# 🪵 StructlogPlugin / LoguruPlugin -- log context around each event (#273)
# -----------------------------------------------------------------------------
# 🏛️ Bind `machine_id`, `state`, `event` (and `correlation_id` when the
#    event carries one) as context variables from `on_event_received` until
#    `on_event_processed` (#304), so *user* log lines emitted inside actions
#    carry them without the action knowing about logging at all.
#
# 📝 SOFT imports: neither package is pinned by `[observability]`. The
#    plugin constructor raises `MissingExtraError` naming the PACKAGE when
#    it is absent (`pip install structlog`).
#
# 🔒 X0.6: `correlation_id` is log CONTEXT (per-line, not an index/label)
#    and only bound when present; payloads are never bound.
# -----------------------------------------------------------------------------
"""structlog and loguru context plugins."""

from __future__ import annotations

import importlib
import threading
from typing import Any, Dict, List, Optional, Tuple

from ...plugins import PluginBase
from .._compat import require_extra
from ._hygiene import event_label

__all__ = ["StructlogPlugin", "LoguruPlugin", "log_context"]


def _correlation_id(event: Any) -> Optional[str]:
    payload = getattr(event, "payload", None)
    if not isinstance(payload, dict):
        return None
    for key in ("correlation_id", "correlationid", "correlationId"):
        if key in payload:
            return str(payload[key])
    headers = payload.get("headers")
    if isinstance(headers, dict):
        for key in ("correlation_id", "x-correlation-id"):
            if key in headers:
                return str(headers[key])
    return None


def log_context(interpreter: Any, event: Any) -> Dict[str, Any]:
    """The fields both plugins bind for one event."""
    ctx: Dict[str, Any] = {
        "machine_id": str(interpreter.machine.id),
        "state": sorted(interpreter.current_state_ids),
        "event": event_label(
            interpreter.machine, getattr(event, "type", None)
        ),
    }
    cid = _correlation_id(event)
    if cid is not None:
        ctx["correlation_id"] = cid
    return ctx


def _soft(module: str, package: str) -> Any:
    require_extra(
        "observability",
        module,
        hint=f"-- or: pip install {package} (a soft dependency, not pinned)",
    )
    return importlib.import_module(module)


class _ContextPlugin(PluginBase[Any]):
    """Shared stack discipline: one context per in-flight event per thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _stack(self) -> List[Tuple[Any, Any]]:
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        return stack

    def _enter(self, fields: Dict[str, Any]) -> Any:  # pragma: no cover
        raise NotImplementedError

    def _exit(self, token: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        token = self._enter(log_context(interpreter, event))
        self._stack().append((event, token))

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        stack = self._stack()
        for idx in range(len(stack) - 1, -1, -1):
            if stack[idx][0] is event:
                # unwind anything nested above it too (LIFO for contextvars)
                while len(stack) > idx:
                    self._exit(stack.pop()[1])
                return


class StructlogPlugin(_ContextPlugin):
    """Bind event context with ``structlog.contextvars``.

    Your structlog configuration must include
    ``structlog.contextvars.merge_contextvars`` in its processors (the
    default configuration does).
    """

    def __init__(self) -> None:
        super().__init__()
        self._sl = _soft("structlog", "structlog")
        importlib.import_module("structlog.contextvars")

    def _enter(self, fields: Dict[str, Any]) -> Any:
        return self._sl.contextvars.bind_contextvars(**fields)

    def _exit(self, token: Any) -> None:
        self._sl.contextvars.reset_contextvars(**token)


class LoguruPlugin(_ContextPlugin):
    """Bind event context with ``logger.contextualize()``; the fields land
    in ``record["extra"]``."""

    def __init__(self, logger: Any = None) -> None:
        super().__init__()
        self._logger = logger or _soft("loguru", "loguru").logger

    def _enter(self, fields: Dict[str, Any]) -> Any:
        cm = self._logger.contextualize(**fields)
        cm.__enter__()
        return cm

    def _exit(self, token: Any) -> None:
        token.__exit__(None, None, None)
