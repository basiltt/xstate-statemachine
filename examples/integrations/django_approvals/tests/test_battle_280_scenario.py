# examples/integrations/django_approvals/tests/test_battle_280_scenario.py
"""#280 battle: the approvals app under the load a finance team puts on it.

* **two hundred expenses, both roles racing** -- legal and finance
  approve every expense from separate threads (per-thread connections,
  `select_for_update` under the default pessimistic lock): every expense
  ends `approved`, nothing lost, no raw driver error, in bounded time;
* **a double-click** -- 16 threads re-sending LEGAL_APPROVE on ONE
  expense: exactly one transition, the rest are no-ops (never a 500 in
  the admin, never a corrupted parallel configuration);
* **optimistic mode on the same fleet** with `send_with_retry`;
* **rollback is total** -- an action that raises mid-transaction rolls
  back the snapshot, the denormalised columns, the deadline row AND the
  audit row (`actionErrorPolicy: rollback`); a `post_transition(
  on_commit=True)` receiver never fires for a rolled-back send;
* **the 48 h escalation at scale** -- 200 expenses in review; the
  `xsm_deadlines` command (two concurrent runs) wakes each exactly once;
  an approved expense's deadline is gone;
* **migrations from scratch** -- `migrate` on an empty database, then
  `makemigrations --check` is clean (X0.10); `xsm_inspect`;
* **the admin under concurrency** -- two reviewers' browsers posting the
  transition form at once;
* **Postgres** -- the same on a real server when `DATABASE_URL` is set
  (`tests/contrib/django/test_battle_280_postgres.py` drives this module
  in a subprocess against a testcontainer when ``XSM_CONTAINERS=1``).
"""

from __future__ import annotations

import io
import re
import threading
import time
from typing import Any, Dict, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connections
from django.test import Client

from approvals.models import FINANCE, LEGAL, Expense
from xstate_statemachine.contrib.django import post_transition
from xstate_statemachine.contrib.django.mixin import send_with_retry
from xstate_statemachine.contrib.django.models import StatechartDeadline
from xstate_statemachine.exceptions import LockTimeoutError

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


# -----------------------------------------------------------------------------
# 1. two hundred expenses, both roles racing
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mode", ["pessimistic", "optimistic"])
def test_both_roles_race_on_two_hundred_expenses(people: Any, mode: str):
    pks = [
        Expense.objects.create(title=f"e{i}", amount="10.00").pk
        for i in range(N)
    ]
    for pk in pks:
        Expense.objects.get(pk=pk).send("SUBMIT")

    timeouts = [0]

    def approve(role: str, event: str) -> Any:
        def go() -> None:
            for pk in pks:
                for _ in range(50):
                    row = Expense.objects.get(pk=pk)
                    try:
                        if mode == "pessimistic":
                            row.send(event, actor=people[role])
                        else:
                            send_with_retry(
                                row,
                                event,
                                actor=people[role],
                                lock="optimistic",
                            )
                        break
                    except LockTimeoutError:
                        # 📝 SQLite: a writer waited out busy_timeout -- the
                        #    documented retryable signal (never a raw
                        #    driver OperationalError); retry the row
                        timeouts[0] += 1
                else:
                    raise AssertionError("50 consecutive lock timeouts")

        return go

    t0 = time.perf_counter()
    errors = _threads(
        [
            approve("legal", "LEGAL_APPROVE"),
            approve("finance", "FINANCE_APPROVE"),
            approve("legal", "LEGAL_APPROVE"),  # a second legal reviewer
        ]
    )
    took = time.perf_counter() - t0
    assert errors == [], errors[:3]
    states = list(
        Expense.objects.filter(pk__in=pks).values_list(
            "statechart_state", flat=True
        )
    )
    assert states.count("approval.approved") == N, (
        {s: states.count(s) for s in set(states)},
    )
    assert Expense.objects.in_state("approval.approved").count() == N
    assert StatechartDeadline.objects.count() == 0  # review left: no timer
    assert took < 300, took


# -----------------------------------------------------------------------------
# 2. a double-click on one expense
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_sixteen_simultaneous_identical_approvals_apply_once(people: Any):
    e = Expense.objects.create(title="dup", amount="1.00")
    e.send("SUBMIT")
    changed: List[bool] = []
    lock = threading.Lock()

    def click() -> None:
        r = Expense.objects.get(pk=e.pk).send(
            "LEGAL_APPROVE", actor=people["legal"]
        )
        with lock:
            changed.append(r.changed)

    assert _threads([click] * 16) == []
    assert changed.count(True) == 1 and changed.count(False) == 15
    e.refresh_from_db()
    assert e.matches("approval.review.legal.approved")
    assert e.matches("approval.review.finance.pending")
    # the audit keeps the 15 "unhandled" re-sends too (that IS the record
    # of a double-click); exactly ONE row is a transition for the event
    rows = list(e.history.filter(event="LEGAL_APPROVE"))
    assert sum(1 for r in rows if r.disposition == "transition") == 1
    assert sum(1 for r in rows if r.disposition == "unhandled") == 15


