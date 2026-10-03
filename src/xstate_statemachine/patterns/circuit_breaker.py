# src/xstate_statemachine/patterns/circuit_breaker.py
# -----------------------------------------------------------------------------
# ⚡ CircuitBreaker -- Nygard's pattern as a statechart (#265)
# -----------------------------------------------------------------------------
# 🏛️ Dogfooding: the breaker IS a three-state chart --
#
#     closed --FAILURE[threshold reached]--> open
#     open   --after(cooldown)-------------> half_open
#     half_open --SUCCESS--> closed   |   half_open --FAILURE--> open
#
# -- run on a `SyncInterpreter` (thread-free timers; `tick()` drains the
#    cooldown) behind ONE lock. `xsm inspect` renders it from
#    `CIRCUIT_BREAKER_CONFIG`. Because the chart owns the state, the usual
#    half-open race ("two callers both think they're the probe") is solved
#    where it belongs: `admit()` is a guarded transition inside the lock,
#    so exactly `half_open_max_calls` probes get through per half-open
#    window, however many threads hammer it.
#
# 📝 Why the lock wraps `tick()` too (review amendment): the cooldown is an
#    `after` on the sync engine, which fires only when someone pumps the
#    clock. `state` therefore ticks first -- otherwise it reports a stale
#    `open` after the cooldown has elapsed -- and that tick must not race a
#    concurrent `call()`.
# -----------------------------------------------------------------------------
"""`CircuitBreaker`, `circuit_breaker()` decorator, `CIRCUIT_BREAKER_CONFIG`."""

from __future__ import annotations

import asyncio
import copy
import functools
import inspect
import math
import threading
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Literal,
    Optional,
    Tuple,
    TypeVar,
)

from ..clock import Clock
from ..exceptions import InterpreterStoppedError, XStateMachineError
from ..factory import create_machine
from ..machine_logic import MachineLogic
from ..sync_interpreter import SyncInterpreter

__all__ = [
    "CIRCUIT_BREAKER_CONFIG",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "circuit_breaker",
]

T = TypeVar("T")
CircuitState = Literal["closed", "open", "half_open"]

#: The breaker chart. `cooldown` is a NAMED delay so the same JSON serves
#: every breaker; `failure_threshold` / `half_open_max_calls` live in
#: context so guards read them. Feed it to `xsm inspect` as-is.
CIRCUIT_BREAKER_CONFIG: Dict[str, Any] = {
    "id": "circuitBreaker",
    "version": "1",
    "initial": "closed",
    "context": {
        "failures": 0,
        "failure_threshold": 5,
        "half_open_calls": 0,
        "half_open_max_calls": 1,
        "opened_count": 0,
    },
    "states": {
        "closed": {
            "description": "Calls pass through; consecutive failures counted.",
            "entry": "resetFailures",
            "on": {
                "SUCCESS": {"actions": "resetFailures"},
                "FAILURE": [
                    {
                        "guard": "thresholdReached",
                        "target": "open",
                        "actions": "countFailure",
                    },
                    {"actions": "countFailure"},
                ],
            },
        },
        "open": {
            "description": "Calls fail fast; waiting out the cooldown.",
            "tags": ["rejecting"],
            "entry": "countOpen",
            "after": {"cooldown": {"target": "half_open"}},
        },
        "half_open": {
            "description": "A bounded number of probe calls is admitted.",
            "entry": "resetProbes",
            "on": {
                "PROBE": {"guard": "probeAvailable", "actions": "countProbe"},
                "SUCCESS": {"target": "closed"},
                "FAILURE": {"target": "open"},
            },
        },
    },
}


class CircuitOpenError(XStateMachineError):
    """Raised by `CircuitBreaker.call` / `acall` when the circuit is open
    (or half-open with no probe slot left). The wrapped function was NOT
    invoked."""

    def __init__(self, name: str, state: str) -> None:
        self.breaker = name
        self.state = state
        super().__init__(
            f"Circuit '{name}' is {state}; call rejected without invoking "
            f"the target."
        )


def _threshold_reached(ctx: Dict[str, Any], e: Any) -> bool:
    # +1: this FAILURE is being counted by the same transition.
    return int(ctx["failures"]) + 1 >= int(ctx["failure_threshold"])


def _probe_available(ctx: Dict[str, Any], e: Any) -> bool:
    return int(ctx["half_open_calls"]) < int(ctx["half_open_max_calls"])


