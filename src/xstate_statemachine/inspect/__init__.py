# src/xstate_statemachine/inspect/__init__.py
# -----------------------------------------------------------------------------
# 🔎 Live inspector (#274, B7) -- speak the Stately Inspector protocol
# -----------------------------------------------------------------------------
# 🏛️ Zero-dependency core: the plugin, the protocol builders, and three
#    stdlib sinks (memory, JSON Lines, SSE over `http.server`). The
#    WebSocket sink lives in `contrib.starlette` (needs `[starlette]`).
#    See docs/_guide/integration-inspector.md.
# -----------------------------------------------------------------------------
"""Live inspection of running machines (Stately Inspector protocol)."""

from __future__ import annotations

from .plugin import InspectorPlugin
from .protocol import (
    MESSAGE_TYPES,
    PROTOCOL_VERSION,
    actor_message,
    event_message,
    snapshot_message,
)
from .replay import replay_messages
from .sinks import (
    COOKIE_NAME,
    JsonLinesSink,
    MemorySink,
    SseSink,
    read_jsonl,
)

__all__ = [
    "COOKIE_NAME",
    "InspectorPlugin",
    "JsonLinesSink",
    "MESSAGE_TYPES",
    "MemorySink",
    "PROTOCOL_VERSION",
    "SseSink",
    "actor_message",
    "event_message",
    "read_jsonl",
    "replay_messages",
    "snapshot_message",
]
