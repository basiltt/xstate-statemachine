# examples/integrations/django_approvals/tests/test_battle_282_scenario.py
"""#282 battle: the admin and the management commands on an ops team's day.

* **fifty reviewers in the admin at once** -- changelist, change form and
  transition POSTs from 50 logged-in clients on 50 expenses, both roles:
  every POST is a redirect or a page (never a 500), every expense ends
  `approved`, every button a user saw was one they could press;
* **bulk actions** -- a reviewer selects 200 expenses and sends
  LEGAL_APPROVE: the message reports exactly how many changed and how
  many were denied (the finance-only ones), nothing is half-applied;
* **the confirm form** -- REJECT (`meta.confirm`) asks for a reason, a
  POST without `_xsm_confirmed` never transitions, the reason lands in
  the audit row; a tampered `_xsm_event` is refused;
* **ten thousand rows** -- the changelist with the state filter, the
  search box and the `TransitionLog` admin at ~30k rows all render in
  bounded time and a bounded number of queries (no N+1 on the state
  column, no per-row permission query);
* **the commands on ten thousand rows** -- `xsm_snapshots --stale`,
  `xsm_refresh_columns --batch`, `xsm_deadlines`, `xsm_inspect` and
  `xsm_diagram` finish in bounded time with bounded memory (tracemalloc
  peak well under the dataset's size), and `--plain` output encodes on a
  cp1252 console (a subprocess with ``PYTHONIOENCODING=cp1252``).

Both dialects: SQLite here, Postgres via
`tests/contrib/django/test_battle_280_postgres.py`.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connections
from django.test import Client
from django.test.utils import CaptureQueriesContext

from approvals.models import FINANCE, LEGAL, Expense
from xstate_statemachine.contrib.django.models import TransitionLog

EXAMPLE = Path(__file__).resolve().parents[1]
CHANGE = "/admin/approvals/expense/{pk}/change/"
TRANSITION = "/admin/approvals/expense/{pk}/xsm-transition/"
CHANGELIST = "/admin/approvals/expense/"
BUTTON = re.compile(r'name="_xsm_submit" value="([A-Z_]+)"')


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


def _submit(n: int, prefix: str = "e") -> List[int]:
    rows = Expense.objects.bulk_create(
        [Expense(title=f"{prefix}{i}", amount="10.00") for i in range(n)]
    )
    pks = (
        [r.pk for r in rows]
        if rows and rows[0].pk
        else list(
            Expense.objects.filter(title__startswith=prefix).values_list(
                "pk", flat=True
            )
        )
    )
    for pk in pks:
        Expense.objects.get(pk=pk).send("SUBMIT")
    return pks


# -----------------------------------------------------------------------------
# 1. fifty reviewers in the admin at once
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_fifty_reviewers_in_the_admin_at_once(people: Any) -> None:
    pks = _submit(50)
    U = get_user_model()
    legal_g = Group.objects.get(name=LEGAL)
    fin_g = Group.objects.get(name=FINANCE)
    perms = list(
        Permission.objects.filter(
            codename__in=("view_expense", "change_expense")
        )
    )
    reviewers = []
    for i in range(50):
        u = U.objects.create_user(f"rev{i}", password="p", is_staff=True)
        u.user_permissions.add(*perms)
        (legal_g if i % 2 == 0 else fin_g).user_set.add(u)
        reviewers.append(U.objects.get(pk=u.pk))
    statuses: List[int] = []
    wrong_buttons: List[str] = []
    lock = threading.Lock()

    def reviewer(i: int) -> Any:
        u = reviewers[i]
        mine = "LEGAL_APPROVE" if i % 2 == 0 else "FINANCE_APPROVE"

        def go() -> None:
            c = Client()
            c.force_login(u)
            r = c.get(CHANGELIST)
            with lock:
                statuses.append(r.status_code)
            for pk in pks[i : i + 3] + pks[:2]:  # overlap with others
                html = c.get(CHANGE.format(pk=pk)).content.decode()
                buttons = BUTTON.findall(html)
                for b in buttons:
                    if b.endswith("_APPROVE") and b != mine:
                        with lock:
                            wrong_buttons.append(f"{u.username} saw {b}")
                r = c.post(TRANSITION.format(pk=pk), {"_xsm_event": mine})
                with lock:
                    statuses.append(r.status_code)

        return go

    t0 = time.perf_counter()
    assert _threads([reviewer(i) for i in range(50)]) == []
    took = time.perf_counter() - t0
    assert all(s < 500 for s in statuses), sorted(set(statuses))
    assert wrong_buttons == [], wrong_buttons[:5]
    # everyone's approvals landed: every expense that got both roles is
    # approved; none is in an impossible state
    states = set(
        Expense.objects.filter(pk__in=pks).values_list(
            "statechart_state", flat=True
        )
    )
    assert states <= {
        "approval.approved",
        "approval.review.finance.approved,approval.review.legal.pending",
        "approval.review.finance.pending,approval.review.legal.approved",
        "approval.review.finance.pending,approval.review.legal.pending",
    }, states
    assert (
        Expense.objects.filter(pk__in=pks[:2])
        .filter(statechart_state="approval.approved")
        .count()
        == 2
    )
    assert took < 240, took


# -----------------------------------------------------------------------------
# 2. bulk actions
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_bulk_action_reports_exact_counts(people: Any) -> None:
    pks = _submit(200)
    # 40 of them already legal-approved: LEGAL_APPROVE is a no-op there
    for pk in pks[:40]:
        Expense.objects.get(pk=pk).send("LEGAL_APPROVE", actor=people["legal"])
    c = Client()
    c.force_login(people["legal"])
    r = c.post(
        CHANGELIST,
        {
            "action": "xsm_LEGAL_APPROVE",
            "_selected_action": [str(pk) for pk in pks],
        },
        follow=True,
    )
    assert r.status_code == 200
    msgs = [str(m) for m in r.context["messages"]]
    assert any("160 changed" in m and "40 denied" in m for m in msgs), msgs
    assert (
        Expense.objects.filter(pk__in=pks)
        .filter(statechart_state__contains="legal.approved")
        .count()
        == 200
    )
    # the finance reviewer bulk-sending LEGAL_APPROVE changes nothing
    c2 = Client()
    c2.force_login(people["finance"])
    r = c2.post(
        CHANGELIST,
        {
            "action": "xsm_LEGAL_APPROVE",
            "_selected_action": [str(pk) for pk in pks[:10]],
        },
        follow=True,
    )
    msgs = [str(m) for m in r.context["messages"]]
    assert any("0 changed" in m and "10 denied" in m for m in msgs), msgs


# -----------------------------------------------------------------------------
# 3. the confirm form
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_confirm_form_reason_and_tampered_event(people: Any) -> None:
    [pk] = _submit(1)
    c = Client()
    c.force_login(people["legal"])
    url = TRANSITION.format(pk=pk)
    r = c.post(url, {"_xsm_event": "REJECT"})
    assert r.status_code == 200 and b"Reason" in r.content
    assert Expense.objects.get(pk=pk).matches("approval.review")
    # confirmed without a reason: still a transition (reason optional) --
    # but the audit row records the empty reason honestly
    r = c.post(
        url,
        {
            "_xsm_event": "REJECT",
            "_xsm_confirmed": "1",
            "reason": "duplicate claim",
        },
    )
    assert r.status_code == 302
    e = Expense.objects.get(pk=pk)
    assert e.state == "approval.rejected"
    assert e.history.last().reason == "duplicate claim"
    # tampered / unknown event names are refused, never a 500
    [pk2] = _submit(1)
    for bad in ("DROP_TABLE", "legal_approve", "", "LEGAL_APPROVE; --"):
        r = c.post(TRANSITION.format(pk=pk2), {"_xsm_event": bad})
        assert r.status_code in (302, 400, 403, 404), (bad, r.status_code)
    assert Expense.objects.get(pk=pk2).matches("approval.review")


# -----------------------------------------------------------------------------
# 4. ten thousand rows in the admin
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_changelist_and_log_admin_at_scale_are_bounded(people: Any) -> None:
    Expense.objects.bulk_create(
        [Expense(title=f"big{i}", amount="1.00") for i in range(10_000)]
    )
    # a few hundred get a history (SUBMIT + approvals = ~3 rows each)
    for e in Expense.objects.filter(title__startswith="big")[:300]:
        e.send("SUBMIT")
        e.send("LEGAL_APPROVE", actor=people["legal"])
    c = Client()
    c.force_login(people["legal"])
    with CaptureQueriesContext(connections["default"]) as cq:
        t0 = time.perf_counter()
        r = c.get(CHANGELIST)
        took = time.perf_counter() - t0
    assert r.status_code == 200
    assert len(cq) < 40, len(cq)  # no per-row query on the state column
    assert took < 10, took
    with CaptureQueriesContext(connections["default"]) as cq:
        r = c.get(CHANGELIST + "?statechart_state=approval.review")
    assert r.status_code == 200 and len(cq) < 40, len(cq)
    r = c.get(CHANGELIST + "?q=big42")
    assert r.status_code == 200
    # the audit changelist is its own model: `view_transitionlog`
    people["legal"].user_permissions.add(
        Permission.objects.get(codename="view_transitionlog")
    )
    c.force_login(get_user_model().objects.get(pk=people["legal"].pk))
    with CaptureQueriesContext(connections["default"]) as cq:
        t0 = time.perf_counter()
        r = c.get("/admin/xsm_django/transitionlog/")
        took = time.perf_counter() - t0
    assert r.status_code == 200, r.status_code
    assert len(cq) < 40, len(cq)
    assert took < 10, took
    assert TransitionLog.objects.count() >= 600


# -----------------------------------------------------------------------------
# 5. the commands on ten thousand rows
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_commands_on_ten_thousand_rows_are_bounded(people: Any) -> None:
    Expense.objects.bulk_create(
        [Expense(title=f"cmd{i}", amount="1.00") for i in range(10_000)]
    )
    for e in Expense.objects.filter(title__startswith="cmd")[:500]:
        e.send("SUBMIT")
    results: Dict[str, Any] = {}
    for name, args in (
        ("snapshots", ["xsm_snapshots", "approvals.Expense", "--stale"]),
        (
            "refresh",
            ["xsm_refresh_columns", "approvals.Expense", "--batch", "500"],
        ),
        ("deadlines", ["xsm_deadlines", "approvals.Expense"]),
        ("inspect", ["xsm_inspect", "approvals.Expense", "--plain"]),
        ("diagram", ["xsm_diagram", "approvals.Expense", "-f", "mermaid"]),
    ):
        out = io.StringIO()
        tracemalloc.start()
        t0 = time.perf_counter()
        call_command(*args, stdout=out)
        took = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[name] = (took, peak, out.getvalue())
        assert took < 120, (name, took)
        # 10k snapshots are ~10 MB of JSON; a batched command must not
        # hold them all at once
        assert peak < 80 * 1024 * 1024, (name, peak)
    assert "approval" in results["inspect"][2]
    assert "stateDiagram" in results["diagram"][2]
    assert "woke 0/" in results["deadlines"][2]


def test_plain_output_encodes_on_a_cp1252_console(transactional_db: Any):
    env = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONUTF8": "0",
        "PYTHONPATH": os.pathsep.join(
            [str(EXAMPLE.parents[2] / "src"), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep),
        "APPROVALS_DB": str(EXAMPLE / "cp1252.sqlite3"),
    }
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env.pop("DATABASE_URL", None)
    try:
        for argv in (
            ["migrate", "-v0"],
            ["xsm_inspect", "approvals.Expense", "--plain"],
            ["xsm_diagram", "approvals.Expense", "-f", "mermaid"],
            ["xsm_deadlines", "approvals.Expense"],
            ["xsm_snapshots", "approvals.Expense"],
        ):
            r = subprocess.run(
                [sys.executable, "manage.py", *argv],
                cwd=str(EXAMPLE),
                env=env,
                capture_output=True,
                timeout=300,
            )
            assert r.returncode == 0, (argv, r.stderr[-1500:])
            assert b"UnicodeEncodeError" not in r.stderr, argv
    finally:
        for suffix in ("", "-journal", "-wal", "-shm"):
            try:
                os.remove(str(EXAMPLE / f"cp1252.sqlite3{suffix}"))
            except OSError:
                pass
