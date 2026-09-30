# src/xstate_statemachine/eda/__init__.py
# -----------------------------------------------------------------------------
# 📡 eda -- event-driven architecture core (#272)
# -----------------------------------------------------------------------------
# 🏛️ Zero-dependency, in core, NOT imported by `import xstate_statemachine`.
#    The CloudEvents-shaped `Envelope`, the `BrokerAdapter` /
#    `SyncBrokerAdapter` protocols every broker adapter implements, and the
#    in-memory `FakeBrokerAdapter` for tests.
# -----------------------------------------------------------------------------
"""Event-driven architecture core: envelopes and broker protocols."""

from __future__ import annotations

from .broker import BrokerAdapter, Delivery, SyncBrokerAdapter
from .envelope import (
    ATTEMPT_EXTENSION,
    SPECVERSION,
    Envelope,
    EnvelopeCorruptError,
    EnvelopeTooLargeError,
    default_event_name,
    new_id,
)
from .fake import BrokerPublishError, FakeBrokerAdapter, SyncFakeBrokerAdapter

__all__ = [
    "ATTEMPT_EXTENSION",
    "BrokerAdapter",
    "BrokerPublishError",
    "Delivery",
    "Envelope",
    "EnvelopeCorruptError",
    "EnvelopeTooLargeError",
    "FakeBrokerAdapter",
    "SPECVERSION",
    "SyncBrokerAdapter",
    "SyncFakeBrokerAdapter",
    "default_event_name",
    "new_id",
]
