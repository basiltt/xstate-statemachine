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
