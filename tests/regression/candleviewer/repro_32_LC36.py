"""LC-36 repro: built-in action params must be nested under `"params"`.

The obvious spelling `{"type": "raise", "event": "X"}` parses without any
error or warning at `create_machine()` time and is a **silent no-op** at
runtime. Only `{"type": "raise", "params": {"event": "X"}}` works.

The same applies to every built-in action creator (`sendTo`, `log`,
`cancel`, ...): `ActionDefinition.__init__` reads `config.get("params")`
and nothing validates that a built-in got the params it requires.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from xstate_statemachine import Interpreter, create_machine

logging.disable(logging.CRITICAL)


def cfg(raise_action: dict) -> dict:
    return {
        "id": "eval",
        "initial": "idle",
        "states": {
            "idle": {"on": {"EVALUATE": {"target": "scoring"}}},
            "scoring": {"entry": [raise_action], "on": {"PLACE": "placed"}},
            "placed": {"type": "final"},
        },
    }


WRONG = {"type": "raise", "event": "PLACE"}  # the obvious spelling
RIGHT = {"type": "raise", "params": {"event": "PLACE"}}  # the working one


async def run(action: dict) -> tuple[str, list[str]]:
    machine = create_machine(cfg(action))
    interp = await Interpreter(machine).start()
    await interp.send("EVALUATE")
    await asyncio.sleep(0.05)
    states = list(interp.current_state_ids)
    status = interp.status
    await interp.stop()
    return status, states


async def main() -> int:
    ok = True

    # 1) The wrong spelling is accepted by create_machine() with no error.
    try:
        m = create_machine(cfg(WRONG))
        parsed = m.states["scoring"].entry[0]
        print(
            f"OBSERVED create_machine() accepted {WRONG} -> "
            f"type={parsed.type!r} params={parsed.params!r}"
        )
        print(
            "EXPECTED InvalidConfigError: built-in 'raise' requires "
            "params.event"
        )
        ok = False
    except Exception as exc:  # pragma: no cover - would be the fix
        print(f"OBSERVED create_machine() raised {type(exc).__name__}: {exc}")

    # 2) At runtime the wrong spelling does nothing.
    #    0.8.0 (#32): create_machine() now REJECTS the wrong spelling, so
    #    it cannot reach the runtime at all -- which is the fix this issue
    #    asked for ("or the wrong one to error"). Treat that as equivalent
    #    to the right spelling's outcome.
    try:
        status_w, states_w = await run(WRONG)
        print(f"OBSERVED wrong spelling -> status={status_w} states={states_w}")
    except Exception as exc:  # noqa: BLE001
        print(f"OBSERVED wrong spelling -> rejected at build: {type(exc).__name__}")
        status_w, states_w = "rejected", None
    status_r, states_r = await run(RIGHT)
    print(f"OBSERVED right spelling -> status={status_r} states={states_r}")
    print("EXPECTED both to reach 'eval.placed' (or the wrong one to error)")
    if states_w == states_r or states_w is None:
        ok = True and ok  # both worked, or wrong one errored -> not reproduced

    reproduced = (states_w is not None and states_w != states_r) or not ok
    print(
        "RESULT:",
        "REPRODUCED (misspelled built-in params silently ignored)"
        if reproduced
        else "NOT REPRODUCED",
    )
    return 1 if reproduced else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
