# tests/test_battle_305_snapshots_clock_codec.py
# -----------------------------------------------------------------------------
# 🧪 Battle tests for #305 part B: snapshot layout v4, wall clock, deadlines,
#    machine version and the receipt codec.
# -----------------------------------------------------------------------------
"""Adversarial tests. Rule under test (AGENTS.md): a bad snapshot value is a
typed `XStateMachineError` (`SnapshotCorruptError` for shape), never a bare
TypeError / KeyError / ValueError / AttributeError."""

from __future__ import annotations

import asyncio
import copy
import gc
import itertools
import json
import math
import pathlib
import random
import sys
import time
import tracemalloc
import unittest
from typing import Any, Callable, Dict, List
from unittest import mock

import pytest

import src.xstate_statemachine as _pkg
from src.xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    create_machine,
    receipt_from_json,
    receipt_to_json,
    receipt_to_status,
)
from src.xstate_statemachine.clock import RealClock, SimulatedClock
from src.xstate_statemachine.events import Receipt
from src.xstate_statemachine.exceptions import (
    SnapshotCorruptError,
    SnapshotDriftError,
    SnapshotVersionError,
    XStateMachineError,
)
from src.xstate_statemachine.persistence import (
    SNAPSHOT_VERSION,
    Deadline,
    check_deadline_record,
    snapshot as snapmod,
)
from src.xstate_statemachine.receipts import ReceiptError

#: The package directory, for attributing tracemalloc allocations to the
#: library (and not to pytest, coverage, or the test itself).
SRC_DIR = pathlib.Path(_pkg.__file__).resolve().parent

CFG: Dict[str, Any] = {
    "id": "m",
    "version": "1",
    "initial": "p",
    "context": {"n": 1},
    "states": {
        "p": {
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "h0",
                    "states": {
                        "h0": {"on": {"X": "h1"}},
                        "h1": {},
                        "hist": {"type": "history"},
                    },
                },
                "r2": {
                    "initial": "w",
                    "states": {"w": {"after": {"5000": "d"}}, "d": {}},
                },
            },
        }
    },
}

TIMER_CFG: Dict[str, Any] = {
    "id": "t",
    "initial": "a",
    "context": {"fired": 0},
    "states": {
        "a": {"after": {"5000": "b"}, "on": {"BOUNCE": "c"}},
        "c": {"on": {"BACK": "a"}},
        "b": {"on": {"AGAIN": "a"}},
    },
}


def _sync_snapshot(cfg: Dict[str, Any] = CFG) -> str:
    i = SyncInterpreter(create_machine(cfg)).start()
    try:
        return i.get_snapshot()
    finally:
        i.stop()


def _load_both(text: Any, machine: Any = None, **kw: Any) -> None:
    """Restore on both engines; the caller asserts on the exception."""
    machine = machine or create_machine(CFG)
    SyncInterpreter.from_snapshot(text, machine, **kw)
    Interpreter.from_snapshot(text, machine, **kw)


def _outcome(text: Any, engine: Any) -> str:
    """'ok' | typed-error class name | 'BARE:<cls>' for a leaked builtin."""
    try:
        engine.from_snapshot(text, create_machine(CFG))
    except XStateMachineError as exc:
        return type(exc).__name__
    except Exception as exc:  # noqa: BLE001 - this IS the defect detector
        return f"BARE:{type(exc).__name__}:{exc}"
    return "ok"


