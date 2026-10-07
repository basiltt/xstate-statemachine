# tests/contrib/django/test_battle_281_a.py
"""#281 battle, adversary A: marker plugins under ``send()``, signals,
audit, outbox and inbox -- on SQLite and, with
``DATABASE_URL=postgresql://...``, on a real Postgres."""

from __future__ import annotations

import threading
from typing import Any, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection

from xstate_statemachine.contrib.django.signals import post_transition

pytestmark = pytest.mark.django_db

PG = connection.vendor == "postgresql"


@pytest.fixture
def approver(db: Any) -> Any:
    U = get_user_model()
    u = U.objects.create_user("approver281a", password="p")
    u.user_permissions.add(Permission.objects.get(codename="approve_approval"))
    return U.objects.get(pk=u.pk)


@pytest.fixture
def plugins_reset() -> Any:
    from shop.models import Approval, Order

    yield
    Approval.statechart_plugins = ()
    Order.statechart_plugins = ()


@pytest.fixture
def approval_row(db: Any) -> Any:
    from shop.models import Approval

    return Approval.objects.create()


class _Rec:
    def __init__(self) -> None:
        self.calls: List[dict] = []

    def __call__(self, sender: Any, **kw: Any) -> None:
        self.calls.append(dict(kw, sender=sender))

    def method(self, sender: Any, **kw: Any) -> None:
        self.calls.append(dict(kw, sender=sender))


def _outbox(sink: Any = None) -> Any:
    from xstate_statemachine.contrib.django.outbox import DjangoOutboxStore
    from xstate_statemachine.eda.outbox import OutboxPlugin

    return OutboxPlugin(sink or DjangoOutboxStore())


class _FailingStore:
    """An `OutboxStore` whose INSERT fails."""

    def add(self, topic: str, envelope: Any) -> None:
        raise RuntimeError("outbox insert failed")

    def pending(self, *, limit: int = 100) -> list:  # pragma: no cover
        return []

    def mark_sent(self, seqs: Any) -> int:  # pragma: no cover
        return 0


# -----------------------------------------------------------------------------
# 1. marker plugins
# -----------------------------------------------------------------------------
def test_shared_outbox_plugin_other_session_exit_keeps_buffering(
    approver: Any, plugins_reset: Any
) -> None:
    """ONE `OutboxPlugin` shared by every row: another send's session
    ending mid-run must not switch buffering off for this send -- its
    failing outbox INSERT was swallowed again (defect 2 revived)."""
    from shop.models import Approval

    from xstate_statemachine.contrib.django._markers import _marker_session
    from xstate_statemachine.eda.outbox import OutboxPlugin

    entered, leave, left = (threading.Event() for _ in range(3))

    class Hook(OutboxPlugin):
        def on_transition(self, *a: Any) -> None:
            super().on_transition(*a)
            leave.set()
            left.wait(10)

    shared = Hook(_FailingStore())

    def other_send() -> None:  # stands in for a concurrent send
        with _marker_session([shared]):
            entered.set()
            leave.wait(10)
        left.set()

    Approval.statechart_plugins = lambda row: [shared]
    a = Approval.objects.create()
    t = threading.Thread(target=other_send)
    t.start()
    assert entered.wait(10)
    try:
        with pytest.raises(RuntimeError, match="outbox insert failed"):
            a.send("APPROVE", actor=approver)
    finally:
        leave.set()
        t.join(10)
    assert Approval.objects.get(pk=a.pk).state == "approval.pending"


def test_flush_failure_rolls_back_and_propagates(
    approver: Any, plugins_reset: Any
) -> None:
    from shop.models import Approval

    Approval.statechart_plugins = lambda row: [_outbox(_FailingStore())]
    a = Approval.objects.create()
    with pytest.raises(RuntimeError, match="outbox insert failed"):
        a.send("APPROVE", actor=approver)
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.state == "approval.pending" and fresh.history.count() == 0


