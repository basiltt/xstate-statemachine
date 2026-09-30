# src/xstate_statemachine/contrib/django/_deadlines.py
# -----------------------------------------------------------------------------
# ⏰ Deadline-index primitives on the ORM (internal)
# -----------------------------------------------------------------------------
# 🏛️ `StatechartModelMixin` (source = the model's ``db_table``) and
#    `DjangoStore` (source = its namespace) keep one row per armed `after`
#    timer in ``xsm_django_deadline``; `due_keys` answers the scanner from
#    the ``(source, due_at_wall)`` index instead of loading every snapshot.
#    Every function runs on the CALLER's connection / transaction, so the
#    rows commit with the state change or not at all.
# -----------------------------------------------------------------------------
"""Deadline rows (internal)."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

from django.db.models import Min

from ...persistence.deadline import Deadline

__all__: List[str] = []


def _model() -> Any:
    # 📝 Through the app registry, never `from .models import`: the test
    #    suite imports this package under two names (`src.` and the
    #    installed one) and a second import of models.py would register
    #    conflicting model classes.
    from django.apps import apps

    return apps.get_model("xsm_django", "StatechartDeadline")


def write(
    using: str, source: str, key: str, deadlines: Sequence[Deadline]
) -> int:
    """Replace the rows of (*source*, *key*); return how many were
    removed."""
    m = _model()
    removed, _ = m.objects.using(using).filter(source=source, key=key).delete()
    if deadlines:
        m.objects.using(using).bulk_create(
            [
                m(
                    source=source,
                    key=key,
                    state_id=d.state_id,
                    entry_seq=int(d.entry_seq),
                    due_at_wall=float(d.due_at_wall),
                    delay_ms=int(d.delay_ms),
                    event_type=d.event_type,
                )
                for d in deadlines
            ]
        )
    return int(removed)


def read(using: str, source: str, key: str) -> List[Deadline]:
    m = _model()
    return [
        Deadline(
            state_id=r.state_id,
            entry_seq=int(r.entry_seq),
            due_at_wall=float(r.due_at_wall),
            delay_ms=int(r.delay_ms),
            event_type=r.event_type,
        )
        for r in m.objects.using(using)
        .filter(source=source, key=key)
        .order_by("due_at_wall", "id")
    ]


def due(
    using: str, source: str, until_wall: float, limit: int
) -> List[Tuple[str, float]]:
    m = _model()
    rows = (
        m.objects.using(using)
        .filter(source=source, due_at_wall__lte=until_wall)
        .values("key")
        .annotate(first=Min("due_at_wall"))
        .order_by("first", "key")[: int(limit)]
    )
    return [(str(r["key"]), float(r["first"])) for r in rows]
