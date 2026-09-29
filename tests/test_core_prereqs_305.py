# tests/test_core_prereqs_305.py
# -----------------------------------------------------------------------------
# 🧪 #305 A0b core prerequisites, part 1: snapshot layout v4, wall clock,
#    `Deadline`, `MachineNode.version`, receipt codec.
# -----------------------------------------------------------------------------
"""Tests for the #305 part-1 surface, on both engines where an engine is
involved. X0 baseline (#303): receipts never pickle; errors serialise as
{type, message} strings only."""

from __future__ import annotations

import copy
import json
import time
import unittest

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
    InterpreterStoppedError,
    SnapshotCorruptError,
    SnapshotVersionError,
)
from src.xstate_statemachine.persistence import (
    SNAPSHOT_VERSION,
    Deadline,
    check_deadline_record,
    check_shape,
    check_version,
    upcast,
)
from src.xstate_statemachine.receipts import (
    STATUS_ACCEPTED,
    STATUS_CONFLICT,
    STATUS_ERROR,
    STATUS_OK,
    ReceiptError,
)

CFG = {
    "id": "m",
    "version": 7,  # deliberately an int: must coerce to "7"
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"type": "final"}},
}


# -----------------------------------------------------------------------------
# 🏷️ MachineNode.version
# -----------------------------------------------------------------------------
class TestMachineVersion(unittest.TestCase):
    def test_reads_root_version_key_as_str(self) -> None:
        self.assertEqual(create_machine(CFG).version, "7")

    def test_string_version_kept(self) -> None:
        cfg = dict(CFG, version="2024.1-rc")
        self.assertEqual(create_machine(cfg).version, "2024.1-rc")

    def test_none_when_absent(self) -> None:
        cfg = {k: v for k, v in CFG.items() if k != "version"}
        self.assertIsNone(create_machine(cfg).version)

    def test_version_not_part_of_structure_hash(self) -> None:
        # The label is metadata; a re-label must not make old blobs drift.
        a = create_machine(CFG).structure_hash
        b = create_machine(dict(CFG, version="8")).structure_hash
        self.assertEqual(a, b)


# -----------------------------------------------------------------------------
# 📦 Snapshot layout v4
# -----------------------------------------------------------------------------
def _v3_blob() -> dict:
    """A blob exactly as a 0.10.x writer produced it (no v4 keys)."""
    return {
        "version": 3,
        "machine_id": "m",
        "machine_hash": create_machine(CFG).structure_hash,
        "taken_at": 0.0,
        "status": "running",
        "context": {},
        "state_ids": ["m.a"],
        "value": "a",
        "configuration": ["m", "m.a"],
        "output": None,
        "error": None,
        "chain_trips": 0,
        "last_chain_error": None,
        "deferred": [],
        "pending_events": [],
        "scheduled_sends": [],
        "history": {},
        "actors": {},
        "system": {},
    }