def test_nested_send_from_post_transition_on_other_row(
    approver: Any, plugins_reset: Any
) -> None:
    from shop.models import Approval

    from xstate_statemachine.contrib.django.outbox import DjangoOutboxStore

    store = DjangoOutboxStore()
    shared = _outbox(store)
    Approval.statechart_plugins = lambda row: [shared]
    a, b = Approval.objects.create(), Approval.objects.create()

    def chain(sender: Any, instance: Any, **kw: Any) -> None:
        if instance.pk == a.pk:
            Approval.objects.get(pk=b.pk).send("APPROVE", actor=approver)

    post_transition.connect(chain, weak=False)
    try:
        a.send("APPROVE", actor=approver)
    finally:
        post_transition.disconnect(chain)
    assert Approval.objects.get(pk=b.pk).state == "approval.approved"
    subjects = [r.envelope.subject for r in store.pending()]
    assert len(subjects) == 2 and len(set(subjects)) == 2


def test_same_row_send_from_post_transition(approver: Any) -> None:
    from shop.models import Approval

    a = Approval.objects.create()

    def again(sender: Any, instance: Any, event: Any, **kw: Any) -> None:
        if event.type == "COMMENT":
            instance.send("APPROVE", actor=approver)

    post_transition.connect(again, weak=False)
    try:
        a.send("COMMENT", text="x")
    finally:
        post_transition.disconnect(again)
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.state == "approval.approved"
    assert fresh.statechart_version == 2
    assert [r.seq for r in fresh.history.all()] == [1, 2]


def _idem(inbox: Any = None) -> Any:
    from xstate_statemachine.contrib.django.inbox import DjangoInbox
    from xstate_statemachine.persistence.idempotency import IdempotencyPlugin

    return IdempotencyPlugin(
        inbox or DjangoInbox(), principal=lambda e: "u1", ttl_s=None
    )


def test_inbox_through_statechart_plugins_rolls_back_with_send(
    approver: Any, plugins_reset: Any
) -> None:
    from django.apps import apps
    from shop.models import Approval

    plug = _idem()
    Approval.statechart_plugins = lambda row: [plug]
    a = Approval.objects.create()

    def boom(sender: Any, **kw: Any) -> None:
        raise RuntimeError("receiver")

    post_transition.connect(boom, weak=False)
    try:
        with pytest.raises(RuntimeError):
            a.send("APPROVE", actor=approver, idempotency_key="k1")
    finally:
        post_transition.disconnect(boom)
    rec = apps.get_model("xsm_django", "IdempotencyRecord")
    assert rec.objects.count() == 0  # the claim rolled back too
    r1 = a.send("APPROVE", actor=approver, idempotency_key="k1")
    assert r1.changed and not r1.duplicate
    r2 = Approval.objects.get(pk=a.pk).send(
        "APPROVE", actor=approver, idempotency_key="k1"
    )
    assert r2.duplicate
    assert r2.state_ids == r1.state_ids and r2.changed == r1.changed
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.statechart_version == 1 and fresh.history.count() == 1


# -----------------------------------------------------------------------------
# 2. signals
# -----------------------------------------------------------------------------
def test_on_commit_bound_method_disconnects() -> None:
    rec = _Rec()
    post_transition.connect(rec.method, on_commit=True)
    assert post_transition.disconnect(rec.method)
    assert not post_transition.has_listeners()


def test_on_commit_per_sender_disconnect() -> None:
    from shop.models import Approval, Order

    rec = _Rec()
    post_transition.connect(rec, sender=Approval, on_commit=True)
    post_transition.connect(rec, sender=Order, on_commit=True)
    assert post_transition.disconnect(rec, sender=Approval)
    assert post_transition.disconnect(rec, sender=Order)
    assert not post_transition.has_listeners()


def test_on_commit_dispatch_uid_spellings() -> None:
    rec = _Rec()
    post_transition.connect(rec, dispatch_uid="u", on_commit=True)
    post_transition.connect(rec, dispatch_uid="u", on_commit=True)
    assert len(post_transition.receivers) == 1
    assert post_transition.disconnect(dispatch_uid="u")
    post_transition.connect(rec, dispatch_uid="u", on_commit=True)
    assert post_transition.disconnect(rec, dispatch_uid="u", on_commit=True)
    assert not post_transition.has_listeners()


