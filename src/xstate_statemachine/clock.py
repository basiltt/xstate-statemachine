# /src/xstate_statemachine/clock.py
# -----------------------------------------------------------------------------
# ⏱️ Clock: time as an injectable dependency
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision (#48, #49, #50): before 0.8.0 the async engine
# called `asyncio.sleep` for every `after` and delayed send, and the sync
# engine started a daemon OS THREAD per timer. Three consequences:
#
#   * a test of a 30 s timeout burned 30 s of wall clock (#49);
#   * a due `after` on the async engine queued behind every external event
#     already in the inbox, so it fired ~180 ms late at 500 busy machines
#     (#48);
#   * the "single-threaded" sync engine ran actions on timer threads that
#     mutated `context` with no lock (#50).
#
# XState v5 solves the first by making the clock a `createActor` option and
# shipping `SimulatedClock`. This module mirrors that and uses the same seam
# for the other two. A `Clock` schedules CALLBACKS; the interpreter decides
# what a fired callback means. The default (`RealClock`) preserves today's
# async timing byte-for-byte via `loop.call_later`, and gives the sync engine
# a thread-free deadline list drained by `tick()` / `send()`.
#
# Design constraints that shaped the API:
#   * The same `Clock` object must serve BOTH engines, so a parent and its
#     invoked children (which may be either) share one timeline.
#   * `SimulatedClock.increment()` must fire timers in DUE order and, on the
#     async engine, let the interpreter settle before returning -- otherwise
#     the assertion after `increment` races the loop. It therefore has an
#     awaitable form; calling it without `await` inside a loop is a mistake
#     we detect (a RuntimeWarning) rather than a silent race.
#   * A fired timer records `scheduled_for` / `fired_at` so lateness is data,
#     not inference (#48 item 3).
# -----------------------------------------------------------------------------
"""`Clock` protocol, `RealClock` default and `SimulatedClock` for tests."""

from __future__ import annotations

import asyncio
import heapq
import inspect
import itertools
import logging
import math
import threading
import time
from typing import Any, Awaitable, Callable, List, Optional, Tuple, Union

from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class WallClock(Protocol):
    """Optional second protocol: a clock that knows epoch time (RU-28).

    The engines read ``wall_now()`` with ``getattr`` for durable timers and
    audit records (#305) and fall back to ``time.time()`` when a custom
    clock lacks it -- so implement this on any `Clock` whose notion of
    "now" is not the real one.
    """

    def wall_now(self) -> float:
        """Seconds since the Unix epoch on this clock's timeline."""
        ...


@runtime_checkable
class Clock(Protocol):
    """What an interpreter needs from a source of time.

    Mirrors XState's ``Clock`` (``setTimeout`` / ``clearTimeout``) with one
    Python-specific addition, :meth:`pump`, which lets a clock that does
    not run its own thread or loop deliver due callbacks when the owner
    asks (the sync engine's `tick()`; see :class:`RealClock`).

    📝 Delivery contract for ``pump()`` (RU-01/RU-02): a due batch is fired
    in deadline order; a timer cleared by an earlier callback of the same
    batch does NOT fire; an exception from one callback never prevents the
    others from running -- the first one is re-raised after the batch.
    A clock may also expose ``wall_now()`` (seconds since the epoch); the
    engine reads it with ``getattr`` and falls back to ``time.time()``.
    """

    def now(self) -> float:
        """Current time in seconds (monotonic; origin is clock-specific)."""
        ...

    def set_timeout(
        self,
        fn: Callable[[], Any],
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
        """Schedule *fn* after *delay_sec*; return a cancellation handle.

        Engines pass ``sync=True|False`` (#76) to say which delivery lane
        they can drain; a clock that does not care may ignore it. A clock
        written against the 0.8.0 protocol (no ``sync`` parameter) is
        still accepted at runtime -- the engine retries without it.
        """
        ...

    def clear_timeout(self, handle: Any) -> None:
        """Cancel a scheduled callback. Idempotent."""
        ...

    def pump(self) -> int:
        """Run every callback whose deadline has passed; return how many."""
        ...


# -----------------------------------------------------------------------------
# 🔥 Batch delivery shared by every clock lane
# -----------------------------------------------------------------------------
def _require_finite(value: float, what: str) -> None:
    """Reject NaN/inf at the clock boundary (RU-26).

    ``nan < 0`` is False, so a NaN would sail past the "cannot move
    backwards" check and wedge ``now()`` forever (every later comparison
    is False); ``inf`` would fire everything and pin ``now()`` at inf.

    Args:
        value: The number a caller handed to the clock.
        what: Parameter name used in the error message.

    Raises:
        ValueError: If *value* is NaN or infinite.
    """
    if not math.isfinite(value):
        raise ValueError(f"{what} must be a finite number, got {value!r}")


def _fire_batch(timers: List["_Timer"]) -> Tuple[int, Optional[Exception]]:
    """Run an already-popped due batch, one timer at a time.

    🏛️ `due_before()` POPS every due timer first, so a callback that raised
    used to drop the rest of the batch for good (RU-01), and a timer
    cleared by an earlier sibling still ran (RU-02). Each timer is now
    re-checked for ``cancelled`` right before it runs, and an exception is
    contained so the remaining timers still fire.

    Args:
        timers: Timers in deadline order, as returned by `due_before`.

    Returns:
        ``(fired, first_error)``: how many callbacks ran and the first
        exception any of them raised (``None`` when all succeeded). Later
        errors are logged. The caller decides when to re-raise.
    """
    fired = 0
    first_error: Optional[Exception] = None
    for t in timers:
        if t.cancelled:  # 📝 cleared by an earlier callback in this batch
            continue
        try:
            t.fn()
        except Exception as exc:
            if first_error is None:
                first_error = exc
            else:
                logger.error(
                    "Clock timer callback raised: %r", exc, exc_info=exc
                )
        fired += 1
    return fired, first_error


# -----------------------------------------------------------------------------
# 🧱 Shared deadline heap
# -----------------------------------------------------------------------------
class _Timer:
    """One scheduled callback."""

    __slots__ = ("due", "seq", "fn", "owner", "cancelled")

    def __init__(
        self, due: float, seq: int, fn: Callable[[], Any], owner: Any
    ):
        self.due = due
        self.seq = seq
        self.fn = fn
        self.owner = owner
        self.cancelled = False

    def __lt__(self, other: "_Timer") -> bool:  # heap ordering: due, then FIFO
        return (self.due, self.seq) < (other.due, other.seq)


class _DeadlineHeap:
    """A cancellable min-heap of timers, safe to mutate from any thread.

    Cancellation is lazy (a flag), so `clear_timeout` is O(1) and the heap
    is never re-sorted. `due_before(t)` pops in due order and skips
    cancelled entries.
    """

    def __init__(self) -> None:
        self._heap: List[_Timer] = []
        self._seq = itertools.count()
        #: ⚡ Allocated on the first `push`. A `threading.Lock` is the most
        #: expensive thing a fresh `RealClock` owned, and most interpreters
        #: never arm a timer -- yet every one got a clock, heap and lock.
        #: `pump()` / `due_before()` on an empty heap never take the lock.
        self._lock_: Optional[threading.Lock] = None

    @property
    def _lock(self) -> threading.Lock:
        lock = self._lock_
        if lock is None:
            # Benign race: two threads may each build a Lock; the second
            # assignment wins and the first is garbage. Both are unlocked,
            # and the heap is empty until the first push completes under
            # whichever lock that push took -- a push and a pop cannot
            # interleave before any push has happened.
            lock = self._lock_ = threading.Lock()
        return lock

    def push(self, due: float, fn: Callable[[], Any], owner: Any) -> _Timer:
        """Schedule *fn* to run once the heap time reaches *due*.

        Args:
            due: Absolute deadline on the owning clock's timeline.
            fn: Zero-argument callable to invoke when the timer fires.
            owner: Opaque owner stored on the timer for bookkeeping.

        Returns:
            The queued timer, usable as a handle for `cancel`.
        """
        t = _Timer(due, next(self._seq), fn, owner)
        with self._lock:
            heapq.heappush(self._heap, t)
        return t

    def cancel(self, t: Any) -> None:
        """Mark a timer cancelled (lazy; O(1)). Idempotent, lock-free.

        📝 A plain attribute store is atomic under the GIL, and a race with
        `due_before` is benign: the timer is either skipped at pop time or
        re-checked by `_fire_batch` right before it runs.
        """
        if isinstance(t, _Timer):
            t.cancelled = True

    def due_before(
        self,
        now: float,
        owner_filter: Optional[Callable[[Any], bool]] = None,
    ) -> List[_Timer]:
        """Pop every live timer whose deadline is at or before *now*.

        Args:
            now: Current time on the owning clock's timeline.
            owner_filter: When given, only timers whose ``owner`` satisfies
                it are popped; due timers of other owners stay queued.

        Returns:
            Uncancelled timers in deadline order; cancelled ones are discarded.
        """
        out: List[_Timer] = []
        if not self._heap:  # ⚡ no lock for the empty case
            return out
        with self._lock:
            if owner_filter is None:
                while self._heap and self._heap[0].due <= now:
                    t = heapq.heappop(self._heap)
                    if not t.cancelled:
                        out.append(t)
                return out
            # 🧵 Review ENG-06: a pump restricted to ONE owner's deadlines
            #    (a child machine sharing its parent's `SimulatedClock`).
            #    Due timers of other owners go back on the heap untouched;
            #    they keep their `seq`, so the firing order is preserved.
            keep: List[_Timer] = []
            while self._heap and self._heap[0].due <= now:
                t = heapq.heappop(self._heap)
                if t.cancelled:
                    continue
                (out if owner_filter(t.owner) else keep).append(t)
            for t in keep:
                heapq.heappush(self._heap, t)
        return out

    def is_empty(self) -> bool:
        """True when no timer (live or cancelled) is queued. Lock-free."""
        return not self._heap

    def next_due(self) -> Optional[float]:
        """Deadline of the earliest live timer, or ``None`` when idle."""
        with self._lock:
            while self._heap and self._heap[0].cancelled:
                heapq.heappop(self._heap)
            return self._heap[0].due if self._heap else None

    def __len__(self) -> int:
        if not self._heap:
            return 0
        with self._lock:
            return sum(1 for t in self._heap if not t.cancelled)


# -----------------------------------------------------------------------------
# 🕰️ RealClock -- wall time; the default
# -----------------------------------------------------------------------------
class RealClock:
    """Wall-clock time. The default for both engines.

    * **Inside a running asyncio loop** (the async `Interpreter`) a timeout
      is `loop.call_later`, exactly the primitive `asyncio.sleep` uses, so
      existing timing behaviour is unchanged -- except that the fired
      callback is invoked directly by the loop rather than by a task that
      must first win a slot in the inbox (#48).
    * **Outside a loop** (the `SyncInterpreter`) a timeout is a record in a
      deadline heap and NO thread is started. Due callbacks run when the
      owner calls :meth:`pump` -- which `SyncInterpreter.send()` and
      `tick()` do -- on the caller's thread (#50).

    One `RealClock` may serve a mixed tree (async parent, sync child). The
    lane is chosen by the ENGINE that owns the timer, not by whether a
    loop happens to be running on the calling thread (#76): the sync
    engine passes ``sync=True`` and always gets the heap, so `tick()` can
    always reach its own deadlines; the async engine passes ``sync=False``
    and always gets ``call_later``. A caller that passes neither (a
    third-party scheduler) gets the ambient-context heuristic.
    """

    def __init__(self) -> None:
        self._heap = _DeadlineHeap()

    def now(self) -> float:
        """Monotonic seconds; the origin is process-specific."""
        return time.monotonic()

    def wall_now(self) -> float:
        """Seconds since the Unix epoch (#305). Durable timers (#264) and
        audit records are anchored to THIS, never to `now()`, whose origin
        is process-specific and meaningless after a restart."""
        return time.time()

    def set_timeout(
        self,
        fn: Callable[[], Any],
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
        """Schedule *fn* after *delay_sec* seconds.

        Args:
            fn: Zero-argument callable to run when the delay elapses.
            delay_sec: Delay in seconds; negative values are treated as 0.
            owner: Opaque owner recorded on heap timers.
            sync: ``True`` forces the heap (fired by `pump`), ``False`` uses
                the running asyncio loop. ``None`` picks the loop when one is
                running and the heap otherwise. ⚠️ `loop.call_later` is not
                thread-safe: the ``sync=False`` lane must be called from the
                loop's own thread.

        Returns:
            A handle to pass to `clear_timeout`.

        Raises:
            ValueError: If *delay_sec* is NaN or infinite.
        """
        _require_finite(delay_sec, "delay_sec")
        if sync is None:
            try:
                asyncio.get_running_loop()
                sync = False
            except RuntimeError:
                sync = True
        if not sync:
            return asyncio.get_running_loop().call_later(
                max(0.0, delay_sec), fn
            )
        return self._heap.push(self.now() + max(0.0, delay_sec), fn, owner)

    def clear_timeout(self, handle: Any) -> None:
        """Cancel a handle returned by `set_timeout`. Idempotent."""
        if isinstance(handle, asyncio.TimerHandle):
            handle.cancel()
        else:
            self._heap.cancel(handle)

    def pump(self) -> int:
        """Fire every heap timer that is due now.

        Returns:
            The number of timers fired (``0`` when none are armed).
        """
        # ⚡ The sync engine pumps at the top of EVERY send(); a machine
        #    with no timers armed must not pay for a lock + monotonic() +
        #    heap scan each time. An empty list is a plain attribute read.
        if self._heap.is_empty():
            return 0
        fired, error = _fire_batch(self._heap.due_before(self.now()))
        if error is not None:
            raise error
        return fired

    def pump_filtered(self, owner_filter: Callable[[Any], bool]) -> int:
        """`pump`, restricted to the deadlines whose owner passes the filter.

        🧵 Review ENG-06: a `SyncInterpreter` child that shares its parent's
        clock pumps on its own thread and must fire only its OWN deadlines;
        the parent's stay queued for the parent's pump.

        Args:
            owner_filter: ``True`` for an ``owner`` tag this pump may fire.

        Returns:
            The number of timers fired.
        """
        if self._heap.is_empty():
            return 0
        fired, error = _fire_batch(
            self._heap.due_before(self.now(), owner_filter)
        )
        if error is not None:
            raise error
        return fired

    @property
    def pending(self) -> int:
        """Deadlines waiting in the heap (sync-engine timers only)."""
        return len(self._heap)


# -----------------------------------------------------------------------------
# 🧪 SimulatedClock -- virtual time for deterministic tests
# -----------------------------------------------------------------------------
class SimulatedClock:
    """Virtual time, mirroring XState's ``SimulatedClock``.

    Time does not pass on its own. :meth:`increment` advances virtual now
    and fires every timer that became due, in due order. :meth:`set` jumps
    to an absolute time and refuses to travel backwards.

    Async use::

        clock = SimulatedClock()
        interp = await Interpreter(machine, clock=clock).start()
        await clock.increment(30_000)   # fires the 30 s `after`, settles

    Sync use::

        clock = SimulatedClock()
        interp = SyncInterpreter(machine, clock=clock).start()
        clock.increment(30_000)

    🏛️ `increment` returns an awaitable when called inside a running loop
    and ``None`` otherwise, so the two idioms above are both correct. A
    forgotten ``await`` inside a loop emits a ``RuntimeWarning`` (see
    :class:`_MustAwait`) and the timers do NOT fire.
    """

    def __init__(self, *, wall_start: Optional[float] = None) -> None:
        self._now = 0.0
        self._heap = _DeadlineHeap()
        #: 🕰️ #305: virtual WALL time = `wall_start` + elapsed virtual
        #: seconds, so a durable-timer test can assert an absolute
        #: `due_at_wall`. Defaults to the real epoch instant the clock was
        #: built, which is what a test that never reads it expects.
        self._wall_start: float = (
            time.time() if wall_start is None else float(wall_start)
        )
        #: Interpreters to settle after each increment: async engines
        #: register coroutines, sync engines register plain callables.
        self._settlers: List[Callable[[], Any]] = []

    # -- Clock protocol ----------------------------------------------------
    def now(self) -> float:
        """Current virtual time in seconds."""
        return self._now

    def wall_now(self) -> float:
        """Virtual epoch seconds: ``wall_start`` plus elapsed virtual time."""
        return self._wall_start + self._now

    def set_timeout(
        self,
        fn: Callable[[], Any],
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
        """Schedule *fn* at virtual ``now + delay_sec`` (never fires alone).

        Args:
            fn: Zero-argument callable run by `increment`/`set`/`pump`.
            delay_sec: Delay in virtual seconds; negative is treated as 0.
            owner: Opaque owner recorded on the timer.
            sync: Ignored; a simulated clock has a single lane.

        Returns:
            A handle to pass to `clear_timeout`.

        Raises:
            ValueError: If *delay_sec* is NaN or infinite.
        """
        _require_finite(delay_sec, "delay_sec")
        return self._heap.push(self._now + max(0.0, delay_sec), fn, owner)

    def clear_timeout(self, handle: Any) -> None:
        """Cancel a handle returned by `set_timeout`. Idempotent."""
        self._heap.cancel(handle)

    def pump(self) -> int:
        """Fire every timer due at the simulated time.

        Returns:
            The number of timers fired (``0`` when none are armed).
        """
        if self._heap.is_empty():  # ⚡ see RealClock.pump
            return 0
        fired, error = _fire_batch(self._heap.due_before(self._now))
        if error is not None:
            raise error
        return fired

    def pump_filtered(self, owner_filter: Callable[[Any], bool]) -> int:
        """`pump`, restricted to the deadlines whose owner passes the filter.

        See `RealClock.pump_filtered` (review ENG-06). The test-facing
        `advance()` / `increment()` / `fire_until()` stay unfiltered: they
        run on the test thread, which owns every attached interpreter.

        Args:
            owner_filter: ``True`` for an ``owner`` tag this pump may fire.

        Returns:
            The number of timers fired.
        """
        if self._heap.is_empty():
            return 0
        fired, error = _fire_batch(
            self._heap.due_before(self._now, owner_filter)
        )
        if error is not None:
            raise error
        return fired

    # -- test-facing API ---------------------------------------------------
    @property
    def pending(self) -> int:
        """Number of live (uncancelled) timers."""
        return len(self._heap)

    def next_due(self) -> Optional[float]:
        """Virtual time (seconds) of the earliest live timer, or ``None``.

        📝 Public so `persistence.replay()` can walk recorded `after` steps
        one timer at a time without reaching into the heap (review #262).
        """
        return self._heap.next_due()

    def fire_until(self, target: float) -> None:
        """Advance to *target* (virtual seconds), firing due timers in order
        and settling attached SYNC interpreters -- never awaiting.

        ⚠️ For callers that know they hold no running loop, or that run
        the sync engine from inside async code (`replay()` does): the
        `increment()` / `set()` API detects a running loop and returns an
        awaitable instead, which `replay()` cannot use.

        Args:
            target: Absolute virtual time in seconds.

        Raises:
            ValueError: On a backwards or non-finite target.
        """
        _require_finite(target, "target")
        if target < self._now:
            raise ValueError(
                f"SimulatedClock.fire_until({target}) would move backwards "
                f"from {self._now}"
            )
        self._drain_sync(target)

    def increment(self, ms: float) -> Union[None, Awaitable[None]]:
        """Advance virtual time by *ms* and fire what became due, in order.

        ⚠️ The return type depends on the ambient context (awaitable inside
        a running loop, ``None`` otherwise), which one signature cannot
        express; typed code should call `advance` / `advance_sync`.

        Timers are fired ONE AT A TIME, re-reading the heap between them,
        so a timer that schedules another timer inside the same window
        (an `after` chain) is honoured in the correct order.
        """
        _require_finite(ms, "ms")
        if ms < 0:
            raise ValueError("SimulatedClock cannot move backwards")
        return self._advance_to(self._now + ms / 1000.0)

    async def advance(self, ms: float) -> None:
        """Typed async twin of `increment` -- always awaitable (RU-28).

        ``await clock.increment(ms)`` is a ``mypy --strict`` error because
        `increment` returns ``None`` outside a loop; use this from async
        code instead.

        Args:
            ms: Milliseconds to advance; must be finite and >= 0.

        Raises:
            ValueError: On a negative or non-finite *ms*.
        """
        await self._drain_async(self._checked_target(ms))

    def advance_sync(self, ms: float) -> None:
        """Typed sync twin of `increment` -- never awaits (RU-28).

        Args:
            ms: Milliseconds to advance; must be finite and >= 0.

        Raises:
            ValueError: On a negative or non-finite *ms*.
        """
        self._drain_sync(self._checked_target(ms))

    def _checked_target(self, ms: float) -> float:
        """Validate a relative advance and return the absolute target."""
        _require_finite(ms, "ms")
        if ms < 0:
            raise ValueError("SimulatedClock cannot move backwards")
        return self._now + ms / 1000.0

    def set(self, ms: float) -> Union[None, Awaitable[None]]:
        """Jump to absolute virtual time *ms*; raises if that is in the past."""
        _require_finite(ms, "ms")
        target = ms / 1000.0
        if target < self._now:
            raise ValueError(
                f"SimulatedClock.set({ms}) would move backwards from "
                f"{self._now * 1000:.0f} ms"
            )
        return self._advance_to(target)

    def _advance_to(self, target: float) -> Union[None, Awaitable[None]]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._drain_sync(target)
            return None
        return _MustAwait(self._drain_async(target))

    def _drain_sync(self, target: float) -> None:
        # 🔥 A raising callback must neither strand the rest of the window
        #    nor leave `now()` mid-way: finish the drain, then re-raise the
        #    first error (RU-01).
        first_error: Optional[Exception] = None
        while True:
            nxt = self._heap.next_due()
            if nxt is None or nxt > target:
                break
            self._now = nxt
            _, error = _fire_batch(self._heap.due_before(nxt))
            first_error = first_error or error
            self._settle_sync()
        self._now = target
        self._settle_sync()
        if first_error is not None:
            raise first_error

    def _settle_sync(self) -> None:
        """Let every attached SYNC interpreter process what timers queued."""
        for settle in list(self._settlers):
            result = settle()
            if hasattr(result, "close"):  # an async settler in sync mode
                result.close()

    async def _drain_async(self, target: float) -> None:
        first_error: Optional[Exception] = None  # 🔥 see _drain_sync
        while True:
            nxt = self._heap.next_due()
            if nxt is None or nxt > target:
                break
            self._now = nxt
            _, error = _fire_batch(self._heap.due_before(nxt))
            first_error = first_error or error
            await self._settle()
        self._now = target
        await self._settle()
        if first_error is not None:
            raise first_error

    async def _settle(self) -> None:
        """Let every attached interpreter process what the timers queued.

        A clock may serve BOTH engines at once (an async parent with a sync
        child); sync settlers are plain callables that return ``None``,
        async ones return a coroutine. Await only what is awaitable.
        """
        for settle in list(self._settlers):
            result = settle()
            if inspect.isawaitable(result):
                await result
        # One extra turn for anything the settlers themselves enqueued.
        await asyncio.sleep(0)

    def _attach(self, settle: Callable[[], Any]) -> None:
        """Interpreter hook: register a drain-the-inbox callable.

        Async engines pass a coroutine function; sync engines a plain one.
        """
        if settle not in self._settlers:
            self._settlers.append(settle)

    def _detach(self, settle: Callable[[], Any]) -> None:
        """Interpreter hook: unregister a settle callable (#115).

        The pair to `_attach`. Bound methods compare equal by (self, func),
        so the interpreter can pass the same attribute it registered.
        """
        try:
            self._settlers.remove(settle)
        except ValueError:
            pass


class _MustAwait:
    """Awaitable that WARNS if garbage-collected without being awaited.

    Mirrors asyncio's "coroutine was never awaited" warning, because a
    silently un-awaited `increment()` inside a loop is exactly the race the
    async form exists to prevent.

    ⚠️ It is a ``RuntimeWarning``, not an exception: ``__del__`` cannot
    raise (errors there go to ``sys.unraisablehook``), the warning is
    attributed to the finaliser's frame rather than the caller, and
    ``-W error`` cannot promote it into the awaiting code path.
    """

    __slots__ = ("_coro", "_awaited")

    def __init__(self, coro: Awaitable[None]) -> None:
        self._coro = coro
        self._awaited = False

    def __await__(self):  # type: ignore[no-untyped-def]
        self._awaited = True
        return self._coro.__await__()

    def __del__(self) -> None:  # pragma: no cover - diagnostic only
        if not self._awaited:
            import warnings

            warnings.warn(
                "SimulatedClock.increment()/set() was called inside a running "
                "event loop but never awaited; timers did not fire. Use "
                "`await clock.increment(ms)`.",
                RuntimeWarning,
                stacklevel=2,
            )
            coro = self._coro
            if hasattr(coro, "close"):
                coro.close()


__all__ = ["Clock", "RealClock", "SimulatedClock"]
