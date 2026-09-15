"""LC-29 repro: `invoke.input` is static, and it is ignored entirely when the
invoked `src` resolves to a child machine.

Two defects:
  1. A callable `input: ({context, event}) => ...` (XState v5) is stored
     verbatim as the function object — never called.
  2. Even a static dict `input` never reaches a spawned child machine's
     context; `_spawn_and_manage_actor` constructs `Interpreter(actor_machine)`
     with no `input` argument.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine

logging.disable(logging.CRITICAL)

CHILD = {
    "id": "leg",
    "initial": "work",
    "context": {"snapshot": None},
    "states": {"work": {"on": {"GO": "done"}}, "done": {"type": "final"}},
}

PARENT = {
    "id": "book",
    "context": {"profile": {"venue": "X", "size": 7}},
    "initial": "running",
    "states": {
        "running": {
            "invoke": {
                "id": "leg1",
                "src": "leg",
                "input": {"snapshot": {"venue": "X", "size": 7}},
            }
        }
    },
}


async def main() -> int:
    ok = True

    # 1) Callable input is never invoked — stored as-is on the definition.
    cfg = {
        **PARENT,
        "states": {
            "running": {
                "invoke": {
                    "id": "leg1",
                    "src": "leg",
                    "input": lambda ctx, evt: {"snapshot": ctx["profile"]},
                }
            }
        },
    }
    m = create_machine(
        cfg, logic=MachineLogic(services={"leg": create_machine(CHILD)})
    )
    inv = m.states["running"].invoke[0]
    print(
        f"OBSERVED type(invoke.input) with a callable = {type(inv.input).__name__}"
    )
    print(
        "EXPECTED it to be resolved per-spawn against {context, event} (a dict)"
    )
    if callable(inv.input):
        ok = False

    # 2) Static input never reaches the spawned child's context.
    parent_m = create_machine(
        PARENT, logic=MachineLogic(services={"leg": create_machine(CHILD)})
    )
    interp = await Interpreter(parent_m).start()
    await asyncio.sleep(0.05)
    child = next(iter(interp._actors.values()))
    print(f"OBSERVED spawned child context = {child.context}")
    print(f"OBSERVED spawned child .input  = {child.input!r}")
    print(
        "EXPECTED context = {'snapshot': {'venue': 'X', 'size': 7}} "
        "(invoke.input seeds the child)"
    )
    if child.context.get("snapshot") != {"venue": "X", "size": 7}:
        ok = False
    await interp.stop()

    print(
        "RESULT:",
        (
            "REPRODUCED (invoke.input static + ignored)"
            if not ok
            else "NOT REPRODUCED"
        ),
    )
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
