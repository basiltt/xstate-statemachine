# src/xstate_statemachine/_graph_model.py
# -----------------------------------------------------------------------------
# 🧱 The graph data model -- Step, Path, step execution, forced outcomes
# -----------------------------------------------------------------------------
# 🏛️ Split out of `graph.py` (#269 battle). `graph.py` re-exports `Step` and
#    `Path`; the explorer imports the step runner from here.
# -----------------------------------------------------------------------------
"""Data model and step execution for `xstate_statemachine.graph`."""

from __future__ import annotations

import contextlib
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple

from .clock import SimulatedClock
from .sync_interpreter import SyncInterpreter

logger = logging.getLogger("xstate_statemachine.graph")

Config = FrozenSet[str]


#: ⏰ Clock advance used to fire a NAMED `after` delay whose duration is not
#: known statically. Large enough to exceed any realistic delay.
UNKNOWN_DELAY_MS = 10**9


# -----------------------------------------------------------------------------
# 🧱 Data model
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Step:
    """One edge: an event sent, or a clock advance firing an `after`.

    Attributes:
        event: Event type sent, or ``None`` for a clock advance.
        delay_ms: Clock advance in ms for `after` steps; ``None`` for
            events and for named delays of unknown duration (the latter
            carry a ``"delay:<name>=unknown"`` assumption).
        from_states: Configuration before the step.
        to_states: Configuration after the step.
        assumptions: Forced guard / service outcomes, e.g.
            ``("guard:isValid=False",)`` or ``("service:fetch=error",)``.
    """

    event: Optional[str]
    delay_ms: Optional[float]
    from_states: FrozenSet[str]
    to_states: FrozenSet[str]
    assumptions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Path:
    """A replayable sequence of steps ending in ``final_states``."""

    steps: Tuple[Step, ...]
    final_states: FrozenSet[str]

    def replay(
        self, interp: SyncInterpreter[Any], clock: SimulatedClock
    ) -> None:
        """Drive *interp* (on *clock*) through every step.

        Starts the interpreter if it has not been started. Each step's
        ``assumptions`` are forced on ``interp.machine.logic`` for the
        duration of that step only.
        """
        if interp.status == "uninitialized":
            interp.start()
        # 🔇 #269 battle: a `service:<name>=error` assumption is the path's
        #    intent, not an incident -- the engine logs each forced failure
        #    at ERROR with a traceback (one per generated test under
        #    `xsm_path`). Quiet the library logger for forced steps only.
        for step in self.steps:
            if any(a.startswith("service:") for a in step.assumptions):
                with _quiet():
                    _apply_step(interp, clock, step)
            else:
                _apply_step(interp, clock, step)

    def event_string(self) -> str:
        """The ``xsm simulate --events`` grammar: ``"SUBMIT,+2000,PAY"``."""
        parts: List[str] = []
        for step in self.steps:
            if step.event is not None:
                parts.append(step.event)
            else:
                parts.append(f"+{_fmt_ms(_advance_of(step))}")
        return ",".join(parts)

    @property
    def total_delay_ms(self) -> float:
        """Sum of every clock advance on the path."""
        return sum(_advance_of(s) for s in self.steps if s.event is None)


_QUIET_LOCK = threading.Lock()
_quiet_depth = 0
_quiet_saved = logging.NOTSET


@contextlib.contextmanager
def _quiet() -> Iterator[None]:
    """Silence the library logger; re-entrant and thread-safe.

    🐛 #269 battle (A5): each caller used to save/restore the level
    itself. Two overlapping traversals on different threads restored in
    the wrong order (A saves INFO, B saves CRITICAL, A restores INFO, B
    restores CRITICAL) and the library logger stayed muted for the rest
    of the process. Now the FIRST entrant saves and the LAST restores.
    """
    global _quiet_depth, _quiet_saved
    lib_logger = logging.getLogger("xstate_statemachine")
    with _QUIET_LOCK:
        if _quiet_depth == 0:
            _quiet_saved = lib_logger.level
            lib_logger.setLevel(logging.CRITICAL)
        _quiet_depth += 1
    try:
        yield
    finally:
        with _QUIET_LOCK:
            _quiet_depth -= 1
            if _quiet_depth == 0:
                lib_logger.setLevel(_quiet_saved)


def _fmt_ms(ms: float) -> str:
    return str(int(ms)) if float(ms).is_integer() else str(ms)


def _advance_of(step: Step) -> float:
    return UNKNOWN_DELAY_MS if step.delay_ms is None else step.delay_ms


# -----------------------------------------------------------------------------
# 🔧 Step execution (shared by exploration and `Path.replay`)
# -----------------------------------------------------------------------------
def _forced_guard(value: bool) -> Any:
    def _guard(c: Any, e: Any) -> bool:
        return value

    return _guard


def _failing_service(name: str) -> Any:
    def _service(i: Any, c: Any, e: Any) -> Any:
        raise RuntimeError(f"graph: service '{name}' forced to error")

    return _service


@contextlib.contextmanager
def _forced(logic: Any, assumptions: Tuple[str, ...]) -> Iterator[None]:
    """Temporarily force guard / service outcomes named in *assumptions*."""
    saved: List[Tuple[Dict[str, Any], str, Any]] = []

    def patch(table: Dict[str, Any], key: str, value: Any) -> None:
        saved.append((table, key, table.get(key, _MISSING)))
        table[key] = value

    try:
        for a in assumptions:
            kind, _, rest = a.partition(":")
            name, _, val = rest.rpartition("=")
            if kind == "guard":
                keys = list(logic.guards) if name == "*" else [name]
                for k in keys:
                    patch(logic.guards, k, _forced_guard(val == "True"))
            elif kind == "service" and val == "error":
                patch(logic.services, name, _failing_service(name))
        yield
    finally:
        for table, key, old in reversed(saved):
            if old is _MISSING:
                table.pop(key, None)
            else:
                table[key] = old


_MISSING = object()


def _apply_step(
    interp: SyncInterpreter[Any], clock: SimulatedClock, step: Step
) -> None:
    with _forced(interp.machine.logic, step.assumptions):
        if step.event is not None:
            interp.send(step.event)
        elif step.delay_ms is None:
            # ⏰ reviewer H1 (#269 battle): a NAMED delay has no static
            #    duration. Advancing a fixed 10^9 ms fired the WHOLE chain
            #    of later timers in one step -- `a --after slow--> b
            #    --after 300--> c` yielded only `{a, d}`; `b` and `c` were
            #    "unreachable". Advance to the EARLIEST pending deadline
            #    instead (the named one, by construction the only one
            #    armed in the just-entered state), so later numeric
            #    `after`s stay their own steps. No deadline at all (the
            #    delay resolved to nothing): fall back to the sentinel.
            nxt = clock._heap.next_due()
            ms = (
                UNKNOWN_DELAY_MS
                if nxt is None
                else max((nxt - clock.now()) * 1000.0, 0.0)
            )
            clock.increment(ms)
        else:
            clock.increment(step.delay_ms)
