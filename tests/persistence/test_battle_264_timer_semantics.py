# tests/persistence/test_battle_264_timer_semantics.py
"""#264 battle (agent A): ENGINE semantics of durable `after` timers on
both engines -- restore modes, ordering, `entry_seq`, record corruption,
wall-clock jumps, named delays, interplay, cross-engine, leaks, corpus.

📝 Complements `test_durable_timers.py`; nothing here repeats it."""

from __future__ import annotations

import asyncio
import gc
import json
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.cli.extractor import extract_logic_names
from src.xstate_statemachine.events import Event, persist_event
from src.xstate_statemachine.exceptions import (
    SnapshotCorruptError,
    StateNotFoundError,
    XStateMachineError,
)
from src.xstate_statemachine.persistence import Deadline
from src.xstate_statemachine.persistence.snapshot import check_shape

pytestmark = pytest.mark.timeout(30)

T0 = 1000.0
CFG: Dict[str, Any] = {
    "id": "r",
    "initial": "w",
    "context": {"n": 0},
    "states": {
        "w": {
            "after": {"5000": "d"},
            "on": {"AGAIN": {"target": "w", "reenter": True}, "GO": "o"},
        },
        "o": {"on": {"BACK": "w"}},
        "d": {"type": "final"},
    },
}


class Rec(PluginBase):
    """Records every transition's event type."""

    def __init__(self) -> None:
        self.seen: List[str] = []

    def on_transition(self, i: Any, f: Any, t: Any, tr: Any) -> None:
        self.seen.append(tr.event)


def _m(cfg: Dict[str, Any] = CFG, **logic: Any) -> Any:
    return create_machine(cfg, logic=MachineLogic(**logic))


def _blob(m: Any, advance_ms: int = 0, wall: float = T0) -> Dict[str, Any]:
    clk = SimulatedClock(wall_start=wall)
    i = SyncInterpreter(m, clock=clk).start()
    clk.increment(advance_ms)
    b = json.loads(i.get_snapshot())
    i.stop()
    return b


def _sync_restore(
    blob: Dict[str, Any], m: Any, wall: float, mode: Any = "resume"
) -> Any:
    clk = SimulatedClock(wall_start=wall)
    r = SyncInterpreter.from_snapshot(
        json.dumps(blob), m, clock=clk, restart_timers=mode
    )
    return r, clk


# ---------------------------------------------------------------------------
# 1. Acceptance criterion 2, both engines, and WHERE fire_due fires
# ---------------------------------------------------------------------------
class TestAcceptance:
    def test_sync_resume_2999_then_1(self) -> None:
        b = _blob(_m(), 2000)
        r, clk = _sync_restore(b, _m(), T0 + 2)
        r.start()
        clk.increment(2999)
        assert r.current_state_ids == {"r.w"}
        clk.increment(1)
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_async_resume_2999_then_1(self) -> None:
        b = _blob(_m(), 2000)

        async def go() -> Any:
            clk = SimulatedClock(wall_start=T0 + 2)
            r = Interpreter.from_snapshot(
                json.dumps(b), _m(), clock=clk, restart_timers="resume"
            )
            await r.start()
            await clk.increment(2999)
            a = set(r.current_state_ids)
            await clk.increment(1)
            z = set(r.current_state_ids)
            await r.stop()
            return a, z

        assert asyncio.run(go()) == ({"r.w"}, {"r.d"})

    def test_sync_resume_hour_late_arms_at_zero_fires_on_next_pump(
        self,
    ) -> None:
        b = _blob(_m(), 2000)
        r, clk = _sync_restore(b, _m(), T0 + 3600, "resume")
        r.start()
        # "resume" arms the matured timer at 0 ms but does not pump it.
        assert r.current_state_ids == {"r.w"}
        clk.increment(0)
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_sync_fire_due_fires_inside_start_not_from_snapshot(
        self,
    ) -> None:
        """📝 DOCUMENTED: the sync engine fires matured deadlines inside
        `start()` (pumped before it returns), NOT deferred to the first
        `tick()`/`send()`. Pinned so a change is deliberate."""
        b = _blob(_m(), 2000)
        rec = Rec()
        r, _ = _sync_restore(b, _m(), T0 + 3600, "fire_due")
        r.use(rec)
        assert rec.seen == [] and r.current_state_ids == {"r.w"}
        r.start()
        assert rec.seen == ["after.5000.r.w"]
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_async_fire_due_fires_inside_start(self) -> None:
        b = _blob(_m(), 2000)

        async def go() -> Any:
            rec = Rec()
            clk = SimulatedClock(wall_start=T0 + 3600)
            r = Interpreter.from_snapshot(
                json.dumps(b), _m(), clock=clk, restart_timers="fire_due"
            ).use(rec)
            before = list(rec.seen)
            await r.start()
            after = list(rec.seen)
            await r.stop()
            return before, after

        assert asyncio.run(go()) == ([], ["after.5000.r.w"])


