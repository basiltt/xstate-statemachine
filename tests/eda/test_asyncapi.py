# tests/eda/test_asyncapi.py
"""#293/#295: `asyncapi_document()` validates against the VENDORED AsyncAPI
3.0.0 JSON Schema, offline; consumed and published events are listed."""

from __future__ import annotations

import unittest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.eda import (
    ASYNCAPI_VERSION,
    asyncapi_document,
    consumed_events,
    load_asyncapi_schema,
    validate_asyncapi,
)

try:
    import jsonschema  # noqa: F401

    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover - env dependent
    HAVE_JSONSCHEMA = False

CFG = {
    "id": "order",
    "version": "2.1",
    "initial": "open",
    "states": {
        "open": {
            "on": {
                "PAY": {
                    "target": "paid",
                    "meta": {
                        "publish": {"type": "order.paid", "data": ["total"]}
                    },
                },
                "CANCEL": "cancelled",
                "*": "open",
            }
        },
        "paid": {"tags": ["publish"]},
        "cancelled": {"type": "final"},
    },
}


class TestSchemaIsVendored(unittest.TestCase):
    def test_offline_schema(self) -> None:
        schema = load_asyncapi_schema()
        self.assertEqual(
            schema["$id"],
            "http://asyncapi.com/definitions/3.0.0/asyncapi.json",
        )
        self.assertEqual(ASYNCAPI_VERSION, "3.0.0")


class TestDocument(unittest.TestCase):
    def test_content(self) -> None:
        doc = asyncapi_document(
            create_machine(CFG),
            server={"host": "localhost:9092", "protocol": "kafka"},
            inbound_topic="orders.commands",
        )
        self.assertEqual(doc["asyncapi"], "3.0.0")
        self.assertEqual(doc["info"]["version"], "2.1")
        self.assertEqual(
            doc["channels"]["inbound"]["address"], "orders.commands"
        )
        names = {m["name"] for m in doc["components"]["messages"].values()}
        self.assertEqual(
            names,
            {
                "xsm.order.PAY",
                "xsm.order.CANCEL",
                "order.paid",
                "xsm.order.transition.paid",
            },
        )
        self.assertEqual(doc["servers"]["default"]["protocol"], "kafka")
        self.assertEqual(
            consumed_events(create_machine(CFG)), ["CANCEL", "PAY"]
        )

    def test_no_channels_for_a_silent_machine(self) -> None:
        doc = asyncapi_document(
            create_machine({"id": "q", "initial": "a", "states": {"a": {}}})
        )
        self.assertEqual(doc["channels"], {})
        self.assertEqual(doc["info"]["version"], "0.0.0")

    @unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
    def test_validates_against_the_vendored_schema(self) -> None:
        for machine in (create_machine(CFG),):
            with self.subTest(machine=machine.id):
                validate_asyncapi(
                    asyncapi_document(
                        machine, server={"host": "h", "protocol": "amqp"}
                    )
                )

    @unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
    def test_an_invalid_document_is_rejected(self) -> None:
        import jsonschema as js

        doc = asyncapi_document(create_machine(CFG))
        doc["asyncapi"] = "9.9.9"
        with self.assertRaises(js.ValidationError):
            validate_asyncapi(doc)


if __name__ == "__main__":
    unittest.main()
