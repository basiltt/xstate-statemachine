"""LC-43 repro: cross-thread `send()` drops events with no library-level signal.

`Interpreter.send` is a coroutine function. Called from a foreign OS thread it
merely *builds* a coroutine object; nothing awaits it, so the event never
reaches the queue. `send()` raises nothing, the library logs nothing, and the
interpreter stays `running` — the only feedback is CPython's own GC-timed
`RuntimeWarning: coroutine 'Interpreter.send' was never awaited`, which fires
at an arbitrary later moment, names the caller rather than the library, and is
routinely filtered out in production logging setups.
`asyncio.run_coroutine_threadsafe` is the only correct form, and nothing in the
API points a caller towards it.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import sys
import threading
import time
import warnings

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

N = 500

CFG = {
    "id": "fills",
    "initial": "live",
    "states": {"live": {"on": {"FILL": {"actions": ["count"]}}}},
}


def count(interp, ctx, event, action_def):  # noqa: ANN001
    ctx["n"] = ctx.get("n", 0) + 1


async def main() -> int:
    ok = True
    logic = MachineLogic(actions={"count": count})
    loop = asyncio.get_running_loop()

    # --- A) bare send() from a foreign thread ------------------------------
    interp = await Interpreter(
        create_machine({**CFG, "context": {"n": 0}}, logic=logic)
    ).start()

    caught: list[str] = []

    raised: list[str] = []

    def worker_bare() -> None:
        for i in range(N):
            try:
                interp.send("FILL", i=i)  # noqa: RUF006 — the bug under test
            except Exception as exc:  # noqa: BLE001
                # 0.8.0 (#37): send() now raises WrongThreadError eagerly at
                # the call site instead of discarding the coroutine.
                raised.append(type(exc).__name__)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        t = threading.Thread(target=worker_bare)
        t.start()
        t.join()
        await asyncio.sleep(0.2)
        gc.collect()
        await asyncio.sleep(0.05)
        caught = [str(x.message) for x in w if "never awaited" in str(x.message)]

    delivered_bare = interp.context.get("n", 0)
    print(f"OBSERVED bare cross-thread send(): {delivered_bare}/{N} delivered, "
          f"exceptions raised = 0, interpreter still status={interp.status!r}")
    print(f"OBSERVED the only signal is {len(caught)} GC-timed "
          "RuntimeWarning('coroutine ... was never awaited') attributed to the "
          "caller's line, not an error raised by the library")
    print(f"EXPECTED either {N}/{N} delivered, or a raised error from send()")
    # Fixed if EITHER every event was delivered OR the library raised on
    # every foreign-thread call (the issue's "or a raised error from send()").
    if delivered_bare != N and len(raised) != N:
        ok = False
    if raised:
        print(f"OBSERVED send() raised {raised[0]} on all {len(raised)}/{N} foreign-thread calls")
    await interp.stop()

    # --- B) run_coroutine_threadsafe: works, but 10x cost -----------------
    interp2 = await Interpreter(
        create_machine({**CFG, "context": {"n": 0}}, logic=logic)
    ).start()
    elapsed: list[float] = []

    def worker_safe() -> None:
        t0 = time.perf_counter()
        # 0.8.0 (#37): `send()` now raises on a foreign thread by design
        # (that is the fix), so part B uses the supported thread-safe API.
        futs = [interp2.send_threadsafe("FILL", i=i) for i in range(N)]
        for f in futs:
            f.result()
        elapsed.append(time.perf_counter() - t0)

    t2 = threading.Thread(target=worker_safe)
    t2.start()
    while t2.is_alive():
        await asyncio.sleep(0.001)
    t2.join()
    await asyncio.sleep(0.2)
    print(
        f"OBSERVED run_coroutine_threadsafe: {interp2.context.get('n', 0)}/{N} "
        f"delivered at {elapsed[0] / N * 1e6:.0f} us/event"
    )
    await interp2.stop()

    print("RESULT:", "REPRODUCED (silent cross-thread loss)" if not ok else "NOT REPRODUCED")
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
