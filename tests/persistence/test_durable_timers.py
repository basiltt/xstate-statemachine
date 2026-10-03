# tests/persistence/test_durable_timers.py
"""#264: persisted `after` deadlines, `restart_timers` modes on both
engines, `DueTimerScanner`, end-to-end on SQLiteStore and FileStore."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Iterator, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import StateNotFoundError
from src.xstate_statemachine.persistence import (
    DEFAULT_RESTART_TIMERS,
    Deadline,
    DueTimerScanner,
    FileStore,
    MemoryStore,
    OptimisticLock,
    PessimisticLock,
    SnapshotMigrator,
    SQLiteStore,
    load_interpreter,
    persisted,
    save_interpreter,
)

CFG = {
    "id": "r",
    "initial": "waiting",
    "context": {"fired": []},
    "states": {
        "waiting": {
            "after": {"5000": {"target": "reminded", "actions": "note"}},
            "on": {"AGAIN": {"target": "waiting", "reenter": True}},
        },
        "reminded": {"type": "final"},
    },
}


def _note(i: Any, c: Any, e: Any, a: Any) -> None:
    c["fired"].append(e.type)


def machine(cfg: Dict[str, Any] = CFG):
    return create_machine(cfg, logic=MachineLogic(actions={"note": _note}))


class TestPendingDeadlines:
    def test_sync_arm_persist_forget(self) -> None:
        clk = SimulatedClock(wall_start=1000.0)
        i = SyncInterpreter(machine(), clock=clk).start()
        (d,) = i.pending_deadlines()
        assert d == Deadline(
            "r.waiting", 1, 1005.0, 5000, "after.5000.r.waiting"
        )
        blob = json.loads(i.get_snapshot())
        assert blob["deadlines"] == [d.to_dict()]
        clk.increment(5000)
        assert i.pending_deadlines() == []  # fired -> forgotten
        assert json.loads(i.get_snapshot())["deadlines"] == []
        i.stop()

    def test_reenter_bumps_entry_seq(self) -> None:
        clk = SimulatedClock(wall_start=0.0)
        i = SyncInterpreter(machine(), clock=clk).start()
        clk.increment(1000)
        i.send("AGAIN")
        (d,) = i.pending_deadlines()
        assert d.entry_seq == 2 and d.due_at_wall == 6.0  # re-armed at t=1
        i.stop()

    def test_exit_forgets(self) -> None:
        cfg = {
            "id": "x",
            "initial": "a",
            "states": {
                "a": {"after": {"100": "b"}, "on": {"GO": "b"}},
                "b": {},
            },
        }
        i = SyncInterpreter(
            create_machine(cfg), clock=SimulatedClock()
        ).start()
        assert len(i.pending_deadlines()) == 1
        i.send("GO")
        assert i.pending_deadlines() == []
        i.stop()

    def test_async_parity(self) -> None:
        async def go() -> Any:
            clk = SimulatedClock(wall_start=1000.0)
            i = await Interpreter(machine(), clock=clk).start()
            (d,) = i.pending_deadlines()
            blob = json.loads(i.get_snapshot())
            await clk.increment(5000)
            left = i.pending_deadlines()
            await i.stop()
            return d, blob["deadlines"], left

        d, persisted_, left = asyncio.run(go())
        assert d.due_at_wall == 1005.0 and d.delay_ms == 5000
        assert persisted_ == [d.to_dict()] and left == []

    def test_named_delay_stores_resolved_ms(self) -> None:
        cfg = {
            "id": "n",
            "initial": "a",
            "states": {"a": {"after": {"slow": "b"}}, "b": {}},
        }
        m = create_machine(cfg, logic=MachineLogic(delays={"slow": 1234}))
        i = SyncInterpreter(m, clock=SimulatedClock(wall_start=0)).start()
        (d,) = i.pending_deadlines()
        assert d.delay_ms == 1234 and d.due_at_wall == 1.234
        i.stop()


def _snapshot_at_2s() -> str:
    clk = SimulatedClock(wall_start=1000.0)
    i = SyncInterpreter(machine(), clock=clk).start()
    clk.increment(2000)
    blob = i.get_snapshot()
    i.stop()
    return blob


class TestRestartModes:
    def test_resume_rearms_remaining(self) -> None:
        clk = SimulatedClock(wall_start=1002.0)  # restored exactly at t=2s
        r = SyncInterpreter.from_snapshot(
            _snapshot_at_2s(), machine(), clock=clk, restart_timers="resume"
        )
        assert r.has_dormant_timers  # parked until start()
        assert (
            json.loads(r.get_snapshot())["deadlines"][0]["due_at_wall"]
            == 1005.0
        )  # re-emitted verbatim
        r.start()
        clk.increment(2999)
        assert r.current_state_ids == {"r.waiting"}
        clk.increment(1)
        assert r.current_state_ids == {"r.reminded"}
        r.stop()

    def test_restart_and_true_alias_rearm_from_zero(self) -> None:
        for mode in ("restart", True):
            clk = SimulatedClock(wall_start=1002.0)
            r = SyncInterpreter.from_snapshot(
                _snapshot_at_2s(), machine(), clock=clk, restart_timers=mode
            ).start()
            clk.increment(3001)
            assert r.current_state_ids == {"r.waiting"}, mode
            clk.increment(1999)
            assert r.current_state_ids == {"r.reminded"}, mode
            r.stop()

    def test_false_keeps_static(self) -> None:
        clk = SimulatedClock(wall_start=1002.0)
        r = SyncInterpreter.from_snapshot(
            _snapshot_at_2s(), machine(), clock=clk, restart_timers=False
        ).start()
        clk.increment(100_000)
        assert r.current_state_ids == {"r.waiting"} and r.has_dormant_timers
        r.stop()

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError):
            SyncInterpreter.from_snapshot(
                _snapshot_at_2s(), machine(), restart_timers="soon"
            )

    def test_fire_due_fires_at_start_in_order(self) -> None:
        seen: List[str] = []

        class P(PluginBase):
            def on_transition(self, i: Any, f: Any, t: Any, tr: Any) -> None:
                seen.append(tr.event)

        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "a": {
                    "initial": "w",
                    "states": {
                        "w": {"after": {"1000": "d"}},
                        "d": {"type": "final"},
                    },
                },
                "b": {
                    "initial": "w",
                    "states": {
                        "w": {"after": {"3000": "d"}},
                        "d": {"type": "final"},
                    },
                },
                "c": {
                    "initial": "w",
                    "states": {
                        "w": {"after": {"9000": "d"}},
                        "d": {"type": "final"},
                    },
                },
            },
        }
        m = create_machine(cfg)
        clk = SimulatedClock(wall_start=0.0)
        i = SyncInterpreter(m, clock=clk).start()
        blob = i.get_snapshot()
        i.stop()
        # Wake 5 s late: a (1s) and b (3s) matured, c (9s) has 4 s left.
        clk2 = SimulatedClock(wall_start=5.0)
        r = (
            SyncInterpreter.from_snapshot(
                blob, m, clock=clk2, restart_timers="fire_due"
            )
            .use(P())
            .start()
        )
        assert seen == [
            "after.1000.p.a.w",
            "after.3000.p.b.w",
        ]  # deadline order
        assert {"p.a.d", "p.b.d", "p.c.w"} == r.current_state_ids
        (left,) = r.pending_deadlines()
        assert left.state_id == "p.c.w" and left.due_at_wall == 9.0
        clk2.increment(3999)
        assert "p.c.w" in r.current_state_ids
        clk2.increment(1)
        assert r.current_state_ids == {"p.a.d", "p.b.d", "p.c.d"}
        r.stop()

    def test_fire_due_async(self) -> None:
        blob = _snapshot_at_2s()

        async def go() -> Any:
            clk = SimulatedClock(wall_start=1000.0 + 3600)
            r = Interpreter.from_snapshot(
                blob, machine(), clock=clk, restart_timers="fire_due"
            )
            await r.start()
            ids = set(r.current_state_ids)
            fired = list(r.context["fired"])
            await r.stop()
            return ids, fired

        ids, fired = asyncio.run(go())
        assert ids == {"r.reminded"} and fired == ["after.5000.r.waiting"]

    def test_resume_async(self) -> None:
        blob = _snapshot_at_2s()

        async def go() -> Any:
            clk = SimulatedClock(wall_start=1002.0)
            r = Interpreter.from_snapshot(
                blob, machine(), clock=clk, restart_timers="resume"
            )
            await r.start()
            await clk.increment(2999)
            before = set(r.current_state_ids)
            await clk.increment(1)
            after = set(r.current_state_ids)
            await r.stop()
            return before, after

        assert asyncio.run(go()) == ({"r.waiting"}, {"r.reminded"})

    def test_orphan_deadline_after_migration_fails_loudly(self) -> None:
        v1 = {
            "id": "m",
            "version": "1",
            "initial": "wait",
            "states": {
                "wait": {"after": {"1000": "done"}},
                "done": {"type": "final"},
            },
        }
        v2 = {
            "id": "m",
            "version": "2",
            "initial": "hold",
            "states": {
                "hold": {"on": {"GO": "done"}},
                "done": {"type": "final"},
            },
        }
        blob = (
            SyncInterpreter(create_machine(v1), clock=SimulatedClock())
            .start()
            .get_snapshot()
        )
        mig = SnapshotMigrator()
        # Renames the state but forgets the deadline: must not be silent.
        mig.add(
            "1",
            "2",
            lambda b: {
                **b,
                "state_ids": ["m.hold"],
                "configuration": ["m", "m.hold"],
            },
        )
        r = SyncInterpreter.from_snapshot(
            blob, create_machine(v2), migrator=mig, restart_timers="resume"
        )
        with pytest.raises(StateNotFoundError):
            r.start()


class TestScanner:
    @pytest.fixture(params=["sqlite", "file", "memory"])
    def store_factory(self, request: Any, tmp_path: Any):
        def make() -> Any:  # a NEW handle each call = "another process"
            if request.param == "sqlite":
                return SQLiteStore(tmp_path / "s.db")
            if request.param == "file":
                return FileStore(tmp_path / "fs")
            return shared

        shared = MemoryStore()
        return make

    def test_end_to_end_wakes_only_due_and_is_idempotent(
        self, store_factory: Any
    ) -> None:
        m = machine(
            {
                **CFG,
                "states": {
                    **CFG["states"],
                    "waiting": {
                        "after": {
                            "3600000": {
                                "target": "reminded",
                                "actions": "note",
                            }
                        }
                    },
                },
            }
        )
        with persisted(store_factory(), "u1", m):
            pass
        with persisted(store_factory(), "u2", m):
            pass
        now = time.time()
        sc = DueTimerScanner(store_factory(), lambda k: m)
        assert sc.run_once(now=now + 1800) == 0
        assert sc.due_keys(now + 3601) and len(sc.due_keys(now + 3601)) == 2
        assert sc.run_once(now=now + 3601) == 2
        r = sc.last_result
        assert (
            r.due == 2 and r.woken == 2 and r.errors == [] and r.max_lag_s >= 0
        )
        assert sc.run_once(now=now + 3601) == 0  # idempotent
        for key in ("u1", "u2"):
            with persisted(store_factory(), key, m) as i:
                assert i.current_state_ids == {"r.reminded"}
                assert i.context["fired"] == ["after.3600000.r.waiting"]
            assert store_factory().load(key).deadlines == ()

    def test_persisted_default_is_resume(self, tmp_path: Any) -> None:
        assert DEFAULT_RESTART_TIMERS == "resume"
        store = SQLiteStore(tmp_path / "s.db")
        m = machine()
        clk = SimulatedClock(wall_start=1000.0)
        with persisted(store, "k", m, clock=clk) as i:
            clk.increment(2000)
        clk2 = SimulatedClock(wall_start=1002.0)
        with persisted(store, "k", m, clock=clk2) as i:
            clk2.increment(2999)
            assert i.current_state_ids == {"r.waiting"}
            clk2.increment(1)
            assert i.current_state_ids == {"r.reminded"}
        # load_interpreter too
        store2 = SQLiteStore(tmp_path / "s2.db")
        with persisted(store2, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        i, _ = load_interpreter(
            store2, "k", m, clock=SimulatedClock(wall_start=4.999)
        )
        (d,) = i.pending_deadlines()
        assert abs(d.due_at_wall - 5.0) < 1e-9
        i.stop()
        store.close()
        store2.close()

    def test_skew_tolerance_and_prefix_and_limit(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        m = machine()
        for k in ("a-1", "a-2", "b-1"):
            with persisted(store, k, m, clock=SimulatedClock(wall_start=0)):
                pass  # all due at wall 5.0
        sc = DueTimerScanner(store, lambda k: m, prefix="a-")
        assert sc.run_once(now=4.0) == 0  # 1 s early, strict
        sc_skew = DueTimerScanner(
            store, lambda k: m, prefix="a-", skew_tolerance_s=2
        )
        assert sc_skew.run_once(now=4.0) == 2  # within tolerance
        assert sc_skew.run_once(now=4.0) == 0
        assert store.load("b-1").deadlines  # prefix excluded it
        # limit batches the EARLIEST due keys (#264 battle: it used to
        # inspect the first `limit` keys by NAME, starving b-1 here).
        sc_lim = DueTimerScanner(store, lambda k: m, limit=1)
        assert sc_lim.run_once(now=10.0) == 1  # b-1, the only one left
        assert sc_lim.last_result.scanned == 1
        assert DueTimerScanner(store, lambda k: m).run_once(now=10.0) == 0
        store.close()

    def test_stale_under_lock_is_skipped(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        m = machine()
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass

        class Racy(DueTimerScanner):
            fired_by_other = False

            def due_keys(self, now=None):  # type: ignore[override]
                keys = super().due_keys(now)
                if keys and not self.fired_by_other:
                    # Another worker fires it between our scan and our lock.
                    self.fired_by_other = True
                    with persisted(
                        store, "k", m, clock=SimulatedClock(wall_start=10)
                    ):
                        pass  # resume -> already due -> fires, deadlines cleared
                return keys

        sc = Racy(store, lambda k: m)
        assert sc.run_once(now=6.0) == 0
        assert (
            sc.last_result.skipped_stale == 1 and sc.last_result.errors == []
        )
        store.close()

    def test_error_in_one_key_does_not_stop_scan(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        m = machine()
        for k in ("bad", "good"):
            with persisted(store, k, m, clock=SimulatedClock(wall_start=0)):
                pass

        def pick(key: str) -> Any:
            if key == "bad":
                raise RuntimeError("no machine for you")
            return m

        sc = DueTimerScanner(store, pick, lock=PessimisticLock())
        assert sc.run_once(now=6.0) == 1
        assert [k for k, _ in sc.last_result.errors] == ["bad"]
        store.close()

    def test_run_forever_stops(self, tmp_path: Any) -> None:
        import threading

        sc = DueTimerScanner(
            MemoryStore(), lambda k: machine(), lock=OptimisticLock()
        )
        t = threading.Thread(target=sc.run_forever, args=(0.01,))
        t.start()
        time.sleep(0.05)
        sc.stop()
        t.join(2)
        assert not t.is_alive()

    def test_guarded_after_that_refuses_stays_armed(
        self, tmp_path: Any
    ) -> None:
        cfg = {
            "id": "g",
            "initial": "w",
            "context": {"ok": False},
            "states": {
                "w": {"after": {"1000": {"target": "d", "guard": "ok"}}},
                "d": {"type": "final"},
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(guards={"ok": lambda c, e: c["ok"]})
        )
        store = MemoryStore()
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        sc = DueTimerScanner(store, lambda k: m)
        assert sc.run_once(now=5.0) == 1  # woken; the guard said no
        # The timer fired and was consumed (a denied `after` is not
        # re-queued), so the saved record has no deadline...
        assert store.load("k").deadlines == ()
        with persisted(
            store, "k", m, clock=SimulatedClock(wall_start=5.0)
        ) as i:
            assert i.current_state_ids == {"g.w"}
            # ...and the next hydration re-arms the state's `after` from
            # zero (#128 semantics for a state with an unarmed timer), so
            # the guard gets another look one delay later.
            (d,) = i.pending_deadlines()
            assert d.due_at_wall == 6.0
