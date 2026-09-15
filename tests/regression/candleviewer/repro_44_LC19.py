"""LC-19 - restoring a snapshot taken mid-`invoke` produces a parked machine.

An order machine is snapshotted while `submitting` has a live `invoke` in
flight. After `from_snapshot(...).start()` the machine reports
`status == "running"` and sits in `o.submitting`, but the service was never
restarted and `submitting`'s entry actions never re-ran: nothing will ever
drive it to `submitted`.
"""

from __future__ import annotations

import asyncio
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine

calls = {"place": 0, "entry": 0}


async def place(interp, ctx, evt):  # noqa: ANN001
    calls["place"] += 1
    await asyncio.sleep(5)  # request in flight when the snapshot is taken
    return {"ok": True}


def on_entry(interp, ctx, evt, action):  # noqa: ANN001
    calls["entry"] += 1


CFG = {
    "id": "o",
    "initial": "submitting",
    "states": {
        "submitting": {
            "entry": ["on_entry"],
            "invoke": {"id": "place", "src": "place", "onDone": "submitted"},
        },
        "submitted": {},
    },
}
LOGIC = MachineLogic(actions={"on_entry": on_entry}, services={"place": place})


async def main() -> int:
    interp = await Interpreter(create_machine(CFG, logic=LOGIC)).start()
    await asyncio.sleep(0.1)
    snapshot = interp.get_snapshot()
    await interp.stop()
    print(f"OBSERVED pre-crash : state={sorted(interp.current_state_ids)} "
          f"place_calls={calls['place']} entry_calls={calls['entry']}")

    calls["place"] = calls["entry"] = 0
    restored = Interpreter.from_snapshot(snapshot, create_machine(CFG, logic=LOGIC))
    await restored.start()
    await asyncio.sleep(0.3)
    print(f"OBSERVED restored  : state={sorted(restored.current_state_ids)} "
          f"place_calls={calls['place']} entry_calls={calls['entry']} "
          f"status={restored.status!r}")
    print("OBSERVED no API reports that `o.submitting` has an invoke that is not running")
    print("EXPECTED restored  : the `place` invoke is restarted (place_calls >= 1) "
          "under an opt-in flag, or an API enumerating stalled invokes so the "
          "application can re-drive them")
    await restored.stop()
    return 1 if calls["place"] == 0 else 0


sys.exit(asyncio.run(main()))
