# tests/contrib/flask/test_battle_285_a.py
"""#285 battle, adversary A: concurrency, idempotency races, leaks,
cookie sizes, CSRF, SSE on a real threaded server, Quart, `flask xsm`.

Defects found (each test below failed before its fix):

* `act()` in the APP'S OWN view: a GET (`MethodNotAllowedError`) and a
  lost optimistic race (`ConflictError`) were HTML 500s -- the 405 / 409
  problems only existed inside the blueprint. Same under Quart.
* `SessionStore` capped each snapshot at 3 KiB, but every machine on a
  session shares ONE cookie: two wizards made a 4.3 KiB cookie, which
  browsers drop silently. The cap is now the session's total.
* `SessionStoreTooLargeError` raised from an app view was a 500; it is
  now a 413 problem.
* The Quart stream skipped the ``Origin`` check (X0.7); `QuartXState`
  lacked ``allowed_origins`` / ``max_connections_per_key`` / ``clock`` /
  ``migrator``, and its `act()` did not derive the principal for the inbox.
"""

from __future__ import annotations

import asyncio
import random
import string
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any, List

import pytest

from ..conftest import requires_extra

pytestmark = [requires_extra("flask"), pytest.mark.timeout(300)]
pytest.importorskip("flask")

from flask import Flask, g  # noqa: E402

from src.xstate_statemachine.contrib.flask import (  # noqa: E402
    SessionStore,
    XState,
    allow_all,
)
from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryInbox,
    MemoryStore,
    PessimisticLock,
    SQLiteStore,
)

from .conftest import make_app, order_machine  # noqa: E402

BROWSER_COOKIE_LIMIT = 4093  # RFC 6265 user agents: name+value+attrs


