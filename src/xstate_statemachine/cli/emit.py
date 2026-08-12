# src/xstate_statemachine/cli/emit.py
# -----------------------------------------------------------------------------
# 🏛️ Shared IR → Python rendering primitives
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the three pythonic templates differ only in their
# *surface syntax*, not in what they must express. Nesting, timers, guards and
# invoke semantics are identical concerns for all of them.
#
# The pre-v0.7.0 emitters each re-derived those decisions independently, which
# is why they each got them wrong in a different way — and why a fix applied to
# one never reached the others. This module is the single place where "what
# does this IR node mean in Python" is decided.
#
# Everything here consumes ``ir.MachineIR`` and returns source text. Nothing
# here touches raw JSON.
# -----------------------------------------------------------------------------
"""Shared helpers for rendering the IR as Python source."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from .ir import (
    ActionIR,
    GuardIR,
    InvokeIR,
    MachineIR,
    StateIR,
    TransitionIR,
)
from .naming import IdentifierAllocator, literal

# 📝 Names bound by the generated module's own imports. Reserving them stops a
#    state called "State" from shadowing the class used to build it.
RESERVED_BINDINGS = frozenset(
    {
        "State",
        "StateMachine",
        "MachineBuilder",
        "Interpreter",
        "SyncInterpreter",
        "build_machine",
        "build",
        "action",
        "guard",
        "service",
        "logger",
        "logging",
        "asyncio",
        "Any",
        "Dict",
        "List",
        "Optional",
        "Union",
        "machine",
    }
)


def indent(lines: Sequence[str], level: int = 1) -> List[str]:
    """Indent *lines* by *level* four-space steps, preserving blank lines."""
    pad = "    " * level
    return [f"{pad}{line}" if line.strip() else "" for line in lines]


# -----------------------------------------------------------------------------
# 🎯 Target resolution
# -----------------------------------------------------------------------------


def resolve_target(
    target: str,
    source: StateIR,
    machine: MachineIR,
) -> Optional[StateIR]:
    """Resolve a transition target against the IR tree.

    Unlike the old string-suffix matching, this walks a real hierarchy, so
    scope rules can be applied in the correct order:

    1. ``#customId`` / ``#machineId.path`` absolute references
    2. Siblings of the source state
    3. Descendants of the source state (``.child`` relative targets)
    4. Ancestor-scoped names, walking outward
    5. Root-level names

    Args:
        target: The raw target string from the config.
        source: The state the transition is declared on.
        machine: The whole machine, for absolute lookups.

    Returns:
        The resolved ``StateIR``, or None if the target cannot be found.
    """
    raw = target

    # 1️⃣ Absolute "#id" references.
    if raw.startswith("#"):
        body = raw[1:]
        head, _, rest = body.partition(".")
        if head == machine.id:
            return machine.find(rest) if rest else None
        for state in machine.walk():
            if state.custom_id == head:
                if not rest:
                    return state
                return _descend(state, rest.split("."))
        return None

    # 2️⃣ Relative ".child" references resolve from the source's PARENT.
    #    This mirrors resolver.py ("Base the search from the parent of the
    #    current state"). Treating them as descending from the source
    #    itself silently resolved to the wrong state.
    if raw.startswith("."):
        parent = _state_at(machine, source.path[:-1])
        base_children = parent.children if parent else machine.states
        parts = raw.lstrip(".").split(".")
        for candidate in base_children:
            if candidate.key == parts[0]:
                return _descend(candidate, parts[1:])
        return None

    parts = raw.split(".")

    # 3️⃣ Siblings, then 4️⃣ ancestors walking outward.
    parent_path = source.path[:-1]
    while True:
        scope = _state_at(machine, parent_path)
        siblings = scope.children if scope else machine.states
        for candidate in siblings:
            if candidate.key == parts[0]:
                return _descend(candidate, parts[1:])
        if not parent_path:
            break
        parent_path = parent_path[:-1]

    # 5️⃣ Fall back to a unique match anywhere in the tree.
    matches = [s for s in machine.walk() if s.dotted == raw]
    if len(matches) == 1:
        return matches[0]
    matches = [s for s in machine.walk() if s.key == raw]
    if len(matches) == 1:
        return matches[0]
    return None


def _state_at(machine: MachineIR, path: Tuple[str, ...]) -> Optional[StateIR]:
    """Return the state at an absolute *path*, or None for the root."""
    if not path:
        return None
    return machine.find(".".join(path))


def _descend(state: StateIR, parts: Sequence[str]) -> Optional[StateIR]:
    """Walk down from *state* following child keys in *parts*."""
    current = state
    for part in parts:
        if not part:
            continue
        for child in current.children:
            if child.key == part:
                current = child
                break
        else:
            return None
    return current


# -----------------------------------------------------------------------------
# 🧱 Rendering IR fragments as Python literals
# -----------------------------------------------------------------------------


def render_guard(guard: Optional[GuardIR]) -> Optional[str]:
    """Render a guard as a Python expression.

    Composite guards keep their full nested structure, so ``and``/``or``/
    ``not`` semantics survive into the generated config.
    """
    if guard is None:
        return None
    if not guard.is_composite:
        return literal(guard.type)
    children = ", ".join(
        _render_guard_value(child) for child in guard.children
    )
    return (
        f"{{'type': {literal(guard.type)}, "
        f"'params': {{'guards': [{children}]}}}}"
    )


def _render_guard_value(guard: GuardIR) -> str:
    """Render a guard as it appears nested inside a composite."""
    rendered = render_guard(guard)
    return rendered if rendered is not None else literal(guard.type)


def render_actions(actions: Sequence[ActionIR]) -> Optional[str]:
    """Render an action list, preserving parameterised actions."""
    if not actions:
        return None
    parts: List[str] = []
    for act in actions:
        if act.params:
            parts.append(
                f"{{'type': {literal(act.type)}, "
                f"'params': {literal(act.params)}}}"
            )
        else:
            parts.append(literal(act.type))
    return f"[{', '.join(parts)}]"


def render_transition_value(
    trans: TransitionIR,
    source: StateIR,
    machine: MachineIR,
) -> str:
    """Render one transition as the dict/string a config expects."""
    target_state = (
        resolve_target(trans.target, source, machine) if trans.target else None
    )
    target_path = (
        _target_expression(target_state, source, machine)
        if target_state
        else trans.target
    )

    guard = render_guard(trans.guard)
    actions = render_actions(trans.actions)

    # 📝 A bare target with no guard/actions can stay a plain string.
    if target_path and not guard and not actions and not trans.reenter:
        return literal(target_path)

    parts: List[str] = []
    if target_path:
        parts.append(f"'target': {literal(target_path)}")
    if guard:
        parts.append(f"'guard': {guard}")
    if actions:
        parts.append(f"'actions': {actions}")
    if trans.reenter:
        parts.append("'reenter': True")
    return "{" + ", ".join(parts) + "}"


def _target_expression(
    target: StateIR,
    source: StateIR,
    machine: MachineIR,
) -> str:
    """Render *target* the way the engine will resolve it from *source*.

    🛡️ Targets are scope-relative, not absolute. Emitting a fully qualified
    dotted path changes meaning: from ``outerA.innerX`` the target
    ``"outerA.innerY"`` would be looked up among innerX's *siblings*, where
    no such key exists. The engine resolves a bare sibling key, so that is
    what must be emitted.

    Preference order mirrors the engine's own lookup: sibling key, then a
    path relative to the nearest common ancestor, then an absolute ``#id``
    reference as an unambiguous last resort.
    """
    # 1️⃣ Sibling of the source — the overwhelmingly common case.
    if target.path[:-1] == source.path[:-1]:
        return target.key

    # 2️⃣ Descendant of one of the source's ancestors: emit the path
    #    relative to that ancestor, which the engine resolves by walking up.
    #
    # 🛡️ The leading-dot form is deliberately NOT used for a descendant of
    #    the source. `resolver.py` bases a `.child` lookup on the source's
    #    PARENT (see "Base the search from the parent of the current
    #    state"), so emitting `.p` for a child of `x` sends the engine
    #    looking for `x`'s sibling `p` and the transition silently fails to
    #    resolve. Every candidate below is round-trip verified instead.
    for depth in range(len(source.path), -1, -1):
        ancestor_path = source.path[:depth]
        if target.path[:depth] == ancestor_path and len(target.path) > depth:
            candidate = ".".join(target.path[depth:])
            # ✅ Only safe if it resolves back to the same state.
            if resolve_target(candidate, source, machine) is target:
                return candidate

    # 3️⃣ Absolute reference — always unambiguous.
    return f"#{machine.id}.{target.dotted}"


def render_on_map(state: StateIR, machine: MachineIR) -> Optional[str]:
    """Render a state's ``on`` block, grouping multi-candidate events."""
    if not state.transitions:
        return None
    grouped: Dict[str, List[TransitionIR]] = {}
    for trans in state.transitions:
        grouped.setdefault(trans.event, []).append(trans)

    entries: List[str] = []
    for event, transitions in grouped.items():
        if len(transitions) == 1:
            value = render_transition_value(transitions[0], state, machine)
        else:
            rendered = ", ".join(
                render_transition_value(t, state, machine) for t in transitions
            )
            value = f"[{rendered}]"
        entries.append(f"{literal(event)}: {value}")
    return "{" + ", ".join(entries) + "}"


