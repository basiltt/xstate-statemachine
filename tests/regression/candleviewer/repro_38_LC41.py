"""LC-41 repro: unbounded interpreter queue, no backpressure, no depth API.

`Interpreter._event_queue` is a private, unbounded `asyncio.Queue`. A producer
can enqueue an arbitrary number of events faster than the single consumer
drains them: `send()` never blocks, never raises, never drops, and there is no
public way to observe how far behind the machine is.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    QueueOverflowError,
    create_machine,
)

logging.disable(logging.CRITICAL)

BURST = 20_000
SLOW_MS = 2.0

CFG = {
    "id": "gw",
    "initial": "idle",
    "states": {"idle": {"on": {"TICK": {"actions": ["work"]}}}},
}


async def work(interp, ctx, event, action_def):  # noqa: ANN001
    await asyncio.sleep(SLOW_MS / 1000.0)  # a realistic slow handler


async def main() -> int:
    ok = True
    logic = MachineLogic(actions={"work": work})
    # 0.8.0 (#38): the default queue stays unbounded (the issue's own design
    # note: `max_queue_size=None` reproduces 0.7.x byte-for-byte). The
    # acceptance criteria are about the OPT-IN bound + policy, so build the
    # interpreter with one and expect backpressure.
    interp = await Interpreter(
        create_machine(CFG, logic=logic), max_queue_size=1000
    ).start()

    # 1) No public queue-depth API of any kind.
    public = [n for n in dir(interp) if not n.startswith("_")]
    depth_api = [
        n
        for n in public
        if any(
            k in n.lower()
            for k in ("queue", "qsize", "backlog", "pending_event")
        )
    ]
    print(f"OBSERVED public queue/depth API on Interpreter = {depth_api}")
    print("EXPECTED something like `queue_depth` / `qsize()` to be public")
    if not depth_api:
        ok = False

    # 2) A burst of 20,000 events is accepted with zero backpressure.
    t0 = time.monotonic()
    raised = 0
    for i in range(BURST):
        try:
            await interp.send("TICK", i=i)
        except QueueOverflowError:
            raised += 1
    enqueue_ms = (time.monotonic() - t0) * 1000
    backlog = interp.queue_depth  # public since 0.8.0
    print(
        f"OBSERVED {BURST} send() calls accepted in {enqueue_ms:.1f} ms, "
        f"0 dropped, {raised} raised (QueueOverflowError); backlog = {backlog}"
    )
    print(
        "EXPECTED either a bounded queue that applies backpressure/raises, "
        "or at minimum an observable depth so a caller can shed load"
    )
    if backlog > 1000:
        ok = False

    # 3) The latency an event enqueued now will experience is unbounded and
    #    invisible: nothing in the public API predicts it.
    t1 = time.monotonic()
    try:
        await interp.send("TICK", i=-1)
    except QueueOverflowError:
        pass  # saturation IS detectable now -- that is the point
    submit_ms = (time.monotonic() - t1) * 1000
    print(
        f"OBSERVED send() of one more event returned in {submit_ms:.3f} ms "
        f"while ~{backlog} events (~{backlog * SLOW_MS / 1000:.1f} s of work) "
        "are still queued ahead of it"
    )
    print("EXPECTED a way to detect this saturation before enqueuing")

    # 4) Constructing with a bound is not supported.
    try:
        Interpreter(create_machine(CFG, logic=logic), max_queue_size=100)
        print("OBSERVED Interpreter(..., max_queue_size=100) accepted")
    except TypeError as exc:
        print(
            f"OBSERVED Interpreter(..., max_queue_size=100) -> TypeError: {exc}"
        )
        ok = False
    print("EXPECTED an optional bound + overflow policy")

    await interp.stop()
    print(
        "RESULT:",
        (
            "REPRODUCED (unbounded, unobservable queue)"
            if not ok
            else "NOT REPRODUCED"
        ),
    )
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
