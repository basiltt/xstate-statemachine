# /src/xstate_statemachine/resolver.py
# -----------------------------------------------------------------------------
# 🗺️ State Target Resolver
# -----------------------------------------------------------------------------
# This module provides the crucial logic for resolving state target strings,
# a key feature for XState compatibility. Statechart transitions can target
# other states in various ways (e.g., relative to a parent, or absolutely
# from the root), and this resolver correctly interprets those targets.
#
# The `resolve_target_state` function acts as a "Strategy" selector, choosing
# the correct resolution method based on the format of the target string
# (e.g., does it start with '#', '.', or is it a plain ID?). This ensures
# a robust and predictable mechanism for navigating the statechart tree.
# -----------------------------------------------------------------------------
"""
Provides a centralized function for resolving transition target states.

This module is responsible for interpreting the `target` strings found in a
machine's configuration and resolving them to the correct `StateNode` object
within the statechart tree.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .exceptions import StateNotFoundError

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for Forward References
# -----------------------------------------------------------------------------
if TYPE_CHECKING:
    # This avoids circular import errors at runtime while providing type hints.
    from .models import StateNode, MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Private Helper Functions
# -----------------------------------------------------------------------------


def _validate_segments(
    segments: List[str], target: str, reference_id: str
) -> None:
    """Checks for invalid path segments like empty strings.

    This helper ensures that target paths like 'state..child' or 'state.'
    are rejected early, as they are syntactically invalid.

    Args:
        segments: The list of path segments produced by `split('.')`.
        target: The original target string, for error reporting.
        reference_id: The ID of the state where resolution started, for context.

    Raises:
        StateNotFoundError: If any segment is an empty string.
    """
    # 🛡️ Reject targets with consecutive or trailing dots (e.g., 'a..b', 'a.').
    if any(seg == "" for seg in segments):
        logger.error(
            "❌ Invalid target path '%s' contains empty segments.", target
        )
        raise StateNotFoundError(target, reference_id)


def _find_descendant(start_node: "StateNode", path: List[str]) -> "StateNode":
    """Traverses down the state tree to find a descendant node.

    Args:
        start_node: The `StateNode` from which to begin the search.
        path: A list of state keys representing the path to the descendant.

    Returns:
        The descendant `StateNode`.

    Raises:
        StateNotFoundError: If any key in the path does not correspond to a
            child state at that level of the traversal.
    """
    current = start_node
    for key in path:
        if key not in current.states:
            raise StateNotFoundError(".".join(path), start_node.id)
        current = current.states[key]
    return current


# -----------------------------------------------------------------------------
# 🗺️ Public Resolver Function
# -----------------------------------------------------------------------------


def resolve_target_state(
    target: str, reference_state: "StateNode"
) -> "StateNode":
    """Resolves a target string to a specific `StateNode` in the machine.

    This function implements the XState resolution algorithm, which provides
    flexible ways to target states from anywhere in the machine. The resolution
    is attempted in a specific order based on the target string's format.

    Args:
        target: The target string to resolve (e.g., "#foo", ".bar", "baz").
        reference_state: The `StateNode` from which the transition originates.

    Returns:
        The resolved `StateNode` object.

    Raises:
        TypeError: If the target is not a string.
        StateNotFoundError: If the target string is empty or cannot be
            resolved to a valid state in the machine.

    Resolution Order:
        1.  **Absolute Path**: If `target` starts with '#', it's resolved from
            the machine's root (e.g., `"#machine.state.child"`).
        2.  **Parent State**: If `target` is exactly '.', it resolves to the
            parent of the `reference_state`.
        3.  **Relative Path**: If `target` starts with '.', it's resolved
            relative to the parent of the `reference_state`.
        4.  **Plain Identifier**: Otherwise, it's treated as a plain ID and
            the function searches for a matching state by "bubbling up"
            the hierarchy from the `reference_state`.
    """
    # 🧪 Validate input type.
    if not isinstance(target, str):
        raise TypeError(
            f"Transition target must be a string, but got {type(target)}"
        )
    if not target:
        raise StateNotFoundError(target, reference_state.id)

    machine: "MachineNode" = reference_state.machine
    logger.debug(
        "🗺️ Resolving target '%s' from state '%s'", target, reference_state.id
    )

    # -------------------------------------------------------------------------
    # 🏛️ Strategy 1: Absolute path resolution (e.g., "#machine.state.child")
    # -------------------------------------------------------------------------
    if target.startswith("#"):
        logger.debug("  -> Attempting absolute path resolution...")
        segments = target[1:].split(".")
        _validate_segments(segments, target, reference_state.id)

        # 🏛️ Resolution order matters. The MACHINE key is checked first: a
        #    nested state is free to declare `id: "m"` while the machine is
        #    also called "m", and letting the custom-id registry win there
        #    silently redirected every existing `#m.child` target into that
        #    unrelated branch. The machine root is the more established
        #    meaning, so it keeps priority.
        if segments[0] == machine.key:
            try:
                return _find_descendant(machine, segments[1:])
            except StateNotFoundError:
                # ⤵️ Fall through: a custom id may still match, which keeps
                #    `#name.child` working when `name` shadows the machine key
                #    but the path only exists under the custom-id anchor.
                pass

        # 🏷️ A custom `id` declared on a state. XState lets any state name
        #    itself so distant branches can target it as `#myId`; without this
        #    the lookup demanded that the first segment be the MACHINE key, so
        #    every custom-id target raised `StateNotFoundError`. Supports
        #    `#myId` and `#myId.child.leaf`.
        custom_ids = getattr(machine, "_custom_ids", None)
        if custom_ids:
            anchor = custom_ids.get(segments[0])
            if anchor is not None:
                return (
                    anchor
                    if len(segments) == 1
                    else _find_descendant(anchor, segments[1:])
                )

        raise StateNotFoundError(target, reference_state.id)

    # -------------------------------------------------------------------------
    # 🏛️ Strategy 2: Parent state resolution ('.')
    # -------------------------------------------------------------------------
    if target == ".":
        logger.debug("  -> Attempting parent state resolution...")
        # ✅ Return parent, or self if at the root.
        return reference_state.parent or reference_state

    # -------------------------------------------------------------------------
    # 🏛️ Strategy 3: Relative path resolution (e.g., '.sibling')
    # -------------------------------------------------------------------------
    if target.startswith("."):
        logger.debug("  -> Attempting relative path resolution...")
        segments = target[1:].split(".")
        _validate_segments(segments, target, reference_state.id)
        # ✅ Base the search from the parent of the current state.
        base = reference_state.parent or reference_state
        return _find_descendant(base, segments)

    # -------------------------------------------------------------------------
    # 🏛️ Strategy 4: Plain ID resolution (e.g., 'myState')
    # -------------------------------------------------------------------------
    logger.debug("  -> Attempting plain ID resolution (bubbling up)...")
    segments = target.split(".")
    _validate_segments(segments, target, reference_state.id)

    current: Optional["StateNode"] = reference_state
    while current:
        # 4a. Is it a descendant of the current node?
        try:
            return _find_descendant(current, segments)
        except StateNotFoundError:
            pass  # If not, continue to the next check.

        # 4b. Is it the current node's key itself? (for non-dotted targets)
        if len(segments) == 1 and segments[0] == current.key:
            return current

        # 4c. 🛁 Bubble up to the parent and try again.
        current = current.parent

    # ❌ If we've bubbled up to the top and found nothing, the target is invalid.
    logger.error(
        "❌ Failed to resolve target '%s' from reference '%s'",
        target,
        reference_state.id,
    )
    raise StateNotFoundError(target, reference_state.id)