# ---------------------------------------------------------------------------
# 2. Ordering under fire_due
# ---------------------------------------------------------------------------
def _region(name: str, delay: int) -> Dict[str, Any]:
    return {
        "initial": "w",
        "states": {
            "w": {"after": {str(delay): "d"}},
            "d": {"type": "final"},
        },
    }


ORDER_CFG = {
    "id": "p",
    "type": "parallel",
    "states": {
        "e": _region("e", 500),
        "a": _region("a", 4000),
        "c": {
            "initial": "outer",
            "states": {
                "outer": {
                    "initial": "inner",
                    "states": {"inner": {"after": {"1000": "#p.c.x"}}},
                },
                "x": {"type": "final"},
            },
        },
        "b": _region("b", 3000),
        "d": _region("d", 2000),
    },
}


class TestOrdering:
    def test_five_matured_fire_in_deadline_order(self) -> None:
        m = create_machine(ORDER_CFG)
        b = _blob(m)
        rec = Rec()
        r, _ = _sync_restore(b, m, T0 + 60, "fire_due")
        r.use(rec).start()
        assert rec.seen == [
            "after.500.p.e.w",
            "after.1000.p.c.outer.inner",
            "after.2000.p.d.w",
            "after.3000.p.b.w",
            "after.4000.p.a.w",
        ]
        assert r.pending_deadlines() == []
        r.stop()

    def test_equal_due_times_tie_break_by_state_id(self) -> None:
        """Equal deadlines: arm order is sorted by `(due, state_id)`, the
        clock heap is FIFO for ties -> state-id order. Deterministic."""
        cfg = {
            "id": "q",
            "type": "parallel",
            "states": {k: _region(k, 1000) for k in ("z", "m", "a")},
        }
        m = create_machine(cfg)
        b = _blob(m)
        for eng in ("sync", "async"):
            rec = Rec()
            if eng == "sync":
                r, _ = _sync_restore(b, m, T0 + 60, "fire_due")
                r.use(rec).start()
                r.stop()
            else:

                async def go() -> None:
                    ar = Interpreter.from_snapshot(
                        json.dumps(b),
                        m,
                        clock=SimulatedClock(wall_start=T0 + 60),
                        restart_timers="fire_due",
                    ).use(rec)
                    await ar.start()
                    await ar.stop()

                asyncio.run(go())
            assert rec.seen == [
                "after.1000.q.a.w",
                "after.1000.q.m.w",
                "after.1000.q.z.w",
            ], eng

    def test_guard_refusal_consumes_and_is_not_pending(self) -> None:
        """📝 DOCUMENTED: a matured deadline whose guards all refuse is
        CONSUMED (not re-reported pending) -- same as a live `after`."""
        cfg = {
            "id": "g",
            "initial": "w",
            "states": {
                "w": {"after": {"1000": {"target": "d", "guard": "no"}}},
                "d": {},
            },
        }
        m = _m(cfg, guards={"no": lambda c, e: False})
        b = _blob(m)
        r, _ = _sync_restore(b, m, T0 + 60, "fire_due")
        r.start()
        assert r.current_state_ids == {"g.w"}
        assert r.pending_deadlines() == []
        r.stop()

    def test_after_reentering_same_state_bumps_seq(self) -> None:
        cfg = {
            "id": "s",
            "initial": "w",
            "states": {
                "w": {"after": {"1000": {"target": "w", "reenter": True}}}
            },
        }
        m = create_machine(cfg)
        clk = SimulatedClock(wall_start=0)
        i = SyncInterpreter(m, clock=clk).start()
        (d1,) = i.pending_deadlines()
        clk.increment(1000)
        (d2,) = i.pending_deadlines()
        assert d2.entry_seq == d1.entry_seq + 1
        assert d2.due_at_wall == 2.0
        i.stop()


