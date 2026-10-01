# src/xstate_statemachine/contrib/django/audit.py
# -----------------------------------------------------------------------------
# 📜 DjangoAuditPlugin -- the audit row commits with the state change
# -----------------------------------------------------------------------------
# 🏛️ `django-fsm-log` writes its rows from a separate signal handler, so a
#    crash between the save and the handler leaves a state with no audit
#    row (or the reverse). Here the core `AuditPlugin` (#262) collects the
#    record while the machine runs; the mixin writes it with
#    ``DjangoTransitionLogStore.append`` on the SAME connection, inside the
#    SAME ``transaction.atomic()`` as the snapshot UPDATE. Payloads go
#    through the shared `redact` (X0.5 / X0.6).
#
# 📝 ``forget`` (X0.5) is a documented CHOICE: ``mode="redact"`` (default)
#    keeps the append-only chain and blanks ``payload``/``actor``/
#    ``reason``; ``mode="delete"`` removes the rows.
# -----------------------------------------------------------------------------
"""`DjangoTransitionLogStore`, `DjangoAuditPlugin`."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, List, Optional

from django.db.models import Max

from ...persistence.log import AuditPlugin, TransitionRecord

__all__ = ["DjangoAuditPlugin", "DjangoTransitionLogStore"]


def _log_model() -> Any:
    from django.apps import apps

    return apps.get_model("xsm_django", "TransitionLog")


def _ct(instance: Any) -> Any:
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.db_manager(
        instance._state.db or "default"
    ).get_for_model(type(instance), for_concrete_model=False)


class DjangoTransitionLogStore:
    """A `TransitionLogStore` bound to ONE row, writing `TransitionLog`.

    ``machine_id`` is ``"<app_label>.<model>:<pk>"``; the row identity
    comes from the bound instance, so records for other ids are refused.
    """

    def __init__(self, instance: Any, *, using: str = "default") -> None:
        self.instance = instance
        self.using = using
        self.machine_id = log_id(instance)
        self._ct_obj: Any = None
        self._next: Optional[int] = None
        #: The acting user OBJECT (the record only carries its id).
        self.actor: Any = None
        #: When set, `append` buffers instead of writing; `flush()` writes.
        #: 🏛️ The mixin buffers: a plugin's errors are CONTAINED by the
        #: engine, so an insert failing inside the interpreter would be
        #: swallowed while the state still committed. Flushing from the
        #: mixin, after the fenced UPDATE, lets a failure roll back both.
        self.buffer: Optional[List[TransitionRecord]] = None

    @property
    def _ct(self) -> Any:
        # 📝 Lazy: resolved on first WRITE, after the fenced UPDATE, so
        #    an optimistic send never reads before it writes (SQLite).
        if self._ct_obj is None:
            self._ct_obj = _ct(self.instance)
        return self._ct_obj

    def _qs(self) -> Any:
        return (
            _log_model()
            .objects.using(self.using)
            .filter(content_type=self._ct, object_id=str(self.instance.pk))
        )

    def next_seq(self, machine_id: str) -> int:
        if self.buffer is not None:
            # 📝 Provisional (1, 2, ...): the real seq is assigned by
            #    `flush()` AFTER the fenced UPDATE, so an optimistic send
            #    leads with its write (no read lock to upgrade on SQLite).
            return len(self.buffer) + 1
        if self._next is None:
            top = self._qs().aggregate(m=Max("seq"))["m"]
            self._next = int(top or 0) + 1
        return self._next

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        if rec.machine_id != self.machine_id:
            raise ValueError(
                f"record for {rec.machine_id!r} on a log bound to "
                f"{self.machine_id!r}"
            )
        self._next = rec.seq + 1
        if self.buffer is not None:
            self.buffer.append(rec)
            return
        self._write(rec)

    def flush(self) -> int:
        """Write buffered records now (the caller's transaction), with
        their final ``seq`` continuing this row's chain."""
        batch, self.buffer = list(self.buffer or ()), []
        if not batch:
            return 0
        base = int(self._qs().aggregate(m=Max("seq"))["m"] or 0)
        for i, rec in enumerate(batch, start=1):
            self._write(replace(rec, seq=base + i))
        self._next = base + len(batch) + 1
        return len(batch)

    def _write(self, rec: TransitionRecord) -> None:
        actor = self.actor
        actor_pk = getattr(actor, "pk", None) if actor is not None else None
        _log_model().objects.using(self.using).create(
            content_type=self._ct,
            object_id=str(self.instance.pk),
            seq=rec.seq,
            event=rec.event_type,
            payload=rec.event_payload,
            from_states=list(rec.from_states),
            to_states=list(rec.to_states),
            actions=list(rec.actions),
            disposition=rec.disposition,
            actor_id=actor_pk,
            reason=rec.reason or "",
            correlation_id=rec.correlation_id or "",
            machine_version=rec.machine_version or "",
        )

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        rows = self._qs().filter(seq__gt=after_seq).order_by("seq")[:limit]
        return [
            TransitionRecord(
                machine_id=self.machine_id,
                seq=r.seq,
                ts=r.created.timestamp(),
                event_type=r.event,
                event_payload=dict(r.payload or {}),
                from_states=tuple(r.from_states or ()),
                to_states=tuple(r.to_states or ()),
                actions=tuple(r.actions or ()),
                disposition=r.disposition,
                actor=None if r.actor_id is None else str(r.actor_id),
                reason=r.reason or None,
                correlation_id=r.correlation_id or None,
                machine_version=r.machine_version,
            )
            for r in rows
        ]

    def purge_older_than(self, cutoff_ts: float) -> int:
        from datetime import datetime, timezone

        cutoff = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc)
        n, _ = self._qs().filter(created__lt=cutoff).delete()
        return int(n)

    def forget(self, machine_id: str, *, mode: str = "redact") -> int:
        return forget_log(self.instance, using=self.using, mode=mode)


def log_id(instance: Any) -> str:
    return f"{instance._meta.label_lower}:{instance.pk}"


def forget_log(instance: Any, *, using: str, mode: str = "redact") -> int:
    """X0.5 for one row's audit trail (see module notes)."""
    if mode not in ("redact", "delete"):
        raise ValueError("mode must be 'redact' or 'delete'")
    qs = (
        _log_model()
        .objects.using(using)
        .filter(content_type=_ct(instance), object_id=str(instance.pk))
    )
    if mode == "delete":
        n, _ = qs.delete()
        return int(n)
    return int(qs.update(payload={}, actor=None, reason="", correlation_id=""))


class DjangoAuditPlugin(AuditPlugin):
    """`AuditPlugin` writing `TransitionLog` rows for one model instance.

    Attached per send by `StatechartModelMixin` when the model sets
    ``statechart_audit = True`` (the default when the ``xsm_django`` app
    and ``contenttypes`` are installed). ``actor_id`` / ``reason`` come
    from the payload `send(actor=, reason=)` built.
    """

    def __init__(
        self, instance: Any, *, using: str = "default", **kw: Any
    ) -> None:
        self.store = DjangoTransitionLogStore(instance, using=using)
        kw.setdefault("actor_key", "actor_id")
        super().__init__(
            self.store, machine_id=lambda i: self.store.machine_id, **kw
        )


def history_of(instance: Any, using: Optional[str] = None) -> Any:
    """``TransitionLog`` rows of *instance*, ordered by ``seq``."""
    return (
        _log_model()
        .objects.using(using or instance._state.db or "default")
        .filter(content_type=_ct(instance), object_id=str(instance.pk))
        .order_by("seq")
    )
