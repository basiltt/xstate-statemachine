# tests/contrib/testing/test_battle_271_payloads.py
"""#271 battle (adversary A): payload inference from `EventModel`s.

Before: ``Decimal`` / ``datetime`` / nested models were "uninferable"
(``ValueError``), and constrained fields (``Field(ge=1)``,
``min_length``) were inferred from the bare annotation -- every draw
outside the constraint raised `InvalidEventPayloadError` on send. Now the
mapping is wider and every draw is filtered through the model itself.
"""

from __future__ import annotations

import datetime
import decimal
import pathlib
from typing import Any, List, Literal, Optional

import pytest

pytest.importorskip("hypothesis")
pytest.importorskip("pydantic")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)
from src.xstate_statemachine.contrib.testing import (  # noqa: E402
    model_test,
    payload_strategy,
)

S = settings(
    deadline=None,
    database=None,
    derandomize=True,
    suppress_health_check=list(HealthCheck),
    max_examples=30,
)


class Inner(BaseModel):
    x: int


def _model(name: str, ann: Any, **field: Any) -> Any:
    ns: dict = {"__annotations__": {"type": Literal[name], "v": ann}}
    ns["type"] = name
    if field:
        ns["v"] = Field(**field)
    return type(name, (EventModel,), ns)


CASES = {
    "INT": (int, {}),
    "STR": (str, {}),
    "LIT": (Literal["a", "b"], {}),
    "OPT": (Optional[int], {}),
    "LST": (List[int], {}),
    "NEST": (Inner, {}),
    "DEC": (decimal.Decimal, {}),
    "DT": (datetime.datetime, {}),
    "GE": (int, {"ge": 1}),
    "MINLEN": (str, {"min_length": 3}),
}


@pytest.mark.parametrize("event", sorted(CASES))
def test_inferred_payloads_always_validate(
    event: str, tmp_path: pathlib.Path
) -> None:
    ann, field = CASES[event]
    model = _model(event, ann, **field)
    cfg = {
        "id": "p" + event,
        "initial": "a",
        "states": {"a": {"on": {event: "b"}}, "b": {"on": {"BACK": "a"}}},
    }
    machine = create_machine(cfg, event_schemas=events_union(model))
    model_test(machine, settings=S, failing_path=tmp_path / "f.json").TestCase(
        "runTest"
    ).runTest()


def test_constraint_is_honoured_by_the_strategy() -> None:
    strat = payload_strategy(_model("GE", int, ge=1))

    @S
    @given(strat)
    def check(p: dict) -> None:
        assert p["v"] >= 1

    check()


def test_uninferable_required_field_is_value_error() -> None:
    with pytest.raises(ValueError, match="cannot infer"):
        payload_strategy(_model("CPX", complex))
