# tests/eda/test_envelope.py
"""#272/#293: the CloudEvents-shaped `Envelope` -- ids, JSON round trip,
validation before `to_event()`, size caps (X0.4), no credentials in
extensions and a validated `traceparent` (X0.8)."""

from __future__ import annotations

import json
import re
import unittest

from src.xstate_statemachine import SyncInterpreter, create_machine
from src.xstate_statemachine.eda import (
    ATTEMPT_EXTENSION,
    Envelope,
    EnvelopeCorruptError,
    EnvelopeTooLargeError,
    default_event_name,
    new_id,
)
from src.xstate_statemachine.exceptions import XStateMachineError

TP = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestIds(unittest.TestCase):
    def test_uuid7_layout_and_sortable(self) -> None:
        ids = [new_id() for _ in range(2000)]
        self.assertTrue(all(UUID.match(i) for i in ids))
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))

    def test_time_prefix_orders_across_milliseconds(self) -> None:
        self.assertLess(new_id(now_ms=10**12), new_id(now_ms=10**12 + 1))

    def test_same_millisecond_is_still_increasing(self) -> None:
        a = new_id(now_ms=2 * 10**12)
        b = new_id(now_ms=2 * 10**12)
        self.assertLess(a, b)


class TestRoundTrip(unittest.TestCase):
    def test_json_round_trip(self) -> None:
        e = Envelope.new(
            type="xsm.order.PAY",
            subject="o-1",
            data={"amount": 5},
            correlationid="c",
            causationid="x",
            machineid="order",
            machineversion="2",
            extensions={"traceparent": TP, "tenant": "acme"},
        )
        back = Envelope.from_json(e.to_json())
        self.assertEqual(back, e)
        raw = json.loads(e.to_json())
        self.assertEqual(raw["specversion"], "1.0")
        self.assertEqual(raw["tenant"], "acme")  # extensions are top-level
        self.assertNotIn("extensions", raw)

    def test_bytes_input(self) -> None:
        e = Envelope.new(type="t", subject="s")
        self.assertEqual(Envelope.from_json(e.to_json().encode()), e)

    def test_to_event(self) -> None:
        ev = Envelope.new(type="xsm.order.PAY", data={"a": 1}).to_event()
        self.assertEqual((ev.type, ev.payload), ("PAY", {"a": 1}))
        self.assertEqual(
            Envelope.new(type="order.paid").to_event("PAID").type, "PAID"
        )

    def test_default_event_name(self) -> None:
        self.assertEqual(default_event_name("xsm.m.GO"), "GO")
        self.assertEqual(default_event_name("xsm.m.a.b"), "a.b")
        self.assertEqual(default_event_name("order.paid"), "order.paid")
        self.assertEqual(default_event_name("xsm.m"), "xsm.m")

    def test_from_transition_causation_and_correlation(self) -> None:
        m = create_machine(
            {
                "id": "order",
                "version": "3",
                "initial": "a",
                "states": {"a": {}},
            }
        )
        i = SyncInterpreter(m).start()
        cause = Envelope.new(
            type="xsm.order.GO",
            subject="o-9",
            correlationid="corr",
            extensions={"traceparent": TP},
        )
        out = Envelope.from_transition(i, type="order.moved", cause=cause)
        self.assertEqual(out.causationid, cause.id)
        self.assertEqual(out.correlationid, "corr")
        self.assertEqual(out.subject, "o-9")
        self.assertEqual(out.machineid, "order")
        self.assertEqual(out.machineversion, "3")
        self.assertEqual(out.source, "xsm/order")
        self.assertEqual(out.extensions["traceparent"], TP)
        root = Envelope.from_transition(i, type="t")
        self.assertIsNone(root.causationid)
        self.assertEqual(root.correlationid, root.id)
        self.assertEqual(root.subject, i.id)
        # correlation falls back to the cause's id
        c2 = Envelope.new(type="t", subject="s")
        self.assertEqual(
            Envelope.from_transition(i, type="t", cause=c2).correlationid,
            c2.id,
        )
        i.stop()


