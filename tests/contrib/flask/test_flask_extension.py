# tests/contrib/flask/test_flask_extension.py
"""#285: application factory (two apps, two stores, no cross-talk),
session-keyed wizards + `SessionStore`, the ``flask xsm`` CLI, 50
concurrent requests on one key over `SQLiteStore`, Flask-WTF CSRF."""

from __future__ import annotations

import json
import threading
from typing import Any, List

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("flask")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryStore,
    OptimisticLock,
    PessimisticLock,
    SQLiteStore,
)

from .conftest import ORDER, make_app, order_machine  # noqa: E402

WIZARD = {
    "id": "wizard",
    "initial": "name",
    "context": {"answers": {}},
    "states": {
        "name": {"on": {"NEXT": {"target": "email", "actions": "keep"}}},
        "email": {
            "on": {
                "NEXT": {"target": "done", "actions": "keep"},
                "BACK": "name",
            }
        },
        "done": {"type": "final"},
    },
}


def _keep(i: Any, c: Any, e: Any, a: Any) -> None:
    c["answers"] = {**c["answers"], **dict(e.payload)}


def wizard_app(store: Any = None) -> Any:
    from uuid import uuid4

    from flask import Flask, request, session

    from src.xstate_statemachine import MachineLogic
    from src.xstate_statemachine.contrib.flask import (
        SessionStore,
        XState,
        allow_all,
        receipt_response,
    )

    xsm = XState()
    xsm.register(
        "wizard",
        create_machine(WIZARD, logic=MachineLogic(actions={"keep": _keep})),
        key=lambda: session.setdefault("wizard_id", uuid4().hex),
        authorize=allow_all,
        context_serializer=lambda c: c,
    )
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    xsm.init_app(app, store=store or SessionStore())

    @app.post("/wizard/<event>")
    def step(event: str) -> Any:
        from flask import g

        with g.xsm.act("wizard") as w:
            return receipt_response(
                w, w.send(event, wait=True, **request.get_json())
            )

    return app


