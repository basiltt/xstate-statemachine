"""LC-34 repro: no strict mode — unknown event types and unvalidated payloads.

Three observations:
  1. `send("TYPOD_EVENT")` on a machine that has no such descriptor is a
     silent no-op: no exception, no error status, nothing a caller can
     branch on.
  2. Arbitrary payloads are accepted with no schema: `send("FILL",
     qty="not-a-number")` is stored verbatim in the event.
  3. There is no `strict` option anywhere: neither `create_machine()` nor
     `Interpreter()` accepts one (grep: no `strict=` in the runtime source).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sys

from xstate_statemachine import Interpreter, create_machine

logging.disable(logging.CRITICAL)

CFG = {
    "id": "order",
    "initial": "pending",
    "context": {"qty": 0},
    "states": {
        "pending": {"on": {"FILL": {"target": "filled"}}},
        "filled": {"type": "final"},
    },
}


async def main() -> int:
    ok = True

    # 1) No `strict` option exists on either public constructor.
    cm_params = list(inspect.signature(create_machine).parameters)
    it_params = list(inspect.signature(Interpreter.__init__).parameters)
    print(f"OBSERVED create_machine params = {cm_params}")
    print(f"OBSERVED Interpreter.__init__ params = {it_params}")
    print("EXPECTED a `strict` option on at least one of them")
    if "strict" in cm_params or "strict" in it_params:
        ok = False  # not reproduced

    # 2) A typo'd event is a silent no-op.
    interp = await Interpreter(create_machine(CFG)).start()
    before = list(interp.current_state_ids)
    raised = None
    try:
        await interp.send("FILLL")  # typo: should be FILL
        await asyncio.sleep(0.05)
    except Exception as exc:  # pragma: no cover - would be the fix
        raised = exc
    print(
        f"OBSERVED send('FILLL'): raised={raised!r} "
        f"status={interp.status} states={list(interp.current_state_ids)} "
        f"(was {before})"
    )
    print("EXPECTED under strict=True: an error naming the unknown event type")
    if raised is not None:
        ok = False

    # 3) Payloads are unvalidated.
    seen: list = []
    machine2 = create_machine(CFG)
    interp2 = await Interpreter(machine2).start()
    interp2.subscribe(lambda snap: seen.append(dict(snap.context)))
    await interp2.send("FILL", qty="not-a-number", side=object())
    await asyncio.sleep(0.05)
    print(
        f"OBSERVED send('FILL', qty='not-a-number') accepted; "
        f"status={interp2.status} states={list(interp2.current_state_ids)}"
    )
    print("EXPECTED under strict=True: payload validated against a schema")
    await interp.stop()
    await interp2.stop()

    print(
        "RESULT:",
        "REPRODUCED (no strict mode; unknown events and payloads unvalidated)"
        if ok
        else "NOT REPRODUCED",
    )
    return 1 if ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
