# tests/persistence/test_battle_264_child_timers.py
"""#264 battle (agent A): durable `after` deadlines of CHILD actors.

📝 Decisions pinned here:
- A child's deadline lives in ``actors[<id>].snapshot.deadlines`` (the
  child blob is a full snapshot) and is NOT in the parent's
  ``pending_deadlines()`` -- each interpreter reports its own. LIMITATION:
  ``StateStore.save(deadlines=)`` indexes only the root's, so a scanner
  cannot wake a machine for a child-only deadline.
- ``from_snapshot(parent, restart_timers=...)`` forwards the policy (and
  the clock) to every restored child, and both engines start restored
  children -- so ``"fire_due"`` fires matured child timers, 3 levels deep.
  (BUG fixed: the policy was dropped and the sync engine never started
  restored children, so a child's SLA silently died.)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Tuple

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)

pytestmark = pytest.mark.timeout(30)

GRANDKID = {
    "id": "gk",
    "initial": "w",
    "states": {"w": {"after": {"7000": "d"}}, "d": {"type": "final"}},
}
KID = {
    "id": "kid",
    "initial": "w",
    "states": {"w": {"entry": "spawn_gk", "after": {"5000": "d"}}, "d": {}},
}
PARENT = {"id": "par", "initial": "a", "states": {"a": {"entry": "spawn_kid"}}}


def _parent() -> Any:
    gk = create_machine(GRANDKID)
    kid = create_machine(KID, logic=MachineLogic(services={"gk": gk}))
    return create_machine(PARENT, logic=MachineLogic(services={"kid": kid}))


def _tree(i: Any) -> List[Tuple[str, Any, List[str]]]:
    """Flatten the actor tree to (machine id, states, deadline states)."""
    out = []
    for a in i._actors.values():
        out.append(
            (
                a.machine.id,
                set(a.current_state_ids),
                [d.state_id for d in a.pending_deadlines()],
            )
        )
        out.extend(_tree(a))
    return sorted(out, key=lambda t: t[0])


def _blob() -> str:
    p = SyncInterpreter(_parent(), clock=SimulatedClock(wall_start=0)).start()
    s = p.get_snapshot()
    p.stop()
    return s


def _child_deadlines(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for actor in (rec.get("actors") or {}).values():
        out.extend(actor["snapshot"]["deadlines"])
        out.extend(_child_deadlines(actor["snapshot"]))
    return out


def test_child_deadline_is_in_child_blob_not_parent() -> None:
    b = json.loads(_blob())
    assert b["deadlines"] == []
    assert sorted(d["state_id"] for d in _child_deadlines(b)) == [
        "gk.w",
        "kid.w",
    ]
    p = SyncInterpreter(_parent(), clock=SimulatedClock(wall_start=0))
    p.start()
    assert p.pending_deadlines() == []  # each interpreter reports its own
    p.stop()


@pytest.mark.parametrize("eng", ["sync", "async"])
def test_fire_due_fires_child_and_grandchild(eng: str) -> None:
    b = _blob()
    if eng == "sync":
        r = SyncInterpreter.from_snapshot(
            b,
            _parent(),
            clock=SimulatedClock(wall_start=100),
            restart_timers="fire_due",
        ).start()
        tree = _tree(r)
        r.stop()
    else:

        async def go() -> Any:
            r = Interpreter.from_snapshot(
                b,
                _parent(),
                clock=SimulatedClock(wall_start=100),
                restart_timers="fire_due",
            )
            await r.start()
            t = _tree(r)
            await r.stop()
            return t

        tree = asyncio.run(go())
    assert tree == [("gk", {"gk.d"}, []), ("kid", {"kid.d"}, [])]


@pytest.mark.parametrize("eng", ["sync", "async"])
def test_resume_rearms_children_with_remaining_time(eng: str) -> None:
    b = _blob()  # kid due at wall 5, gk at wall 7

    async def run_async() -> Any:
        clk = SimulatedClock(wall_start=1)
        r = Interpreter.from_snapshot(
            b, _parent(), clock=clk, restart_timers="resume"
        )
        await r.start()
        await clk.increment(3999)
        a = _tree(r)
        await clk.increment(1)
        z = _tree(r)
        await r.stop()
        return a, z

    if eng == "async":
        before, after = asyncio.run(run_async())
    else:
        clk = SimulatedClock(wall_start=1)
        r = SyncInterpreter.from_snapshot(
            b, _parent(), clock=clk, restart_timers="resume"
        ).start()
        clk.increment(3999)
        before = _tree(r)
        clk.increment(1)
        after = _tree(r)
        r.stop()
    assert before == [
        ("gk", {"gk.w"}, ["gk.w"]),
        ("kid", {"kid.w"}, ["kid.w"]),
    ]
    assert after == [("gk", {"gk.w"}, ["gk.w"]), ("kid", {"kid.d"}, [])]


def test_false_keeps_children_static() -> None:
    r = SyncInterpreter.from_snapshot(
        _blob(),
        _parent(),
        clock=SimulatedClock(wall_start=100),
        restart_timers=False,
    ).start()
    assert _tree(r) == [
        ("gk", {"gk.w"}, ["gk.w"]),
        ("kid", {"kid.w"}, ["kid.w"]),
    ]
    r.stop()
