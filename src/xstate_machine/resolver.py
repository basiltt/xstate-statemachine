# src/xstate_python/resolver.py
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
# XState resolution logic.
# -----------------------------------------------------------------------------


def resolve_target_state(target: str, reference_state: StateNode) -> StateNode:
    """
    Resolves a target string to a StateNode.

    This function implements the state resolution algorithm:
    1. If target starts with '#', it's an absolute path from the machine root.
    2. If target starts with '.', it's a relative path from the reference state.
    3. Otherwise, it's a sibling or descendant of the reference state's parent.

    Args:
        target: The target string (e.g., "state1", ".child", "#machine.state1").
        reference_state: The state where the transition is defined.

    Returns:
        The resolved StateNode.

    Raises:
        StateNotFoundError: If the target cannot be resolved.
    """
    machine = reference_state.machine

    # 1. Absolute path from root (e.g., "#some.state")
    if target.startswith("#"):
        path = target[1:].split(".")
        # The first part of the path must match the machine ID
        if path[0] != machine.key:
            raise StateNotFoundError(target, reference_state.id)

        node = machine
        for key in path[1:]:
            if key not in node.states:
                raise StateNotFoundError(target, reference_state.id)
            node = node.states[key]
        return node

    # 2. Relative path from reference state (e.g., ".child")
    if target.startswith("."):
        path = target[1:].split(".")
        node = reference_state
        for key in path:
            if key not in node.states:
                raise StateNotFoundError(target, reference_state.id)
            node = node.states[key]
        return node

    # 3. Sibling or ancestor's child
    path = target.split(".")
    node = reference_state
    while node.parent:
        try:
            return _find_descendant(node.parent, path)
        except StateNotFoundError:
            node = node.parent

    # If not found in any ancestor, fail
    raise StateNotFoundError(target, reference_state.id)


def _find_descendant(start_node: StateNode, path: list[str]) -> StateNode:
    """Helper to find a descendant state from a path list."""
    current = start_node
    for key in path:
        if key not in current.states:
            raise StateNotFoundError(".".join(path), start_node.id)
        current = current.states[key]
    return current
