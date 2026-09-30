# tests/contrib/django/test_review_361.py
"""#361: M1 (partial saves of the statechart columns are refused), L2
(send_with_retry warns inside atomic()), L3 (class-level resolver)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import transaction

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "fields",
    [
        ["statechart"],
        ["statechart_state"],
        ["title", "statechart_version"],
    ],
)
def test_update_fields_naming_statechart_columns_is_refused(
    order: Any, fields: Any
) -> None:
    from shop.models import Order

    order.statechart = {**order.statechart, "state_ids": ["order.paid"]}
    with pytest.raises(ValueError, match="send"):
        order.save(update_fields=fields)
    fresh = Order.objects.get(pk=order.pk)
    assert fresh.state == "order.draft"
    assert Order.objects.in_state("order.paid").count() == 0


def test_update_fields_for_other_columns_still_works(order: Any) -> None:
    order.title = "x"
    order.save(update_fields=["title"])
    order.refresh_from_db()
    assert order.title == "x"


def test_send_with_retry_warns_inside_atomic(order: Any) -> None:
    from xstate_statemachine.contrib.django import send_with_retry

    with transaction.atomic():
        with pytest.warns(RuntimeWarning, match="outside atomic"):
            send_with_retry(order, "INC")


def test_class_level_machine_resolution() -> None:
    from shop.models import Order

    assert Order.statechart_class_machine().id == "order"
