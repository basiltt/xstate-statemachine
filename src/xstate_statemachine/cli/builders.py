# src/xstate_statemachine/cli/builders.py
# -----------------------------------------------------------------------------
# 🏛️ IR → machine construction code, for all three Pythonic templates
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: one implementation of "build the machine", three
# surface syntaxes.
#
# Before v0.7.0 each template derived machine construction independently, and
# each got it wrong differently:
#
#   pythonic-functional  emitted `a.to(b, event="GO")` as a bare expression.
#                        `.to()` RETURNS a Transition, it does not register
#                        one — so the value was discarded and every machine
#                        it ever produced had zero transitions.
#   pythonic-builder     never recursed into `states`, silently dropping all
#                        nested states.
#   pythonic-class       emitted nested states into one flat namespace, so
#                        several carried `initial=True` and construction died
#                        with "Multiple initial states".
#
# Each function here emits a `build()` that has been verified against the
# golden harness to reconstruct the source machine exactly.
# -----------------------------------------------------------------------------
"""Render machine construction code from the IR."""

from __future__ import annotations

from typing import Dict, List, Optional

from . import emit
from .ir import MachineIR, StateIR
from .naming import literal

# -----------------------------------------------------------------------------
# 🧩 Shared: State(...) keyword arguments
# -----------------------------------------------------------------------------


def _state_kwargs(
    state: StateIR,
    machine: MachineIR,
    *,
    include_initial: bool,
) -> List[str]:
    """Build the keyword arguments describing *state*.

    Every feature the IR models is emitted here. Anything omitted would be a
    silent fidelity loss, which is exactly the class of defect v0.7.0 exists
    to eliminate.
    """
    kwargs: List[str] = []

    if include_initial:
        kwargs.append("initial=True")
    if state.kind == "final":
        kwargs.append("final=True")
    elif state.kind == "parallel":
        kwargs.append("parallel=True")
    elif state.kind == "history":
        kwargs.append(f"history={literal(state.history_kind or 'shallow')}")

    if state.entry:
        kwargs.append(f"entry={emit.render_actions(state.entry)}")
    if state.exit:
        kwargs.append(f"exit={emit.render_actions(state.exit)}")

    on_map = emit.render_on_map(state, machine)
    if on_map:
        kwargs.append(f"on={on_map}")

    after_map = emit.render_after_map(state, machine)
    if after_map:
        kwargs.append(f"after={after_map}")

    always = emit.render_always(state, machine)
    if always:
        kwargs.append(f"always={always}")

    invoke = emit.render_invoke(state, machine)
    if invoke:
        kwargs.append(f"invoke={invoke}")

    on_done = emit.render_on_done(state, machine)
    if on_done:
        kwargs.append(f"on_done={on_done}")

    if state.tags:
        kwargs.append(f"tags={list(state.tags)!r}")
    if state.meta:
        kwargs.append(f"meta={literal(state.meta)}")

    return kwargs


def _is_initial(state: StateIR, machine: MachineIR) -> bool:
    """Whether *state* is the initial child of its own parent.

    Scoping this per-parent is what fixes audit defect #6: the old emitters
    flattened nested states into one namespace, so six states could all claim
    ``initial=True`` and construction failed outright.

    🛡️ When a compound parent declares no ``initial``, NOTHING is nominated.
    The engine leaves such a state's ``initial`` as None and warns; inventing
    one here would make the generated machine differ from the source, which
    is precisely the silent-divergence class of bug v0.7.0 exists to kill.
    The generated code reproduces the machine faithfully, warts included.
    """
    parent = (
        machine.find(".".join(state.path[:-1]))
        if len(state.path) > 1
        else None
    )
    if parent is None:
        return machine.initial == state.key

    # 🚦 Parallel regions are all active at once; none is "initial".
    if parent.kind == "parallel":
        return False
    return parent.initial == state.key


# -----------------------------------------------------------------------------
# 1️⃣ Functional style: State objects + build_machine()
# -----------------------------------------------------------------------------


