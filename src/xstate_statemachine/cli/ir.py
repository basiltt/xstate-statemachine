# src/xstate_statemachine/cli/ir.py
# -----------------------------------------------------------------------------
# 🏛️ Intermediate Representation for code generation
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: emitters must never walk raw JSON again.
#
# The v0.7.0 audit traced most Tier-0 defects to a single cause: hierarchy was
# destroyed *at the data layer* before any template ran. ``collect_all_states``
# returned a flat list keyed by ``parent_child``, so nesting could not be
# emitted even in principle — the information was already gone.
#
# The second cause was silent subset translation: emitters understood ``on``
# and ``initial`` and quietly dropped ``final``, ``after``, ``parallel``,
# ``history``, ``tags``, ``meta``. There was no "unknown key" path, so a flat
# machine could lose data with exit code 0.
#
# This module fixes both structurally:
#
#   • Parse ONCE into a typed tree that preserves hierarchy (``MachineIR``).
#   • Record every key consumed. Anything left over lands in ``unsupported``,
#     so a template can refuse to emit rather than lie (M6).
#
# Emitters consume the IR and nothing else.
# -----------------------------------------------------------------------------
"""Typed intermediate representation of an XState machine config."""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, Iterator, List, Optional, Tuple

# 📝 Keys the IR fully understands. Anything outside this set on a state is
#    surfaced as unsupported rather than silently dropped.
_KNOWN_STATE_KEYS = frozenset(
    {
        "id",
        "type",
        "initial",
        "states",
        "on",
        "entry",
        "exit",
        "onEntry",
        "onExit",
        "after",
        "always",
        "invoke",
        "onDone",
        "history",
        "tags",
        "meta",
        "description",
        "context",
    }
)

# 🛡️ Guard combinators evaluated by the engine itself. These are never
#    user-supplied implementations and must never be emitted as stub names.
_COMPOSITE_OPERATORS = frozenset({"and", "or", "not"})

# 📝 Purely cosmetic Stately/editor keys — safe to ignore without warning.
_IGNORED_STATE_KEYS = frozenset({"description"})


@dataclasses.dataclass(frozen=True)
class GuardIR:
    """A guard reference, which may be composite.

    XState v5 allows ``{"type": "and", "params": {"guards": [...]}}``. The old
    extractor tested ``isinstance(value, str)`` and therefore never discovered
    the leaf guard names nested inside composites, so they were never stubbed
    and blew up at runtime with ``ImplementationMissingError``.
    """

    type: str
    children: Tuple["GuardIR", ...] = ()
    params: Optional[Dict[str, Any]] = None

    @property
    def is_composite(self) -> bool:
        """Whether this guard combines other guards."""
        return bool(self.children)

    def leaf_names(self) -> Tuple[str, ...]:
        """All non-composite guard names reachable from here.

        🛡️ Composite *operators* (``and``/``or``/``not``) are never returned.
        They are combinators evaluated by the engine, not user-supplied
        implementations — emitting one as a stub name produces
        ``guards=[and, ...]``, which is a SyntaxError.
        """
        if self.children:
            out: List[str] = []
            for child in self.children:
                out.extend(child.leaf_names())
            return tuple(out)
        # 📝 A childless composite operator has nothing to implement.
        if self.type in _COMPOSITE_OPERATORS:
            return ()
        return (self.type,)


@dataclasses.dataclass(frozen=True)
class ActionIR:
    """An action reference with optional parameters."""

    type: str
    params: Optional[Dict[str, Any]] = None


@dataclasses.dataclass(frozen=True)
class TransitionIR:
    """A single transition edge.

    Attributes:
        event: Event name. Empty string denotes an eventless/``always``
            transition; ``after`` transitions carry a synthetic marker.
        target: Raw target string exactly as written in the source, or None
            for internal transitions. Resolution happens later, against the
            IR tree, so scope information is still available.
        actions: Actions to run on this transition.
        guard: Optional guard, possibly composite.
        reenter: Force exit/re-entry on self-transitions.
        internal: Whether this transition is internal.
        delay: For ``after`` transitions, the delay key (int ms or a named
            delay string). None otherwise.
    """

    event: str
    target: Optional[str] = None
    actions: Tuple[ActionIR, ...] = ()
    guard: Optional[GuardIR] = None
    reenter: bool = False
    internal: bool = False
    delay: Optional[Any] = None


