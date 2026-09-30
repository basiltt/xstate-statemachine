# tests/contrib/django/test_admin_commands.py
"""#282: admin transition buttons (CSRF POST forms) and management commands."""

from __future__ import annotations

import argparse
import io
import re
from contextlib import redirect_stdout
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

SHOP = __import__("pathlib").Path(__file__).parent / "project" / "shop"


def _staff(username: str, *perms: str, groups: Any = ()) -> Any:
    U = get_user_model()
    u = U.objects.create_user(username, password="p", is_staff=True)
    for codename in perms:
        u.user_permissions.add(Permission.objects.get(codename=codename))
    for g in groups:
        u.groups.add(Group.objects.get_or_create(name=g)[0])
    return U.objects.get(pk=u.pk)


@pytest.fixture
def approval(db: Any) -> Any:
    from shop.models import Approval

    return Approval.objects.create(title="a")


@pytest.fixture
def approver(db: Any) -> Any:
    return _staff(
        "approver",
        "view_approval",
        "change_approval",
        "approve_approval",
    )


@pytest.fixture
def clerk(db: Any) -> Any:
    return _staff("clerk", "view_approval", "change_approval")


def _client(user: Any, csrf: bool = False) -> Client:
    c = Client(enforce_csrf_checks=csrf)
    c.force_login(user)
    return c


def _urls(obj: Any) -> Any:
    return (
        reverse("admin:shop_approval_change", args=[obj.pk]),
        reverse("admin:shop_approval_xsm_transition", args=[obj.pk]),
        reverse("admin:shop_approval_xsm_diagram", args=[obj.pk]),
    )


def _buttons(html: str) -> list:
    return re.findall(r'name="_xsm_submit" value="([A-Z_]+)"', html)


class TestButtons:
    def test_only_permitted_events_are_buttons(
        self, approval: Any, approver: Any, clerk: Any
    ) -> None:
        change, url, _ = _urls(approval)
        html = _client(approver).get(change).content.decode()
        assert _buttons(html) == ["APPROVE", "BOOM", "COMMENT", "REJECT"]
        assert 'method="post"' in html and "csrfmiddlewaretoken" in html
        assert ">Approve&hellip;<" in html  # meta.title + confirm marker
        html = _client(clerk).get(change).content.decode()
        assert _buttons(html) == ["BOOM", "COMMENT"]

    def test_post_transitions_and_audits_actor(
        self, approval: Any, approver: Any
    ) -> None:
        _, url, _ = _urls(approval)
        r = _client(approver).post(url, {"_xsm_event": "REJECT"})
        assert r.status_code == 302
        approval.refresh_from_db()
        assert approval.state == "approval.rejected"
        row = approval.history.get()
        assert row.actor == approver and row.event == "REJECT"

    def test_confirm_page_then_reason_is_stored(
        self, approval: Any, approver: Any
    ) -> None:
        _, url, _ = _urls(approval)
        c = _client(approver)
        r = c.post(url, {"_xsm_event": "APPROVE"})  # meta.confirm
        assert r.status_code == 200 and b'name="reason"' in r.content
        approval.refresh_from_db()
        assert approval.state == "approval.pending"  # not yet
        r = c.post(
            url,
            {"_xsm_event": "APPROVE", "_xsm_confirmed": "1", "reason": "LGTM"},
        )
        assert r.status_code == 302
        approval.refresh_from_db()
        assert approval.state == "approval.approved"
        assert approval.history.get().reason == "LGTM"

    def test_get_does_not_transition(
        self, approval: Any, approver: Any
    ) -> None:
        _, url, _ = _urls(approval)
        r = _client(approver).get(url, {"_xsm_event": "REJECT"})
        assert r.status_code == 200  # a form, nothing done
        approval.refresh_from_db()
        assert approval.state == "approval.pending"
        assert approval.history.count() == 0

    def test_post_without_csrf_token_is_403(
        self, approval: Any, approver: Any
    ) -> None:
        _, url, _ = _urls(approval)
        r = _client(approver, csrf=True).post(url, {"_xsm_event": "REJECT"})
        assert r.status_code == 403
        approval.refresh_from_db()
        assert approval.state == "approval.pending"

    def test_permission_rechecked_on_post(
        self, approval: Any, clerk: Any
    ) -> None:
        _, url, _ = _urls(approval)
        r = _client(clerk).post(
            url, {"_xsm_event": "REJECT", "_xsm_confirmed": "1"}, follow=True
        )
        approval.refresh_from_db()
        assert approval.state == "approval.pending"
        assert b"may not perform" in r.content
        # a forged / unknown event is refused outright
        r = _client(clerk).post(url, {"_xsm_event": "NOPE"})
        assert r.status_code == 403

    def test_view_only_user_gets_no_buttons(self, approval: Any) -> None:
        viewer = _staff("viewer", "view_approval", "approve_approval")
        change, url, diagram = _urls(approval)
        html = _client(viewer).get(change).content.decode()
        assert _buttons(html) == []
        _client(viewer).post(url, {"_xsm_event": "REJECT"}, follow=True)
        approval.refresh_from_db()
        assert approval.state == "approval.pending"

    def test_denied_by_guard_after_render_warns(
        self, approval: Any, approver: Any
    ) -> None:
        _, url, _ = _urls(approval)
        approval.send("REJECT", actor=approver)  # someone else got there
        r = _client(approver).post(url, {"_xsm_event": "COMMENT"}, follow=True)
        assert b"may not perform" in r.content


