"""LC-09 repro: a guard that raises is swallowed and reported as `False`.

A crashing risk check and a legitimately-failing risk check are indistinguishable
to every observer: same selected transition, no exception, and the plugin hook
`on_guard_evaluated` reports result=False in both cases. There is no
`on_guard_error` hook, so the defect is invisible.
"""

import asyncio
import sys

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.interpreter import Interpreter
from xstate_statemachine.plugins import PluginBase


class GuardSpy(PluginBase):
    def __init__(self) -> None:
        self.seen = []

    def on_guard_evaluated(self, interpreter, guard_type, event, result):  # noqa: ANN001
        self.seen.append((guard_type, result))


def build(guard_fn):
    cfg = {
        "id": "m",
        "initial": "s",
        "states": {
            "s": {
                "on": {
                    "GO": [
                        {"target": "primary", "guard": "risk_ok"},
                        {"target": "fallback"},
                    ]
                }
            },
            "primary": {},
            "fallback": {},
        },
    }
    return create_machine(cfg, logic=MachineLogic(guards={"risk_ok": guard_fn}))


async def run(guard_fn):
    spy = GuardSpy()
    interp = Interpreter(build(guard_fn))
    interp.use(spy)
    await interp.start()
    raised = None
    try:
        await interp.send("GO")
        await asyncio.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        raised = type(exc).__name__
    out = {"state": sorted(interp.current_state_ids), "raised": raised, "plugin": spy.seen}
    await interp.stop()
    return out


async def main() -> int:
    def falsy(c, e):  # noqa: ANN001
        return False

    def boom(c, e):  # noqa: ANN001
        raise ValueError("risk service unreachable")

    a = await run(falsy)
    b = await run(boom)
    print(f"OBSERVED: guard returns False -> {a}")
    print(f"OBSERVED: guard RAISES       -> {b}")
    print("EXPECTED: the two cases are distinguishable (raise, or on_guard_error hook)")
    ok = a != b
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