@dataclasses.dataclass(frozen=True)
class InvokeIR:
    """A service invocation."""

    src: str
    id: Optional[str] = None
    on_done: Tuple[TransitionIR, ...] = ()
    on_error: Tuple[TransitionIR, ...] = ()
    input: Optional[Any] = None


@dataclasses.dataclass
class StateIR:
    """One state node, with children intact.

    This is the type whose mere existence fixes RC-1: ``children`` is a real
    tree, so an emitter can render nesting without reconstructing it from
    underscore-joined names.
    """

    key: str
    path: Tuple[str, ...]
    kind: str = "atomic"  # atomic | compound | parallel | final | history
    initial: Optional[str] = None
    custom_id: Optional[str] = None
    history_kind: Optional[str] = None  # shallow | deep
    entry: Tuple[ActionIR, ...] = ()
    exit: Tuple[ActionIR, ...] = ()
    transitions: Tuple[TransitionIR, ...] = ()
    after: Tuple[TransitionIR, ...] = ()
    always: Tuple[TransitionIR, ...] = ()
    invoke: Tuple[InvokeIR, ...] = ()
    on_done: Tuple[TransitionIR, ...] = ()
    tags: Tuple[str, ...] = ()
    meta: Optional[Dict[str, Any]] = None
    children: Tuple["StateIR", ...] = ()
    unsupported: Tuple[str, ...] = ()

    @property
    def dotted(self) -> str:
        """Dotted path from the machine root, e.g. ``outerA.innerX``."""
        return ".".join(self.path)

    @property
    def is_leaf(self) -> bool:
        """Whether this state has no child states."""
        return not self.children

    def walk(self) -> Iterator["StateIR"]:
        """Yield this state and every descendant, depth-first."""
        yield self
        for child in self.children:
            yield from child.walk()


@dataclasses.dataclass
class MachineIR:
    """A whole machine, parsed once.

    Attributes:
        id: The machine ``id``.
        initial: Root-level initial state key.
        context: Initial context dict, when it is a real dict. Stately
            exports sometimes ship ``"{{initialContext}}"`` as a string;
            that is recorded in ``context_is_placeholder`` instead.
        states: Top-level states, each retaining its own children.
        root: The machine root treated as a state in its own right. Real
            machines put ``on``/``entry``/``exit``/``tags`` and even
            ``type: parallel`` at the top level, and those were silently
            dropped before v0.7.0.
        unsupported: Machine-level keys the IR does not model.
    """

    id: str
    initial: Optional[str]
    states: Tuple[StateIR, ...]
    root: Optional[StateIR] = None
    context: Optional[Dict[str, Any]] = None
    context_is_placeholder: bool = False
    tags: Tuple[str, ...] = ()
    meta: Optional[Dict[str, Any]] = None
    unsupported: Tuple[str, ...] = ()

    @property
    def is_parallel(self) -> bool:
        """Whether the machine root itself is a parallel state."""
        return self.root is not None and self.root.kind == "parallel"

    def walk(self) -> Iterator[StateIR]:
        """Yield every state in the machine, depth-first."""
        for state in self.states:
            yield from state.walk()

    def all_unsupported(self) -> List[str]:
        """Collect every unsupported-key report across the machine."""
        found = list(self.unsupported)
        for state in self.walk():
            found.extend(state.unsupported)
        return found

    def find(self, dotted: str) -> Optional[StateIR]:
        """Look up a state by dotted path from the root."""
        for state in self.walk():
            if state.dotted == dotted:
                return state
        return None


# -----------------------------------------------------------------------------
# 🔧 Parsing
# -----------------------------------------------------------------------------