def test_on_commit_receiver_registered_twice_runs_once(
    approval_row: Any, django_capture_on_commit_callbacks: Any
) -> None:
    rec = _Rec()
    post_transition.connect(rec, on_commit=True)
    post_transition.connect(rec, on_commit=True)
    try:
        with django_capture_on_commit_callbacks(execute=True):
            approval_row.send("COMMENT", text="x")
    finally:
        post_transition.disconnect(rec)
    assert len(rec.calls) == 1


def test_on_commit_bound_method_is_weak_by_default(
    approval_row: Any, django_capture_on_commit_callbacks: Any
) -> None:
    """Like Django's own ``connect(obj.method)``: the wrapper does not
    keep a dead receiver alive (and cleans itself up)."""
    import gc

    rec = _Rec()
    post_transition.connect(rec.method, on_commit=True)
    del rec
    gc.collect()
    with django_capture_on_commit_callbacks(execute=True) as cbs:
        approval_row.send("COMMENT", text="x")
    assert cbs == []
    assert not post_transition.has_listeners()


def test_on_commit_weak_false_keeps_bound_method_alive(
    approval_row: Any, django_capture_on_commit_callbacks: Any
) -> None:
    import gc

    calls: List[Any] = []

    class R:
        def m(self, sender: Any, **kw: Any) -> None:
            calls.append(kw)

    post_transition.connect(
        R().m, weak=False, on_commit=True, dispatch_uid="strong"
    )
    gc.collect()
    try:
        with django_capture_on_commit_callbacks(execute=True):
            approval_row.send("COMMENT", text="x")
    finally:
        assert post_transition.disconnect(dispatch_uid="strong")
    assert len(calls) == 1


def test_sender_filter(approval_row: Any) -> None:
    from shop.models import Approval, Order

    a_rec, o_rec, any_rec = _Rec(), _Rec(), _Rec()
    post_transition.connect(a_rec, sender=Approval, weak=False)
    post_transition.connect(o_rec, sender=Order, weak=False)
    post_transition.connect(any_rec, weak=False)
    try:
        approval_row.send("COMMENT", text="x")
        Order.objects.create().send("INC")
    finally:
        for r in (a_rec, o_rec, any_rec):
            post_transition.disconnect(r, sender=None)
        post_transition.disconnect(a_rec, sender=Approval)
        post_transition.disconnect(o_rec, sender=Order)
    assert [c["sender"] for c in a_rec.calls] == [Approval]
    assert [c["sender"] for c in o_rec.calls] == [Order]
    assert len(any_rec.calls) == 2


def test_parallel_and_done_state_payload(order: Any) -> None:
    rec = _Rec()
    post_transition.connect(rec, weak=False)
    try:
        order.send("SUBMIT")
        order.send("LEGAL_OK")
        order.send("FINANCE_OK")
    finally:
        post_transition.disconnect(rec)
    assert len(rec.calls) == 3
    sub, legal, fin = rec.calls
    assert sub["to_states"] == (
        "order.review.finance.pending",
        "order.review.legal.pending",
    )
    assert legal["from_states"] == sub["to_states"]
    assert "order.review.legal.ok" in legal["to_states"]
    # one post_transition per SEND: the engine's done.state step folds in
    assert fin["to_states"] == ("order.approved",)
    assert fin["using"] == "default" and fin["actor"] is None


def test_engine_done_state_audit_row_has_no_human_actor(
    order: Any, approver: Any
) -> None:
    """The ``done.state`` step the engine raises is not the user's act:
    its row must carry ``actor=None`` (the brief), not the sender's."""
    order.send("SUBMIT", actor=approver)
    order.send("LEGAL_OK", actor=approver)
    order.send("FINANCE_OK", actor=approver)
    rows = list(order.history.all())
    assert [r.seq for r in rows] == list(range(1, len(rows) + 1))
    human = [r for r in rows if not r.event.startswith("done.")]
    engine = [r for r in rows if r.event.startswith("done.")]
    assert all(r.actor_id == approver.pk for r in human)
    assert engine, [r.event for r in rows]
    assert all(r.actor_id is None for r in engine), [
        (r.event, r.actor_id) for r in engine
    ]


