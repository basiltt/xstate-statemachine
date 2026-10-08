# src/xstate_statemachine/eda/__init__.py
# -----------------------------------------------------------------------------
# 📡 eda -- event-driven architecture core (#272, #293, #295)
# -----------------------------------------------------------------------------
# 🏛️ Zero-dependency, in core, NOT imported by `import xstate_statemachine`
#    (import it explicitly). Everything a broker integration builds on:
#
#      * `Envelope` -- CloudEvents 1.0-shaped wire format, sortable ids;
#      * `BrokerAdapter` / `SyncBrokerAdapter` protocols + `Delivery`;
#      * `FakeBrokerAdapter` -- in-memory broker for tests;
#      * `InboundDispatcher` -- envelope → persisted instance → send, with
#        dedup, per-subject order, poison → DLQ (X0.8);
#      * `OutboxPlugin` + `OutboxStore` (`SQLiteOutboxStore`) -- publish
#        what the chart tags, transactionally with the snapshot;
#      * dead letters: `SQLiteDeadLetterStore`, `BrokerDeadLetterSink`;
#      * `asyncapi_document` -- AsyncAPI 3.0 from a chart.
#
#    `[cloudevents]` only adds SDK interop (`contrib.cloudevents`); the
#    real brokers arrive with #294.
# -----------------------------------------------------------------------------
"""Event-driven architecture core: envelopes, brokers, outbox, DLQ."""

from __future__ import annotations

from .asyncapi import (
    ASYNCAPI_VERSION,
    asyncapi_document,
    consumed_events,
    load_asyncapi_schema,
    validate_asyncapi,
)
from .broker import BrokerAdapter, Delivery, SyncBrokerAdapter
from .dead_letter import (
    BrokerDeadLetterSink,
    DeadLetterStoreProtocol,
    MemoryDeadLetterStore,
    SQLiteDeadLetterStore,
    dlq_topic,
    redact_record,
)
from .dispatcher import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_IN_FLIGHT,
    DispatchResult,
    InboundDispatcher,
    ReplayRefusedError,
    ReplayResult,
    replay_dead_letter,
)
from .envelope import (
    MAX_DATA_DEPTH,
    ATTEMPT_EXTENSION,
    SPECVERSION,
    Envelope,
    EnvelopeCorruptError,
    EnvelopeTooLargeError,
    default_event_name,
    new_id,
)
from .fake import BrokerPublishError, FakeBrokerAdapter, SyncFakeBrokerAdapter
from .outbox import (
    DEFAULT_CLAIM_LEASE_S,
    PUBLISH_TAG,
    MemoryOutboxStore,
    OutboxPlugin,
    OutboxRecord,
    OutboxRelay,
    OutboxStore,
    SQLiteOutboxStore,
    publish_specs,
)
from ..patterns.dead_letter import DeadLetter, DeadLetterPlugin

#: The frozen contract name. `patterns.DeadLetterStore` is the in-memory
#: implementation; this is the protocol every store satisfies.
DeadLetterStore = DeadLetterStoreProtocol

__all__ = [
    "MAX_DATA_DEPTH",
    "DEFAULT_CLAIM_LEASE_S",
    "ASYNCAPI_VERSION",
    "ATTEMPT_EXTENSION",
    "BrokerAdapter",
    "BrokerDeadLetterSink",
    "BrokerPublishError",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_MAX_IN_FLIGHT",
    "DeadLetter",
    "DeadLetterPlugin",
    "DeadLetterStore",
    "Delivery",
    "DispatchResult",
    "Envelope",
    "EnvelopeCorruptError",
    "EnvelopeTooLargeError",
    "FakeBrokerAdapter",
    "InboundDispatcher",
    "MemoryDeadLetterStore",
    "MemoryOutboxStore",
    "OutboxPlugin",
    "OutboxRecord",
    "OutboxRelay",
    "OutboxStore",
    "PUBLISH_TAG",
    "ReplayRefusedError",
    "ReplayResult",
    "SPECVERSION",
    "SQLiteDeadLetterStore",
    "SQLiteOutboxStore",
    "SyncBrokerAdapter",
    "SyncFakeBrokerAdapter",
    "asyncapi_document",
    "consumed_events",
    "default_event_name",
    "dlq_topic",
    "load_asyncapi_schema",
    "new_id",
    "publish_specs",
    "redact_record",
    "replay_dead_letter",
    "validate_asyncapi",
]
