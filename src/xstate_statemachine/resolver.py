# src/xstate_statemachine/resolver.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import StateNotFoundError

if TYPE_CHECKING:
    from .models import StateNode


# -----------------------------------------------------------------------------
# 🗺️ State Resolver
# -----------------------------------------------------------------------------
# This module is responsible for the critical task of finding a target state
# node based on a target string from a reference state. It implements the full
# XState resolution logic, forming a core part of the state transition
# algorithm. Its functions are pure and have no side effects, adhering to the
# principle of Separation of Concerns.
# -----------------------------------------------------------------------------


def resolve_target_state(
    target: str, reference_state: "StateNode"
) -> "StateNode":
    """Resolves a target string to a specific StateNode within the machine.

    This function implements the state resolution algorithm according to the
    standard XState specification for resolving state targets:
    1.  **Absolute**: If the target starts with '#', it's an absolute path
        from the machine root (e.g., "#machine.state.child").
    2.  **Relative**: If the target starts with '.', it's a relative path
        from the parent of the reference state (or the state itself if it's the root).
    3.  **Sibling/Ancestor**: Otherwise, it's treated as a sibling of the reference
        state, bubbling up through ancestors if not found immediately.

    Args:
        target: The target string to resolve.
        reference_state: The `StateNode` where the transition is defined.

    Returns:
        The resolved `StateNode`.

    Raises:
        StateNotFoundError: If the target string cannot be resolved to a valid
                            state node in the machine.
        TypeError: If the provided target is not a string.
    """
    if not isinstance(target, str):
        raise TypeError(
            f"Transition target must be a string, but got {type(target)}"
        )

    machine = reference_state.machine

    if target == ".":
        return reference_state.parent or reference_state

    if target.startswith("#"):
        path = target[1:].split(".")
        if path[0] != machine.key:
            raise StateNotFoundError(target, reference_state.id)
        node = machine
        for key in path[1:]:
            if key not in node.states:
                raise StateNotFoundError(target, reference_state.id)
            node = node.states[key]
        return node

    if target.startswith("."):
        path = target[1:].split(".")
        start_node = reference_state.parent or reference_state
        return _find_descendant(start_node, path)

    path = target.split(".")
    node = reference_state
    while node:  # FIX: Change to `while node` to include the root machine.
        # Check if the target is a direct key of the current node
        if path[0] == node.key and len(path) == 1:
            return node

        # Check for descendants if the node has a parent
        if node.parent:
            try:
                return _find_descendant(node.parent, path)
            except StateNotFoundError:
                pass  # Not found, continue bubbling up

        node = node.parent

    raise StateNotFoundError(target, reference_state.id)


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------


def _find_descendant(start_node: "StateNode", path: list[str]) -> "StateNode":
    """A private helper to find a descendant state from a path list.

    This function traverses down the state tree from a given starting node.

    Args:
        start_node: The `StateNode` from which to begin the search.
        path: A list of state keys representing the path to the descendant.

    Returns:
        The found descendant `StateNode`.

    Raises:
        StateNotFoundError: If any key in the path does not correspond to a
                            valid child state.
    """
    current = start_node
    for key in path:
        if key not in current.states:
            raise StateNotFoundError(".".join(path), start_node.id)
        current = current.states[key]
    return current