# ---------------------------------------------------------------------------
# 3. entry_seq
# ---------------------------------------------------------------------------
class TestEntrySeq:
    def test_two_timers_share_one_seq_and_reentry_renews(self) -> None:
        cfg = {
            "id": "t",
            "initial": "w",
            "states": {
                "w": {
                    "after": {"1000": "x", "2000": "x"},
                    "on": {"GO": "x"},
                },
                "x": {"on": {"BACK": "w"}},
            },
        }
        i = SyncInterpreter(
            create_machine(cfg), clock=SimulatedClock()
        ).start()
        a, b = i.pending_deadlines()
        assert a.entry_seq == b.entry_seq
        i.send("GO")
        i.send("BACK")
        c, _ = i.pending_deadlines()
        assert c.entry_seq > a.entry_seq
        i.stop()

    def test_restored_high_seq_raises_counter(self) -> None:
        b = _blob(_m())
        b["deadlines"][0]["entry_seq"] = 1000
        r, _ = _sync_restore(b, _m(), T0, "resume")
        assert r._entry_seq == 1000
        r.start()
        (d,) = r.pending_deadlines()
        assert d.entry_seq == 1001
        r.send("AGAIN")
        assert r.pending_deadlines()[0].entry_seq == 1002
        r.stop()

    @pytest.mark.parametrize("bad", [-1, 1.5, True, 2**63, "1", None])
    def test_bad_seq_is_corrupt(self, bad: Any) -> None:
        b = _blob(_m())
        b["deadlines"][0]["entry_seq"] = bad
        with pytest.raises(SnapshotCorruptError):
            check_shape(b)
        with pytest.raises(SnapshotCorruptError):
            _sync_restore(b, _m(), T0)


# ---------------------------------------------------------------------------
# 4. Record corruption
# ---------------------------------------------------------------------------
BAD_FIELDS = [
    ("state_id", 5),
    ("state_id", ""),
    ("state_id", None),
    ("event_type", 3),
    ("event_type", ""),
    ("due_at_wall", float("nan")),
    ("due_at_wall", float("inf")),
    ("due_at_wall", float("-inf")),
    ("due_at_wall", "soon"),
    ("due_at_wall", True),
    ("delay_ms", -1),
    ("delay_ms", 1.5),
    ("delay_ms", False),
    ("delay_ms", 2**63),
]