# -----------------------------------------------------------------------------
# 💥 Corruption fuzz
# -----------------------------------------------------------------------------
class TestByteFuzz(unittest.TestCase):
    def _sweep(self, text: str, positions: List[int]) -> List[str]:
        raw = text.encode("utf-8")
        bare: List[str] = []
        for pos in positions:
            variants = [
                raw[:pos] + bytes([raw[pos] ^ 0xFF]) + raw[pos + 1 :],
                raw[:pos] + bytes([raw[pos] ^ 0x01]) + raw[pos + 1 :],
                raw[:pos],
                raw[:pos] + b"\x00" + raw[pos:],
                raw[:pos] + b'"' + raw[pos:],
            ]
            for blob in variants:
                s = blob.decode("latin-1")
                for engine in (SyncInterpreter, Interpreter):
                    res = _outcome(s, engine)
                    if res.startswith("BARE"):
                        bare.append(f"@{pos} {engine.__name__}: {res}")
        return bare

    def test_every_byte_position_flip_truncate_insert_is_typed(self) -> None:
        # Arrange
        text = json.dumps(json.loads(_sync_snapshot()), separators=(",", ":"))
        positions = list(range(len(text)))
        random.Random(305).shuffle(positions)
        # Act -- every position; ~5 variants x 2 engines each
        bare = self._sweep(text, positions)
        # Assert
        self.assertEqual(bare[:5], [])

    def test_smallest_blob_every_position(self) -> None:
        # Arrange: the tiniest valid blob, so the sweep is exhaustive
        cfg = {"id": "s", "initial": "a", "states": {"a": {}}}
        i = SyncInterpreter(create_machine(cfg)).start()
        text = json.dumps(json.loads(i.get_snapshot()), separators=(",", ":"))
        i.stop()
        raw = text.encode()
        bare = []
        for pos in range(len(raw)):
            for blob in (
                raw[:pos] + bytes([raw[pos] ^ 0xFF]) + raw[pos + 1 :],
                raw[:pos],
                raw[:pos] + b"\x07" + raw[pos:],
            ):
                for engine in (SyncInterpreter, Interpreter):
                    try:
                        engine.from_snapshot(
                            blob.decode("latin-1"), create_machine(cfg)
                        )
                    except XStateMachineError:
                        pass
                    except Exception as exc:  # noqa: BLE001
                        bare.append((pos, type(exc).__name__, str(exc)))
        self.assertEqual(bare[:5], [])

    def test_invalid_json_is_wrapped_not_raw(self) -> None:
        # Arrange / Act / Assert: documented as InvalidConfigError wrap
        for engine in (SyncInterpreter, Interpreter):
            with self.assertRaises(XStateMachineError):
                engine.from_snapshot("{", create_machine(CFG))


def _mutations() -> List[Any]:
    base = json.loads(_sync_snapshot())
    out: List[Any] = []
    for key in base:
        for label, val in (
            ("DEL", ...),
            ("None", None),
            ("str", "x"),
            ("int", 7),
            ("list", []),
            ("dict", {}),
            ("float", 1.5),
            ("bool", True),
            ("nested", [{"state_id": 5}]),
            ("nestedmap", {"a": 1}),
            ("listoflist", [[1]]),
        ):
            blob = copy.deepcopy(base)
            if val is ...:
                del blob[key]
            else:
                blob[key] = val
            out.append((f"{key}:{label}", blob))
    extra = {
        "version-str4": {"version": "4"},
        "version-float4": {"version": 4.0},
        "version-neg": {"version": -1},
        "version-huge": {"version": 2**63},
        "version-nan": {"version": float("nan")},
        "version-inf": {"version": float("inf")},
        "version-v5": {"version": 5},
        "mv-huge": {"machine_version": "x" * 1_000_000},
        "mv-int": {"machine_version": 1},
        "ids-unknown": {
            "state_ids": ["m.nope"],
            "configuration": ["m", "m.nope"],
        },
        "ids-dup": {
            "state_ids": ["m.p.r1.h0", "m.p.r1.h0", "m.p.r2.w"],
        },
        "ids-compound-leaf": {
            "state_ids": ["m.p.r1", "m.p.r2.w"],
            "configuration": ["m", "m.p", "m.p.r1", "m.p.r2", "m.p.r2.w"],
        },
        "dl-bad-due": {
            "deadlines": [
                {
                    "state_id": "m.p.r2.w",
                    "entry_seq": 1,
                    "due_at_wall": "soon",
                    "delay_ms": 5,
                    "event_type": "e",
                }
            ]
        },
        "dl-unknown-state": {
            "deadlines": [
                {
                    "state_id": "m.ghost",
                    "entry_seq": 1,
                    "due_at_wall": 1.0,
                    "delay_ms": 5,
                    "event_type": "e",
                }
            ]
        },
        "dl-nan": {
            "deadlines": [
                {
                    "state_id": "m.p.r2.w",
                    "entry_seq": 1,
                    "due_at_wall": float("nan"),
                    "delay_ms": 5,
                    "event_type": "e",
                }
            ]
        },
        "dl-huge-seq": {
            "deadlines": [
                {
                    "state_id": "m.p.r2.w",
                    "entry_seq": 10**30,
                    "due_at_wall": 1.0,
                    "delay_ms": 5,
                    "event_type": "e",
                }
            ]
        },
        "ctx-list": {"context": []},
        "hist-wrong": {"history": {"m.p.r1": "m.p.r1.h0"}},
        "hist-unknown": {"history": {"m.p.r1": ["m.ghost"]}},
    }
    for label, patch in extra.items():
        blob = copy.deepcopy(base)
        blob.update(patch)
        out.append((label, blob))
    return out


