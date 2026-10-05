"""pytest-bdd step definitions for ``order.feature`` (#272 recipe).

Every step is a one-line call on the `Scenario` that ``given()`` returns.
Step values arrive as plain strings parsed by ``pytest_bdd.parsers`` --
nothing in the feature file is evaluated as Python. Without pytest-bdd
installed the whole folder is skipped.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator

import pytest

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.testing import Scenario, given

# 📝 a conftest cannot `importorskip` (a skip outside a test is an error);
#    `test_order_feature.py` does, so without pytest-bdd nothing runs.
try:
    from pytest_bdd import given as bdd_given
    from pytest_bdd import parsers, then, when
except ImportError:  # pragma: no cover - exercised by the skip test
    bdd_given = None

ORDER: Dict[str, Any] = {
    "id": "order",
    "initial": "pending",
    "context": {"orderId": None, "trackingId": None},
    "states": {
        "pending": {"on": {"PAY": "paid", "CANCEL": "cancelled"}},
        "paid": {
            "on": {
                "PACKED": {"target": "shipped", "actions": "setTracking"},
                "CANCEL": "cancelled",
            }
        },
        "shipped": {},
        "cancelled": {"type": "final"},
    },
}


def _set_tracking(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["trackingId"] = f"TRK-{ctx['orderId']}"


@pytest.fixture
def order_machine() -> Any:
    return create_machine(
        ORDER, logic=MachineLogic(actions={"setTracking": _set_tracking})
    )


@pytest.fixture
def spec(order_machine: Any) -> Iterator[Scenario]:
    # 📝 one Scenario per Gherkin scenario; every step shares it
    with given(order_machine) as s:
        yield s


if bdd_given is not None:

    @bdd_given(parsers.parse('the order is in state "{state}"'))
    def _in_state(spec: Scenario, state: str) -> None:
        spec.in_state(state)

    @bdd_given(parsers.parse('the context has {key} "{value}"'))
    def _given_context(spec: Scenario, key: str, value: str) -> None:
        spec.with_context(**{key: value})

    @when(parsers.parse('I send "{event}"'))
    def _send(spec: Scenario, event: str) -> None:
        spec.when(event)

    @then(parsers.parse('the state is "{state}"'))
    def _state_is(spec: Scenario, state: str) -> None:
        spec.then_state(state)

    @then(parsers.parse('the context has {key} "{value}"'))
    def _then_context(spec: Scenario, key: str, value: str) -> None:
        spec.then_context(**{key: value})

    @then("nothing changed")
    def _unchanged(spec: Scenario) -> None:
        spec.then_changed(False)
