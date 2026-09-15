"""LC-22 repro: `from_snapshot` assigns the restored context wholesale.

`base_interpreter.py:872` does `interpreter.context = snapshot["context"]`.
Context keys added to the machine definition after a snapshot was written
are therefore MISSING from the restored interpreter: the machine's own
default context is never merged underneath the persisted one. An action
shipped with the new schema then raises KeyError on live restored state.

Exit code 1 on failure.
"""

from __future__ import annotations

import asyncio
import json
import logging

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

V1 = {
    "id": "order",
    "initial": "submitting",
    "context": {"order_id": "A-1", "qty": 10},
    "states": {
        "submitting": {"on": {"FILL": {"target": "filled"}}},
        "filled": {},
    },
}
# v2 of the same machine: two context keys added by a later release.
V2 = json.loads(json.dumps(V1))
V2["context"] = {"order_id": "A-1", "qty": 10, "cum_qty": 0, "venue": "X"}
V2["states"]["submitting"]["on"]["FILL"]["actions"] = ["book"]

ERRORS: list[str] = []


def book(i, c, e, a):  # noqa: ANN001
    # Written against the v2 schema, where `cum_qty` always exists.
    try:
        c["cum_qty"] = c["cum_qty"] + 1
    except KeyError as exc:
        ERRORS.append(f"KeyError: {exc}")


async def main() -> int:
    ok = True
    i1 = await Interpreter(create_machine(V1)).start()
    snap = i1.get_snapshot()
    await i1.stop()

    m2 = create_machine(V2, logic=MachineLogic(actions={"book": book}))
    i2 = Interpreter.from_snapshot(snap, m2)
    missing = sorted({"cum_qty", "venue"} - set(i2.context))
    print(f"OBSERVED restored context     = {i2.context}")
    print(
        "EXPECTED restored context     = "
        "{'order_id': 'A-1', 'qty': 10, 'cum_qty': 0, 'venue': 'X'}"
    )
    print(f"OBSERVED missing default keys = {missing}")
    print("EXPECTED missing default keys = []")
    if missing:
        ok = False

    # The missing keys are not cosmetic: v2 logic fails on restored state.
    await i2.start()
    await i2.send("FILL")
    await asyncio.sleep(0.1)
    await i2.stop()
    print(f"OBSERVED action errors        = {ERRORS}")
    print("EXPECTED action errors        = []")
    if ERRORS:
        ok = False

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
