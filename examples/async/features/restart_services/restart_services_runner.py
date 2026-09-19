# examples/async/features/restart_services/restart_services_runner.py
# -----------------------------------------------------------------------------
# 🔁 from_snapshot(restart_services=True) (0.8.0, #44)
# -----------------------------------------------------------------------------
"""Demonstrates ``restart_services=True`` on `from_snapshot`.

`from_snapshot` is, by default, a STATIC restore: it puts the state and
context back exactly as they were, but starts no `invoke` -- so a machine
snapshotted mid-invoke comes back parked, its pending work never
completing. `pending_invocations()` lists what is dormant; opting in
with `restart_services=True` re-invokes each of them from scratch through
the same path a live `_enter_states` would use. This is a deliberate
opt-in because the service reruns from the beginning, not resumes -- for
an order placement that means the caller needs an idempotency key.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import Interpreter, MachineLogic, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "order",
    "initial": "submitting",
    "context": {"acked": False},
    "states": {
        "submitting": {
            "invoke": {"src": "place", "id": "place", "onDone": "live"},
        },
        "live": {"entry": ["ack"]},
    },
}


def build_logic(calls: List[str]) -> MachineLogic:
    """🏗️ `place` records each call so a restart is visibly a re-run."""

    async def place(interpreter, context, event) -> str:
        calls.append("place")
        await asyncio.sleep(0.02)
        return "ok"

    def ack(interpreter, context, event, action_def) -> None:
        context["acked"] = True

    return MachineLogic(actions={"ack": ack}, services={"place": place})


async def main() -> None:
    """🚀 Snapshot mid-invoke, restore statically, then restart it."""
    print("\n--- 🔁 restart_services Simulation ---")
    calls: List[str] = []
    logic = build_logic(calls)
    machine_with_logic = create_machine(CONFIG, logic=logic)
    interpreter = await Interpreter(machine_with_logic).start()
    await asyncio.sleep(0.005)  # 'place' has started, is far from done
    snapshot = interpreter.get_snapshot()
    await interpreter.stop()
    logger.info(f"Snapshot taken mid-invoke; calls so far: {calls}")

    # 🧊 Static restore (default): parked, nothing pending is re-invoked.
    static_restore = Interpreter.from_snapshot(snapshot, machine_with_logic)
    logger.info(
        f"Static restore pending invocations: "
        f"{static_restore.pending_invocations()}"
    )
    assert static_restore.pending_invocations()

    # 🔁 Opt-in restart: `place` runs again, from scratch, and completes.
    restarted = Interpreter.from_snapshot(
        snapshot, machine_with_logic, restart_services=True
    )
    await restarted.start()
    # ⏳ Settle on the OBSERVABLE condition, not a fixed sleep: a slow CI
    #    runner can take longer than 50 ms to run a 20 ms service.
    for _ in range(400):
        if "order.live" in restarted.current_state_ids:
            break
        await asyncio.sleep(0.005)
    logger.info(f"After restart, calls: {calls}")
    logger.info(f"State: {restarted.current_state_ids}")
    assert calls.count("place") == 2  # original attempt + the restart
    assert "order.live" in restarted.current_state_ids

    await restarted.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