def render_after_map(state: StateIR, machine: MachineIR) -> Optional[str]:
    """Render a state's ``after`` block.

    Both numeric delays and *named* delays are emitted. Named delays were
    dropped entirely before v0.7.0, so those transitions never fired.
    """
    if not state.after:
        return None
    grouped: Dict[object, List[TransitionIR]] = {}
    for trans in state.after:
        grouped.setdefault(trans.delay, []).append(trans)

    entries: List[str] = []
    for delay, transitions in grouped.items():
        if len(transitions) == 1:
            value = render_transition_value(transitions[0], state, machine)
        else:
            rendered = ", ".join(
                render_transition_value(t, state, machine) for t in transitions
            )
            value = f"[{rendered}]"
        entries.append(f"{_delay_key(delay)}: {value}")
    return "{" + ", ".join(entries) + "}"


def _delay_key(delay: object) -> str:
    """Render an ``after`` key the way a human would write it.

    JSON object keys are always strings, so a numeric delay arrives as
    ``"1000"``. The engine normalises both forms to ``1000``, so emitting
    the string is *behaviourally* identical — but nobody hand-writes
    ``after={"1000": ...}``, and generated code that looks hand-written is
    the whole point. Named delays stay quoted.
    """
    if isinstance(delay, str):
        try:
            return str(int(delay))
        except ValueError:
            return literal(delay)
    return literal(delay)


