# tests/test_battle_263_chained_invokes_receipt.py
"""#263 battle (found by the fastapi_orders rolling-upgrade scenario):
`apersisted()` snapshotted a machine still mid-step (`SnapshotMidStepError`)
on any chart with two plain `def` invokes in a row.

Why: ``await send(..., wait=True)`` resolves when the EVENT's macrostep
ends. A service completion is the NEXT macrostep (SCXML), which the run
loop starts at once; when that step enters another `def` invoke it awaits
the executor with the step open -- exactly when the block exited and
snapshotted. The sync engine's `send()` drains the whole chain, so
`persisted()` never saw it. Fix: `Interpreter.await_settled()` and a
bounded settle in `apersisted()` before the snapshot.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import SnapshotMidStepError
from src.xstate_statemachine.persistence import MemoryStore, apersisted


def _svc(i: Any, ctx: Any, e: Any) -> Dict[str, Any]:
    return {"ok": True}


def chain(n: int, service: Any = _svc) -> Any:
    states: Dict[str, Any] = {"idle": {"on": {"GO": "s0"}}}
    for k in range(n):
        nxt = f"s{k + 1}" if k + 1 < n else "done"
        states[f"s{k}"] = {
            "invoke": {"id": f"i{k}", "src": "svc", "onDone": nxt}
        }
    states["done"] = {"type": "final"}
    return create_machine(
        {"id": "m", "initial": "idle", "states": states},
        logic=MachineLogic(services={"svc": service}),
    )


def test_sync_engine_settles_the_whole_chain_inside_send() -> None:
    i = SyncInterpreter(chain(3)).start()
    i.send("GO")
    assert i.current_state_ids == {"m.done"} and i.status == "done"
    i.stop()


def test_async_receipt_is_the_events_macrostep_not_the_chain() -> None:
    """Pins the documented contract so a future 'fix' does not silently
    widen the receipt: the receipt describes GO's step (idle -> s0); the
    completions are later steps. `await_settled()` is how to wait for
    those."""

    async def go() -> None:
        i = await Interpreter(chain(3)).start()
        r = await i.send("GO", wait=True)
        assert set(r.state_ids) == {"m.s0"} and r.changed
        assert await i.await_settled(5.0) is True
        assert i.current_state_ids == {"m.done"} and i.status == "done"
        assert json.loads(i.get_snapshot())["state_ids"] == ["m.done"]
        await i.stop()

    asyncio.run(go())


@pytest.mark.parametrize("n", [1, 2, 5])
def test_apersisted_saves_the_settled_state_for_n_chained_invokes(
    n: int,
) -> None:
    store = MemoryStore()

    async def go() -> None:
        async with apersisted(store, "k", chain(n)) as i:
            await i.send("GO", wait=True)

    asyncio.run(go())
    rec = store.load("k")
    assert rec is not None
    blob = json.loads(rec.snapshot)
    assert blob["state_ids"] == ["m.done"] and blob["status"] == "done"


def test_apersisted_settle_timeout_zero_restores_the_old_behaviour() -> None:
    """`settle_timeout=0` is the opt-out: the block exits as soon as the
    receipt resolves and the snapshot is refused loudly if mid-step --
    the pre-#263 contract, still honest."""
    store = MemoryStore()

    def slow(i: Any, ctx: Any, e: Any) -> Dict[str, Any]:
        time.sleep(0.05)
        return {}

    async def go() -> None:
        async with apersisted(
            store, "k", chain(2, slow), settle_timeout=0
        ) as i:
            await i.send("GO", wait=True)

    with pytest.raises(SnapshotMidStepError):
        asyncio.run(go())
    assert store.load("k") is None  # nothing torn was written


def test_await_settled_is_bounded_by_its_timeout() -> None:
    def forever(i: Any, ctx: Any, e: Any) -> Dict[str, Any]:
        time.sleep(0.4)
        return {}

    async def go() -> float:
        i = await Interpreter(chain(2, forever)).start()
        await i.send("GO", wait=True)
        t0 = time.monotonic()
        settled = await i.await_settled(0.05)
        elapsed = time.monotonic() - t0
        assert settled is False
        await i.stop()
        return elapsed

    assert asyncio.run(go()) < 0.3


def test_await_settled_ignores_a_pending_after_timer() -> None:
    """A fired/armed `after` is a clock-driven process, not owed work: a
    machine sitting in a state with a live timer IS settled (otherwise a
    `persisted()` block on any SLA chart would wait out the SLA)."""
    cfg = {
        "id": "t",
        "initial": "a",
        "states": {"a": {"after": {"3600000": "b"}}, "b": {}},
    }

    async def go() -> bool:
        i = await Interpreter(create_machine(cfg)).start()
        t0 = time.monotonic()
        ok = await i.await_settled(5.0)
        assert time.monotonic() - t0 < 1.0
        await i.stop()
        return ok

    assert asyncio.run(go()) is True


def test_await_settled_on_a_stopped_machine_returns_at_once() -> None:
    async def go() -> bool:
        i = await Interpreter(chain(1)).start()
        await i.stop()
        return await i.await_settled(5.0)

    assert asyncio.run(go()) is True
