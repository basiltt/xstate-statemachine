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
import warnings
from typing import TYPE_CHECKING, List, Optional, Set, Tuple

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


def _machine_of(node: "StateNode") -> Optional["StateNode"]:
    """Walk to the root of *node*'s tree."""
    current: Optional["StateNode"] = node
    while current is not None and current.parent is not None:
        current = current.parent
    return current


#: (source id, target) pairs already warned about, so a hot transition
#: does not warn on every event (#31).
_SIBLING_FALLBACKS_WARNED: Set[Tuple[str, str]] = set()
#: Cap on the throttle set (#31 ride-along). A long-lived process that
#: builds a machine per job accumulated one entry per distinct pair
#: forever; past the cap the set is cleared, which at worst re-warns once.
_SIBLING_FALLBACKS_WARNED_MAX = 1024


def _warn_sibling_fallback(
    target: str, source: "StateNode", resolved: "StateNode"
) -> None:
    key = (source.id, target)
    if key in _SIBLING_FALLBACKS_WARNED:
        return
    if len(_SIBLING_FALLBACKS_WARNED) >= _SIBLING_FALLBACKS_WARNED_MAX:
        _SIBLING_FALLBACKS_WARNED.clear()
    _SIBLING_FALLBACKS_WARNED.add(key)
    root = _machine_of(source)
    machine_id = root.id if root is not None else "?"
    warnings.warn(
        f"Target '{target}' on state '{source.id}' resolved to the SIBLING "
        f"'{resolved.id}' via the pre-0.8.0 fallback (XState reads a "
        f"leading dot as 'child of the source'). Write it unambiguously as "
        f"'#{resolved.id}' -- or set 'strictTargets': true on machine "
        f"'{machine_id}' to disable the fallback. The fallback is removed "
        f"in 1.0.",
        DeprecationWarning,
        # 📍 Reached from several depths (build-time validation, runtime
        #    resolution); the message names the source state and target, so
        #    the frame attribution matters less than the text.
        stacklevel=2,
    )


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
        # 🔑 The machine key may itself contain dots (`"my.machine"`), in
        #    which case it spans several segments. Match the longest prefix
        #    of the raw path against the key rather than `segments[0]` alone,
        #    otherwise every `#my.machine.x` target is unresolvable (#30/#31
        #    review) -- and `pythonic` emits exactly that form.
        raw = target[1:]
        if raw == machine.key or raw.startswith(machine.key + "."):
            rest = raw[len(machine.key) :]
            try:
                return _find_descendant(
                    machine, rest[1:].split(".") if rest else []
                )
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
        # 🏛️ Architecture decision (0.8.0, #31): XState resolves a leading
        #    dot into the SOURCE state's own descendants -- `{target:
        #    ".child"}` on state `A` enters `A.child`. Verified against
        #    XState 5.33.0. Before 0.8.0 this library based the lookup on
        #    the source's PARENT (a "sibling" reading), so every `.child`
        #    target failed to resolve and the transition was silently
        #    dropped. The child lookup is now primary. The sibling reading
        #    is kept as a FALLBACK so machines written against the old
        #    behaviour keep working -- but under `strictTargets: True` that
        #    fallback is disabled and a `.child` that is not a child raises.
        try:
            return _find_descendant(reference_state, segments)
        except StateNotFoundError:
            pass
        root = _machine_of(reference_state)
        if root is not None and getattr(root, "strict_targets", False):
            raise StateNotFoundError(target, reference_state.id)
        base = reference_state.parent or reference_state
        resolved = _find_descendant(base, segments)
        # 📢 #31 (0.8.1): the fallback succeeded, so the machine relies on
        #    the pre-0.8.0 sibling reading. Say so, once per (source,
        #    target) pair, and name the unambiguous spelling -- this is the
        #    migration path that lets a 0.7.x codebase find its own
        #    ambiguous targets without a flag day.
        _warn_sibling_fallback(target, reference_state, resolved)
        return resolved

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
