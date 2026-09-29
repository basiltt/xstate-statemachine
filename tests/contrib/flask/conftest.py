# tests/contrib/flask/conftest.py
"""Flask fixtures: an app factory over a store of the test's choosing."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("flask")

ORDER = {
    "id": "order",
    "initial": "cart",
    "context": {"items": 0, "secret": "s3cr3t"},
    "states": {
        "cart": {
            "on": {
                "ADD": {"actions": "add"},
                "CHECKOUT": {"target": "paying", "guard": "hasItems"},
                "LATER": {},
            }
        },
        "paying": {"on": {"PAY": "paid", "BOOM": {"actions": "boom"}}},
        "paid": {"type": "final"},
    },
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["items"] = c["items"] + int(e.payload.get("n", 1))


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("secret internals: do not leak")


def order_machine() -> Any:
    from src.xstate_statemachine import MachineLogic, create_machine

    return create_machine(
        {**ORDER, "actionErrorPolicy": "rollback"},
        logic=MachineLogic(
            actions={"add": _add, "boom": _boom},
            guards={"hasItems": lambda c, e: c["items"] > 0},
        ),
    )


def make_app(
    store: Any,
    *,
    authorize: Optional[Callable[..., bool]] = None,
    inbox: Any = None,
    log: Any = None,
    per_event_routes: bool = False,
    **init_kw: Any,
) -> Any:
    from flask import Flask

    from src.xstate_statemachine.contrib.flask import (
        XState,
        allow_all,
        create_statechart_blueprint,
    )

    xsm = XState()
    xsm.register(
        "order",
        order_machine(),
        authorize=authorize or allow_all,
        source=ORDER,
    )
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    kw: Dict[str, Any] = dict(init_kw)
    if inbox is not None:
        kw.setdefault("principal", lambda req: req.headers.get("X-User", "u"))
    xsm.init_app(app, store=store, inbox=inbox, log=log, **kw)
    app.register_blueprint(
        create_statechart_blueprint(
            xsm, "order", "/orders", per_event_routes=per_event_routes
        )
    )
    app.xsm = xsm  # type: ignore[attr-defined]
    return app


@pytest.fixture
def app() -> Any:
    from src.xstate_statemachine.persistence import MemoryStore

    return make_app(MemoryStore())


@pytest.fixture
def client(app: Any) -> Any:
    return app.test_client()
