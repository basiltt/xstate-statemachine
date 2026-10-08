# tests/contrib/django/test_battle_310_a.py
"""#310 battle, adversary A: the data path of ``xsm_migrate_fsm``.

``extract_chart`` on the shapes real legacy apps have (state values that
are not XState keys, dynamic ``RETURN_VALUE`` / ``GET_STATE`` targets,
``on_error``, lambdas and same-named conditions, ``custom``),
``migrate_rows`` on a UUID pk / ``protected=True`` / NULLable column /
``FSMIntegerField`` / another database alias / tens of thousands of
unknown rows, ``from_state_ids`` deadlines, and the two-way dual write
under concurrency. SQLite here; the Postgres cells run through
``test_battle_310_postgres.py`` when ``DATABASE_URL`` is set.
"""

from __future__ import annotations

import io
import json
import threading
import tracemalloc
from typing import Any, Dict, List

import pytest
from django.core.management import call_command
from django.db import connections, models

pytest.importorskip("django_fsm")

from django_fsm import (  # noqa: E402
    GET_STATE,
    RETURN_VALUE,
    FSMField,
    transition,
)

from xstate_statemachine import create_machine  # noqa: E402
from xstate_statemachine.contrib.django.fsm import (  # noqa: E402
    extract_chart,
    migrate_rows,
)
from xstate_statemachine.testing_utils import stub_logic  # noqa: E402


def _out(*args: Any, **kw: Any) -> str:
    buf = io.StringIO()
    call_command(*args, stdout=buf, **kw)
    return buf.getvalue()


def _strict(chart: Dict[str, Any]) -> Any:
    return create_machine(chart, logic=stub_logic(chart), strict_config=True)


def _gadget() -> Any:
    from legacy.models import Gadget

    return Gadget


def _counter() -> Any:
    from legacy.models import Counter

    return Counter


# -----------------------------------------------------------------------------
# 1. extract_chart
# -----------------------------------------------------------------------------
def cond_a(i: Any) -> bool:
    return True


def _models() -> Any:
    """Throw-away models in an isolated registry (they must not leak into
    ``makemigrations`` for the real ``legacy`` app)."""
    from django.test.utils import isolate_apps

    with isolate_apps("legacy"):

        class Shapes(models.Model):
            state = FSMField(
                default="in-progress",
                choices=[
                    ("in-progress", "dash"),
                    ("in_progress", "underscore"),
                    ("état", "accent"),
                    ("1", "digit"),
                    ("only_in_choices", "x"),
                ],
            )

            class Meta:
                app_label = "legacy"

            @transition(field=state, source="*", target="état")
            def a(self) -> None:
                pass

            @transition(field=state, source="+", target="1", on_error="failed")
            def b(self) -> None:
                pass

            @transition(field=state, source="1", target=None)
            def check(self) -> None:
                pass

            @transition(
                field=state,
                source="1",
                target=RETURN_VALUE("in-progress", "état"),
            )
            def rv(self) -> str:
                return "état"

            @transition(
                field=state,
                source="état",
                target=GET_STATE(
                    lambda s: "1", states=["1", "only_in_get_state"]
                ),
            )
            def gs(self) -> None:
                pass

            @transition(
                field=state,
                source="in_progress",
                target="1",
                permission=lambda i, u: True,
                conditions=[lambda i: True, cond_a],
                custom={"label": "Go", "n": 1},
            )
            def go(self) -> None:
                pass

            @transition(
                field=state,
                source="in-progress",
                target="1",
                permission=lambda i, u: False,
            )
            def go2(self) -> None:
                pass

        class Unbounded(models.Model):
            state = FSMField(default="a")

            class Meta:
                app_label = "legacy"

            @transition(field=state, source="a", target=RETURN_VALUE())
            def anywhere(self) -> str:
                return "b"

    return Shapes, Unbounded


Shapes, Unbounded = _models()


def test_state_values_that_are_not_keys_stay_distinct_and_reversible() -> None:
    chart = extract_chart(Shapes, "state")
    states = chart["states"]
    values = {
        k: (v.get("meta") or {}).get("fsm_value", k) for k, v in states.items()
    }
    # 🔥 "in-progress" and "in_progress" used to MERGE into one node (with
    #    every fanned-out transition listed twice); "état" became "_tat"
    for v in ("in-progress", "in_progress", "état", "1", "only_in_choices"):
        assert list(values.values()).count(v) == 1, (v, values)
    assert values["état"] == "état"  # a unicode key is a legal key
    # every key resolves; no transition is listed twice
    for node in states.values():
        for spec in (node.get("on") or {}).values():
            specs = spec if isinstance(spec, list) else [spec]
            keys = [json.dumps(s, sort_keys=True) for s in specs]
            assert len(keys) == len(set(keys)), specs
    _strict(chart)