class TestCorruption:
    @pytest.mark.parametrize("key,val", BAD_FIELDS)
    def test_bad_field_is_typed(self, key: str, val: Any) -> None:
        b = _blob(_m())
        b["deadlines"][0][key] = val
        with pytest.raises(SnapshotCorruptError):
            check_shape(b)
        with pytest.raises(SnapshotCorruptError):
            _sync_restore(b, _m(), T0)

    @pytest.mark.parametrize(
        "key", list(Deadline("a", 0, 0, 0, "e").to_dict())
    )
    def test_missing_key_is_typed(self, key: str) -> None:
        b = _blob(_m())
        del b["deadlines"][0][key]
        with pytest.raises(SnapshotCorruptError):
            _sync_restore(b, _m(), T0)

    @pytest.mark.parametrize("sid", ["r.nope", "r.w\x00"])
    @pytest.mark.parametrize("mode", ["resume", "fire_due"])
    def test_unknown_state_loud_on_resume(self, sid: str, mode: str) -> None:
        b = _blob(_m())
        b["deadlines"][0]["state_id"] = sid
        r, _ = _sync_restore(b, _m(), T0, mode)
        with pytest.raises(StateNotFoundError):
            r.start()

    def test_unknown_state_restart_drops_and_rearms_from_zero(self) -> None:
        """📝 DECIDED: "restart" ignores persisted records by contract (it
        re-arms from the chart), so an orphan record is simply dropped."""
        b = _blob(_m())
        b["deadlines"][0]["state_id"] = "r.nope"
        r, _ = _sync_restore(b, _m(), T0 + 10, "restart")
        r.start()
        (d,) = r.pending_deadlines()
        assert d.state_id == "r.w" and d.due_at_wall == T0 + 15
        r.stop()

    def test_unknown_state_false_is_re_emitted_verbatim(self) -> None:
        """📝 DECIDED: `False` is a static restore -- the record is carried
        through untouched so a later loader (or the scanner) decides."""
        b = _blob(_m())
        b["deadlines"][0]["state_id"] = "r.nope"
        r, _ = _sync_restore(b, _m(), T0, False)
        r.start()
        assert [d.state_id for d in r.pending_deadlines()] == ["r.nope"]
        r.stop()

    def test_event_type_for_undeclared_delay_falls_back_to_chart(
        self,
    ) -> None:
        """📝 DOCUMENTED: the chart changed `after` 1000 -> 5000 under the
        same state id. The stale record's event type matches nothing, so
        "resume" arms the CURRENT declared delay from zero."""
        b = _blob(_m())
        b["deadlines"][0]["event_type"] = "after.1000.r.w"
        b["deadlines"][0]["delay_ms"] = 1000
        r, clk = _sync_restore(b, _m(), T0 + 0.5, "resume")
        r.start()
        (d,) = r.pending_deadlines()
        assert d.event_type == "after.5000.r.w"
        assert d.due_at_wall == T0 + 5.5
        r.stop()

    def test_duplicate_records_earliest_wins(self) -> None:
        b = _blob(_m())
        first = dict(b["deadlines"][0], due_at_wall=T0 + 1)
        b["deadlines"] = [b["deadlines"][0], first]  # late one listed first
        r, clk = _sync_restore(b, _m(), T0, "resume")
        r.start()
        clk.increment(1000)
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_redeployed_shorter_delay_does_not_fire_early(self) -> None:
        """Review H2: the clamp bounds the remainder by the delay the
        deadline was ARMED with (persisted `delay_ms`), not today's
        declared value. Armed with 24 h, chart redeployed with 1 h (same
        state id, same event type), restored 1 h in: 23 h remain -- the
        first cut clamped that to 1 h and fired 22 h EARLY, breaking "no
        earlier than due". Now the full remainder is honoured."""
        day = {**CFG, "states": {**CFG["states"]}}
        day["states"]["w"] = {**CFG["states"]["w"], "after": {"86400000": "d"}}
        b = _blob(_m(day))  # armed with 24 h at T0
        (d,) = b["deadlines"]
        assert d["delay_ms"] == 86_400_000
        hour = {**CFG, "states": {**CFG["states"]}}
        hour["states"]["w"] = {**CFG["states"]["w"], "after": {"3600000": "d"}}
        # the event type is keyed by the delay, so rename it the way a
        # SnapshotMigrator step would when the chart's `after` key changed
        b["deadlines"][0]["event_type"] = "after.3600000.r.w"
        # (the structure changed by design: the redeploy is "known
        # compatible", exactly the documented `verify_machine_hash=False`
        # case; a real deploy would do this through a migrator step)
        clk = SimulatedClock(wall_start=T0 + 3600)
        r = SyncInterpreter.from_snapshot(
            json.dumps(b),
            _m(hour),
            clock=clk,
            restart_timers="resume",
            verify_machine_hash=False,
        )
        r.start()
        (pending,) = r.pending_deadlines()
        assert pending.due_at_wall == pytest.approx(T0 + 86_400)  # unchanged
        clk.increment(3600 * 1000)  # 1 h later: the OLD rule would fire here
        assert r.current_state_ids == {"r.w"}
        clk.increment((86_400 - 7200) * 1000)  # the real remainder
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_clock_stepped_back_clamps_to_armed_delay(self) -> None:
        """The clamp's reason to exist: a wall clock stepped BACK 2 h makes
        the remainder 2 h 5 s on a 5 s timer -- clamped to the 5 s it was
        armed with."""
        b = _blob(_m())
        r, clk = _sync_restore(b, _m(), T0 - 7200, "resume")
        r.start()
        clk.increment(4999)
        assert r.current_state_ids == {"r.w"}
        clk.increment(1)
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_duplicate_records_newest_seq_beats_earlier_stale(self) -> None:
        b = _blob(_m())
        fresh = dict(b["deadlines"][0], entry_seq=5)
        stale = dict(fresh, entry_seq=4, due_at_wall=T0 - 100)
        b["deadlines"] = [fresh, stale]  # stale listed LAST
        r, clk = _sync_restore(b, _m(), T0, "fire_due")
        r.start()
        clk.increment(0)
        assert r.current_state_ids == {"r.w"}
        r.stop()

    def test_100k_records_bounded_time(self) -> None:
        b = _blob(_m())
        b["deadlines"] = b["deadlines"] * 100_000
        t = time.perf_counter()
        r, _ = _sync_restore(b, _m(), T0, "resume")
        r.start()
        assert len(r.pending_deadlines()) == 1
        r.stop()
        assert time.perf_counter() - t < 10

    def test_deadlines_on_stopped_snapshot_do_not_resurrect(self) -> None:
        b = _blob(_m())
        b["status"] = "stopped"
        r, _ = _sync_restore(b, _m(), T0 + 60, "fire_due")
        with pytest.raises(XStateMachineError):
            r.start()
        assert r.current_state_ids == {"r.w"}


