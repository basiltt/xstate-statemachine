"""LC-28 repro: every invoked child-machine actor costs two asyncio tasks,
one of which polls at 5 ms instead of awaiting a completion future.

Counts live asyncio tasks as N child actors are invoked, and counts how many
times the event loop is woken while the children simply idle.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from xstate_statemachine import Interpreter, MachineLogic, create_machine
from xstate_statemachine import interpreter as interp_mod

logging.disable(logging.CRITICAL)

CHILD = {
    "id": "leg",
    "initial": "working",
    "states": {
        "working": {"on": {"FINISH": "done"}},
        "done": {"type": "final"},
    },
}


def parent_cfg(n: int) -> dict:
    return {
        "id": "book",
        "initial": "running",
        "states": {
            "running": {
                "invoke": [{"id": f"leg{i}", "src": "leg"} for i in range(n)]
            }
        },
    }


async def measure(n: int) -> tuple[int, float]:
    machine = create_machine(
        parent_cfg(n),
        logic=MachineLogic(services={"leg": create_machine(CHILD)}),
    )
    base = len(asyncio.all_tasks())
    interp = await Interpreter(machine).start()
    await asyncio.sleep(0.05)
    tasks = len(asyncio.all_tasks()) - base

    # Measure loop wakeups while the children are idle: each poller wakes
    # 1/_ACTOR_POLL_INTERVAL times per second doing nothing.
    wakeups = 0
    t_end = time.monotonic() + 0.2
    while time.monotonic() < t_end:
        await asyncio.sleep(0)
        wakeups += 1
    await interp.stop()
    return tasks, wakeups


async def main() -> int:
    # 0.8.0 (#43): the acceptance criteria require the constant to be gone.
    poll_interval = getattr(interp_mod, "_ACTOR_POLL_INTERVAL", None)
    print(f"OBSERVED _ACTOR_POLL_INTERVAL = {poll_interval}")
    counts = {}
    for n in (0, 2, 10, 50):
        tasks, _ = await measure(n)
        counts[n] = tasks
        print(f"OBSERVED children={n:>3} -> live asyncio tasks = {tasks}")
    print("EXPECTED ~1 task per child (a lifecycle task awaiting a completion")
    print("EXPECTED future), i.e. no dedicated 5 ms polling task per child")

    per_child = [(counts[n] - counts[0]) / n for n in (2, 10, 50)]
    print(f"OBSERVED tasks per child = {per_child}")
    polling = poll_interval is not None and poll_interval <= 0.01
    two_per_child = all(p >= 2 for p in per_child)
    print(
        f"OBSERVED dedicated poll loop present = {polling}; "
        f"two-tasks-per-child = {two_per_child}"
    )
    bad = polling and two_per_child
    print(
        "RESULT:",
        "REPRODUCED (2 tasks/child, 5 ms poll)" if bad else "NOT REPRODUCED",
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
