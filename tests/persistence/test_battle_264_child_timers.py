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


# ---------------------------------------------------------------------------
# Review M5 / M6 / H1: finished children, sendParent on resume, invokes
# ---------------------------------------------------------------------------
class Starts:
    """Count `on_interpreter_start` per machine id."""

    def __init__(self) -> None:
        self.ids: List[str] = []

    def on_interpreter_start(self, interp: Any) -> None:
        self.ids.append(interp.machine.id)

    def __getattr__(self, name: str) -> Any:  # every other hook: no-op
        if name.startswith("on_"):
            return lambda *a, **k: None
        raise AttributeError(name)


NOTIFIER_KID = {
    "id": "kid",
    "initial": "w",
    "states": {
        "w": {
            "after": {"5000": {"target": "d", "actions": "tell"}},
        },
        "d": {"type": "final"},
    },
}
NOTIFIER_PARENT = {
    "id": "par",
    "initial": "a",
    "context": {"told": 0},
    "states": {
        "a": {"entry": "spawn_kid", "on": {"TOLD": {"actions": "bump"}}}
    },
}


def _notifier_parent() -> Any:
    def tell(i: Any, c: Any, e: Any, a: Any) -> None:
        i.parent.send("TOLD")

    def bump(i: Any, c: Any, e: Any, a: Any) -> None:
        c["told"] += 1

    kid = create_machine(
        NOTIFIER_KID, logic=MachineLogic(actions={"tell": tell})
    )
    return create_machine(
        NOTIFIER_PARENT,
        logic=MachineLogic(services={"kid": kid}, actions={"bump": bump}),
    )


@pytest.mark.parametrize("eng", ["sync", "async"])
def test_finished_child_is_not_restarted_on_resume(eng: str) -> None:
    """Review M5: a child restored as `done` is finished -- no spurious
    `on_interpreter_start` for it on either engine."""
    clk0 = SimulatedClock(wall_start=1)
    i = SyncInterpreter(_notifier_parent(), clock=clk0).start()
    clk0.increment(2000)
    b_dict = json.loads(i.get_snapshot())
    i.stop()
    # 📝 A child that reaches `done` is REAPED from the parent (#57), so a
    #    snapshot taken afterwards carries no such child. The M5 case is a
    #    blob written mid-flight whose child record says `done` -- which
    #    is what a child-first save ordering, or a hand-edited blob, can
    #    produce. Build it.
    (kid_rec,) = b_dict["actors"].values()
    kid_rec["snapshot"]["status"] = "done"
    kid_rec["snapshot"]["state_ids"] = ["kid.d"]
    kid_rec["snapshot"]["configuration"] = ["kid", "kid.d"]
    kid_rec["snapshot"]["deadlines"] = []
    b = json.dumps(b_dict)

    starts = Starts()
    if eng == "sync":
        r = SyncInterpreter.from_snapshot(
            b,
            _notifier_parent(),
            clock=SimulatedClock(wall_start=100),
            restart_timers="fire_due",
            plugins=[starts],
        ).start()
        r.stop()
    else:

        async def run() -> None:
            r = Interpreter.from_snapshot(
                b,
                _notifier_parent(),
                clock=SimulatedClock(wall_start=100),
                restart_timers="fire_due",
                plugins=[starts],
            )
            await r.start()
            await r.stop()

        asyncio.run(run())
    assert starts.ids == ["par"]  # the kid (done) was not started


def test_sync_resumed_child_sendparent_lands_in_this_start() -> None:
    """Review M6: a child's matured `after` that `sendParent`s during the
    parent's `start()` must be processed by THAT start -- not sit in the
    parent's inbox until an unrelated send() (and be snapshotted as
    pending by a `persisted()` block in between)."""
    clk0 = SimulatedClock(wall_start=1)
    i = SyncInterpreter(_notifier_parent(), clock=clk0).start()
    clk0.increment(2000)  # kid timer: 3 s remain
    b = i.get_snapshot()
    i.stop()

    r = SyncInterpreter.from_snapshot(
        b,
        _notifier_parent(),
        clock=SimulatedClock(wall_start=100),  # 99 s later: matured
        restart_timers="fire_due",
    ).start()
    assert r.context["told"] == 1, "TOLD was left in the parent's inbox"
    assert json.loads(r.get_snapshot())["pending_events"] == []
    r.stop()


INVOKING_KID = {
    "id": "kid",
    "initial": "w",
    "states": {
        "w": {
            "invoke": {"id": "job", "src": "job", "onDone": "ok"},
            "after": {"5000": "late"},
        },
        "ok": {"type": "final"},
        "late": {"type": "final"},
    },
}


@pytest.mark.parametrize("restart_services", [False, True])
def test_child_with_invoke_and_after_restart_services_flag(
    restart_services: bool,
) -> None:
    """Review H1, pinned: `restart_services` is forwarded to child
    restores too. With False the child's dormant invoke stays dormant
    (its `after` still fires -- a timer is not a service); with True the
    service re-runs and wins the race against the 5 s timer."""
    calls: List[int] = []

    def job(i: Any, c: Any, e: Any) -> int:
        calls.append(1)
        import time

        time.sleep(0.05)
        return 1

    def parent() -> Any:
        kid = create_machine(
            INVOKING_KID, logic=MachineLogic(services={"job": job})
        )
        return create_machine(
            PARENT, logic=MachineLogic(services={"kid": kid})
        )

    # A kid caught mid-invoke: use the TIMER-ONLY kid from `_parent()` to
    # get a live child record, then rewrite it into the invoking kid's
    # shape (state `w` with a 5 s deadline armed at wall 1) -- what a
    # worker that died during the invoke leaves behind.
    i = SyncInterpreter(_parent(), clock=SimulatedClock(wall_start=1)).start()
    b = json.loads(i.get_snapshot())
    i.stop()
    kid_rec = next(
        rec
        for rec in b["actors"].values()
        if rec["snapshot"]["machine_id"] == "kid"
    )
    kid_rec["snapshot"].pop("machine_hash", None)  # a different kid chart
    kid_rec["snapshot"]["actors"] = {}  # drop the grandkid
    kid_rec["snapshot"]["system"] = {}
    kid_rec["snapshot"]["state_ids"] = ["kid.w"]
    kid_rec["snapshot"]["configuration"] = ["kid", "kid.w"]
    kid_rec["snapshot"]["status"] = "running"
    kid_rec["snapshot"]["deadlines"] = [
        {
            "state_id": "kid.w",
            "entry_seq": 1,
            "due_at_wall": 6.0,
            "delay_ms": 5000,
            "event_type": "after.5000.kid.w",
        }
    ]
    calls.clear()
    r = SyncInterpreter.from_snapshot(
        json.dumps(b),
        parent(),
        clock=SimulatedClock(wall_start=3),  # 3 s remain on the timer
        restart_timers="resume",
        restart_services=restart_services,
        verify_machine_hash=False,  # the kid chart is the invoking one
    ).start()
    (kid2,) = r._actors.values()
    if restart_services:
        assert len(calls) == 1 and kid2.current_state_ids == {"kid.ok"}
    else:
        assert calls == [] and kid2.has_dormant_invocations
        assert kid2.current_state_ids == {"kid.w"}
    r.stop()
