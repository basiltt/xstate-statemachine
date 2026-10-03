# tests/contrib/django/test_battle_263_snapshots_cmd.py
"""#263 battle: `manage.py xsm_snapshots --stale` parity with `xsm
snapshots` -- stale filter before `--limit`; unlabelled rows not stale."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def _stale(*extra: str) -> Any:
    out = io.StringIO()
    call_command(
        "xsm_snapshots", "shop.Order", "--stale", "--json", *extra, stdout=out
    )
    return json.loads(out.getvalue())


def test_stale_filter_runs_before_limit() -> None:
    from shop.models import Order

    # Arrange: 5 current rows, then 1 stale row beyond `--limit 3`
    rows = [Order.objects.create(title=f"t{i}") for i in range(6)]
    Order.objects.filter(pk=rows[-1].pk).update(statechart_machine_version="0")

    # Act
    got = _stale("--limit", "3")

    # Assert: 🔥 it used to slice first and report 0 stale
    assert [r["key"] for r in got["snapshots"]] == [str(rows[-1].pk)]


def test_unlabelled_rows_are_not_stale() -> None:
    from shop.models import Order

    o = Order.objects.create(title="t")
    Order.objects.filter(pk=o.pk).update(statechart_machine_version=None)

    assert _stale()["count"] == 0
