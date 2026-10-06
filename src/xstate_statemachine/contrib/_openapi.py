# src/xstate_statemachine/contrib/_openapi.py
# -----------------------------------------------------------------------------
# 🆔 operationIds shared by the `[fastapi]` router and the `[litestar]`
#    controller -- one rule, so a chart gets the SAME ids from both.
# -----------------------------------------------------------------------------
"""Stable, unique OpenAPI operationIds for per-event routes."""

from __future__ import annotations

import unicodedata
from typing import Dict, Sequence

__all__ = ["FIXED_OPS", "ident", "operation_ids"]

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

    📝 ids must not move when an event is ADDED later -- a generated SDK
    pins them. Events whose name already IS the folded identifier
    (``ORDER_PAID``) claim the plain id first, in declaration order; names
    that had to be folded (``ORDER.PAID``, ``pay-now``) come second and
    take a ``_2`` ... suffix only when the plain id is taken. Fixed routes
    never lose their id.
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
