"""xstate-statemachine adapter: SyncInterpreter engine.

Uses the synchronous engine (`SyncInterpreter`) for every scenario it can
express. S7 (delayed transition) uses `SimulatedClock` so the benchmark
does not burn wall-clock time waiting on a real timer -- `clock.increment()`
advances virtual time and fires the due `after` transition immediately.
S8 (native asyncio dispatch) is not applicable here; see `xstate_async.py`.
"""

from __future__ import annotations

from xstate_statemachine import (
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    __version__,
    create_machine,
)

LIB_NAME = "xstate-statemachine (sync)"
LIB_VERSION = __version__

CAPABILITY_NOTES = {
    "S8": "native asyncio dispatch benchmarked separately in xstate_async.py",
}


# -----------------------------------------------------------------------------
# S1: flat_toggle
# -----------------------------------------------------------------------------
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
    interp = SyncInterpreter(machine).start()

    def hot(n: int) -> None:
        for _ in range(n):
            interp.send("NEXT")
        assert interp.current_state_ids <= {"toggle.A", "toggle.B"}

    return hot


# -----------------------------------------------------------------------------
# S2: guarded_context
# -----------------------------------------------------------------------------
def _make_s2_config(limit: int) -> dict:
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
                        "actions": "increment",
                    }
                }
            }
        },
    }


def setup_S2():
    n_holder = {"n": None}

    def below_limit(ctx, event):
        return ctx["count"] < n_holder["n"]

    def increment(interp, ctx, event, action_def):
        ctx["count"] += 1

    logic = MachineLogic(
        actions={"increment": increment}, guards={"below_limit": below_limit}
    )

    def hot(n: int) -> None:
        n_holder["n"] = n
        machine = create_machine(_make_s2_config(n), logic=logic)
        interp = SyncInterpreter(machine).start()
        for _ in range(n):
            interp.send("INC")
        assert interp.context["count"] == n

    return hot


# -----------------------------------------------------------------------------
# S3: hierarchical
# -----------------------------------------------------------------------------
_S3_CONFIG = {
    # Every CROSS/DEEP send in the hot loop below performs a real, valid
    # cross-level transition -- no state in this 4-state cycle is ever sent
    # an event it lacks a handler for, so there are zero free/no-op sends
    # (see benchmarks/competitors audit fairness rules #1 and #2).
    "id": "hier",
    "initial": "a",
    "states": {
        "a": {
            "initial": "a1",
            "states": {
                "a1": {"on": {"CROSS": "#hier.b.b2"}},
                "a2": {"on": {"DEEP": "#hier.a.a1"}},
            },
        },
        "b": {
            "initial": "b1",
            "states": {
                "b1": {"on": {"CROSS": "#hier.a.a2"}},
                "b2": {"on": {"DEEP": "#hier.b.b1"}},
            },
        },
    },
}


def setup_S3():
    machine = create_machine(_S3_CONFIG)
    interp = SyncInterpreter(machine).start()

    def hot(n: int) -> None:
        for i in range(n):
            interp.send("CROSS")
            interp.send("DEEP")
        assert interp.current_state_ids

    return hot


# -----------------------------------------------------------------------------
# S4: parallel
# -----------------------------------------------------------------------------
_S4_CONFIG = {
    "id": "par",
    "type": "parallel",
    "states": {
        "region1": {
            "initial": "on1",
            "states": {
                "on1": {"on": {"TOGGLE1": "off1"}},
                "off1": {"on": {"TOGGLE1": "on1"}},
            },
        },
        "region2": {
            "initial": "on2",
            "states": {
                "on2": {"on": {"TOGGLE2": "off2"}},
                "off2": {"on": {"TOGGLE2": "on2"}},
            },
        },
    },
}


def setup_S4():
    machine = create_machine(_S4_CONFIG)
    interp = SyncInterpreter(machine).start()

    def hot(n: int) -> None:
        for i in range(n):
            interp.send("TOGGLE1" if i % 2 == 0 else "TOGGLE2")
        assert len(interp.current_state_ids) == 2

    return hot


# -----------------------------------------------------------------------------
# S5: construction
# -----------------------------------------------------------------------------
def setup_S5():
    def hot(n: int) -> None:
        last = None
        for _ in range(n):
            machine = create_machine(_S3_CONFIG)
            last = SyncInterpreter(machine).start()
        assert last.current_state_ids

    return hot


# -----------------------------------------------------------------------------
# S6: many_instances
# -----------------------------------------------------------------------------
def setup_S6():
    machine = create_machine(_S1_CONFIG)

    def hot(n: int) -> None:
        instances = [SyncInterpreter(machine).start() for _ in range(n)]
        for interp in instances:
            interp.send("NEXT")
        assert all(i.current_state_ids == {"toggle.B"} for i in instances)

    return hot


# -----------------------------------------------------------------------------
# S7: delayed_transition (via SimulatedClock -- no real sleeping)
# -----------------------------------------------------------------------------
_S7_CONFIG = {
    "id": "delayed",
    "initial": "waiting",
    "states": {
        "waiting": {"after": {1: [{"target": "done"}]}},
        "done": {"type": "final"},
    },
}


def setup_S7():
    def hot(n: int) -> None:
        fired = 0
        for _ in range(n):
            clock = SimulatedClock()
            machine = create_machine(_S7_CONFIG)
            interp = SyncInterpreter(machine, clock=clock).start()
            clock.increment(1)
            if interp.current_state_ids == {"delayed.done"}:
                fired += 1
        assert fired == n

    return hot


# -----------------------------------------------------------------------------
# S8: async_dispatch -- not applicable to the sync engine.
# -----------------------------------------------------------------------------
def setup_S8():
    return None
