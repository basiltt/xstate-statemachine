# src/xstate_statemachine/contrib/django/models.py
# -----------------------------------------------------------------------------
# 🗃️ The app's own tables (label ``xsm_django``)
# -----------------------------------------------------------------------------
#    xsm_django_snapshot   `DjangoStore` key-value records
#    xsm_django_deadline   durable `after` deadlines, indexed by due time --
#                          what `DueTimerScanner` / ``xsm_deadlines`` read
#    xsm_django_lock       `DjangoStore.lock()` leases (portable: SQLite has
#                          no row locks)
#
# 📝 ``source`` names the owner of a key: a model's ``db_table`` for
#    `StatechartModelMixin` rows, the store's namespace for `DjangoStore`.
# -----------------------------------------------------------------------------
"""Models of the ``xsm_django`` app."""

from __future__ import annotations

from django.db import models

__all__ = ["StatechartDeadline", "StatechartLock", "StatechartSnapshot"]


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
