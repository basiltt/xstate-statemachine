"""The django_approvals example, end to end: parallel review with two roles,
admin buttons, the audit trail, DRF + schema, Channels, the 48 h escalation."""

import asyncio
import re
import time

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import Client
from rest_framework.test import APIClient

from approvals.models import FINANCE, LEGAL, Expense
from approvals.ws import websocket_urlpatterns


def _user(name, group=None, staff=True):
    U = get_user_model()
    u = U.objects.create_user(name, password="p", is_staff=staff)
    for codename in ("view_expense", "change_expense"):
        u.user_permissions.add(Permission.objects.get(codename=codename))
    if group:
        u.groups.add(Group.objects.get_or_create(name=group)[0])
    return U.objects.get(pk=u.pk)


@pytest.fixture
def people(db):
    return {"legal": _user("lena", LEGAL), "finance": _user("fin", FINANCE)}


@pytest.fixture
def expense(db):
    e = Expense.objects.create(title="Laptop", amount="1999.00")
    e.send("SUBMIT")
    return e


@pytest.mark.django_db
def test_both_roles_approve_in_parallel(expense, people):
    assert expense.matches("approval.review")
    assert expense.send("FINANCE_APPROVE", actor=people["legal"]).denied
    assert expense.send("LEGAL_APPROVE", actor=people["legal"]).changed
    assert expense.state == (
        "approval.review.finance.pending,approval.review.legal.approved"
    )
    assert expense.send("FINANCE_APPROVE", actor=people["finance"]).changed
    assert expense.state == "approval.approved"
    events = [(h.event, h.actor_id) for h in expense.history.all()]
    assert events[:3] == [
        ("SUBMIT", None),
        ("FINANCE_APPROVE", people["legal"].pk),  # the refused attempt
        ("LEGAL_APPROVE", people["legal"].pk),
    ]


@pytest.mark.django_db
def test_admin_buttons_follow_the_role(expense, people):
    url = f"/admin/approvals/expense/{expense.pk}/change/"
    c = Client()
    c.force_login(people["legal"])
    html = c.get(url).content.decode()
    buttons = re.findall(r'name="_xsm_submit" value="([A-Z_]+)"', html)
    assert buttons == ["LEGAL_APPROVE", "REJECT"]
    t = f"/admin/approvals/expense/{expense.pk}/xsm-transition/"
    r = c.post(t, {"_xsm_event": "REJECT"})  # meta.confirm → a form
    assert r.status_code == 200 and b"Reason" in r.content
    c.post(t, {"_xsm_event": "REJECT", "_xsm_confirmed": "1", "reason": "dup"})
    expense.refresh_from_db()
    assert expense.state == "approval.rejected"
    assert expense.history.last().reason == "dup"


@pytest.mark.django_db
def test_drf_actions_and_schema(expense, people):
    c = APIClient()
    c.force_authenticate(people["finance"])
    r = c.post(f"/api/expenses/{expense.pk}/legal-approve/", {}, format="json")
    assert r.status_code == 403  # not in the legal group
    r = c.post(
        f"/api/expenses/{expense.pk}/finance-approve/", {}, format="json"
    )
    assert r.status_code == 200 and r.json()["changed"] is True
    body = c.get(f"/api/expenses/{expense.pk}/").json()["statechart"]
    assert body["available_events"] == ["REJECT"]
    schema = c.get("/api/schema/", HTTP_ACCEPT="application/json").json()
    assert "/api/expenses/{id}/legal-approve/" in schema["paths"]


@pytest.mark.django_db
def test_escalation_after_48h_via_the_deadlines_table(expense):
    out = __import__("io").StringIO()
    call_command("xsm_deadlines", "approvals.Expense", stdout=out)
    assert "woke 0/0" in out.getvalue()
    later = time.time() + 49 * 3600
    call_command("xsm_deadlines", "approvals.Expense", now=later, stdout=out)
    assert "woke 1/1" in out.getvalue()
    expense.refresh_from_db()
    assert expense.machine.context["escalated"] is True
    assert expense.matches("approval.review")  # still waiting on people


@pytest.mark.django_db(transaction=True)
def test_channels_status_stream(people):
    e = Expense.objects.create(title="Chair", amount="80.00")
    e.send("SUBMIT")

    async def go():
        comm = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f"/ws/expenses/{e.pk}/"
        )
        comm.scope["user"] = people["legal"]
        ok, _ = await comm.connect()
        assert ok
        assert (await comm.receive_json_from())["kind"] == "snapshot"
        await comm.send_json_to({"type": "LEGAL_APPROVE"})
        assert (await comm.receive_json_from())["changed"] is True
        pushed = await comm.receive_json_from()
        assert pushed["kind"] == "transition"
        assert pushed["state"]["review"]["legal"] == "approved"
        await comm.disconnect()

    asyncio.run(go())


@pytest.mark.django_db
def test_status_page_requires_login(expense, people):
    c = Client()
    assert c.get(f"/expenses/{expense.pk}/").status_code == 302
    c.force_login(people["legal"])
    assert b"/ws/expenses/" in c.get(f"/expenses/{expense.pk}/").content
