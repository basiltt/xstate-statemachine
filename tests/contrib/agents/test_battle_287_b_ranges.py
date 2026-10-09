"""#287 battle (adversary B): value-range constraints on tool arguments.

A tool's `Field(gt=0, le=...)` is how a value range becomes part of the
X0.13 schema check. Before this battle `Annotated[int, Field(...)]` was
flattened to `int` (``get_type_hints`` without ``include_extras``), so a
reviewer was asked to approve ``amount_cents=-1``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from pydantic import Field  # noqa: E402
from typing_extensions import Annotated  # noqa: E402

from xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    run_agent_sync,
    tool,
    tool_registry,
)

MAX_CENTS = 100_000


def _refund_annotated(
    order_id: int, amount_cents: Annotated[int, Field(gt=0, le=MAX_CENTS)]
) -> str:
    """Refund an order."""
    return "ok"


def _refund_default(
    order_id: int, amount_cents: int = Field(gt=0, le=MAX_CENTS)
) -> str:
    """Refund an order."""
    return "ok"


def _run(fn, amount):
    reg = tool_registry(tool(fn, name="refund", side_effect=True))
    script = [
        {"tool": "refund", "args": {"order_id": 1, "amount_cents": amount}}
    ]
    return run_agent_sync(
        model=FakeModel(script, is_async=False), tools=reg, prompt="p"
    )


@pytest.mark.parametrize("fn", [_refund_annotated, _refund_default])
@pytest.mark.parametrize("amount", [-1, 0, 10**12])
def test_out_of_range_value_is_denied_before_the_human_gate(fn, amount):
    # Act
    res = _run(fn, amount)

    # Assert
    assert res.error is not None and res.error["kind"] == "tool_denied"
    assert "amount_cents" in res.error["message"]
    assert not res.waiting


@pytest.mark.parametrize("fn", [_refund_annotated, _refund_default])
def test_in_range_value_reaches_the_human(fn):
    res = _run(fn, 2400)
    assert res.waiting and res.error is None


def test_annotated_constraint_is_in_the_schema_the_model_sees():
    reg = tool_registry(_refund_annotated)
    prop = reg.get("_refund_annotated").parameters["properties"]
    assert prop["amount_cents"]["maximum"] == MAX_CENTS
    assert prop["amount_cents"]["exclusiveMinimum"] == 0
