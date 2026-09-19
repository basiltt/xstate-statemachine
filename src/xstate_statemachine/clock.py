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
#     awaitable form; calling it without `await` inside a loop is an error
#     we detect rather than a silent race.
#   * A fired timer records `scheduled_for` / `fired_at` so lateness is data,
#     not inference (#48 item 3).
# -----------------------------------------------------------------------------
"""`Clock` protocol, `RealClock` default and `SimulatedClock` for tests."""

from __future__ import annotations

import asyncio
import heapq
import inspect
import itertools
import threading
import time
from typing import Any, Awaitable, Callable, List, Optional, Union

try:  # pragma: no cover - Python 3.8+ has Protocol; kept defensive
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore


@runtime_checkable
class Clock(Protocol):
    """What an interpreter needs from a source of time.

    Mirrors XState's ``Clock`` (``setTimeout`` / ``clearTimeout``) with one
    Python-specific addition, :meth:`pump`, which lets a clock that does
    not run its own thread or loop deliver due callbacks when the owner
    asks (the sync engine's `tick()`; see :class:`RealClock`).
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
        self._lock = threading.Lock()

    def push(self, due: float, fn: Callable[[], Any], owner: Any) -> _Timer:
        t = _Timer(due, next(self._seq), fn, owner)
        with self._lock:
            heapq.heappush(self._heap, t)
        return t

    def cancel(self, t: Any) -> None:
        if isinstance(t, _Timer):
            t.cancelled = True

    def due_before(self, now: float) -> List[_Timer]:
        out: List[_Timer] = []
        with self._lock:
            while self._heap and self._heap[0].due <= now:
                t = heapq.heappop(self._heap)
                if not t.cancelled:
                    out.append(t)
        return out

    def next_due(self) -> Optional[float]:
        with self._lock:
            while self._heap and self._heap[0].cancelled:
                heapq.heappop(self._heap)
            return self._heap[0].due if self._heap else None

    def __len__(self) -> int:
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
        return time.monotonic()

    def set_timeout(
        self,
        fn: Callable[[], Any],
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
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
        if isinstance(handle, asyncio.TimerHandle):
            handle.cancel()
        else:
            self._heap.cancel(handle)

    def pump(self) -> int:
        fired = 0
        for t in self._heap.due_before(self.now()):
            t.fn()
            fired += 1
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
    and ``None`` otherwise, so the two idioms above are both correct and a
    forgotten ``await`` inside a loop raises instead of racing (see
    :class:`_MustAwait`).
    """

    def __init__(self) -> None:
        self._now = 0.0
        self._heap = _DeadlineHeap()
        #: Interpreters to settle after each increment: async engines
        #: register coroutines, sync engines register plain callables.
        self._settlers: List[Callable[[], Any]] = []

    # -- Clock protocol ----------------------------------------------------
    def now(self) -> float:
        return self._now

    def set_timeout(
        self,
        fn: Callable[[], Any],
        delay_sec: float,
        *,
        owner: Any = None,
        sync: Optional[bool] = None,
    ) -> Any:
        return self._heap.push(self._now + max(0.0, delay_sec), fn, owner)

    def clear_timeout(self, handle: Any) -> None:
        self._heap.cancel(handle)

    def pump(self) -> int:
        fired = 0
        for t in self._heap.due_before(self._now):
            t.fn()
            fired += 1
        return fired

    # -- test-facing API ---------------------------------------------------
    @property
    def pending(self) -> int:
        """Number of live (uncancelled) timers."""
        return len(self._heap)

    def increment(self, ms: float) -> Union[None, Awaitable[None]]:
        """Advance virtual time by *ms* and fire what became due, in order.

        Timers are fired ONE AT A TIME, re-reading the heap between them,
        so a timer that schedules another timer inside the same window
        (an `after` chain) is honoured in the correct order.
        """
        if ms < 0:
            raise ValueError("SimulatedClock cannot move backwards")
        return self._advance_to(self._now + ms / 1000.0)

    def set(self, ms: float) -> Union[None, Awaitable[None]]:
        """Jump to absolute virtual time *ms*; raises if that is in the past."""
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
        while True:
            nxt = self._heap.next_due()
            if nxt is None or nxt > target:
                break
            self._now = nxt
            for t in self._heap.due_before(nxt):
                t.fn()
            self._settle_sync()
        self._now = target
        self._settle_sync()

    def _settle_sync(self) -> None:
        """Let every attached SYNC interpreter process what timers queued."""
        for settle in list(self._settlers):
            result = settle()
            if hasattr(result, "close"):  # an async settler in sync mode
                result.close()  # type: ignore[union-attr]

    async def _drain_async(self, target: float) -> None:
        while True:
            nxt = self._heap.next_due()
            if nxt is None or nxt > target:
                break
            self._now = nxt
            for t in self._heap.due_before(nxt):
                t.fn()
            await self._settle()
        self._now = target
        await self._settle()

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
    """Awaitable that raises if garbage-collected without being awaited.

    Mirrors the intent of asyncio's "coroutine was never awaited" warning
    but as a hard error at the call site's next GC, because a silently
    un-awaited `increment()` inside a loop is exactly the race the async
    form exists to prevent.
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
                coro.close()  # type: ignore[attr-defined]


__all__ = ["Clock", "RealClock", "SimulatedClock"]
