# src/xstate_statemachine/contrib/django/outbox.py
# -----------------------------------------------------------------------------
# 📤 DjangoOutboxStore -- the transactional outbox on the ORM (D5 parity)
# -----------------------------------------------------------------------------
# 🏛️ Implements the EDA core's `OutboxStore` protocol (#293) on
#    ``xsm_django_outboxmessage``. ``add()`` is a plain ORM insert, so it
#    joins whatever ``transaction.atomic()`` is open -- a model's
#    ``send()`` (attach an `OutboxPlugin(DjangoOutboxStore())` via
#    ``statechart_plugins``) or a `persisted()` block over `DjangoStore`
#    under a ``with store.transaction():``. A forced rollback leaves NO
#    row; an `OutboxRelay` publishes committed rows at least once.
# -----------------------------------------------------------------------------
"""`DjangoOutboxStore`."""

from __future__ import annotations

import time
from typing import Any, List

from ...eda.envelope import Envelope
from ...eda.outbox import OutboxRecord

__all__ = ["DjangoOutboxStore"]


class DjangoOutboxStore:
    """`OutboxStore` in the ``xsm_django`` app's outbox table."""

    def __init__(self, *, using: str = "default") -> None:
        self.using = using

    @property
    def _model(self) -> Any:
        from django.apps import apps

        return apps.get_model("xsm_django", "OutboxMessage")

    def add(self, topic: str, envelope: Envelope) -> None:
        self._model.objects.using(self.using).create(
            message_id=envelope.id,
            topic=topic,
            subject=envelope.subject,
            envelope=envelope.to_json(),
            created_at=time.time(),
        )

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        rows = (
            self._model.objects.using(self.using)
            .filter(sent_at__isnull=True)
            .order_by("seq")[: int(limit)]
        )
        return [
            OutboxRecord(int(r.seq), r.topic, Envelope.from_json(r.envelope))
            for r in rows
        ]

    def mark_sent(self, seqs: List[int]) -> int:
        if not seqs:
            return 0
        return int(
            self._model.objects.using(self.using)
            .filter(seq__in=[int(s) for s in seqs], sent_at__isnull=True)
            .update(sent_at=time.time())
        )

    def count(self, *, pending_only: bool = False) -> int:
        qs = self._model.objects.using(self.using).all()
        if pending_only:
            qs = qs.filter(sent_at__isnull=True)
        return int(qs.count())

    def purge_sent(self, *, older_than_s: float = 86400.0) -> int:
        n, _ = (
            self._model.objects.using(self.using)
            .filter(sent_at__lt=time.time() - float(older_than_s))
            .delete()
        )
        return int(n)