class TestSnapshotV4(unittest.TestCase):
    def test_layout_constant_is_4(self) -> None:
        self.assertEqual(SNAPSHOT_VERSION, 4)

    def test_sync_writer_emits_v4_keys(self) -> None:
        i = SyncInterpreter(create_machine(CFG)).start()
        blob = json.loads(i.get_snapshot())
        i.stop()
        self.assertEqual(blob["version"], 4)
        self.assertEqual(blob["machine_version"], "7")
        self.assertEqual(blob["deadlines"], [])

    def test_async_writer_emits_v4_keys(self) -> None:
        async def go() -> dict:
            i = await Interpreter(create_machine(CFG)).start()
            blob = json.loads(i.get_snapshot())
            await i.stop()
            return blob

        import asyncio

        blob = asyncio.run(go())
        self.assertEqual(blob["version"], 4)
        self.assertEqual(blob["machine_version"], "7")
        self.assertEqual(blob["deadlines"], [])

    def test_machine_version_none_when_chart_has_none(self) -> None:
        cfg = {k: v for k, v in CFG.items() if k != "version"}
        i = SyncInterpreter(create_machine(cfg)).start()
        blob = json.loads(i.get_snapshot())
        i.stop()
        self.assertIsNone(blob["machine_version"])

    def test_upcast_v3_adds_defaults(self) -> None:
        blob = upcast(_v3_blob(), 3)
        self.assertIsNone(blob["machine_version"])
        self.assertEqual(blob["deadlines"], [])

    def test_upcast_matrix_v0_to_v4_all_reach_v4_shape(self) -> None:
        for v in range(0, 5):
            blob = _v3_blob()
            if v == 0:
                blob.pop("version")
                blob.pop("machine_hash")
                blob.pop("configuration")
            else:
                blob["version"] = v
            if v == 4:
                blob["machine_version"] = "7"
                blob["deadlines"] = []
            out = upcast(copy.deepcopy(blob), v)
            self.assertIn("machine_version", out, f"v{v}")
            self.assertIn("deadlines", out, f"v{v}")
            self.assertIn("pending_events", out, f"v{v}")

    def test_v3_blob_restores_on_sync_engine(self) -> None:
        i = SyncInterpreter.from_snapshot(
            json.dumps(_v3_blob()), create_machine(CFG)
        ).start()
        self.assertIn("m.a", i.current_state_ids)
        blob = json.loads(i.get_snapshot())
        i.stop()
        # Re-persisted at the current layout, label recovered from the chart.
        self.assertEqual(blob["version"], 4)
        self.assertEqual(blob["machine_version"], "7")

    def test_check_version_refuses_v5(self) -> None:
        with self.assertRaises(SnapshotVersionError):
            check_version(dict(_v3_blob(), version=5))

    def test_check_shape_rejects_non_string_machine_version(self) -> None:
        blob = dict(_v3_blob(), version=4, machine_version=7, deadlines=[])
        with self.assertRaises(SnapshotCorruptError) as cm:
            check_shape(blob, version=4)
        self.assertIn("machine_version", str(cm.exception))

    def test_check_shape_rejects_bad_deadlines(self) -> None:
        for bad in ({}, [1], [{"state_id": "x"}]):
            blob = dict(
                _v3_blob(), version=4, machine_version=None, deadlines=bad
            )
            with self.assertRaises(SnapshotCorruptError, msg=repr(bad)):
                check_shape(blob, version=4)

    def test_check_shape_accepts_valid_deadline(self) -> None:
        d = Deadline("m.a", 1, 1.0e9, 5000, "after.5000.m.a")
        blob = dict(
            _v3_blob(), version=4, machine_version="7", deadlines=[d.to_dict()]
        )
        check_shape(blob, version=4)  # no raise


# -----------------------------------------------------------------------------
# ⏰ Deadline + wall clock
# -----------------------------------------------------------------------------
class TestDeadline(unittest.TestCase):
    def test_round_trip(self) -> None:
        d = Deadline("m.a", 3, 1700000000.5, 30000, "after.30000.m.a")
        rec = d.to_dict()
        self.assertIsNone(check_deadline_record(rec))
        self.assertEqual(Deadline.from_dict(json.loads(json.dumps(rec))), d)

    def test_remaining_ms_clamps_at_zero(self) -> None:
        d = Deadline("m.a", 0, 100.0, 1000, "after.1000.m.a")
        self.assertEqual(d.remaining_ms(99.0), 1000)
        self.assertEqual(d.remaining_ms(200.0), 0)

    def test_validator_messages(self) -> None:
        self.assertIn("object", check_deadline_record([]) or "")
        base = Deadline("m.a", 1, 1.0, 1, "e").to_dict()
        self.assertIn(
            "state_id", check_deadline_record(dict(base, state_id=""))
        )
        self.assertIn(
            "entry_seq", check_deadline_record(dict(base, entry_seq=True))
        )
        self.assertIn(
            "entry_seq", check_deadline_record(dict(base, entry_seq=-1))
        )
        self.assertIn(
            "due_at_wall", check_deadline_record(dict(base, due_at_wall="x"))
        )
        self.assertIn(
            "event_type", check_deadline_record(dict(base, event_type=""))
        )
        missing = dict(base)
        del missing["delay_ms"]
        self.assertIn("delay_ms", check_deadline_record(missing))


class TestWallNow(unittest.TestCase):
    def test_real_clock_wall_now_is_epoch(self) -> None:
        before = time.time()
        self.assertGreaterEqual(RealClock().wall_now(), before - 1)

    def test_simulated_clock_wall_start_and_increment(self) -> None:
        clk = SimulatedClock(wall_start=1_000_000.0)
        self.assertEqual(clk.wall_now(), 1_000_000.0)
        clk.increment(3_600_000)  # "restarted an hour later"
        self.assertEqual(clk.wall_now(), 1_003_600.0)
        self.assertEqual(clk.now(), 3600.0)  # monotonic origin still 0

    def test_simulated_clock_defaults_wall_start_to_real_time(self) -> None:
        before = time.time()
        self.assertGreaterEqual(SimulatedClock().wall_now(), before - 1)

    def test_sync_engine_wall_now_delegates_to_clock(self) -> None:
        clk = SimulatedClock(wall_start=42.0)
        i = SyncInterpreter(create_machine(CFG), clock=clk).start()
        self.assertEqual(i.wall_now(), 42.0)
        i.stop()

    def test_async_engine_wall_now_delegates_to_clock(self) -> None:
        import asyncio

        async def go() -> float:
            clk = SimulatedClock(wall_start=42.0)
            i = await Interpreter(create_machine(CFG), clock=clk).start()
            try:
                return i.wall_now()
            finally:
                await i.stop()

        self.assertEqual(asyncio.run(go()), 42.0)

    def test_clock_without_wall_now_falls_back_to_time(self) -> None:
        class Legacy:  # 0.8.0-era Clock: no wall_now
            def now(self) -> float:
                return 0.0

            def set_timeout(self, fn, delay_sec, *, owner=None):  # noqa
                return None

            def clear_timeout(self, handle) -> None:  # noqa
                pass

            def pump(self) -> int:
                return 0

        before = time.time()
        i = SyncInterpreter(create_machine(CFG), clock=Legacy())
        self.assertGreaterEqual(i.wall_now(), before - 1)


