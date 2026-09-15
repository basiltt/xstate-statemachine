"""LC-06: over-forgiving target resolution silently binds an unrelated state.

`order.submitting` declares `target: "filled"`. There is no `filled` sibling in
`order` — the only node whose last id segment is `filled` lives in a completely
unrelated region, `audit.archive.filled`. A conforming engine must fail (XState
raises at machine-creation time for an unresolvable target). This library walks
the whole tree and binds the foreign node.
"""

from __future__ import annotations

import asyncio
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine


async def main() -> int:
    cfg = {
        "id": "m",
        "type": "parallel",
        "context": {},
        "states": {
            "audit": {
                "initial": "archive",
                "states": {
                    "archive": {
                        "initial": "open",
                        "states": {"open": {}, "filled": {}},
                    }
                },
            },
            "order": {
                "initial": "submitting",
                "states": {
                    # ⚠️ `filled` does not exist inside `order`.
                    "submitting": {"on": {"FILL": "filled"}},
                    "done": {},
                },
            },
        },
    }
    interp = await Interpreter(
        create_machine(cfg, logic=MachineLogic())
    ).start()
    await interp.send("FILL")
    await asyncio.sleep(0.2)
    observed = sorted(interp.current_state_ids)
    await interp.stop()

    print("OBSERVED:", observed)
    print(
        "EXPECTED: create_machine() or send() to raise StateNotFoundError for "
        "unresolvable target 'filled'; never bind 'm.audit.archive.filled'"
    )
    bad = "m.audit.archive.filled" in observed
    print("BOUND_FOREIGN_STATE:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