def test_dynamic_targets_become_guarded_candidates_not_garbage() -> None:
    chart = extract_chart(Shapes, "state")
    text = json.dumps(chart)
    # 🔥 the target used to be "_django_fsm_RETURN_VALUE_object_at_0x..."
    #    -- a fake state, and a different JSON on every run
    assert "object_at" not in text and "RETURN_VALUE object" not in text
    keys = {
        (v.get("meta") or {}).get("fsm_value", k): k
        for k, v in chart["states"].items()
    }
    rv = chart["states"][keys["1"]]["on"]["RV"]
    assert [s["target"] for s in rv] == [keys["in-progress"], keys["état"]]
    assert all(s["meta"]["dynamic"] == "RETURN_VALUE" for s in rv)
    gs = chart["states"][keys["état"]]["on"]["GS"]
    assert "only_in_get_state" in keys  # allowed states are states
    assert [s["target"] for s in gs] == [keys["1"], keys["only_in_get_state"]]
    with pytest.raises(ValueError, match="anywhere"):
        extract_chart(Unbounded, "state")


def test_on_error_custom_and_guard_names_are_kept_distinct() -> None:
    chart = extract_chart(Shapes, "state")
    keys = {
        (v.get("meta") or {}).get("fsm_value", k): k
        for k, v in chart["states"].items()
    }
    # 🔥 on_error was dropped silently -- and a row in "failed" then had
    #    no state to migrate into
    assert "failed" in keys
    b = chart["states"][keys["in-progress"]]["on"]["B"]
    assert b["meta"]["on_error"] == keys["failed"]
    go = chart["states"][keys["in_progress"]]["on"]["GO"]
    assert go["meta"]["custom"] == {"label": "Go", "n": 1}
    go2 = chart["states"][keys["in-progress"]]["on"]["GO2"]
    # 🔥 two DIFFERENT lambdas were both named "lambda": one implementation
    #    would silently guard both transitions
    names = go["guard"]["children"] + [go2["guard"]]
    assert len(set(names)) == len(names) == 4, names
    assert "lambda" not in names and "condA" in names


def test_same_named_conditions_from_two_modules_do_not_merge() -> None:
    import types

    m1, m2 = types.ModuleType("billing"), types.ModuleType("shipping")
    exec("def is_ready(i):\n    return True", m1.__dict__)
    exec("def is_ready(i):\n    return False", m2.__dict__)

    from django.test.utils import isolate_apps

    with isolate_apps("legacy"):
        Twin = _twin(m1, m2)
    on = extract_chart(Twin, "state")["states"]["a"]["on"]
    assert on["PAY"]["guard"] != on["SHIP"]["guard"]


def _twin(m1: Any, m2: Any) -> Any:
    class Twin(models.Model):
        state = FSMField(default="a")

        class Meta:
            app_label = "legacy"

        @transition(
            field=state, source="a", target="b", conditions=[m1.is_ready]
        )
        def pay(self) -> None:
            pass

        @transition(
            field=state, source="a", target="c", conditions=[m2.is_ready]
        )
        def ship(self) -> None:
            pass

    return Twin


def test_extraction_is_byte_stable() -> None:
    a = json.dumps(extract_chart(Shapes, "state"), indent=2)
    b = json.dumps(extract_chart(Shapes, "state"), indent=2)
    assert a == b


