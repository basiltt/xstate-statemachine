"""LC-32 repro: terminal machines are not reaped.

When a machine reaches a top-level final state, `BaseInterpreter._complete()`
(base_interpreter.py:2335) sets `status = "done"`, records `output`, fires the
plugin `on_done` hooks — and stops. No teardown is performed. Concretely:

  1. `context` is retained in full (nothing is released).
  2. Spawned child actors keep RUNNING: their event loops, `after` timers and
     invoked services are still scheduled on the asyncio loop.
  3. The actor-system registry entry survives — and is *never* removed, not
     even by an explicit `stop()`, so `interpreter.system` grows monotonically
     for the lifetime of the root.

Nothing is released until the owner explicitly calls `stop()`, and even then
the system registry is left dirty. A fleet of short-lived machines therefore
requires an application-level reaper.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

# A child that stays busy: a long `after` timer keeps its loop and timer task
# alive, standing in for a real invoked service (an exchange poll, a stream).
CHILD = {
    "id": "leg",
    "initial": "work",
    "states": {
        "work": {"after": {100_000: {"target": "fin"}}},
        "fin": {"type": "final"},
    },
}

SPAWN = {"type": "spawn_leg", "params": {"id": "legA", "systemId": "legsys"}}

CFG = {
    "id": "order",
    "initial": "pending",
    "context": {"blob": None},
    "states": {
        "pending": {"entry": [SPAWN], "on": {"FILL": "filled"}},
        "filled": {"type": "final"},
    },
}


async def main() -> int:
    ok = True
    machine = create_machine(
        CFG, logic=MachineLogic(services={"leg": create_machine(CHILD)})
    )
    interp = Interpreter(machine)
    interp.context["blob"] = ["x"] * 50_000  # something worth reclaiming
    await interp.start()
    await asyncio.sleep(0.05)
    print(
        f"OBSERVED while running: actors={sorted(interp._actors)} "
        f"system={sorted(interp.system.get_all())}"
    )

    await interp.send("FILL")  # -> top-level final state
    await asyncio.sleep(0.15)

    tasks_live = len([t for t in asyncio.all_tasks() if not t.done()])
    child = next(iter(interp._actors.values()), None)
    print(f"OBSERVED status={interp.status!r} is_running={interp.is_running}")
    print(
        f"OBSERVED context retained: len(blob)={len(interp.context['blob'])}"
    )
    print(f"OBSERVED actors after done  = {sorted(interp._actors)}")
    print(
        f"OBSERVED child after done: status="
        f"{child.status if child else None!r} event_loop_done="
        f"{child._event_loop_task.done() if child else None}"
    )
    print(
        f"OBSERVED system registry after done = "
        f"{sorted(interp.system.get_all())}"
    )
    print(f"OBSERVED live asyncio tasks after done = {tasks_live}")

    leaked_on_done = bool(interp._actors) or (
        child is not None and child.status == "running"
    )

    await interp.stop()
    await asyncio.sleep(0.05)
    print(
        f"OBSERVED after explicit stop(): actors={sorted(interp._actors)} "
        f"system={sorted(interp.system.get_all())}"
    )
    leaked_after_stop = bool(interp.system.get_all())

    print(
        "EXPECTED on reaching a top-level final state: child actors stopped, "
        "their tasks cancelled, system-registry entries removed and context "
        "releasable — without the owner calling stop(); and stop() must in "
        "any case leave the system registry empty"
    )

    ok = leaked_on_done and leaked_after_stop
    print(
        "RESULT:",
        (
            "REPRODUCED (done machine keeps children running; registry entry "
            "survives even stop())"
            if ok
            else "NOT REPRODUCED"
        ),
    )
    return 1 if ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
