# tests/contrib/cloudevents/test_cloudevents.py
"""#293 `[cloudevents]`: `Envelope` round-trips the official SDK objects and
both HTTP modes (binary + structured); credentials in headers never become
extensions (X0.8); bodies are size-capped before parsing (X0.4)."""

from __future__ import annotations

import unittest

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("cloudevents")
pytest.importorskip("cloudevents")

from src.xstate_statemachine.contrib.cloudevents import (  # noqa: E402
    from_cloudevent,
    from_http,
    to_binary,
    to_cloudevent,
    to_structured,
)
from src.xstate_statemachine.eda import (  # noqa: E402
    Envelope,
    EnvelopeCorruptError,
    EnvelopeTooLargeError,
)

TP = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"


def _env() -> Envelope:
    return Envelope.new(
        type="order.paid",
        subject="o-1",
        source="xsm/order",
        data={"total": 5, "items": ["a"]},
        correlationid="c-1",
        causationid="x-1",
        machineid="order",
        machineversion="2",
        extensions={"traceparent": TP, "tenant": "acme"},
    )


class TestSDK(unittest.TestCase):
    def test_sdk_round_trip(self) -> None:
        e = _env()
        ce = to_cloudevent(e)
        self.assertEqual(ce["type"], "order.paid")
        self.assertEqual(ce["correlationid"], "c-1")
        self.assertEqual(from_cloudevent(ce), e)

    def test_http_binary_mode(self) -> None:
        e = _env()
        headers, body = to_binary(e)
        self.assertEqual(headers["ce-type"], "order.paid")
        self.assertEqual(headers["ce-subject"], "o-1")
        self.assertEqual(headers["ce-causationid"], "x-1")
        self.assertEqual(from_http(headers, body), e)

    def test_http_structured_mode(self) -> None:
        e = _env()
        headers, body = to_structured(e)
        self.assertIn("cloudevents+json", headers["content-type"])
        self.assertEqual(from_http(headers, body.decode("utf-8")), e)
        self.assertEqual(Envelope.from_json(body), e)  # same wire format

    def test_no_credentials_from_headers(self) -> None:
        headers, body = to_binary(_env())
        headers.update(
            {
                "Authorization": "Bearer x",
                "Cookie": "s=1",
                "ce-authorization": "Bearer y",
                "ce-apikey": "k",
                "X-Other": "ignored",
            }
        )
        e = from_http(headers, body)
        self.assertEqual(set(e.extensions), {"traceparent", "tenant"})

    def test_size_cap_and_garbage(self) -> None:
        headers, body = to_structured(
            Envelope.new(type="t", data={"b": "x" * 5000})
        )
        with self.assertRaises(EnvelopeTooLargeError):
            from_http(headers, body, max_bytes=1000)
        with self.assertRaises(EnvelopeCorruptError):
            from_http({"content-type": "application/json"}, b"{nope")

    def test_bad_traceparent_is_rejected(self) -> None:
        headers, body = to_binary(Envelope.new(type="t", data={}))
        headers["ce-traceparent"] = "garbage"
        with self.assertRaises(EnvelopeCorruptError):
            from_http(headers, body)


if __name__ == "__main__":
    unittest.main()
