# tests/contrib/pydantic/test_battle_266_context.py
"""#266 battle (agent A): typed context -- write-back shape, secrets."""

import asyncio
import io
import json
import logging
from decimal import Decimal
from typing import List

import pytest

pydantic = pytest.importorskip("pydantic")

from pydantic import BaseModel  # noqa: E402

from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.contrib.pydantic import (  # noqa: E402
    ContextValidationError,
    PydanticCodec,
    context_model,
)

SECRET = "12345678901234"


class Item(BaseModel):
    sku: str
    qty: int


class Ctx(BaseModel):
    items: List[Item] = []
    total: Decimal = Decimal(0)
    card_token: str = "tok"


def _add(i, c, e, a):
    c["items"].append({"sku": "a", "qty": "2"})
    c["total"] = "1.5"


def _bad(i, c, e, a):
    c["total"] = "9"
    c["card_token"] = int(SECRET)


def _machine():
    cfg = {
        "id": "m",
        "initial": "a",
        "context": {"items": [], "total": "0", "card_token": "tok"},
        "actionErrorPolicy": "rollback",
        "states": {
            "a": {"on": {"ADD": {"actions": "add"}, "BAD": {"actions": "bad"}}}
        },
    }
    return create_machine(
        cfg,
        logic=MachineLogic(actions={"add": _add, "bad": _bad}),
        context_validator=context_model(Ctx),
    )


@pytest.fixture
def log_buf():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    root = logging.getLogger()
    root.addHandler(h)
    yield buf
    root.removeHandler(h)


def test_write_back_stores_plain_dicts_for_nested_models():
    i = SyncInterpreter(_machine()).start()
    i.send("ADD")
    assert i.context["items"] == [{"sku": "a", "qty": 2}]
    assert i.context["total"] == Decimal("1.5")
    snap = json.loads(i.get_snapshot())["context"]
    # Was ["sku='a' qty=2"] -- the model repr via default=str.
    assert snap["items"] == [{"sku": "a", "qty": 2}]
    enc = json.loads(PydanticCodec(Ctx).encode(i.get_snapshot()))
    assert enc["context"]["items"] == [{"sku": "a", "qty": 2}]


def test_rollback_restores_coerced_values_sync(log_buf):
    i = SyncInterpreter(_machine()).start()
    i.send("ADD")
    i.send("BAD")
    assert i.status == "running"
    assert i.context["total"] == Decimal("1.5")
    assert i.context["card_token"] == "tok"
    assert SECRET not in log_buf.getvalue()


def test_rollback_and_no_leak_async(log_buf):
    async def run():
        i = Interpreter(_machine())
        await i.start()
        await i.send("ADD")
        await i.send("BAD")
        await asyncio.sleep(0.05)
        try:
            return dict(i.context), i.status
        finally:
            await i.stop()

    ctx, status = asyncio.run(run())
    assert status == "running"
    assert ctx["total"] == Decimal("1.5")
    assert ctx["items"] == [{"sku": "a", "qty": 2}]
    assert SECRET not in log_buf.getvalue()


def test_context_validation_error_carries_no_input_value():
    validate = context_model(Ctx)
    with pytest.raises(ContextValidationError) as ei:
        validate({"card_token": int(SECRET)})
    exc = ei.value
    assert SECRET not in str(exc)
    assert SECRET not in str(exc.cause)
    assert SECRET not in repr(exc.errors)
    assert exc.errors[0]["loc"] == ("card_token",)
    assert exc.__cause__ is None and exc.__suppress_context__


def test_scrub_keeps_custom_validator_errors_value_free():
    from pydantic import field_validator

    class V(BaseModel):
        pin: str

        @field_validator("pin")
        @classmethod
        def _c(cls, v):
            raise ValueError("bad pin")

    with pytest.raises(ContextValidationError) as ei:
        context_model(V)({"pin": SECRET})
    assert SECRET not in str(ei.value)
    assert ei.value.errors[0]["loc"] == ("pin",)


# --------------------------------------------------------------------------
# PydanticCodec round trips, warning, threads; persisted() refusal; leaks
# --------------------------------------------------------------------------
import datetime  # noqa: E402
import enum  # noqa: E402
import gc  # noqa: E402
import threading  # noqa: E402
import tracemalloc  # noqa: E402

from pydantic import ConfigDict  # noqa: E402

from xstate_statemachine.contrib.pydantic import (  # noqa: E402
    TypedContextPlugin,
)
from xstate_statemachine.persistence import MemoryStore  # noqa: E402
from xstate_statemachine.persistence.locking import (  # noqa: E402
    apersisted,
    persisted,
)

_TZ = datetime.timezone(datetime.timedelta(hours=5))


class Color(enum.Enum):
    R = "r"


