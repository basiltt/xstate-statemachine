# tests/contrib/flask/test_flask_blueprint.py
"""#285: the blueprint route table + status matrix, Idempotency-Key,
authorize, JSON-only bodies, refused state-changing GETs, SSE, history."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("flask")

from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryInbox,
    MemoryLog,
    MemoryStore,
    PessimisticLock,
)

from .conftest import make_app  # noqa: E402


def post(c: Any, path: str, body: Any = None, **kw: Any) -> Any:
    return c.post(path, json=body if body is not None else {}, **kw)


class TestRouteTable:
    def test_routes(self, app: Any) -> None:
        rules = {
            (r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"})))
            for r in app.url_map.iter_rules()
            if r.rule.startswith("/orders")
        }
        assert ("/orders/<key>", ("GET",)) in rules
        assert ("/orders/<key>/send", ("POST",)) in rules
        assert ("/orders/<key>/events/<event>", ("POST",)) in rules
        assert ("/orders/<key>/events", ("GET",)) in rules
        assert ("/orders/<key>/history", ("GET",)) in rules
        assert ("/orders/<key>/stream", ("GET",)) in rules
        assert ("/orders/schema/diagram.mmd", ("GET",)) in rules

    def test_per_event_routes(self) -> None:
        app = make_app(MemoryStore(), per_event_routes=True)
        eps = {r.endpoint for r in app.url_map.iter_rules()}
        assert {"xsm_order.event_ADD", "xsm_order.event_PAY"} <= eps
        c = app.test_client()
        r = post(c, "/orders/1/events/ADD", {"n": 2})
        assert r.status_code == 200
        assert c.get("/orders/1").get_json()["state"] == "cart"

    def test_get_state_is_state_only(self, client: Any) -> None:
        body = client.get("/orders/1").get_json()
        assert body == {
            "state": "cart",
            "state_ids": ["order.cart"],
            "available_events": ["ADD", "LATER"],
            "machine_version": None,
        }
        assert "context" not in body  # X0.1: context only via serializer

    def test_events_and_diagram(self, client: Any) -> None:
        body = client.get("/orders/1/events").get_json()
        assert body["declared"] == ["ADD", "BOOM", "CHECKOUT", "LATER", "PAY"]
        assert body["available"] == ["ADD", "LATER"]
        r = client.get("/orders/schema/diagram.mmd")
        assert r.status_code == 200 and r.data.startswith(b"stateDiagram")


class TestStatusMatrix:
    def test_200_changed_and_unchanged(self, client: Any) -> None:
        r = post(client, "/orders/1/send", {"type": "ADD", "n": 3})
        assert r.status_code == 200 and r.get_json()["changed"] is True
        r = post(client, "/orders/1/send", {"type": "PAY"})  # not here
        assert r.status_code == 200 and r.get_json()["changed"] is False

    def test_409_denied_by_guard(self, client: Any) -> None:
        r = post(client, "/orders/1/send", {"type": "CHECKOUT"})
        assert r.status_code == 409 and r.get_json()["denied"] is True

    def test_500_action_error_carries_class_name_only(self, client: Any):
        post(client, "/orders/1/send", {"type": "ADD"})
        post(client, "/orders/1/send", {"type": "CHECKOUT"})
        r = post(client, "/orders/1/send", {"type": "BOOM"})
        assert r.status_code == 500
        assert r.get_json()["error"] == "RuntimeError"
        assert b"secret internals" not in r.data  # X0.7

    def test_202_deferred(self) -> None:
        from flask import Flask

        from src.xstate_statemachine import create_machine
        from src.xstate_statemachine.contrib.flask import (
            XState,
            allow_all,
            create_statechart_blueprint,
        )

        m = create_machine(
            {
                "id": "d",
                "initial": "a",
                "onUnhandled": "defer",
                "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"X": "a"}}},
            }
        )
        xsm = XState()
        xsm.register("d", m, authorize=allow_all)
        app = Flask(__name__)
        xsm.init_app(app, store=MemoryStore())
        app.register_blueprint(create_statechart_blueprint(xsm, "d", "/d"))
        r = post(app.test_client(), "/d/1/send", {"type": "X"})
        assert r.status_code == 202 and r.get_json()["deferred"] is True

    def test_403_authorize_refuses(self) -> None:
        seen = []

        def only_alice(req: Any, *, name: str, key: Any, event: Any) -> bool:
            seen.append((name, key, event))
            return req.headers.get("X-User") == "alice"

        c = make_app(MemoryStore(), authorize=only_alice).test_client()
        r = post(c, "/orders/1/send", {"type": "ADD"})
        assert r.status_code == 403
        assert r.mimetype == "application/problem+json"
        assert c.get("/orders/1").status_code == 403
        r = post(
            c, "/orders/1/send", {"type": "ADD"}, headers={"X-User": "alice"}
        )
        assert r.status_code == 200
        assert ("order", "1", "ADD") in seen and ("order", "1", None) in seen

    def test_415_413_422_bodies(self, app: Any) -> None:
        c = app.test_client()
        r = c.post(
            "/orders/1/send", data="type=ADD", content_type="text/plain"
        )
        assert r.status_code == 415
        app.extensions["xstate"].max_body_bytes = 64
        r = post(c, "/orders/1/send", {"type": "ADD", "pad": "x" * 200})
        assert r.status_code == 413
        r = c.post(
            "/orders/1/send", data="not json", content_type="application/json"
        )
        assert r.status_code == 422
        r = c.post(
            "/orders/1/send", data="[1]", content_type="application/json"
        )
        assert r.status_code == 422
        r = post(c, "/orders/1/send", {"no": "type"})
        assert r.status_code == 400
        for r in ():
            pass

    def test_409_on_conflict_is_a_problem(self, app: Any, monkeypatch) -> None:
        from src.xstate_statemachine.exceptions import ConflictError

        store = app.extensions["xstate"].store

        def conflict(*a: Any, **k: Any) -> int:
            raise ConflictError("order.1", 0, 1)

        monkeypatch.setattr(store, "save", conflict)
        r = post(app.test_client(), "/orders/1/send", {"type": "ADD"})
        assert r.status_code == 409
        assert r.get_json()["title"] == "Conflict"

    def test_404_when_create_if_missing_false(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import (
            XState,
            allow_all,
            create_statechart_blueprint,
        )

        from .conftest import order_machine

        xsm = XState()
        xsm.register("order", order_machine(), authorize=allow_all)
        app = Flask(__name__)
        xsm.init_app(app, store=MemoryStore())
        app.register_blueprint(
            create_statechart_blueprint(
                xsm, "order", "/o", create_if_missing=False
            )
        )
        c = app.test_client()
        assert c.get("/o/1").status_code == 404
        assert post(c, "/o/1/send", {"type": "ADD"}).status_code == 404


class TestSafeMethods:
    def test_state_changing_get_is_refused(self, client: Any) -> None:
        r = client.get("/orders/1/send")
        assert r.status_code == 405
        assert r.headers["Allow"] == "POST"
        assert r.mimetype == "application/problem+json"
        assert client.get("/orders/1/events/ADD").status_code == 405

    def test_act_inside_a_get_view_is_refused(self, app: Any) -> None:
        @app.get("/sneaky/<key>")
        def sneaky(key: str) -> Any:
            with app.xsm.act("order", key) as i:
                i.send("ADD")
            return "done"

        # 📝 #285 battle (A): the app-level handler answers a 405 problem
        #    (was an HTML 500 outside testing mode).
        r = app.test_client().get("/sneaky/1")
        assert r.status_code == 405
        assert r.content_type == "application/problem+json"
        assert r.get_json()["error"] == "MethodNotAllowedError"


class TestIdempotency:
    def _client(self) -> Any:
        return make_app(MemoryStore(), inbox=MemoryInbox()).test_client()

    def test_replay_is_duplicate_and_not_reapplied(self) -> None:
        c = self._client()
        h = {"Idempotency-Key": "k-1", "X-User": "alice"}
        r1 = post(c, "/orders/1/send", {"type": "ADD", "n": 5}, headers=h)
        r2 = post(c, "/orders/1/send", {"type": "ADD", "n": 5}, headers=h)
        assert r1.status_code == r2.status_code == 200
        assert r1.get_json()["duplicate"] is False
        assert r2.get_json()["duplicate"] is True
        with c.application.test_request_context(method="POST"):
            store = c.application.extensions["xstate"].store
            snap = json.loads(store.load("order.1").snapshot)
        assert snap["context"]["items"] == 5
        assert store.load("order.1").version == 1  # the replay did not save

    def test_mismatch_is_422_problem(self) -> None:
        c = self._client()
        h = {"Idempotency-Key": "k-1", "X-User": "alice"}
        post(c, "/orders/1/send", {"type": "ADD", "n": 5}, headers=h)
        r = post(c, "/orders/1/send", {"type": "ADD", "n": 6}, headers=h)
        assert r.status_code == 422
        assert r.mimetype == "application/problem+json"
        assert r.get_json()["error"] == "IdempotencyMismatchError"

    def test_scope_is_the_principal(self) -> None:
        c = self._client()
        body = {"type": "ADD", "n": 1}
        post(
            c,
            "/orders/1/send",
            body,
            headers={"Idempotency-Key": "k", "X-User": "a"},
        )
        r = post(
            c,
            "/orders/1/send",
            body,
            headers={"Idempotency-Key": "k", "X-User": "b"},
        )
        assert r.get_json()["duplicate"] is False  # b's key is b's own

    def test_inbox_requires_principal(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import XState

        with pytest.raises(ValueError, match="X0.2"):
            XState().init_app(
                Flask(__name__), store=MemoryStore(), inbox=MemoryInbox()
            )


class TestHistoryAndStream:
    def test_history_404_without_log(self, client: Any) -> None:
        r = client.get("/orders/1/history")
        assert r.status_code == 404
        assert r.get_json()["title"] == "History not enabled"

    def test_history_with_log(self) -> None:
        c = make_app(MemoryStore(), log=MemoryLog()).test_client()
        post(c, "/orders/1/send", {"type": "ADD", "actor": "basil"})
        items = c.get("/orders/1/history").get_json()["items"]
        assert [(i["seq"], i["event_type"], i["actor"]) for i in items] == [
            (1, "ADD", "basil")
        ]
        assert "event_payload" not in items[0]
        assert c.get("/orders/1/history?after=x").status_code == 400

    def test_stream_snapshot_and_transition(self, app: Any) -> None:
        c = app.test_client()
        r = c.get("/orders/1/stream?once=1")
        assert r.status_code == 200 and r.mimetype == "text/event-stream"
        assert r.data.startswith(b"id: 0\nevent: snapshot\ndata: ")
        # a live stream receives a committed transition
        resp = c.get("/orders/1/stream", buffered=False)
        it = resp.response
        first = next(iter(it))
        assert b"event: snapshot" in first
        post(c, "/orders/1/send", {"type": "ADD"})
        nxt = next(iter(it))
        assert b"event: transition" in nxt and b'"changed":true' in nxt
        resp.close()
        assert app.extensions["xstate"].fanout.connections("order", "1") == 0

    def test_stream_origin_and_connection_cap(self) -> None:
        app = make_app(MemoryStore(), max_connections_per_key=1)
        c = app.test_client()
        r = c.get(
            "/orders/1/stream?once=1", headers={"Origin": "https://evil.test"}
        )
        assert r.status_code == 403
        held = c.get("/orders/1/stream", buffered=False)
        next(iter(held.response))
        assert c.get("/orders/1/stream?once=1").status_code == 429
        held.close()


class TestAllowAll:
    def test_warns_once(self, caplog: Any) -> None:
        from src.xstate_statemachine.contrib.flask import _core

        _core._allow_all_warned.clear()
        c = make_app(MemoryStore()).test_client()
        with caplog.at_level(logging.WARNING):
            c.get("/orders/1")
            c.get("/orders/2")
        msgs = [m for m in caplog.messages if "allow_all" in m]
        assert len(msgs) == 1

    def test_authorize_is_required(self) -> None:
        from src.xstate_statemachine.contrib.flask import XState

        from .conftest import order_machine

        with pytest.raises(TypeError, match="X0.1"):
            XState().register("order", order_machine())  # type: ignore
        with pytest.raises(ValueError):
            XState().register(
                "a.b", order_machine(), authorize=lambda *a, **k: True
            )