# -----------------------------------------------------------------------------
# 2. migrate_rows
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True, databases=["default", "other"])
class TestMigrateRows:
    def test_uuid_pk_protected_nullable_renamed_field_batch_1(self) -> None:
        Gadget = _gadget()
        values = ["in-progress", "état", "1", None, "parked"]
        Gadget.objects.bulk_create(
            [Gadget(status=values[i % 5]) for i in range(25)]
        )
        unknown: Dict[str, int] = {}
        done, batches = migrate_rows(
            Gadget,
            "status",
            statechart_field="chart",
            batch=1,
            unknown=unknown,
        )
        assert (done, unknown) == (20, {"None": 5})
        for g in Gadget.objects.exclude(status=None):
            leaf = g.chart_state.split(".", 1)[1]
            meta = g.statechart_machine_node().states[leaf].meta or {}
            assert meta.get("fsm_value", leaf) == g.status
        # idempotent: thrice → nothing
        for _ in range(2):
            assert (
                migrate_rows(
                    Gadget, "status", statechart_field="chart", batch=1
                )[0]
                == 0
            )
        # a skipped row fixed by hand is picked up
        Gadget.objects.filter(status=None).update(status="parked")
        assert migrate_rows(Gadget, "status", statechart_field="chart")[0] == 5

    def test_integer_field_and_dual_write_back_as_int(self) -> None:
        Counter = _counter()
        c = Counter.objects.create(level=1)
        migrate_rows(Counter, "level")
        c.refresh_from_db()
        assert c.statechart_state == "counter.s_1"
        assert c.send("UP").changed
        # 🔥 the dual write used to store the KEY ("s_2") in the int column
        assert Counter.objects.get(pk=c.pk).level == 2
        # and the reverse: an FSM @transition re-adopts s_3
        c = Counter.objects.get(pk=c.pk)
        c.top()
        c.save()
        c = Counter.objects.get(pk=c.pk)
        assert (c.level, c.statechart_state) == (3, "counter.s_3")

    def test_protected_field_dual_write_both_ways(self) -> None:
        Gadget = _gadget()
        g = Gadget.objects.create(status="in-progress")
        migrate_rows(Gadget, "status", statechart_field="chart")
        g = Gadget.objects.get(pk=g.pk)
        v0 = g.chart_version
        # 🔥 "in-progress" vs key "in_progress": every save() re-adopted
        #    (a spurious version bump that fails concurrent senders)
        g.save()
        assert Gadget.objects.get(pk=g.pk).chart_version == v0
        assert g.send("ADVANCE").changed
        g = Gadget.objects.get(pk=g.pk)
        assert (g.status, g.chart_state) == ("état", "gadget.état")
        g.finish()  # protected=True: through the @transition only
        g.save()
        g = Gadget.objects.get(pk=g.pk)
        assert g.chart_state == "gadget.s_1" and g.status == "1"
        assert g.send("RESTART").changed
        assert Gadget.objects.get(pk=g.pk).status == "in-progress"

    def test_other_database_alias(self) -> None:
        from legacy.models import Ticket

        Ticket.objects.using("other").create(state="resolved")
        Ticket.objects.create(state="new")
        out = _out("xsm_migrate_fsm", "legacy.Ticket", "--database", "other")
        assert "migrated 1 row(s)" in out
        assert Ticket.objects.filter(statechart__isnull=True).count() == 1
        t = Ticket.objects.using("other").get()
        assert t.statechart_state == "ticket.resolved"

    def test_context_raising_for_one_row(self) -> None:
        from legacy.models import Ticket

        Ticket.objects.bulk_create(
            [Ticket(state="new", assignee=str(i)) for i in range(10)]
        )

        def ctx(row: Any) -> Dict[str, Any]:
            if row.assignee == "4":
                raise KeyError("no such customer")
            return {"who": row.assignee}

        # without a `failed` sink: loud, naming the row -- and the batch
        # rolls back whole (no partial rows), the earlier one stays
        with pytest.raises(ValueError, match="pk="):
            migrate_rows(Ticket, batch=3, context=ctx)
        assert Ticket.objects.filter(statechart__isnull=False).count() == 3
        failed: Dict[Any, str] = {}
        done, _ = migrate_rows(Ticket, batch=3, context=ctx, failed=failed)
        assert done == 6 and len(failed) == 1
        assert "no such customer" in next(iter(failed.values()))
        t = Ticket.objects.filter(assignee="7").get()
        assert t.statechart["context"]["who"] == "7"

    def test_ten_thousand_unknown_rows_do_not_build_a_huge_query(
        self,
    ) -> None:
        from legacy.models import Ticket

        n = 48_000  # 36k unknown > SQLite 32766 host params
        Ticket.objects.bulk_create(
            [Ticket(state="typo" if i % 4 else "new") for i in range(n)],
            batch_size=5000,
        )
        tracemalloc.start()
        unknown: Dict[str, int] = {}
        done, _ = migrate_rows(Ticket, batch=2000, unknown=unknown)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert (done, unknown) == (n // 4, {"typo": n * 3 // 4})
        assert peak < 40 * 1024 * 1024, peak


# -----------------------------------------------------------------------------
# 3. dual write under concurrency
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_eight_threads_send_and_fsm_transition_on_one_row() -> None:
    from legacy.models import Ticket

    from xstate_statemachine.contrib.django.mixin import send_with_retry

    t = Ticket.objects.create(state="new", assignee="me")
    migrate_rows(Ticket)
    errors: List[str] = []
    versions: List[int] = []
    lock = threading.Lock()

    def sender() -> None:
        for _ in range(6):
            row = Ticket.objects.get(pk=t.pk)
            ev = {"new": "START", "in_progress": "RESOLVE"}.get(
                row.state, "REOPEN"
            )
            send_with_retry(row, ev, retries=50)

    def legacy() -> None:
        for _ in range(6):
            row = Ticket.objects.get(pk=t.pk)
            if row.state == "resolved":
                row.reopen()
            elif row.state == "in_progress":
                row.resolve()
            else:
                row.reset()
            row.save()

    def watch() -> None:
        for _ in range(40):
            v = Ticket.objects.values_list(
                "statechart_version", flat=True
            ).get(pk=t.pk)
            with lock:
                versions.append(v)

    def run(fn: Any) -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - reported
            with lock:
                errors.append(repr(exc)[:300])
        finally:
            connections.close_all()

    fns = [sender, legacy] * 4 + [watch]
    ts = [threading.Thread(target=run, args=(f,)) for f in fns]
    for th in ts:
        th.start()
    for th in ts:
        th.join(300)
    assert errors == []
    assert versions == sorted(versions)  # monotonic
    row = Ticket.objects.get(pk=t.pk)
    assert row.statechart_state == f"ticket.{row.state}"


# -----------------------------------------------------------------------------
# 4. from_state_ids: deadlines for an adopted `after` state
# -----------------------------------------------------------------------------
def test_adopted_after_state_has_a_deadline_when_asked() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter
    from xstate_statemachine.persistence.adopt import from_state_ids

    m = create_machine(
        {
            "id": "o",
            "initial": "a",
            "states": {
                "a": {},
                "wait": {"after": {"60000": "late"}},
                "late": {},
            },
        }
    )
    assert json.loads(from_state_ids(m, ["wait"]))["deadlines"] == []
    clock = SimulatedClock(wall_start=1000.0)
    snap = json.loads(from_state_ids(m, ["wait"], timers=True, clock=clock))
    [d] = snap["deadlines"]
    assert (d["state_id"], d["due_at_wall"]) == ("o.wait", 1060.0)
    i = SyncInterpreter.from_snapshot(
        json.dumps(snap),
        m,
        restart_timers="fire_due",
        clock=SimulatedClock(wall_start=2000.0),
    ).start()
    assert i.current_state_ids == {"o.late"}


def test_compound_and_parallel_charts_map_to_one_value_or_none() -> None:
    from xstate_statemachine.contrib.django.fsm import (
        _NO_VALUE,
        _top_value,
        key_for_value,
    )
    from xstate_statemachine.persistence.adopt import from_state_ids

    m = create_machine(
        {
            "id": "t",
            "initial": "new",
            "states": {
                "new": {},
                "in_progress": {
                    "meta": {"fsm_value": "in-progress"},
                    "initial": "triage",
                    "states": {"triage": {}, "work": {}},
                },
            },
        }
    )
    # a column value adopted into a COMPOUND enters its initial child
    key = key_for_value(m, "in-progress")
    assert json.loads(from_state_ids(m, [key]))["state_ids"] == [
        "t.in_progress.triage"
    ]
    # every child of it dual-writes the compound's FSM value
    assert _top_value(m, ["t.in_progress.work"], {}) == "in-progress"
    p = create_machine(
        {
            "id": "p",
            "type": "parallel",
            "states": {
                "a": {"initial": "x", "states": {"x": {}}},
                "b": {"initial": "y", "states": {"y": {}}},
            },
        }
    )
    # a parallel root has no single value: the dual write is a no-op
    assert _top_value(p, ["p.a.x", "p.b.y"], {}) is _NO_VALUE
    assert _top_value(p, [], {}) is _NO_VALUE