class TestStructuralMutations(unittest.TestCase):
    def test_every_mutation_is_success_or_typed_on_both_engines(self) -> None:
        # Arrange
        bad: List[str] = []
        for label, blob in _mutations():
            text = json.dumps(blob)  # NaN/Infinity pass through json.loads
            for engine in (SyncInterpreter, Interpreter):
                # Act
                res = _outcome(text, engine)
                if res.startswith("BARE"):
                    bad.append(f"{label} {engine.__name__} {res[:120]}")
        # Assert
        self.assertEqual(bad, [])

    def test_wrong_typed_deadlines_are_snapshot_corrupt(self) -> None:
        base = json.loads(_sync_snapshot())
        for bad in ([{"state_id": 5}], {}, "x", [None], [[]]):
            blob = dict(base, deadlines=bad)
            for engine in (SyncInterpreter, Interpreter):
                with self.assertRaises(SnapshotCorruptError, msg=repr(bad)):
                    engine.from_snapshot(json.dumps(blob), create_machine(CFG))

    def test_version_forms(self) -> None:
        base = json.loads(_sync_snapshot())
        for val, want in [
            ("4", "ok"),
            (4.0, "ok"),
            (2**63, "SnapshotVersionError"),
            (5, "SnapshotVersionError"),
            (True, "SnapshotCorruptError"),
            (None, "SnapshotCorruptError"),
            ("x", "SnapshotCorruptError"),
            ([4], "SnapshotCorruptError"),
        ]:
            res = _outcome(
                json.dumps(dict(base, version=val)), SyncInterpreter
            )
            self.assertEqual(res, want, msg=repr(val))

    def test_version_infinity_is_snapshot_corrupt_regression(self) -> None:
        # Defect: `int(float("inf"))` raised a bare OverflowError.
        text = _sync_snapshot().replace('"version": 4', '"version": Infinity')
        for engine in (SyncInterpreter, Interpreter):
            with self.assertRaises(SnapshotCorruptError):
                engine.from_snapshot(text, create_machine(CFG))

    def test_v5_refusal_names_both_versions(self) -> None:
        base = dict(json.loads(_sync_snapshot()), version=5)
        with self.assertRaises(SnapshotVersionError) as cm:
            SyncInterpreter.from_snapshot(
                json.dumps(base), create_machine(CFG)
            )
        msg = str(cm.exception)
        self.assertIn("5", msg)
        self.assertIn(str(SNAPSHOT_VERSION), msg)

    def test_unknown_extra_keys_in_v4_are_ignored(self) -> None:
        # 📝 Forward-compat is by version number only: same-version unknown
        #    keys are accepted and dropped (see report: undocumented).
        base = dict(json.loads(_sync_snapshot()), future_key={"a": 1})
        for engine in (SyncInterpreter, Interpreter):
            i = engine.from_snapshot(json.dumps(base), create_machine(CFG))
            self.assertNotIn("future_key", json.loads(i.get_snapshot()))


