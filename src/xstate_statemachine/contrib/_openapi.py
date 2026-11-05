# src/xstate_statemachine/contrib/_openapi.py
# -----------------------------------------------------------------------------
# 🆔 operationIds shared by the `[fastapi]` router and the `[litestar]`
#    controller -- one rule, so a chart gets the SAME ids from both.
# -----------------------------------------------------------------------------
"""Stable, unique OpenAPI operationIds for per-event routes."""

from __future__ import annotations

import string
import unicodedata
from typing import Dict, Iterable, Sequence

__all__ = [
    "FIXED_OPS",
    "ident",
    "operation_ids",
    "require_route_safe_events",
]

#: Suffixes of the fixed routes' operationIds (``<op>_get`` ...).
FIXED_OPS = frozenset({"get", "send", "events", "diagram", "stream"})


def ident(etype: str) -> str:
    """ASCII ``[a-z0-9_]`` spelling of *etype* (operationIds feed SDK
    generators: ``éclair`` → ``eclair``, ``pay-now`` → ``pay_now``)."""
    ascii_ = (
        unicodedata.normalize("NFKD", etype)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return "".join(c if c.isalnum() else "_" for c in ascii_).lower() or "e"


def operation_ids(op: str, events: Sequence[str]) -> Dict[str, str]:
    """A UNIQUE and STABLE operationId per event route.

    🔥 battle #276-b / #278-b: ``ORDER.PAID`` and ``ORDER_PAID`` both
    became ``order_order_paid`` and an event named ``GET``/``send`` reused
    a fixed route's id -- an invalid document (Litestar answered 500 on
    ``/schema/openapi.json``) and merged methods in generated SDKs.

    📝 Stability, stated precisely (review CW-13 corrected an overclaim):
    adding an event whose id does not collide with an existing one never
    moves any id. A COLLISION is resolved deterministically: events whose
    name already IS the folded identifier (``ORDER_PAID``) claim the plain
    id first, in declaration order; names that had to be folded
    (``ORDER.PAID``, ``pay-now``) come second and take a ``_2`` ... suffix
    only when the plain id is taken. So adding ``ORDER_PAID`` to a chart
    that already has ``ORDER.PAID`` re-numbers ``ORDER.PAID`` (to
    ``..._2``) -- avoid such look-alike names, or pin ``operation_id``
    yourself, when an SDK depends on the ids. Fixed routes never lose
    their id.
    """
    taken = {f"{op}_{f}" for f in FIXED_OPS}
    out: Dict[str, str] = {}
    plain = [e for e in events if ident(e) == e.lower()]
    folded = [e for e in events if ident(e) != e.lower()]
    for etype in plain + folded:
        base = f"{op}_{ident(etype)}"
        cand, n = base, 1
        while cand in taken:
            n += 1
            cand = f"{base}_{n}"
        taken.add(cand)
        out[etype] = cand
    return out


#: Characters that change how a path TEMPLATE is parsed or routed. A plain
#: space is NOT one of them: clients send it as ``%20``, the ASGI server
#: decodes it before matching, and the generated router already serves
#: look-alike names such as ``"pay now"`` / ``"pay-now"`` side by side
#: (`operation_ids` disambiguates them). Line breaks and tabs stay refused.
_ROUTE_UNSAFE = frozenset("/{}?#%" + chr(92)) | (
    frozenset(string.whitespace) - frozenset(" ")
)


def require_route_safe_events(events: Iterable[str]) -> None:
    """Refuse event names that cannot be a route path segment.

    🔥 Review CW-30: names were interpolated straight into
    ``/<key>/events/<EVENT>``: ``order/paid`` added a segment, ``a{b}``
    became a path parameter and ``a?b`` / ``a#b`` never matched -- the
    router built without a word and the route was unreachable or shadowed
    another. Silent acceptance is a bug: fail at build time, naming the
    event.

    Args:
        events: The declared, client-sendable event names.

    Raises:
        ValueError: If a name holds a character unsafe in a URL path.
    """
    for etype in events:
        bad = sorted(c for c in set(etype) if c in _ROUTE_UNSAFE)
        if bad:
            raise ValueError(
                f"Event {etype!r} cannot be served as a per-event route: "
                f"it contains {bad!r}, which is not safe in a URL path "
                f"segment. Rename the event."
            )
