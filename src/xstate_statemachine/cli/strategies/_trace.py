# src/xstate_statemachine/cli/strategies/_trace.py
# -----------------------------------------------------------------------------
# 🧪 Ground-truth trajectories for the generated test scaffold
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the `pytest` template does not GUESS what a
#    transition does. At generation time it runs the real machine -- with
#    stub logic, on a `SimulatedClock`, on the `SyncInterpreter` -- along
#    the reachable event sequence, records the configuration after each
#    step, and emits assertions against THAT. A generated test can therefore
#    only fail when the machine (or the library) changes behaviour, which is
#    exactly when it should.
# -----------------------------------------------------------------------------
"""Record what a machine actually does so tests can assert it."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ...clock import SimulatedClock
from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...sync_interpreter import SyncInterpreter
from ...validation import walk
from ..extractor import extract_logic_names
from ..ir import parse_machine
from ..simulation import reachable_event_sequence


@dataclass
class Step:
    """One recorded step: the event sent (or clock advance) and the result."""

    kind: str  # "event" | "clock"
    event: Optional[str]
    advance_ms: Optional[int]
    state_ids: List[str]
    changed: bool
    actions_ran: List[str] = field(default_factory=list)


@dataclass
class Trace:
    initial_state_ids: List[str]
    steps: List[Step]
    final_reached: bool
    guard_names: List[str]
    action_names: List[str]
    service_names: List[str]
    timers: List[Tuple[str, int]]  # (state id, delay ms) for numeric `after`
    events: List[str]
    unreached_events: List[str]


def _stub_logic(
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
    ran: List[str],
    guard_value: bool,
) -> MachineLogic:
    def mk_action(name: str):
        def _a(i: Any, c: Any, e: Any, ad: Any) -> None:
            ran.append(name)

        return _a

    return MachineLogic(
        actions={a: mk_action(a) for a in actions},
        guards={g: (lambda c, e: guard_value) for g in guards},
        services={s: (lambda i, c, e: None) for s in services},
    )


def record(config: Dict[str, Any], *, max_events: int = 24) -> Trace:
    """Run *config* along its reachable event sequence and record it."""
    logging.disable(logging.CRITICAL)
    try:
        actions, guards, services = extract_logic_names(config)
        ran: List[str] = []
        logic = _stub_logic(actions, guards, services, ran, True)
        machine = create_machine(json.loads(json.dumps(config)), logic=logic)
        clock = SimulatedClock()
        interp = SyncInterpreter(machine, clock=clock).start()
        initial = sorted(interp.current_state_ids)

        ir = parse_machine(config)
        sequence = reachable_event_sequence(ir, max_events=max_events)

        timers: List[Tuple[str, int]] = []
        for node in walk(machine):
            for key in node.after:
                if isinstance(key, int):
                    timers.append((node.id, key))

        steps: List[Step] = []
        for ev in sequence:
            before = set(interp.current_state_ids)
            ran.clear()
            interp.send(ev)
            after = set(interp.current_state_ids)
            steps.append(
                Step(
                    "event",
                    ev,
                    None,
                    sorted(after),
                    after != before,
                    list(ran),
                )
            )
            if interp.status != "running":
                break
        # ⏱️ If a numeric timer is armed in the current configuration, jump
        #    past the longest one and record the landing.
        if interp.status == "running":
            armed = [
                d
                for sid, d in timers
                if any(
                    s == sid or s.startswith(sid + ".")
                    for s in interp.current_state_ids
                )
            ]
            if armed:
                before = set(interp.current_state_ids)
                ran.clear()
                clock.increment(max(armed) + 1)
                after = set(interp.current_state_ids)
                steps.append(
                    Step(
                        "clock",
                        None,
                        max(armed) + 1,
                        sorted(after),
                        after != before,
                        list(ran),
                    )
                )
        final = interp.status == "done"
        interp.stop()
        seen = {s.event for s in steps if s.event}
        return Trace(
            initial_state_ids=initial,
            steps=steps,
            final_reached=final,
            guard_names=sorted(guards),
            action_names=sorted(actions),
            service_names=sorted(services),
            timers=timers,
            events=sorted(machine.known_events),
            unreached_events=sorted(set(machine.known_events) - seen),
        )
    finally:
        logging.disable(logging.NOTSET)
