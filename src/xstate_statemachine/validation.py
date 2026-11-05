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
# This module walks the fully-built tree ONCE and reports every problem of a
# category together, so a rename that breaks twenty transitions is one error
# message, not twenty runtime surprises. Categories are raised one at a
# time, most severe first (see `validate_machine`).
#
# Validation is a separate module rather than inline in `MachineNode` because
# it needs the WHOLE tree (targets resolve across branches), so it can only
# run after construction completes.
# -----------------------------------------------------------------------------
"""Post-construction validation for `MachineNode` trees (#29, #30, #32)."""

from __future__ import annotations

import warnings
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
    Container,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from .actions import BUILTIN_ACTION_PARAM_SPEC, RAISE, resolve_builtin
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

logger = logging.getLogger(__name__)


def walk(node: "StateNode[Any]") -> Iterator["StateNode[Any]"]:
    """Yield *node* and every descendant, depth-first, in document order.

    ⚡ Iterative (an explicit stack) rather than a recursive generator: the
    nested ``yield from`` chain cost one generator frame per level for
    every node, on every `create_machine()` (#307 benchmark). Children
    are pushed in reverse so they pop in declaration order; the sequence
    is exactly the recursive pre-order walk.
    """
    stack = [node]
    pop = stack.pop
    while stack:
        current = pop()
        yield current
        children = current.states
        if children:
            stack.extend(reversed(list(children.values())))


def transitions_of(
    node: "StateNode[Any]",
) -> Iterator[Tuple[str, "TransitionDefinition"]]:
    """Yield ``(label, transition)`` for every transition owned by *node*.

    Covers ``on``, ``always`` (stored under the ``""`` event), ``after``,
    ``onDone`` and every ``invoke``'s ``onDone`` / ``onError``.
    """
    for event, group in node.on.items():
        label = "always" if event == "" else f"on '{event}'"
        for t in group:
            yield label, t
    for t in node.on_done_transitions:
        yield "onDone", t
    for delay, group in node.after.items():
        for t in group:
            yield f"after {delay!r}", t
    for inv in node.invoke:
        for t in inv.on_done:
            yield f"invoke '{inv.src}' onDone", t
        for t in inv.on_error:
            yield f"invoke '{inv.src}' onError", t


def _targeted_transitions(
    node: "StateNode[Any]",
) -> Iterator[Tuple[str, "TransitionDefinition"]]:
    """`transitions_of`, restricted to transitions that HAVE a target.

    ⚡ Build-time hot path (#307 benchmark): `transitions_of` formats a
    label string for every transition, but the validator only reads the
    label when a target fails to resolve. Targetless transitions (pure
    action handlers) are skipped before any string is built, and the
    common ``on`` case avoids the generic dispatch.
    """
    for event, group in node.on.items():
        for t in group:
            if t.target_str:
                yield ("always" if event == "" else f"on '{event}'"), t
    for t in node.on_done_transitions:
        if t.target_str:
            yield "onDone", t
    for delay, group in node.after.items():
        for t in group:
            if t.target_str:
                yield f"after {delay!r}", t
    for inv in node.invoke:
        for t in inv.on_done:
            if t.target_str:
                yield f"invoke '{inv.src}' onDone", t
        for t in inv.on_error:
            if t.target_str:
                yield f"invoke '{inv.src}' onError", t


def resolve_strict(
    target_str: str, source: "StateNode[Any]", machine: "MachineNode[Any]"
) -> "Optional[StateNode[Any]]":
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


def _suggest(target_str: str, machine: "MachineNode[Any]") -> str:
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
    label: str, t: "TransitionDefinition", target: "StateNode[Any]"
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


def _branch_below(
    node: "StateNode[Any]", ancestor: "StateNode[Any]"
) -> "Optional[StateNode[Any]]":
    """The child of *ancestor* on *node*'s path (``None`` if not below)."""
    current: "Optional[StateNode[Any]]" = node
    while current is not None and current.parent is not ancestor:
        current = current.parent
    return current


