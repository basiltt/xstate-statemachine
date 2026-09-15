"""LC-07 repro: relative `.child` targets resolve to nothing, silently.

XState v5 defines a leading-dot target (`target: ".A2"`) as relative to the
*transition's source state* — i.e. a CHILD of the source. This library's
resolver bases the lookup on the source's PARENT instead (resolver.py:199-207),
so `.A2` on source `m.A` looks for `m.A2`, which does not exist. The resulting
StateNotFoundError is then swallowed by the async Interpreter's run loop
(interpreter.py:479-487): no exit/entry actions, no state change, no error
reaches the caller and the machine keeps running.
"""

import asyncio
import sys

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.interpreter import Interpreter

CONFIG = {
    "id": "m",
    "initial": "A",
    "states": {
        "A": {
            "initial": "A1",
            "on": {"GO": {"target": ".A2"}},
            "states": {"A1": {"exit": ["xA1"]}, "A2": {"entry": ["eA2"]}},
        }
    },
}


async def main() -> int:
    log = []
    logic = MachineLogic(
        # 📝 Actions receive (interpreter, context, event, action_def) -- the
        #    original 3-arg lambda bound `n` to the ActionDefinition, which
        #    made the log compare unequal even once the fix landed.
        actions={n: (lambda i, c, e, a, n=n: log.append(n)) for n in ("xA1", "eA2")}
    )
    machine = create_machine(CONFIG, logic=logic)
    interp = await Interpreter(machine).start()

    raised = None
    try:
        await interp.send("GO")
        await asyncio.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"

    state = sorted(interp.current_state_ids)
    await interp.stop()

    print(f"OBSERVED: state={state} actions={log} raised={raised}")
    print("EXPECTED: state=['m.A.A2'] actions=['xA1', 'eA2'] raised=None")
    print("EXPECTED (acceptable alternative): create_machine() rejects '.A2'")
    print(
        "NOTE: the dot is resolved parent-relative, so '.A2' from source 'm.A' "
        "looks for 'm.A2' (a sibling), not the child 'm.A.A2'."
    )

    ok = state == ["m.A.A2"] and log == ["xA1", "eA2"]
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