def render_functional_build(
    machine: MachineIR,
    *,
    context: Optional[Dict] = None,
) -> str:
    """Emit a ``build()`` using ``State`` objects and ``build_machine()``.

    States are emitted deepest-first so a parent can reference its children
    by variable in ``states=[...]`` — this is the real hierarchy that the old
    emitter discarded.
    """
    bindings = emit.allocate_bindings(machine)
    lines: List[str] = [
        "def build() -> Any:",
        f'    """Build the {machine.id} machine (functional style)."""',
    ]

    emitted: List[str] = []

    def emit_state(state: StateIR) -> None:
        # 📝 Children first: a parent's states=[...] needs their bindings.
        for child in state.children:
            emit_state(child)

        var = bindings[state.dotted]
        kwargs = _state_kwargs(
            state, machine, include_initial=_is_initial(state, machine)
        )
        if state.children:
            child_vars = ", ".join(
                bindings[c.dotted] for c in state.children
            )
            kwargs.append(f"states=[{child_vars}]")

        args = ", ".join([literal(state.key)] + kwargs)
        emitted.append(f"    {var} = State({args})")

    for state in machine.states:
        emit_state(state)

    lines.extend(emitted)
    lines.append("")

    root_vars = ", ".join(bindings[s.dotted] for s in machine.states)
    build_args = [f"id={literal(machine.id)}", f"states=[{root_vars}]"]

    # 🌳 Machine-level on/entry/exit/tags/parallel, carried on a root State.
    root_kwargs = _root_kwargs(machine)
    if root_kwargs:
        lines.append(f"    _root = State('', {', '.join(root_kwargs)})")
        lines.append("")
        build_args.append("root=_root")

    if context:
        build_args.append(f"context={literal(context)}")

    lines.append("    return build_machine(")
    for arg in build_args:
        lines.append(f"        {arg},")
    lines.append("    )")
    lines.append("")
    return "\n".join(lines)


def _root_kwargs(machine: MachineIR) -> List[str]:
    """Keyword arguments describing machine-level (root) properties.

    Real machines routinely declare a global escape transition such as
    ``on: {EMERGENCY: "..."}`` at the top level. Before v0.7.0 these were
    dropped, so the generated machine simply could not be escaped.
    """
    root = machine.root
    if root is None:
        return []

    kwargs: List[str] = []
    if root.kind == "parallel":
        kwargs.append("parallel=True")
    if root.entry:
        kwargs.append(f"entry={emit.render_actions(root.entry)}")
    if root.exit:
        kwargs.append(f"exit={emit.render_actions(root.exit)}")

    on_map = emit.render_on_map(root, machine)
    if on_map:
        kwargs.append(f"on={on_map}")
    after_map = emit.render_after_map(root, machine)
    if after_map:
        kwargs.append(f"after={after_map}")
    always = emit.render_always(root, machine)
    if always:
        kwargs.append(f"always={always}")
    invoke = emit.render_invoke(root, machine)
    if invoke:
        kwargs.append(f"invoke={invoke}")
    on_done = emit.render_on_done(root, machine)
    if on_done:
        kwargs.append(f"on_done={on_done}")
    if root.tags:
        kwargs.append(f"tags={list(root.tags)!r}")
    if root.meta:
        kwargs.append(f"meta={literal(root.meta)}")
    return kwargs


# -----------------------------------------------------------------------------
# 2️⃣ Builder style: MachineBuilder fluent chain
# -----------------------------------------------------------------------------


def render_builder_build(
    machine: MachineIR,
    *,
    context: Optional[Dict] = None,
) -> str:
    """Emit a ``build()`` using the fluent ``MachineBuilder`` API.

    ``MachineBuilder.state()`` is flat by design, so nested states are
    attached with ``child_states()``. The old emitter simply never recursed,
    which is why one level of nesting lost two of four states.
    """
    lines: List[str] = [
        "def build() -> Any:",
        f'    """Build the {machine.id} machine (builder style)."""',
        f"    builder = MachineBuilder({literal(machine.id)})",
    ]

    if context:
        lines.append(f"    builder.context({literal(context)})")

    root_call = _builder_root_call(machine)
    if root_call:
        lines.append(root_call)

    for state in machine.states:
        kwargs = _state_kwargs(
            state, machine, include_initial=_is_initial(state, machine)
        )
        args = ", ".join([literal(state.key)] + kwargs)
        lines.append(f"    builder.state({args})")

        if state.children:
            nested = _nested_config(state, machine)
            initial_key = state.initial
            initial = (
                f", initial={literal(initial_key)}"
                if initial_key and state.kind != "parallel"
                else ""
            )
            parallel = ", parallel=True" if state.kind == "parallel" else ""
            lines.append(
                f"    builder.child_states("
                f"{literal(state.key)}, states={nested}{initial}{parallel})"
            )

    lines.append("    return builder.build()")
    lines.append("")
    return "\n".join(lines)


