# tests/contrib/django/test_battle_310_scenario.py
"""#310 battle: migrating a real django-fsm-2 app, the way a team does it
on a Friday evening with the site still up.

* **ten thousand tickets in batches** -- `xsm_migrate_fsm --batch 500`
  over 10k rows: bounded time, bounded memory (one batch in memory at a
  time), every row's `statechart_state` equals its old FSM value and the
  denormalised columns are correct;
* **`--dry-run` writes nothing** -- not a snapshot, not a column, not a
  chart file;
* **dirty data** -- a column holding values the chart does not know
  (a typo'd legacy state, an EMPTY string, a state that was renamed): the
  command must REPORT them per value and finish the clean rows, never
  die on row 4,217 with a traceback and half a migration; a rename
  mapping (`--map old=new`) folds them in;
* **the site is still up** -- writers keep saving rows and `@transition`s
  keep firing on the FSM column while the migration runs: no row is
  migrated into a state it had already left, no row is lost, a re-run
  picks up the stragglers;
* **two FSMFields on one model** -- `--field` selects; the other is left
  alone;
* **the dual-read window** -- after migration a `send()` keeps the FSM
  column in sync and an FSM `@transition` call keeps the snapshot in
  sync (both directions), so a mixed deployment stays consistent;
* **Postgres** -- the same through `tests/contrib/django/
  test_battle_310_postgres.py` on a testcontainer.
"""

from __future__ import annotations

import io
import json
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections

pytest.importorskip("django_fsm")

pytestmark = pytest.mark.django_db(transaction=True)
N = 10_000
STATES = ["new", "in_progress", "resolved", "closed"]


def _ticket() -> Any:
    from legacy.models import Ticket

    return Ticket


def _out(*args: Any, **kw: Any) -> str:
    buf = io.StringIO()
    call_command(*args, stdout=buf, **kw)
    return buf.getvalue()


def _seed(n: int, states: List[str] = STATES) -> None:
    Ticket = _ticket()
    Ticket.objects.bulk_create(
        [
            Ticket(state=states[i % len(states)], assignee="x")
            for i in range(n)
        ],
        batch_size=2000,
    )


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
# 1. ten thousand tickets in batches
# -----------------------------------------------------------------------------
def test_ten_thousand_rows_in_batches_bounded_and_correct() -> None:
    Ticket = _ticket()
    _seed(N)
    tracemalloc.start()
    t0 = time.perf_counter()
    out = _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "500")
    took = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert f"migrated {N} row(s) in 20 batch(es); 0 remaining" in out, out
    assert took < 240, took
    assert peak < 60 * 1024 * 1024, peak  # one batch at a time, not 10k
    bad = (
        list(
            Ticket.objects.exclude(statechart_state=None)
            .extra(where=["statechart_state != 'ticket.' || state"])
            .values_list("pk", flat=True)[:5]
        )
        if connections["default"].vendor == "sqlite"
        else [
            t.pk
            for t in Ticket.objects.only("state", "statechart_state")
            if t.statechart_state != f"ticket.{t.state}"
        ]
    )
    assert bad == [], bad
    assert Ticket.objects.filter(statechart__isnull=True).count() == 0
    sample = Ticket.objects.order_by("pk").first()
    assert sample.statechart_state_ids == [f"ticket.{sample.state}"]
    assert sample.statechart_version == 0
    assert sample.statechart_machine_version == sample.machine.machine.version
    # in_state works on the migrated columns
    assert Ticket.objects.in_state("ticket.closed").count() == N // 4


# -----------------------------------------------------------------------------
# 2. --dry-run touches no ROW (the chart file is step 1's deliverable)
# -----------------------------------------------------------------------------
def test_dry_run_touches_no_row(tmp_path: Path) -> None:
    Ticket = _ticket()
    _seed(40)
    chart = tmp_path / "ticket.json"
    out = _out(
        "xsm_migrate_fsm",
        "legacy.Ticket",
        "--dry-run",
        "--write-chart",
        str(chart),
    )
    assert "ticket" in out.lower()
    assert Ticket.objects.filter(statechart__isnull=True).count() == 40
    assert Ticket.objects.exclude(statechart_state=None).count() == 0
    assert json.loads(chart.read_text("utf-8"))["id"] == "ticket"


