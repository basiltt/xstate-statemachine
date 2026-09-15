"""LC-16: `sendTo` cannot address an invoked actor by its `invoke` id/systemId.

Runs three identical parent machines that differ only in the name used as the
`send_to` target: the service key, the declared invoke `id`, and the declared
`systemId`. Only the service key delivers; the other two drop the event.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Dict, Optional

from xstate_statemachine import Interpreter, MachineLogic, create_machine

CHILD = create_machine(
    {
        "id": "child",
        "initial": "idle",
        "context": {},
        "states": {
            "idle": {
                "on": {
                    "PING": {
                        "actions": [
                            {"type": "send_parent", "params": {"event": "PONG"}}
                        ]
                    }
                }
            }
        },
    },
    logic=MachineLogic(),
)


async def attempt(to: str, invoke: Dict[str, Any]) -> Optional[str]:
    seen: Dict[str, Any] = {}

    def cap(i, c, e, a):  # noqa: ANN001
        seen["reply"] = e.type

    cfg = {
        "id": "p",
        "initial": "run",
        "context": {},
        "states": {
            "run": {
                "invoke": invoke,
                "on": {
                    "POKE": {
                        "actions": [
                            {
                                "type": "send_to",
                                "params": {"to": to, "event": "PING"},
                            }
                        ]
                    },
                    "PONG": {"target": "got", "actions": ["cap"]},
                },
            },
            "got": {},
        },
    }
    logic = MachineLogic(actions={"cap": cap}, services={"child": CHILD})
    interp = await Interpreter(create_machine(cfg, logic=logic)).start()
    await asyncio.sleep(0.1)
    await interp.send("POKE")
    await asyncio.sleep(0.25)
    await interp.stop()
    return seen.get("reply")


async def main() -> int:
    observed = {
        "by_service_key": await attempt("child", {"id": "kid", "src": "child"}),
        "by_invoke_id": await attempt("kid", {"id": "kid", "src": "child"}),
        "by_system_id": await attempt(
            "kid", {"id": "kid", "src": "child", "systemId": "kid"}
        ),
    }
    expected = {k: "PONG" for k in observed}
    print("OBSERVED:", observed)
    print("EXPECTED:", expected)
    return 0 if observed == expected else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
