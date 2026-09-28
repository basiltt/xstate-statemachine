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
# -----------------------------------------------------------------------------
"""Resilience patterns: `RetryPolicy`, `DeadLetterPlugin`, `CircuitBreaker`."""

from __future__ import annotations

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
    DeadLetter,
    DeadLetterPlugin,
    DeadLetterStore,
)
from .retry import JitterMode, RetryPolicy

__all__ = [
    "CIRCUIT_BREAKER_CONFIG",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "circuit_breaker",
    "circuit_breaker_logic",
    "DEAD_LETTER_TAG",
    "DeadLetter",
    "DeadLetterPlugin",
    "DeadLetterStore",
    "JitterMode",
    "RetryPolicy",
]
