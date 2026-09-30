# tests/contrib/django/project/shop/models.py
"""Models of the test project's ``shop`` app."""

from __future__ import annotations

from django.db import models

from xstate_statemachine.contrib.django.fields import StatechartField
from xstate_statemachine.contrib.django.mixin import StatechartModelMixin


class Order(StatechartModelMixin, models.Model):
    """The reference model: parallel review, `after`, guard, actions."""

    statechart_machine = "machines/order.json"
    statechart_logic = "shop.logic"

    title = models.CharField(max_length=100, blank=True, default="")
    statechart = StatechartField()

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.pk}"


class Counter(StatechartModelMixin, models.Model):
    """A one-state self-loop for the concurrency tests."""

    statechart_machine = {
        "id": "counter",
        "initial": "on",
        "context": {"n": 0},
        "states": {"on": {"on": {"BUMP": {"actions": "bump"}}}},
    }
    statechart_logic = "shop.models:counter_logic"

    statechart = StatechartField()


def counter_logic() -> object:
    from xstate_statemachine import MachineLogic

    def bump(i: object, ctx: dict, e: object, a: object) -> None:
        ctx["n"] = ctx["n"] + 1

    return MachineLogic(actions={"bump": bump})


def approval_logic() -> object:
    """#281: two roles -- ``shop.approve_approval`` (approvers) and the
    ``managers`` group (may reopen)."""
    from xstate_statemachine import MachineLogic
    from xstate_statemachine.contrib.django.permissions import (
        PermissionGuard,
        RoleGuard,
    )

    def note(i: object, ctx: dict, e: object, a: object) -> None:
        ctx.setdefault("notes", []).append(e.payload.get("text", ""))

    def explode(i: object, ctx: dict, e: object, a: object) -> None:
        raise RuntimeError("action failed")

    return MachineLogic(
        actions={"note": note, "explode": explode},
        guards={
            "canApprove": PermissionGuard("shop.approve_approval"),
            "isManager": RoleGuard("managers"),
        },
    )


class Approval(StatechartModelMixin, models.Model):
    """#281/#282: permission-guarded approval with an audit trail."""

    statechart_machine = "machines/approval.json"
    statechart_logic = "shop.models:approval_logic"

    title = models.CharField(max_length=100, blank=True, default="")
    statechart = StatechartField()

    class Meta:
        permissions = [("approve_approval", "Can approve approvals")]

    def __str__(self) -> str:  # pragma: no cover
        return f"Approval #{self.pk}"
