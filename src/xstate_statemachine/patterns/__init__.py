# src/xstate_statemachine/patterns/__init__.py
# -----------------------------------------------------------------------------
# 🧱 patterns -- resilience building blocks, each a small statechart (#265)
# -----------------------------------------------------------------------------
# 🏛️ Zero-dependency, in core. Retry-with-backoff, dead-lettering and the
#    circuit breaker are the three things every service team re-implements
#    by hand and gets subtly wrong (no jitter → thundering herd; half-open
#    probe races; poison messages with no error context). They need only
#    existing engine features -- `after` with named delays, guards,
#    context, plugins -- so they live here and every integration (Celery
#    #279, the persistence locking in #260, the broker adapters) builds on
#    the same objects rather than its own copy.
#
# 🧾 #295 adds the two EDA patterns: `SagaBuilder` (orchestration, plain
#    JSON) and `ChoreographyRouter` (machines reacting over a bus). The
#    router pulls in the EDA core, which `import xstate_statemachine` must
#    not load (persistence imports this package), so it resolves lazily.
# -----------------------------------------------------------------------------
"""Resilience and EDA patterns: `RetryPolicy`, `DeadLetterPlugin`,
`CircuitBreaker`, `SagaBuilder`, `ChoreographyRouter`."""

from __future__ import annotations

from typing import Any

from .circuit_breaker import (
    CIRCUIT_BREAKER_CONFIG,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    circuit_breaker,
    circuit_breaker_logic,
)
from .dead_letter import (
    DEAD_LETTER_TAG,
    ERRORS_CONTEXT_KEY,
    DeadLetter,
    DeadLetterPlugin,
    DeadLetterStore,
    MemoryDeadLetterStore,
)
from .retry import JitterMode, RetryPolicy
from .saga import SagaBuilder, SagaStep

_LAZY = {"ChoreographyRouter": ".choreography", "Route": ".choreography"}


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module, __name__), name)


__all__ = [
    "CIRCUIT_BREAKER_CONFIG",
    "ChoreographyRouter",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "circuit_breaker",
    "circuit_breaker_logic",
    "DEAD_LETTER_TAG",
    "ERRORS_CONTEXT_KEY",
    "DeadLetter",
    "DeadLetterPlugin",
    "DeadLetterStore",
    "JitterMode",
    "MemoryDeadLetterStore",
    "RetryPolicy",
    "Route",
    "SagaBuilder",
    "SagaStep",
]
