# src/xstate_statemachine/contrib/django/inbox.py
# -----------------------------------------------------------------------------
# 📥 DjangoInbox -- the idempotency inbox (#261) on the ORM
# -----------------------------------------------------------------------------
# 🏛️ Implements `InboxStore` on ``xsm_django_idempotencyrecord``. Every
#    call is a plain ORM statement, so inside a model ``send()`` the claim
#    and the mark JOIN the send's ``transaction.atomic()``: the receipt is
#    recorded exactly when the state change commits (X0.3), and a rolled-
#    back send leaves the key unclaimed for the retry. The scope is
#    ``principal / machine.id / instance`` (X0.2) -- the DRF viewset
#    derives the principal from ``request.user``.
# -----------------------------------------------------------------------------
"""`DjangoInbox`."""

from __future__ import annotations

import time
from typing import Any, Optional

from django.db import IntegrityError, transaction

from ...persistence.idempotency import InboxEntry

__all__ = ["DjangoInbox"]


class DjangoInbox:
    """`InboxStore` in the ``xsm_django`` app's tables."""

    def __init__(self, *, using: str = "default") -> None:
        self.using = using

    @property
    def _qs(self) -> Any:
        from django.apps import apps

        return apps.get_model("xsm_django", "IdempotencyRecord").objects.using(
            self.using
        )

    @staticmethod
    def _live(row: Any, now: float) -> bool:
        return row.expires_at is None or row.expires_at > now

    @staticmethod
    def _exp(ttl_s: Optional[float], now: float) -> Optional[float]:
        return None if ttl_s is None else now + float(ttl_s)

    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        row = self._qs.filter(scope=scope, key=key).first()
        if row is None or not self._live(row, time.time()):
            return None
        return InboxEntry(row.fingerprint, row.receipt_json, row.expires_at)

    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        now = time.time()
        self._qs.filter(scope=scope, key=key, expires_at__lte=now).delete()
        try:
            with transaction.atomic(using=self.using):
                self._qs.create(
                    scope=scope,
                    key=key,
                    fingerprint=fp,
                    receipt_json=None,
                    expires_at=self._exp(ttl_s, now),
                )
        except IntegrityError:
            return False
        return True

    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        now = time.time()
        n = self._qs.filter(scope=scope, key=key).update(
            receipt_json=receipt_json, expires_at=self._exp(ttl_s, now)
        )
        if not n:
            self._qs.create(
                scope=scope,
                key=key,
                fingerprint="",
                receipt_json=receipt_json,
                expires_at=self._exp(ttl_s, now),
            )

    def release(self, scope: str, key: str) -> None:
        self._qs.filter(
            scope=scope, key=key, receipt_json__isnull=True
        ).delete()

    def purge_expired(self, *, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        n, _ = self._qs.filter(expires_at__lte=now).delete()
        return int(n)

    def forget(self, scope: str) -> int:
        n, _ = self._qs.filter(scope=scope).delete()
        return int(n)
