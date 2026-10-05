# tests/contrib/testing/test_battle_272_replay.py
"""Battle #272 (adversary A): `replay()` / `assert_replay_consistent()`.

* a store-backed check read only the first page (``limit=1000``): a
  log tampered at record 1200 was reported consistent;
* ``upto=`` is inclusive, ``0`` is the initial state, negative refused;
* stubs reproduce STATE (context untouched), real logic reproduces
  context; gaps / trimmed heads / foreign snapshots / mixed keys loud;
* the returned interpreter is running on a `SimulatedClock`, no threads.
"""

from __future__ import annotations

import dataclasses
import threading
import time
import unittest
from typing import Any, List, Tuple

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.contrib.testing import (
    ReplayDivergenceError,
    assert_replay_consistent,
    replay,
)
from src.xstate_statemachine.exceptions import XStateMachineError
from src.xstate_statemachine.persistence import (
    MemoryLog,
    TransitionLogPlugin,
)

CFG = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"GO": {"target": "b", "actions": "inc"}}},
        "b": {"on": {"GO": {"target": "a", "actions": "inc"}}},
    },
}


def inc(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] += 1


def logic() -> MachineLogic:
    return MachineLogic(actions={"inc": inc})


def recorded(
    n: int, log: Any = None, name: Any = None
) -> Tuple[Any, Any, str]:
    m = create_machine(CFG, logic=logic())
    log = log if log is not None else MemoryLog()
    kw = {} if name is None else {"machine_id": lambda i: name}
    it = SyncInterpreter(m).use(TransitionLogPlugin(log, **kw)).start()
    for _ in range(n):
        it.send("GO")
    key = it.store_key or it.id
    it.stop()
    return m, log, key


class TestStorePaging(unittest.TestCase):
    def test_tamper_past_first_page_is_caught(self) -> None:
        m, log, key = recorded(1500)
        recs = log.read(key, limit=10**9)
        bad = MemoryLog()
        for r in recs:
            if r.seq == 1200:
                r = dataclasses.replace(r, event_type="NOPE")
            bad.append(r)
        with self.assertRaises(AssertionError) as cm:
            assert_replay_consistent(m, bad, key=key)
        self.assertIn("seq 1200", str(cm.exception))

    def test_long_clean_store_replays_every_record(self) -> None:
        m, log, key = recorded(2001)
        it = assert_replay_consistent(m, log, key=key)
        self.assertEqual(it.current_state_ids, {"m.b"})
        it.stop()

    def test_store_needs_key(self) -> None:
        m, log, _ = recorded(1)
        with self.assertRaises(ValueError):
            assert_replay_consistent(m, log)


class TestUpto(unittest.TestCase):
    def test_inclusive_and_zero(self) -> None:
        m, log, key = recorded(5)
        recs = log.read(key)
        self.assertEqual(replay(m, recs, upto=1).current_state_ids, {"m.b"})
        self.assertEqual(replay(m, recs, upto=2).current_state_ids, {"m.a"})
        self.assertEqual(replay(m, recs, upto=0).current_state_ids, {"m.a"})
        self.assertEqual(
            replay(m, recs, upto=10**6).current_state_ids, {"m.b"}
        )

    def test_negative_or_non_int_refused(self) -> None:
        m, log, key = recorded(2)
        for bad in (-1, 1.5, True, "2"):
            with self.assertRaises(ValueError):
                replay(m, log.read(key), upto=bad)  # type: ignore[arg-type]


class TestContextAndLogic(unittest.TestCase):
    def test_stubs_reproduce_state_not_context(self) -> None:
        m, log, key = recorded(4)
        it = replay(m, log.read(key))
        self.assertEqual(
            (it.current_state_ids, it.context), ({"m.a"}, {"n": 0})
        )

    def test_real_logic_reproduces_context(self) -> None:
        m, log, key = recorded(4)
        it = replay(m, log.read(key), logic=logic())
        self.assertEqual(it.context, {"n": 4})

    def test_callers_machine_untouched(self) -> None:
        m, log, key = recorded(3)
        before = m.logic
        replay(m, log.read(key))
        self.assertIs(m.logic, before)


class TestBrokenLogs(unittest.TestCase):
    def test_gap_names_missing_seq(self) -> None:
        m, log, key = recorded(6)
        recs = log.read(key)
        with self.assertRaises(ReplayDivergenceError) as cm:
            replay(m, recs[:3] + recs[4:])
        self.assertEqual((cm.exception.field, cm.exception.seq), ("seq", 4))

    def test_trimmed_head_without_snapshot(self) -> None:
        m, log, key = recorded(6)
        with self.assertRaises(ReplayDivergenceError) as cm:
            replay(m, log.read(key)[2:])
        self.assertEqual(cm.exception.field, "seq")

    def test_trimmed_head_with_matching_snapshot(self) -> None:
        m = create_machine(CFG, logic=logic())
        log = MemoryLog()
        it = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        it.send("GO")
        it.send("GO")
        snap = it.get_snapshot()
        it.send("GO")
        key = it.store_key or it.id
        r = replay(m, log.read(key)[2:], snapshot=snap)
        self.assertEqual(r.current_state_ids, {"m.b"})

    def test_foreign_snapshot_is_typed(self) -> None:
        m, log, key = recorded(4)
        other = create_machine(
            {"id": "z", "initial": "q", "states": {"q": {}}}
        )
        snap = SyncInterpreter(other).start().get_snapshot()
        with self.assertRaises(XStateMachineError):
            replay(m, log.read(key)[2:], snapshot=snap)

    def test_version_mismatch(self) -> None:
        m, log, key = recorded(2)
        m2 = create_machine({**CFG, "version": "2"}, logic=logic())
        with self.assertRaises(ReplayDivergenceError) as cm:
            replay(m2, log.read(key))
        self.assertEqual(cm.exception.field, "machine_version")

    def test_mixed_keys(self) -> None:
        shared = MemoryLog()
        m, _, _ = recorded(3, shared, "one")
        recorded(2, shared, "two")
        k1, k2 = "one", "two"
        mixed: List[Any] = shared.read(k1) + shared.read(k2)
        with self.assertRaises(ValueError):
            replay(m, mixed)
        self.assertEqual(replay(m, mixed, key=k2).current_state_ids, {"m.a"})
        it = assert_replay_consistent(m, mixed, key=k1)
        self.assertEqual(it.current_state_ids, {"m.b"})


class TestReturnedInterpreter(unittest.TestCase):
    def test_running_and_no_thread_leak(self) -> None:
        m, log, key = recorded(10)
        before = threading.active_count()
        it = assert_replay_consistent(m, log, key=key)
        self.assertEqual(it.status, "running")
        self.assertEqual(threading.active_count(), before)
        it.stop()
        self.assertEqual(it.status, "stopped")

    def test_linear_scale(self) -> None:
        m, log, key = recorded(2)
        recs = log.read(key)

        def build(n: int) -> List[Any]:
            return [
                dataclasses.replace(recs[i % 2], seq=i + 1) for i in range(n)
            ]

        small, large = build(2000), build(20000)
        t0 = time.perf_counter()
        replay(m, small)
        t1 = time.perf_counter()
        replay(m, large)
        t2 = time.perf_counter()
        self.assertLess(t2 - t1, max(0.5, (t1 - t0) * 30))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