def render_always(state: StateIR, machine: MachineIR) -> Optional[str]:
    """Render eventless (``always``) transitions."""
    if not state.always:
        return None
    rendered = ", ".join(
        render_transition_value(t, state, machine) for t in state.always
    )
    return f"[{rendered}]"


def render_invoke(state: StateIR, machine: MachineIR) -> Optional[str]:
    """Render ``invoke`` definitions including onDone/onError handlers."""
    if not state.invoke:
        return None

    def one(inv: InvokeIR) -> str:
        parts = [f"'src': {literal(inv.src)}"]
        if inv.id:
            parts.append(f"'id': {literal(inv.id)}")
        if inv.on_done:
            parts.append(
                "'onDone': "
                + _render_handler_list(inv.on_done, state, machine)
            )
        if inv.on_error:
            parts.append(
                "'onError': "
                + _render_handler_list(inv.on_error, state, machine)
            )
        if inv.input is not None:
            parts.append(f"'input': {literal(inv.input)}")
        return "{" + ", ".join(parts) + "}"

    if len(state.invoke) == 1:
        return one(state.invoke[0])
    return "[" + ", ".join(one(i) for i in state.invoke) + "]"


def render_on_done(state: StateIR, machine: MachineIR) -> Optional[str]:
    """Render a compound state's ``onDone`` completion transition."""
    if not state.on_done:
        return None
    return _render_handler_list(state.on_done, state, machine)


def _render_handler_list(
    transitions: Sequence[TransitionIR],
    state: StateIR,
    machine: MachineIR,
) -> str:
    """Render onDone/onError handlers, collapsing the single case."""
    if len(transitions) == 1:
        return render_transition_value(transitions[0], state, machine)
    rendered = ", ".join(
        render_transition_value(t, state, machine) for t in transitions
    )
    return f"[{rendered}]"


# -----------------------------------------------------------------------------
# 🔎 Logic discovery
# -----------------------------------------------------------------------------


def collect_implementations(
    machine: MachineIR,
) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """Find every action, guard, service and named delay the machine needs.

    Returns:
        ``(actions, guards, services, delays)`` as sorted-ready sets.

    Composite guards contribute their *leaves*, which the pre-v0.7.0
    extractor missed entirely — those guards were never stubbed and raised
    ``ImplementationMissingError`` at runtime.
    """
    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()
    delays: Set[str] = set()

    def absorb(transitions: Sequence[TransitionIR]) -> None:
        for trans in transitions:
            actions.update(a.type for a in trans.actions)
            if trans.guard is not None:
                guards.update(trans.guard.leaf_names())
            if isinstance(trans.delay, str):
                delays.add(trans.delay)

    for state in machine.walk():
        actions.update(a.type for a in state.entry)
        actions.update(a.type for a in state.exit)
        absorb(state.transitions)
        absorb(state.after)
        absorb(state.always)
        absorb(state.on_done)
        for inv in state.invoke:
            services.add(inv.src)
            absorb(inv.on_done)
            absorb(inv.on_error)

    return actions, guards, services, delays


def allocate_bindings(machine: MachineIR) -> Dict[str, str]:
    """Allocate a unique Python binding for every state in the machine.

    Keys are dotted paths, so two states with colliding leaf names still get
    distinct variables (audit defect #3).
    """
    alloc = IdentifierAllocator(reserved=RESERVED_BINDINGS)
    bindings: Dict[str, str] = {}
    for state in machine.walk():
        # 📝 Deeper states include their parent in the fallback so a
        #    collision produces a readable name, not just `state_7`.
        bindings[state.dotted] = alloc.allocate(
            state.dotted, fallback="_".join(state.path) or "state"
        )
    return bindings
