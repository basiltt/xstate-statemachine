# src/xstate_statemachine/contrib/celery/__init__.py
# -----------------------------------------------------------------------------
# 🥬 [celery] -- Celery tasks as `invoke` services, workers, Beat (#292)
# -----------------------------------------------------------------------------
# 🏛️ Celery has no state abstraction; this package maps the statechart onto
#    it in four pieces, each a thin bridge over existing core machinery:
#
#      * `celery_service(task)` -- an ``invoke`` ``src`` that dispatches
#        the task (``apply_async``) and returns WITHOUT blocking. The
#        completion (`done.invoke.<id>` / `error.platform.<id>`) is
#        delivered later through the engine's own actor-logic path, so
#        provenance is engine-grade (a forged ``send("done.invoke.x")`` is
#        refused by the engine, as ever). Delivery: live -- a watcher
#        thread polls the result backend while the interpreter lives;
#        durable -- `deliver_result()` (called by the ``task_success`` /
#        ``task_failure`` signal handlers `connect_signals()` installs, or
#        by `poll_results()`), which opens the persisted instance and
#        verifies the invocation is STILL the active one before completing
#        it (stale completion -> ignored + ``on_event_dropped``).
#      * `@statechart_task(app, store, machine)` -- a worker task that
#        runs load -> send -> persist -> discard, retrying
#        `ConflictError` with Celery's own ``autoretry_for``.
#      * `DurableTimerScheduler` -- `DueTimerScanner.run_once` as a Beat
#        task (EXACTLY ONE Beat process must run it).
#      * `outbox_relay_task` -- `OutboxRelay.relay_once_sync` as a task.
#
# 🔐 Amendments (#292): task headers carrying ``store_key`` /
#    ``invocation_id`` are trusted input only after the persisted instance
#    confirms them; `@statechart_task` asserts ``task_serializer ==
#    "json"`` (no pickle); state exit ``revoke()``s best-effort.
# -----------------------------------------------------------------------------
"""Celery integration: `celery_service`, `statechart_task`, Beat, outbox.

Install with ``pip install "xstate-statemachine[celery]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("celery", "celery")

from .beat import (  # noqa: E402
    DurableTimerScheduler,
    outbox_relay_task,
    xsm_deadlines_every,
)
from .service import (  # noqa: E402
    HEADER_INVOCATION,
    HEADER_KEY,
    CeleryInvocation,
    MemoryPendingResults,
    PendingResult,
    celery_service,
    connect_signals,
    deliver_result,
    poll_results,
)
from .worker import (  # noqa: E402
    UNSAFE_CONTENT,
    assert_json_serializer,
    register_task,
    statechart_task,
)

__all__ = [
    "CeleryInvocation",
    "DurableTimerScheduler",
    "HEADER_INVOCATION",
    "HEADER_KEY",
    "UNSAFE_CONTENT",
    "MemoryPendingResults",
    "PendingResult",
    "assert_json_serializer",
    "celery_service",
    "connect_signals",
    "deliver_result",
    "outbox_relay_task",
    "poll_results",
    "register_task",
    "statechart_task",
    "xsm_deadlines_every",
]
