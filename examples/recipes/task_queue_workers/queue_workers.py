# examples/recipes/task_queue_workers/queue_workers.py
# -----------------------------------------------------------------------------
# 🧵 load -> send -> persist, by hand, for RQ, arq and Dramatiq (#308)
# -----------------------------------------------------------------------------
# 🏛️ A job carries only (key, event, payload) -- never a pickled machine.
#    The worker loads the snapshot, sends ONE event, and saves under an
#    optimistic version check. When two jobs for the same key race, one
#    save raises `ConflictError`; the loser reloads and re-applies, so no
#    update is lost. That loop is `apply_event` below; each queue library
#    only decides WHERE the function runs.
# 💡 No queue library is imported at module import time: RQ takes a plain
#    function, arq takes an `async def job(ctx, ...)`, and Dramatiq wraps
#    one with `dramatiq.actor` -- done lazily in `dramatiq_actor()`.
# -----------------------------------------------------------------------------
"""The statechart-task pattern, written by hand for three queues."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.persistence import (
    ConflictError,
    apersisted,
    persisted,
)

HERE = Path(__file__).resolve().parent
RETRIES = 5
#: Set by the worker process at start-up (`configure`).
STORE: Any = None
MACHINE: Any = None


def build_machine() -> Any:
    def count_scan(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["scans"] += 1

    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    logic = MachineLogic(actions={"countScan": count_scan})
    return create_machine(config, logic=logic)


def configure(store: Any, machine: Optional[Any] = None) -> None:
    """Worker start-up: one store handle per process."""
    global STORE, MACHINE
    STORE, MACHINE = store, machine or build_machine()


def apply_event(
    key: str, event: str, payload: Optional[Dict] = None
) -> Dict[str, Any]:
    """Load, send, save; reload and re-apply on `ConflictError`."""
    for attempt in range(RETRIES + 1):
        try:
            with persisted(STORE, key, MACHINE) as inst:
                receipt = inst.send(event, wait=True, **(payload or {}))
                state = inst.value
            return {"state": state, "changed": receipt.changed}
        except ConflictError:
            if attempt == RETRIES:
                raise  # let the queue's own retry/dead-letter take over


async def apply_event_async(
    key: str, event: str, payload: Optional[Dict] = None
) -> Dict[str, Any]:
    """The same loop on the async engine (for arq)."""
    for attempt in range(RETRIES + 1):
        try:
            async with apersisted(STORE, key, MACHINE) as inst:
                receipt = await inst.send(event, wait=True, **(payload or {}))
                state = inst.value
            return {"state": state, "changed": receipt.changed}
        except ConflictError:
            if attempt == RETRIES:
                raise


# -- RQ: `queue.enqueue(rq_job, "shipment.42", "PICKED_UP")` ------------------
def rq_job(key: str, event: str, payload: Optional[Dict] = None) -> Dict:
    return apply_event(key, event, payload)


# -- arq: `WorkerSettings.functions = [arq_job]`;
#         `await redis.enqueue_job("arq_job", "shipment.42", "PICKED_UP")` ---
async def arq_job(
    ctx: Dict, key: str, event: str, payload: Optional[Dict] = None
) -> Dict:
    return await apply_event_async(key, event, payload)


# -- Dramatiq: `dramatiq_actor().send("shipment.42", "PICKED_UP")` ----------
def dramatiq_job(key: str, event: str, payload: Optional[Dict] = None) -> None:
    apply_event(key, event, payload)  # Dramatiq discards return values


def dramatiq_actor(**options: Any) -> Any:
    import dramatiq  # soft: only the Dramatiq worker needs it

    return dramatiq.actor(dramatiq_job, max_retries=3, **options)