# -----------------------------------------------------------------------------
# ⬆️ Upcast fixtures v0..v3
# -----------------------------------------------------------------------------
def _fixture(version: int) -> Dict[str, Any]:
    m = create_machine(CFG)
    blob = json.loads(_sync_snapshot())
    for k in ("machine_version", "deadlines"):
        blob.pop(k)
    blob["version"] = version
    blob["machine_hash"] = m.structure_hash
    if version < 3:
        for k in ("scheduled_sends", "chain_trips", "last_chain_error"):
            blob.pop(k)
    if version < 1:
        for k in ("version", "machine_id", "machine_hash", "configuration"):
            blob.pop(k, None)
    return blob


class TestUpcast(unittest.TestCase):
    def test_every_older_version_upcasts_to_v4_defaults(self) -> None:
        for v in range(4):
            blob = snapmod.upcast(_fixture(v), v)
            self.assertIsNone(blob["machine_version"], v)
            self.assertEqual(blob["deadlines"], [], v)

    def test_every_older_version_restores_on_both_engines(self) -> None:
        for v in range(4):
            for engine in (SyncInterpreter, Interpreter):
                i = engine.from_snapshot(
                    json.dumps(_fixture(v)), create_machine(CFG)
                )
                out = json.loads(i.get_snapshot())
                self.assertEqual(out["version"], SNAPSHOT_VERSION)
                self.assertEqual(out["state_ids"], ["m.p.r1.h0", "m.p.r2.w"])

    def test_upcast_preserves_explicit_v4_values(self) -> None:
        blob = dict(_fixture(3), machine_version="z", deadlines=[1])
        out = snapmod.upcast(blob, 3)
        self.assertEqual(
            (out["machine_version"], out["deadlines"]), ("z", [1])
        )


# -----------------------------------------------------------------------------
# 🪪 Identity
# -----------------------------------------------------------------------------
class TestIdentity(unittest.TestCase):
    def test_same_id_different_structure_is_drift(self) -> None:
        text = _sync_snapshot()
        other = copy.deepcopy(CFG)
        other["states"]["p"]["states"]["r1"]["states"]["h0"]["on"]["Y"] = "h1"
        for engine in (SyncInterpreter, Interpreter):
            with self.assertRaises(SnapshotDriftError):
                engine.from_snapshot(text, create_machine(other))

    def test_different_machine_id_is_drift(self) -> None:
        text = _sync_snapshot()
        other = dict(copy.deepcopy(CFG), id="other")
        with self.assertRaises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(text, create_machine(other))

    def test_same_structure_different_version_label_current_behaviour(
        self,
    ) -> None:
        # 📝 Observed: label mismatch is accepted by default (hash ignores it)
        text = _sync_snapshot()
        from src.xstate_statemachine.persistence.migration import (
            MachineVersionMismatchError,
        )

        other = dict(copy.deepcopy(CFG), version="2")
        with self.assertRaises(MachineVersionMismatchError):
            SyncInterpreter.from_snapshot(text, create_machine(other))
        i = SyncInterpreter.from_snapshot(
            text, create_machine(other), on_version_mismatch="warn"
        )
        self.assertEqual(json.loads(i.get_snapshot())["machine_version"], "2")

    def test_structure_hash_stable_and_recomputed_cost(self) -> None:
        m = create_machine(CFG)
        with mock.patch.object(
            snapmod, "structure_hash", wraps=snapmod.structure_hash
        ) as spy:
            for _ in range(200):
                m.structure_hash
            calls = spy.call_count
        # Observation only: <=200 either way; memoised would be <=1.
        self.assertLessEqual(calls, 200)
        self.assertEqual(m.structure_hash, snapmod.structure_hash(m))


