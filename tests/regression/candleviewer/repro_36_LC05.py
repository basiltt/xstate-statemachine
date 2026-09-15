"""LC-05: `raise` is queued behind pending external events (no macrostep).

Entry into state `b` raises RAISED. An external EXTERNAL event is sent right
after GO. XState/SCXML settle the internal (raised) event within the same
macrostep, so the trace must be entry, RAISED, EXTERNAL.
"""

from __future__ import annotations

import asyncio
import sys
from typing import List

from xstate_statemachine import Interpreter, MachineLogic, create_machine


async def main() -> int:
    trace: List[str] = []

    def mark_entry(i, c, e, a):  # noqa: ANN001
        trace.append("entry")

    def rec(i, c, e, a):  # noqa: ANN001
        trace.append(e.type)

    cfg = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"GO": "b"}},
            "b": {
                "entry": [
                    "mark_entry",
                    {"type": "raise", "params": {"event": "RAISED"}},
                ],
                "on": {
                    "RAISED": {"actions": ["rec"]},
                    "EXTERNAL": {"actions": ["rec"]},
                },
            },
        },
    }
    logic = MachineLogic(actions={"mark_entry": mark_entry, "rec": rec})
    interp = await Interpreter(create_machine(cfg, logic=logic)).start()
    await interp.send("GO")
    await interp.send("EXTERNAL")
    await asyncio.sleep(0.3)
    await interp.stop()

    expected = ["entry", "RAISED", "EXTERNAL"]
    print("OBSERVED:", trace)
    print("EXPECTED:", expected)
    return 0 if trace == expected else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
