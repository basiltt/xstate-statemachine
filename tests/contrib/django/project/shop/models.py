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
