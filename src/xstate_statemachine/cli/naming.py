# src/xstate_statemachine/cli/naming.py
# -----------------------------------------------------------------------------
# 🏛️ Identifier allocation for generated code
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: sanitising a name and using the result as the state
# *id* is a data-loss bug, not a formatting choice.
#
# The old ``safe_identifier()`` was naive string mangling with three
# consequences found in the v0.7.0 audit:
#
#   • No collision registry. ``"my-state"`` and ``"my_state"`` both became
#     ``my_state``; the second assignment silently destroyed the first. In the
#     reproducer the casualty was the machine's *initial* state.
#   • The mangled result was written back as the state id, so
#     ``matches("edgeCase.class")`` failed because the id had become
#     ``class_``.
#   • Keywords used as *service* names produced ``None = none`` — a hard
#     SyntaxError.
#
# The fix separates two concepts that were previously conflated:
#
#   ORIGINAL NAME  — belongs in the machine config, always preserved verbatim.
#   PYTHON BINDING — a local variable name, allocated collision-free.
#
# ``IdentifierAllocator`` owns the second and never touches the first.
# -----------------------------------------------------------------------------
"""Collision-free Python identifier allocation for generated code."""

from __future__ import annotations

import keyword
import re
import unicodedata
from typing import Dict, FrozenSet, Optional, Set

# 📝 Soft keywords are legal identifiers but shadowing them in generated code
#    produces confusing output; `match`/`case` in particular.
_SOFT_KEYWORDS = frozenset({"match", "case", "type", "_"})

# 📝 Builtins worth avoiding as bindings — shadowing these in a generated
#    module is legal but hostile to readers and linters.
_SHADOW_RISK = frozenset(
    {"id", "type", "input", "next", "object", "list", "dict", "set", "all"}
)

_INVALID_CHARS = re.compile(r"[^0-9a-zA-Z_]+")


def _transliterate(name: str) -> str:
    """Reduce Unicode to an ASCII-ish skeleton, keeping meaning where possible.

    ``"café"`` becomes ``"cafe"`` rather than ``"caf_"``. Scripts with no
    ASCII decomposition (e.g. CJK) fall through to the empty string and the
    caller supplies a positional fallback.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def to_identifier(name: str, *, fallback: str = "state") -> str:
    """Convert an arbitrary name into a syntactically valid Python identifier.

    This handles shape only. Uniqueness is the allocator's job.

    Args:
        name: The raw name from the machine config.
        fallback: Base used when *name* yields nothing usable.

    Returns:
        A valid, non-keyword Python identifier.
    """
    candidate = _INVALID_CHARS.sub("_", _transliterate(name)).strip("_")

    if not candidate:
        # 🌏 Names that are entirely non-ASCII (Cyrillic, CJK, emoji) reduce
        #    to nothing. The fallback is sanitised too — it is often derived
        #    from the same untrusted name, so trusting it verbatim would
        #    re-introduce the very characters we just stripped.
        candidate = _INVALID_CHARS.sub("_", _transliterate(fallback)).strip(
            "_"
        )
    if not candidate:
        candidate = "state"

    if candidate[0].isdigit():
        candidate = f"s_{candidate}"

    if keyword.iskeyword(candidate) or candidate in _SOFT_KEYWORDS:
        candidate = f"{candidate}_"
    elif candidate in _SHADOW_RISK:
        candidate = f"{candidate}_"

    return candidate


class IdentifierAllocator:
    """Hands out unique Python bindings for one generated module.

    Two different source names never receive the same binding, and asking
    twice for the same source name returns the same binding.

    Example::

        alloc = IdentifierAllocator()
        alloc.allocate("my-state")   # -> "my_state"
        alloc.allocate("my_state")   # -> "my_state_2"  (collision avoided)
        alloc.allocate("my-state")   # -> "my_state"    (stable)
    """

    def __init__(self, reserved: Optional[FrozenSet[str]] = None) -> None:
        """Initialise the allocator.

        Args:
            reserved: Names already bound in the target module (imports,
                helper functions) that must never be handed out.
        """
        self._by_key: Dict[str, str] = {}
        self._taken: Set[str] = set(reserved or frozenset())

    def allocate(self, name: str, *, fallback: str = "state") -> str:
        """Return a unique, stable binding for *name*.

        Args:
            name: The original name from the config, used verbatim as the key.
            fallback: Base to use if *name* has no identifier-safe characters.

        Returns:
            A Python identifier unique within this allocator.
        """
        if name in self._by_key:
            return self._by_key[name]

        base = to_identifier(name, fallback=fallback)
        candidate = base
        suffix = 2
        while candidate in self._taken:
            candidate = f"{base}_{suffix}"
            suffix += 1

        self._taken.add(candidate)
        self._by_key[name] = candidate
        return candidate

    def get(self, name: str) -> Optional[str]:
        """Return the binding already allocated for *name*, if any."""
        return self._by_key.get(name)

    def reserve(self, *names: str) -> None:
        """Mark *names* as unavailable without associating a source name."""
        self._taken.update(names)

    def __contains__(self, name: str) -> bool:
        """Whether a binding has been allocated for *name*."""
        return name in self._by_key


def literal(value: object) -> str:
    """Render *value* as a Python literal safe to embed in generated source.

    Uses ``repr()`` rather than hand-rolled quoting. The old emitters escaped
    strings manually, which broke on backslashes, newlines and mixed quotes.
    """
    return repr(value)


# 🛡️ Characters that let a value escape a docstring or inject a comment.
_DOCSTRING_UNSAFE = re.compile(r'["\\\r\n]')


def docstring_safe(value: object, *, limit: int = 120) -> str:
    """Render *value* for embedding in a generated docstring.

    🛡️ SECURITY: docstrings are the one place generated code interpolates a
    machine-supplied string *outside* a ``repr()``. A machine id containing
    ``\"\"\"`` closes the docstring early, after which the rest of the id is
    parsed as CODE — a config file becomes arbitrary execution the moment
    the generator verifies its own output.

    Reproducer this defends against::

        {"id": "p\\"\\"\\"\\n    import os; os.system('...')\\n    \\"\\"\\""}

    Quotes, backslashes and newlines are therefore removed rather than
    escaped: a docstring is prose, so there is nothing to preserve, and
    stripping cannot be undone by a second layer of interpretation.
    """
    text = str(value)
    cleaned = _DOCSTRING_UNSAFE.sub(" ", text).strip()
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "…"
    return cleaned or "machine"
