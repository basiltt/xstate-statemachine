"""Battle test #262 part A: transition-log replay fidelity and append ordering.

Attacks `xstate_statemachine.persistence.log` (`TransitionLogPlugin`, the
three log stores, `replay()`) on both engines:

* **Fidelity** -- one chart exercising every outcome kind (changed,
  unhandled, denied, deferred-then-released, errored under ``continue`` and
  ``rollback``, a 3-deep ``raise`` chain, an eventless ``always`` chain, two
  ``after`` rungs, an invoke failing then succeeding, parallel + deep
  history re-entry, a top-level ``final``) is recorded and replayed; the
  replay must reach the identical configuration, context and status, also
  midway (``upto=``) against a snapshot taken at that point.
* **Divergence** -- inverted guard / renamed target / removed action /
  different version, seq gaps, a purged head, interleaved keys.
* **Ordering** -- the log and the snapshot after a real ``os._exit(9)`` at
  each point of the save/append sequence; gap-free seq under 16 threads
  for each lock strategy; two processes on one ``SQLiteLog``.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.clock import SimulatedClock
from src.xstate_statemachine.exceptions import ConflictError
from src.xstate_statemachine.persistence import (
    AuditPlugin,
    JSONLinesLog,
    MemoryLog,
    NoLock,
    OptimisticLock,
    PessimisticLock,
    ReplayDivergenceError,
    SQLiteLog,
    SQLiteStore,
    TransitionLogPlugin,
    TransitionRecord,
    apersisted,
    persisted,
    replay,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHILD_TIMEOUT_S = 60
ENGINE_PREFIXES = ("after.", "done.invoke.", "error.platform.")


# =============================================================================
# 🧪 The everything-chart
# =============================================================================
def _raise(evt: str) -> Dict[str, Any]:
    return {"type": "raise", "params": {"event": {"type": evt}}}


def chart(
    policy: str = "continue",
    version: Optional[str] = None,
    unhandled: str = "defer",
) -> Dict:
    cfg: Dict[str, Any] = {
        "id": "big",
        "initial": "idle",
        "onUnhandled": unhandled,
        "actionErrorPolicy": policy,
        "context": {"n": 0, "data": None},
        "states": {
            "idle": {
                "on": {
                    "START": {"target": "work", "actions": "inc"},
                    "NOPE": {"target": "done", "guard": "never"},
                    "NOOP": {},
                }
            },
            "work": {
                "type": "parallel",
                "states": {
                    "left": {
                        "initial": "l1",
                        "states": {
                            "l1": {
                                "on": {
                                    "STEP": {"target": "l2", "actions": "inc"}
                                }
                            },
                            "l2": {
                                "initial": "deep1",
                                "states": {
                                    "deep1": {"on": {"DEEPER": "deep2"}},
                                    "deep2": {},
                                },
                            },
                            "hist": {"type": "history", "history": "deep"},
                        },
                    },
                    "right": {"initial": "r1", "states": {"r1": {}}},
                },
                "on": {
                    "PAUSE": "paused",
                    "CHAIN": {"actions": [_raise("C1")]},
                    "C1": {"actions": ["inc", _raise("C2")]},
                    "C2": {"actions": ["inc", _raise("C3")]},
                    "C3": {"actions": "inc"},
                    "BOOM": {"actions": ["inc", "boom", "inc"]},
                },
            },
            "paused": {
                "on": {"RESUME": "#big.work.left.hist", "LATER": "fetching"}
            },
            "fetching": {
                "invoke": {
                    "src": "fetchIt",
                    "onDone": {"target": "timed", "actions": "store"},
                    "onError": "failed",
                }
            },
            "failed": {"on": {"RETRY": "fetching2"}},
            "fetching2": {
                "invoke": {
                    "src": "fetchIt",
                    "onDone": {"target": "timed", "actions": "store"},
                    "onError": "failed",
                }
            },
            "timed": {"after": {"100": "rung2"}},
            "rung2": {"after": {"200": "eventless"}},
            "eventless": {"always": "e2"},
            "e2": {"always": {"target": "e3", "actions": "inc"}},
            "e3": {"on": {"FIN": "done", "HELD": {"actions": "inc"}}},
            "done": {"type": "final"},
        },
    }
    if version is not None:
        cfg["version"] = version
    return cfg


SCRIPT = [
    "NOPE",  # guard says no: "denied" (ignore) / "deferred" (defer policy)
    "NOOP",  # handled, targetless, no actions -> unhandled (no change)
    "HELD",  # deferred until e3 (defer policy) / unhandled (ignore)
    "START",
    "STEP",
    "DEEPER",
    "CHAIN",  # raise C1 -> C2 -> C3
    "BOOM",  # action raises
    "PAUSE",
    "RESUME",  # deep history re-entry
    "PAUSE",
    "LATER",  # invoke -> error.platform
    "RETRY",  # invoke -> done.invoke
]


class Effects:
    """Real implementations with an externally visible side-effect log."""

    def __init__(self) -> None:
        self.calls: List[str] = []
        self.tries = 0

    def logic(self, *, guard: bool = False) -> MachineLogic:
        def inc(i: Any, c: Any, e: Any, a: Any) -> None:
            self.calls.append("inc")
            c["n"] += 1

        def boom(i: Any, c: Any, e: Any, a: Any) -> None:
            self.calls.append("boom")
            raise RuntimeError("bang password=hunter2")

        def store(i: Any, c: Any, e: Any, a: Any) -> None:
            c["data"] = e.data

        def fetch(i: Any, c: Any, e: Any) -> Any:
            self.tries += 1
            self.calls.append("fetch")
            if self.tries == 1:
                raise RuntimeError("upstream down")
            return {"v": 7}

        return MachineLogic(
            actions={"inc": inc, "boom": boom, "store": store},
            guards={"never": lambda c, e: guard},
            services={"fetchIt": fetch},
        )


def strip(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in ctx.items() if not str(k).startswith("__xsm")}


def state_of(i: Any) -> Tuple[Any, ...]:
    return (
        tuple(sorted(i.current_state_ids)),
        strip(json.loads(json.dumps(i.context))),
        i.status,
    )


def record_sync(
    log: Any, policy: str = "continue", unhandled: str = "defer"
) -> Tuple[Any, Any, Dict[int, Tuple[Any, ...]], Dict[int, str]]:
    """Run the script on SyncInterpreter; state + snapshot after each step,
    keyed by the last seq written so far."""
    fx = Effects()
    m = create_machine(chart(policy, unhandled=unhandled), logic=fx.logic())
    clock = SimulatedClock()
    i = SyncInterpreter(m, clock=clock).use(TransitionLogPlugin(log)).start()
    states: Dict[int, Tuple[Any, ...]] = {}
    snaps: Dict[int, str] = {}

    def mark() -> None:
        rows = log.read("big", limit=10**6)
        last = rows[-1].seq if rows else 0
        states[last] = state_of(i)
        snaps[last] = i.get_snapshot()

    for ev in SCRIPT:
        i.send(ev)
        mark()
    clock.increment(100)
    mark()
    clock.increment(200)
    mark()
    i.send("FIN")
    mark()
    return m, i, states, snaps


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="b262_"))
        self._closers: List[Any] = []

    def tearDown(self) -> None:
        for c in reversed(self._closers):
            try:
                c()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sqlite(self, name: str = "app.db") -> SQLiteStore:
        s = SQLiteStore(self.tmp / name)
        self._closers.append(s.close)
        return s

    def logs(self) -> Dict[str, Any]:
        return {
            "memory": MemoryLog(),
            "jsonl": JSONLinesLog(self.tmp / "log.jsonl"),
            "sqlite": SQLiteLog(self.sqlite()),
        }


# =============================================================================
# 🔁 Fidelity
# =============================================================================
class TestReplayFidelity(_Tmp):
    def test_every_outcome_kind_is_recorded(self) -> None:
        log = MemoryLog()
        record_sync(log)
        rows = log.read("big")
        self.assertEqual([r.seq for r in rows], list(range(1, len(rows) + 1)))
        disp = {r.disposition for r in rows}
        self.assertEqual(
            disp, {"unhandled", "deferred", "transition", "error"}
        )
        by = [(r.event_type, r.disposition, r.origin) for r in rows]
        # under onUnhandled=defer a guard-blocked event is deferred
        self.assertIn(("NOPE", "deferred", "external"), by)
        self.assertIn(("HELD", "deferred", "external"), by)
        self.assertIn(("BOOM", "error", "external"), by)
        # the raise chain: one record per processed event, all internal
        for evt in ("C1", "C2", "C3"):
            self.assertIn((evt, "transition", "internal"), by)
        # engine events are internal + engine-flagged
        for r in rows:
            if r.event_type.startswith(ENGINE_PREFIXES):
                self.assertTrue(r.engine)
                self.assertEqual(r.origin, "internal")
        # the deferred event is released at e3 -> an internal record
        self.assertEqual(
            [r.origin for r in rows if r.event_type == "HELD"][-1], "internal"
        )
        boom = next(r for r in rows if r.event_type == "BOOM")
        self.assertEqual(boom.error["type"], "RuntimeError")
        self.assertEqual(boom.error["actions"], "boom")

    def test_denied_under_ignore_policy_records_and_replays(self) -> None:
        for engine_logic in (None, "real"):
            with self.subTest(logic=engine_logic):
                log = MemoryLog()
                m, orig, _, _ = record_sync(log, unhandled="ignore")
                rows = log.read("big")
                self.assertEqual(rows[0].disposition, "denied")
                self.assertEqual(rows[0].to_states, rows[0].from_states)
                lg = Effects().logic() if engine_logic else None
                r = replay(m, rows, logic=lg)
                want = state_of(orig) if lg else state_of(orig)[0]
                got = state_of(r) if lg else state_of(r)[0]
                self.assertEqual(got, want)

    def test_replay_matches_on_all_three_stores_with_real_logic(self) -> None:
        for name, log in self.logs().items():
            for policy in ("continue", "rollback"):
                with self.subTest(store=name, policy=policy):
                    log.forget("big")
                    m, orig, _, _ = record_sync(log, policy)
                    fx = Effects()
                    r = replay(m, log.read("big"), logic=fx.logic())
                    self.assertEqual(state_of(r), state_of(orig))
                    self.assertEqual(orig.status, "done")
                    # the service was NOT called again: completions are
                    # replayed from the record, even with real logic
                    self.assertNotIn("fetch", fx.calls)
                    r.stop()

    def test_replay_matches_state_with_stub_logic(self) -> None:
        log = MemoryLog()
        m, orig, _, _ = record_sync(log)
        r = replay(m, log.read("big"))
        self.assertEqual(state_of(r)[0], state_of(orig)[0])
        self.assertEqual(r.status, "done")
        # stubs reproduce state, not context (documented)
        self.assertEqual(r.context["n"], 0)

    def test_upto_midway_matches_snapshot_taken_at_that_point(self) -> None:
        log = MemoryLog()
        m, _orig, states, snaps = record_sync(log)
        for seq, expected in states.items():
            with self.subTest(upto=seq):
                r = replay(
                    m, log.read("big"), upto=seq, logic=Effects().logic()
                )
                self.assertEqual(state_of(r)[:2], expected[:2])
                r.stop()

    def test_replay_from_snapshot_plus_tail(self) -> None:
        """A purged head is replayable from a snapshot at the cut."""
        log = MemoryLog()
        m, orig, states, snaps = record_sync(log)
        cut = sorted(states)[5]
        tail = [r for r in log.read("big") if r.seq > cut]
        r = replay(m, tail, snapshot=snaps[cut], logic=Effects().logic())
        self.assertEqual(state_of(r), state_of(orig))

    def test_replay_never_sends_engine_minted_events(self) -> None:
        log = MemoryLog()
        m, orig, _, _ = record_sync(log)
        sent: List[str] = []
        real = SyncInterpreter.send

        def spy(self_: Any, ev: Any, *a: Any, **k: Any) -> Any:
            sent.append(str(getattr(ev, "type", ev)))
            return real(self_, ev, *a, **k)

        with mock.patch.object(SyncInterpreter, "send", spy):
            r = replay(m, log.read("big"), logic=Effects().logic())
        self.assertFalse([s for s in sent if s.startswith(ENGINE_PREFIXES)])
        # internal events (raise chain, released deferral) not re-sent
        self.assertNotIn("C1", sent)
        self.assertEqual(sent.count("HELD"), 1)
        self.assertEqual(state_of(r), state_of(orig))

    def test_side_effects_stubbed_without_logic_repeat_with_it(self) -> None:
        fx = Effects()
        m = create_machine(chart(), logic=fx.logic())
        log = MemoryLog()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("START")
        self.assertEqual(fx.calls, ["inc"])
        replay(m, log.read("big")).stop()
        self.assertEqual(fx.calls, ["inc"])  # stub: did not fire
        replay(m, log.read("big"), logic=m.logic).stop()
        self.assertEqual(fx.calls, ["inc", "inc"])  # real: fires again

    def test_action_sending_to_its_own_machine(self) -> None:
        """An action's own `send()` is internal: not re-sent with real logic
        (the action re-sends it), re-sent from the record under stubs."""
        cfg = {
            "id": "s",
            "initial": "a",
            "actionErrorPolicy": "continue",
            "context": {"n": 0},
            "states": {
                "a": {"on": {"SEND": {"actions": "sender"}, "X": "b"}},
                "b": {"entry": "inc"},
            },
        }

        def sender(i: Any, c: Any, e: Any, a: Any) -> None:
            i.send("X")

        lg = MachineLogic(
            actions={
                "sender": sender,
                "inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1),
            }
        )
        m = create_machine(cfg, logic=lg)
        log = MemoryLog()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("SEND")
        rows = log.read("s")
        self.assertEqual(
            [(r.event_type, r.origin) for r in rows],
            [("SEND", "external"), ("X", "internal")],
        )
        self.assertEqual(state_of(replay(m, rows, logic=lg)), state_of(i))
        self.assertEqual(
            replay(m, rows).current_state_ids, i.current_state_ids
        )

    def test_macrostep_records_and_leaf_ids(self) -> None:
        log = MemoryLog()
        record_sync(log)
        rows = log.read("big")
        # an `always` chain is folded into the triggering record
        after200 = next(
            r for r in rows if r.event_type.startswith("after.200")
        )
        self.assertEqual(after200.to_states, ("big.e3",))
        self.assertEqual(after200.actions, ("inc",))
        # leaves only, sorted; parallel -> one leaf per region
        start = next(r for r in rows if r.event_type == "START")
        self.assertEqual(
            start.to_states, ("big.work.left.l1", "big.work.right.r1")
        )
        for r in rows:
            for sid in r.from_states + r.to_states:
                self.assertNotIn(sid, ("big.work", "big.work.left"))


class TestDivergence(_Tmp):
    def _rows(self) -> Tuple[Any, List[TransitionRecord]]:
        log = MemoryLog()
        m, *_ = record_sync(log)
        return m, log.read("big")

    def test_inverted_guard(self) -> None:
        _m, rows = self._rows()
        m2 = create_machine(chart(), logic=Effects().logic(guard=True))
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m2, rows)
        self.assertEqual(ei.exception.seq, 1)
        self.assertEqual(ei.exception.expected, ("big.idle",))
        self.assertEqual(ei.exception.actual, ("big.done",))

    def test_renamed_target(self) -> None:
        _m, rows = self._rows()
        cfg = chart()
        st = cfg["states"]["work"]["states"]["left"]["states"]
        st["l1"]["on"]["STEP"]["target"] = "l3"
        st["l3"] = {}
        m2 = create_machine(cfg, logic=Effects().logic())
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m2, rows)
        seq = next(r.seq for r in rows if r.event_type == "STEP")
        self.assertEqual(ei.exception.seq, seq)
        self.assertEqual(ei.exception.field, "to_states")
        self.assertIn("big.work.left.l3", ei.exception.actual)

    def test_removed_action(self) -> None:
        _m, rows = self._rows()
        cfg = chart()
        cfg["states"]["work"]["states"]["left"]["states"]["l1"]["on"][
            "STEP"
        ] = "l2"
        m2 = create_machine(cfg, logic=Effects().logic())
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m2, rows)
        self.assertEqual(ei.exception.field, "actions")
        self.assertEqual(ei.exception.expected, ("inc",))
        self.assertEqual(ei.exception.actual, ())

    def test_different_version_string(self) -> None:
        _m, rows = self._rows()
        m2 = create_machine(chart(version="v2"), logic=Effects().logic())
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m2, rows)
        self.assertEqual(ei.exception.field, "machine_version")
        self.assertEqual(
            (ei.exception.expected, ei.exception.actual), ("", "v2")
        )
        # verify=False is the explicit "replay it on the new version anyway"
        r = replay(m2, rows, verify=False)
        self.assertEqual(r.status, "done")

    def test_seq_gap_is_loud(self) -> None:
        m, rows = self._rows()
        gapped = rows[:5] + rows[6:]
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m, gapped)
        self.assertEqual((ei.exception.field, ei.exception.seq), ("seq", 6))

    def test_deleted_row_in_sqlite_is_loud(self) -> None:
        store = self.sqlite()
        log = SQLiteLog(store)
        m, *_ = record_sync(log)
        store._conn().execute(
            "DELETE FROM transitions WHERE machine_id='big' AND seq=7"
        )
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m, log.read("big"))
        self.assertEqual(ei.exception.seq, 7)

    def test_purged_head_without_snapshot_is_loud(self) -> None:
        m, rows = self._rows()
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m, rows[3:])
        self.assertEqual(ei.exception.field, "seq")
        self.assertEqual(ei.exception.expected, 1)

    def test_tampered_event_type_and_extra_record(self) -> None:
        m, rows = self._rows()
        bad = list(rows)
        k = next(n for n, r in enumerate(rows) if r.event_type == "C2")
        bad[k] = TransitionRecord(**{**rows[k].to_dict(), "event_type": "CX"})
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m, bad)
        self.assertEqual(ei.exception.field, "event_type")
        # a log that stops short of what the engine does is "unrecorded"
        k2 = next(n for n, r in enumerate(rows) if r.event_type == "C3")
        with self.assertRaises(ReplayDivergenceError) as ei:
            replay(m, rows[:k2])
        self.assertEqual(ei.exception.field, "unrecorded")

    def test_interleaved_keys(self) -> None:
        log = MemoryLog()
        fx = Effects()
        m = create_machine(chart(), logic=fx.logic())
        a = (
            SyncInterpreter(m)
            .use(TransitionLogPlugin(log, machine_id=lambda i: "A"))
            .start()
        )
        b = (
            SyncInterpreter(m)
            .use(TransitionLogPlugin(log, machine_id=lambda i: "B"))
            .start()
        )
        for ev in ("START", "STEP", "PAUSE"):
            a.send(ev)
            b.send("NOPE")
        b.send("START")
        mixed = log.read("A") + log.read("B")
        with self.assertRaises(ValueError):
            replay(m, mixed)
        self.assertEqual(
            replay(m, mixed, key="A").current_state_ids, a.current_state_ids
        )
        self.assertEqual(
            replay(m, mixed, key="B").current_state_ids, b.current_state_ids
        )


# =============================================================================
# 🔐 Payload capture
# =============================================================================
class TestPayloadCapture(_Tmp):
    def test_large_payload_verbatim_and_redaction(self) -> None:
        log = JSONLinesLog(self.tmp / "p.jsonl")
        fx = Effects()
        m = create_machine(chart(), logic=fx.logic())
        i = SyncInterpreter(m).use(AuditPlugin(log)).start()
        blob = "x" * (1 << 20)
        i.send("START", blob=blob, password="hunter2", nested={"apiKey": "k"})
        i.send("BOOM")
        rows = log.read("big")
        p = rows[0].event_payload
        self.assertEqual(len(p["blob"]), 1 << 20)  # no cap: stored verbatim
        self.assertEqual(p["password"], "***")
        self.assertEqual(p["nested"], {"apiKey": "***"})
        # context is not recorded at all -> nothing to redact there
        self.assertNotIn("context", rows[0].to_dict())
        # 📌 Pinned limitation: redaction is KEY-based; an exception's free
        #    text is recorded verbatim (as LoggingInspector logs it).
        self.assertEqual(rows[1].error["message"], "bang password=hunter2")
        self.assertEqual(rows[1].error["actions"], "boom")

    def test_service_error_message_is_recorded_verbatim(self) -> None:
        """Pinned limitation: an exception's TEXT is not key-redacted."""
        log = MemoryLog()
        m = create_machine(chart(), logic=Effects().logic())
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        for ev in ("START", "PAUSE", "LATER"):
            i.send(ev)
        err = [r for r in log.read("big") if r.event_type.startswith("error.")]
        self.assertEqual(
            err[0].event_payload["error"]["message"], "upstream down"
        )


