# tests/persistence/test_adopt.py
"""#310: `from_state_ids` -- adopt an existing record into a machine."""

from __future__ import annotations

import json

import pytest

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    InvalidConfigError,
    StateNotFoundError,
)
from src.xstate_statemachine.persistence import from_state_ids

CFG = {
    "id": "o",
    "initial": "draft",
    "context": {"n": 0, "keep": True},
    "states": {
        "draft": {"entry": "boom", "on": {"GO": "review"}},
        "review": {
            "type": "parallel",
            "states": {
                "legal": {
                    "initial": "pending",
                    "states": {"pending": {"on": {"OK": "ok"}}, "ok": {}},
                },
                "finance": {
                    "initial": "pending",
                    "states": {"pending": {}, "ok": {}},
                },
            },
        },
        "wait": {"after": {"1000": "done"}},
        "noinit": {"states": {"a": {}, "b": {}}},
        "done": {"type": "final"},
    },
}


def machine():
    def boom(*a):  # entry actions must NOT run on adoption
        raise AssertionError("entry action ran")

    return create_machine(CFG, logic=MachineLogic(actions={"boom": boom}))


def test_leaf_round_trips_without_running_anything() -> None:
    m = machine()
    blob = from_state_ids(m, ["o.draft"], {"n": 5})
    snap = json.loads(blob)
    assert snap["state_ids"] == ["o.draft"]
    assert snap["configuration"] == ["o", "o.draft"]
    assert snap["context"] == {"n": 5, "keep": True}
    assert snap["machine_hash"] and snap["version"] >= 4
    i = SyncInterpreter.from_snapshot(blob, m)
    assert i.current_state_ids == {"o.draft"} and i.context["n"] == 5
    i.start()
    i.send("GO")
    assert i.matches("o.review.legal.pending")
    i.stop()


def test_relative_ids_and_parallel_completion() -> None:
    m = machine()
    snap = json.loads(from_state_ids(m, ["review.legal.ok"]))
    assert snap["state_ids"] == [
        "o.review.finance.pending",
        "o.review.legal.ok",
    ]
    assert snap["value"] == {"review": {"legal": "ok", "finance": "pending"}}
    snap = json.loads(from_state_ids(m, ["o.review"]))
    assert snap["state_ids"] == [
        "o.review.finance.pending",
        "o.review.legal.pending",
    ]


def test_timers_are_not_armed_until_restored_and_started() -> None:
    m = machine()
    snap = json.loads(from_state_ids(m, ["wait"]))
    assert snap["deadlines"] == []
    i = SyncInterpreter.from_snapshot(
        json.dumps(snap), m, restart_timers="restart"
    )
    i.start()
    assert [d.event_type for d in i.pending_deadlines()] == [
        "after.1000.o.wait"
    ]
    i.stop()


def test_final_status() -> None:
    snap = json.loads(from_state_ids(machine(), ["done"], status="done"))
    assert snap["status"] == "done"
    with pytest.raises(InvalidConfigError):
        from_state_ids(machine(), ["done"], status="weird")


@pytest.mark.parametrize(
    "ids,exc",
    [
        (["nope"], StateNotFoundError),
        (["o.review.legal.zzz"], StateNotFoundError),
        ([], InvalidConfigError),
        (["draft", "wait"], InvalidConfigError),  # two root children
        (["review.legal.ok", "review.legal.pending"], InvalidConfigError),
        (["noinit"], InvalidConfigError),  # compound without initial
    ],
)
def test_invalid_configurations_are_refused_loudly(ids, exc) -> None:
    with pytest.raises(exc):
        from_state_ids(machine(), ids)


def test_noinit_with_explicit_child_is_fine() -> None:
    snap = json.loads(from_state_ids(machine(), ["noinit.b"]))
    assert snap["state_ids"] == ["o.noinit.b"]