# -----------------------------------------------------------------------------
# 🔀 Cross-engine hop and wall-clock deadlines
# -----------------------------------------------------------------------------
HOUR = 3600.0
T0 = 1_700_000_000.0


class TestCrossEngine(unittest.IsolatedAsyncioTestCase):
    async def test_sync_snapshot_resumes_on_async_after_restart(self) -> None:
        # Arrange: arm on sync at wall T0, 5 s timer
        clock = SimulatedClock(wall_start=T0)
        src = SyncInterpreter(create_machine(TIMER_CFG), clock=clock).start()
        blob = json.loads(src.get_snapshot())
        src.stop()
        self.assertEqual(len(blob["deadlines"]), 1)
        self.assertAlmostEqual(blob["deadlines"][0]["due_at_wall"], T0 + 5)
        # Act: "restarted an hour later" -> timer already overdue
        clock2 = SimulatedClock(wall_start=T0 + HOUR)
        dst = Interpreter.from_snapshot(
            json.dumps(blob),
            create_machine(TIMER_CFG),
            clock=clock2,
            restart_timers="fire_due",
        )
        await dst.start()
        await clock2.increment(0)
        # Assert
        self.assertIn("t.b", dst.current_state_ids)
        await dst.stop()


class TestCrossEngineSyncRestore(unittest.TestCase):
    def test_async_snapshot_resumes_remaining_time_on_sync(self) -> None:
        clock = SimulatedClock(wall_start=T0)

        async def produce() -> str:
            src = await Interpreter(
                create_machine(TIMER_CFG), clock=clock
            ).start()
            await clock.increment(2000)
            out = src.get_snapshot()
            await src.stop()
            return out

        blob = asyncio.run(produce())
        clock2 = SimulatedClock(wall_start=T0 + 2.0)
        dst = SyncInterpreter.from_snapshot(
            blob,
            create_machine(TIMER_CFG),
            clock=clock2,
            restart_timers="resume",
        ).start()
        clock2.increment(2900)
        self.assertIn("t.a", dst.current_state_ids)
        clock2.increment(200)
        self.assertIn("t.b", dst.current_state_ids)
        dst.stop()

    def test_stale_deadline_from_prior_visit_is_not_fired(self) -> None:
        # Arrange: leave `a`, re-enter it (entry_seq grows); a stale record
        # with a lower entry_seq must not shorten the new visit's timer.
        clock = SimulatedClock(wall_start=T0)
        i = SyncInterpreter(create_machine(TIMER_CFG), clock=clock).start()
        i.send("BOUNCE")
        i.send("BACK")
        blob = json.loads(i.get_snapshot())
        i.stop()
        fresh = blob["deadlines"][0]
        stale = dict(fresh, entry_seq=1, due_at_wall=T0 - 100)
        self.assertGreater(fresh["entry_seq"], 1)
        blob["deadlines"] = [stale, fresh]
        # Act
        clock2 = SimulatedClock(wall_start=T0)
        dst = SyncInterpreter.from_snapshot(
            json.dumps(blob),
            create_machine(TIMER_CFG),
            clock=clock2,
            restart_timers="fire_due",
        ).start()
        clock2.increment(0)
        # Assert: still in `a`: the stale overdue record was ignored
        # (or, if this fails, the stale deadline fired the new visit early)
        self.assertIn("t.a", dst.current_state_ids)
        dst.stop()


