"""LC-27 repro: no clock injection / virtual time for `after` transitions.

An `after` transition is driven by a hard-coded `asyncio.sleep`. There is no
`clock` argument on `Interpreter` and no way to advance time, so a test of a
5-second timeout must burn 5 real seconds of wall clock.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sys
import time

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

DELAY_MS = 600

CFG = {
    "id": "order",
    "initial": "submitting",
    "states": {
        "submitting": {"after": {DELAY_MS: {"target": "timed_out"}}},
        "timed_out": {"type": "final"},
    },
}


# 0.8.0 (#49): the library ships `SimulatedClock` (XState's name and
# semantics). The stand-in that used to live here -- a class nothing
# consumed, to demonstrate the gap -- is replaced by the real one.
from xstate_statemachine import SimulatedClock  # noqa: E402


async def main() -> int:
    ok = True

    # 1) No `clock` parameter exists on the Interpreter constructor.
    params = list(inspect.signature(Interpreter.__init__).parameters)
    print(f"OBSERVED Interpreter.__init__ params = {params}")
    print("EXPECTED a 'clock' parameter (XState v5 `createActor(m, {clock})`)")
    if "clock" not in params:
        ok = False

    # 2) Passing one is a hard TypeError.
    machine = create_machine(CFG, logic=MachineLogic())
    clock = SimulatedClock()
    try:
        Interpreter(machine, clock=clock)
        print("OBSERVED Interpreter(machine, clock=...) accepted")
    except TypeError as exc:
        print(f"OBSERVED Interpreter(machine, clock=...) -> TypeError: {exc}")
        ok = False

    # 3) Advancing the simulated clock does nothing; only wall time fires it.
    interp = await Interpreter(
        create_machine(CFG, logic=MachineLogic()), clock=clock
    ).start()
    started = time.monotonic()
    await clock.increment(10_000)
    fired_after_virtual_advance = "order.timed_out" in interp.current_state_ids
    print(
        "OBSERVED after advancing simulated clock by 10000ms: "
        f"timer fired = {fired_after_virtual_advance}"
    )
    print("EXPECTED timer fired = True (virtual time should drive `after`)")
    if not fired_after_virtual_advance:
        ok = False

    while "order.timed_out" not in interp.current_state_ids:
        await asyncio.sleep(0.01)
    elapsed_ms = (time.monotonic() - started) * 1000
    print(
        f"OBSERVED real wall-clock time to reach 'timed_out' = {elapsed_ms:.0f} ms"
    )
    print(
        f"EXPECTED ~0 ms under a simulated clock (real delay is {DELAY_MS} ms)"
    )
    if elapsed_ms >= DELAY_MS * 0.8:
        ok = False
    await interp.stop()

    print(
        "RESULT:",
        "REPRODUCED (no clock injection)" if not ok else "NOT REPRODUCED",
    )
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