class TestValidation(unittest.TestCase):
    def test_is_an_xstate_error(self) -> None:
        self.assertTrue(issubclass(EnvelopeCorruptError, XStateMachineError))

    def test_missing_required(self) -> None:
        for raw in (
            {"id": "1", "type": "t", "specversion": "1.0"},
            {"id": "1", "source": "s", "specversion": "1.0"},
            {"type": "t", "source": "s", "specversion": "1.0"},
            {"id": "1", "type": "t", "source": "s"},
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.from_dict(raw)

    def test_wrong_shapes(self) -> None:
        bad = [
            "not json",
            "[1, 2]",
            json.dumps(
                {"id": 1, "type": "t", "source": "s", "specversion": "1.0"}
            ),
            json.dumps(
                {"id": "1", "type": "t", "source": "s", "specversion": "0.3"}
            ),
            json.dumps(
                {"id": "1", "type": "", "source": "s", "specversion": "1.0"}
            ),
            json.dumps(
                {
                    "id": "1",
                    "type": "t",
                    "source": "s",
                    "specversion": "1.0",
                    "BadName": 1,
                }
            ),
            json.dumps(
                {
                    "id": "1",
                    "type": "t",
                    "source": "s",
                    "specversion": "1.0",
                    "x": {"a": 1},
                }
            ),
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.from_json(text)
        with self.assertRaises(EnvelopeCorruptError):
            Envelope.from_json(42)  # type: ignore[arg-type]
        with self.assertRaises(EnvelopeCorruptError):
            Envelope(type="t", source="s", subject="x" * 2000)

    def test_data_must_be_an_object_to_become_an_event(self) -> None:
        with self.assertRaises(EnvelopeCorruptError):
            Envelope.new(type="t", data=[1, 2]).to_event()
        self.assertEqual(Envelope.new(type="t").to_event().payload, {})

    def test_size_cap_checked_before_parsing(self) -> None:
        e = Envelope.new(type="t", data={"blob": "x" * 5000})
        with self.assertRaises(EnvelopeTooLargeError):
            Envelope.from_json(e.to_json(), max_bytes=1000)
        with self.assertRaises(EnvelopeTooLargeError):
            Envelope.from_json(b"{" * 2000, max_bytes=1000)  # never parsed
        with self.assertRaises(EnvelopeTooLargeError):
            e.to_json(max_bytes=1000)

    def test_no_credentials_in_extensions(self) -> None:
        for name in ("authorization", "cookie", "xapikey", "authtoken"):
            with self.subTest(name=name):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.new(type="t", extensions={name: "secret"})
        safe = Envelope.safe_extensions(
            {"Authorization": "a", "set-cookie": "b", "tenant": "t"}
        )
        self.assertEqual(safe, {"tenant": "t"})

    def test_reserved_names_are_not_extensions(self) -> None:
        with self.assertRaises(EnvelopeCorruptError):
            Envelope.new(type="t", extensions={"subject": "x"})

    def test_traceparent_validated(self) -> None:
        Envelope.new(type="t", extensions={"traceparent": TP})
        for bad in (
            "garbage",
            "00-" + "0" * 32 + "-b7ad6b7169203331-01",
            "ff-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            TP.upper(),
        ):
            with self.subTest(tp=bad):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.new(type="t", extensions={"traceparent": bad})

    def test_attempt_counter(self) -> None:
        e = Envelope.new(type="t")
        self.assertEqual(e.attempt, 0)
        e2 = e.with_attempt(3)
        self.assertEqual((e2.attempt, e2.id), (3, e.id))
        self.assertEqual(e.attempt, 0)  # immutable
        for bad in (-1, "2", True):
            with self.subTest(bad=bad):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.new(type="t", extensions={ATTEMPT_EXTENSION: bad})

    def test_replace_returns_a_copy(self) -> None:
        e = Envelope.new(type="t", subject="a")
        self.assertEqual(e.replace(subject="b").subject, "b")
        self.assertEqual(e.subject, "a")


if __name__ == "__main__":
    unittest.main()
