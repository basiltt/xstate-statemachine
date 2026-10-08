# src/xstate_statemachine/contrib/django/_events.py
"""Event-name helpers shared by the mixin, admin, DRF and Channels."""

from __future__ import annotations

from typing import Any, List

__all__ = ["available_events", "declared_events", "value_from_ids"]

_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")


def declared_events(machine: Any) -> List[str]:
    """Declared, client-sendable event names (sorted)."""
    return sorted(
        e
        for e in machine.known_events
        if not e.startswith(_INTERNAL_PREFIXES) and "*" not in e and e
    )


def available_events(interp: Any) -> List[str]:
    """User-facing events that would cause a transition right now."""
    return [e for e in declared_events(interp.machine) if interp.can(e)]


def value_from_ids(machine: Any, state_ids: Any) -> Any:
    """XState's hierarchical ``value`` for a set of leaf *state_ids*
    (what `interp.value` gives for a LIVE machine), without hydrating an
    interpreter -- a receipt / an audit row carries ids only."""
    ids = set(state_ids)
    root = machine

    def active(node: Any) -> bool:
        return node.id in ids or any(active(c) for c in node.states.values())

    def value_of(node: Any) -> Any:
        if getattr(node, "type", "") == "parallel":
            return {
                key: value_of(child)
                for key, child in node.states.items()
                if active(child)
            }
        child = next((c for c in node.states.values() if active(c)), None)
        if child is None:
            return node.key
        if not child.states:
            return child.key
        return {child.key: value_of(child)}

    if not ids:
        return {}
    return value_of(root)
