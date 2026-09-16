"""xstate-statemachine adapter: pure reducer API (no interpreter loop).

Uses `get_initial_snapshot` / `get_next_snapshot`, the actor-free reducer
pair mirroring XState's `initialTransition()` / `getNextSnapshot()`. This
is the fair comparison for libraries that only offer a pure
`(state, event) -> state` step with no running interpreter, so only S1-S3
are implemented (S4-S8 need an interpreter/instance/timer/loop, which the
pure API deliberately does not provide).
"""

from __future__ import annotations

from xstate_statemachine import (
    MachineLogic,
    __version__,
    assign,
    create_machine,
    get_initial_snapshot,
    get_next_snapshot,
)

LIB_NAME = "xstate-statemachine (pure)"
LIB_VERSION = __version__

CAPABILITY_NOTES = {
    "S4": "pure reducer has no instance to hold two orthogonal regions across calls meaningfully; use the interpreter adapters",
    "S5": "pure API has no interpreter to construct; construction cost is measured on the interpreter adapters",
    "S6": "pure API has no interpreter instances; use the interpreter adapters",
    "S7": "pure API is actor-free and schedules no timers; use the interpreter adapters",
    "S8": "pure API has no asyncio dispatch loop; use xstate_async.py",
}

_S1_CONFIG = {
    "id": "toggle",
    "initial": "A",
    "states": {
        "A": {"on": {"NEXT": "B"}},
        "B": {"on": {"NEXT": "A"}},
    },
}


def setup_S1():
    machine = create_machine(_S1_CONFIG)
    snapshot = get_initial_snapshot(machine)

    def hot(n: int) -> None:
        snap = snapshot
        for _ in range(n):
            snap = get_next_snapshot(machine, snap, "NEXT")
        assert snap.state_ids <= {"toggle.A", "toggle.B"}

    return hot


def _make_s2_config() -> dict:
    return {
        "id": "counter",
        "context": {"count": 0},
        "initial": "running",
        "states": {
            "running": {
                "on": {
                    "INC": {
                        "target": "running",
                        "guard": "below_limit",
                        "actions": assign(
                            lambda args: {
                                "count": args["context"]["count"] + 1
                            }
                        ),
                    }
                }
            }
        },
    }


def setup_S2():
    n_holder = {"n": None}

    def below_limit(ctx, event):
        return ctx["count"] < n_holder["n"]

    logic = MachineLogic(guards={"below_limit": below_limit})
    machine = create_machine(_make_s2_config(), logic=logic)

    def hot(n: int) -> None:
        n_holder["n"] = n
        snap = get_initial_snapshot(machine)
        for _ in range(n):
            snap = get_next_snapshot(machine, snap, "INC")
        assert snap.context["count"] == n

    return hot


_S3_CONFIG = {
    "id": "hier",
    "initial": "a",
    "states": {
        "a": {
            "initial": "a1",
            "states": {
                "a1": {"on": {"DEEP": "a2", "CROSS": "#hier.b.b2"}},
                "a2": {"on": {"DEEP": "a1"}},
            },
        },
        "b": {
            "initial": "b1",
            "states": {
                "b1": {"on": {"DEEP": "b2", "CROSS": "#hier.a.a1"}},
                "b2": {"on": {"DEEP": "b1"}},
            },
        },
    },
}


def setup_S3():
    machine = create_machine(_S3_CONFIG)
    snapshot = get_initial_snapshot(machine)

    def hot(n: int) -> None:
        snap = snapshot
        for _ in range(n):
            snap = get_next_snapshot(machine, snap, "CROSS")
            snap = get_next_snapshot(machine, snap, "DEEP")
        assert snap.state_ids

    return hot


def setup_S4():
    return None


def setup_S5():
    return None


def setup_S6():
    return None


def setup_S7():
    return None


def setup_S8():
    return None
