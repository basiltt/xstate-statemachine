"""#281 battle (adversary B): the outbox the README documents, relayed by
``manage.py relay_outbox``; the read-only audit changelist."""

import io
import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from approvals.models import FINANCE, LEGAL, Expense
from xstate_statemachine.contrib.django import DjangoOutboxStore


def _approved(db):
    U = get_user_model()
    lena = U.objects.create_user("lena")
    lena.groups.add(Group.objects.get_or_create(name=LEGAL)[0])
    fin = U.objects.create_user("fin")
    fin.groups.add(Group.objects.get_or_create(name=FINANCE)[0])
    e = Expense.objects.create(title="Laptop", amount="10.00")
    e.send("SUBMIT")
    e.send("LEGAL_APPROVE", actor=lena)
    e.send("FINANCE_APPROVE", actor=fin)
    assert e.state == "approval.approved"
    return e


@pytest.mark.django_db
def test_relay_outbox_publishes_once_then_nothing(db):
    e = _approved(db)
    assert DjangoOutboxStore().count(pending_only=True) == 1
    out, err = io.StringIO(), io.StringIO()
    call_command("relay_outbox", stdout=out, stderr=err)
    lines = [json.loads(x) for x in out.getvalue().splitlines() if x]
    assert len(lines) == 1 and "relayed 1" in err.getvalue()
    assert lines[0]["topic"] == "approvals"
    assert lines[0]["subject"] and lines[0]["id"]
    assert str(e.pk) in json.dumps(lines[0])
    out2 = io.StringIO()
    call_command("relay_outbox", stdout=out2, stderr=io.StringIO())
    assert out2.getvalue() == ""
    assert DjangoOutboxStore().count(pending_only=True) == 0


@pytest.mark.django_db
def test_audit_changelist_is_read_only(db):
    _approved(db)
    U = get_user_model()
    U.objects.create_superuser("root", "r@x", "p")
    c = Client()
    c.login(username="root", password="p")
    page = c.get("/admin/xsm_django/transitionlog/?disposition__exact=denied")
    assert page.status_code == 200
    assert c.get("/admin/xsm_django/transitionlog/add/").status_code == 403