# -----------------------------------------------------------------------------
# 3. audit
# -----------------------------------------------------------------------------
def test_audit_redacts_nested_and_keeps_correlation(approval_row: Any) -> None:
    approval_row.send(
        "COMMENT",
        text="hi",
        correlation_id="corr-1",
        meta={"auth": {"x": "t"}, "list": [{"secret": 2}]},
    )
    row = approval_row.history.get()
    assert row.correlation_id == "corr-1"
    assert row.payload["meta"]["auth"] == "***"  # "auth" is a key itself
    assert row.payload["meta"]["list"][0]["secret"] == "***"
    assert row.payload["text"] == "hi"
    assert row.payload["meta"]["list"][0]["secret"] == "***"


def test_audit_one_megabyte_payload(order: Any) -> None:
    big = "x" * (1 << 20)
    order.send("INC", blob=big)  # payload is not kept in the context
    assert len(order.history.get().payload["blob"]) == 1 << 20


def test_statechart_error_and_audit_under_both_policies(
    approval_row: Any,
) -> None:
    from xstate_statemachine.contrib.django.signals import statechart_error

    rec = _Rec()
    statechart_error.connect(rec, weak=False)
    try:
        r = approval_row.send("BOOM")  # the chart says "continue"
    finally:
        statechart_error.disconnect(rec)
    assert [c["kind"] for c in rec.calls] == ["action"]
    row = approval_row.history.get()
    assert row.disposition == "error", r


def test_forget_redact_keeps_chain_and_structure(
    approval_row: Any, approver: Any
) -> None:
    approval_row.send("COMMENT", text="pii", actor=approver, reason="why")
    approval_row.send("APPROVE", actor=approver, correlation_id="c")
    approval_row.forget_statechart()
    rows = list(approval_row.history.all())
    assert [r.seq for r in rows] == [1, 2]
    assert [r.event for r in rows] == ["COMMENT", "APPROVE"]
    assert rows[1].to_states == ["approval.approved"]
    for r in rows:
        assert r.payload == {} and r.actor_id is None
        assert r.reason == "" and r.correlation_id == ""


def test_forget_delete_mode(approval_row: Any) -> None:
    approval_row.send("COMMENT", text="pii")
    type(approval_row).statechart_forget_log = "delete"
    try:
        counts = approval_row.forget_statechart()
    finally:
        del type(approval_row).statechart_forget_log
    assert counts["log_entries"] == 1
    assert approval_row.history.count() == 0


# -----------------------------------------------------------------------------
# 4. outbox
# -----------------------------------------------------------------------------
def _env(i: int) -> Any:
    from xstate_statemachine.eda.envelope import Envelope

    return Envelope(type="t", source="s", data={"i": i}, subject=str(i))


def test_outbox_store_ordering_mark_sent_idempotent_and_relay(db: Any) -> None:
    from xstate_statemachine.contrib.django.outbox import DjangoOutboxStore
    from xstate_statemachine.eda.fake import SyncFakeBrokerAdapter
    from xstate_statemachine.eda.outbox import OutboxRelay

    s = DjangoOutboxStore()
    for i in range(5):
        s.add("t", _env(i))
    pend = s.pending()
    assert [r.envelope.data["i"] for r in pend] == list(range(5))
    assert [r.seq for r in pend] == sorted(r.seq for r in pend)
    assert s.mark_sent([pend[0].seq]) == 1
    assert s.mark_sent([pend[0].seq]) == 0  # already marked: not twice
    broker = SyncFakeBrokerAdapter()
    assert OutboxRelay(s, broker, batch=2).relay_once_sync() == 2
    assert OutboxRelay(s, broker).relay_once_sync() == 2
    assert s.count(pending_only=True) == 0 and s.count() == 5
    assert s.purge_sent(older_than_s=3600) == 0
    assert s.purge_sent(older_than_s=-1) == 5


