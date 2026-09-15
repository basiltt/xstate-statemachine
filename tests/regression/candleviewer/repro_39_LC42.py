"""LC-42 repro: `send()` is fire-and-forget; a statechart cannot answer.

`Interpreter.send()` is `await self._event_queue.put(event)` — it resolves as
soon as the event is *queued*, not when it is *processed*. The caller gets no
handle on the resulting transition, so "ask the machine and act on the answer"
(a kill switch, a rate governor, a risk lockout) has to poll, and the answer
arrives an unbounded time later.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import statistics
import sys
import time

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

CFG = {
    "id": "gov",
    "initial": "open",
    "states": {
        "open": {"on": {"TRIP": {"target": "tripped"}, "NOISE": {}}},
        "tripped": {"type": "final"},
    },
}

BACKGROUND = 2_000


async def main() -> int:
    ok = True
    interp = await Interpreter(create_machine(CFG, logic=MachineLogic())).start()

    # 1) send() returns None — no future/receipt to await.
    ret = await interp.send("NOISE")
    sig = inspect.signature(Interpreter.send)
    print(f"OBSERVED Interpreter.send(...) returned {ret!r}; return annotation "
          f"= {sig.return_annotation!r}")
    print("EXPECTED an awaitable receipt resolving after the event is processed")
    if ret is not None:
        ok = False

    # 2) After `await send(TRIP)` the machine has NOT transitioned yet.
    interp2 = await Interpreter(create_machine(CFG, logic=MachineLogic())).start()
    await interp2.send("TRIP")
    state_right_after = set(interp2.current_state_ids)
    print(f"OBSERVED state immediately after `await send('TRIP')` = {state_right_after}")
    print("EXPECTED {'gov.tripped'} (XState `actor.send` processes synchronously)")
    if "gov.tripped" not in state_right_after:
        ok = False
    await interp2.stop()

    # 3) The decision latency under a modest backlog. Caller must poll.
    lat = []
    for _ in range(5):
        i = await Interpreter(create_machine(CFG, logic=MachineLogic())).start()
        for n in range(BACKGROUND):
            await i.send("NOISE", n=n)
        t0 = time.perf_counter()
        await i.send("TRIP")
        while "gov.tripped" not in i.current_state_ids:
            await asyncio.sleep(0)  # the only available "answer" mechanism
        lat.append((time.perf_counter() - t0) * 1000)
        await i.stop()
    print(
        f"OBSERVED decision latency behind {BACKGROUND} queued events: "
        f"p50={statistics.median(lat):.2f}ms max={max(lat):.2f}ms (poll loop)"
    )
    print("EXPECTED O(1) synchronous answer, or a priority send that jumps the queue")
    if statistics.median(lat) > 1.0:
        ok = False

    # 4) No priority/urgent send exists.
    prio = [n for n in dir(interp) if "prio" in n.lower() or "urgent" in n.lower()]
    print(f"OBSERVED priority-send API = {prio}")
    print("EXPECTED e.g. `send(..., priority=True)` or `send_sync()`")
    if not prio:
        ok = False

    await interp.stop()
    print("RESULT:", "REPRODUCED (send cannot answer)" if not ok else "NOT REPRODUCED")
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
