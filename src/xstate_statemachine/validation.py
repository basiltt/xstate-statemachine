# /src/xstate_statemachine/validation.py
# -----------------------------------------------------------------------------
# 🛡️ Build-time Machine Validation
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: before 0.8.0 an unknown *action* name raised at
# `create_machine()`, but an unknown *target*, an `always` transition that
# could never make progress, and a misspelled built-in `params` key all
# loaded fine and failed silently at runtime -- a dropped transition, a
# machine that parks forever, an action that does nothing. Each is a class
# of defect that no test can catch because nothing observable happens.
#
# This module walks the fully-built tree ONCE and reports every such problem
# together, so a rename that breaks twenty transitions is one error message,
# not twenty runtime surprises.
#
# Validation is a separate module rather than inline in `MachineNode` because
# it needs the WHOLE tree (targets resolve across branches), so it can only
# run after construction completes.
# -----------------------------------------------------------------------------
"""Post-construction validation for `MachineNode` trees (#29, #30, #32)."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple

from .actions import RAISE, resolve_builtin
from .exceptions import (
    InvalidConfigError,
    RootTargetError,
    StateNotFoundError,
)
from .resolver import resolve_target_state

if TYPE_CHECKING:  # pragma: no cover
    from .models import (
        ActionDefinition,
        MachineNode,
        StateNode,
        TransitionDefinition,
    )


def walk(node: "StateNode") -> Iterator["StateNode"]:
    """Yield *node* and every descendant, depth-first."""
    yield node
    for child in node.states.values():
        yield from walk(child)


def transitions_of(
    node: "StateNode",
) -> Iterator[Tuple[str, "TransitionDefinition"]]:
    """Yield ``(label, transition)`` for every transition owned by *node*.

    Covers ``on``, ``always`` (stored under the ``""`` event), ``after``,
    ``onDone`` and every ``invoke``'s ``onDone`` / ``onError``.
    """
    for event, group in node.on.items():
        label = "always" if event == "" else f"on '{event}'"
        for t in group:
            yield label, t
    if node.on_done is not None:
        yield "onDone", node.on_done
    for delay, group in node.after.items():
        for t in group:
            yield f"after {delay!r}", t
    for inv in node.invoke:
        for t in inv.on_done:
            yield f"invoke '{inv.src}' onDone", t
        for t in inv.on_error:
            yield f"invoke '{inv.src}' onError", t


def resolve_strict(
    target_str: str, source: "StateNode", machine: "MachineNode"
) -> "Optional[StateNode]":
    """Resolve *target_str* using only UNAMBIGUOUS strategies.

    🏛️ Architecture decision: this is the resolution the runtime SHOULD do,
    and what the validator checks against. It runs the resolver's standard
    strategies from the source, its parent and the root, plus one exact
    lookup of the string as a top-level state KEY (so a key like ``"v2.0"``
    still works). It deliberately omits the runtime's last-segment fuzzy
    fallbacks -- ``candidate.id.split(".")[-1] == target`` -- which are what
    let a typo bind to an unrelated state in another region (#34).

    Returns ``None`` when nothing unambiguous matches.
    """
    # 📍 `#id` and `.relative` targets carry their own anchor; the resolver
    #    is the single authority on them (including `strictTargets`), so
    #    do not retry them from other reference points.
    if target_str.startswith((".", "#")):
        try:
            return resolve_target_state(target_str, source)
        except StateNotFoundError:
            return None
    # 🪞 This list mirrors `BaseInterpreter._resolve_target_state_node`'s
    #    standard attempts ONE-FOR-ONE. Keep them in lock-step: any strategy
    #    present on one side and absent on the other is a build/runtime
    #    disagreement -- either a machine that validates and then fails at
    #    runtime, or one that is rejected although the runtime handles it.
    parent = source.parent
    attempts = [
        (target_str, source),
        (target_str, parent) if parent is not None else None,
        (target_str, machine),
        (f"{machine.id}.{target_str}", machine),
    ]
    for tgt, ref in filter(None, attempts):
        try:
            return resolve_target_state(tgt, ref)
        except StateNotFoundError:
            continue
    # Exact top-level KEY match (handles dotted keys such as "v2.0").
    return machine.states.get(target_str)


def _suggest(target_str: str, machine: "MachineNode") -> str:
    """Name the absolute form(s) of any NESTED state matching *target_str*.

    🏛️ Architecture decision: before 0.8.0 a bare ``"up"`` written from a
    sibling branch reached ``moving.up`` through the runtime's last-segment
    fallback -- the same fallback that let a typo bind to an unrelated state
    (#34). XState rejects it, and so does the validator now; but a user
    upgrading from 0.7.x deserves the one-line fix, not just the rejection.
    """
    key = target_str.split(".")[-1]
    hits = [n.id for n in walk(machine) if n is not machine and n.key == key]
    if not hits:
        return ""
    forms = ", ".join(f'"#{h}"' for h in sorted(hits))
    return f" (did you mean {forms}?)"


def _is_dead_always_loop(
    label: str, t: "TransitionDefinition", target: "StateNode"
) -> bool:
    """True when an ``always`` transition can never make progress (#29).

    An eventless transition that targets its own owning state without
    ``reenter`` never exits/re-enters, so ``entry`` never re-runs; if it
    also carries no actions, nothing in the microstep can mutate context
    and flip the guard. The eventless loop ends when a step changes
    nothing -- which this step, by construction, never does -- so the
    machine parks forever while reporting ``"running"``. Transitions with
    actions are exempt: an action CAN mutate context.
    """
    return (
        label == "always"
        and target is t.source
        and not t.reenter
        and not t.actions
    )


def _collect_findings(
    machine: "MachineNode",
) -> Tuple[List[str], List[str], List[str]]:
    """Walk the tree once; gather ``(unresolved, dead_loops, root_targets)``.

    The three lists have different severities downstream: `unresolved` is
    downgradable to a warning by ``strict_targets=False``; `dead_loops`
    and `root_targets` are not (#147) -- both describe a machine that
    cannot run, not a transition that will merely no-op.
    """
    unresolved: List[str] = []
    dead_loops: List[str] = []
    root_targets: List[str] = []

    for node in walk(machine):
        for label, t in transitions_of(node):
            if not t.target_str:
                continue
            # 🎯 #30: every target must resolve at build time. Uses the
            #    resolver's standard strategies only -- NOT the interpreter's
            #    last-segment fallbacks, which are what let a typo bind to an
            #    unrelated state (#34).
            target = resolve_strict(t.target_str, t.source, machine)
            # ⚡ Memoise for the runtime (see TransitionDefinition.resolved_target).
            t.resolved_target = target
            if target is None:
                unresolved.append(
                    f"  {node.id}: {label} -> target {t.target_str!r} "
                    f"does not resolve{_suggest(t.target_str, machine)}"
                )
            elif target is machine:
                # 🛑 #108: entering the ROOT enters nothing below it; the
                #    configuration ends up EMPTY while `status` stays
                #    "running" -- a silently inert machine on both engines.
                #    XState/SCXML: entering a compound state enters its
                #    initial child, so "target the root" has no meaning.
                # 🛑 #147: kept SEPARATE from `unresolved` so that
                #    `strict_targets=False` (which downgrades unresolvable
                #    targets to a warning) cannot reopen this hole.
                root_targets.append(
                    f"  {node.id}: {label} -> target {t.target_str!r} is the "
                    f"machine root; entering it empties the configuration. "
                    f"Target the root's initial child "
                    f"('#{machine.id}.{machine.initial}') or a specific "
                    f"state."
                )
            elif _is_dead_always_loop(label, t, target):
                dead_loops.append(
                    f"  {node.id}: always self-target can never make "
                    f"progress -- the transition does not re-enter the "
                    f"state, so 'entry' will not re-run. Add "
                    f'"reenter": true, route via an intermediate state, '
                    f"or give the transition actions that mutate context."
                )
    return unresolved, dead_loops, root_targets


def _static_raise_event_type(action: "ActionDefinition") -> Optional[str]:
    """The event type a `raise` built-in will emit, if it is knowable now."""
    if resolve_builtin(action.type) != RAISE or not action.params:
        return None
    event = action.params.get("event")
    if isinstance(event, str):
        return event
    if isinstance(event, dict) and isinstance(event.get("type"), str):
        return event["type"]
    return None  # callable / dynamic -- checked at runtime by _check_strict


def _collect_unknown_raises(machine: "MachineNode") -> List[str]:
    """`strict` machines: every STATIC `raise` must name a declared event
    (#51 follow-up).

    `_check_strict` already runs on the `raise` built-in at runtime, but
    under the default ``actionErrorPolicy: "continue"`` that exception is
    contained like any other action failure -- logged, reported through
    `on_action_error`, and the transition still commits -- so a typo'd
    internal event never *raised* to anyone. A literal event name in the
    config is a configuration error, and configuration errors belong at
    `create_machine()`.
    """
    findings: List[str] = []

    def check(actions, where: str) -> None:
        for action in actions:
            event_type = _static_raise_event_type(action)
            # #190: a `raise` is DISPATCHED, so a wildcard handler does
            #    catch it -- the dispatch question, not the strict one.
            if event_type is None or machine.is_known_event(
                event_type, wildcard_matches=True
            ):
                continue
            findings.append(
                f"  {where}: raise {event_type!r} names an event no state "
                f"handles{_suggest_event(event_type, machine)}"
            )

    for node in walk(machine):
        check(node.entry, f"{node.id} entry")
        check(node.exit, f"{node.id} exit")
        for label, t in transitions_of(node):
            check(t.actions, f"{node.id}: {label}")
    return findings


def _suggest_event(event_type: str, machine: "MachineNode") -> str:
    import difflib

    close = difflib.get_close_matches(
        event_type, sorted(machine.known_events), n=1, cutoff=0.6
    )
    return f". Did you mean {close[0]!r}?" if close else ""


def validate_machine(machine: "MachineNode", *, strict_targets: bool) -> None:
    """Run every build-time check and raise once with all findings.

    Args:
        machine: The fully constructed tree.
        strict_targets: When False, unresolvable targets emit a
            ``DeprecationWarning`` instead of raising -- the 0.7.x escape
            hatch, removed in 1.0.

    Raises:
        InvalidConfigError: One or more targets do not resolve, or an
            ``always`` self-target cannot make progress. The message lists
            every finding.
    """
    unresolved, dead_loops, root_targets = _collect_findings(machine)

    # 🛑 #108 / #147: a root target is a typed, NON-downgradable error on
    #    every flag setting. `RootTargetError` is an `InvalidConfigError`,
    #    so existing handlers still catch it.
    if root_targets:
        raise RootTargetError(
            f"Machine '{machine.id}' has transition(s) targeting the "
            f"machine root:\n" + "\n".join(root_targets)
        )

    # 🛡️ #51 follow-up: a strict machine must not be able to raise, from a
    #    literal in its own config, an event it can never handle.
    if machine.strict:
        unknown_raises = _collect_unknown_raises(machine)
        if unknown_raises:
            raise InvalidConfigError(
                f"Machine '{machine.id}' is strict but raises undeclared "
                f"event(s):\n" + "\n".join(unknown_raises)
            )

    # 🛑 Dead loops are never downgradable: unlike a missing target (a
    #    silent no-op), a parked machine is a hang.
    if dead_loops:
        raise InvalidConfigError(
            f"Machine '{machine.id}' has non-progressing 'always' "
            f"transitions:\n" + "\n".join(dead_loops)
        )

    if unresolved:
        message = (
            f"Machine '{machine.id}' has unresolvable transition targets:\n"
            + "\n".join(unresolved)
        )
        if strict_targets:
            raise InvalidConfigError(message)
        warnings.warn(
            message
            + "\n  (strict_targets=False: these transitions will be silent "
            "no-ops at runtime. This escape hatch is removed in 1.0.)",
            DeprecationWarning,
            stacklevel=3,
        )