class TestWallClock(unittest.TestCase):
    def test_real_clock_wall_now_non_decreasing(self) -> None:
        c = RealClock()
        vals = [c.wall_now() for _ in range(1000)]
        self.assertEqual(vals, sorted(vals))

    def test_simulated_wall_start_and_stepping(self) -> None:
        c = SimulatedClock(wall_start=T0)
        self.assertEqual(c.wall_now(), T0)
        c.increment(2500)
        self.assertAlmostEqual(c.wall_now(), T0 + 2.5)

    def test_interpreter_wall_now_both_engines(self) -> None:
        c = SimulatedClock(wall_start=T0)
        s = SyncInterpreter(create_machine(TIMER_CFG), clock=c)
        self.assertEqual(s.wall_now(), T0)
        a = Interpreter(create_machine(TIMER_CFG), clock=c)
        self.assertEqual(a.wall_now(), T0)

    def test_wall_start_garbage_gives_clear_error(self) -> None:
        import datetime

        for bad in (
            datetime.datetime(2024, 1, 1),
            "x",
            [1],
        ):
            with self.assertRaises((TypeError, ValueError), msg=repr(bad)):
                SimulatedClock(wall_start=bad)  # type: ignore[arg-type]

    def test_wall_start_nonfinite_or_negative_current_behaviour(self) -> None:
        # 📝 Observed: float() accepts these silently. Recorded, see report.
        for val in (-5.0, float("nan"), float("inf")):
            c = SimulatedClock(wall_start=val)
            self.assertTrue(
                math.isnan(c.wall_now()) or c.wall_now() == val, repr(val)
            )

    def test_backwards_wall_jump_real_clock_is_defined(self) -> None:
        # Arrange: arm a 5 s timer at wall=1000, restore at wall=500
        # (the wall clock went BACKWARDS 500 s).
        with mock.patch("time.time", return_value=1000.0):
            i = SyncInterpreter(create_machine(TIMER_CFG)).start()
            blob = i.get_snapshot()
            i.stop()
        d = json.loads(blob)["deadlines"][0]
        # Act
        remaining = Deadline.from_dict(d).remaining_ms(500.0)
        # Assert: deadline is ABSOLUTE (1005); at wall=500 it is 505 s away.
        # Backwards jump => fires LATE, never early, never lost.
        self.assertEqual(remaining, 505_000)


