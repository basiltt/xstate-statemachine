"""Shared helpers for `tests/inspect/` (#274)."""

from __future__ import annotations

import json
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

CHILD = {
    "id": "child",
    "initial": "idle",
    "states": {
        "idle": {
            "on": {
                "PING": {
                    "target": "pinged",
                    "actions": {
                        "type": "sendParent",
                        "params": {"event": {"type": "PONG"}},
                    },
                }
            }
        },
        "pinged": {},
    },
}

PARENT = {
    "id": "parent",
    "initial": "a",
    "context": {"count": 0, "api_token": "sk-SECRET", "email": "a@b"},
    "invoke": {"id": "kid", "src": "kid"},
    "states": {
        "a": {
            "on": {
                "GO": {
                    "target": "b",
                    "actions": [
                        {
                            "type": "sendTo",
                            "params": {"to": "kid", "event": {"type": "PING"}},
                        }
                    ],
                }
            }
        },
        "b": {"on": {"PONG": "c"}},
        "c": {},
    },
}


def recorded():
    return json.loads(
        (FIXTURES / "stately_inspect_messages.json").read_text("utf-8")
    )


@pytest.fixture
def family():
    import copy

    from src.xstate_statemachine import MachineLogic, create_machine

    child = create_machine(copy.deepcopy(CHILD))
    return create_machine(
        copy.deepcopy(PARENT), logic=MachineLogic(services={"kid": child})
    )


@pytest.fixture(autouse=True)
def _clean_global_registry():
    from src.xstate_statemachine import plugins

    before = plugins.global_plugins()
    yield
    for p in plugins.global_plugins():
        if not any(p is b for b in before):
            plugins.unregister_global(p)
