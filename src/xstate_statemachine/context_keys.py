# src/xstate_statemachine/context_keys.py
# -----------------------------------------------------------------------------
# 🔑 Library-private context keys
# -----------------------------------------------------------------------------
# 🏛️ #265 battle: some library bookkeeping must SURVIVE the process -- under
#    create → act → persist → discard the interpreter is thrown away after
#    every request, so anything that has to be there next time has to be in
#    the snapshot, and the only user-shaped, migrator-visible, redactable
#    place in the snapshot is `context`. Such keys carry the `_xsm_` prefix
#    and are the library's, not the user's: validators ignore them, API body
#    serializers drop them, and user code must not rely on them.
#
#    The first such key is the dead-letter error chain
#    (`patterns.dead_letter.ERRORS_CONTEXT_KEY == "_xsm_errors"`).
# -----------------------------------------------------------------------------
"""The reserved `_xsm_` context-key prefix and its one predicate."""

from __future__ import annotations

from typing import Any, Dict

__all__ = [
    "PRIVATE_CONTEXT_PREFIX",
    "is_private_context_key",
    "public_context",
]

#: Keys starting with this are the library's bookkeeping, persisted in the
#: snapshot's ``context`` but not part of the user's domain model.
PRIVATE_CONTEXT_PREFIX = "_xsm_"


def is_private_context_key(key: Any) -> bool:
    """``True`` for a library-private context key (``_xsm_…``)."""
    return isinstance(key, str) and key.startswith(PRIVATE_CONTEXT_PREFIX)


def public_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """A shallow copy of *ctx* without the library-private keys -- what a
    generic API body or a user-facing serializer should show."""
    return {k: v for k, v in ctx.items() if not is_private_context_key(k)}