def _as_list(value: Any) -> List[Any]:
    """Normalise a scalar-or-list field into a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_guard(raw: Any) -> Optional[GuardIR]:
    """Parse a guard reference, recursing through composites.

    Handles the three shapes XState permits::

        "isReady"
        {"type": "isReady", "params": {...}}
        {"type": "and", "params": {"guards": ["a", {"type": "not", ...}]}}
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return GuardIR(type=raw)
    if not isinstance(raw, dict):
        return None

    guard_type = raw.get("type")
    if not isinstance(guard_type, str):
        return None

    params = raw.get("params")
    children: List[GuardIR] = []
    if isinstance(params, dict):
        # 🔍 Composite guards nest their operands under params.guards.
        for nested in _as_list(params.get("guards")):
            parsed = parse_guard(nested)
            if parsed is not None:
                children.append(parsed)

    return GuardIR(
        type=guard_type,
        children=tuple(children),
        params=params if isinstance(params, dict) else None,
    )


def parse_action(raw: Any) -> Optional[ActionIR]:
    """Parse a single action reference."""
    if isinstance(raw, str):
        return ActionIR(type=raw)
    if isinstance(raw, dict):
        action_type = raw.get("type")
        if isinstance(action_type, str):
            params = raw.get("params")
            return ActionIR(
                type=action_type,
                params=params if isinstance(params, dict) else None,
            )
    return None


def parse_actions(raw: Any) -> Tuple[ActionIR, ...]:
    """Parse an action field that may be a scalar, dict, or list."""
    out: List[ActionIR] = []
    for item in _as_list(raw):
        parsed = parse_action(item)
        if parsed is not None:
            out.append(parsed)
    return tuple(out)


def parse_transitions(
    event: str,
    raw: Any,
    *,
    delay: Optional[Any] = None,
) -> Tuple[TransitionIR, ...]:
    """Parse the value of one ``on``/``after``/``always`` entry.

    A single event may map to a list of guarded candidates, so this always
    returns a tuple.
    """
    out: List[TransitionIR] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            out.append(TransitionIR(event=event, target=item, delay=delay))
        elif isinstance(item, dict):
            target = item.get("target")
            guard_raw = item.get("guard", item.get("cond"))
            out.append(
                TransitionIR(
                    event=event,
                    target=target if isinstance(target, str) else None,
                    actions=parse_actions(item.get("actions")),
                    guard=parse_guard(guard_raw),
                    reenter=bool(
                        item.get("reenter", item.get("internal") is False)
                    )
                    and item.get("reenter") is not False,
                    internal=bool(item.get("internal")),
                    delay=delay,
                )
            )
    return tuple(out)


def parse_invoke(raw: Any) -> Tuple[InvokeIR, ...]:
    """Parse the ``invoke`` field, which may be a dict or list of dicts."""
    out: List[InvokeIR] = []
    for item in _as_list(raw):
        if not isinstance(item, dict):
            continue
        src = item.get("src")
        if not isinstance(src, str):
            continue
        invoke_id = item.get("id")
        out.append(
            InvokeIR(
                src=src,
                id=invoke_id if isinstance(invoke_id, str) else None,
                on_done=parse_transitions("onDone", item.get("onDone")),
                on_error=parse_transitions("onError", item.get("onError")),
                input=item.get("input"),
            )
        )
    return tuple(out)


def _infer_kind(config: Dict[str, Any], has_children: bool) -> str:
    """Determine a state's kind from its declared type and shape.

    🛡️ Mirrors the engine exactly. A state declared ``final`` that also has
    *children* is downgraded to compound by the engine rather than rejected
    — real Stately exports contain these. Note the rule is children only:
    ``final`` with outgoing transitions stays ``final``. The IR must agree,
    or generated code would refuse to build a machine the library itself
    loads without complaint.
    """
    declared = config.get("type")
    if declared == "final":
        return "compound" if has_children else "final"
    if declared == "parallel":
        return "parallel"
    if declared == "history":
        return "history"
    return "compound" if has_children else "atomic"


