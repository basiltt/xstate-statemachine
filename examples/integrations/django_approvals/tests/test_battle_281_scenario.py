# examples/integrations/django_approvals/tests/test_battle_281_scenario.py
"""#281 battle: signals, audit, permissions and the outbox -- as an audit
team and an integration team actually lean on them.

* **the audit trail under load** -- 200 expenses approved by two roles
  from separate connections: every row's `TransitionLog` has a gapless
  `seq`, carries the actor and the reason, refused attempts included,
  and the trail never disagrees with the state (`to_states` of the last
  transition row == the row's columns);
* **a veto is nothing** -- a `pre_transition` receiver raising
  `TransitionVetoed` gives `denied`, no state change, no audit row, no
  outbox row, no `post_transition`;
* **receivers that raise** -- an in-transaction `post_transition`
  receiver that raises rolls the send back entirely; an
  `on_commit=True` receiver that raises leaves the committed send in
  place and the error surfaces to the caller (never swallowed);
* **permissions at scale** -- 1000 users, each in one of the two
  groups: `permitted_events` for each is right, `available_events_for`
  costs a bounded number of queries per user, and no user ever gets an
  event their role forbids under concurrency;
* **the outbox is transactional WITH the approval** -- `approved`
  (tagged `publish`) writes exactly one row in the send's transaction; a
  rolled-back approval writes none; a relay that crashes between
  publish and mark re-sends the SAME envelope id (at-least-once);
* **forget is X0.5** -- `forget_statechart()` redacts payload / actor in
  the audit rows (append-only chain kept), clears deadlines and the
  snapshot.

Both dialects: SQLite here, Postgres via
`tests/contrib/django/test_battle_280_postgres.py`.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connections, transaction
from django.test.utils import CaptureQueriesContext

from approvals.models import FINANCE, LEGAL, Expense
from xstate_statemachine.contrib.django import (
    DjangoOutboxStore,
    TransitionVetoed,
    permitted_events,
    post_transition,
    pre_transition,
)
from xstate_statemachine.contrib.django.models import StatechartDeadline
from xstate_statemachine.eda import Envelope, OutboxRelay

N = 200


def _user(name: str, group: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(name, password="p", is_staff=True)
    for codename in ("view_expense", "change_expense"):
        u.user_permissions.add(Permission.objects.get(codename=codename))
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return U.objects.get(pk=u.pk)


@pytest.fixture
def people(transactional_db: Any) -> Dict[str, Any]:
    return {"legal": _user("lena", LEGAL), "finance": _user("fin", FINANCE)}


def _threads(fns: List[Any]) -> List[str]:
    errors: List[str] = []
    lock = threading.Lock()

    def run(fn: Any) -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - reported
            with lock:
                errors.append(repr(exc)[:200])
        finally:
            connections.close_all()

    ts = [threading.Thread(target=run, args=(fn,)) for fn in fns]
    for t in ts:
        t.start()
    for t in ts:
        t.join(600)
    return errors


def _submit(n: int) -> List[int]:
    pks = [
        Expense.objects.create(title=f"e{i}", amount="10.00").pk
        for i in range(n)
    ]
    for pk in pks:
        Expense.objects.get(pk=pk).send("SUBMIT", reason="filed")
    return pks


# -----------------------------------------------------------------------------
# 1. the audit trail under load
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_audit_trail_is_gapless_attributed_and_agrees_with_state(
    people: Any,
) -> None:
    pks = _submit(N)

    def approve(role: str, event: str, reason: str) -> Any:
        def go() -> None:
            for pk in pks:
                Expense.objects.get(pk=pk).send(
                    event, actor=people[role], reason=reason
                )

        return go

    # the finance reviewer also tries LEGAL_APPROVE on every row: refused,
    # and the refusal is on the record
    assert (
        _threads(
            [
                approve("legal", "LEGAL_APPROVE", "looks fine"),
                approve("finance", "FINANCE_APPROVE", "within budget"),
                approve("finance", "LEGAL_APPROVE", "not my call"),
            ]
        )
        == []
    )
    for pk in pks:
        e = Expense.objects.get(pk=pk)
        rows = list(e.history.all())
        seqs = [r.seq for r in rows]
        assert seqs == list(range(1, len(rows) + 1)), (pk, seqs)
        by_event = {(r.event, r.disposition): r for r in rows}
        legal = by_event[("LEGAL_APPROVE", "transition")]
        assert legal.actor_id == people["legal"].pk
        assert legal.reason == "looks fine"
        # the finance user's LEGAL_APPROVE is "denied" by the role guard
        # when legal has not acted yet, "unhandled" once the region has
        # left `pending` -- either way it is ON THE RECORD with its actor
        refused = [
            r
            for r in rows
            if r.event == "LEGAL_APPROVE" and r.disposition != "transition"
        ]
        assert len(refused) == 1, [(r.event, r.disposition) for r in rows]
        assert refused[0].disposition in ("denied", "unhandled")
        assert refused[0].actor_id == people["finance"].pk
        assert refused[0].reason == "not my call"
        last = [r for r in rows if r.disposition == "transition"][-1]
        assert sorted(last.to_states) == sorted(e.statechart_state_ids)
        assert e.state == "approval.approved"


# -----------------------------------------------------------------------------
# 2. a veto is nothing
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_pre_transition_veto_writes_nothing(people: Any) -> None:
    [pk] = _submit(1)
    e = Expense.objects.get(pk=pk)
    before = (e.statechart_version, e.history.count(), _outbox().count())
    fired: List[str] = []

    def veto(sender: Any, instance: Any, event: Any, **kw: Any) -> None:
        if event.type == "LEGAL_APPROVE":
            raise TransitionVetoed("legal hold")

    def after(sender: Any, **kw: Any) -> None:
        fired.append(kw["event"].type)

    pre_transition.connect(veto, weak=False)
    post_transition.connect(after, weak=False)
    try:
        r = e.send("LEGAL_APPROVE", actor=people["legal"])
    finally:
        pre_transition.disconnect(veto)
        post_transition.disconnect(after)
    assert r.denied and not r.changed
    e.refresh_from_db()
    assert e.matches("approval.review.legal.pending")
    assert (e.statechart_version, e.history.count(), _outbox().count()) == (
        before
    ), "a vetoed send left something behind"
    assert fired == []


# -----------------------------------------------------------------------------
# 3. receivers that raise
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_in_transaction_receiver_rolls_back_and_on_commit_one_surfaces(
    people: Any,
) -> None:
    [pk] = _submit(1)
    e = Expense.objects.get(pk=pk)
    v0 = e.statechart_version

    def boom(sender: Any, **kw: Any) -> None:
        raise RuntimeError("downstream exploded")

    # in-transaction receiver: the whole send rolls back
    post_transition.connect(boom, weak=False)
    try:
        with pytest.raises(RuntimeError, match="downstream"):
            e.send("LEGAL_APPROVE", actor=people["legal"])
    finally:
        post_transition.disconnect(boom)
    e = Expense.objects.get(pk=pk)
    assert e.statechart_version == v0
    assert e.matches("approval.review.legal.pending")
    assert e.history.filter(event="LEGAL_APPROVE").count() == 0
    # on_commit receiver: the send is KEPT, the error reaches the caller
    post_transition.connect(boom, on_commit=True, weak=False)
    try:
        with pytest.raises(RuntimeError, match="downstream"):
            e.send("LEGAL_APPROVE", actor=people["legal"])
    finally:
        post_transition.disconnect(boom)
    e = Expense.objects.get(pk=pk)
    assert e.matches("approval.review.legal.approved")
    assert e.statechart_version == v0 + 1
    assert (
        e.history.filter(
            event="LEGAL_APPROVE", disposition="transition"
        ).count()
        == 1
    )


# -----------------------------------------------------------------------------
# 4. permissions at scale
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_thousand_users_get_exactly_their_roles_events(people: Any) -> None:
    [pk] = _submit(1)
    e = Expense.objects.get(pk=pk)
    U = get_user_model()
    legal_g = Group.objects.get(name=LEGAL)
    fin_g = Group.objects.get(name=FINANCE)
    users = U.objects.bulk_create(
        [U(username=f"u{i}", is_staff=True) for i in range(1000)]
    )
    users = list(U.objects.filter(username__startswith="u").order_by("pk"))
    legal_g.user_set.add(*users[::2])
    fin_g.user_set.add(*users[1::2])
    want_legal = ["LEGAL_APPROVE", "REJECT"]
    want_fin = ["FINANCE_APPROVE", "REJECT"]
    t0 = time.perf_counter()
    for i, u in enumerate(users):
        got = sorted(permitted_events(u, e))
        assert got == sorted(want_legal if i % 2 == 0 else want_fin), (i, got)
    took = time.perf_counter() - t0
    assert took < 120, took
    # bounded cost: one user's permitted events is a handful of queries
    with CaptureQueriesContext(connections["default"]) as cq:
        permitted_events(users[0], e)
    assert len(cq) <= 12, len(cq)
    # concurrency: 100 users (50 per role) all try BOTH approvals at once
    # on fresh expenses -- no user ever lands an event their role forbids
    pks = _submit(50)
    bad: List[str] = []
    lock = threading.Lock()

    def attempt(u: Any, pk: int) -> Any:
        def go() -> None:
            row = Expense.objects.get(pk=pk)
            for ev in ("LEGAL_APPROVE", "FINANCE_APPROVE"):
                r = row.send(ev, actor=u)
                is_legal = u.groups.filter(name=LEGAL).exists()
                allowed = (ev == "LEGAL_APPROVE") == is_legal
                if r.changed and not allowed:
                    with lock:
                        bad.append(f"{u.username} did {ev}")
                row = Expense.objects.get(pk=pk)

        return go

    # row k gets one legal user (even index) and one finance user (odd)
    fns = [attempt(users[2 * k], pks[k]) for k in range(50)]
    fns += [attempt(users[2 * k + 1], pks[k]) for k in range(50)]
    assert _threads(fns) == []
    assert bad == [], bad[:5]
    assert (
        Expense.objects.filter(pk__in=pks)
        .filter(statechart_state="approval.approved")
        .count()
        == 50
    )


# -----------------------------------------------------------------------------
# 5. the outbox is transactional WITH the approval
# -----------------------------------------------------------------------------
def _outbox() -> DjangoOutboxStore:
    return DjangoOutboxStore()


@pytest.mark.django_db(transaction=True)
def test_outbox_row_commits_with_the_approval_and_relay_is_at_least_once(
    people: Any,
) -> None:
    outbox = _outbox()
    [pk] = _submit(1)
    e = Expense.objects.get(pk=pk)
    e.send("LEGAL_APPROVE", actor=people["legal"])
    assert outbox.count() == 0  # not approved yet
    # a view that fails AFTER the final approval in its own atomic block:
    # the approval AND its outbox row roll back together
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            Expense.objects.get(pk=pk).send(
                "FINANCE_APPROVE", actor=people["finance"]
            )
            assert outbox.count() == 1  # visible inside the transaction
            raise RuntimeError("view failed after send()")
    assert outbox.count() == 0, "outbox row survived the rollback"
    assert Expense.objects.get(pk=pk).matches(
        "approval.review.finance.pending"
    )
    # commit it: exactly one row
    Expense.objects.get(pk=pk).send("FINANCE_APPROVE", actor=people["finance"])
    [rec] = outbox.pending()
    assert rec.topic == "approvals"
    assert rec.envelope.type.endswith("approved")
    first_id = rec.envelope.id
    # a second approved expense, then a relay that crashes mid-batch
    [pk2] = _submit(1)
    Expense.objects.get(pk=pk2).send("LEGAL_APPROVE", actor=people["legal"])
    Expense.objects.get(pk=pk2).send(
        "FINANCE_APPROVE", actor=people["finance"]
    )
    assert outbox.count(pending_only=True) == 2

    class CrashyBroker:
        def __init__(self) -> None:
            self.published: List[Envelope] = []

        def publish(self, topic: str, env: Envelope) -> None:
            self.published.append(env)
            if len(self.published) == 2:
                raise ConnectionError("broker went away")

    broker = CrashyBroker()
    with pytest.raises(ConnectionError):
        OutboxRelay(outbox, broker).relay_once_sync()
    assert outbox.count(pending_only=True) == 1  # the acked one is marked
    [again] = outbox.pending()
    assert again.envelope.id != first_id
    assert OutboxRelay(outbox, broker).relay_once_sync() == 1
    ids = [x.id for x in broker.published]
    assert len(ids) == 3 and len(set(ids)) == 2  # one dup, same id


# -----------------------------------------------------------------------------
# 6. forget is X0.5
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_forget_redacts_audit_and_clears_deadlines(people: Any) -> None:
    [pk] = _submit(1)
    e = Expense.objects.get(pk=pk)
    e.send("LEGAL_APPROVE", actor=people["legal"], reason="secret reason")
    assert StatechartDeadline.objects.count() == 1
    n_rows = e.history.count()
    counts = e.forget_statechart()
    assert counts["deadlines"] == 1
    e.refresh_from_db()
    assert e.statechart is None and e.state is None
    assert StatechartDeadline.objects.count() == 0
    rows = list(e.history.all())
    assert len(rows) == n_rows  # append-only chain kept (redact mode)
    assert [r.seq for r in rows] == list(range(1, n_rows + 1))
    for r in rows:
        assert r.actor_id is None, r
        assert "secret reason" not in (r.reason or "")
        assert "secret" not in str(r.payload)


# -----------------------------------------------------------------------------
# 7. a failing outbox write fails the send (not a swallowed log line)
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_failing_outbox_write_rolls_the_approval_back(people: Any) -> None:
    """🔥 before the fix the outbox INSERT ran inside the engine's plugin
    containment: its failure was LOGGED and the approval committed without
    its integration event -- the worst outcome for an outbox."""
    [pk] = _submit(1)
    Expense.objects.get(pk=pk).send("LEGAL_APPROVE", actor=people["legal"])
    real = DjangoOutboxStore.add

    def broken(self: Any, topic: str, env: Envelope) -> None:
        raise RuntimeError("outbox table unavailable")

    DjangoOutboxStore.add = broken  # type: ignore[method-assign]
    try:
        with pytest.raises(RuntimeError, match="outbox table"):
            Expense.objects.get(pk=pk).send(
                "FINANCE_APPROVE", actor=people["finance"]
            )
    finally:
        DjangoOutboxStore.add = real  # type: ignore[method-assign]
    e = Expense.objects.get(pk=pk)
    assert e.matches("approval.review.finance.pending"), e.state
    assert (
        e.history.filter(
            event="FINANCE_APPROVE", disposition="transition"
        ).count()
        == 0
    )
    assert _outbox().count() == 0