class TestDiagramListBulk:
    def test_diagram_requires_view_and_highlights(
        self, approval: Any, approver: Any
    ) -> None:
        _, _, diagram = _urls(approval)
        r = _client(approver).get(diagram)
        assert r.status_code == 200
        body = r.content.decode()
        assert "stateDiagram" in body and "class pending xsmActive" in body
        nobody = _staff("nobody")
        assert _client(nobody).get(diagram).status_code == 403

    def test_changelist_state_column_filter_and_bulk(
        self, approver: Any
    ) -> None:
        from shop.models import Approval

        a, b, c = (Approval.objects.create() for _ in range(3))
        a.send("REJECT", actor=approver)
        cl = reverse("admin:shop_approval_changelist")
        client = _client(approver)
        html = client.get(cl).content.decode()
        assert "xsm-state" in html
        filtered = client.get(cl, {"xsm_state": "approval.rejected"})
        ids = re.findall(
            r'name="_selected_action" value="(\d+)"', filtered.content.decode()
        )
        assert ids == [str(a.pk)]
        r = client.post(
            cl,
            {
                "action": "xsm_REJECT",
                "_selected_action": [a.pk, b.pk, c.pk],
            },
            follow=True,
        )
        assert b"2 changed / 1 denied" in r.content
        assert Approval.objects.in_state("approval.rejected").count() == 3


# -----------------------------------------------------------------------------
# ⌨️ management commands
# -----------------------------------------------------------------------------
def _direct(fn: Any, *a: Any, **kw: Any) -> str:
    """What the standalone `xsm` prints for the same call, --plain."""
    from xstate_statemachine.cli.commands import (
        configure_console,
        reset_console,
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        reset_console()
        configure_console(
            argparse.Namespace(plain=True, no_color=False, no_anim=True)
        )
        try:
            fn(*a, **kw)
        except SystemExit:
            pass
    reset_console()
    return buf.getvalue()


def _cmd(*args: Any) -> str:
    out = io.StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


ORDER_JSON = str(SHOP / "machines" / "order.json")


class TestCommands:
    def test_inspect_matches_cli_byte_for_byte(self) -> None:
        from xstate_statemachine.cli.commands.inspect import run_inspect

        got = _cmd("xsm_inspect", "shop.Order", "--plain")
        assert got == _direct(run_inspect, ORDER_JSON)
        assert "review" in got and "legal" in got
        got = _cmd("xsm_inspect", "shop.Order", "--json", "--plain")
        assert got == _direct(run_inspect, ORDER_JSON, as_json=True)

    def test_diagram_docs_simulate_match_cli(self) -> None:
        from xstate_statemachine.cli.commands.diagram import run_diagram
        from xstate_statemachine.cli.commands.docs import run_docs
        from xstate_statemachine.cli.commands.simulate import run_simulate

        for fmt in ("mermaid", "plantuml", "ascii"):
            got = _cmd("xsm_diagram", "shop.Order", "-f", fmt, "--plain")
            assert got == _direct(run_diagram, ORDER_JSON, fmt=fmt)
        assert _cmd("xsm_diagram", "shop.Order", "--plain").startswith(
            "stateDiagram"
        )
        assert _cmd("xsm_docs", "shop.Order", "--plain") == _direct(
            run_docs, [ORDER_JSON]
        )
        got = _cmd(
            "xsm_simulate", "shop.Order", "-e", "SUBMIT,LEGAL_OK", "--json"
        )
        assert got == _direct(
            run_simulate, ORDER_JSON, events="SUBMIT,LEGAL_OK", as_json=True
        )
        assert "legal" in got

    def test_dict_spec_model_uses_temp_json(self) -> None:
        got = _cmd("xsm_inspect", "shop.Counter", "--plain")
        assert "counter" in got and "BUMP" in got

    def test_inspect_with_row_and_snapshots(self, approver: Any) -> None:
        from shop.models import Order

        o = Order.objects.create()
        o.send("SUBMIT")
        got = _cmd("xsm_inspect", "shop.Order", str(o.pk), "--plain")
        assert f"row {o.pk}: order.review" in got and "version 1" in got
        with pytest.raises(CommandError):
            call_command("xsm_inspect", "shop.Order", "999999")
        got = _cmd("xsm_snapshots", "shop.Order")
        assert "snapshots (machine version '1'): 1" in got
        Order.objects.filter(pk=o.pk).update(statechart_machine_version="0")
        got = _cmd("xsm_snapshots", "shop.Order", "--stale", "--json")
        assert '"count": 1' in got and '"machine_version": "0"' in got

    def test_docs_output_dir_and_errors(self, tmp_path: Any) -> None:
        _cmd("xsm_docs", "shop.Order", "-o", str(tmp_path), "--plain")
        assert (tmp_path / "order.md").is_file()
        with pytest.raises(CommandError):
            call_command("xsm_diagram", "nope.Model")
        with pytest.raises(CommandError):
            call_command("xsm_diagram", "auth.User")
