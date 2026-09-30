# src/xstate_statemachine/contrib/channels/__init__.py
# -----------------------------------------------------------------------------
# 📡 [channels] -- a live statechart over a Django Channels WebSocket
# -----------------------------------------------------------------------------
# 🏛️ `StatechartConsumer` is the Channels twin of the Starlette WebSocket
#    bridge: connect → the current state; inbound ``{"type", "payload"}``
#    → the model's ``send()`` (in ``database_sync_to_async``, so the row
#    lock never blocks the event loop); every committed transition is
#    pushed to the group ``xsm.<app_label>.<model>.<pk>`` -- so a second
#    connection (another tab, another worker) sees it too.
#
# 🔐 X0.7: an unauthenticated scope (no ``AuthMiddlewareStack``, or an
#    anonymous user) is closed with 1008; `authorize()` is the per-object
#    read check (default: the model's ``view`` permission) and each event
#    is re-checked with `has_event_permission`. A heartbeat ``{"kind":
#    "ping"}`` keeps idle proxies from dropping the socket. No interpreter
#    outlives a message (create → act → persist → discard), and the
#    heartbeat task is cancelled on disconnect -- the leak test pins 0.
# -----------------------------------------------------------------------------
"""Django Channels integration.

Install with ``pip install "xstate-statemachine[channels]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("channels", "channels", "django")

import importlib  # noqa: E402
from typing import Any  # noqa: E402

#: 📝 Lazy, like ``contrib.django``: importable before ``django.setup()``
#:    (the consumer module touches models through the permissions).
_LAZY = {
    "StatechartConsumer": ".consumer",
    "WS_POLICY_VIOLATION": ".consumer",
    "live_consumers": ".consumer",
}

__all__ = sorted(_LAZY)


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module, __name__), name)