# ---------------------------------------------------------------------------
# 5. Wall-clock jumps
# ---------------------------------------------------------------------------
class TestWallClockJumps:
    @pytest.mark.parametrize("eng", ["sync", "async"])
    def test_clock_stepped_back_clamps_to_declared(self, eng: str) -> None:
        """🔥 BUG fixed: a wall clock 2 h EARLIER than at arming made
        "resume" wait 2 h + 5 s; now clamped to the declared delay."""
        b = _blob(_m())
        if eng == "sync":
            r, clk = _sync_restore(b, _m(), T0 - 7200, "resume")
            r.start()
            clk.increment(5000)
            assert r.current_state_ids == {"r.d"}
            r.stop()
            return

        async def go() -> Any:
            clk = SimulatedClock(wall_start=T0 - 7200)
            r = Interpreter.from_snapshot(
                json.dumps(b), _m(), clock=clk, restart_timers="resume"
            )
            await r.start()
            await clk.increment(5000)
            ids = set(r.current_state_ids)
            await r.stop()
            return ids

        assert asyncio.run(go()) == {"r.d"}

    def test_far_future_due_never_emits_inf(self) -> None:
        """🔥 BUG fixed: `due_at_wall=1e308` re-emitted as `inf`, which the
        next `check_shape` refused -- a self-poisoning key."""
        b = _blob(_m())
        b["deadlines"][0]["due_at_wall"] = 1e308
        r, _ = _sync_restore(b, _m(), T0, "resume")
        r.start()
        blob2 = json.loads(r.get_snapshot())
        check_shape(blob2)
        assert blob2["deadlines"][0]["due_at_wall"] == T0 + 5
        r.stop()

    def test_ancient_deadline_fires_once(self) -> None:
        cfg = {
            "id": "a",
            "initial": "w",
            "context": {"n": 0},
            "states": {
                "w": {"after": {"1000": {"actions": "inc"}}},
            },
        }

        def inc(i: Any, c: Any, e: Any, a: Any) -> None:
            c["n"] += 1

        m = _m(cfg, actions={"inc": inc})
        b = _blob(m)
        b["deadlines"][0]["due_at_wall"] = T0 - 10 * 365 * 86400
        r, clk = _sync_restore(b, m, T0, "fire_due")
        r.start()
        clk.increment(0)
        assert r.context["n"] == 1
        r.stop()


# ---------------------------------------------------------------------------
# 6. Named / dynamic delays
# ---------------------------------------------------------------------------
DYN = {
    "id": "y",
    "initial": "w",
    "context": {"ms": 1000},
    "states": {
        "w": {"after": {"retryDelay": "d"}, "on": {"SET": {"actions": "s"}}},
        "d": {},
    },
}