# =============================================================================
# 🧵 Ordering under concurrency
# =============================================================================
COUNTER = {
    "id": "c",
    "initial": "a",
    "actionErrorPolicy": "continue",
    "context": {"n": 0},
    "states": {"a": {"on": {"INC": {"actions": "inc"}}}},
}


def counter_machine() -> Any:
    return create_machine(
        COUNTER,
        logic=MachineLogic(
            actions={"inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}
        ),
    )


class TestSeqUnderConcurrency(_Tmp):
    THREADS = 16
    PER = 100

    def _hammer(self, lock_factory: Any) -> Tuple[SQLiteStore, SQLiteLog, int]:
        store = self.sqlite(f"{id(lock_factory)}.db")
        log = SQLiteLog(store)
        m = counter_machine()
        plugin = TransitionLogPlugin(log)
        committed = [0]
        gate = threading.Lock()
        errors: List[BaseException] = []

        def worker() -> None:
            for _ in range(self.PER):
                try:
                    lock = lock_factory()
                    if isinstance(lock, OptimisticLock):
                        lock.run(
                            store,
                            "k",
                            m,
                            lambda i: i.send("INC"),
                            plugins=[plugin],
                        )
                    else:
                        with persisted(
                            store, "k", m, plugins=[plugin], lock=lock
                        ) as i:
                            i.send("INC")
                    with gate:
                        committed[0] += 1
                except ConflictError:
                    pass  # retries exhausted: nothing committed
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

        ts = [threading.Thread(target=worker) for _ in range(self.THREADS)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])
        return store, log, committed[0]

    def _assert_gap_free(self, log: SQLiteLog, n: int) -> None:
        seqs = [r.seq for r in log.read("k", limit=10**6)]
        self.assertEqual(seqs, list(range(1, n + 1)))

    def test_optimistic_only_committed_attempts_are_logged(self) -> None:
        store, log, committed = self._hammer(
            lambda: OptimisticLock(retries=50)
        )
        n = json.loads(store.load("k").snapshot)["context"]["n"]
        self.assertEqual(n, committed)
        self._assert_gap_free(log, committed)  # a lost attempt: no record

    def test_pessimistic(self) -> None:
        store, log, committed = self._hammer(
            lambda: PessimisticLock(timeout=30)
        )
        self.assertEqual(committed, self.THREADS * self.PER)
        n = json.loads(store.load("k").snapshot)["context"]["n"]
        self.assertEqual(n, committed)
        self._assert_gap_free(log, committed)

    def test_nolock_seq_is_still_gap_free(self) -> None:
        """NoLock loses context updates (last writer wins, documented) but
        the log keeps one gap-free record per committed block -- before
        the fix two writers minted the same seq and the PK refused one."""
        _store, log, committed = self._hammer(NoLock)
        self.assertEqual(committed, self.THREADS * self.PER)
        self._assert_gap_free(log, committed)

    def test_append_next_is_atomic_per_store(self) -> None:
        for name, log in self.logs().items():
            with self.subTest(store=name):
                proto = TransitionRecord(
                    machine_id="x",
                    seq=0,
                    ts=1.0,
                    event_type="E",
                    event_payload={},
                    from_states=(),
                    to_states=(),
                    actions=(),
                )

                def go() -> None:
                    for _ in range(25):
                        log.append_next(proto)

                ts = [threading.Thread(target=go) for _ in range(8)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                seqs = [r.seq for r in log.read("x", limit=10**6)]
                self.assertEqual(seqs, list(range(1, 201)))

    def test_separate_log_is_written_after_the_commit(self) -> None:
        """In-process twin of the kill: when the JSONL append runs, the
        pessimistic transaction has already committed."""
        store = self.sqlite()
        log = JSONLinesLog(self.tmp / "sep.jsonl")
        seen: List[bool] = []
        real = log.append_next

        def spy(rec: Any, **k: Any) -> Any:
            seen.append(store._conn().in_transaction)
            return real(rec, **k)

        log.append_next = spy  # type: ignore[method-assign]
        with persisted(
            store,
            "k",
            counter_machine(),
            plugins=[TransitionLogPlugin(log)],
            lock=PessimisticLock(),
        ) as i:
            i.send("INC")
        self.assertEqual(seen, [False])
        self.assertEqual(len(log.read("k")), 1)

    def test_raised_block_and_lost_conflict_leave_no_record(self) -> None:
        store = self.sqlite()
        log = SQLiteLog(store)
        m = counter_machine()
        plugin = TransitionLogPlugin(log)
        with self.assertRaises(RuntimeError):
            with persisted(store, "k", m, plugins=[plugin]) as i:
                i.send("INC")
                raise RuntimeError("caller aborted")
        self.assertEqual(log.read("k"), [])
        with self.assertRaises(ConflictError):
            with persisted(store, "k", m, plugins=[plugin]) as i:
                i.send("INC")
                store.save("k", i.get_snapshot())  # a concurrent writer
        self.assertEqual(log.read("k"), [])


TWO_PROC_CHILD = r"""
import json, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine import create_machine, SyncInterpreter
from src.xstate_statemachine.persistence import (
    SQLiteLog, SQLiteStore, TransitionLogPlugin)
m = create_machine({"id": "c", "initial": "a",
                    "states": {"a": {"on": {"T": {}}}}})
log = SQLiteLog(SQLiteStore(args["db"]))
i = SyncInterpreter(m).use(
    TransitionLogPlugin(log, machine_id=lambda _i: "shared")).start()
for _ in range(args["n"]):
    i.send("T")
"""


class TestTwoProcesses(_Tmp):
    def test_two_processes_one_key_gap_free(self) -> None:
        db = self.tmp / "shared.db"
        SQLiteLog(self.sqlite("shared.db"))  # create the table up front
        args = json.dumps({"root": str(ROOT), "db": str(db), "n": 150})
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", TWO_PROC_CHILD, args],
                cwd=str(ROOT),
                stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        for p in procs:
            _out, err = p.communicate(timeout=CHILD_TIMEOUT_S)
            self.assertEqual(p.returncode, 0, err.decode(errors="replace"))
        log = SQLiteLog(self.sqlite("shared.db"))
        seqs = [r.seq for r in log.read("shared", limit=10**6)]
        self.assertEqual(seqs, list(range(1, 301)))


# =============================================================================
# 💀 Log vs snapshot after a kill
# =============================================================================
KILL_CHILD = r"""
import asyncio, json, os, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine import create_machine, MachineLogic
from src.xstate_statemachine.persistence import (
    JSONLinesLog, OptimisticLock, PessimisticLock, SQLiteLog, SQLiteStore,
    TransitionLogPlugin, apersisted, persisted)

m = create_machine(args["cfg"], logic=MachineLogic(actions={
    "inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}))
store = SQLiteStore(args["db"])
log = (SQLiteLog(store) if args["log"] == "sqlite"
       else JSONLinesLog(args["jsonl"]))
plugin = TransitionLogPlugin(log)
lock = PessimisticLock(timeout=10) if args["lock"] == "pess" else OptimisticLock()

def step():
    if args["engine"] == "sync":
        with persisted(store, "k", m, plugins=[plugin], lock=lock) as i:
            i.send("INC")
    else:
        async def go():
            async with apersisted(store, "k", m, plugins=[plugin],
                                  lock=lock) as i:
                await i.send("INC", wait=True)
        asyncio.run(go())

step()  # step 1 commits normally
point = args["point"]
if point == "after_save":
    real = store.save
    def save(*a, **k):
        real(*a, **k)
        os._exit(9)
    store.save = save
elif point == "after_append":
    real_a = log.append_next
    def append_next(*a, **k):
        real_a(*a, **k)
        os._exit(9)
    log.append_next = append_next
step()
sys.exit(3)
"""


class TestKillWindows(_Tmp):
    def _kill(
        self, point: str, log_kind: str, lock: str, engine: str
    ) -> Tuple[int, int]:
        args = {
            "root": str(ROOT),
            "cfg": COUNTER,
            "db": str(self.tmp / f"{point}{log_kind}{lock}{engine}.db"),
            "jsonl": str(self.tmp / f"{point}{lock}{engine}.jsonl"),
            "log": log_kind,
            "lock": lock,
            "engine": engine,
            "point": point,
        }
        p = subprocess.run(
            [sys.executable, "-c", KILL_CHILD, json.dumps(args)],
            cwd=str(ROOT),
            capture_output=True,
            timeout=CHILD_TIMEOUT_S,
        )
        self.assertEqual(
            p.returncode, 9, p.stderr.decode(errors="replace")[-2000:]
        )
        store = self.sqlite(pathlib.Path(args["db"]).name)
        snap_n = json.loads(store.load("k").snapshot)["context"]["n"]
        log = (
            SQLiteLog(store)
            if log_kind == "sqlite"
            else JSONLinesLog(args["jsonl"])
        )
        rows = log.read("k")
        self.assertEqual([r.seq for r in rows], list(range(1, len(rows) + 1)))
        return snap_n, len(rows)

    def test_shared_sqlite_pessimistic_commits_together(self) -> None:
        """GUARANTEE: the log append and the save are one transaction."""
        for engine in ("sync", "async"):
            for point in ("after_save", "after_append"):
                with self.subTest(engine=engine, point=point):
                    self.assertEqual(
                        self._kill(point, "sqlite", "pess", engine), (1, 1)
                    )

    def test_optimistic_or_separate_log_snapshot_may_lead_never_lag(
        self,
    ) -> None:
        """Without a shared transaction the save commits first; a kill
        before the append leaves the snapshot ONE step ahead of the log --
        never the log ahead of the state (before the fix: the reverse)."""
        cases = [
            ("after_save", "sqlite", "opt", "sync", (2, 1)),
            ("after_save", "jsonl", "opt", "async", (2, 1)),
            # pess + a separate log: the kill lands before COMMIT, and the
            # append is deferred to after it (before the fix: (1, 2))
            ("after_save", "jsonl", "pess", "sync", (1, 1)),
            ("after_save", "jsonl", "pess", "async", (1, 1)),
            ("after_append", "sqlite", "opt", "sync", (2, 2)),
            ("after_append", "jsonl", "opt", "sync", (2, 2)),
        ]
        for point, log_kind, lock, engine, want in cases:
            with self.subTest(point=point, log=log_kind, lock=lock, e=engine):
                self.assertEqual(
                    self._kill(point, log_kind, lock, engine), want
                )


# =============================================================================
# ⚡ Async parity
# =============================================================================
class TestAsyncParity(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="b262a_"))

    async def asyncTearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    async def _settle(self, i: Any, target: str) -> None:
        for _ in range(200):
            if any(s.endswith(target) for s in i.current_state_ids):
                return
            await asyncio.sleep(0.005)
        self.fail(f"never reached {target}: {i.current_state_ids}")

    async def test_async_recorded_log_equals_sync_and_replays(self) -> None:
        sync_log = MemoryLog()
        # 📝 Off the loop: inside one, SimulatedClock.increment returns an
        #    awaitable and the sync recording's timers would never fire.
        m, sync_i, _, _ = await asyncio.to_thread(record_sync, sync_log)

        log = MemoryLog()
        fx = Effects()
        m2 = create_machine(chart(), logic=fx.logic())
        clock = SimulatedClock()
        i = (
            await Interpreter(m2, clock=clock)
            .use(TransitionLogPlugin(log))
            .start()
        )
        for ev in SCRIPT:
            await i.send(ev)
            await asyncio.sleep(0)
            if ev == "LATER":
                await self._settle(i, "failed")
            elif ev == "RETRY":
                await self._settle(i, "timed")
            else:
                await asyncio.sleep(0.01)
        for target, ms in (("rung2", 100), ("e3", 200)):
            for _ in range(200):  # the timer is armed by the run loop
                if clock.pending:
                    break
                await asyncio.sleep(0.005)
            await clock.increment(ms)
            await self._settle(i, target)
        await i.send("FIN")
        await self._settle(i, "done")

        def shape(rows: List[TransitionRecord]) -> List[Tuple[Any, ...]]:
            return [
                (
                    r.seq,
                    r.event_type,
                    r.disposition,
                    r.origin,
                    r.to_states,
                    r.actions,
                )
                for r in rows
            ]

        self.assertEqual(shape(log.read("big")), shape(sync_log.read("big")))
        r = replay(m2, log.read("big"), logic=Effects().logic())
        self.assertEqual(state_of(r), state_of(i))
        self.assertEqual(state_of(r), state_of(sync_i))
        r.stop()

    async def test_apersisted_pessimistic_shared_sqlite_logs(self) -> None:
        """Before the fix: the post-save append ran on the loop thread while
        the adapter's worker held BEGIN IMMEDIATE -> LockTimeoutError and
        no records at all."""
        store = SQLiteStore(self.tmp / "a.db")
        try:
            log = SQLiteLog(store)
            m = counter_machine()
            plugin = TransitionLogPlugin(log)
            for _ in range(3):
                async with apersisted(
                    store,
                    "k",
                    m,
                    plugins=[plugin],
                    lock=PessimisticLock(timeout=5),
                ) as i:
                    await i.send("INC", wait=True)
            self.assertEqual([r.seq for r in log.read("k")], [1, 2, 3])
            self.assertEqual(
                json.loads(store.load("k").snapshot)["context"]["n"], 3
            )
            r = replay(m, log.read("k"), logic=m.logic)
            self.assertEqual(r.context["n"], 3)
        finally:
            store.close()

    async def test_event_pending_at_block_exit_is_logged_when_run(
        self,
    ) -> None:
        """A fire-and-forget send still queued when `apersisted` takes the
        snapshot is persisted as PENDING. Before the fix its record was
        flushed anyway (processed while `await save` yielded), and the
        restore re-processed it: the log carried the step twice and ran
        ahead of the state. Now the log follows the snapshot exactly."""
        store = SQLiteStore(self.tmp / "p.db")
        try:
            log = SQLiteLog(store)
            m = counter_machine()
            plugin = TransitionLogPlugin(log)
            for _ in range(3):
                async with apersisted(store, "k", m, plugins=[plugin]) as i:
                    await i.send("INC")  # no wait: may still be queued
            snap = json.loads(store.load("k").snapshot)
            done = snap["context"]["n"]
            self.assertEqual(
                [r.seq for r in log.read("k")], list(range(1, done + 1))
            )
            # the pending one is processed (and logged) by the next block
            async with apersisted(store, "k", m, plugins=[plugin]) as i:
                await i.send("INC", wait=True)
            n = json.loads(store.load("k").snapshot)["context"]["n"]
            self.assertEqual(n, 4)
            self.assertEqual([r.seq for r in log.read("k")], [1, 2, 3, 4])
        finally:
            store.close()

    async def test_async_external_vs_internal_origin(self) -> None:
        log = MemoryLog()
        m = create_machine(chart(), logic=Effects().logic())
        i = await Interpreter(m).use(TransitionLogPlugin(log)).start()
        await i.send("START")
        await i.send("CHAIN")
        await asyncio.sleep(0.05)
        await i.stop()
        got = [(r.event_type, r.origin) for r in log.read("big")]
        self.assertEqual(
            got,
            [
                ("START", "external"),
                ("CHAIN", "external"),
                ("C1", "internal"),
                ("C2", "internal"),
                ("C3", "internal"),
            ],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