def multi_target_problem(
    targets: "Sequence[StateNode[Any]]",
) -> Optional[str]:
    """Why a multi-target transition's targets cannot be entered together.

    XState v5 / SCXML allow several targets only when every two of them
    lie in DIFFERENT regions of a common parallel state (each region then
    enters its target instead of its initial state). Anything else --
    two targets in one compound state, a target and its own descendant,
    the same state twice -- would activate two states of one region.

    Returns:
        ``None`` when the targets are compatible, else a short reason.
    """
    for i, first in enumerate(targets):
        for second in targets[i + 1 :]:
            common = first.parent
            while common is not None and _branch_below(second, common) is None:
                common = common.parent
            if (
                common is None
                or common.type != "parallel"
                or _branch_below(first, common)
                is _branch_below(second, common)
            ):
                return (
                    f"targets {first.id!r} and {second.id!r} are not in "
                    f"different regions of one parallel state"
                )
    return None


def _pending_targets(
    machine: "MachineNode[Any]",
) -> "Iterator[Tuple[TransitionDefinition, str, Any]]":
    """Every targeted transition as ``(transition, kind, extra)``.

    ⚡ The parser hands the validator this list as it builds the tree
    (`MachineNode._targeted_transitions`, document order); a second walk
    of the finished tree, filtering every transition for a target, was
    ~7 % of `create_machine()` (#307 benchmark). The list is consumed
    once; a later validation of the same machine (or a tree built outside
    `MachineNode.__init__`) falls back to the walk, which yields the same
    transitions in the same order.
    """
    pending = getattr(machine, "_targeted_transitions", None)
    if pending is not None:
        machine._targeted_transitions = None  # consumed
        yield from pending
        return
    for node in walk(machine):
        for group in node.on.values():
            for t in group:
                if t.target_strs:
                    yield t, "on", None
        for t in node.on_done_transitions:
            if t.target_strs:
                yield t, "onDone", None
        for delay, group in node.after.items():
            for t in group:
                if t.target_strs:
                    yield t, "after", delay
        for inv in node.invoke:
            for t in inv.on_done:
                if t.target_strs:
                    yield t, "invoke-done", inv.src
            for t in inv.on_error:
                if t.target_strs:
                    yield t, "invoke-error", inv.src


def _pending_label(t: "TransitionDefinition", kind: str, extra: Any) -> str:
    """The finding label for a `_pending_targets` entry (built lazily: the
    validator reads it only when a target is wrong)."""
    if kind == "on":
        return "always" if t.event == "" else f"on '{t.event}'"
    if kind == "after":
        return f"after {extra!r}"
    if kind == "invoke-done":
        return f"invoke '{extra}' onDone"
    if kind == "invoke-error":
        return f"invoke '{extra}' onError"
    return kind  # "onDone"