def _dyn(fn: Optional[Callable[..., Any]] = None) -> Any:
    return _m(
        DYN,
        delays={"retryDelay": fn or (lambda c, e: c["ms"])},
        actions={"s": lambda i, c, e, a: c.__setitem__("ms", 9000)},
    )


class TestDynamicDelays:
    def test_persisted_resolved_restart_reresolves_resume_does_not(
        self,
    ) -> None:
        b = _blob(_dyn())
        assert b["deadlines"][0]["delay_ms"] == 1000
        b["context"]["ms"] = 9000  # restored context differs
        r, _ = _sync_restore(b, _dyn(), T0, "restart")
        r.start()
        assert r.pending_deadlines()[0].due_at_wall == T0 + 9
        r.stop()
        r, clk = _sync_restore(b, _dyn(), T0, "resume")
        r.start()
        clk.increment(1000)
        assert r.current_state_ids == {"y.d"}  # persisted remainder won
        r.stop()

    @pytest.mark.parametrize(
        "ret", [float("nan"), -5, "soon", None, RuntimeError("x")]
    )
    def test_bad_delay_on_restore_is_not_bare(self, ret: Any) -> None:
        """📝 DOCUMENTED: an unresolvable delay on restore is skipped with
        a warning (the pre-existing `_resolve_delay` contract) or typed."""
        b = _blob(_dyn())

        def bad(c: Any, e: Any) -> Any:
            if isinstance(ret, Exception):
                raise ret
            return ret

        r, _ = _sync_restore(b, _dyn(bad), T0, "restart")
        try:
            r.start()
        except XStateMachineError:
            return
        assert all(
            d.due_at_wall == d.due_at_wall for d in r.pending_deadlines()
        )
        # 🔥 BUG fixed: a negative delay was persisted as `delay_ms < 0`
        #    and the NEXT load refused its own blob.
        check_shape(json.loads(r.get_snapshot()))
        r.stop()


