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

from .fields import StatechartSerializerField, event_serializer  # noqa: E402
from .permissions import (  # noqa: E402
    StatechartEventPermission,
    StatechartHistoryPermission,
)
from .viewsets import StatechartViewSetMixin, problem_response  # noqa: E402

__all__ = [
    "StatechartEventPermission",
    "StatechartHistoryPermission",
    "StatechartSerializerField",
    "StatechartViewSetMixin",
    "event_serializer",
    "problem_response",
]
