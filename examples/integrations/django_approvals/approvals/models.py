# examples/integrations/django_approvals/approvals/models.py
"""The expense-approval model: parallel legal ∥ finance review, two
reviewer roles, audit in the same transaction, a 48 h escalation."""

from __future__ import annotations

from django.db import models

from xstate_statemachine import MachineLogic
from xstate_statemachine.contrib.django import (
    AnyOf,
    DjangoOutboxStore,
    RoleGuard,
    StatechartField,
    StatechartModelMixin,
)
from xstate_statemachine.eda import OutboxPlugin

#: The two reviewer roles (Django groups).
LEGAL, FINANCE = "legal", "finance"


def escalate(i: object, ctx: dict, e: object, a: object) -> None:
    """Runs when the 48 h `after` matures (fired by `xsm_deadlines`)."""
    ctx["escalated"] = True


def approval_logic() -> MachineLogic:
    return MachineLogic(
        actions={"escalate": escalate},
        guards={
            "isLegal": RoleGuard(LEGAL),
            "isFinance": RoleGuard(FINANCE),
            "isReviewer": AnyOf(RoleGuard(LEGAL), RoleGuard(FINANCE)),
        },
    )


class Expense(StatechartModelMixin, models.Model):
    statechart_machine = "machine.json"  # the example's chart
    statechart_logic = "approvals.models:approval_logic"

    # 📤 #281: `approved` is tagged `publish` -- the integration event is
    #    written to the outbox IN the send's transaction; `manage.py
    #    xsm_relay`-style draining is the relay's job (see README).
    statechart_plugins = staticmethod(
        lambda row: [
            OutboxPlugin(
                DjangoOutboxStore(using=row._state.db or "default"),
                topic="approvals",
            )
        ]
    )

    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    statechart = StatechartField()

    def __str__(self) -> str:
        return f"{self.title} ({self.amount})"
