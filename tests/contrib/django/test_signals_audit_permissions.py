# tests/contrib/django/test_signals_audit_permissions.py
"""#281: signals, in-transaction audit, permission guards, outbox."""

from __future__ import annotations

from typing import Any, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction

from xstate_statemachine.contrib.django.permissions import (
    AllOf,
    AnyOf,
    PermissionGuard,
    RoleGuard,
    StatechartPermission,
    has_event_permission,
    permitted_events,
)
from xstate_statemachine.contrib.django.signals import (
    TransitionVetoed,
    post_transition,
    pre_transition,
    statechart_error,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def users(db: Any) -> Any:
    U = get_user_model()
    approver = U.objects.create_user("approver", password="p")
    approver.user_permissions.add(
        Permission.objects.get(codename="approve_approval")
    )
    intern = U.objects.create_user("intern", password="p")
    manager = U.objects.create_user("manager", password="p")
    manager.groups.add(Group.objects.create(name="managers"))
    return {
        "approver": U.objects.get(pk=approver.pk),  # fresh perm cache
        "intern": intern,
        "manager": manager,
    }


@pytest.fixture
def approval(db: Any) -> Any:
    from shop.models import Approval

    return Approval.objects.create(title="a")


class Recorder:
    def __init__(self) -> None:
        self.calls: List[dict] = []

    def __call__(self, sender: Any, **kw: Any) -> None:
        self.calls.append(kw)


# -----------------------------------------------------------------------------
# 📣 signals
# -----------------------------------------------------------------------------
class TestSignals:
    def test_post_transition_fires_once_with_from_to(
        self, approval: Any, users: Any
    ) -> None:
        rec = Recorder()
        post_transition.connect(rec, weak=False)
        try:
            r = approval.send("APPROVE", actor=users["approver"], reason="ok")
        finally:
            post_transition.disconnect(rec)
        assert r.changed
        assert len(rec.calls) == 1
        call = rec.calls[0]
        assert call["instance"] is approval
        assert call["event"].type == "APPROVE"
        assert call["from_states"] == ("approval.pending",)
        assert call["to_states"] == ("approval.approved",)
        assert call["actor"] == users["approver"]

    def test_pre_transition_veto_denies_without_change_or_audit(
        self, approval: Any, users: Any
    ) -> None:
        def veto(sender: Any, **kw: Any) -> None:
            raise TransitionVetoed("frozen")

        pre_transition.connect(veto, weak=False)
        try:
            r = approval.send("APPROVE", actor=users["approver"])
        finally:
            pre_transition.disconnect(veto)
        assert r.denied and not r.changed
        fresh = type(approval).objects.get(pk=approval.pk)
        assert fresh.state == "approval.pending"
        assert fresh.statechart_version == 0
        assert approval.history.count() == 0

    def test_statechart_error_on_raising_action(self, approval: Any) -> None:
        rec = Recorder()
        statechart_error.connect(rec, weak=False)
        try:
            r = approval.send("BOOM")
        finally:
            statechart_error.disconnect(rec)
        assert r.error is not None
        assert [c["kind"] for c in rec.calls] == ["action"]
        assert isinstance(rec.calls[0]["error"], RuntimeError)

    def test_on_commit_receiver_runs_only_after_commit(
        self, approval: Any, users: Any, django_capture_on_commit_callbacks
    ) -> None:
        rec = Recorder()
        post_transition.connect(rec, on_commit=True)
        try:
            with django_capture_on_commit_callbacks(execute=True) as cbs:
                approval.send("COMMENT", text="x")
                assert rec.calls == []  # not yet: still in the transaction
            assert len(cbs) == 1 and len(rec.calls) == 1
            # A rolled-back send never reaches the on_commit receiver.
            with django_capture_on_commit_callbacks(execute=True) as cbs:
                with pytest.raises(RuntimeError):
                    with transaction.atomic():
                        approval.send("COMMENT", text="y")
                        raise RuntimeError("rollback")
            assert cbs == [] and len(rec.calls) == 1
        finally:
            assert post_transition.disconnect(rec, on_commit=True)


@pytest.mark.django_db(transaction=True)
def test_post_transition_raise_rolls_back_state_and_audit() -> None:
    """Audit row and state change are atomic (real commits)."""
    from shop.models import Approval

    a = Approval.objects.create()

    def boom(sender: Any, **kw: Any) -> None:
        raise RuntimeError("receiver failed")

    post_transition.connect(boom, weak=False)
    try:
        with pytest.raises(RuntimeError):
            a.send("COMMENT", text="x")
    finally:
        post_transition.disconnect(boom)
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.statechart_version == 0
    assert "notes" not in fresh.machine.context
    assert fresh.history.count() == 0
    fresh.send("COMMENT", text="ok")  # and it still works afterwards
    assert fresh.history.count() == 1


# -----------------------------------------------------------------------------
# 📜 audit
# -----------------------------------------------------------------------------
class TestAudit:
    def test_history_rows_ordered_redacted_with_actor(
        self, approval: Any, users: Any
    ) -> None:
        approval.send("COMMENT", text="hi", password="hunter2")
        approval.send("APPROVE", actor=users["intern"], reason="try")
        approval.send("APPROVE", actor=users["approver"], reason="ok")
        rows = list(approval.history.all())
        assert [r.seq for r in rows] == [1, 2, 3]
        assert [r.event for r in rows] == ["COMMENT", "APPROVE", "APPROVE"]
        assert [r.disposition for r in rows] == [
            "transition",
            "denied",
            "transition",
        ]
        assert rows[0].payload["password"] == "***"
        assert rows[0].actions == ["note"]
        assert rows[1].actor == users["intern"] and rows[1].reason == "try"
        assert rows[2].from_states == ["approval.pending"]
        assert rows[2].to_states == ["approval.approved"]

    def test_log_store_protocol_and_forget_modes(
        self, approval: Any, users: Any
    ) -> None:
        from xstate_statemachine.contrib.django.audit import (
            DjangoTransitionLogStore,
        )
        from xstate_statemachine.persistence.log import TransitionLogStore

        approval.send("COMMENT", text="secret stuff", actor=users["intern"])
        store = DjangoTransitionLogStore(approval)
        assert isinstance(store, TransitionLogStore)
        recs = store.read(store.machine_id)
        assert len(recs) == 1 and recs[0].actor == str(users["intern"].pk)
        assert store.next_seq(store.machine_id) == 2
        with pytest.raises(ValueError):
            store.append(_other(recs[0]))
        # redact (default): the chain survives, the personal data does not
        counts = approval.forget_statechart()
        assert counts["log_entries"] == 1
        row = approval.history.get()
        assert row.payload == {} and row.actor is None
        # delete mode
        type(approval).statechart_forget_log = "delete"
        try:
            approval.refresh_from_db()
            approval.statechart = None
            assert store.forget(store.machine_id, mode="delete") == 1
        finally:
            type(approval).statechart_forget_log = "redact"
        assert approval.history.count() == 0
        with pytest.raises(ValueError):
            store.forget(store.machine_id, mode="bogus")
        assert store.purge_older_than(0.0) == 0

    def test_audit_can_be_disabled(self, users: Any) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        Approval.statechart_audit = False
        try:
            a.send("COMMENT", text="x")
        finally:
            Approval.statechart_audit = None
        assert a.history.count() == 0


def _other(rec: Any) -> Any:
    from dataclasses import replace

    return replace(rec, machine_id="other:1")


# -----------------------------------------------------------------------------
# 🔐 permissions
# -----------------------------------------------------------------------------
class TestPermissions:
    def test_permission_guard_true_false_and_no_actor(
        self, approval: Any, users: Any
    ) -> None:
        assert approval.send("APPROVE").denied  # no actor
        assert approval.send("APPROVE", actor=users["intern"]).denied
        assert approval.can("APPROVE", actor=users["approver"])
        assert not approval.can("APPROVE", actor=users["intern"])
        r = approval.send("APPROVE", actor=users["approver"], reason="ok")
        assert r.changed and approval.state == "approval.approved"
        # RoleGuard: only the managers group may reopen
        assert approval.send("REOPEN", actor=users["approver"]).denied
        assert approval.send("REOPEN", actor=users["manager"]).changed

    def test_object_level_backend(self, approval: Any, users: Any, settings):
        from shop.models import Approval

        other = Approval.objects.create()
        settings.AUTHENTICATION_BACKENDS = [
            "django.contrib.auth.backends.ModelBackend",
            "shop.backends.OwnRowBackend",
        ]
        guard = PermissionGuard("shop.approve_approval", fallback_global=False)
        intern = users["intern"]
        # object-level only: the fake backend grants row `approval.pk`
        from shop import backends

        backends.GRANTS[(intern.pk, approval.pk)] = True
        assert guard.check(intern, approval) is True
        assert guard.check(intern, other) is False
        assert guard.check(intern, None) is False  # global: not granted

    def test_guard_constructors(self) -> None:
        with pytest.raises(ValueError):
            PermissionGuard()
        with pytest.raises(ValueError):
            PermissionGuard("no_dot")
        with pytest.raises(ValueError):
            RoleGuard()
        with pytest.raises(ValueError):
            AnyOf()
        with pytest.raises(ValueError):
            AllOf()
        assert "approve" in repr(PermissionGuard("shop.approve_approval"))
        assert "managers" in repr(RoleGuard("managers"))

    def test_composition(self, users: Any) -> None:
        p = PermissionGuard("shop.approve_approval")
        r = RoleGuard("managers")
        a, m, i = users["approver"], users["manager"], users["intern"]
        assert AnyOf(p, r).check(a, None) and AnyOf(p, r).check(m, None)
        assert not AnyOf(p, r).check(i, None)
        assert not AllOf(p, r).check(a, None)
        m.user_permissions.add(
            Permission.objects.get(codename="approve_approval")
        )
        m = get_user_model().objects.get(pk=m.pk)
        assert AllOf(p, r).check(m, None)

    def test_has_event_permission_matrix(
        self, approval: Any, users: Any
    ) -> None:
        from django.contrib.auth.models import AnonymousUser

        a, i, m = users["approver"], users["intern"], users["manager"]

        def hp(u: Any, e: str) -> bool:
            return has_event_permission(u, approval, e)

        # pending: approver may approve/reject; nobody may reopen (can()=False)
        assert hp(a, "APPROVE") and hp(a, "REJECT") and hp(a, "COMMENT")
        assert not hp(i, "APPROVE") and hp(i, "COMMENT")
        assert not hp(m, "REOPEN")  # guard ok but not enabled in `pending`
        assert not hp(AnonymousUser(), "COMMENT")
        assert not hp(None, "COMMENT")
        i.is_active = False
        assert not hp(i, "COMMENT")
        i.is_active = True
        assert permitted_events(a, approval) == [
            "APPROVE",
            "BOOM",
            "COMMENT",
            "REJECT",
        ]
        assert permitted_events(i, approval) == ["BOOM", "COMMENT"]
        approval.send("APPROVE", actor=a)
        assert hp(m, "REOPEN") and not hp(a, "REOPEN")
        pol = StatechartPermission()
        assert pol.permitted_events(m, approval) == ["REOPEN"]
        assert pol.has_event_permission(m, approval, None)
        assert not pol.has_event_permission(AnonymousUser(), approval, None)

    def test_available_events_for_actor(
        self, approval: Any, users: Any
    ) -> None:
        assert "APPROVE" not in approval.available_events
        assert "APPROVE" in approval.available_events_for(users["approver"])


# -----------------------------------------------------------------------------
# 📤 outbox
# -----------------------------------------------------------------------------
class TestOutbox:
    def _model(self) -> Any:
        from shop.models import Approval

        from xstate_statemachine.contrib.django.outbox import (
            DjangoOutboxStore,
        )
        from xstate_statemachine.eda.outbox import OutboxPlugin

        outbox = DjangoOutboxStore()
        Approval.statechart_plugins = lambda row: [OutboxPlugin(outbox)]
        return Approval, outbox

    def teardown_method(self) -> None:
        from shop.models import Approval

        Approval.statechart_plugins = ()

    def test_rows_written_in_the_send_transaction(self, users: Any) -> None:
        from xstate_statemachine.eda.outbox import OutboxStore

        Approval, outbox = self._model()
        assert isinstance(outbox, OutboxStore)
        a = Approval.objects.create()
        a.send("APPROVE", actor=users["approver"])
        pend = outbox.pending()
        assert len(pend) == 1
        assert pend[0].envelope.subject is not None
        assert outbox.count(pending_only=True) == 1
        assert outbox.mark_sent([pend[0].seq]) == 1
        assert outbox.mark_sent([]) == 0
        assert outbox.pending() == []
        assert outbox.purge_sent(older_than_s=-1) == 1

    def test_forced_rollback_leaves_no_row(self, users: Any) -> None:
        Approval, outbox = self._model()
        a = Approval.objects.create()
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                a.send("APPROVE", actor=users["approver"])
                assert outbox.count() == 1
                raise RuntimeError("rollback")
        assert outbox.count() == 0
        assert Approval.objects.get(pk=a.pk).state == "approval.pending"

    def test_djangostore_persisted_block_shares_the_transaction(self) -> None:
        from xstate_statemachine import create_machine
        from xstate_statemachine.contrib.django import DjangoStore
        from xstate_statemachine.contrib.django.outbox import (
            DjangoOutboxStore,
        )
        from xstate_statemachine.eda.outbox import OutboxPlugin
        from xstate_statemachine.persistence import persisted

        m = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {
                    "a": {"on": {"GO": "b"}},
                    "b": {"tags": ["publish"]},
                },
            }
        )
        store, outbox = DjangoStore("outbox"), DjangoOutboxStore()
        with pytest.raises(RuntimeError):
            with store.transaction():
                with persisted(
                    store, "k", m, plugins=[OutboxPlugin(outbox)]
                ) as i:
                    i.send("GO")
                raise RuntimeError("after the save, before commit")
        assert store.load("k") is None and outbox.count() == 0
        with store.transaction():
            with persisted(store, "k", m, plugins=[OutboxPlugin(outbox)]) as i:
                i.send("GO")
        assert store.load("k") is not None and outbox.count() == 1
