# tests/test_event_payload.py
# -----------------------------------------------------------------------------
# 📦 events.py -- the value objects every engine passes around
# -----------------------------------------------------------------------------
"""Unit tests for `Event`, `AfterEvent` and `Receipt` (events.py)."""

import pytest

from src.xstate_statemachine.events import AfterEvent, Event, Receipt


def test_event_default_payload_is_isolated():
    first = Event(type="A")
    second = Event(type="B")
    first.payload["x"] = 1
    assert "x" not in second.payload


def test_event_data_is_an_alias_for_payload():
    """`data` predates `payload` and is still what most examples read."""
    e = Event(type="LOGIN", payload={"user": "alice"})
    assert e.data is e.payload
    assert e.data["user"] == "alice"


def test_event_data_rejects_non_dict_payload():
    """A payload that is not a dict is a caller bug; say so, don't
    return something `.get()` will blow up on later."""
    e = Event(type="X", payload=["not", "a", "dict"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Expected payload to be a dict"):
        _ = e.data


def test_after_event_lateness_is_fired_minus_scheduled_in_ms():
    e = AfterEvent(type="after.10.m.a", scheduled_for=1.000, fired_at=1.035)
    assert e.lateness_ms == pytest.approx(35.0)


def test_after_event_lateness_never_negative():
    """A timer cannot fire early; clock jitter must not produce -0.3 ms."""
    e = AfterEvent(type="after.10.m.a", scheduled_for=2.0, fired_at=1.9)
    assert e.lateness_ms == 0.0


def test_after_event_defaults_to_zero_lateness():
    # #118: unknown telemetry is None, never an affirmative 0.0
    assert AfterEvent(type="after.5.m.a").lateness_ms is None
    assert (
        AfterEvent(
            type="after.5.m.a", scheduled_for=1.0, fired_at=1.0
        ).lateness_ms
        == 0.0
    )


def test_receipt_is_a_plain_value_object():
    r = Receipt(frozenset({"m.a"}), False, None)
    assert r.state_ids == frozenset({"m.a"})
    assert r.changed is False
    assert r.error is None
