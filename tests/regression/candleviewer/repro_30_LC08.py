"""LC-08 repro: an unknown target state is never validated and is a silent no-op.

An unknown ACTION name fails loudly (ImplementationMissingError, raised out of
`start()`). An unknown TARGET name does not: it passes `create_machine()`, and
at runtime the async Interpreter swallows the StateNotFoundError in its event
loop, leaving the machine in its old state, still running, with no signal to
the caller.
"""

import asyncio
import sys

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.interpreter import Interpreter

BAD_TARGET = {
    "id": "m",
    "initial": "s",
    "states": {"s": {"on": {"GO": "nowhere_at_all"}}, "t": {}},
}

BAD_ACTION = {
    "id": "m",
    "initial": "s",
    "states": {"s": {"entry": ["no_such_action"]}},
}


async def main() -> int:
    # Control: an unknown ACTION name fails loudly (at start()).
    action_err = None
    try:
        m = create_machine(BAD_ACTION, logic=MachineLogic())
        await Interpreter(m).start()
    except Exception as exc:  # noqa: BLE001
        action_err = type(exc).__name__

    # Subject: an unknown TARGET name.
    create_err = None
    try:
        machine = create_machine(BAD_TARGET, logic=MachineLogic())
    except Exception as exc:  # noqa: BLE001
        create_err = type(exc).__name__
        print(f"OBSERVED: create_machine raised {create_err}")
        print("RESULT: PASS")
        return 0

    interp = await Interpreter(machine).start()
    send_err = None
    try:
        await interp.send("GO")
        await asyncio.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        send_err = type(exc).__name__
    state = sorted(interp.current_state_ids)
    running = interp.is_running
    await interp.stop()

    print(f"OBSERVED: unknown action -> {action_err} (raised out of start())")
    print(
        f"OBSERVED: unknown target -> create_machine={create_err} "
        f"send={send_err} state={state} running={running}"
    )
    print(
        "EXPECTED: unknown target raises at create_machine() (like unknown actions)"
    )

    ok = False
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