# ---------------------------------------------------------------------------
# 7. Interplay
# ---------------------------------------------------------------------------
class TestInterplay:
    def test_history_does_not_resurrect_exited_timer(self) -> None:
        cfg = {
            "id": "h",
            "initial": "c",
            "states": {
                "c": {
                    "initial": "w",
                    "states": {
                        "w": {"after": {"5000": "z"}},
                        "z": {},
                        "hist": {"type": "history"},
                    },
                    "on": {"OUT": "o"},
                },
                "o": {"on": {"BACK": "c.hist"}},
            },
        }
        m = create_machine(cfg)
        clk = SimulatedClock(wall_start=T0)
        i = SyncInterpreter(m, clock=clk).start()
        clk.increment(1000)
        i.send("OUT")
        b = json.loads(i.get_snapshot())
        i.stop()
        assert b["deadlines"] == []
        r, clk2 = _sync_restore(b, m, T0 + 100, "fire_due")
        r.start()
        r.send("BACK")
        (d,) = r.pending_deadlines()  # fresh arm on re-entry, from zero
        assert d.due_at_wall == T0 + 105
        r.stop()

    def test_parallel_sibling_deadline_untouched(self) -> None:
        cfg = {
            "id": "pp",
            "type": "parallel",
            "states": {"a": _region("a", 1000), "b": _region("b", 9000)},
        }
        m = create_machine(cfg)
        clk = SimulatedClock(wall_start=0)
        i = SyncInterpreter(m, clock=clk).start()
        before = [d for d in i.pending_deadlines() if "b" in d.state_id]
        clk.increment(1000)
        assert i.pending_deadlines() == before
        i.stop()

    def test_after_and_delayed_raise_both_fire_once(self) -> None:
        cfg = {
            "id": "rd",
            "initial": "w",
            "context": {"log": []},
            "states": {
                "w": {
                    "entry": {
                        "type": "xstate.raise",
                        "params": {"event": {"type": "PONG"}, "delay": 1000},
                    },
                    "after": {"3000": {"actions": "note"}},
                    "on": {"PONG": {"actions": "note"}},
                }
            },
        }

        def note(i: Any, c: Any, e: Any, a: Any) -> None:
            c["log"].append(e.type)

        m = _m(cfg, actions={"note": note})
        b = _blob(m)
        # 📝 Both are persisted side by side: the deadline in `deadlines`,
        #    the delayed self-send in `scheduled_sends` (#213).
        assert b["scheduled_sends"][0]["type"] == "PONG"
        assert b["deadlines"][0]["event_type"] == "after.3000.rd.w"
        r, clk = _sync_restore(b, m, T0 + 60, "fire_due")
        r.start()
        clk.increment(0)
        clk.increment(10_000)
        # 📝 DOCUMENTED: #213 self-sends persist RELATIVE remaining time
        #    (not wall-anchored), so after a 60 s outage PONG still waits
        #    its 1 s while the matured `after` fires inside start(). Each
        #    fires exactly once.
        assert r.context["log"] == ["after.3000.rd.w", "PONG"]
        r.stop()

    def test_restored_inbox_drains_before_fire_due(self) -> None:
        cfg = {
            "id": "ib",
            "initial": "w",
            "states": {
                "w": {"after": {"1000": "x"}, "on": {"PING": "y"}},
                "x": {"on": {"PING": "z"}},
                "y": {},
                "z": {},
            },
        }
        m = create_machine(cfg)
        b = _blob(m)
        b["pending_events"] = [persist_event(Event("PING"))]
        rec = Rec()
        r, _ = _sync_restore(b, m, T0 + 60, "fire_due")
        r.use(rec).start()
        # 📝 DECIDED (both engines agree): the restored inbox drains BEFORE
        #    matured timers. Causally right -- every inbox event was
        #    ACCEPTED before the snapshot, while a deadline in the blob was
        #    still pending at that instant, i.e. it matured AFTER them.
        #    PING exits `w`, so the matured timer is cancelled, not fired.
        assert rec.seen == ["PING"]
        assert r.current_state_ids == {"ib.y"}
        assert r.pending_deadlines() == []
        r.stop()

        async def go() -> Any:
            ar = Interpreter.from_snapshot(
                json.dumps(b),
                m,
                clock=SimulatedClock(wall_start=T0 + 60),
                restart_timers="fire_due",
            )
            await ar.start()
            ids = set(ar.current_state_ids)
            await ar.stop()
            return ids

        assert asyncio.run(go()) == {"ib.y"}


# ---------------------------------------------------------------------------
# 8. Cross-engine
# ---------------------------------------------------------------------------
class TestCrossEngine:
    def test_async_written_sync_restored_fire_due(self) -> None:
        async def snap() -> str:
            clk = SimulatedClock(wall_start=T0)
            i = await Interpreter(_m(), clock=clk).start()
            await clk.increment(2000)
            s = i.get_snapshot()
            await i.stop()
            return s

        b = json.loads(asyncio.run(snap()))
        r, clk = _sync_restore(b, _m(), T0 + 4.999, "resume")
        r.start()
        clk.increment(1)
        assert r.current_state_ids == {"r.d"}
        r.stop()
        r, _ = _sync_restore(b, _m(), T0 + 99, "fire_due")
        r.start()
        assert r.current_state_ids == {"r.d"}
        r.stop()

    def test_sync_written_async_restored_resume(self) -> None:
        b = _blob(_m(), 2000)

        async def go() -> Any:
            clk = SimulatedClock(wall_start=T0 + 4.999)
            r = Interpreter.from_snapshot(
                json.dumps(b), _m(), clock=clk, restart_timers="resume"
            )
            await r.start()
            await clk.increment(1)
            ids = set(r.current_state_ids)
            await r.stop()
            return ids

        assert asyncio.run(go()) == {"r.d"}