def _count_failure(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["failures"] = int(ctx["failures"]) + 1


def _reset_failures(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["failures"] = 0


def _count_open(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["opened_count"] = int(ctx["opened_count"]) + 1


def _reset_probes(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["half_open_calls"] = 0


def _count_probe(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["half_open_calls"] = int(ctx["half_open_calls"]) + 1


def circuit_breaker_logic(cooldown_ms: float) -> MachineLogic:
    """The logic `CIRCUIT_BREAKER_CONFIG` needs, with the cooldown bound."""
    return MachineLogic(
        actions={
            "countFailure": _count_failure,
            "resetFailures": _reset_failures,
            "countOpen": _count_open,
            "resetProbes": _reset_probes,
            "countProbe": _count_probe,
        },
        guards={
            "thresholdReached": _threshold_reached,
            "probeAvailable": _probe_available,
        },
        delays={"cooldown": float(cooldown_ms)},
    )


class CircuitBreaker:
    """A thread-safe circuit breaker driven by `CIRCUIT_BREAKER_CONFIG`.

    Args:
        failure_threshold: Consecutive failures that open the circuit.
        cooldown_ms: How long it stays open before admitting probes.
        half_open_max_calls: Probes admitted per half-open window.
        clock: A `Clock`; pass a `SimulatedClock` in tests and
            ``increment(cooldown_ms + 1)`` to reach ``half_open``.
        plugins: Attached to the internal interpreter (a
            `LoggingInspector` shows every trip).
        name: Used in `CircuitOpenError` messages; defaults to the config id.
        exceptions: Exception types that count as a failure (default: any
            `Exception`). Others propagate without touching the breaker.

    ``call(fn, *a, **kw)`` / ``await acall(fn, *a, **kw)`` run *fn* if the
    breaker admits it, record the outcome, and re-raise *fn*'s exception.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_ms: float = 30_000.0,
        half_open_max_calls: int = 1,
        clock: Optional[Clock] = None,
        plugins: Iterable[Any] = (),
        name: Optional[str] = None,
        exceptions: tuple = (Exception,),
    ) -> None:
        if failure_threshold < 1 or half_open_max_calls < 1:
            raise ValueError(
                "failure_threshold and half_open_max_calls must be >= 1"
            )
        # 📝 #265 battle: a negative cooldown half-opened instantly, NaN
        #    and inf left the circuit open forever (the `after` was
        #    silently skipped). Silent acceptance is a bug -- fail loudly.
        cooldown = float(cooldown_ms)
        if not math.isfinite(cooldown) or cooldown < 0:
            raise ValueError("cooldown_ms must be a finite number >= 0")
        cfg = copy.deepcopy(CIRCUIT_BREAKER_CONFIG)
        cfg["context"]["failure_threshold"] = int(failure_threshold)
        cfg["context"]["half_open_max_calls"] = int(half_open_max_calls)
        if name:
            cfg["id"] = name
        self.name = cfg["id"]
        self.exceptions = exceptions
        self._lock = threading.RLock()
        # 🏛️ #265 battle: bumped by `reset()`; part of the admission token.
        self._generation = 0
        machine = create_machine(cfg, logic=circuit_breaker_logic(cooldown_ms))
        self._interp: SyncInterpreter[Any] = SyncInterpreter(
            machine, clock=clock
        )
        for p in plugins:
            self._interp.use(p)
        self._interp.start()

    # -- state ------------------------------------------------------------------
    def _leaf(self) -> str:
        ids = self._interp.current_state_ids
        return sorted(ids)[0].rsplit(".", 1)[-1] if ids else "closed"

    @property
    def state(self) -> CircuitState:
        """``"closed"`` / ``"open"`` / ``"half_open"``. Ticks the clock
        first so an elapsed cooldown is reflected (review amendment)."""
        with self._lock:
            self._interp.tick()
            return self._leaf()  # type: ignore[return-value]

    @property
    def failures(self) -> int:
        """Consecutive failures counted in the current closed window."""
        with self._lock:
            return int(self._interp.context["failures"])

    @property
    def opened_count(self) -> int:
        """How many times the circuit has tripped open."""
        with self._lock:
            return int(self._interp.context["opened_count"])

    @property
    def interpreter(self) -> SyncInterpreter[Any]:
        """The underlying interpreter (read-only use: snapshots, plugins)."""
        return self._interp

    # -- admission ----------------------------------------------------------------
    def _window(self, state: str) -> Tuple[int, int, str]:
        return (
            self._generation,
            int(self._interp.context["opened_count"]),
            state,
        )

    def _admit(self) -> Tuple[int, int, str]:
        """Decide, under the lock, whether one call may proceed.

        Returns the admission *window* the outcome must be recorded in.
        """
        with self._lock:
            # 📝 #265 battle: after `close()` the interpreter is stopped
            #    and every `send` is dropped -- `call()` used to run the
            #    target with no protection at all. Fail loudly instead.
            if self._interp.status != "running":
                raise InterpreterStoppedError(
                    f"Circuit '{self.name}' is closed (stopped); "
                    f"call rejected without invoking the target."
                )
            self._interp.tick()
            state = self._leaf()
            if state == "closed":
                return self._window(state)
            if state == "half_open":
                rcp = self._interp.send("PROBE", wait=True)
                if rcp is not None and rcp.changed:
                    # probe slot taken by THIS caller
                    return self._window(state)
            raise CircuitOpenError(self.name, state)

    def _record(self, ok: bool, window: Tuple[int, int, str]) -> None:
        with self._lock:
            # 🏛️ #265 battle: an outcome only counts in the window that
            #    admitted it. A slow call admitted while `closed` whose
            #    SUCCESS landed after the breaker had opened and
            #    half-opened used to CLOSE the circuit without any probe
            #    (and a late FAILURE re-opened it). Late results from an
            #    earlier window -- or from before `reset()` -- are ignored.
            if window != self._window(self._leaf()):
                return
            self._interp.send("SUCCESS" if ok else "FAILURE")

    def reset(self) -> None:
        """Force the circuit closed (operator override)."""
        with self._lock:
            self._generation += 1  # in-flight outcomes become stale
            # A SUCCESS closes half_open; from open we must re-start.
            if self._leaf() == "open":
                opened = int(self._interp.context["opened_count"])
                self._interp.stop()
                machine = self._interp.machine
                clock = self._interp.clock
                plugins = list(self._interp.plugins)
                self._interp = SyncInterpreter(machine, clock=clock)
                for p in plugins:
                    self._interp.use(p)
                self._interp.start()
                # 📝 #265 battle: `opened_count` is a lifetime trip
                #    counter; the rebuild must not zero it.
                self._interp.context["opened_count"] = opened
            else:
                self._interp.send("SUCCESS")

    # -- calling ---------------------------------------------------------------------
    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run *fn* through the breaker (sync target)."""
        window = self._admit()
        try:
            result = fn(*args, **kwargs)
        except self.exceptions:
            self._record(False, window)
            raise
        self._record(True, window)
        return result

    async def acall(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run *fn* through the breaker; awaits a coroutine result.

        The breaker's own bookkeeping is synchronous and lock-guarded, so
        one `CircuitBreaker` may be shared by async tasks and threads.
        """
        window = self._admit()
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except asyncio.CancelledError:
            raise
        except self.exceptions:
            self._record(False, window)
            raise
        self._record(True, window)
        return result

    def close(self) -> None:
        """Stop the internal interpreter."""
        with self._lock:
            self._interp.stop()


def circuit_breaker(
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: one `CircuitBreaker` per decorated function.

    Works on sync and ``async def`` targets. The breaker is exposed as
    ``wrapper.breaker`` for inspection and tests.

    Example::

        @circuit_breaker(failure_threshold=3, cooldown_ms=5_000)
        def fetch(url): ...
    """

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        # 📝 #265 battle: a generator's body runs AFTER the wrapper has
        #    returned, so the breaker would record SUCCESS before any work
        #    happened and never see the failures. Refuse loudly.
        if inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
            raise TypeError(
                "circuit_breaker() cannot wrap a generator function: its "
                "outcome is unknown when the call returns"
            )
        # 📝 #265 battle: copy -- `setdefault` on the shared kwargs made a
        #    reused decorator name every later breaker after the first fn.
        opts = dict(kwargs)
        opts.setdefault("name", getattr(fn, "__name__", "circuitBreaker"))
        breaker = CircuitBreaker(**opts)
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def awrapper(*a: Any, **kw: Any) -> Any:
                return await breaker.acall(fn, *a, **kw)

            awrapper.breaker = breaker  # type: ignore[attr-defined]
            return awrapper

        @functools.wraps(fn)
        def wrapper(*a: Any, **kw: Any) -> Any:
            return breaker.call(fn, *a, **kw)

        wrapper.breaker = breaker  # type: ignore[attr-defined]
        return wrapper

    return deco
