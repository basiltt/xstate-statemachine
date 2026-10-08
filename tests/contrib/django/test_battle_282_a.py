# tests/contrib/django/test_battle_282_a.py
"""#282 battle, adversary A: the admin attacked by a hostile or careless
staff user."""

from __future__ import annotations

import threading
from typing import Any, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connections
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

BOSS = ("view_approval", "change_approval", "approve_approval")


def _staff(username: str, *perms: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(username, password="p", is_staff=True)
    for codename in perms:
        u.user_permissions.add(Permission.objects.get(codename=codename))
    return U.objects.get(pk=u.pk)


def _client(user: Any, csrf: bool = False) -> Client:
    c = Client(enforce_csrf_checks=csrf)
    c.force_login(user)
    return c


def _url(name: str, obj: Any) -> str:
    return reverse(f"admin:shop_approval_{name}", args=[obj.pk])


def _msgs(r: Any) -> List[str]:
    return [str(m) for m in r.context["messages"]]


class TestNoPermissionLeaks:
    def test_confirm_page_is_403_without_view_permission(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create(title="secret-title")
        nobody = _staff("nobody")
        r = _client(nobody).get(
            _url("xsm_transition", a), {"_xsm_event": "APPROVE"}
        )
        assert r.status_code == 403

    def test_missing_pk_is_404_for_a_viewer(self) -> None:
        viewer = _staff("viewer", "view_approval")
        c = _client(viewer)
        for name in ("xsm_diagram", "xsm_transition"):
            url = reverse(f"admin:shop_approval_{name}", args=[987654])
            assert c.get(url, {"_xsm_event": "APPROVE"}).status_code == 404
        for junk in ("abc", "1/../2", "%2e%2e"):
            r = c.get(f"/admin/shop/approval/{junk}/statechart/")
            assert r.status_code in (404, 302), junk

    def test_missing_pk_without_permission_is_403(self) -> None:
        nobody = _staff("nobody2")
        url = reverse("admin:shop_approval_xsm_diagram", args=[987654])
        assert _client(nobody).get(url).status_code == 403

    def test_view_only_user_gets_no_bulk_transition_actions(self) -> None:
        from shop.models import Approval

        Approval.objects.create()
        cl = reverse("admin:shop_approval_changelist")
        viewer = _staff("viewer2", "view_approval", "approve_approval")
        assert "xsm_REJECT" not in _client(viewer).get(cl).content.decode()
        boss = _staff("boss", *BOSS)
        assert "xsm_REJECT" in _client(boss).get(cl).content.decode()


class TestMermaid:
    def test_hostile_state_key_cannot_break_out(
        self, monkeypatch: Any
    ) -> None:
        from shop.models import Approval

        from xstate_statemachine import create_machine

        evil = "x</pre><script>alert(1)</script>"
        chart = {
            "id": "approval",
            "initial": evil,
            "states": {evil: {"on": {"GO": "b"}}, "b": {}},
        }
        node = create_machine(chart)
        monkeypatch.setattr(
            Approval, "statechart_machine_node", lambda self: node
        )
        a = Approval.objects.create()
        boss = _staff("boss2", *BOSS)
        body = _client(boss).get(_url("xsm_diagram", a)).content.decode()
        assert "<script>alert(1)" not in body

    def test_class_lines_only_for_safe_ids(self) -> None:
        from xstate_statemachine import create_machine
        from xstate_statemachine.contrib.django.admin import (
            highlighted_mermaid,
        )

        node = create_machine({"id": "m", "initial": "a", "states": {"a": {}}})
        text = highlighted_mermaid(
            node, ["m.a", "m.x\n    click a call alert()"]
        )
        assert "class a xsmActive" in text
        assert "click" not in text


class TestBulk:
    def test_lock_timeout_mid_bulk_is_counted_as_failed(
        self, monkeypatch: Any
    ) -> None:
        from shop.models import Approval

        from xstate_statemachine.exceptions import LockTimeoutError

        rows = [Approval.objects.create() for _ in range(5)]
        victim = rows[2].pk
        real = Approval.send

        def send(self: Any, *a: Any, **kw: Any) -> Any:
            if self.pk == victim:
                raise LockTimeoutError("approval", 1.0)
            return real(self, *a, **kw)

        monkeypatch.setattr(Approval, "send", send)
        boss = _staff("boss3", *BOSS)
        r = _client(boss).post(
            reverse("admin:shop_approval_changelist"),
            {"action": "xsm_REJECT", "_selected_action": [x.pk for x in rows]},
            follow=True,
        )
        msgs = _msgs(r)
        assert any(
            "4 changed" in m and "0 denied" in m and "1 failed" in m
            for m in msgs
        ), msgs
        done = Approval.objects.filter(
            statechart_state="approval.rejected"
        ).values_list("pk", flat=True)
        assert sorted(done) == sorted(x.pk for x in rows if x.pk != victim)


class TestTemplates:
    def test_documented_block_override_keeps_buttons(
        self, settings: Any, tmp_path: Any
    ) -> None:
        from shop.models import Approval

        d = tmp_path / "admin" / "xsm"
        d.mkdir(parents=True)
        # 📝 the documented way: override admin/xsm/change_form.html in
        #    the project, extending the packaged one (Django resolves a
        #    same-name extends to the next loader) and replacing a block.
        (d / "change_form.html").write_text(
            '{% extends "admin/xsm/change_form.html" %}'
            "{% block xsm_badge %}<p id=custom-badge>B</p>{% endblock %}",
            encoding="utf-8",
        )
        settings.TEMPLATES = [
            {**settings.TEMPLATES[0], "DIRS": [str(tmp_path)]}
        ]
        a = Approval.objects.create()
        boss = _staff("boss4", *BOSS)
        html = _client(boss).get(_url("change", a)).content.decode()
        assert "custom-badge" in html
        assert 'value="REJECT"' in html


@pytest.mark.django_db(transaction=True)
def test_sixteen_staff_confirm_at_once_exactly_one_transition() -> None:
    from shop.models import Approval

    a = Approval.objects.create()
    users = [_staff(f"s{i}", *BOSS) for i in range(16)]
    url = _url("xsm_transition", a)
    gate = threading.Barrier(16)
    status: List[Any] = []
    errors: List[BaseException] = []

    def run(u: Any) -> None:
        try:
            c = _client(u)
            gate.wait(30)
            r = c.post(
                url,
                {
                    "_xsm_event": "APPROVE",
                    "_xsm_confirmed": "1",
                    "reason": u.username,
                },
            )
            status.append(r.status_code)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connections.close_all()

    ts = [threading.Thread(target=run, args=(u,)) for u in users]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    assert not errors, errors
    assert status == [302] * 16
    a.refresh_from_db()
    assert a.state == "approval.approved"
    kinds = list(a.history.values_list("disposition", flat=True))
    # 📝 one applied, fifteen audited as no-ops (the guard saw approved)
    assert kinds.count("transition") == 1
    assert kinds.count("unhandled") == 15


class TestMoreProbes:
    def test_parallel_filter_matches_whole_segments(self) -> None:
        from shop.models import Order

        o = Order.objects.create()
        o.send("SUBMIT")
        boss = _staff("boss5", "view_order", "change_order")
        cl = reverse("admin:shop_order_changelist")
        c = _client(boss)

        def ids(v: str) -> List[str]:
            import re

            html = c.get(cl, {"xsm_state": v}).content.decode()
            return re.findall(r'name="_selected_action" value="(\d+)"', html)

        assert ids("order.review.legal") == [str(o.pk)]
        assert ids("order.review.finance.pending") == [str(o.pk)]
        assert ids("order.review.leg") == []

    def test_hostile_reason_is_escaped_in_the_history_inline(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        boss = _staff("boss6", *BOSS)
        evil = "<img src=x onerror=alert(1)>"
        c = _client(boss)
        c.post(
            _url("xsm_transition", a),
            {"_xsm_event": "APPROVE", "_xsm_confirmed": "1", "reason": evil},
        )
        a.refresh_from_db()
        assert a.history.get().reason == evil
        html = c.get(_url("change", a)).content.decode()
        assert evil not in html and "&lt;img" in html

    def test_bulk_actions_off(self, monkeypatch: Any) -> None:
        from shop.admin import ApprovalAdmin

        monkeypatch.setattr(ApprovalAdmin, "xsm_bulk_actions", False)
        boss = _staff("boss7", *BOSS)
        html = (
            _client(boss)
            .get(reverse("admin:shop_approval_changelist"))
            .content.decode()
        )
        assert "xsm_REJECT" not in html

    def test_permission_revoked_between_get_and_post(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        boss = _staff("boss8", *BOSS)
        c = _client(boss)
        assert (
            b"Confirm"
            in c.get(
                _url("xsm_transition", a), {"_xsm_event": "APPROVE"}
            ).content
        )
        boss.user_permissions.remove(
            Permission.objects.get(codename="approve_approval")
        )
        r = c.post(
            _url("xsm_transition", a),
            {"_xsm_event": "APPROVE", "_xsm_confirmed": "1"},
            follow=True,
        )
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.state == "approval.pending"
