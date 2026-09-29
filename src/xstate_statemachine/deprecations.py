# src/xstate_statemachine/deprecations.py
# -----------------------------------------------------------------------------
# ⏳ Deprecation policy helper (#296)
# -----------------------------------------------------------------------------
# One helper so every deprecation in the library says the same four things:
# WHAT is deprecated, SINCE which release, the release it is REMOVED in at the
# earliest, and the ALTERNATIVE. The policy itself (one minor release of
# warning, removal no earlier than the next major) lives in
# docs/_guide/deprecation-policy.md; `deprecations()` feeds that page.
#
# 🏛️ Once per CALL SITE, keyed by (what, caller filename, caller lineno):
#    a hot loop that touches `ErrorEvent.data` a million times warns once,
#    but two different lines of user code each learn about it. Python's own
#    `__warningregistry__` does the same thing only under the "default"
#    filter -- pytest and `-W always` switch that off, so the helper keeps
#    its own record.
# -----------------------------------------------------------------------------
"""Deprecation helper and registry.

Example:
    >>> from xstate_statemachine.deprecations import deprecations
    >>> any(d.what == "ErrorEvent.data" for d in deprecations())
    True
"""

from __future__ import annotations

import sys
import threading
import warnings
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

__all__ = [
    "Deprecation",
    "deprecated",
    "deprecations",
    "register",
    "reset_deprecation_warnings",
]


class Deprecation(NamedTuple):
    """One registered deprecation (what the policy page renders)."""

    what: str
    since: str
    removal: str
    alternative: str


_REGISTRY: Dict[str, Deprecation] = {}
_SEEN: Set[Tuple[str, str, int]] = set()
_LOCK = threading.Lock()
#: Bound so a pathological caller (generated code, exec) cannot grow the
#: record without limit; on overflow it is cleared and warnings repeat.
_SEEN_MAX = 4096


def register(
    what: str, *, since: str, removal: str, alternative: str
) -> Deprecation:
    """Record a deprecation in the registry without emitting anything.

    For deprecations whose warning has its own, older de-duplication rule
    (e.g. once per process) but that must still appear in the policy table.
    """
    entry = Deprecation(what, since, removal, alternative)
    with _LOCK:
        _REGISTRY[what] = entry
    return entry


def _message(entry: Deprecation, detail: Optional[str]) -> str:
    text = (
        f"{entry.what} is deprecated since {entry.since} and will be "
        f"removed in {entry.removal}; use {entry.alternative} instead."
    )
    return f"{text} {detail}" if detail else text


def deprecated(
    what: str,
    *,
    since: str,
    removal: str,
    alternative: str,
    detail: Optional[str] = None,
    stacklevel: int = 2,
) -> bool:
    """Emit a `DeprecationWarning` once per call site.

    Args:
        what: The deprecated thing, e.g. ``"ErrorEvent.data"``.
        since: The release that first warned, e.g. ``"0.9.0"``.
        removal: The earliest release that removes it, e.g. ``"1.0"``.
        alternative: What to use instead.
        detail: Optional extra sentence appended to the message.
        stacklevel: As for `warnings.warn`, relative to the CALLER of
            `deprecated` (2 = the function that called this helper's
            caller -- i.e. user code for a direct shim).

    Returns:
        True if a warning was emitted, False if this call site already
        warned.
    """
    entry = register(
        what, since=since, removal=removal, alternative=alternative
    )
    try:
        frame = sys._getframe(stacklevel)
        site = (what, frame.f_code.co_filename, frame.f_lineno)
    except ValueError:  # stack shallower than stacklevel
        site = (what, "<unknown>", 0)
    with _LOCK:
        if site in _SEEN:
            return False
        if len(_SEEN) >= _SEEN_MAX:
            _SEEN.clear()
        _SEEN.add(site)
    warnings.warn(
        _message(entry, detail), DeprecationWarning, stacklevel=stacklevel + 1
    )
    return True


def deprecations() -> List[Deprecation]:
    """Every registered deprecation, sorted by name."""
    with _LOCK:
        return sorted(_REGISTRY.values())


def reset_deprecation_warnings() -> None:
    """Forget which call sites have warned. For tests."""
    with _LOCK:
        _SEEN.clear()


# -----------------------------------------------------------------------------
# 📋 The library's current deprecations. Registered at import so the policy
#    page and `deprecations()` list them even before one fires.
# -----------------------------------------------------------------------------
register(
    "ErrorEvent.data",
    since="0.9.0",
    removal="1.0",
    alternative="ErrorEvent.error",
)
register(
    "--style",
    since="0.4.1",
    removal="1.0",
    alternative="--template",
)
for _name in ("engine_done", "engine_error", "engine_after"):
    register(
        f"xstate_statemachine.events.{_name}",
        since="0.9.0",
        removal="1.0",
        alternative=f"nothing -- internal; `_{_name}` is private",
    )
register(
    "leading-dot sibling target fallback",
    since="0.8.0",
    removal="1.0",
    alternative="'#<state id>' or 'strictTargets': true",
)
register(
    "strict_targets=False",
    since="0.8.0",
    removal="1.0",
    alternative="fix the unresolvable targets",
)
register(
    "implicit actionErrorPolicy default 'continue'",
    since="0.8.0",
    removal="1.0 (default becomes 'rollback')",
    alternative="an explicit 'actionErrorPolicy' on every machine",
)
register(
    "reserved send() keywords in a dict-form payload",
    since="0.4.1",
    removal="1.0",
    alternative="renamed payload keys (not 'wait' / 'priority')",
)
