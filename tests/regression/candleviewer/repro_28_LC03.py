"""LC-03 repro: events that have no handler in the *current* state are silently
discarded. An OMS order machine sitting in `submitting` (awaiting an invoke) loses
every `PARTIAL`/`FILL` that arrives before the ack — no error, no hook, no warning
the caller can observe.

Exits 1 when the defect is present.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

CONFIG = {
    "id": "oms",
    "initial": "idle",
    "context": {"filled": 0},
    "states": {
        "idle": {"on": {"NEW": "submitting"}},
        # `submitting` has NO handler for PARTIAL/FILL — it only waits for the ack.
        "submitting": {
            "invoke": {"src": "place", "onDone": {"target": "live"}},
        },
        "live": {
            "on": {
                "PARTIAL": {"actions": ["apply_fill"]},
                "FILL": {"target": "filled", "actions": ["apply_fill"]},
            }
        },
        "filled": {"type": "final"},
    },
}


async def main() -> int:
    def apply_fill(i, c, e, a):
        c["filled"] += e.payload["qty"]

    async def place(i, c, e):
        await asyncio.sleep(0.05)  # exchange ack latency
        return "ok"

    logic = MachineLogic(actions={"apply_fill": apply_fill}, services={"place": place})
    interp = Interpreter(create_machine(CONFIG, logic=logic))
    await interp.start()

    await interp.send("NEW")
    # Exchange pushes fills while we are still awaiting the ack.
    await interp.send({"type": "PARTIAL", "qty": 10})
    await interp.send({"type": "PARTIAL", "qty": 10})
    await interp.send({"type": "FILL", "qty": 10})
    await asyncio.sleep(0.3)

    states = sorted(interp.current_state_ids)
    filled = interp.context["filled"]
    status = interp.status
    await interp.stop()

    print(f"OBSERVED state  : {states}")
    print(f"OBSERVED filled : {filled}")
    print(f"OBSERVED status : {status}")
    print("EXPECTED state  : ['oms.filled'] (or an observable unhandled-event signal)")
    print("EXPECTED filled : 30")
    print("EXPECTED: the 3 events must not vanish without any programmatic trace.")

    bad = filled == 0 and states != ["oms.filled"]
    print("RESULT: DEFECT REPRODUCED" if bad else "RESULT: not reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
