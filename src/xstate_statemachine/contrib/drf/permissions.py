# src/xstate_statemachine/contrib/drf/permissions.py
"""DRF permission classes built on `has_event_permission` (#281)."""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission

from ..django.permissions import has_event_permission

__all__ = ["StatechartEventPermission", "StatechartHistoryPermission"]


class StatechartEventPermission(BasePermission):
    """Object permission for a transition: the event the view is about to
    send (``view.xsm_event``) must pass `has_event_permission` for
    ``request.user``. Reads (no event) require an authenticated user."""

    message = "You may not send this event to this object now."

    def has_permission(self, request: Any, view: Any) -> bool:
        user = getattr(request, "user", None)
        return bool(user is not None and user.is_authenticated)

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        event = getattr(view, "xsm_event", None)
        if event is None:
            return True
        return has_event_permission(request.user, obj, event)


class StatechartHistoryPermission(BasePermission):
    """Who may read ``history/``: the model's ``view`` permission (history
    carries actors and reasons -- a separate grant from sending)."""

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        opts = obj._meta
        return bool(
            request.user.has_perm(f"{opts.app_label}.view_{opts.model_name}")
        )
