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
import threading
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Literal,
    Optional,
    TypeVar,
)

from ..clock import Clock
from ..exceptions import XStateMachineError
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
        cfg = copy.deepcopy(CIRCUIT_BREAKER_CONFIG)
        cfg["context"]["failure_threshold"] = int(failure_threshold)
        cfg["context"]["half_open_max_calls"] = int(half_open_max_calls)
        if name:
            cfg["id"] = name
        self.name = cfg["id"]
        self.exceptions = exceptions
        self._lock = threading.RLock()
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
    def _admit(self) -> None:
        """Decide, under the lock, whether one call may proceed."""
        with self._lock:
            self._interp.tick()
            state = self._leaf()
            if state == "closed":
                return
            if state == "half_open":
                rcp = self._interp.send("PROBE", wait=True)
                if rcp is not None and rcp.changed:
                    return  # probe slot taken by THIS caller
            raise CircuitOpenError(self.name, state)

    def _record(self, ok: bool) -> None:
        with self._lock:
            self._interp.send("SUCCESS" if ok else "FAILURE")

    def reset(self) -> None:
        """Force the circuit closed (operator override)."""
        with self._lock:
            # A SUCCESS closes half_open; from open we must re-start.
            if self._leaf() == "open":
                self._interp.stop()
                machine = self._interp.machine
                clock = self._interp.clock
                plugins = list(self._interp.plugins)
                self._interp = SyncInterpreter(machine, clock=clock)
                for p in plugins:
                    self._interp.use(p)
                self._interp.start()
            else:
                self._interp.send("SUCCESS")

    # -- calling ---------------------------------------------------------------------
    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run *fn* through the breaker (sync target)."""
        self._admit()
        try:
            result = fn(*args, **kwargs)
        except self.exceptions:
            self._record(False)
            raise
        self._record(True)
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
        self._admit()
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except asyncio.CancelledError:
            raise
        except self.exceptions:
            self._record(False)
            raise
        self._record(True)
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
        kwargs.setdefault("name", getattr(fn, "__name__", "circuitBreaker"))
        breaker = CircuitBreaker(**kwargs)
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
