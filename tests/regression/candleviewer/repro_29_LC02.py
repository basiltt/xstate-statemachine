"""LC-02 repro: an `always` (eventless) transition whose fallback targets its OWN
state never re-runs `entry`, so the guard is never re-evaluated and the machine
parks forever in the loop state with no error and `status == "running"`.

Note on scope: XState v5 AGREES that an explicit self-target does not re-run
`entry`/`exit` (https://stately.ai/docs/transitions#re-entering) -- so the
entry/exit semantics here are correct and `reenter: True` is the documented
opt-in, which works (control case below). The defect is the absence of any
DIAGNOSTIC: XState documents that it "will help guard against most infinite loop
scenarios" and that "if `target` is declared, the value should differ from the
current state node" (https://stately.ai/docs/eventless-transitions
#avoid-infinite-loops). This library accepts the non-progressing config at
build time and then deadlocks silently. It also silently discards the XState v4
`internal` key, which is what a migrating user would reach for.

Exits 1 when the defect is present.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

SELF_LOOP = {
    "id": "m",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {"on": {"GO": "loop"}},
        "loop": {
            "entry": ["inc"],
            "always": [{"target": "done", "guard": "enough"}, {"target": "loop"}],
        },
        "done": {},
    },
}

# Identical logic, but the loop goes through a DISTINCT intermediate state.
VIA_B = {
    "id": "m",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {"on": {"GO": "A"}},
        "A": {
            "entry": ["inc"],
            "always": [{"target": "done", "guard": "enough"}, {"target": "B"}],
        },
        "B": {"always": {"target": "A"}},
        "done": {},
    },
}

# Control: the XState v5 opt-in. This converges today, proving the engine can
# drive the loop and that no semantic change is needed -- only a diagnostic.
REENTER = {
    "id": "m",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {"on": {"GO": "loop"}},
        "loop": {
            "entry": ["inc"],
            "always": [
                {"target": "done", "guard": "enough"},
                {"target": "loop", "reenter": True},
            ],
        },
        "done": {},
    },
}

# Control: the XState v4 spelling a migrating user reaches for. Silently dropped
# (models.py:397 reads `reenter` but never `internal`), so it parks like SELF_LOOP.
INTERNAL_FALSE = {
    "id": "m",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {"on": {"GO": "loop"}},
        "loop": {
            "entry": ["inc"],
            "always": [
                {"target": "done", "guard": "enough"},
                {"target": "loop", "internal": False},
            ],
        },
        "done": {},
    },
}


def make_logic():
    def inc(i, c, e, a):
        c["n"] += 1

    return MachineLogic(actions={"inc": inc}, guards={"enough": lambda c, e: c["n"] >= 5})


async def run(cfg):
    interp = Interpreter(create_machine(cfg, logic=make_logic()))
    await interp.start()
    await interp.send("GO")
    await asyncio.sleep(0.2)
    out = (sorted(interp.current_state_ids), interp.context["n"], interp.status)
    await interp.stop()
    return out


async def main() -> int:
    self_state, self_n, self_status = await run(SELF_LOOP)
    via_state, via_n, _ = await run(VIA_B)
    re_state, re_n, _ = await run(REENTER)
    int_state, int_n, _ = await run(INTERNAL_FALSE)

    print(f"OBSERVED self-target loop  : state={self_state} n={self_n} status={self_status}")
    print(f"OBSERVED via-B loop        : state={via_state} n={via_n}")
    print(f"OBSERVED reenter:True loop : state={re_state} n={re_n}")
    print(f"OBSERVED internal:False    : state={int_state} n={int_n}")
    print("EXPECTED: NOT that the self-target loop converges -- XState v5 agrees an")
    print("EXPECTED: explicit self-target does not re-run `entry` (docs/transitions")
    print("EXPECTED: #re-entering). `reenter: True` is the v5 opt-in and works here.")
    print("EXPECTED: The defect is the ABSENCE OF A DIAGNOSTIC: create_machine()")
    print("EXPECTED: should reject an `always` self-target that can never progress")
    print("EXPECTED: (XState: 'If target is declared, the value should differ from")
    print("EXPECTED: the current state node'), and `internal: False` must not be")
    print("EXPECTED: silently dropped. Today both are accepted and the machine")
    print("EXPECTED: parks forever while still reporting status == 'running'.")

    # The defect: the non-progressing config builds without error, then parks
    # silently -- while the documented opt-in (`reenter: True`) proves the engine
    # can drive the loop, and `internal: False` is silently discarded.
    parks_silently = self_state == ["m.loop"] and self_n < 5 and self_status == "running"
    engine_can_loop = via_state == ["m.done"] and re_state == ["m.done"]
    internal_dropped = int_state == ["m.loop"] and int_n < 5

    bad = parks_silently and engine_can_loop and internal_dropped
    print("RESULT: DEFECT REPRODUCED" if bad else "RESULT: not reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
