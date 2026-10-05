# src/xstate_statemachine/contrib/testing/gwt.py
# -----------------------------------------------------------------------------
# 🧪 given / when / then -- a readable one-liner per behaviour (#272)
# -----------------------------------------------------------------------------
# 🏛️ The #272 acceptance criteria promised a fluent helper over the sync
#    engine ("`given(machine).in_state(...).when(...).then_state(...)`")
#    and it never shipped; the battle scenario needed it to read like the
#    team's specs. It is a THIN wrapper: `SyncInterpreter` + `SimulatedClock`
#    + `from_state_ids` for the starting configuration; every assertion
#    failure is an `AssertionError` whose message names the step, the
#    expected and the actual -- never a bare comparison.
# -----------------------------------------------------------------------------
"""``given(machine).in_state(...).when(...).then_state(...)``."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Union

from ...clock import SimulatedClock
from ...events import Event, Receipt
from ...models import MachineNode
from ...persistence.adopt import from_state_ids
from ...sync_interpreter import SyncInterpreter

__all__ = ["Scenario", "given"]


class Scenario:
    """The object `given()` returns; every method returns ``self``.

    The interpreter is built lazily on the first ``when`` so ``in_state``
    / ``with_context`` can be given in any order. ``interp`` and ``clock``
    are public for anything the fluent surface does not cover.
    """

    def __init__(self, machine: MachineNode[Any]) -> None:
        self.machine = machine
        self.clock = SimulatedClock()
        self._states: Optional[List[str]] = None
        self._context: Optional[Dict[str, Any]] = None
        self._interp: Optional[SyncInterpreter[Any]] = None
        self.receipt: Optional[Receipt] = None
        self._steps: List[str] = []

    # -- given ----------------------------------------------------------------
    def in_state(self, *state_ids: str) -> "Scenario":
        """Start in this configuration (full ids or leaf names)."""
        self._require_not_started("in_state")
        if not state_ids:
            raise ValueError("given(...).in_state() needs at least one state")
        full = [self._full_id(s) for s in state_ids]
        for sid in full:
            node = self.machine.get_state_by_id(sid)
            if node is not None and node.type == "history":
                # 🔥 battle #272: a history node is a pseudostate, never
                #    active; from_state_ids' "conflict" message misled.
                raise ValueError(
                    f"given/then: {sid!r} is a history pseudostate and is "
                    f"never active; name the state it would restore"
                )
        self._states = full
        self._steps.append(f"in_state({', '.join(map(repr, state_ids))})")
        return self

    def with_context(self, **context: Any) -> "Scenario":
        """Start with these context keys (merged over the chart's)."""
        self._require_not_started("with_context")
        self._context = {**(self._context or {}), **context}
        self._steps.append(f"with_context({', '.join(sorted(context))})")
        return self

    # -- when -----------------------------------------------------------------
    def when(
        self, event: Union[str, Event, Dict[str, Any]], **payload: Any
    ) -> "Scenario":
        """Send *event*; the `Receipt` is kept on ``self.receipt``."""
        interp = self._ensure_live("when")
        label = (
            event if isinstance(event, str) else getattr(event, "type", event)
        )
        self._steps.append(f"when({label!r})")
        self.receipt = interp.send(event, wait=True, **payload)
        return self

    def after(self, ms: float) -> "Scenario":
        """Advance the simulated clock by *ms* (fires due ``after``s)."""
        self._ensure_live("after")
        if not isinstance(ms, (int, float)) or not math.isfinite(ms):
            # 🔥 battle #272: nan advanced the clock to nan silently
            raise ValueError(f"after() needs a finite number of ms: {ms!r}")
        self._steps.append(f"after({ms:g})")
        self.clock.increment(ms)
        return self

    # -- then -----------------------------------------------------------------
    def then_state(self, *state_ids: str) -> "Scenario":
        """The active configuration contains every given state."""
        interp = self._ensure()
        active = set(interp.current_state_ids)
        missing = [
            s
            for s in state_ids
            if not interp.matches(self._full_id(s, active=active))
        ]
        if missing:
            self._fail(
                f"expected state(s) {sorted(missing)} to be active; "
                f"active: {sorted(active)}"
            )
        return self

    def then_not_state(self, *state_ids: str) -> "Scenario":
        interp = self._ensure()
        active = set(interp.current_state_ids)
        present = [
            s
            for s in state_ids
            if interp.matches(self._full_id(s, active=active))
        ]
        if present:
            self._fail(
                f"expected state(s) {sorted(present)} NOT to be active; "
                f"active: {sorted(interp.current_state_ids)}"
            )
        return self

    def then_context(self, **expected: Any) -> "Scenario":
        interp = self._ensure()
        bad = {
            k: (v, interp.context.get(k, "<missing>"))
            for k, v in expected.items()
            if k not in interp.context or interp.context[k] != v
        }
        if bad:
            detail = ", ".join(
                f"{k}: expected {e!r}, got {a!r}" for k, (e, a) in bad.items()
            )
            self._fail(f"context mismatch -- {detail}")
        return self

    def then_changed(self, changed: bool = True) -> "Scenario":
        r = self._last_receipt("then_changed")
        if bool(r.changed) != changed:
            self._fail(
                f"expected receipt.changed={changed}, got {r.changed} "
                f"(denied={r.denied}, error={r.error!r})"
            )
        return self

    def then_denied(self) -> "Scenario":
        r = self._last_receipt("then_denied")
        if not r.denied:
            self._fail(f"expected the event to be denied; receipt={r!r}")
        return self

    def then_error(self, error_type: Optional[type] = None) -> "Scenario":
        r = self._last_receipt("then_error")
        if r.error is None:
            self._fail("expected an action/validator error on the receipt")
        if error_type is not None and not isinstance(r.error, error_type):
            self._fail(
                f"expected error of type {error_type.__name__}, got "
                f"{type(r.error).__name__}: {r.error}"
            )
        return self

    def then_no_error(self) -> "Scenario":
        r = self._last_receipt("then_no_error")
        if r.error is not None:
            self._fail(f"unexpected error on the receipt: {r.error!r}")
        return self

    def then_done(self) -> "Scenario":
        interp = self._ensure()
        if interp.status != "done":
            self._fail(f"expected status 'done', got {interp.status!r}")
        return self

    # -- lifecycle ------------------------------------------------------------
    @property
    def interp(self) -> SyncInterpreter[Any]:
        return self._ensure()

    def stop(self) -> None:
        if self._interp is not None and self._interp.status == "running":
            self._interp.stop()

    def __enter__(self) -> "Scenario":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # -- internals ------------------------------------------------------------
    def _ensure(self) -> SyncInterpreter[Any]:
        if self._interp is not None:
            return self._interp
        if self._states is None:
            interp: SyncInterpreter[Any] = SyncInterpreter(
                self.machine, clock=self.clock
            )
            if self._context:
                # 📝 merge BEFORE start so entry actions see it
                interp.context.update(self._context)
            interp.start()
        else:
            # 🔥 battle #272: a top-level final configuration is `done`,
            #    not a running interpreter parked in a final state.
            nodes = [self.machine.get_state_by_id(s) for s in self._states]
            status = (
                "done"
                if any(
                    n is not None
                    and n.type == "final"
                    and n.parent is self.machine
                    for n in nodes
                )
                else "running"
            )
            blob = from_state_ids(
                self.machine, self._states, self._context, status=status
            )
            interp = SyncInterpreter.from_snapshot(
                blob, self.machine, clock=self.clock, restart_timers="restart"
            ).start()
        self._interp = interp
        return interp

    def _ensure_live(self, step: str) -> SyncInterpreter[Any]:
        interp = self._ensure()
        if interp.status != "running":
            # 🔥 battle #272: a send to a stopped/done interpreter was a
            #    silent no-op, so the next then_* blamed the chart.
            raise RuntimeError(
                f"{step}(): the scenario's interpreter is "
                f"{interp.status!r}, not running"
            )
        return interp

    def _require_not_started(self, step: str) -> None:
        if self._interp is not None:
            raise RuntimeError(
                f"given(...).{step}() must come before the first when()"
            )

    def _last_receipt(self, step: str) -> Receipt:
        if self.receipt is None:
            raise RuntimeError(f"{step}() needs a preceding when()")
        return self.receipt

    def _full_id(
        self, state: str, active: Optional[Iterable[str]] = None
    ) -> str:
        if state.startswith(self.machine.id + ".") or state == self.machine.id:
            return state
        if "." in state:
            return f"{self.machine.id}.{state}"
        # 📝 #272 review (M1): for then_* a bare leaf name is resolved
        #    against the ACTIVE configuration first -- a chart with two
        #    `idle` leaves (one per region) is a common shape and the
        #    assertion should pass when exactly one of them is active.
        if active is not None:
            live = sorted(
                {
                    anc
                    for sid in active
                    for anc in _ancestors(sid)
                    if anc.rsplit(".", 1)[-1] == state
                }
            )
            if len(live) == 1:
                return live[0]
        # a bare leaf name: find it in the whole tree
        matches = [
            n.id
            for n in _walk(self.machine)
            if n is not self.machine and n.id.rsplit(".", 1)[-1] == state
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(
                f"given/then: no state named {state!r} in machine "
                f"{self.machine.id!r}"
            )
        raise ValueError(
            f"given/then: {state!r} is ambiguous ({sorted(matches)}); "
            f"use a full id"
        )

    def _fail(self, message: str) -> None:
        trail = " -> ".join(self._steps) or "given()"
        raise AssertionError(f"{trail}: {message}")


def _ancestors(state_id: str) -> Iterable[str]:
    """``a.b.c`` -> ``a.b.c``, ``a.b``, ``a``."""
    parts = state_id.split(".")
    for n in range(len(parts), 0, -1):
        yield ".".join(parts[:n])


def _walk(machine: MachineNode[Any]) -> Iterable[Any]:
    from ...validation import walk

    return walk(machine)


def given(machine: MachineNode[Any]) -> Scenario:
    """Start a Given/When/Then scenario on *machine* (sync engine,
    `SimulatedClock`). See `Scenario`."""
    return Scenario(machine)