class TestApplicationFactory:
    def test_two_apps_two_stores_no_cross_talk(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import (
            XState,
            allow_all,
            create_statechart_blueprint,
        )

        xsm = XState()  # ONE extension object
        xsm.register("order", order_machine(), authorize=allow_all)
        stores = (MemoryStore(), MemoryStore())
        apps = []
        for s in stores:
            app = Flask(__name__)
            xsm.init_app(app, store=s)
            app.register_blueprint(
                create_statechart_blueprint(xsm, "order", "/o")
            )
            apps.append(app)
        a, b = (x.test_client() for x in apps)
        a.post("/o/1/send", json={"type": "ADD"})
        a.post("/o/1/send", json={"type": "CHECKOUT"})
        assert a.get("/o/1").get_json()["state"] == "paying"
        assert b.get("/o/1").get_json()["state"] == "cart"
        assert stores[0].list_keys() == ["order.1"]
        assert stores[1].list_keys() == []
        assert apps[0].extensions["xstate"] is not apps[1].extensions["xstate"]
        assert not hasattr(xsm, "store")  # nothing bound on the instance

    def test_act_outside_init_app_is_clear(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import XState

        with Flask(__name__).app_context():
            with pytest.raises(RuntimeError, match="init_app"):
                XState().registry()

    def test_per_app_registration_and_key_required(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import XState, allow_all

        xsm = XState()
        app = Flask(__name__)
        xsm.init_app(app, store=MemoryStore())
        simple = {"id": "o", "initial": "cart", "states": {"cart": {}}}
        xsm.register("o", simple, authorize=allow_all, app=app)  # a dict
        with app.test_request_context(method="POST"):
            with pytest.raises(TypeError, match="key="):
                with xsm.act("o"):
                    pass
            with xsm.act("o", "7") as i:
                assert i.value == "cart"
        with pytest.raises(ValueError):
            xsm.register("o", simple, authorize=allow_all, app=app)
        with pytest.raises(TypeError):
            xsm.register("x", 42, authorize=allow_all)

    def test_act_outside_a_request_and_pessimistic_lock(self) -> None:
        app = make_app(MemoryStore(), lock=PessimisticLock())
        with app.app_context():
            with app.xsm.act("order", "9") as i:  # no request: allowed
                i.send("ADD")
            assert app.xsm.peek("order", "9")["state"] == "cart"


class TestSessionWizard:
    def test_two_clients_advance_independent_wizards(self) -> None:
        app = wizard_app()
        a, b = app.test_client(), app.test_client()
        r = a.post("/wizard/NEXT", json={"name": "Ada"})
        assert r.status_code == 200 and r.get_json()["state"] == "email"
        r = b.post("/wizard/NEXT", json={"name": "Bob"})
        assert r.get_json()["context"]["answers"] == {"name": "Bob"}
        r = a.post("/wizard/NEXT", json={"email": "ada@x"})
        body = r.get_json()
        assert body["state"] == "done"
        assert body["context"]["answers"] == {"name": "Ada", "email": "ada@x"}
        r = b.post("/wizard/BACK", json={})
        assert r.get_json()["state"] == "name"

    def test_session_store_refuses_oversize(self) -> None:
        from src.xstate_statemachine.contrib.flask import (
            SessionStoreTooLargeError,
        )
        from src.xstate_statemachine.exceptions import SnapshotTooLargeError

        app = wizard_app()
        app.testing = True
        c = app.test_client()
        with pytest.raises(SessionStoreTooLargeError) as ei:
            c.post("/wizard/NEXT", json={"essay": "x" * 4000})
        assert isinstance(ei.value, SnapshotTooLargeError)
        assert ei.value.limit == 3 * 1024
        assert "server-side store" in str(ei.value)
        # nothing was written: the wizard is still at the start
        r = c.post("/wizard/NEXT", json={"name": "ok"})
        assert r.get_json()["state"] == "email"

    def test_session_store_contract_bits(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import SessionStore
        from src.xstate_statemachine.exceptions import ConflictError
        from src.xstate_statemachine.persistence import Deadline

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "t"
        with app.test_request_context():
            s = SessionStore()
            assert s.load("k") is None and s.list_keys() == []
            d = Deadline("w.a", 1, 5.0, 5, "after.5.w.a")
            assert s.save("k", "{}", expected_version=0, deadlines=[d]) == 1
            with pytest.raises(ConflictError):
                s.save("k", "{}", expected_version=0)
            assert s.load("k").deadlines == (d,)
            with s.lock("k"):
                assert s.save("k", "{}") == 2
            assert s.list_keys(prefix="k") == ["k"]
            assert s.forget("k") == {"snapshots": 1, "deadlines": 0}
            assert s.delete("k") is False


class TestCLI:
    def test_flask_xsm_inspect_equals_xsm_inspect(self, tmp_path: Any):
        from src.xstate_statemachine.cli.commands import reset_console
        from src.xstate_statemachine.cli.commands.inspect import run_inspect

        path = tmp_path / "order.json"
        path.write_text(json.dumps(ORDER), encoding="utf-8")
        app = make_app(MemoryStore())
        # the same JSON FILE the direct call reads (the header shows it)
        app.extensions["xstate"].reg("order").source = path
        res = app.test_cli_runner().invoke(
            args=["xsm", "inspect", "order", "--plain"]
        )
        assert res.exit_code == 0, res.output

        import argparse
        import io
        from contextlib import redirect_stdout

        from src.xstate_statemachine.cli.commands import configure_console

        buf = io.StringIO()
        with redirect_stdout(buf):
            reset_console()
            configure_console(
                argparse.Namespace(plain=True, no_color=False, no_anim=True)
            )
            run_inspect(str(path))
        reset_console()
        direct = buf.getvalue()

        assert res.output == direct
        assert "cart" in res.output and "paying" in res.output

    def test_diagram_docs_simulate_and_errors(self) -> None:
        app = make_app(MemoryStore())
        run = app.test_cli_runner().invoke
        r = run(args=["xsm", "diagram", "order", "--plain"])
        assert r.exit_code == 0 and "stateDiagram" in r.output
        r = run(args=["xsm", "docs", "order", "--plain"])
        assert r.exit_code == 0 and "order" in r.output
        r = run(
            args=["xsm", "simulate", "order", "-e", "ADD,CHECKOUT", "--json"]
        )
        assert r.exit_code == 0
        assert json.loads(r.output)["value"] == "paying"
        r = run(args=["xsm", "inspect", "nope"])
        assert r.exit_code != 0 and "registered: order" in r.output

    def test_machine_node_without_source(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import XState, allow_all

        xsm = XState()
        xsm.register("o", order_machine(), authorize=allow_all)
        app = Flask(__name__)
        xsm.init_app(app, store=MemoryStore())
        r = app.test_cli_runner().invoke(args=["xsm", "inspect", "o"])
        assert r.exit_code != 0 and "source=" in r.output


class TestConcurrency:
    def test_fifty_concurrent_requests_no_lost_updates(self, tmp_path):
        """50 threads POST ADD to ONE key over SQLiteStore; the optimistic
        lock turns races into 409s which the client retries → exactly 50."""
        store = SQLiteStore(tmp_path / "app.db")
        app = make_app(store, lock=OptimisticLock(retries=0))
        conflicts: List[int] = []
        errors: List[Any] = []
        start = threading.Barrier(50)

        def worker() -> None:
            c = app.test_client()
            start.wait()
            for _ in range(500):
                r = c.post("/orders/1/send", json={"type": "ADD"})
                if r.status_code == 200:
                    return
                if r.status_code == 409:
                    conflicts.append(1)
                    continue
                errors.append((r.status_code, r.data))
                return
            errors.append("gave up")

        ts = [threading.Thread(target=worker) for _ in range(50)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        assert errors == []
        snap = json.loads(store.load("order.1").snapshot)
        assert snap["context"]["items"] == 50
        store.close()


class TestCSRF:
    def _app(self, exempt: bool) -> Any:
        pytest.importorskip("flask_wtf")
        from flask_wtf.csrf import CSRFProtect

        app = make_app(MemoryStore())
        app.config["WTF_CSRF_ENABLED"] = True
        csrf = CSRFProtect(app)
        if exempt:
            csrf.exempt(app.blueprints["xsm_order"])
        return app

    def test_blocked_without_token_then_exempt_blueprint_works(self) -> None:
        c = self._app(exempt=False).test_client()
        assert (
            c.post("/orders/1/send", json={"type": "ADD"}).status_code == 400
        )
        c = self._app(exempt=True).test_client()
        assert (
            c.post("/orders/1/send", json={"type": "ADD"}).status_code == 200
        )

    def test_x_csrftoken_header_works(self) -> None:
        pytest.importorskip("flask_wtf")  # before _app, which skips too
        from flask import session
        from flask_wtf.csrf import generate_csrf

        app = self._app(exempt=False)

        @app.get("/token")
        def token() -> Any:
            return {"t": generate_csrf()}

        c = app.test_client()
        t = c.get("/token").get_json()["t"]
        r = c.post(
            "/orders/1/send", json={"type": "ADD"}, headers={"X-CSRFToken": t}
        )
        assert r.status_code == 200
        _ = session  # imported for clarity: the token is session-bound