def _collect_findings(
    machine: "MachineNode[Any]",
) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Check every targeted transition once; gather the build-time findings.

    Returns ``(unresolved, dead_loops, root_targets, bad_multi_targets)``.
    The lists have different severities downstream: `unresolved` is
    downgradable to a warning by ``strict_targets=False``; the others are
    not (#147) -- they describe a machine that cannot run, not a
    transition that will merely no-op.
    """
    unresolved: List[str] = []
    dead_loops: List[str] = []
    root_targets: List[str] = []
    bad_multi: List[str] = []
    findings = (unresolved, dead_loops, root_targets)

    for t, kind, extra in _pending_targets(machine):
        # 🎯 #30: every target must resolve at build time. Uses the
        #    resolver's standard strategies only -- NOT the interpreter's
        #    last-segment fallbacks, which are what let a typo bind to an
        #    unrelated state (#34).
        source = t.source
        target_strs = t.target_strs
        if len(target_strs) == 1:
            # ⚡ The single-target shape of almost every transition: no
            #    list, no all()/tuple() passes.
            target_str = target_strs[0]
            target = resolve_strict(target_str, source, machine)
            t.resolved_target = target
            _check_one_target(
                machine, source, kind, extra, t, target_str, target, findings
            )
            continue
        resolved = [
            (target_str, resolve_strict(target_str, source, machine))
            for target_str in target_strs
        ]
        # ⚡ Memoise for the runtime (see TransitionDefinition.resolved_target).
        t.resolved_target = resolved[0][1]
        if all(r is not None for _, r in resolved):
            nodes = tuple(r for _, r in resolved if r is not None)
            t.resolved_targets = nodes
            problem = multi_target_problem(nodes)
            if problem is not None:
                bad_multi.append(
                    f"  {source.id}: {_pending_label(t, kind, extra)} -> "
                    f"{problem}"
                )
        for target_str, target in resolved:
            _check_one_target(
                machine, source, kind, extra, t, target_str, target, findings
            )
    return unresolved, dead_loops, root_targets, bad_multi


def _check_one_target(
    machine: "MachineNode[Any]",
    node: "StateNode[Any]",
    kind: str,
    extra: Any,
    t: "TransitionDefinition",
    target_str: str,
    target: "Optional[StateNode[Any]]",
    findings: Tuple[List[str], List[str], List[str]],
) -> None:
    """Record what is wrong with one resolved target of *t*, if anything.

    *kind* / *extra* describe where the transition is declared (see
    `_pending_targets`); the label is formatted only for a finding.
    """
    unresolved, dead_loops, root_targets = findings
    if target is None:
        unresolved.append(
            f"  {node.id}: {_pending_label(t, kind, extra)} -> target "
            f"{target_str!r} does not resolve{_suggest(target_str, machine)}"
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
            f"  {node.id}: {_pending_label(t, kind, extra)} -> target "
            f"{target_str!r} is the "
            f"machine root; entering it empties the configuration. "
            f"Target the root's initial child "
            f"('#{machine.id}.{machine.initial}') or a specific "
            f"state."
        )
    elif (
        kind == "on"
        and t.event == ""
        and len(t.target_strs) == 1
        and _is_dead_always_loop("always", t, target)
    ):
        dead_loops.append(
            f"  {node.id}: always self-target can never make "
            f"progress -- the transition does not re-enter the "
            f"state, so 'entry' will not re-run. Add "
            f'"reenter": true, route via an intermediate state, '
            f"or give the transition actions that mutate context."
        )


def _static_raise_event_type(action: "ActionDefinition") -> Optional[str]:
    """The event type a `raise` built-in will emit, if it is knowable now."""
    if resolve_builtin(action.type) != RAISE or not action.params:
        return None
    event = action.params.get("event")
    if isinstance(event, str):
        return event
    if isinstance(event, dict) and isinstance(event.get("type"), str):
        # 📝 isinstance above proved `type` is a str.
        return cast(str, event["type"])
    return None  # callable / dynamic -- checked at runtime by _check_strict


def _collect_unknown_raises(machine: "MachineNode[Any]") -> List[str]:
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

    def check(actions: "Sequence[ActionDefinition]", where: str) -> None:
        """Record every static `raise` in *actions* that names an event no
        state handles.

        Args:
            actions: The parsed actions to scan.
            where: The owning location, prefixed to each finding.
        """
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


def _suggest_event(event_type: str, machine: "MachineNode[Any]") -> str:
    """A "did you mean" hint naming the closest declared event, or "".

    Args:
        event_type: The undeclared event name.
        machine: The machine whose `known_events` are searched.

    Returns:
        str: ``". Did you mean 'X'?"`` or an empty string.
    """
    import difflib  # 📝 lazy: only paid when a finding is reported

    close = difflib.get_close_matches(
        event_type, sorted(machine.known_events), n=1, cutoff=0.6
    )
    return f". Did you mean {close[0]!r}?" if close else ""


#: 🏷️ Metadata keys: never behavioural, accepted at every level.
_METADATA_KEYS: FrozenSet[str] = frozenset({"meta", "description", "tags"})

#: 🗝️ #216 / #220: every key a STATE node reads (`StateNode.__init__`,
#: `_prefetch_node_keys`). A key not in this set (and not `x-`-prefixed)
#: is silently dropped by the parser: a misspelled `entry` is an action
#: that never runs, a misspelled `on` a transition that does not exist,
#: a misspelled `after` a deadline that never fires. Kept next to the
#: validator so adding a key to the parser means adding it here.
KNOWN_STATE_KEYS: FrozenSet[str] = frozenset(
    {
        "id",
        "initial",
        "states",
        "type",
        "output",
        "on",
        "entry",
        "exit",
        "after",
        "always",
        "invoke",
        "onDone",
        "history",
        "target",  # history state's default target
    }
    | _METADATA_KEYS
)

#: 🗝️ Every key the ROOT reads: the state keys plus `context`, the 0.8.0
#: policies and `version`. Policies are read from the root only, so a
#: policy key under a state is reported there too (it would be inert).
KNOWN_ROOT_KEYS: FrozenSet[str] = KNOWN_STATE_KEYS | frozenset(
    {
        "context",
        "version",
        # policies (0.8.0+)
        "actionErrorPolicy",
        "guardErrorPolicy",
        "onUnhandled",
        "maxIterations",
        "spawnBlockingTimeout",
        "strict",
        "strictTargets",
        "strictConfig",
    }
)

#: Back-compat alias for the 0.9.0 (#216) name.
KNOWN_MACHINE_KEYS: FrozenSet[str] = KNOWN_ROOT_KEYS

#: 🗝️ #220: keys `TransitionDefinition` / `_create_transition` read.
KNOWN_TRANSITION_KEYS: FrozenSet[str] = (
    frozenset({"target", "actions", "guard", "cond", "internal", "reenter"})
    | _METADATA_KEYS
)

#: 🗝️ #220: keys `InvokeDefinition` / `_parse_invoke` read.
KNOWN_INVOKE_KEYS: FrozenSet[str] = (
    frozenset({"id", "src", "input", "systemId", "onDone", "onError"})
    | _METADATA_KEYS
)

#: 🗝️ Keys `ActionDefinition` reads from an action OBJECT. A misspelled
#: ``"parms"`` left the action with no params at all.
KNOWN_ACTION_KEYS: FrozenSet[str] = frozenset({"type", "params"})

#: 🗝️ Keys `GuardDefinition` reads from a guard OBJECT.
KNOWN_GUARD_KEYS: FrozenSet[str] = frozenset({"type", "params", "children"})


def _unknown_keys(config: Dict[str, Any], known: FrozenSet[str]) -> List[str]:
    """Human-readable hints for the keys of *config* not in *known*."""
    # ⚡ Hot path (#307 benchmark): every state and transition of every
    #    build passes through here, and almost all of them have only known
    #    keys. One set subtraction answers that case; the sort, the
    #    ``x-`` filter, the difflib import and the hint strings are paid
    #    only by a config that actually has an offending key.
    if config.keys() <= known:
        return []
    import difflib

    unknown = sorted(
        k
        for k in config
        if isinstance(k, str) and k not in known and not k.startswith("x-")
    )
    # 🛡️ A non-string key (``{1: ...}``, possible only from Python) can
    #    never be read by the parser; it used to be dropped from the report.
    hints = [f"{k!r} (not a string)" for k in config if not isinstance(k, str)]
    for key in unknown:
        close = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.6)
        hints.append(
            f"'{key}'" + (f" (did you mean '{close[0]}'?)" if close else "")
        )
    return hints


def _collect_action_keys(
    raw: Any,
    where: str,
    out: List[str],
    user_actions: Optional[Container[str]],
) -> None:
    """Report unknown keys of the action OBJECTS in *raw* (VAL-01).

    Checks each action dict against `KNOWN_ACTION_KEYS` and, for a
    built-in action, its ``params`` against the keys the built-in reads
    (`BUILTIN_ACTION_PARAM_SPEC`): ``{"type": "raise", "params": {"event":
    "X", "delya": 5}}`` used to build a raise with no delay. A type the
    machine's logic implements is the USER's action (it resolves before
    the built-in), so its params are not checked.

    Args:
        raw: An ``entry`` / ``exit`` / ``actions`` value.
        where: The owning location, prefixed to each finding.
        out: Accumulator for findings.
        user_actions: Action names the machine's logic implements.
    """
    if raw is None or isinstance(raw, str):
        return  # ⚡ the common shapes: nothing, or a bare action name
    for item in raw if isinstance(raw, list) else [raw]:
        if not isinstance(item, dict):
            continue
        action_type = item.get("type")
        hints = _unknown_keys(item, KNOWN_ACTION_KEYS)
        if hints:
            out.append(f"{where} action {action_type!r}: {', '.join(hints)}")
        params = item.get("params")
        if not isinstance(params, dict) or not isinstance(action_type, str):
            continue
        if user_actions is not None and action_type in user_actions:
            continue
        canonical = resolve_builtin(action_type)
        spec = BUILTIN_ACTION_PARAM_SPEC.get(canonical) if canonical else None
        if spec is None:
            continue
        hints = _unknown_keys(params, spec[0] | spec[1])
        if hints:
            out.append(
                f"{where} action {action_type!r} params: {', '.join(hints)}"
            )


def _collect_guard_keys(raw: Any, where: str, out: List[str]) -> None:
    """Report unknown keys of a guard OBJECT and its nested guards (VAL-01).

    Args:
        raw: A transition's ``guard`` / ``cond`` value.
        where: The owning location, prefixed to each finding.
        out: Accumulator for findings.
    """
    if not isinstance(raw, dict):
        return  # ⚡ a named guard (or nothing) has no keys
    hints = _unknown_keys(raw, KNOWN_GUARD_KEYS)
    if hints:
        out.append(f"{where} guard {raw.get('type')!r}: {', '.join(hints)}")
    children = raw.get("children")
    if isinstance(children, list):
        for child in children:
            _collect_guard_keys(child, where, out)


def _collect_transition_keys(
    t: Dict[str, Any],
    where: str,
    out: List[str],
    user_actions: Optional[Container[str]],
) -> None:
    """Report unknown keys of one transition dict, its actions and guard.

    Args:
        t: The transition dict.
        where: The owning location, prefixed to each finding.
        out: Accumulator for findings.
        user_actions: Action names the machine's logic implements.
    """
    h = _unknown_keys(t, KNOWN_TRANSITION_KEYS)
    if h:
        out.append(f"{where}: {', '.join(h)}")
    # ⚡ Probe before calling: most transitions carry neither key.
    if "actions" in t:
        _collect_action_keys(t["actions"], where, out, user_actions)
    guard = t.get("guard", t.get("cond"))
    if guard is not None:
        _collect_guard_keys(guard, where, out)


def _transition_dicts(raw: Any) -> Iterator[Dict[str, Any]]:
    """Yield the dict forms of a transition config (string shorthand and
    `None` (forbidden) carry no keys to check)."""
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        if isinstance(item, dict):
            yield item


def _collect_unknown_keys(
    config: Dict[str, Any],
    path: str,
    known: FrozenSet[str],
    out: List[str],
    user_actions: Optional[Container[str]] = None,
) -> None:
    """#220: walk one state node (root included) and its transitions,
    invokes, action objects and guard objects, appending one line per
    offending config object to *out*.

    Args:
        config: The state's raw config dict.
        path: The state's id, prefixed to each finding.
        known: The keys this node may declare (root or state keys).
        out: Accumulator for findings.
        user_actions: Action names the machine's logic implements; their
            ``params`` are the user's to define (see
            `_collect_action_keys`).
    """
    hints = _unknown_keys(config, known)
    if hints:
        out.append(f"{path}: {', '.join(hints)}")
    # ⚡ ONE pass over the node's (typically 1-3) keys, dispatching each
    #    present key to its check. Probing every optional key with `.get`
    #    (six probes per node, most of them misses) was the bulk of this
    #    scan's cost on every `create_machine()` (#307 benchmark); the
    #    per-key work (generators, lists, label formatting) is still paid
    #    only when the key is present.
    for key, raw in config.items():
        if key == "on":
            if isinstance(raw, dict):
                for event, raw_t in raw.items():
                    # ⚡ String shorthand ("EVENT": "target") carries no keys.
                    if isinstance(raw_t, str):
                        continue
                    for t in _transition_dicts(raw_t):
                        _collect_transition_keys(
                            t, f"{path} on['{event}']", out, user_actions
                        )
        elif key == "states":
            if isinstance(raw, dict):
                for child_key, child in raw.items():
                    if isinstance(child, dict):
                        _collect_unknown_keys(
                            child,
                            f"{path}.{child_key}",
                            KNOWN_STATE_KEYS,
                            out,
                            user_actions,
                        )
        elif key == "entry" or key == "exit":
            # entry / exit action objects (VAL-01)
            if raw is not None:
                _collect_action_keys(raw, f"{path} {key}", out, user_actions)
        elif key == "always":
            if raw is not None:
                for t in _transition_dicts(raw):
                    _collect_transition_keys(
                        t, f"{path} always", out, user_actions
                    )
        elif key == "after":
            if isinstance(raw, dict):
                for delay, raw_t in raw.items():
                    for t in _transition_dicts(raw_t):
                        _collect_transition_keys(
                            t, f"{path} after[{delay!r}]", out, user_actions
                        )
        elif key == "onDone":
            if raw is not None:
                for t in _transition_dicts(raw):
                    _collect_transition_keys(
                        t, f"{path} onDone", out, user_actions
                    )
        elif key == "invoke":
            if raw is not None:
                invokes = raw if isinstance(raw, list) else [raw]
                for i, inv in enumerate(invokes):
                    if not isinstance(inv, dict):
                        continue
                    ipath = f"{path} invoke[{inv.get('id', i)}]"
                    h = _unknown_keys(inv, KNOWN_INVOKE_KEYS)
                    if h:
                        out.append(f"{ipath}: {', '.join(h)}")
                    for label in ("onDone", "onError"):
                        for t in _transition_dicts(inv.get(label)):
                            _collect_transition_keys(
                                t, f"{ipath} {label}", out, user_actions
                            )


def validate_top_level_keys(
    config: Dict[str, Any],
    *,
    strict_config: bool,
    user_actions: Optional[Container[str]] = None,
) -> None:
    """#216 / #220: refuse (or warn about) config keys the parser does not
    read -- at the root AND in every state, transition and invoke.

    A bad VALUE for a known key has always been refused with
    `InvalidConfigError`; a bad KEY was never looked up at all, so a
    one-character typo passed a clean build: a misspelled policy degraded
    to its permissive default (#216); a misspelled `entry` / `on` / `after`
    inside a state built a machine in which something simply never
    happened (#220). Keys starting with ``x-`` are a reserved namespace
    for caller metadata and are never reported, at any level.

    Args:
        config: The raw top-level machine config.
        strict_config: ``True`` raises `InvalidConfigError` listing every
            offending key; ``False`` (the 0.8.x default, for callers who
            attach ad-hoc keys) logs one WARNING with the same list and a
            "did you mean" hint per key.
        user_actions: Action names the machine's logic implements. Their
            ``params`` belong to the user, so they are not checked against
            the built-in of the same name (AGENTS.md: user actions win).

    Raises:
        InvalidConfigError: ``strict_config`` is ``True`` and at least one
            key is unknown.
    """
    machine_id = config.get("id", "<machine>")
    findings: List[str] = []
    _collect_unknown_keys(
        config, str(machine_id), KNOWN_ROOT_KEYS, findings, user_actions
    )
    if not findings:
        return
    msg = (
        f"Machine '{machine_id}' has unknown config key(s) -- "
        f"{'; '.join(findings)}. Unknown keys are ignored by the parser, "
        f"so a misspelled key silently does nothing (a policy reverts to "
        f"its default; an action, transition or deadline never exists). "
        f"Use the 'x-' prefix for custom metadata, or 'meta'."
    )
    if strict_config:
        raise InvalidConfigError(msg)
    logger.warning("⚠️ %s", msg)


def validate_machine(
    machine: "MachineNode[Any]", *, strict_targets: bool
) -> None:
    """Run every build-time check; raise for the first failing category.

    Each category lists ALL of its findings in one message. Categories are
    checked in this priority order and the first non-empty one raises:
    root targets, incompatible multi-targets, (strict machines) undeclared
    raised events, non-progressing ``always`` loops, unresolvable targets.

    Args:
        machine: The fully constructed tree.
        strict_targets: When False, unresolvable targets emit a
            ``DeprecationWarning`` instead of raising -- the 0.7.x escape
            hatch, removed in 1.0.

    Raises:
        InvalidConfigError: One or more targets do not resolve, an
            ``always`` self-target cannot make progress, or a multi-target
            transition's targets are not in different regions of one
            parallel state. The message lists every finding.
    """
    unresolved, dead_loops, root_targets, bad_multi = _collect_findings(
        machine
    )

    # 🛑 #108 / #147: a root target is a typed, NON-downgradable error on
    #    every flag setting. `RootTargetError` is an `InvalidConfigError`,
    #    so existing handlers still catch it.
    if root_targets:
        raise RootTargetError(
            f"Machine '{machine.id}' has transition(s) targeting the "
            f"machine root:\n" + "\n".join(root_targets)
        )

    # 🎯 A multi-target transition whose targets are not in different
    #    regions of one parallel state would activate two states of one
    #    region; never downgradable.
    if bad_multi:
        raise InvalidConfigError(
            f"Machine '{machine.id}' has multi-target transition(s) whose "
            f"targets cannot be entered together (each target must lie in "
            f"a different region of one parallel state):\n"
            + "\n".join(bad_multi)
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
