# src/xstate_statemachine/contrib/django/_events.py
"""Event-name helpers shared by the mixin, admin, DRF and Channels."""

from __future__ import annotations

from typing import Any, List

__all__ = ["available_events", "declared_events"]

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