# -----------------------------------------------------------------------------
# 🧾 Receipt codec
# -----------------------------------------------------------------------------
class TestReceiptCodec(unittest.TestCase):
    def test_status_mapping_table(self) -> None:
        ids = frozenset({"m.a"})
        cases = [
            (Receipt(ids, True), STATUS_OK),
            (Receipt(ids, False), STATUS_OK),  # clean no-op
            (Receipt(ids, False, denied=True), STATUS_CONFLICT),
            (Receipt(ids, False, deferred=True), STATUS_ACCEPTED),
            (Receipt(ids, False, error=RuntimeError("x")), STATUS_ERROR),
            # 🏁 finished / stopped instance: refused like a guard, not 500
            (
                Receipt(ids, False, error=InterpreterStoppedError("done")),
                STATUS_CONFLICT,
            ),
            # precedence: error beats deferred/denied; duplicate is neutral
            (
                Receipt(ids, False, error=RuntimeError("x"), deferred=True),
                STATUS_ERROR,
            ),
            (Receipt(ids, False, deferred=True, denied=True), STATUS_ACCEPTED),
            (Receipt(ids, True, duplicate=True), STATUS_OK),
            (
                Receipt(ids, False, denied=True, duplicate=True),
                STATUS_CONFLICT,
            ),
        ]
        for receipt, expected in cases:
            self.assertEqual(receipt_to_status(receipt), expected, receipt)

    def test_round_trip_without_error(self) -> None:
        r = Receipt(frozenset({"m.b", "m.a"}), True, denied=False)
        data = json.loads(json.dumps(receipt_to_json(r)))
        self.assertEqual(data["state_ids"], ["m.a", "m.b"])  # sorted
        self.assertEqual(receipt_from_json(data), r)

    def test_round_trip_with_error_keeps_type_and_message_only(self) -> None:
        class BoomError(ValueError):
            pass

        r = Receipt(frozenset({"m.a"}), False, error=BoomError("secret? no"))
        data = receipt_to_json(r)
        self.assertEqual(
            data["error"], {"type": "BoomError", "message": "secret? no"}
        )
        back = receipt_from_json(json.loads(json.dumps(data)))
        self.assertIsInstance(back.error, ReceiptError)
        self.assertEqual(back.error.type, "BoomError")
        self.assertEqual(str(back.error), "secret? no")
        self.assertEqual(receipt_to_status(back), STATUS_ERROR)
        # A second encode is stable (ReceiptError re-encodes to the same).
        self.assertEqual(receipt_to_json(back), data)

    def test_all_flags_round_trip(self) -> None:
        r = Receipt(
            frozenset(), False, deferred=True, denied=True, duplicate=True
        )
        self.assertEqual(receipt_from_json(receipt_to_json(r)), r)

    def test_from_json_rejects_malformed(self) -> None:
        good = receipt_to_json(Receipt(frozenset({"m.a"}), True))
        bad_cases = [
            [],
            dict(good, state_ids="m.a"),
            dict(good, state_ids=[1]),
            dict(good, error="boom"),
            dict(good, error={"type": "X"}),
            dict(good, changed="yes"),
            dict(good, duplicate=1),
        ]
        for bad in bad_cases:
            with self.assertRaises(ValueError, msg=repr(bad)):
                receipt_from_json(bad)

    def test_live_receipt_from_engine_encodes(self) -> None:
        i = SyncInterpreter(create_machine(CFG)).start()
        r = i.send("GO", wait=True)
        i.stop()
        data = receipt_to_json(r)
        self.assertEqual(data["state_ids"], ["m.b"])
        self.assertTrue(data["changed"])
        self.assertEqual(receipt_to_status(r), STATUS_OK)


if __name__ == "__main__":
    unittest.main()