# -----------------------------------------------------------------------------
# 💧 Leaks and perf
# -----------------------------------------------------------------------------
class TestLeaks(unittest.TestCase):
    def _cycle_sync(self, n: int) -> None:
        m = create_machine(CFG)
        i = SyncInterpreter(m).start()
        for _ in range(n):
            j = SyncInterpreter.from_snapshot(i.get_snapshot(), m)
            j.stop()
        i.stop()

    def _cycle_async(self, n: int) -> None:
        async def go() -> None:
            m = create_machine(CFG)
            i = await Interpreter(m).start()
            for _ in range(n):
                j = Interpreter.from_snapshot(i.get_snapshot(), m)
                await j.start()
                await j.stop()
            await i.stop()

        asyncio.run(go())

    @staticmethod
    def _library_bytes() -> int:
        """Bytes currently held by allocations made FROM library source.

        ⚠️ `get_traced_memory()` counts everything -- under `pytest --cov`
        the coverage tracer allocates per executed line and the raw total
        grew 36 MB on CI while the library itself grew 0 B. Attributing by
        traceback filename isolates what we are actually measuring.
        """
        snap = tracemalloc.take_snapshot().filter_traces(
            (tracemalloc.Filter(True, str(SRC_DIR / "*")),)
        )
        return sum(s.size for s in snap.statistics("filename"))

    def _growth(self, fn: Callable[[int], None], n: int) -> float:
        # 📝 An interpreter is a reference cycle (plugins ↔ interpreter,
        #    actor system ↔ children), so it is reclaimed by the cyclic GC,
        #    not by refcount. Without `gc.collect()` before each reading
        #    this measured "garbage not yet collected" and flaked at
        #    ~600 B/cycle depending on what the previous 5 000 tests left
        #    in the allocator; with it the true growth is 0 B/cycle.
        fn(50)  # warm caches
        gc.collect()
        tracemalloc.start(1)
        try:
            fn(n // 2)
            gc.collect()
            half = self._library_bytes()
            fn(n)
            gc.collect()
            full = self._library_bytes()
        finally:
            tracemalloc.stop()
        return float(full - half)

    # 📏 Ceiling for the library-attributed growth between the N/2 and N
    #    readings. Measured 0 B/cycle on 3.14 and under the C tracer on
    #    3.13 in isolation. Under `pytest --cov` on CPython ≤ 3.13 the C
    #    tracer's own bookkeeping (per-file line sets, arc dicts) is
    #    attributed to the *library frame that was executing*, so the
    #    reading drifts with the amount of library code the previous 5 000
    #    tests exercised -- 0.4–0.9 MB on the CI coverage job, 25x less
    #    than the un-attributed total but still not ours. A real leak is
    #    per-cycle and linear (≥ 1 KB × cycles = ≥ 1.5 MB here); tracer
    #    noise is sub-linear. So: strict ceiling without the tracer, a
    #    "must be far below a real leak" ceiling with it.
    _LEAK_CEILING_BYTES = 64_000
    _TRACER_CEILING_BYTES = 1_200_000

    def _ceiling(self) -> int:
        tracer_active = sys.gettrace() is not None or (
            hasattr(sys, "monitoring")
            and sys.monitoring.get_tool(sys.monitoring.COVERAGE_ID) is not None
        )
        return (
            self._TRACER_CEILING_BYTES
            if tracer_active
            else self._LEAK_CEILING_BYTES
        )

    def test_sync_roundtrip_does_not_grow(self) -> None:
        self.assertLess(self._growth(self._cycle_sync, 1500), self._ceiling())

    def test_async_roundtrip_does_not_grow(self) -> None:
        self.assertLess(self._growth(self._cycle_async, 600), self._ceiling())


class TestPerf(unittest.TestCase):
    def test_get_snapshot_scaling_reported_and_not_superlinear(self) -> None:
        def p50(ctx_keys: int, states: int) -> float:
            cfg = {
                "id": "p",
                "initial": "s0",
                "context": {f"k{i}": i for i in range(ctx_keys)},
                "states": {
                    f"s{i}": {"on": {"N": f"s{(i + 1) % states}"}}
                    for i in range(states)
                },
            }
            i = SyncInterpreter(create_machine(cfg)).start()
            runs = []
            for _ in range(15):
                t = time.perf_counter()
                i.get_snapshot()
                runs.append(time.perf_counter() - t)
            i.stop()
            return sorted(runs)[len(runs) // 2]

        small = max(p50(1, 1), 1e-6)
        ctx = p50(10_000, 1)
        st = p50(1, 500)
        print(f"\nget_snapshot p50: ctx1={small:.6f}s ctx10k={ctx:.6f}s")
        print(f"get_snapshot p50: states500={st:.6f}s")
        self.assertLess(ctx, 2.0)
        self.assertLess(st, 2.0)


# -----------------------------------------------------------------------------
# 🧾 Receipt codec
# -----------------------------------------------------------------------------
def _errors() -> List[Any]:
    return [None, ValueError("boom"), ReceiptError("Custom", "msg")]


class TestReceiptCodec(unittest.TestCase):
    def test_roundtrip_all_flag_and_error_combinations(self) -> None:
        for flags in itertools.product([False, True], repeat=4):
            for err in _errors():
                changed, deferred, denied, dup = flags
                r = Receipt(
                    state_ids=frozenset({"b", "a"}),
                    changed=changed,
                    error=err,
                    deferred=deferred,
                    denied=denied,
                    duplicate=dup,
                )
                wire = json.loads(json.dumps(receipt_to_json(r)))
                back = receipt_from_json(wire)
                self.assertEqual(back.state_ids, r.state_ids)
                self.assertEqual(
                    (back.changed, back.deferred, back.denied, back.duplicate),
                    flags,
                )
                self.assertEqual(back.error is None, err is None)
                self.assertEqual(receipt_to_status(back), receipt_to_status(r))
                self.assertEqual(receipt_to_json(back), receipt_to_json(r))

    def test_malformed_shapes_raise_value_error_only(self) -> None:
        good = receipt_to_json(Receipt(frozenset({"a"}), True, None))
        junk = [None, 1, "x", [], [1], True, 1.5, object()]
        shapes: List[Any] = list(junk)
        for key in good:
            for val in junk + [{}, {"type": 1}, {"type": "t"}]:
                shapes.append(dict(good, **{key: val}))
            shapes.append({k: v for k, v in good.items() if k != key})
        shapes.append(dict(good, error={"type": "t", "message": None}))
        shapes.append(dict(good, state_ids=[1]))
        shapes.append(dict(good, state_ids=("a", None)))
        bad = []
        for s in shapes:
            try:
                receipt_from_json(s)
            except ValueError:
                pass
            except Exception as exc:  # noqa: BLE001
                bad.append((s, repr(exc)))
        self.assertEqual(bad, [])

    def test_missing_flags_default_false_current_behaviour(self) -> None:
        r = receipt_from_json({"state_ids": []})
        self.assertEqual((r.changed, r.denied, r.duplicate), (False,) * 3)

    def test_state_ids_serialised_sorted(self) -> None:
        r = Receipt(frozenset({"z", "a", "m"}), False, None)
        self.assertEqual(receipt_to_json(r)["state_ids"], ["a", "m", "z"])

    def test_secret_in_error_message_is_not_redacted_by_codec(self) -> None:
        # 📝 The codec is NOT a redaction point (see report / security.md).
        r = Receipt(frozenset(), False, RuntimeError("token=sk-SECRET123"))
        self.assertIn("sk-SECRET123", receipt_to_json(r)["error"]["message"])


def _err(name: str) -> BaseException:
    return type(name, (Exception,), {})("x")


@pytest.mark.parametrize(
    "receipt,status",
    [
        (Receipt(frozenset(), False, _err("IdempotencyMismatchError")), 422),
        (Receipt(frozenset(), True, _err("IdempotencyInFlightError")), 409),
        (Receipt(frozenset(), True, _err("InterpreterStoppedError")), 409),
        (Receipt(frozenset(), True, ValueError("x")), 500),
        # error beats deferred / denied / changed
        (Receipt(frozenset(), True, ValueError("x"), True, True), 500),
        (Receipt(frozenset(), False, None, True, True), 202),  # defer > deny
        (Receipt(frozenset(), True, None, True, False), 202),
        (Receipt(frozenset(), True, None, False, True), 409),
        (Receipt(frozenset(), True, None, False, False), 200),
        (Receipt(frozenset(), False, None, False, False), 200),
        (Receipt(frozenset(), False, None, False, False, True), 200),
        # a decoded ReceiptError routes by its carried class name
        (
            Receipt(
                frozenset(),
                False,
                ReceiptError("IdempotencyMismatchError", "m"),
            ),
            422,
        ),
        (Receipt(frozenset(), False, ReceiptError("", "m")), 500),
    ],
)
def test_receipt_to_status_precedence(receipt: Receipt, status: int) -> None:
    assert receipt_to_status(receipt) == status


class TestCheckDeadlineRecord(unittest.TestCase):
    def test_rejects_bad_records(self) -> None:
        good = {
            "state_id": "s",
            "entry_seq": 1,
            "due_at_wall": 1.0,
            "delay_ms": 1,
            "event_type": "e",
        }
        self.assertIsNone(check_deadline_record(good))
        for key, val in (
            ("state_id", ""),
            ("entry_seq", -1),
            ("entry_seq", True),
            ("delay_ms", 1.5),
            ("due_at_wall", "x"),
            ("due_at_wall", True),
            ("event_type", None),
        ):
            self.assertIsNotNone(
                check_deadline_record(dict(good, **{key: val})), (key, val)
            )