# ---------------------------------------------------------------------------
# 9. Leaks / scale
# ---------------------------------------------------------------------------
class TestLeaks:
    def test_restore_cycle_memory_flat(self) -> None:
        m = _m()
        b = json.dumps(_blob(m))
        running: set = set()
        stopped: set = set()

        def cycle() -> None:
            r = SyncInterpreter.from_snapshot(
                b,
                m,
                clock=SimulatedClock(wall_start=T0),
                restart_timers="resume",
            ).start()
            running.add(len(r._armed_after) + len(r._restored_deadlines))
            r.stop()
            stopped.add(len(r._armed_after) + len(r._restored_deadlines))

        n = 10_000
        for _ in range(200):
            cycle()
        gc.collect()
        tracemalloc.start()
        for _ in range(n // 2):
            cycle()
        gc.collect()
        mid = tracemalloc.take_snapshot()
        for _ in range(n // 2):
            cycle()
        gc.collect()
        end = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(s.size_diff for s in end.compare_to(mid, "filename"))
        assert growth < 64 * 1024
        # Flat across the WHOLE run: 1 armed while running, 0 after stop.
        assert running == {1} and stopped == {0}

    def test_no_thread_leak_real_clock(self) -> None:
        m = _m()
        b = json.dumps(_blob(m, wall=time.time()))
        base = threading.active_count()
        peak = base
        for _ in range(1000):
            SyncInterpreter.from_snapshot(
                b, m, restart_timers="resume"
            ).start().stop()
            peak = max(peak, threading.active_count())
        time.sleep(0.2)
        assert threading.active_count() <= base + 2
        assert peak <= base + 4

    def test_pending_deadlines_linear(self) -> None:
        def build(n: int) -> Any:
            return create_machine(
                {
                    "id": "big",
                    "type": "parallel",
                    "states": {
                        f"s{k}": {
                            "after": {"1000": {}, "2000": {}, "3000": {}}
                        }
                        for k in range(n)
                    },
                }
            )

        def cost(n: int) -> float:
            i = SyncInterpreter(build(n), clock=SimulatedClock()).start()
            t = time.perf_counter()
            for _ in range(20):
                assert len(i.pending_deadlines()) == 3 * n
            dt = time.perf_counter() - t
            i.stop()
            return dt

        small, large = cost(50), cost(500)
        assert large < small * 40  # linear ~10x; quadratic would be ~100x


# ---------------------------------------------------------------------------
# 10. Stately corpus
# ---------------------------------------------------------------------------
CORPUS = Path(__file__).resolve().parents[1] / "tests_cli" / "stately_machines"


def _has_after(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("after"):
            return True
        return any(_has_after(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_after(v) for v in node)
    return False


def stub_logic(cfg: Dict[str, Any]) -> Any:
    """No-op actions, false guards, never-settling-free sync services."""
    acts, guards, svcs = extract_logic_names(cfg)
    return MachineLogic(
        actions={a: (lambda *_: None) for a in acts},
        guards={g: (lambda *_: False) for g in guards},
        services={s: (lambda *_: None) for s in svcs},
    )


def _corpus() -> List[Path]:
    out = []
    for p in sorted(CORPUS.glob("*.json")):
        try:
            if _has_after(json.loads(p.read_text(encoding="utf-8"))):
                out.append(p)
        except ValueError:
            continue
    return out


@pytest.mark.parametrize("path", _corpus(), ids=lambda p: p.stem)
def test_stately_corpus_round_trip(path: Path) -> None:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    try:
        m = create_machine(cfg, logic=stub_logic(cfg))
        i = SyncInterpreter(m, clock=SimulatedClock(wall_start=T0)).start()
    except XStateMachineError:
        pytest.skip("chart not drivable by stub_logic")
    b = json.loads(i.get_snapshot())
    i.stop()
    check_shape(b)
    for rec in b["deadlines"]:
        assert Deadline.from_dict(rec).to_dict() == rec
    rec_ = Rec()
    r, clk = _sync_restore(b, m, T0, "resume")
    r.use(rec_).start()
    if all(d["due_at_wall"] > T0 for d in b["deadlines"]):
        assert not any(e.startswith("after.") for e in rec_.seen)
    r.stop()
    try:
        r, _ = _sync_restore(b, m, T0 + 10**7, "fire_due")
        r.start()
        r.stop()
    except XStateMachineError:
        pass  # typed is allowed