def parse_state(
    key: str,
    config: Any,
    path: Tuple[str, ...],
) -> StateIR:
    """Parse one state and, recursively, all of its children."""
    if not isinstance(config, dict):
        config = {}

    raw_children = config.get("states")
    children: List[StateIR] = []
    if isinstance(raw_children, dict):
        for child_key, child_config in raw_children.items():
            children.append(
                parse_state(child_key, child_config, path + (child_key,))
            )

    # ⏱️ after: each delay key maps to its own transition set.
    after: List[TransitionIR] = []
    raw_after = config.get("after")
    if isinstance(raw_after, dict):
        for delay_key, value in raw_after.items():
            after.extend(
                parse_transitions(
                    f"after.{delay_key}", value, delay=delay_key
                )
            )

    # ➡️ always / eventless transitions, including the legacy "" event key.
    always: List[TransitionIR] = list(
        parse_transitions("", config.get("always"))
    )

    on_map = config.get("on")
    transitions: List[TransitionIR] = []
    if isinstance(on_map, dict):
        for event_name, value in on_map.items():
            parsed = parse_transitions(event_name, value)
            if event_name == "":
                always.extend(parsed)
            else:
                transitions.extend(parsed)

    tags = tuple(t for t in _as_list(config.get("tags")) if isinstance(t, str))
    meta = config.get("meta")
    custom_id = config.get("id")
    history_kind = None
    if _infer_kind(config, bool(children)) == "history":
        raw_history = config.get("history")
        history_kind = raw_history if isinstance(raw_history, str) else "shallow"

    unsupported = tuple(
        sorted(
            k
            for k in config
            if k not in _KNOWN_STATE_KEYS and k not in _IGNORED_STATE_KEYS
        )
    )

    initial = config.get("initial")

    return StateIR(
        key=key,
        path=path,
        kind=_infer_kind(config, bool(children)),
        initial=initial if isinstance(initial, str) else None,
        custom_id=custom_id if isinstance(custom_id, str) else None,
        history_kind=history_kind,
        entry=parse_actions(config.get("entry", config.get("onEntry"))),
        exit=parse_actions(config.get("exit", config.get("onExit"))),
        transitions=tuple(transitions),
        after=tuple(after),
        always=tuple(always),
        invoke=parse_invoke(config.get("invoke")),
        on_done=parse_transitions("onDone", config.get("onDone")),
        tags=tags,
        meta=meta if isinstance(meta, dict) else None,
        children=tuple(children),
        unsupported=unsupported,
    )


def parse_machine(config: Dict[str, Any]) -> MachineIR:
    """Parse a whole XState config into the IR.

    Args:
        config: The raw machine config, as loaded from JSON.

    Returns:
        A ``MachineIR`` preserving hierarchy and recording unsupported keys.
    """
    raw_states = config.get("states")
    states: List[StateIR] = []
    if isinstance(raw_states, dict):
        for key, state_config in raw_states.items():
            states.append(parse_state(key, state_config, (key,)))

    raw_context = config.get("context")
    context: Optional[Dict[str, Any]] = None
    placeholder = False
    if isinstance(raw_context, dict):
        context = raw_context
    elif isinstance(raw_context, str):
        # 📝 Real Stately exports ship "{{initialContext}}" — tolerate it.
        placeholder = True

    machine_known = _KNOWN_STATE_KEYS | {"predictableActionArguments", "version"}
    unsupported = tuple(
        sorted(
            k
            for k in config
            if k not in machine_known and k not in _IGNORED_STATE_KEYS
        )
    )

    initial = config.get("initial")
    machine_id = config.get("id")

    # 🌳 Parse the root as a state too, so top-level on/entry/exit/tags/meta
    #    and `type: parallel` are captured rather than silently dropped.
    #    Children are cleared: `states` already owns them, and leaving them
    #    here would double every state in walk().
    root = dataclasses.replace(
        parse_state("", config, ()), children=(), unsupported=()
    )

    return MachineIR(
        id=machine_id if isinstance(machine_id, str) else "machine",
        initial=initial if isinstance(initial, str) else None,
        states=tuple(states),
        root=root,
        context=context,
        context_is_placeholder=placeholder,
        tags=tuple(
            t for t in _as_list(config.get("tags")) if isinstance(t, str)
        ),
        meta=config.get("meta") if isinstance(config.get("meta"), dict) else None,
        unsupported=unsupported,
    )
