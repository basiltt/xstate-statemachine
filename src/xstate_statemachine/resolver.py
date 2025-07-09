# ─── src/xstate_statemachine/resolver.py ──────────────────────────────────────
from __future__ import annotations
from typing import TYPE_CHECKING, List
from .exceptions import StateNotFoundError

if TYPE_CHECKING:
    from .models import StateNode


_ILLEGAL_DOTS_MSG = "Target path contains empty segments"


def _validate_segments(segments: List[str], target: str, ref: str) -> None:
    """Reject trailing dots (‘b.’) or consecutive dots (‘b..c’)."""
    if any(seg == "" for seg in segments):
        raise StateNotFoundError(target, ref)


def resolve_target_state(
    target: str, reference_state: "StateNode"
) -> "StateNode":
    """
    Resolve *target* (XState-style string) against *reference_state*.

    Resolution order:

    1.  Absolute   – starts with '#'
    2.  Single dot – '.'  →  parent (or self if root)
    3.  Dot path   – '.foo.bar'  →  descendant of parent
    4.  Plain id   – try as
        a) descendant of *current* (new),
        b) the *current* node itself,
        c) bubble to ancestor and repeat
    """
    if not isinstance(target, str):
        raise TypeError(
            f"Transition target must be a string, but got {type(target)}"
        )
    if target == "":
        raise StateNotFoundError(target, reference_state.id)

    machine = reference_state.machine

    # ── 1.  Absolute path  ──────────────────────────────────────────────────
    if target.startswith("#"):
        segments = target[1:].split(".")
        _validate_segments(segments, target, reference_state.id)
        if segments[0] != machine.key:
            raise StateNotFoundError(target, reference_state.id)

        node: StateNode = machine
        for key in segments[1:]:
            if key not in node.states:
                raise StateNotFoundError(target, reference_state.id)
            node = node.states[key]
        return node

    # ── 2.  Single dot  (‘.’)  ──────────────────────────────────────────────
    if target == ".":
        return reference_state.parent or reference_state

    # ── 3.  Dot-relative path  (‘.foo.bar’)  ────────────────────────────────
    if target.startswith("."):
        segments = target[1:].split(".")
        _validate_segments(segments, target, reference_state.id)
        base = reference_state.parent or reference_state
        return _find_descendant(base, segments)

    # ── 4.  Plain identifier / dotted path  ─────────────────────────────────
    segments = target.split(".")
    _validate_segments(segments, target, reference_state.id)

    current: StateNode | None = reference_state
    while current:
        # 4a ▸ descendant of *current*
        try:
            return _find_descendant(current, segments)
        except StateNotFoundError:
            pass

        # 4b ▸ the node itself?
        if len(segments) == 1 and segments[0] == current.key:
            return current

        # 4c ▸ bubble up one level
        current = current.parent

    # Nothing matched
    raise StateNotFoundError(target, reference_state.id)


# Helper stays unchanged (but note empty path never reaches it now)
def _find_descendant(start_node: "StateNode", path: List[str]) -> "StateNode":
    current = start_node
    for key in path:
        if key not in current.states:
            raise StateNotFoundError(".".join(path), start_node.id)
        current = current.states[key]
    return current
