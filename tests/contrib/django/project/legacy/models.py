# tests/contrib/django/project/legacy/models.py
"""#310: a real django-fsm-2 model to migrate -- 4 states, 5 transitions,
1 permission, 1 condition. `Ticket.statechart` is step 2 of the recipe
(a `StatechartField` added BESIDE the FSMField)."""

from __future__ import annotations

from django.db import models
from django_fsm import FSMField, transition

from xstate_statemachine.contrib.django.fields import StatechartField
from xstate_statemachine.contrib.django.fsm import FSMDualWriteMixin
from xstate_statemachine.contrib.django.mixin import StatechartModelMixin


def has_assignee(instance: "Ticket") -> bool:
    return bool(instance.assignee)


class Ticket(FSMDualWriteMixin, StatechartModelMixin, models.Model):
    STATES = [
        ("new", "New"),
        ("in_progress", "In progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    state = FSMField(default="new", choices=STATES, protected=False)
    assignee = models.CharField(max_length=50, blank=True, default="")
    statechart = StatechartField()

    # Written by `xsm_migrate_fsm --write-chart`; the guards the chart
    # names (hasAssignee, closeTicket) are implemented below.
    statechart_machine = "machines/ticket.json"
    statechart_logic = "legacy.models:ticket_logic"
    # 📝 Rows get their snapshot from the data migration, not on insert.
    statechart_initialize = False
    fsm_dual_write_field = "state"

    class Meta:
        permissions = [("close_ticket", "Can close tickets")]

    @transition(
        field=state,
        source="new",
        target="in_progress",
        conditions=[has_assignee],
    )
    def start(self) -> None:
        pass

    @transition(field=state, source="in_progress", target="resolved")
    def resolve(self) -> None:
        pass

    @transition(field=state, source="resolved", target="in_progress")
    def reopen(self) -> None:
        pass

    @transition(
        field=state,
        source=["resolved", "in_progress"],
        target="closed",
        permission="legacy.close_ticket",
    )
    def close(self) -> None:
        pass

    @transition(field=state, source="*", target="new")
    def reset(self) -> None:
        pass


def ticket_logic() -> object:
    from xstate_statemachine import MachineLogic
    from xstate_statemachine.contrib.django.mixin import current_instance
    from xstate_statemachine.contrib.django.permissions import (
        PermissionGuard,
    )

    def has_assignee_guard(ctx: object, e: object) -> bool:
        row = current_instance.get()
        return bool(row is not None and row.assignee)

    return MachineLogic(
        guards={
            "hasAssignee": has_assignee_guard,
            "closeTicket": PermissionGuard("legacy.close_ticket"),
        }
    )


# -----------------------------------------------------------------------------
# #310 battle (adversary A): the awkward shapes a real legacy app has
# -----------------------------------------------------------------------------
GADGET_STATES = [
    ("in-progress", "In progress"),
    ("état", "Étatique"),
    ("1", "One"),
    ("parked", "Parked"),
]


class Gadget(FSMDualWriteMixin, StatechartModelMixin, models.Model):
    """UUID pk, ``protected=True``, NULLable column, state values that are
    not XState-safe keys, a statechart field NOT named ``statechart``."""

    import uuid as _uuid

    id = models.UUIDField(primary_key=True, default=_uuid.uuid4)
    status = FSMField(
        default="in-progress",
        choices=GADGET_STATES,
        protected=True,
        null=True,
    )
    chart = StatechartField()

    statechart_machine = "machines/gadget.json"
    statechart_initialize = False
    fsm_dual_write_field = "status"

    @transition(field=status, source="in-progress", target="état")
    def advance(self) -> None:
        pass

    @transition(field=status, source="état", target="1")
    def finish(self) -> None:
        pass

    @transition(field=status, source="*", target="in-progress")
    def restart(self) -> None:
        pass


class Counter(FSMDualWriteMixin, StatechartModelMixin, models.Model):
    """An ``FSMIntegerField``: the values are ints, the keys ``s_<n>``."""

    from django_fsm import FSMIntegerField as _F

    level = _F(default=1, choices=[(1, "one"), (2, "two"), (3, "three")])
    statechart = StatechartField()

    statechart_machine = "machines/counter.json"
    statechart_initialize = False
    fsm_dual_write_field = "level"

    @transition(field=level, source=1, target=2)
    def up(self) -> None:
        pass

    @transition(field=level, source=2, target=3)
    def top(self) -> None:
        pass
