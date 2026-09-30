# src/xstate_statemachine/contrib/django/models.py
# -----------------------------------------------------------------------------
# ðŸ—ƒï¸ The app's own tables (label ``xsm_django``)
# -----------------------------------------------------------------------------
#    xsm_django_snapshot   `DjangoStore` key-value records
#    xsm_django_deadline   durable `after` deadlines, indexed by due time --
#                          what `DueTimerScanner` / ``xsm_deadlines`` read
#    xsm_django_lock       `DjangoStore.lock()` leases (portable: SQLite has
#                          no row locks)
#    xsm_django_transitionlog  audit rows, written in send()'s transaction
#    xsm_django_outboxmessage  transactional outbox (`DjangoOutboxStore`)
#
# ðŸ“ ``source`` names the owner of a key: a model's ``db_table`` for
#    `StatechartModelMixin` rows, the store's namespace for `DjangoStore`.
# -----------------------------------------------------------------------------
"""Models of the ``xsm_django`` app."""

from __future__ import annotations

from django.conf import settings
from django.db import models

__all__ = [
    "OutboxMessage",
    "StatechartDeadline",
    "StatechartLock",
    "StatechartSnapshot",
    "TransitionLog",
]


class StatechartSnapshot(models.Model):
    """One `DjangoStore` record."""

    source = models.CharField(max_length=128)
    key = models.CharField(max_length=200)
    snapshot = models.TextField()
    version = models.PositiveIntegerField(default=1)
    machine_version = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.FloatField()

    class Meta:
        app_label = "xsm_django"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "key"], name="xsm_snapshot_source_key"
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - admin display
        return f"{self.source}:{self.key}@{self.version}"


class StatechartDeadline(models.Model):
    """A persisted `after` deadline (#264) of one key."""

    source = models.CharField(max_length=128)
    key = models.CharField(max_length=200)
    state_id = models.CharField(max_length=512)
    entry_seq = models.IntegerField()
    due_at_wall = models.FloatField()
    delay_ms = models.BigIntegerField()
    event_type = models.CharField(max_length=600)

    class Meta:
        app_label = "xsm_django"
        indexes = [
            models.Index(
                fields=["source", "due_at_wall"], name="xsm_deadline_due"
            ),
            models.Index(fields=["source", "key"], name="xsm_deadline_key"),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin display
        return f"{self.source}:{self.key} {self.event_type}@{self.due_at_wall}"


class StatechartLock(models.Model):
    """A `DjangoStore.lock()` lease; reclaimed once ``expires_at`` passes."""

    source = models.CharField(max_length=128)
    key = models.CharField(max_length=200)
    owner = models.CharField(max_length=64)
    expires_at = models.FloatField()

    class Meta:
        app_label = "xsm_django"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "key"], name="xsm_lock_source_key"
            )
        ]


class TransitionLog(models.Model):
    """One processed event of one statechart row (#281).

    Written by `DjangoAuditPlugin` INSIDE ``send()``'s transaction, so an
    audit row exists exactly when its state change does. ``payload`` is
    redacted (the shared `redact`); ``actor`` is the acting user.
    ``order.history`` (`StatechartModelMixin.history`) reads these, newest
    last by ``seq``.
    """

    content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.CASCADE
    )
    object_id = models.CharField(max_length=64)
    seq = models.PositiveIntegerField()
    event = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    from_states = models.JSONField(default=list, blank=True)
    to_states = models.JSONField(default=list, blank=True)
    actions = models.JSONField(default=list, blank=True)
    disposition = models.CharField(max_length=16, default="transition")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reason = models.TextField(blank=True, default="")
    correlation_id = models.CharField(max_length=128, blank=True, default="")
    machine_version = models.CharField(max_length=255, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "xsm_django"
        ordering = ["content_type", "object_id", "seq"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "seq"],
                name="xsm_transitionlog_seq",
            )
        ]
        indexes = [
            models.Index(
                fields=["content_type", "object_id"], name="xsm_log_object"
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - admin display
        return f"#{self.seq} {self.event}"


class OutboxMessage(models.Model):
    """A transactional-outbox row (`DjangoOutboxStore`, #281 / D5 parity)."""

    seq = models.BigAutoField(primary_key=True)
    message_id = models.CharField(max_length=64)
    topic = models.CharField(max_length=255)
    subject = models.CharField(max_length=200, null=True, blank=True)
    envelope = models.TextField()
    created_at = models.FloatField()
    sent_at = models.FloatField(null=True, blank=True)

    class Meta:
        app_label = "xsm_django"
        indexes = [
            models.Index(fields=["sent_at", "seq"], name="xsm_outbox_pending")
        ]
