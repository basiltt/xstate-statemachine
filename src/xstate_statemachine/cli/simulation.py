# src/xstate_statemachine/cli/simulation.py
# -----------------------------------------------------------------------------
# 🏛️ Reachable event sequences for generated runners
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: a generated runner should demonstrate the machine,
# not merely enumerate its vocabulary.
#
# The pre-v0.7.0 runner sent every declared event in ALPHABETICAL order. On the
# machine {a: {ZULU: c, ALPHA: b}, b: {MIKE: c}, c: {}} that produced:
#
#     ALPHA  -> moves to b
#     MIKE   -> moves to c
#     ZULU   -> silently ignored; nothing in `c` handles it
#
# So the demo ends by firing an event that does nothing, and the ordering is an
# accident of spelling. A user running the generated file learns little and may
# reasonably conclude the machine is broken.
#
# This module walks the machine breadth-first from its initial state and emits
# only transitions that can actually fire, in an order where each one is
# enabled when it is sent.
#
# 🛡️ Guards are treated as *possibly true*: whether one passes depends on
# context and user code that does not exist yet at generation time. Including
# guarded transitions keeps the demo useful; the alternative — assuming they
# fail — would silently hide most of a realistic machine.
# -----------------------------------------------------------------------------
"""Derive a reachable event sequence for generated runner code."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from . import emit
from .ir import MachineIR, StateIR

# 📝 Keeps a generated demo readable and guarantees termination on machines
#    with large cyclic regions.
_DEFAULT_MAX_EVENTS = 12


def reachable_event_sequence(
    machine: MachineIR,
    *,
    max_events: int = _DEFAULT_MAX_EVENTS,
) -> List[str]:
    """Return events that actually fire, in an order where each is enabled.

    Walks the machine from its initial configuration, following one
    transition at a time and recording the event that caused it. Events
    reachable only after several steps therefore appear in a workable order
    rather than an alphabetical one.

    🧭 The walk prefers a destination that still has somewhere to go. A
    greedy "anything new" rule can jump straight into a terminal state and
    end the demo after one event, leaving most of the machine unexercised.

    Args:
        machine: The parsed machine.
        max_events: Upper bound on emitted events, so a cyclic machine
            cannot produce an unbounded demo.

    Returns:
        An ordered list of event names. May be shorter than the machine's
        full event vocabulary — unreachable events are deliberately omitted.
    """
    start = _initial_leaf(machine)
    if start is None:
        return []

    sequence: List[str] = []
    current = start
    visited: Set[str] = {current.dotted}

    while len(sequence) < max_events:
        step = _next_step(current, machine, visited)
        if step is None:
            break
        event, destination = step
        sequence.append(event)
        current = destination
        visited.add(destination.dotted)

    return sequence


def _next_step(
    state: StateIR,
    machine: MachineIR,
    visited: Set[str],
) -> Optional[Tuple[str, StateIR]]:
    """Choose the next event to send from *state*.

    Preference order:

    1. an unvisited destination that itself has outgoing transitions —
       keeps the walk alive and covers the most states;
    2. any unvisited destination — a terminal state is still worth showing;
    3. any enabled transition, once everything reachable has been seen.
    """
    candidates = _enabled_transitions(state, machine)
    if not candidates:
        return None

    fresh = [
        (event, dest)
        for event, dest in candidates
        if dest.dotted not in visited
    ]
    for event, dest in fresh:
        if _enabled_transitions(dest, machine):
            return event, dest
    if fresh:
        return fresh[0]
    return candidates[0]


def _enabled_transitions(
    state: StateIR,
    machine: MachineIR,
) -> List[Tuple[str, StateIR]]:
    """Event/destination pairs available from *state* and its ancestors.

    Ancestors matter: a transition declared on a compound parent is live
    while any descendant is active, and a machine-level ``on`` block is
    live everywhere. Ignoring those was why global escape events never
    appeared in generated demos.
    """
    out: List[Tuple[str, StateIR]] = []
    seen_events: Set[str] = set()

    scope: Optional[StateIR] = state
    while scope is not None:
        for trans in scope.transitions:
            if not trans.target or trans.event in seen_events:
                continue
            destination = emit.resolve_target(trans.target, scope, machine)
            if destination is None:
                continue
            seen_events.add(trans.event)
            out.append((trans.event, _entry_leaf(destination)))
        scope = _parent_of(scope, machine)

    # 🌍 Machine-level transitions are live from every state.
    root = machine.root
    if root is not None:
        for trans in root.transitions:
            if not trans.target or trans.event in seen_events:
                continue
            destination = _resolve_from_root(trans.target, machine)
            if destination is None:
                continue
            seen_events.add(trans.event)
            out.append((trans.event, _entry_leaf(destination)))

    return out


def _resolve_from_root(target: str, machine: MachineIR) -> Optional[StateIR]:
    """Resolve a machine-level transition target."""
    for state in machine.states:
        if state.key == target:
            return state
    return machine.find(target)


def _parent_of(state: StateIR, machine: MachineIR) -> Optional[StateIR]:
    """The parent of *state*, or None when it is top level."""
    if len(state.path) <= 1:
        return None
    return machine.find(".".join(state.path[:-1]))


def _entry_leaf(state: StateIR) -> StateIR:
    """Descend into *state* until an atomic state is reached.

    Entering a compound state actually activates its initial descendant, so
    the next step must be computed from there — not from the compound state,
    which usually declares no transitions of its own.
    """
    current = state
    guard = 0
    while current.children and guard < 50:
        guard += 1
        chosen = None
        if current.initial:
            for child in current.children:
                if child.key == current.initial:
                    chosen = child
                    break
        if chosen is None:
            # 🚦 Parallel regions and initial-less compounds: the first
            #    non-history child is the best available approximation.
            usable = [c for c in current.children if c.kind != "history"]
            if not usable:
                break
            chosen = usable[0]
        current = chosen
    return current


def _initial_leaf(machine: MachineIR) -> Optional[StateIR]:
    """The atomic state a freshly started machine occupies."""
    if not machine.states:
        return None
    if machine.initial:
        for state in machine.states:
            if state.key == machine.initial:
                return _entry_leaf(state)
    return _entry_leaf(machine.states[0])


def describe_sequence(
    machine: MachineIR,
    sequence: List[str],
) -> Dict[str, str]:
    """Map each event to a short comment describing what it does.

    Used to annotate generated runner code so the demo reads as a narrative
    rather than a list of sends.
    """
    notes: Dict[str, str] = {}
    for state in machine.walk():
        for trans in state.transitions:
            if trans.event in notes or trans.event not in sequence:
                continue
            if not trans.target:
                continue
            destination = emit.resolve_target(trans.target, state, machine)
            if destination is not None:
                notes[trans.event] = f"{state.dotted} -> {destination.dotted}"
    return notes


def demo_events(config: Dict) -> List[str]:
    """Choose the event order a generated runner should demonstrate.

    Prefers a reachable sequence derived from the machine's structure.
    Falls back to the full alphabetical vocabulary when no sequence can be
    derived — for example a machine with no transitions, or one whose
    source is malformed. A demo is a convenience: it must never be the
    reason generation fails.

    Args:
        config: The raw machine config.

    Returns:
        An ordered list of event names to send.
    """
    from .extractor import extract_events
    from .ir import parse_machine

    try:
        sequence = reachable_event_sequence(parse_machine(config))
    except Exception:  # noqa: BLE001 — never let a demo break generation
        sequence = []

    if sequence:
        return sequence
    return sorted(extract_events(config))
