# src/xstate_statemachine/persistence/timers.py
# -----------------------------------------------------------------------------
# ⏰ DueTimerScanner -- the process that wakes machines whose timers matured
# -----------------------------------------------------------------------------
# 🏛️ `after` timers are the library's superpower for retries, SLAs,
#    escalations and reminders -- and until #264 they were in-memory
#    tasks that died with the process. Under create → act → persist →
#    discard the interpreter is discarded after every request, so a
#    24-hour `after` never fired. Now the deadline is IN the snapshot
#    (`deadlines`, layout v4) and indexed by the store; this scanner is the
#    zero-dependency driver that finds matured deadlines and wakes their
#    machines under a lock strategy with `restart_timers="fire_due"`. Celery
#    Beat / APScheduler / cron adapters (phase F) just call `run_once()`.
#
# 🔐 Guarantees (stated in the docs box):
#    * a timer fires no EARLIER than its deadline and no LATER than the
#      next scanner tick after it;
#    * the scanner re-reads the record under the lock and fires only if a
#      deadline with the SAME `entry_seq` still exists (X0.9) -- a machine
#      that moved on between the scan and the wake is left alone;
#    * a crash between fire and save re-fires on the next tick
#      (at-least-once): make the timer's transition idempotent or pair it
#      with the idempotency inbox.
# -----------------------------------------------------------------------------
"""`DueTimerScanner`: find and fire matured persisted `after` deadlines."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Optional, Tuple

from ..logger import logger
from .store import StateStore

__all__ = ["DueTimerScanner", "ScanResult"]


@dataclass
class ScanResult:
    """What one `run_once` did.

    Attributes:
        scanned: Keys inspected.
        due: Keys with at least one matured deadline.
        woken: Machines actually loaded and fired.
        skipped_stale: Due keys skipped because the deadline changed under
            the lock (another worker won, or the machine moved on).
        errors: ``(key, exception)`` for keys whose wake raised.
        max_lag_s: Worst (now - due_at) among fired deadlines -- the
            "how late are we" metric (X0.12).
    """

    scanned: int = 0
    due: int = 0
    woken: int = 0
    skipped_stale: int = 0
    errors: List[Tuple[str, BaseException]] = field(default_factory=list)
    max_lag_s: float = 0.0


class DueTimerScanner:
    """Wake machines whose persisted `after` deadlines have passed.

    Args:
        store: The `StateStore` holding the snapshots (open your own
            handle per process -- the scanner is "another process").
        machine_for_key: ``(key) -> MachineNode`` -- which chart a key runs;
            a plain ``lambda k: machine`` for a single-chart store.
        lock: A `LockStrategy` (default `OptimisticLock`).
        plugins: Attached to every woken interpreter (audit, inbox ...).
        now: ``() -> float`` epoch seconds; default ``time.time``. Inject a
            `SimulatedClock().wall_now` in tests.
        skew_tolerance_s: Fire deadlines up to this many seconds in the
            FUTURE too, to absorb clock skew between the writer host and
            this one. ``0`` is strict.
        prefix: Only scan keys with this prefix.
        limit: Keys inspected per `run_once` (batching).
        migrator / on_version_mismatch: Forwarded to `persisted()` (#263).
    """

    def __init__(
        self,
        store: StateStore,
        machine_for_key: Callable[[str], Any],
        *,
        lock: Optional[Any] = None,
        plugins: Iterable[Any] = (),
        now: Optional[Callable[[], float]] = None,
        skew_tolerance_s: float = 0.0,
        prefix: str = "",
        limit: int = 1000,
        migrator: Optional[Any] = None,
        on_version_mismatch: Optional[str] = None,
    ) -> None:
        self.store = store
        self.machine_for_key = machine_for_key
        self.lock = lock
        self.plugins = list(plugins)
        self.now = now or time.time
        self.skew_tolerance_s = float(skew_tolerance_s)
        self.prefix = prefix
        self.limit = int(limit)
        self.migrator = migrator
        self.on_version_mismatch = on_version_mismatch
        self._stop = threading.Event()

    # -- one pass -------------------------------------------------------------------
    def due_keys(self, now: Optional[float] = None) -> List[Tuple[str, float]]:
        """``(key, earliest due_at)`` for records with a matured deadline,
        soonest first. Reads only the store's deadline index."""
        at = (self.now() if now is None else now) + self.skew_tolerance_s
        # ⚡ A store with a deadline INDEX (Redis zset, #306) answers this
        #    directly; the stdlib stores are scanned record by record.
        indexed = getattr(self.store, "due_keys", None)
        if callable(indexed):
            rows = [
                (k, d)
                for k, d in indexed(at, limit=self.limit)
                if k.startswith(self.prefix)
            ]
            rows.sort(key=lambda kv: kv[1])
            return rows
        out: List[Tuple[str, float]] = []
        for key in self.store.list_keys(prefix=self.prefix, limit=self.limit):
            rec = self.store.load(key)
            if rec is None or not rec.deadlines:
                continue
            earliest = min(d.due_at_wall for d in rec.deadlines)
            if earliest <= at:
                out.append((key, earliest))
        out.sort(key=lambda kv: kv[1])
        return out

    def run_once(self, now: Optional[float] = None) -> int:
        """Scan once; wake every machine with a matured deadline. Returns
        how many were woken (`last_result` has the full `ScanResult`)."""
        return self.scan(now).woken

    def scan(self, now: Optional[float] = None) -> ScanResult:
        from .locking import _DEFAULT_LOCK as _DEFAULT, persisted

        at = self.now() if now is None else now
        result = ScanResult()
        result.scanned = len(
            self.store.list_keys(prefix=self.prefix, limit=self.limit)
        )
        for key, earliest in self.due_keys(at):
            result.due += 1
            try:
                machine = self.machine_for_key(key)
                # 🔒 Take the strategy's lock FIRST (a real lock for
                #    `PessimisticLock`, nothing for optimistic -- there the
                #    fence is the versioned save inside `persisted()`),
                #    then re-read and confirm a matured deadline is STILL
                #    there. A machine another worker advanced between our
                #    scan and now has no such deadline and is skipped, never
                #    double-fired (X0.9). `persisted()` re-acquires the same
                #    lock re-entrantly on the same thread.
                strategy = self.lock if self.lock is not None else _DEFAULT
                with strategy.acquire(self.store, key):
                    rec = self.store.load(key)
                    horizon = at + self.skew_tolerance_s
                    if rec is None or not any(
                        d.due_at_wall <= horizon for d in rec.deadlines
                    ):
                        result.skipped_stale += 1
                        continue
                    with persisted(
                        self.store,
                        key,
                        machine,
                        lock=self.lock,
                        plugins=self.plugins,
                        create_if_missing=False,
                        restart_timers="fire_due",
                        # The woken machine sees "now" as the horizon, so a
                        # deadline inside the skew window is matured for
                        # `fire_due` exactly as it was for the scan.
                        clock=_WallClock(horizon),
                        migrator=self.migrator,
                        on_version_mismatch=self.on_version_mismatch,
                    ):
                        pass  # fire_due ran in start(); exit saves
                result.woken += 1
                result.max_lag_s = max(result.max_lag_s, at - earliest)
            except (
                Exception
            ) as exc:  # noqa: BLE001 -- one key must not stop the scan
                logger.error(
                    "⏰ DueTimerScanner: waking '%s' failed: %r", key, exc
                )
                result.errors.append((key, exc))
        self.last_result = result
        if result.woken and logger.isEnabledFor(logging.INFO):
            logger.info(
                "⏰ DueTimerScanner: woke %d/%d due machine(s); max lag %.1fs",
                result.woken,
                result.due,
                result.max_lag_s,
            )
        return result

    # -- loop -------------------------------------------------------------------------
    def run_forever(self, interval_s: float = 1.0) -> None:
        """Call `run_once` every *interval_s* seconds until `stop()`."""
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 -- keep the loop alive
                logger.exception("⏰ DueTimerScanner: run_once raised")
            self._stop.wait(interval_s)

    def stop(self) -> None:
        self._stop.set()


class _WallClock:
    """A `RealClock` whose `wall_now()` is pinned to the scanner's ``now``.

    The woken interpreter computes "how late is this deadline" against
    `wall_now()`; pinning it to the scan instant makes `fire_due`
    deterministic (and testable with an injected ``now``) while `now()`
    stays monotonic for the engine's own bookkeeping.
    """

    def __init__(self, wall: float) -> None:
        from ..clock import RealClock

        self._inner = RealClock()
        self._wall = float(wall)

    def now(self) -> float:
        return self._inner.now()

    def wall_now(self) -> float:
        return self._wall

    def set_timeout(
        self,
        fn: Any,
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
        return self._inner.set_timeout(fn, delay_sec, owner=owner, sync=sync)

    def clear_timeout(self, handle: Any) -> None:
        self._inner.clear_timeout(handle)

    def pump(self) -> int:
        return self._inner.pump()
