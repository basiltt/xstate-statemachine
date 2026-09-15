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

from .exceptions import InvalidConfigError, StateNotFoundError
from .resolver import resolve_target_state

if TYPE_CHECKING:  # pragma: no cover
    from .models import MachineNode, StateNode, TransitionDefinition


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
    parent = source.parent
    for ref in (source, parent, machine):
        if ref is None:
            continue
        try:
            return resolve_target_state(target_str, ref)
        except StateNotFoundError:
            continue
    try:
        return resolve_target_state(f"{machine.id}.{target_str}", machine)
    except StateNotFoundError:
        pass
    # Exact top-level KEY match (handles dotted keys such as "v2.0").
    exact = machine.states.get(target_str)
    return exact


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
    unresolved: List[str] = []
    dead_loops: List[str] = []

    for node in walk(machine):
        for label, t in transitions_of(node):
            if not t.target_str:
                continue
            # 🎯 #30: every target must resolve at build time. Uses the
            #    resolver's standard strategies only -- NOT the interpreter's
            #    last-segment fallbacks, which are what let a typo bind to an
            #    unrelated state (#34).
            target = resolve_strict(t.target_str, t.source, machine)
            if target is None:
                unresolved.append(
                    f"  {node.id}: {label} -> target {t.target_str!r} "
                    f"does not resolve"
                )
                continue

            # 🔁 #29: an `always` transition that targets its own owning
            #    state without `reenter` never exits/re-enters, so `entry`
            #    never re-runs and nothing else in the microstep mutates
            #    context. The eventless loop ends when a step changes
            #    nothing -- which this step, by construction, never does.
            #    The machine parks forever while reporting "running".
            #    Statically detectable, so reject it here. Transitions
            #    that carry actions are exempt: an action CAN mutate context
            #    and let the guard flip.
            if (
                label == "always"
                and target is t.source
                and not t.reenter
                and not t.actions
            ):
                dead_loops.append(
                    f"  {node.id}: always self-target can never make "
                    f"progress -- the transition does not re-enter the "
                    f"state, so 'entry' will not re-run. Add "
                    f'"reenter": true, route via an intermediate state, '
                    f"or give the transition actions that mutate context."
                )

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