class Rich(BaseModel):
    at: datetime.datetime
    naive: datetime.datetime
    total: Decimal = Decimal("1.10")


class Enumy(BaseModel):
    c: Color = Color.R


class EnumyValues(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    c: Color = Color.R


def _plain():
    cfg = {"id": "p", "initial": "a", "context": {}, "states": {"a": {}}}
    return create_machine(cfg)


def _snapshot_with(ctx):
    i = SyncInterpreter(_plain()).start()
    i.context.update(ctx)
    try:
        return i.get_snapshot()
    finally:
        i.stop()


def test_codec_round_trips_decimal_and_aware_and_naive_datetime():
    ctx = Rich(
        at=datetime.datetime(2026, 1, 1, tzinfo=_TZ),
        naive=datetime.datetime(2026, 1, 1),
    ).model_dump(mode="python")
    blob = PydanticCodec(Rich).encode(_snapshot_with(ctx))
    i = SyncInterpreter.from_snapshot(blob, _plain())
    i.use(TypedContextPlugin(Rich)).start()
    assert i.status == "running"
    assert i.context["at"] == ctx["at"] and i.context["at"].tzinfo
    assert i.context["naive"] == ctx["naive"]
    assert i.context["naive"].tzinfo is None
    assert i.context["total"] == Decimal("1.10")
    i.stop()


def test_codec_warns_on_enum_member_and_use_enum_values_round_trips():
    snap = _snapshot_with({"c": Color.R})  # engine writes "Color.R"
    with pytest.warns(RuntimeWarning, match="Enumy"):
        PydanticCodec(Enumy).encode(snap)
    snap2 = _snapshot_with(EnumyValues(c=Color.R).model_dump(mode="python"))
    blob = PydanticCodec(EnumyValues).encode(snap2)
    assert json.loads(blob)["context"]["c"] == "r"


def test_codec_warning_does_not_echo_the_value_and_keeps_blob():
    snap = _snapshot_with({"total": "x" + SECRET})
    with pytest.warns(RuntimeWarning) as rec:
        out = PydanticCodec(Rich).encode(snap)
    assert all(SECRET not in str(w.message) for w in rec)
    assert out == snap  # stored as-is: refusing would lose the state


def test_codec_does_not_redact_secrets_at_rest():
    snap = _snapshot_with({"card_token": "tok_live"})
    blob = PydanticCodec(Ctx).encode(snap)
    assert json.loads(blob)["context"]["card_token"] == "tok_live"


def test_shared_codec_is_thread_safe():
    codec = PydanticCodec(Ctx)
    snap = _snapshot_with({"items": [{"sku": "a", "qty": 1}], "total": "2"})
    outs, errors = set(), []

    def work():
        try:
            for _ in range(100):
                outs.add(codec.encode(snap))
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(outs) == 1


def _bad_store():
    store = MemoryStore()
    store.save("k", _snapshot_with({"total": "oops"}))
    return store


def test_persisted_refuses_and_does_not_save_after_failed_start():
    store = _bad_store()
    before = store.load("k")
    entered = []
    with pytest.raises(ContextValidationError):
        with persisted(
            store,
            "k",
            _plain(),
            plugins=[TypedContextPlugin(Rich)],
            verify_machine_hash=False,
        ) as i:
            entered.append(i)
    assert not entered
    after = store.load("k")
    assert after.version == before.version
    assert json.loads(after.snapshot)["status"] == "running"


def test_apersisted_refuses_and_does_not_save_after_failed_start():
    store = _bad_store()
    before = store.load("k")

    async def run():
        async with apersisted(
            store,
            "k",
            _plain(),
            plugins=[TypedContextPlugin(Rich)],
            verify_machine_hash=False,
        ):
            raise AssertionError("block must not run")

    with pytest.raises(ContextValidationError):
        asyncio.run(run())
    assert store.load("k").version == before.version


def test_no_leak_across_10k_build_validate_cycles():
    from typing import Literal

    from xstate_statemachine.contrib.pydantic import EventModel, events_union

    class Pay(EventModel):
        type: Literal["PAY"] = "PAY"
        amount: Decimal

    cfg = {"id": "m", "initial": "a", "context": {}, "states": {"a": {}}}

    def cycle():
        m = create_machine(
            cfg,
            context_validator=context_model(Ctx),
            event_schemas=events_union(Pay),
        )
        m.event_schemas["PAY"]({"amount": "1"})

    for _ in range(200):
        cycle()
    gc.collect()
    tracemalloc.start()
    try:
        for _ in range(5000):
            cycle()
        gc.collect()
        half = tracemalloc.get_traced_memory()[0]
        for _ in range(5000):
            cycle()
        gc.collect()
        full = tracemalloc.get_traced_memory()[0]
    finally:
        tracemalloc.stop()
    assert full - half < 64 * 1024