# -----------------------------------------------------------------------------
# 5. concurrency (real commits)
# -----------------------------------------------------------------------------
def _fleet(fns: List[Any]) -> List[BaseException]:
    from django.db import connections

    errors: List[BaseException] = []
    gate = threading.Barrier(len(fns))

    def run(fn: Any) -> None:
        try:
            gate.wait(30)
            fn()
        except BaseException as exc:  # noqa: BLE001 - asserted by caller
            errors.append(exc)
        finally:
            connections.close_all()

    ts = [threading.Thread(target=run, args=(fn,)) for fn in fns]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    return errors


@pytest.mark.django_db(transaction=True)
def test_veto_fleet_gapless_audit_and_versions() -> None:
    """16 writers on one row, a receiver vetoing every odd note: vetoed
    sends write nothing, the rest land; seq gapless, version == rows."""
    from shop.models import Approval

    from xstate_statemachine.contrib.django.mixin import send_with_retry
    from xstate_statemachine.contrib.django.signals import (
        TransitionVetoed,
        pre_transition,
    )

    a = Approval.objects.create()

    def veto(sender: Any, event: Any, **kw: Any) -> None:
        if event.payload.get("n", 0) % 2:
            raise TransitionVetoed("odd")

    receipts: List[Any] = []

    def writer(n: int) -> Any:
        return lambda: receipts.append(
            send_with_retry(
                Approval.objects.get(pk=a.pk), "COMMENT", text=str(n), n=n
            )
        )

    pre_transition.connect(veto, weak=False)
    try:
        errors = _fleet([writer(n) for n in range(16)])
    finally:
        pre_transition.disconnect(veto)
    assert errors == []
    assert sum(r.denied for r in receipts) == 8
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.statechart_version == 8
    rows = list(fresh.history.all())
    assert [r.seq for r in rows] == list(range(1, 9))
    assert sorted(int(t) for t in fresh.machine.context["notes"]) == list(
        range(0, 16, 2)
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_idempotent_sends_apply_once(
    plugins_reset: Any,
) -> None:
    from shop.models import Approval

    plug = _idem()  # ONE plugin instance shared across threads
    Approval.statechart_plugins = lambda row: [plug]
    a = Approval.objects.create()
    out: List[Any] = []

    def go() -> None:
        out.append(
            Approval.objects.get(pk=a.pk).send(
                "COMMENT", text="once", idempotency_key="same"
            )
        )

    errors = _fleet([go] * 8)
    fresh = Approval.objects.get(pk=a.pk)
    assert fresh.machine.context["notes"] == ["once"], errors
    assert fresh.statechart_version == 1
    applied = [r for r in out if r.changed and not r.duplicate]
    assert len(applied) == 1
    # the losers: a duplicate replay, an in-flight refusal, or a retryable
    # lock/conflict error -- never a second application
    for e in errors:
        from xstate_statemachine.exceptions import (
            ConflictError,
            LockTimeoutError,
        )

        assert isinstance(e, (ConflictError, LockTimeoutError)), e


@pytest.mark.django_db(transaction=True)
def test_inbox_fifty_concurrent_claims_one_winner() -> None:
    from xstate_statemachine.contrib.django.inbox import DjangoInbox

    inbox = DjangoInbox()
    wins: List[bool] = []
    errors = _fleet(
        [lambda: wins.append(inbox.claim("s", "k", "fp", ttl_s=60))] * 50
    )
    assert errors == [] or all("lock" in str(e) for e in errors), errors
    assert wins.count(True) == 1


def test_inbox_ttl_purge_and_forget(db: Any) -> None:
    from xstate_statemachine.contrib.django.inbox import DjangoInbox

    inbox = DjangoInbox()
    assert inbox.claim("s1", "a", "fp", ttl_s=-1)  # already expired
    assert inbox.get("s1", "a") is None
    assert inbox.claim("s1", "a", "fp", ttl_s=60)  # expired one replaced
    assert not inbox.claim("s1", "a", "fp", ttl_s=60)
    inbox.mark("s1", "a", '{"r":1}', ttl_s=None)
    inbox.release("s1", "a")  # a marked key is not released
    assert inbox.get("s1", "a").receipt_json == '{"r":1}'
    assert inbox.claim("s2", "b", "fp", ttl_s=-1)
    assert inbox.purge_expired() == 1
    assert inbox.forget("s1") == 1 and inbox.get("s1", "a") is None


@pytest.mark.django_db(transaction=True)
def test_two_relays_at_once_never_double_mark() -> None:
    from xstate_statemachine.contrib.django.outbox import DjangoOutboxStore
    from xstate_statemachine.eda.fake import SyncFakeBrokerAdapter
    from xstate_statemachine.eda.outbox import OutboxRelay

    s = DjangoOutboxStore()
    for i in range(40):
        s.add("t", _env(i))
    marked: List[int] = []

    class Counting(DjangoOutboxStore):
        def mark_sent(self, seqs: Any) -> int:
            n = super().mark_sent(seqs)
            marked.append(n)
            return n

    broker = SyncFakeBrokerAdapter()
    relays = [OutboxRelay(Counting(), broker, batch=40) for _ in range(2)]
    errors = _fleet([r.relay_once_sync for r in relays])
    assert errors == [] or all("lock" in str(e) for e in errors), errors
    assert sum(marked) == 40  # each row marked exactly once overall
    assert s.count(pending_only=True) == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("lock", ["none", "optimistic", "pessimistic"])
def test_audit_seq_gapless_under_16_writers_every_lock_mode(lock: str) -> None:
    """The UPDATE takes the row lock before the audit flush reads
    ``Max(seq)``, so no lock mode can hit the (ct, object_id, seq)
    constraint as a raw IntegrityError."""
    from django.db import IntegrityError
    from shop.models import Approval

    from xstate_statemachine.contrib.django.mixin import send_with_retry

    a = Approval.objects.create()

    def go(n: int) -> Any:
        return lambda: send_with_retry(
            Approval.objects.get(pk=a.pk), "COMMENT", text=str(n), lock=lock
        )

    errors = _fleet([go(n) for n in range(16)])
    assert not [e for e in errors if isinstance(e, IntegrityError)], errors
    fresh = Approval.objects.get(pk=a.pk)
    seqs = [r.seq for r in fresh.history.all()]
    assert seqs == list(range(1, len(seqs) + 1))
    from xstate_statemachine.exceptions import ConflictError

    # 📝 optimistic: a retry budget can run out under a 16-way storm --
    #    a typed ConflictError, never a half-write (#280 decision).
    assert all(isinstance(e, ConflictError) for e in errors), errors
    if lock != "none":
        assert len(seqs) == 16 - len(errors) == fresh.statechart_version
    if lock == "pessimistic":
        assert errors == []


@pytest.mark.django_db(databases=["default", "other"])
@pytest.mark.skipif(PG, reason="the 'other' alias is SQLite-only")
def test_marker_store_on_another_alias_than_the_row_fails_loudly(
    plugins_reset: Any,
) -> None:
    """An outbox / inbox on alias X for a row written on alias Y is NOT
    in the send's transaction -- a rolled-back approval would keep its
    integration event. Refused, never silently non-atomic."""
    from shop.models import Approval

    from xstate_statemachine.contrib.django.outbox import DjangoOutboxStore
    from xstate_statemachine.exceptions import XStateMachineError

    a = Approval.objects.using("other").create()
    Approval.statechart_plugins = lambda row: [_outbox(DjangoOutboxStore())]
    with pytest.raises(XStateMachineError, match="other"):
        a.send("COMMENT", text="x")
    assert DjangoOutboxStore(using="other").count() == 0
    Approval.statechart_plugins = lambda row: [
        _outbox(DjangoOutboxStore(using=row._state.db))
    ]
    Approval.objects.using("other").get(pk=a.pk).send("COMMENT", text="x")
    Approval.statechart_plugins = lambda row: [_idem()]
    with pytest.raises(XStateMachineError, match="inbox"):
        Approval.objects.using("other").get(pk=a.pk).send(
            "COMMENT", text="y", idempotency_key="k"
        )
