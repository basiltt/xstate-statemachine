# src/xstate_statemachine/contrib/observability/sentry.py
# -----------------------------------------------------------------------------
# 🚨 SentryPlugin -- breadcrumbs per transition, opt-in exception capture
# -----------------------------------------------------------------------------
# 📝 `sentry_sdk` is a SOFT import (never pinned). Breadcrumbs carry chart
#    facts only ("a -> b (PAY)"); `capture_errors=True` sends action / guard
#    / service errors and chain trips with `statechart.*` tags.
#
# 🔒 X0.6: tags are the chart id, the allow-listed event type and the
#    action/guard/service NAME; never payloads, context or instance keys.
# -----------------------------------------------------------------------------
"""Sentry breadcrumbs and error capture."""

from __future__ import annotations

import importlib
from typing import Any, Dict

from ...plugins import PluginBase
from .._compat import require_extra
from ._hygiene import event_label

__all__ = ["SentryPlugin"]


class SentryPlugin(PluginBase[Any]):
    """Report transitions as breadcrumbs and (opt-in) errors as events.

    Args:
        level: Breadcrumb level (``"info"``).
        capture_errors: Call ``capture_exception`` for action / guard /
            service errors and chain trips. Default ``False`` -- many
            apps already capture from their own error handlers.
        sdk: Inject a ``sentry_sdk``-shaped module (tests).
    """

    def __init__(
        self,
        level: str = "info",
        *,
        capture_errors: bool = False,
        sdk: Any = None,
    ) -> None:
        if sdk is None:
            require_extra(
                "observability",
                "sentry_sdk",
                hint="-- or: pip install sentry-sdk (a soft dependency, "
                "not pinned)",
            )
            sdk = importlib.import_module("sentry_sdk")
        self.sdk = sdk
        self.level = level
        self.capture_errors = capture_errors

    def on_transition(
        self, interpreter: Any, from_states: Any, to_states: Any, transition
    ) -> None:
        target = getattr(transition, "resolved_target", None)
        src = transition.source.id
        ev = event_label(interpreter.machine, transition.event)
        self.sdk.add_breadcrumb(
            category="statechart",
            message=f"{src} -> {getattr(target, 'id', src)} ({ev})",
            level=self.level,
            data={"machine_id": str(interpreter.machine.id), "event": ev},
        )

    def _capture(self, interpreter: Any, error: BaseException, **tags):
        if not self.capture_errors:
            return
        all_tags: Dict[str, str] = {
            "statechart.machine_id": str(interpreter.machine.id)
        }
        all_tags.update({k: str(v) for k, v in tags.items()})
        # 📝 sentry-sdk 2.x: `new_scope`; 1.x: `push_scope`.
        scoped = getattr(self.sdk, "new_scope", None) or self.sdk.push_scope
        with scoped() as scope:
            for k, v in all_tags.items():
                scope.set_tag(k, v)
            self.sdk.capture_exception(error)

    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        self._capture(
            interpreter,
            error,
            **{"statechart.action": getattr(action, "type", action)},
        )

    def on_guard_error(
        self, interpreter: Any, guard_name: str, event: Any, error: Any
    ) -> None:
        self._capture(interpreter, error, **{"statechart.guard": guard_name})

    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._capture(
            interpreter,
            error,
            **{"statechart.service": getattr(invocation, "src", "")},
        )

    def on_chain_budget_exceeded(
        self, interpreter: Any, error: BaseException, event: Any
    ) -> None:
        self._capture(interpreter, error, **{"statechart.chain_trip": "1"})
