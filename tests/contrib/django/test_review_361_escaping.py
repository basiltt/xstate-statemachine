# tests/contrib/django/test_review_361_escaping.py
"""#361 re-verification: chart-controlled text (meta.title, state titles)
is HTML-escaped on every admin page; an existing model can gain the
field through a normal migration."""

from __future__ import annotations

import re
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db

EVIL = '<script>alert("x")</script>'


def test_chart_text_is_escaped_in_the_admin(monkeypatch: Any) -> None:
    from shop.models import Approval

    from xstate_statemachine.contrib.django import admin as xadmin

    monkeypatch.setattr(xadmin, "event_label", lambda m, e: EVIL)
    monkeypatch.setattr(xadmin, "_state_label", lambda m, s: EVIL)
    a = Approval.objects.create()
    su = get_user_model().objects.create_superuser("su", "s@x.y", "p")
    c = Client()
    c.force_login(su)
    pages = [
        f"/admin/shop/approval/{a.pk}/change/",
        "/admin/shop/approval/",
        f"/admin/shop/approval/{a.pk}/statechart/",
    ]
    for url in pages:
        html = c.get(url).content.decode()
        assert EVIL not in html, url
    html = c.get(
        f"/admin/shop/approval/{a.pk}/xsm-transition/",
        {"_xsm_event": "APPROVE"},
    ).content.decode()
    assert EVIL not in html and "&lt;script&gt;" in html


def test_templates_never_disable_escaping() -> None:
    from pathlib import Path

    import xstate_statemachine.contrib.django as dj

    root = Path(dj.__file__).parent / "templates"
    for tpl in root.rglob("*.html"):
        text = tpl.read_text("utf-8")
        assert not re.search(r"\|\s*safe|autoescape\s+off", text), tpl


def test_existing_model_gains_the_field_by_migration(tmp_path: Any) -> None:
    """An app whose model predates the field: makemigrations proposes the
    field + its four siblings, and a second pass is clean."""
    from django.apps import apps
    from django.db import models
    from django.db.migrations.autodetector import MigrationAutodetector
    from django.db.migrations.graph import MigrationGraph
    from django.db.migrations.state import ModelState, ProjectState

    from xstate_statemachine.contrib.django.fields import StatechartField

    before = ProjectState()
    before.add_model(
        ModelState(
            "legacyapp",
            "Thing",
            [("id", models.AutoField(primary_key=True))],
        )
    )
    after = ProjectState()
    after.add_model(
        ModelState(
            "legacyapp",
            "Thing",
            [
                ("id", models.AutoField(primary_key=True)),
                ("statechart", StatechartField()),
                *StatechartField().sibling_fields_named("statechart"),
            ],
        )
    )
    changes = MigrationAutodetector(before, after)._detect_changes(
        convert_apps={"legacyapp"}, graph=MigrationGraph()
    )
    added = sorted(op.name for op in changes["legacyapp"][0].operations)
    assert added == [
        "statechart",
        "statechart_machine_version",
        "statechart_state",
        "statechart_state_ids",
        "statechart_version",
    ]
    assert (
        MigrationAutodetector(after, after).changes(
            graph=MigrationGraph(), convert_apps={"legacyapp"}
        )
        == {}
    )
    assert apps.ready
