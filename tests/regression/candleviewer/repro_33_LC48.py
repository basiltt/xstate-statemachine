"""LC-48 repro: no error-observability hooks on `PluginBase`.

Three failures that a production system must observe are invisible:

1. an action raising -> `on_transition` still fires as a success, and there
   is no `on_transition_failed(failed_actions)` hook;
2. a guard raising -> reported through `on_guard_evaluated(..., result=False)`,
   indistinguishable from a guard that legitimately returned False; there is
   no `on_guard_error`;
3. an event with no enabled transition -> silently discarded, with no
   `on_unhandled_event` hook (so a typo'd event name looks exactly like a
   legitimately ignored one).

Exits 1 when the hooks are absent / the failures are unobservable.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    create_machine,
)

logging.disable(logging.CRITICAL)

CFG = {
    "id": "order",
    "initial": "submitting",
    "context": {},
    "states": {
        "submitting": {
            "on": {
                "FILL": {"target": "filled", "actions": ["book"]},
                "CANCEL": {"target": "cancelled", "cond": "may_cancel"},
            }
        },
        "filled": {},
        "cancelled": {},
    },
}


def book(interpreter, context, event, action_def):  # noqa: ANN001
    raise RuntimeError("ledger write failed")


def may_cancel(context, event):  # noqa: ANN001
    raise RuntimeError("risk service unreachable")


class Recorder(PluginBase):
    def __init__(self) -> None:
        self.events: list = []

    def on_transition(
        self, interpreter, from_states, to_states, transition
    ):  # noqa: ANN001
        self.events.append(
            ("on_transition", sorted(interpreter.current_state_ids))
        )

    def on_action_error(self, interpreter, action, error):  # noqa: ANN001
        self.events.append(("on_action_error", action.type))

    def on_guard_evaluated(
        self, interpreter, guard_name, event, result
    ):  # noqa: ANN001
        self.events.append(("on_guard_evaluated", guard_name, result))


async def main() -> int:
    machine = create_machine(
        CFG,
        logic=MachineLogic(
            actions={"book": book}, guards={"may_cancel": may_cancel}
        ),
    )
    rec = Recorder()
    interp = Interpreter(machine).use(rec)
    await interp.start()
    await interp.send("TYPO_FILLED")  # 3. unhandled event
    await interp.send("CANCEL")  # 2. raising guard
    await interp.send("FILL")  # 1. raising action
    await asyncio.sleep(0.05)
    await interp.stop()

    missing = [
        h
        for h in (
            "on_transition_failed",
            "on_guard_error",
            "on_unhandled_event",
        )
        if not hasattr(PluginBase, h)
    ]
    declared_duck = [
        h for h in ("on_error", "on_done") if not hasattr(PluginBase, h)
    ]
    print("OBSERVED  plugin events:", rec.events)
    print("OBSERVED  final state:", sorted(interp.current_state_ids))
    print("OBSERVED  missing PluginBase hooks:", missing)
    print(
        "OBSERVED  duck-typed hooks not declared on PluginBase:", declared_duck
    )
    print(
        "EXPECTED  on_transition_failed / on_guard_error / on_unhandled_event declared; "
        "guard failure distinguishable from a False guard; typo'd event surfaced"
    )
    ok = not missing and not declared_duck
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
