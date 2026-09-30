# src/xstate_statemachine/contrib/celery/beat.py
# -----------------------------------------------------------------------------
# â° Celery Beat as the durable `after` scheduler; outbox relay task (#292)
# -----------------------------------------------------------------------------
# ðŸ›ï¸ `DurableTimerScheduler` registers ONE task that runs
#    `DueTimerScanner.run_once` and a Beat entry that calls it every N
#    seconds -- the SAFETY NET that fires every matured deadline. For
#    exact timing, `schedule_exact(key)` also enqueues an ``eta`` job per
#    persisted deadline carrying the deadline's STATE-ENTRY GENERATION
#    (``state_id`` + ``entry_seq``, X0.9): when it fires, the job wakes
#    the instance only if that very deadline is still recorded -- a
#    machine that left the state (or re-entered it: a new generation) is
#    skipped. Double firing is idempotent: the scanner re-checks under the
#    lock and `fire_due` fires a deadline once.
#
# âš ï¸ Run EXACTLY ONE Beat process. Two Beats double the scan traffic
#    (still correct -- the scan is idempotent -- but wasteful); zero
#    Beats means `after` timers of discarded instances never fire.
# -----------------------------------------------------------------------------
"""`DurableTimerScheduler`, `xsm_deadlines_every`, `outbox_relay_task`."""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...eda.outbox import OutboxRelay
from ...persistence.timers import DueTimerScanner

__all__ = [
    "DurableTimerScheduler",
    "outbox_relay_task",
    "xsm_deadlines_every",
]

logger = logging.getLogger(__name__)

DEFAULT_TASK = "xsm.deadlines.scan"
DEFAULT_FIRE_TASK = "xsm.deadlines.fire"
DEFAULT_OUTBOX_TASK = "xsm.outbox.relay"


class DurableTimerScheduler:
    """`DueTimerScanner` as Celery tasks.

    Args:
        app: The Celery app.
        store / machine_for_key / scanner_kw: For `DueTimerScanner`
            (``lock``, ``plugins``, ``now``, ``skew_tolerance_s``,
            ``prefix``, ``limit``, ...).
        name / fire_name: Task names.
    """

    def __init__(
        self,
        app: Any,
        store: Any,
        machine_for_key: Any,
        *,
        name: str = DEFAULT_TASK,
        fire_name: str = DEFAULT_FIRE_TASK,
        **scanner_kw: Any,
    ) -> None:
        self.app = app
        self.store = store
        mfk = machine_for_key
        self.machine_for_key = mfk if callable(mfk) else (lambda _k: mfk)
        self.scanner = DueTimerScanner(
            store, self.machine_for_key, **scanner_kw
        )
        self._scanner_kw = scanner_kw

        # 📝 closures, not bound methods: Celery binds a task function
        #    as if it were declared on the Task class.
        def scan() -> int:
            return self.run_once()

        def fire(key: str, state_id: str, entry_seq: int) -> bool:
            return self.fire(key, state_id, entry_seq)

        self.task = app.task(name=name, serializer="json")(scan)
        self.fire_task = app.task(name=fire_name, serializer="json")(fire)

    def run_once(self) -> int:
        """One safety-net scan; returns how many machines were woken."""
        return self.scanner.run_once()

    def beat_entry(self, seconds: float = 10.0) -> Dict[str, Any]:
        """A ``beat_schedule`` entry calling `run_once` every *seconds*."""
        return {"task": self.task.name, "schedule": float(seconds)}

    # -- exact scheduling ------------------------------------------------------
    def schedule_exact(self, key: str) -> List[Any]:
        """Enqueue one ``eta`` job per persisted deadline of *key*."""
        rec = self.store.load(key)
        sent: List[Any] = []
        for d in rec.deadlines if rec is not None else ():
            eta = datetime.fromtimestamp(d.due_at_wall, tz=timezone.utc)
            sent.append(
                self.fire_task.apply_async(
                    (key, d.state_id, int(d.entry_seq)), eta=eta
                )
            )
        return sent

    def fire(self, key: str, state_id: str, entry_seq: int) -> bool:
        """Wake *key* if the deadline (*state_id*, *entry_seq*) is still
        recorded and due; ``False`` (skipped) otherwise."""
        rec = self.store.load(key)
        live = rec is not None and any(
            d.state_id == state_id and int(d.entry_seq) == int(entry_seq)
            for d in rec.deadlines
        )
        if not live:
            logger.info(
                "â° eta job for %r (%s#%s) is stale; skipped",
                key,
                state_id,
                entry_seq,
            )
            return False
        kw = dict(self._scanner_kw)
        kw["prefix"] = key
        scanner = DueTimerScanner(self.store, self.machine_for_key, **kw)
        return any(k == key for k, _ in scanner.due_keys()) and bool(
            scanner.run_once()
        )


def xsm_deadlines_every(
    scheduler: DurableTimerScheduler, seconds: float = 10.0
) -> Dict[str, Dict[str, Any]]:
    """``app.conf.beat_schedule = xsm_deadlines_every(scheduler, 10)``."""
    return {"xsm-deadlines": scheduler.beat_entry(seconds)}


def outbox_relay_task(
    app: Any,
    outbox: Any,
    broker: Any,
    *,
    name: str = DEFAULT_OUTBOX_TASK,
    batch: int = 100,
) -> Any:
    """Register a task that drains *outbox* to *broker* once per call
    (schedule it with Beat). Works with a sync or an async broker."""
    relay = OutboxRelay(outbox, broker, batch=batch)

    def relay_once() -> int:
        if inspect.iscoroutinefunction(getattr(broker, "publish", None)):
            return asyncio.run(relay.relay_once())
        return relay.relay_once_sync()

    return app.task(name=name, serializer="json")(relay_once)
