# examples/async/features/can_and_pending_events/can_and_pending_events_runner.py
# -----------------------------------------------------------------------------
# 🔮 can() as a dry-run vs. an actually-queued inbox (0.8.0)
# -----------------------------------------------------------------------------
"""Contrasts `interpreter.can()` with `queue_depth`/`pending_events`.

`can(event)` evaluates guards against the CURRENT configuration and answers
"would this transition right now?" without touching the inbox at all --
useful for disabling a UI button before the user even tries. `queue_depth`
and `pending_events` instead inspect events that have already been
ACCEPTED but not yet processed -- a different question, "what is still
waiting?". `drain_pending()` removes that backlog without processing it,
the tool a graceful-shutdown path uses to persist accepted work.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import Interpreter, MachineLogic, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = {
    "id": "door",
    "initial": "locked",
    "context": {"has_key": False},
    "states": {
        "locked": {
            "on": {
                "UNLOCK": {"target": "unlocked", "guard": "has_key"},
                "PING": {"actions": ["noop"]},
            }
        },
        "unlocked": {"on": {"LOCK": "locked"}},
    },
}


def noop(interpreter, context, event, action_def) -> None:
    """💤 Does nothing; exists only to give PING something to process."""


def has_key(context: Dict[str, Any], event: Any) -> bool:
    """🔑 Guard: only unlock when the context says the key is present."""
    return context["has_key"]


async def main() -> None:
    """🚀 can() predicts; queue_depth inspects; drain_pending() clears."""
    print("\n--- 🔮 can() / pending_events Simulation ---")
    logic = MachineLogic(actions={"noop": noop}, guards={"has_key": has_key})
    machine = create_machine(CONFIG, logic=logic)
    interpreter = await Interpreter(machine).start()

    logger.info(f"can('UNLOCK') without a key: {interpreter.can('UNLOCK')}")
    assert interpreter.can("UNLOCK") is False  # guard fails, no side effect
    assert interpreter.queue_depth == 0  # can() never touches the inbox

    interpreter.context["has_key"] = True
    logger.info(f"can('UNLOCK') with a key: {interpreter.can('UNLOCK')}")
    assert interpreter.can("UNLOCK") is True

    # 📥 Queue three PINGs without awaiting, so they pile up in the inbox
    #    before the run loop (a separate task) gets a chance to drain them.
    await interpreter.send("PING", wait=False)
    await interpreter.send("PING", wait=False)
    await interpreter.send("PING", wait=False)
    logger.info(
        f"queue_depth right after queuing: {interpreter.queue_depth}, "
        f"pending_events: {[e.type for e in interpreter.pending_events]}"
    )
    assert interpreter.queue_depth == 3

    drained = await interpreter.drain_pending()
    logger.info(f"Drained without processing: {[e.type for e in drained]}")
    assert [e.type for e in drained] == ["PING", "PING", "PING"]
    assert interpreter.queue_depth == 0

    await asyncio.sleep(0.02)  # let the (now-empty) run loop settle
    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
