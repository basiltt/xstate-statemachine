# src/xstate_statemachine/contrib/drf/__init__.py
# -----------------------------------------------------------------------------
# 🧰 [drf] -- a statechart REST surface in one ViewSet mixin
# -----------------------------------------------------------------------------
# 🏛️ The DRF convention is a hand-written ``@action`` per transition around
#    ``can_proceed``. `StatechartViewSetMixin` GENERATES those actions from
#    the chart (``POST /orders/{pk}/submit/``), plus ``send/``, ``events/``
#    and ``history/``, and maps the `Receipt` to HTTP with the CORE
#    ``receipts`` table (#305) -- the same statuses FastAPI and Flask
#    answer. No dependency on the Starlette extra.
#
# 🔐 X0.1 closed by default: the viewset REFUSES to build without explicit
#    ``permission_classes`` (AllowAny must be written down), each event is
#    re-checked with `has_event_permission` (403), and serialized context
#    is opt-in. X0.2: ``Idempotency-Key`` is scoped to ``request.user``.
#    X0.7: RFC 9457 problem bodies carrying the exception CLASS only.
#    ``SessionAuthentication`` enforces CSRF on unsafe methods as usual.
# -----------------------------------------------------------------------------
"""Django REST framework integration.

Install with ``pip install "xstate-statemachine[drf]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("drf", "rest_framework", "django")

import importlib  # noqa: E402
from typing import Any  # noqa: E402

#: 📝 Lazy, like ``contrib.django``: importable before ``django.setup()``
#:    (DRF itself reads settings on import of its views / fields).
_LAZY = {
    "StatechartEventPermission": ".permissions",
    "StatechartHistoryPermission": ".permissions",
    "StatechartSerializerField": ".fields",
    "StatechartViewSetMixin": ".viewsets",
    "event_serializer": ".fields",
    "problem_response": ".viewsets",
}

__all__ = sorted(_LAZY)


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module, __name__), name)
