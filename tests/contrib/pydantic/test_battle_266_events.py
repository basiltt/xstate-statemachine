# tests/contrib/pydantic/test_battle_266_events.py
"""#266 battle (agent A): typed events -- no payload values in errors."""

import pytest

pydantic = pytest.importorskip("pydantic")

from typing import Literal  # noqa: E402

from xstate_statemachine import SyncInterpreter, create_machine  # noqa: E402
from xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)
from xstate_statemachine.exceptions import (  # noqa: E402
    InvalidEventPayloadError,
)

CARD = 4111111111111111


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    card: str


def _interp():
    cfg = {"id": "n", "initial": "a", "states": {"a": {"on": {"PAY": "a"}}}}
    m = create_machine(cfg, event_schemas=events_union(Pay))
    return SyncInterpreter(m).start()


def test_invalid_payload_error_does_not_echo_the_value():
    i = _interp()
    with pytest.raises(InvalidEventPayloadError) as ei:
        i.send("PAY", card=CARD)
    exc = ei.value
    assert str(CARD) not in str(exc)
    assert isinstance(exc.cause, pydantic.ValidationError)
    errs = exc.cause.errors()
    assert errs[0]["loc"] == ("card",)
    assert str(CARD) not in repr(errs)
    assert exc.cause.__cause__ is None


def test_two_value_literal_type_is_refused():
    class Two(EventModel):
        type: Literal["A", "B"]

    with pytest.raises(TypeError):
        events_union(Two)


def test_empty_union_is_empty_mapping():
    assert events_union() == {}
