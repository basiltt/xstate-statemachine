"""LC-12 - `spawn_blocking_<key>` is honoured only by the SyncInterpreter.

The async `Interpreter` dispatches on `startswith("spawn_")`, so
`spawn_blocking_worker` takes the ordinary non-blocking path: the same action
name means two different things depending on the engine.

Measured by the wall time `start()` blocks while the child runs a 250 ms entry
action, plus whether the child actor survives in `_actors` (blocking spawn
keeps it, the sync non-blocking path reaps it on its background thread).
"""

from __future__ import annotations

import asyncio
import sys
import time

from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

CHILD_WORK_S = 0.25


def parent(action_type: str):
    def slow(interp, ctx, evt, action):  # noqa: ANN001
        time.sleep(CHILD_WORK_S)

    child = create_machine(
        {"id": "w", "initial": "done",
         "states": {"done": {"type": "final", "entry": ["slow"]}}},
        logic=MachineLogic(actions={"slow": slow}),
    )
    return create_machine(
        {"id": "p", "initial": "a", "states": {"a": {"entry": [action_type]}}},
        logic=MachineLogic(services={"worker": child}),
    )


async def main() -> int:
    res = {}
    for t in ("spawn_worker", "spawn_blocking_worker"):
        s = time.perf_counter()
        interp = await Interpreter(parent(t)).start()
        res[("async", t)] = (time.perf_counter() - s, len(interp._actors))
        await interp.stop()
    for t in ("spawn_worker", "spawn_blocking_worker"):
        s = time.perf_counter()
        interp = SyncInterpreter(parent(t)).start()
        res[("sync", t)] = (time.perf_counter() - s, len(interp._actors))
        time.sleep(0.4)
        interp.stop()

    for (engine, t), (el, actors) in res.items():
        print(f"OBSERVED {engine:5s} {t:22s} start_blocked_ms={el * 1000:6.0f} actors_after_spawn={actors}")

    a_plain, a_block = res[("async", "spawn_worker")][0], res[("async", "spawn_blocking_worker")][0]
    s_plain, s_block = res[("sync", "spawn_worker")][0], res[("sync", "spawn_blocking_worker")][0]
    print("OBSERVED async: spawn_ and spawn_blocking_ behave identically "
          f"({a_plain * 1000:.0f} ms vs {a_block * 1000:.0f} ms) - the `blocking` marker is ignored")
    print("OBSERVED sync : spawn_ is non-blocking and spawn_blocking_ blocks "
          f"({s_plain * 1000:.0f} ms vs {s_block * 1000:.0f} ms)")
    print("EXPECTED both engines agree on what `spawn_blocking_<key>` means: "
          "either blocking on both, or a NotSupportedError on the async engine")

    sync_distinguishes = s_block > s_plain + CHILD_WORK_S / 2
    async_distinguishes = abs(a_block - a_plain) > CHILD_WORK_S / 2
    return 0 if (async_distinguishes or not sync_distinguishes) else 1


sys.exit(asyncio.run(main()))
