# tests/contrib/django/test_migrate_fsm.py
"""#310: ``xsm_migrate_fsm`` against a real django-fsm-2 model."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError

pytest.importorskip("django_fsm")

pytestmark = pytest.mark.django_db


def _ticket() -> Any:
    from legacy.models import Ticket

    return Ticket


def _out(*args: Any) -> str:
    buf = io.StringIO()
    call_command(*args, stdout=buf)
    return buf.getvalue()


class TestExtraction:
    def test_dry_run_emits_strict_json_with_the_transition_names(self) -> None:
        from xstate_statemachine import create_machine
        from xstate_statemachine.testing_utils import stub_logic

        text = _out("xsm_migrate_fsm", "legacy.Ticket", "--dry-run")
        chart = json.loads(text[: text.index("\nMigrating ")])
        m = create_machine(chart, logic=stub_logic(chart), strict_config=True)
        assert sorted(m.known_events) == [
            "CLOSE",
            "REOPEN",
            "RESET",
            "RESOLVE",
            "START",
        ]
        assert chart["initial"] == "new"
        assert list(chart["states"]) == [
            "new",
            "in_progress",
            "resolved",
            "closed",
        ]
        # guard names preserved: the condition and the permission
        assert chart["states"]["new"]["on"]["START"]["guard"] == "hasAssignee"
        close = chart["states"]["resolved"]["on"]["CLOSE"]
        assert close["guard"] == "closeTicket"
        assert close["meta"] == {"method": "close"}
        # source="*" fans out over every state
        assert all("RESET" in s["on"] for s in chart["states"].values())
        assert "Dual-read" in text
        # the committed chart is exactly what the command extracts today
        committed = json.loads(
            (
                __import__("pathlib").Path(__file__).parent
                / "project/legacy/machines/ticket.json"
            ).read_text("utf-8")
        )
        assert committed == chart

    def test_write_chart_and_errors(self, tmp_path: Any) -> None:
        out = tmp_path / "t.json"
        _out(
            "xsm_migrate_fsm",
            "legacy.Ticket",
            "--write-chart",
            str(out),
            "--dry-run",
        )
        assert json.loads(out.read_text("utf-8"))["id"] == "ticket"
        with pytest.raises(CommandError):
            call_command("xsm_migrate_fsm", "nope.Nope", "--dry-run")
        with pytest.raises(CommandError):
            call_command(
                "xsm_migrate_fsm", "shop.Order", "--dry-run"
            )  # no FSMField

    def test_guard_and_state_names(self) -> None:
        from xstate_statemachine.contrib.django.fsm import (
            guard_name,
            state_key,
        )

        assert guard_name("legacy.close_ticket") == "closeTicket"
        assert guard_name(lambda i: True) == "lambda"
        assert guard_name("___") == "condition"
        assert state_key("in-review") == "in_review"
        assert state_key(3) == "s_3"

    def test_combined_guards_are_an_and(self) -> None:
        from django.apps import apps
        from django.db import models
        from django_fsm import FSMField, transition

        from xstate_statemachine.contrib.django.fsm import extract_chart

        def ok(i: Any) -> bool:
            return True

        class Two(models.Model):
            state = FSMField(default="a")

            class Meta:
                app_label = "legacy"
                managed = False

            @transition(
                field=state,
                source="a",
                target="b",
                conditions=[ok],
                permission="x.y",
            )
            def go(self) -> None:
                pass

            @transition(field=state, source="+", target="a")
            def back(self) -> None:
                pass

            @transition(field=state, source="a", target=None)
            def check(self) -> None:
                pass

        try:
            chart = extract_chart(Two, "state")
        finally:
            # 📝 A model declared in a test registers itself; drop it so a
            #    later `makemigrations --check` does not see it.
            del apps.all_models["legacy"]["two"]
            apps.clear_cache()
        assert chart["states"]["a"]["on"]["GO"]["guard"] == {
            "type": "and",
            "children": ["ok", "y"],
        }
        # "+" = every state except the target
        assert "BACK" in chart["states"]["b"]["on"]
        assert "BACK" not in chart["states"]["a"].get("on", {})
        # target=None (a validating no-op) is not a transition
        assert "CHECK" not in chart["states"]["a"]["on"]


class TestDataMigration:
    def _seed(self, n: int) -> None:
        Ticket = _ticket()
        states = ["new", "in_progress", "resolved", "closed"]
        Ticket.objects.bulk_create(
            [Ticket(state=states[i % 4], assignee="x") for i in range(n)]
        )

    def test_2000_rows_in_batches_interrupted_and_resumed(self) -> None:
        from xstate_statemachine.contrib.django.fsm import migrate_rows

        Ticket = _ticket()
        self._seed(2000)
        assert Ticket.objects.filter(statechart__isnull=True).count() == 2000
        done, batches = migrate_rows(
            Ticket, "state", batch=300, stop_after_batches=2
        )
        assert (done, batches) == (600, 2)  # "interrupted" at batch 2
        out = _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "300")
        assert "migrated 1400 row(s) in 5 batch(es); 0 remaining" in out
        out = _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "300")
        assert "migrated 0 row(s) in 0 batch(es); 0 remaining" in out
        # every row's statechart_state equals its old FSM state
        mismatched = [
            (t.state, t.statechart_state)
            for t in Ticket.objects.all()
            if t.statechart_state != f"ticket.{t.state}"
        ]
        assert mismatched == []
        assert set(
            Ticket.objects.values_list("statechart_version", flat=True)
        ) == {0}

    def test_migrated_rows_drive_and_dual_write(self) -> None:
        Ticket = _ticket()
        U = get_user_model()
        closer = U.objects.create_user("closer")
        closer.user_permissions.add(
            Permission.objects.get(codename="close_ticket")
        )
        closer = U.objects.get(pk=closer.pk)
        t = Ticket.objects.create(state="new")
        empty = Ticket.objects.create(state="new")
        _out("xsm_migrate_fsm", "legacy.Ticket")
        t.refresh_from_db()
        assert t.send("START").denied  # hasAssignee: no assignee yet
        Ticket.objects.filter(pk=t.pk).update(assignee="me")
        t.refresh_from_db()
        assert t.send("START").changed
        assert Ticket.objects.get(pk=t.pk).state == "in_progress"  # dual write
        assert t.send("CLOSE").denied  # permission guard, no actor
        assert t.send("CLOSE", actor=closer).changed
        fresh = Ticket.objects.get(pk=t.pk)
        assert (
            fresh.state == "closed"
            and fresh.statechart_state == "ticket.closed"
        )
        assert empty.pk  # untouched rows stay migratable

    def test_command_refuses_a_model_without_the_field(self) -> None:
        with pytest.raises(CommandError):
            call_command("xsm_migrate_fsm", "auth.User")

    def test_migrate_rows_validation(self) -> None:
        from xstate_statemachine.contrib.django.fsm import migrate_rows

        with pytest.raises(ValueError):
            migrate_rows(_ticket(), batch=0)
