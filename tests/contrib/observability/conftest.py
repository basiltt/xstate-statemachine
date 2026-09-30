"""Shared fixtures for `tests/contrib/observability/` (#273)."""

from __future__ import annotations

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("observability")

#: A small chart exercising every hook the plugins map: guards (one that
#: denies), actions (one that raises), a service (one that fails), a
#: declared and an undeclared event.
CHART = {
    "id": "shop",
    "initial": "idle",
    "actionErrorPolicy": "continue",
    "context": {"n": 0, "card_number": "4111"},
    "states": {
        "idle": {
            "on": {
                "PAY": {"target": "paying", "guard": "canPay"},
                "DENY": {"target": "paying", "guard": "never"},
                "BOOM": {"actions": ["explode"]},
            }
        },
        "paying": {
            "invoke": {
                "id": "charge",
                "src": "charge",
                "onDone": {"target": "paid", "actions": ["note"]},
                "onError": "failed",
            }
        },
        "paid": {"on": {"RESET": "idle"}},
        "failed": {"on": {"RESET": "idle"}},
    },
}


def make_logic(*, charge_fails: bool = False, log=None):
    from src.xstate_statemachine import MachineLogic

    def charge(i, ctx, e):
        if charge_fails:
            raise RuntimeError("card declined")
        return {"ok": True}

    def note(i, ctx, e, a):
        if log is not None:
            log()

    def explode(i, ctx, e, a):
        raise ValueError("kaboom")

    return MachineLogic(
        actions={"note": note, "explode": explode},
        guards={"canPay": lambda c, e: True, "never": lambda c, e: False},
        services={"charge": charge},
    )


@pytest.fixture
def machine_factory():
    from src.xstate_statemachine import create_machine

    def _make(**kw):
        import copy

        return create_machine(copy.deepcopy(CHART), logic=make_logic(**kw))

    return _make


@pytest.fixture(autouse=True)
def _clean_global_registry():
    from src.xstate_statemachine import plugins

    before = plugins.global_plugins()
    yield
    for p in plugins.global_plugins():
        if not any(p is b for b in before):
            plugins.unregister_global(p)
