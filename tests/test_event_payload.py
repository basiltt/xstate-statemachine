import pytest
from xstate_statemachine.events import Event


def test_event_default_payload_is_isolated():
    first = Event(type="A")
    second = Event(type="B")
    first.payload["x"] = 1
    assert "x" not in second.payload