def _hammer(app: Any, n: int, path: str, **kw: Any) -> List[Any]:
    out: List[Any] = []
    bar = threading.Barrier(n)

    def w() -> None:
        c = app.test_client()
        bar.wait()
        out.append(c.post(path, **kw))

    ts = [threading.Thread(target=w) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    return out


def _items(app: Any, key: str, **kw: Any) -> int:
    with app.test_request_context("/", method="POST"):
        with app.xsm.act("order", key, **kw) as i:
            n: int = i.context["items"]
            app.xsm.skip_save()
    return n


# -----------------------------------------------------------------------------
# 1. Concurrency on one SQLite key
# -----------------------------------------------------------------------------
def test_optimistic_50_threads_exact_increments_and_409s(
    tmp_path: Path,
) -> None:
    app = make_app(SQLiteStore(str(tmp_path / "a.db")))
    rs = _hammer(app, 50, "/orders/1/send", json={"type": "ADD"})
    codes = Counter(r.status_code for r in rs)
    assert set(codes) <= {200, 409}, codes
    for r in rs:
        if r.status_code == 409:
            assert r.content_type == "application/problem+json"
            assert r.get_json()["error"] == "ConflictError"
    assert _items(app, "1") == codes[200]


def test_pessimistic_50_threads_no_409_bounded(tmp_path: Path) -> None:
    app = make_app(SQLiteStore(str(tmp_path / "a.db")), lock=PessimisticLock())
    t0 = time.monotonic()
    rs = _hammer(app, 50, "/orders/1/send", json={"type": "ADD"})
    assert time.monotonic() - t0 < 60
    assert Counter(r.status_code for r in rs) == {200: 50}
    assert _items(app, "1") == 50


@pytest.mark.parametrize("pessimistic", [False, True])
def test_simultaneous_identical_idempotent_requests_apply_once(
    tmp_path: Path, pessimistic: bool
) -> None:
    kw = {"lock": PessimisticLock()} if pessimistic else {}
    app = make_app(
        SQLiteStore(str(tmp_path / "i.db")), inbox=MemoryInbox(), **kw
    )
    hdr = {"Idempotency-Key": "k1", "X-User": "alice"}
    for _ in range(5):
        rs = _hammer(
            app, 2, "/orders/1/send", json={"type": "ADD"}, headers=hdr
        )
        assert all(r.status_code in (200, 409) for r in rs)
    assert _items(app, "1", principal="alice") == 1
    # 🔐 X0.2: bob's identical key is HIS, not a replay of alice's
    r = app.test_client().post(
        "/orders/1/send",
        json={"type": "ADD"},
        headers={"Idempotency-Key": "k1", "X-User": "bob"},
    )
    assert r.status_code == 200 and r.get_json()["duplicate"] is False
    assert _items(app, "1", principal="alice") == 2


# -----------------------------------------------------------------------------
# 1b. DEFECT: act() in the app's own views -> 405 / 409 problems, not 500
# -----------------------------------------------------------------------------
def _app_with_view(store: Any, **kw: Any) -> Any:
    app = make_app(store, **kw)

    @app.route("/v/<key>", methods=["GET", "POST"])
    def v(key: str) -> Any:
        with g.xsm.act("order", key) as i:
            i.send("ADD")
            time.sleep(0.01)
        return "ok"

    @app.post("/boom/<key>")
    def boom(key: str) -> Any:
        with g.xsm.act("order", key) as i:
            i.send("ADD")
            raise RuntimeError("mid-request")

    return app


def test_get_act_in_app_view_is_405_problem() -> None:
    r = _app_with_view(MemoryStore()).test_client().get("/v/1")
    assert r.status_code == 405
    assert r.content_type == "application/problem+json"


def test_lost_race_in_app_view_is_409_problem(tmp_path: Path) -> None:
    app = _app_with_view(SQLiteStore(str(tmp_path / "v.db")))
    rs = _hammer(app, 20, "/v/1")
    codes = Counter(r.status_code for r in rs)
    assert set(codes) <= {200, 409} and codes[409] > 0, codes
    assert _items(app, "1") == codes[200]


def test_raising_act_leaks_no_lock_or_thread(tmp_path: Path) -> None:
    app = _app_with_view(
        SQLiteStore(str(tmp_path / "l.db")), lock=PessimisticLock()
    )
    c = app.test_client()
    base = threading.active_count()
    for n in range(500):
        if n % 2:
            assert c.post("/boom/L").status_code == 500
        else:
            assert c.post("/orders/L/send", json={"type": "ADD"}).status_code
    assert threading.active_count() <= base + 1
    # a held lease would make this block / 409
    assert c.post("/orders/L/send", json={"type": "ADD"}).status_code == 200
    assert _items(app, "L") == 251


def test_g_xsm_is_bound_per_app() -> None:
    a, b = make_app(MemoryStore()), make_app(MemoryStore())
    with a.test_request_context("/", method="POST"):
        a.preprocess_request()
        reg_a = g.xsm.registry
    with b.test_request_context("/", method="POST"):
        b.preprocess_request()
        assert g.xsm.registry is not reg_a


# -----------------------------------------------------------------------------
# 3. SessionStore: the whole cookie stays under the browser limit
# -----------------------------------------------------------------------------
def _session_app(*names: str, **store_kw: Any) -> Any:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "k"
    x = XState()
    for n in names:
        x.register(
            n,
            {
                "id": n,
                "initial": "a",
                "context": {"blob": ""},
                "states": {"a": {"on": {"X": {}}}},
            },
            authorize=allow_all,
        )
    x.init_app(app, store=SessionStore(**store_kw))

    @app.post("/s/<m>/<int:n>/<int:seed>")
    def s(m: str, n: int, seed: int) -> Any:
        from flask import session

        session["user_id"] = "user-0123456789abcdef"
        rnd = random.Random(seed)
        al = string.ascii_letters + '"\\' * 8 + "é漢"
        with g.xsm.act(m, "k") as i:
            i.context["blob"] = "".join(rnd.choice(al) for _ in range(n))
            i.send("X")
        return "ok"

    return app


def _cookie_len(resp: Any) -> int:
    return len(resp.headers.get("Set-Cookie", ""))


def test_one_snapshot_at_the_cap_fits_a_browser_cookie() -> None:
    app = _session_app("w")
    biggest = 0
    for n in range(500, 3200, 50):
        r = app.test_client().post(f"/s/w/{n}/{n}")
        assert r.status_code in (200, 413)
        if r.status_code == 200:
            biggest = max(biggest, _cookie_len(r))
    assert 2500 < biggest < BROWSER_COOKIE_LIMIT


def test_two_machines_share_the_cap_and_the_cookie_fits() -> None:
    app = _session_app("w", "w2")
    c = app.test_client()
    assert c.post("/s/w/1100/1").status_code == 200
    r = c.post("/s/w2/1100/2")
    # 📝 before the fix: 200 and a ~4.3 KiB cookie the browser drops
    assert r.status_code == 413
    assert r.content_type == "application/problem+json"
    assert r.get_json()["error"] == "SessionStoreTooLargeError"
    assert c.post("/s/w2/200/3").status_code == 200
    assert len(c.get_cookie("session").value) < BROWSER_COOKIE_LIMIT


def test_session_clear_drops_the_bucket_and_bad_cookies_start_fresh() -> None:
    app = _session_app("w")

    @app.post("/clear")
    def clear() -> Any:
        from flask import session

        session.clear()
        return "ok"

    c = app.test_client()
    c.post("/s/w/100/1")
    c.post("/clear")
    from flask import session

    with app.test_request_context("/"):
        assert SessionStore().load("w.k") is None and "_xsm" not in session
    # tampered / foreign-key cookies: fresh session, never a 500
    for bad in ("garbage.sig.x", _foreign_cookie(app)):
        c2 = app.test_client()
        c2.set_cookie("session", bad)
        assert c2.post("/s/w/10/1").status_code == 200


def _foreign_cookie(app: Any) -> str:
    other = _session_app("w")
    other.config["SECRET_KEY"] = "another"
    c = other.test_client()
    c.post("/s/w/10/1")
    return str(c.get_cookie("session").value)


def test_codec_compresses_under_the_cap() -> None:
    import base64
    import zlib

    class Zip:
        def encode(self, s: str) -> str:
            return base64.b64encode(zlib.compress(s.encode())).decode()

        def decode(self, s: str) -> str:
            return zlib.decompress(base64.b64decode(s)).decode()

    app = _session_app("w", codec=Zip())

    @app.post("/rep")
    def rep() -> Any:
        with g.xsm.act("w", "k") as i:
            i.context["blob"] = "abc" * 2000  # 6 KB plain
            i.send("X")
        return "ok"

    plain = _session_app("w").test_client().post("/s/w/6000/1")
    assert plain.status_code == 413
    assert app.test_client().post("/rep").status_code == 200


# -----------------------------------------------------------------------------
# 4. CSRF + Origin
# -----------------------------------------------------------------------------
def test_csrf_both_configurations() -> None:
    pytest.importorskip("flask_wtf")
    from flask_wtf.csrf import CSRFProtect, generate_csrf

    app = make_app(MemoryStore())
    csrf = CSRFProtect(app)

    @app.get("/tok")
    def tok() -> Any:
        return generate_csrf()

    c = app.test_client()
    assert c.post("/orders/1/send", json={"type": "ADD"}).status_code == 400
    assert c.get("/orders/1").get_json()["state"] == "cart"
    t = c.get("/tok").data.decode()
    r = c.post(
        "/orders/1/send", json={"type": "ADD"}, headers={"X-CSRFToken": t}
    )
    assert r.status_code == 200
    csrf.exempt(app.blueprints["xsm_order"])
    assert c.post("/orders/1/send", json={"type": "ADD"}).status_code == 200


def test_stream_origin_check() -> None:
    app = make_app(MemoryStore(), allowed_origins=["https://ok.example"])
    c = app.test_client()
    url = "/orders/1/stream?once=1"
    assert c.get(url, headers={"Origin": "https://evil"}).status_code == 403
    assert c.get(url, headers={"Origin": "https://ok.example"}).status_code
    assert c.get(url, headers={"Origin": "http://localhost"}).status_code
    assert c.get(url).status_code == 200


# -----------------------------------------------------------------------------
# 5. SSE on a real threaded WSGI server
# -----------------------------------------------------------------------------
def test_sse_fanout_slots_heartbeat_shutdown() -> None:
    httpx = pytest.importorskip("httpx")
    from werkzeug.serving import make_server

    app = make_app(MemoryStore(), heartbeat_s=0.2)
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    got: List[List[str]] = [[] for _ in range(16)]
    stops = [threading.Event() for _ in range(16)]

    def sub(i: int) -> None:
        with httpx.stream("GET", base + "/orders/1/stream", timeout=20) as r:
            for line in r.iter_lines():
                got[i].append(line)
                if stops[i].is_set():
                    break

    ts = [
        threading.Thread(target=sub, args=(i,), daemon=True) for i in range(16)
    ]
    for t in ts:
        t.start()
    fan = app.extensions["xstate"].fanout
    deadline = time.monotonic() + 10
    while fan.connections("order", "1") < 16 and time.monotonic() < deadline:
        time.sleep(0.05)
    try:
        assert httpx.get(base + "/orders/1/stream?once=1").status_code == 429
        httpx.post(base + "/orders/1/send", json={"type": "ADD"})
        time.sleep(0.8)
        per = [sum(ln == "event: transition" for ln in g_) for g_ in got]
        assert per == [1] * 16
        assert all(any("heartbeat" in ln for ln in g_) for g_ in got)
        stops[0].set()
        ts[0].join(5)
        # 📝 the server notices the hang-up at its next write (heartbeat)
        deadline = time.monotonic() + 5
        while (
            fan.connections("order", "1") > 15 and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        assert fan.connections("order", "1") == 15
        assert httpx.get(base + "/orders/1/stream?once=1").status_code == 200
    finally:
        for s in stops:
            s.set()
        t0 = time.monotonic()
        srv.shutdown()
        assert time.monotonic() - t0 < 5


# -----------------------------------------------------------------------------
# 7. flask xsm without a JSON source
# -----------------------------------------------------------------------------
def test_flask_xsm_cli_errors_are_one_line() -> None:
    app = make_app(MemoryStore())
    app.xsm.register("nosrc", order_machine(), authorize=allow_all, app=app)
    run = app.test_cli_runner()
    r = run.invoke(args=["xsm", "inspect", "nosrc"])
    assert r.exit_code == 1 and "source=" in r.output
    r = run.invoke(args=["xsm", "inspect", "nope"])
    assert r.exit_code == 1 and "registered: nosrc, order" in r.output
    r = run.invoke(args=["xsm", "inspect", "order", "--plain"])
    assert r.exit_code == 0
    r.output.encode("cp1252")  # --plain is cp1252-safe


# -----------------------------------------------------------------------------
# 6. Quart
# -----------------------------------------------------------------------------
def _quart_app(store: Any, **kw: Any) -> Any:
    quart = pytest.importorskip("quart")
    from src.xstate_statemachine.contrib.quart import (
        QuartXState,
        create_quart_statechart_blueprint,
    )

    async def az(req: Any, **_: Any) -> bool:
        return req.headers.get("X-Deny") is None

    app = quart.Quart(__name__)
    x = QuartXState()
    x.register("order", order_machine(), authorize=az)
    x.init_app(app, store=store, **kw)
    app.register_blueprint(create_quart_statechart_blueprint(x, "order", "/o"))

    @app.route("/act/<k>", methods=["GET", "POST"])
    async def act(k: str) -> Any:
        async with x.act("order", k) as i:
            await i.send("ADD", wait=True)
        return "ok"

    return app


@pytest.mark.parametrize("kind", ["memory", "sqlite", "pessimistic"])
def test_quart_50_concurrent_acts_on_one_key(
    tmp_path: Path, kind: str
) -> None:
    store = (
        MemoryStore()
        if kind == "memory"
        else SQLiteStore(str(tmp_path / "q.db"))
    )
    kw = {"lock": PessimisticLock()} if kind == "pessimistic" else {}
    app = _quart_app(store, **kw)

    async def main() -> None:
        c = app.test_client()
        for path, body in (("/o/1/send", {"type": "ADD"}), ("/act/2", None)):
            rs = await asyncio.gather(
                *[c.post(path, json=body) for _ in range(50)]
            )
            codes = Counter(r.status_code for r in rs)
            # 📝 before the fix: the app view's losers were 500s
            assert set(codes) <= {200, 409}, codes
            if kw:
                assert codes == {200: 50}
        assert (await c.get("/act/3")).status_code == 405
        assert (
            await c.get("/o/1", headers={"X-Deny": "1"})
        ).status_code == 403

    asyncio.run(main())


def test_quart_stream_checks_origin_and_takes_flask_options() -> None:
    app = _quart_app(
        MemoryStore(),
        allowed_origins=["https://ok.example"],
        max_connections_per_key=2,
    )

    async def main() -> None:
        c = app.test_client()
        url = "/o/1/stream?once=1"
        bad = await c.get(url, headers={"Origin": "https://evil"})
        assert bad.status_code == 403
        ok = await c.get(url, headers={"Origin": "https://ok.example"})
        assert ok.status_code == 200

    asyncio.run(main())
    assert app.extensions["xstate"].fanout.max_connections_per_key == 2


def test_quart_act_derives_principal_for_the_inbox() -> None:
    app = _quart_app(
        MemoryStore(), inbox=MemoryInbox(), principal=lambda r: "alice"
    )

    async def main() -> None:
        r = await app.test_client().post("/act/1")
        assert r.status_code == 200  # was ValueError -> 500

    asyncio.run(main())
