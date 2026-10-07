# tests/contrib/django/test_battle_281_b.py
"""#281 battle (adversary B): permissions, the audit admin, the docs."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.django.permissions import (
    AllOf,
    AnyOf,
    PermissionGuard,
    RoleGuard,
    has_event_permission,
    permitted_events,
)
from xstate_statemachine.contrib.django.signals import (
    TransitionVetoed,
    pre_transition,
)

pytestmark = pytest.mark.django_db


class FakeUser:
    """A user-like actor whose backend answers are scripted."""

    is_active = True
    is_authenticated = True
    is_superuser = False

    def __init__(self, answer: Any = True, pk: Any = None) -> None:
        self.pk = pk
        self.answer = answer
        self.seen: list = []

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        self.seen.append(obj)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer(obj) if callable(self.answer) else self.answer


@pytest.fixture
def users(db: Any) -> Any:
    U = get_user_model()
    approver = U.objects.create_user("approver", password="p")
    approver.user_permissions.add(
        Permission.objects.get(codename="approve_approval")
    )
    manager = U.objects.create_user("manager", password="p")
    manager.groups.add(Group.objects.create(name="managers"))
    return {
        "approver": U.objects.get(pk=approver.pk),
        "manager": manager,
        "intern": U.objects.create_user("intern", password="p"),
        "root": U.objects.create_superuser("root", "r@x", "p"),
    }


def _swap_chart(monkeypatch: Any, config: dict, **guards: Any) -> Any:
    """Point `Approval` at *config* with the shop guards + *guards*."""
    from shop.models import Approval, approval_logic

    base = approval_logic()
    logic = MachineLogic(
        actions=dict(base.actions), guards={**base.guards, **guards}
    )
    machine = create_machine(config, logic=logic)
    monkeypatch.setattr(Approval, "_xsm_machine_cache", machine, raising=False)
    return Approval


# -----------------------------------------------------------------------------
# 🔐 guards
# -----------------------------------------------------------------------------
class TestGuards:
    def test_object_level_backend_sees_the_saved_row(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create(title="x")
        u = FakeUser(lambda obj: obj is not None)
        assert a.send("APPROVE", actor=u).changed
        assert u.seen and u.seen[0] is a and u.seen[0].pk is not None

    def test_raising_backend_is_a_logged_denial(self, caplog: Any) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        u = FakeUser(RuntimeError("ldap down"))
        with caplog.at_level(logging.ERROR):
            assert not has_event_permission(u, a, "APPROVE")
            assert not has_event_permission(
                u, a, "APPROVE", require_enabled=False
            )
            assert a.send("APPROVE", actor=u).denied
        assert "ldap down" in caplog.text
        assert Approval.objects.get(pk=a.pk).state == "approval.pending"

    def test_inactive_anonymous_none_are_denied(self, users: Any) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        a_user = users["approver"]
        a_user.is_active = False
        for who in (a_user, AnonymousUser(), None):
            assert not has_event_permission(who, a, "APPROVE")
            assert who is None or not a.can("APPROVE", actor=who)

    def test_superuser_semantics(self, users: Any) -> None:
        root = users["root"]
        assert PermissionGuard("shop.approve_approval").check(root, None)
        assert RoleGuard("managers").check(root, None)
        assert not RoleGuard("managers", allow_superuser=False).check(
            root, None
        )

    def test_unknown_group_is_false_not_an_error(self, users: Any) -> None:
        assert not RoleGuard("no-such-group").check(users["manager"], None)

    def test_three_deep_composition(self, users: Any) -> None:
        p = PermissionGuard("shop.approve_approval")
        r = RoleGuard("managers", allow_superuser=False)
        ghost = RoleGuard("ghosts", allow_superuser=False)
        g = AnyOf(AllOf(p, AnyOf(r, ghost)), AllOf(r, AnyOf(ghost, p)))
        assert not g.check(users["approver"], None)  # p but no role
        assert not g.check(users["manager"], None)  # role but no p
        m = users["manager"]
        m.user_permissions.add(
            Permission.objects.get(codename="approve_approval")
        )
        m = get_user_model().objects.get(pk=m.pk)
        assert g.check(m, None)


# -----------------------------------------------------------------------------
# 🧮 the matrix
# -----------------------------------------------------------------------------
MATRIX_CHART = {
    "id": "approval",
    "initial": "pending",
    "context": {"items": 0},
    "states": {
        "pending": {
            "on": {
                "SUBMIT": {
                    "target": "submitted",
                    "guard": {
                        "type": "and",
                        "children": ["canApprove", "hasItems"],
                    },
                },
                "APPROVE": {
                    "target": "approved",
                    "guard": {
                        "type": "or",
                        "children": ["canApprove", "isManager"],
                    },
                },
                "REJECT": [
                    {"target": "rejected", "guard": "canApprove"},
                    {"target": "rejected", "guard": "isManager"},
                ],
            }
        },
        "submitted": {},
        "approved": {},
        "rejected": {},
    },
}


class TestMatrix:
    def test_forbidden_vs_not_possible_right_now(
        self, users: Any, monkeypatch: Any
    ) -> None:
        Approval = _swap_chart(
            monkeypatch,
            MATRIX_CHART,
            hasItems=lambda ctx, e: ctx["items"] > 0,
        )
        a = Approval.objects.create()
        ap, it = users["approver"], users["intern"]
        # approver: allowed to try, but no items -> not possible now
        assert has_event_permission(ap, a, "SUBMIT", require_enabled=False)
        assert not has_event_permission(ap, a, "SUBMIT")
        assert not a.can("SUBMIT", actor=ap)
        # intern: forbidden outright
        assert not has_event_permission(it, a, "SUBMIT", require_enabled=False)

    def test_or_and_alternatives_accept_either_role(
        self, users: Any, monkeypatch: Any
    ) -> None:
        # 🔥 battle: every permission guard named anywhere on the event
        #    had to pass, so `or(canApprove, isManager)` demanded BOTH
        #    and the admin hid a button `send()` would honour.
        Approval = _swap_chart(monkeypatch, MATRIX_CHART, hasItems=None)
        a = Approval.objects.create()
        for who in ("approver", "manager"):
            u = users[who]
            for ev in ("APPROVE", "REJECT"):
                assert a.can(ev, actor=u)
                assert has_event_permission(u, a, ev), (who, ev)
        assert not has_event_permission(users["intern"], a, "APPROVE")
        assert not has_event_permission(users["intern"], a, "REJECT")

    def test_parallel_chart_lists_both_regions(
        self, users: Any, monkeypatch: Any
    ) -> None:
        chart = {
            "id": "approval",
            "type": "parallel",
            "states": {
                "money": {
                    "initial": "open",
                    "states": {
                        "open": {
                            "on": {"PAY": {"target": "paid"}},
                        },
                        "paid": {},
                    },
                },
                "review": {
                    "initial": "waiting",
                    "states": {
                        "waiting": {
                            "on": {
                                "SIGN": {
                                    "target": "signed",
                                    "guard": "canApprove",
                                }
                            }
                        },
                        "signed": {},
                    },
                },
            },
        }
        Approval = _swap_chart(monkeypatch, chart)
        a = Approval.objects.create()
        assert permitted_events(users["approver"], a) == ["PAY", "SIGN"]
        assert permitted_events(users["intern"], a) == ["PAY"]

    def test_permitted_events_query_cost_is_bounded(self, users: Any) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        m = users["manager"]
        m.user_permissions.add(
            Permission.objects.get(codename="approve_approval")
        )
        m = get_user_model().objects.get(pk=m.pk)
        permitted_events(m, a)  # warm the per-user permission cache
        with CaptureQueriesContext(connection) as q:
            evs = permitted_events(m, a)
        assert "APPROVE" in evs
        # 📝 has_perm is cached on the user object; only RoleGuard's
        #    group lookup queries, once per event that names it.
        assert len(q) <= 2, [x["sql"] for x in q]


# -----------------------------------------------------------------------------
# 🛠️ the admin
# -----------------------------------------------------------------------------
class TestAdmin:
    def _login(self, client: Any, users: Any) -> Any:
        client.force_login(users["root"])
        return users["root"]

    def test_veto_and_lock_errors_are_messages_not_500(
        self, client: Any, users: Any, monkeypatch: Any
    ) -> None:
        from shop.models import Approval

        from xstate_statemachine.exceptions import LockTimeoutError

        self._login(client, users)
        a = Approval.objects.create()
        url = f"/admin/shop/approval/{a.pk}/xsm-transition/"

        def veto(sender: Any, **kw: Any) -> None:
            raise TransitionVetoed("frozen")

        pre_transition.connect(veto, weak=False)
        try:
            r = client.post(url, {"_xsm_event": "REJECT"}, follow=True)
        finally:
            pre_transition.disconnect(veto)
        assert r.status_code == 200
        assert "refused" in " ".join(str(m) for m in r.context["messages"])

        def locked(self: Any, *a: Any, **kw: Any) -> Any:
            raise LockTimeoutError("row busy", 1.0)

        monkeypatch.setattr(Approval, "send", locked)
        r = client.post(url, {"_xsm_event": "REJECT"}, follow=True)
        assert r.status_code == 200
        text = " ".join(str(m) for m in r.context["messages"])
        assert "failed" in text and "row busy" in text

    def test_transitionlog_admin_is_append_only(
        self, client: Any, users: Any
    ) -> None:
        from shop.models import Approval

        from xstate_statemachine.contrib.django.models import TransitionLog

        root = self._login(client, users)
        a = Approval.objects.create()
        a.send("REJECT", actor=root, payload={"blob": "x" * 10_000})
        row = TransitionLog.objects.get()
        base = "/admin/xsm_django/transitionlog/"
        page = client.get(base)
        assert page.status_code == 200
        assert len(page.content) < 60_000  # payload preview, not 10 KB
        assert b"REJECT" in page.content
        assert client.get(f"{base}?actor__id__exact={root.pk}").status_code
        assert client.get(f"{base}add/").status_code == 403
        assert (
            client.post(f"{base}{row.pk}/delete/", {"post": "yes"}).status_code
            == 403
        )
        detail = client.get(f"{base}{row.pk}/change/")
        assert detail.status_code == 200 and b'name="event"' not in (
            detail.content
        )
        client.post(f"{base}{row.pk}/change/", {"event": "FORGED"})
        assert TransitionLog.objects.get().event == "REJECT"

    def test_inline_renders_redacted_rows(
        self, client: Any, users: Any
    ) -> None:
        from shop.models import Approval

        from xstate_statemachine.contrib.django.audit import forget_log

        root = self._login(client, users)
        a = Approval.objects.create()
        a.send(
            "REJECT", actor=root, reason="dup", payload={"blob": "x" * 9000}
        )
        forget_log(a, using="default")
        page = client.get(f"/admin/shop/approval/{a.pk}/change/")
        assert page.status_code == 200
        assert b"REJECT" in page.content
        assert len(page.content) < 60_000
