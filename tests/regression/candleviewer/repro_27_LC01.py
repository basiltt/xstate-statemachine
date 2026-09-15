"""LC-01 repro: an action that raises still commits the transition, and there
is no programmatic error channel — `send()` returns normally, the machine keeps
`status == "running"`, the target state is entered, and `on_transition` fires as
though the transition succeeded.

Exits 1 when the defect is present.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, MachineLogic, create_machine
from xstate_statemachine.plugins import PluginBase

logging.disable(logging.CRITICAL)  # keep output clean; the library only logs

CONFIG = {
    "id": "oms",
    "initial": "a",
    "context": {"trace": []},
    "states": {
        "a": {"on": {"GO": {"target": "b", "actions": ["first", "explode", "third"]}}},
        "b": {"entry": ["entry_b"]},
    },
}


class Spy(PluginBase):
    def __init__(self) -> None:
        self.transitions: list[str] = []
        self.action_errors: list[str] = []

    def on_transition(self, interp, from_states, to_states, transition):
        self.transitions.append(sorted(to_states and interp.current_state_ids)[0])

    def on_action_error(self, interp, action_def, error):  # 0.6.0+
        self.action_errors.append(f"{action_def.type}:{type(error).__name__}")


async def main() -> int:
    def first(i, c, e, a):
        c["trace"].append("first")

    def explode(i, c, e, a):
        c["trace"].append("explode")
        raise RuntimeError("exchange rejected the order")

    def third(i, c, e, a):
        c["trace"].append("third")

    def entry_b(i, c, e, a):
        c["trace"].append("entry_b")

    logic = MachineLogic(
        actions={"first": first, "explode": explode, "third": third, "entry_b": entry_b}
    )
    spy = Spy()
    interp = Interpreter(create_machine(CONFIG, logic=logic))
    interp.use(spy)
    await interp.start()

    raised = None
    try:
        await interp.send("GO")
        await asyncio.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"

    states = sorted(interp.current_state_ids)
    trace = list(interp.context["trace"])
    status = interp.status
    await interp.stop()

    print(f"OBSERVED send() raised          : {raised}")
    print(f"OBSERVED trace                  : {trace}")
    print(f"OBSERVED state after failed act : {states}")
    print(f"OBSERVED interpreter.status     : {status}")
    print(f"OBSERVED on_transition fired    : {spy.transitions}")
    print(f"OBSERVED on_action_error fired  : {spy.action_errors}")
    print("EXPECTED: transition NOT committed (state stays ['oms.a']) or an error")
    print("EXPECTED: surfaced to the caller / a transition-failed hook; entry_b must")
    print("EXPECTED: not run and on_transition must not report success.")

    bad = states == ["oms.b"] and "entry_b" in trace and raised is None
    print("RESULT: DEFECT REPRODUCED" if bad else "RESULT: not reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