# -----------------------------------------------------------------------------
# 3. rollback is total
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_rollback_leaves_no_row_column_deadline_or_signal(people: Any):
    e = Expense.objects.create(title="boom", amount="1.00")
    e.send("SUBMIT")
    before = {
        "state": Expense.objects.get(pk=e.pk).statechart_state,
        "version": Expense.objects.get(pk=e.pk).statechart_version,
        "deadlines": StatechartDeadline.objects.count(),
        "history": e.history.count(),
    }
    fired: List[Any] = []

    def receiver(sender: Any, **kw: Any) -> None:
        fired.append(kw.get("event"))

    post_transition.connect(receiver, on_commit=True, weak=False)
    try:
        # the realistic shape: a view does more work after `send()` inside
        # ITS OWN atomic block and that work fails -- the send must roll
        # back with it (same transaction), and the on_commit receiver must
        # never fire for a state that was not kept
        with pytest.raises(RuntimeError, match="after send"):
            _send_then_fail(Expense.objects.get(pk=e.pk), people["legal"])
    finally:
        post_transition.disconnect(receiver)
    after = Expense.objects.get(pk=e.pk)
    assert after.statechart_state == before["state"]
    assert after.statechart_version == before["version"]
    assert StatechartDeadline.objects.count() == before["deadlines"]
    assert after.history.count() == before["history"]
    assert fired == [], fired


def _send_then_fail(row: Any, actor: Any) -> None:
    from django.db import transaction

    with transaction.atomic():
        row.send("LEGAL_APPROVE", actor=actor)
        raise RuntimeError("the view failed after send()")


# -----------------------------------------------------------------------------
# 4. the 48 h escalation at scale
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_escalation_wakes_each_expense_once_with_two_scanners(people: Any):
    pks = [
        Expense.objects.create(title=f"w{i}", amount="5.00").pk
        for i in range(N)
    ]
    for pk in pks:
        Expense.objects.get(pk=pk).send("SUBMIT")
    # approve a quarter fully: their deadline rows must be gone
    for pk in pks[::4]:
        r = Expense.objects.get(pk=pk)
        r.send("LEGAL_APPROVE", actor=people["legal"])
        Expense.objects.get(pk=pk).send(
            "FINANCE_APPROVE", actor=people["finance"]
        )
    assert StatechartDeadline.objects.count() == N - N // 4
    later = time.time() + 49 * 3600
    outs = [io.StringIO(), io.StringIO()]

    def scan(out: io.StringIO) -> Any:
        return lambda: call_command(
            "xsm_deadlines", "approvals.Expense", now=later, stdout=out
        )

    t0 = time.perf_counter()
    assert _threads([scan(outs[0]), scan(outs[1])]) == []
    took = time.perf_counter() - t0
    woke = sum(
        int(m.group(1))
        for o in outs
        for m in [re.search(r"woke (\d+)/", o.getvalue())]
        if m
    )
    assert woke == N - N // 4, [o.getvalue()[-200:] for o in outs]
    escalated = sum(
        1
        for e in Expense.objects.filter(pk__in=pks)
        if e.machine.context.get("escalated")
    )
    assert escalated == N - N // 4
    assert StatechartDeadline.objects.count() == 0
    assert took < 300, took
    out = io.StringIO()
    call_command("xsm_deadlines", "approvals.Expense", now=later, stdout=out)
    assert "woke 0/0" in out.getvalue()


# -----------------------------------------------------------------------------
# 5. migrations from scratch; xsm_inspect
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_makemigrations_check_is_clean_and_inspect_runs() -> None:
    call_command("makemigrations", "approvals", "--check", "--dry-run")
    out = io.StringIO()
    call_command("xsm_inspect", "approvals.Expense", "--plain", stdout=out)
    text = out.getvalue()
    for name in ("draft", "review", "legal", "finance", "approved"):
        assert name in text


# -----------------------------------------------------------------------------
# 6. the admin under concurrency
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_two_reviewers_post_the_admin_form_at_once(people: Any) -> None:
    e = Expense.objects.create(title="Chair", amount="80.00")
    e.send("SUBMIT")
    url = f"/admin/approvals/expense/{e.pk}/xsm-transition/"
    statuses: List[int] = []
    lock = threading.Lock()

    def post(role: str, event: str) -> Any:
        def go() -> None:
            c = Client()
            c.force_login(people[role])
            for _ in range(5):  # a jittery double-click
                r = c.post(url, {"_xsm_event": event})
                with lock:
                    statuses.append(r.status_code)

        return go

    assert (
        _threads(
            [
                post("legal", "LEGAL_APPROVE"),
                post("finance", "FINANCE_APPROVE"),
            ]
        )
        == []
    )
    assert all(s < 500 for s in statuses), sorted(set(statuses))
    e.refresh_from_db()
    assert e.state == "approval.approved", e.state
    # SUBMIT + one transition per role (+ the engine's done.state row);
    # the other 8 posts are "unhandled" audit rows, never a second apply
    kinds = [
        (r.event, r.disposition)
        for r in e.history.all()
        if r.disposition == "transition"
    ]
    assert sorted(kinds) == sorted(
        [
            ("SUBMIT", "transition"),
            ("LEGAL_APPROVE", "transition"),
            ("FINANCE_APPROVE", "transition"),
            ("done.state.approval.review", "transition"),
        ]
    ), kinds
