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


# --------------------------------------------------------------------------
# Send paths, pending snapshot, strict, mixed schemas (round 2)
# --------------------------------------------------------------------------
import asyncio  # noqa: E402
import time  # noqa: E402
from decimal import Decimal  # noqa: E402

from xstate_statemachine import Interpreter, MachineLogic  # noqa: E402
from xstate_statemachine.actor_logic import from_callback  # noqa: E402
from xstate_statemachine.contrib.pydantic import models_of  # noqa: E402
from xstate_statemachine.exceptions import (  # noqa: E402
    SnapshotSerializationError,
    UnknownEventError,
)


class Amount(EventModel):
    type: Literal["AMT"] = "AMT"
    amount: Decimal


def _recording_machine(seen):
    def rec(i, c, e, a):
        seen.append(e.payload["amount"])

    cfg = {
        "id": "r",
        "initial": "a",
        "states": {"a": {"on": {"AMT": {"actions": "rec"}}}},
    }
    return create_machine(
        cfg,
        logic=MachineLogic(actions={"rec": rec}),
        event_schemas=events_union(Amount),
    )


def test_model_on_every_sync_send_path_keeps_decimal():
    seen = []
    i = SyncInterpreter(_recording_machine(seen)).start()
    i.send(Amount(amount=Decimal("1.1")))
    i.send_events([Amount(amount=Decimal("2"))])
    i.send_threadsafe(Amount(amount=Decimal("3")))
    i.send(Amount(amount=Decimal("4")))  # drains the mailbox first
    assert seen == [Decimal("1.1"), Decimal(2), Decimal(3), Decimal(4)]
    assert all(isinstance(v, Decimal) for v in seen)


def test_model_on_async_send_paths_keeps_decimal():
    seen = []

    async def run():
        i = Interpreter(_recording_machine(seen))
        await i.start()
        await i.send_priority(Amount(amount=Decimal("1")))
        await i.send_events([Amount(amount=Decimal("2"))])
        i.send_threadsafe(Amount(amount=Decimal("3")))
        await asyncio.sleep(0.05)
        await i.stop()

    asyncio.run(run())
    assert sorted(seen) == [Decimal(1), Decimal(2), Decimal(3)]


def test_from_callback_send_back_accepts_a_model():
    seen = []

    def rec(i, c, e, a):
        seen.append(e.payload["amount"])

    def setup(send_back, receive, ctx, ev):
        send_back(Amount(amount=Decimal("5")))

    cfg = {
        "id": "c",
        "initial": "a",
        "states": {
            "a": {"invoke": {"src": "cb"}, "on": {"AMT": {"actions": "rec"}}}
        },
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            actions={"rec": rec}, services={"cb": from_callback(setup)}
        ),
        event_schemas=events_union(Amount),
    )
    i = SyncInterpreter(m).start()
    deadline = time.monotonic() + 2
    while not seen and time.monotonic() < deadline:
        time.sleep(0.01)
        i.tick()  # sync engine: send_back lands in the mailbox
    i.stop()
    assert seen == [Decimal("5")]


def test_pending_model_event_with_decimal_refuses_snapshot_loudly():
    """A PENDING event's Decimal is not coerced to str: the snapshot is
    refused (`SnapshotSerializationError`), never a silent type change."""

    async def run():
        i = Interpreter(_recording_machine([]))
        await i.start()
        i.send(Amount(amount=Decimal("5.10")))  # queued, not yet run
        try:
            with pytest.raises(SnapshotSerializationError):
                i.get_snapshot()
        finally:
            await i.stop()

    asyncio.run(run())


def test_strict_unknown_type_and_plain_callable_mixed_in():
    calls = []
    mixed = dict(events_union(Amount))
    mixed["X"] = calls.append
    cfg = {
        "id": "s",
        "initial": "a",
        "strict": True,
        "states": {"a": {"on": {"AMT": "a", "X": "a"}}},
    }
    i = SyncInterpreter(create_machine(cfg, event_schemas=mixed)).start()
    i.send("X", foo=1)
    assert calls and calls[0]["foo"] == 1
    with pytest.raises(UnknownEventError):
        i.send("NOPE")
    assert models_of(mixed) == (Amount,)