def _builder_root_call(machine: MachineIR) -> Optional[str]:
    """Render ``builder.root(...)`` for machine-level properties."""
    root = machine.root
    if root is None:
        return None

    parts: List[str] = []
    if root.kind == "parallel":
        parts.append("type='parallel'")
    if root.entry:
        parts.append(f"entry={emit.render_actions(root.entry)}")
    if root.exit:
        parts.append(f"exit={emit.render_actions(root.exit)}")
    on_map = emit.render_on_map(root, machine)
    if on_map:
        parts.append(f"on={on_map}")
    after_map = emit.render_after_map(root, machine)
    if after_map:
        parts.append(f"after={after_map}")
    always = emit.render_always(root, machine)
    if always:
        parts.append(f"always={always}")
    invoke = emit.render_invoke(root, machine)
    if invoke:
        parts.append(f"invoke={invoke}")
    on_done = emit.render_on_done(root, machine)
    if on_done:
        parts.append(f"onDone={on_done}")
    if root.tags:
        parts.append(f"tags={list(root.tags)!r}")
    if root.meta:
        parts.append(f"meta={literal(root.meta)}")

    if not parts:
        return None
    return f"    builder.root({', '.join(parts)})"


def _nested_config(state: StateIR, machine: MachineIR) -> str:
    """Render a state's descendants as a nested config dict literal."""
    entries: List[str] = []
    for child in state.children:
        entries.append(f"{literal(child.key)}: {_state_dict(child, machine)}")
    return "{" + ", ".join(entries) + "}"


def _state_dict(state: StateIR, machine: MachineIR) -> str:
    """Render one state (and its children) as a config dict literal."""
    parts: List[str] = []
    if state.kind == "final":
        parts.append("'type': 'final'")
    elif state.kind == "parallel":
        parts.append("'type': 'parallel'")
    elif state.kind == "history":
        parts.append("'type': 'history'")
        parts.append(f"'history': {literal(state.history_kind or 'shallow')}")

    if state.initial and state.kind != "parallel":
        parts.append(f"'initial': {literal(state.initial)}")

    if state.entry:
        parts.append(f"'entry': {emit.render_actions(state.entry)}")
    if state.exit:
        parts.append(f"'exit': {emit.render_actions(state.exit)}")

    on_map = emit.render_on_map(state, machine)
    if on_map:
        parts.append(f"'on': {on_map}")
    after_map = emit.render_after_map(state, machine)
    if after_map:
        parts.append(f"'after': {after_map}")
    always = emit.render_always(state, machine)
    if always:
        parts.append(f"'always': {always}")
    invoke = emit.render_invoke(state, machine)
    if invoke:
        parts.append(f"'invoke': {invoke}")
    on_done = emit.render_on_done(state, machine)
    if on_done:
        parts.append(f"'onDone': {on_done}")
    if state.tags:
        parts.append(f"'tags': {list(state.tags)!r}")
    if state.meta:
        parts.append(f"'meta': {literal(state.meta)}")
    if state.children:
        parts.append(f"'states': {_nested_config(state, machine)}")

    return "{" + ", ".join(parts) + "}"


# -----------------------------------------------------------------------------
# 3️⃣ Class style: StateMachine subclass with nested State attributes
# -----------------------------------------------------------------------------


def render_class_build(
    machine: MachineIR,
    class_name: str,
    *,
    context: Optional[Dict] = None,
) -> str:
    """Emit a ``StateMachine`` subclass plus a ``build()`` helper.

    Child states are attached via ``states=[...]`` on their parent rather
    than declared as sibling class attributes — the flattening that made
    several states claim ``initial=True`` simultaneously.
    """
    bindings = emit.allocate_bindings(machine)
    lines: List[str] = [
        f"class {class_name}(StateMachine):",
        f'    """The {machine.id} state machine."""',
        "",
    ]

    if context:
        lines.append(f"    context = {literal(context)}")
        lines.append("")

    # 📝 Nested states are built as locals in a helper, then referenced,
    #    because class bodies cannot easily express a deep tree inline.
    nested_lines: List[str] = []

    def emit_nested(state: StateIR) -> None:
        for child in state.children:
            emit_nested(child)
        if not state.children:
            return
        var = bindings[state.dotted]
        child_vars = ", ".join(bindings[c.dotted] for c in state.children)
        kwargs = _state_kwargs(
            state, machine, include_initial=_is_initial(state, machine)
        )
        kwargs.append(f"states=[{child_vars}]")
        args = ", ".join([literal(state.key)] + kwargs)
        nested_lines.append(f"{var} = State({args})")

    def emit_leaf(state: StateIR) -> None:
        for child in state.children:
            emit_leaf(child)
        if state.children:
            return
        var = bindings[state.dotted]
        kwargs = _state_kwargs(
            state, machine, include_initial=_is_initial(state, machine)
        )
        args = ", ".join([literal(state.key)] + kwargs)
        nested_lines.append(f"{var} = State({args})")

    for state in machine.states:
        emit_leaf(state)
        emit_nested(state)

    for line in nested_lines:
        lines.append(f"    {line}")

    lines.append("")
    lines.append("")
    lines.append("def build() -> Any:")
    lines.append(f'    """Build the {machine.id} machine (class style)."""')
    lines.append(f"    return {class_name}.create_machine()")
    lines.append("")
    return "\n".join(lines)