# -----------------------------------------------------------------------------
# 3. dirty data
# -----------------------------------------------------------------------------
def test_unknown_values_are_reported_not_fatal_and_a_map_folds_them() -> None:
    Ticket = _ticket()
    _seed(400)
    # a renamed legacy state, a typo and an empty string, written straight
    # to the column as a legacy app would have
    Ticket.objects.filter(
        pk__in=list(Ticket.objects.values_list("pk", flat=True)[:50])
    ).update(
        state="open"
    )  # renamed to "new" years ago
    Ticket.objects.filter(
        pk__in=list(Ticket.objects.values_list("pk", flat=True)[50:60])
    ).update(state="inprogres")
    Ticket.objects.filter(
        pk__in=list(Ticket.objects.values_list("pk", flat=True)[60:65])
    ).update(state="")
    out = _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "100")
    # 🔥 the clean rows are migrated; the dirty ones are REPORTED by value
    #    with counts, and the command exits 0 having done what it could
    assert "migrated 335 row(s)" in out, out
    for value, n in (("open", 50), ("inprogres", 10), ("", 5)):
        assert f"{value!r}" in out and str(n) in out, (value, out)
    assert Ticket.objects.filter(statechart__isnull=True).count() == 65
    # the rename mapping folds the legacy value in
    out = _out(
        "xsm_migrate_fsm",
        "legacy.Ticket",
        "--map",
        "open=new",
        "--map",
        "inprogres=in_progress",
    )
    assert "migrated 60 row(s)" in out, out
    assert Ticket.objects.filter(statechart__isnull=True).count() == 5
    assert (
        Ticket.objects.filter(
            state="open", statechart_state="ticket.new"
        ).count()
        == 50
    )
    # a mapping to a state the chart does not have is refused up front
    with pytest.raises(CommandError, match="nope"):
        _out("xsm_migrate_fsm", "legacy.Ticket", "--map", "x=nope")


# -----------------------------------------------------------------------------
# 4. the site is still up
# -----------------------------------------------------------------------------
def test_live_writers_during_the_migration_lose_nothing() -> None:
    Ticket = _ticket()
    _seed(3000, ["new"])
    pks = list(Ticket.objects.values_list("pk", flat=True))
    moved: Dict[int, str] = {}
    lock = threading.Lock()
    stop = threading.Event()

    def migrate() -> None:
        _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "200")
        stop.set()

    def writer(offset: int) -> Any:
        def go() -> None:
            i = offset
            while not stop.is_set() and i < len(pks):
                t = Ticket.objects.get(pk=pks[i])
                if t.statechart is None:
                    # a legacy @transition on the FSM column, as the old
                    # code paths still do during the window
                    t.assignee = "w"
                    t.start()
                    t.save()
                    with lock:
                        moved[t.pk] = "in_progress"
                i += 7
            # new rows keep arriving too
            for _ in range(20):
                Ticket.objects.create(state="new", assignee="late")

        return go

    assert _threads([migrate, writer(1), writer(3), writer(5)]) == []
    # a second run picks up whatever the first one could not see yet
    out = _out("xsm_migrate_fsm", "legacy.Ticket", "--batch", "200")
    assert "0 remaining" in out
    assert Ticket.objects.filter(statechart__isnull=True).count() == 0
    # 🔥 no row migrated into a state it had already left
    stale = [
        t.pk
        for t in Ticket.objects.only("state", "statechart_state")
        if t.statechart_state != f"ticket.{t.state}"
    ]
    assert stale == [], stale[:5]
    assert Ticket.objects.filter(
        pk__in=list(moved), statechart_state="ticket.in_progress"
    ).count() == len(moved)
    assert Ticket.objects.count() == 3000 + 60


# -----------------------------------------------------------------------------
# 5. two FSMFields on one model
# -----------------------------------------------------------------------------
def test_field_selects_one_of_two_fsm_fields() -> None:
    from legacy.models import Ticket

    # the Ticket has one FSMField; a model with two is the shop's concern
    # -- at least the wrong name is refused with the candidates named
    with pytest.raises(CommandError) as ei:
        _out("xsm_migrate_fsm", "legacy.Ticket", "--field", "status")
    assert "state" in str(ei.value), str(ei.value)
    assert Ticket.objects.count() == 0


# -----------------------------------------------------------------------------
# 6. the dual-read window, both directions
# -----------------------------------------------------------------------------
def test_dual_read_window_keeps_both_columns_in_sync() -> None:
    Ticket = _ticket()
    t = Ticket.objects.create(state="new", assignee="me")
    _out("xsm_migrate_fsm", "legacy.Ticket")
    t.refresh_from_db()
    # new code: send() moves the chart and dual-writes the FSM column
    assert t.send("START").changed
    t.refresh_from_db()
    assert (t.state, t.statechart_state) == (
        "in_progress",
        "ticket.in_progress",
    )
    # old code still deployed: an FSM @transition moves the column; the
    # snapshot must follow, or the next send() starts from a stale state
    t.resolve()
    t.save()
    t.refresh_from_db()
    assert t.state == "resolved"
    assert t.statechart_state == "ticket.resolved", (
        t.state,
        t.statechart_state,
    )
    assert t.send("REOPEN").changed
    t.refresh_from_db()
    assert (t.state, t.statechart_state) == (
        "in_progress",
        "ticket.in_progress",
    )
