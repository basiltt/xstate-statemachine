# examples/integrations/django_approvals/tests/test_battle_283_scenario.py
"""#283 battle: the REST API and the WebSocket under the load a company's
expense tool actually gets.

* **two hundred API clients approving** -- 200 expenses, both roles via
  `APIClient` from threads, every request with an `Idempotency-Key` sent
  TWICE (a retrying client): effects exactly once, the replay answers
  `duplicate` with the original body, every expense ends `approved`;
* **the status matrix per role** -- 401 anonymous, 403 wrong role, 200
  the right one, 409 a refused guard / a finished machine, 422 a reserved
  payload key, 404 an event route that does not exist; the generic
  `send/` route agrees with the per-event routes;
* **the OpenAPI schema** -- one path per event, 403/409/422 responses
  documented, valid against `openapi-spec-validator` when installed;
* **a hundred WebSocket subscribers on one expense** -- a transition
  sent by ONE of them is received by all 100 exactly once; a transition
  made through the REST API (or the admin) must reach the subscribers
  too -- a dashboard that only updates when the change came through its
  own socket is not a dashboard; a subscriber disconnecting mid-fan-out
  harms no one; `live_consumers()` returns to zero;
* **auth and origin** -- an anonymous socket closes 1008; a socket for an
  expense the user may not view closes 1008; a cross-origin handshake is
  refused by the ASGI stack;
* **a real daphne** -- the example's `config.asgi:application` in a
  subprocess, driven with httpx (login, REST approve) and `websockets`
  (the snapshot, then the pushed transition) end to end.

Both dialects: SQLite here, Postgres via
`tests/contrib/django/test_battle_280_postgres.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connections
from rest_framework.test import APIClient

from approvals.models import FINANCE, LEGAL, Expense
from approvals.ws import websocket_urlpatterns
from xstate_statemachine.contrib.channels import live_consumers

EXAMPLE = Path(__file__).resolve().parents[1]
N = 200

# 📝 #591: a DEADLINE for waiting on a frame -- a safety net, not a
#    performance budget. Every pushed transition re-authorises and reloads
#    the row on ONE thread-sensitive thread (`database_sync_to_async`), so
#    100 subscribers are ~100 SERIALISED database round trips: a few
#    milliseconds each locally, seconds on a loaded CI runner. Waits must
#    end when the CONDITION holds ("every subscriber received its frame"),
#    never on the testing helpers' 1 s default (the receipt alone measured
#    0.10-0.33 s against a LOCAL Postgres) or a per-frame 10 s stopwatch.
DEADLINE = 120.0
#: 📡 the consumer's keep-alive frame (`StatechartConsumer.heartbeat_s`,
#: 15 s). It is NOT a state change; a scenario slower than the interval has
#: pings interleaved and must skip them, not assert on them.
PING = "ping"


async def _next_frame(c: Any, kind: str) -> Dict[str, Any]:
    """The next frame of *kind* on *c*, skipping heartbeat ``ping`` frames.

    ⏱️ DEADLINE bounds the WHOLE wait, not each read: a ping every 15 s
    would otherwise restart the timeout for ever, and a subscriber that
    never receives its frame would hang the test until the job timeout
    instead of failing it (review finding on #591).
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + DEADLINE
    while True:
        left = deadline - loop.time()
        if left <= 0:
            raise TimeoutError(f"no {kind!r} frame within {DEADLINE:.0f}s")
        msg = await c.receive_json_from(timeout=left)
        if msg.get("kind") == PING:
            continue
        assert msg["kind"] == kind, msg
        return msg


async def _no_more_events(c: Any, window: float = 0.5) -> None:
    """Assert *c* sends no state-change frame for *window* seconds.

    Pings are allowed through: a keep-alive is not a second transition, and
    a slow runner must not fail "exactly once" on one.

    🔥 The check PEEKS (`receive_nothing`) and only reads a frame that is
    ALREADY queued. `WebsocketCommunicator.receive_output()` CANCELS the
    application when a timed read finds nothing ("it should have sent
    something"), and a cancelled consumer never runs `disconnect()` --
    replacing this peek with a timed read leaves every consumer it checked
    in `live_consumers()`.
    """
    loop = asyncio.get_running_loop()
    end = loop.time() + window
    while True:
        left = end - loop.time()
        if left <= 0:
            return
        if await c.receive_nothing(timeout=left):
            return
        # a frame IS queued: this read cannot time out, so it cannot
        # cancel the application
        msg = await c.receive_json_from(timeout=DEADLINE)
        assert msg.get("kind") == PING, msg


async def _receive_all(comms: List[Any], kind: str) -> List[Dict[str, Any]]:
    """Wait until EVERY communicator has received one frame of *kind*.

    The waits run CONCURRENTLY: one deadline covers the whole fan-out, so
    a subscriber late in the queue never eats the next subscriber's budget
    (the old code awaited them one by one with a 10 s timeout each).
    """

    async def one(c: Any) -> Dict[str, Any]:
        return await _next_frame(c, kind)

    tasks = [asyncio.ensure_future(one(c)) for c in comms]
    try:
        return list(await asyncio.gather(*tasks))
    finally:
        # a failure in one wait must not leave the others running under
        # the teardown that follows
        for t in tasks:
            t.cancel()


def _user(name: str, group: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(name, password="p", is_staff=True)
    for codename in ("view_expense", "change_expense"):
        u.user_permissions.add(Permission.objects.get(codename=codename))
    u.groups.add(Group.objects.get_or_create(name=group)[0])
    return U.objects.get(pk=u.pk)


@pytest.fixture
def people(transactional_db: Any) -> Dict[str, Any]:
    return {"legal": _user("lena", LEGAL), "finance": _user("fin", FINANCE)}


def _threads(fns: List[Any]) -> List[str]:
    errors: List[str] = []
    lock = threading.Lock()

    def run(fn: Any) -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - reported
            with lock:
                errors.append(repr(exc)[:200])
        finally:
            connections.close_all()

    ts = [threading.Thread(target=run, args=(fn,)) for fn in fns]
    for t in ts:
        t.start()
    for t in ts:
        t.join(600)
    return errors


def _submit(n: int) -> List[int]:
    pks = [
        Expense.objects.create(title=f"e{i}", amount="10.00").pk
        for i in range(n)
    ]
    for pk in pks:
        Expense.objects.get(pk=pk).send("SUBMIT")
    return pks


def _api(user: Any) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


# -----------------------------------------------------------------------------
# 1. two hundred API clients approving, every request sent twice
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_two_hundred_api_clients_with_idempotent_retries(people: Any):
    pks = _submit(N)
    seen: Dict[str, List[Any]] = {"first": [], "replay": []}
    lock = threading.Lock()

    def approve(role: str, route: str) -> Any:
        def go() -> None:
            c = _api(people[role])
            for pk in pks:
                key = uuid.uuid4().hex
                a = c.post(
                    f"/api/expenses/{pk}/{route}/",
                    {},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )
                b = c.post(
                    f"/api/expenses/{pk}/{route}/",
                    {},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )
                with lock:
                    seen["first"].append((a.status_code, a.json()))
                    seen["replay"].append((b.status_code, b.json()))

        return go

    t0 = time.perf_counter()
    assert (
        _threads(
            [
                approve("legal", "legal-approve"),
                approve("finance", "finance-approve"),
            ]
        )
        == []
    )
    took = time.perf_counter() - t0
    bad = [(s, b) for s, b in seen["first"] if s != 200]
    assert bad == [], bad[:3]
    assert sum(1 for _, b in seen["first"] if b.get("changed")) == 2 * N
    for (sa, ba), (sb, bb) in zip(seen["first"], seen["replay"]):
        assert sb == 200, (sb, bb, ba)
        assert bb.get("duplicate") is True, bb
        assert bb["state"] == ba["state"]  # the ORIGINAL body, not a new run
    assert (
        Expense.objects.filter(pk__in=pks)
        .filter(statechart_state="approval.approved")
        .count()
        == N
    )
    # exactly one transition row per role per expense: no double effects
    e = Expense.objects.get(pk=pks[0])
    kinds = [r.event for r in e.history.all() if r.disposition == "transition"]
    assert kinds.count("LEGAL_APPROVE") == 1
    assert kinds.count("FINANCE_APPROVE") == 1
    assert took < 300, took


# -----------------------------------------------------------------------------
# 2. the status matrix per role
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_status_matrix_per_role_and_generic_send_agrees(people: Any):
    [pk] = _submit(1)
    url = f"/api/expenses/{pk}"
    anon = APIClient()
    assert anon.post(
        f"{url}/legal-approve/", {}, format="json"
    ).status_code in (401, 403)
    fin, leg = _api(people["finance"]), _api(people["legal"])
    assert (
        fin.post(f"{url}/legal-approve/", {}, format="json").status_code == 403
    )
    r = fin.post(f"{url}/send/", {"type": "LEGAL_APPROVE"}, format="json")
    assert r.status_code == 403  # the generic route agrees
    assert (
        fin.post(f"{url}/no-such-event/", {}, format="json").status_code == 404
    )
    r = fin.post(f"{url}/send/", {"type": "NO_SUCH_EVENT"}, format="json")
    assert r.status_code in (404, 409, 422), r.status_code
    # a reserved payload key is refused, never silently applied (X0.7)
    r = leg.post(f"{url}/legal-approve/", {"priority": True}, format="json")
    assert r.status_code == 422, (r.status_code, r.content[:200])
    r = leg.post(f"{url}/legal-approve/", {}, format="json")
    assert r.status_code == 200 and r.json()["changed"] is True
    # again: the region has left `pending` -- no transition; the API
    # says so without a 5xx and without a second audit transition
    r = leg.post(f"{url}/legal-approve/", {}, format="json")
    assert r.status_code in (200, 409), r.status_code
    assert r.json().get("changed") is False
    r = fin.post(f"{url}/finance-approve/", {}, format="json")
    assert r.status_code == 200
    body = leg.get(f"{url}/").json()["statechart"]
    # the serializer field renders the XState `value` form ("approved")
    # and the full ids in `state_ids`
    assert body["state"] == "approved"
    assert body["state_ids"] == ["approval.approved"]
    assert body["available_events"] == []
    # a finished machine refuses everything with a 409, never a 500; the
    # per-event route takes the PAYLOAD only (a `reason` there is the
    # reserved audit key -> 422), the generic route carries the reason
    r = leg.post(f"{url}/reject/", {}, format="json")
    assert r.status_code in (403, 409), (r.status_code, r.content[:200])
    r = leg.post(
        f"{url}/send/",
        {"type": "REJECT"},
        format="json",
        HTTP_X_XSM_REASON="late",
    )
    assert r.status_code in (403, 409), (r.status_code, r.content[:200])
    # ...and on a live expense the header's reason lands in the audit row
    [pk2] = _submit(1)
    r = leg.post(
        f"/api/expenses/{pk2}/reject/",
        {},
        format="json",
        HTTP_X_XSM_REASON="duplicate claim",
    )
    assert r.status_code == 200, (r.status_code, r.content[:200])
    assert (
        Expense.objects.get(pk=pk2).history.last().reason == "duplicate claim"
    )
    # history is paginated / permission-gated and lists the transitions
    r = leg.get(f"{url}/history/")
    assert r.status_code == 200
    rows = r.json()
    rows = rows["results"] if isinstance(rows, dict) else rows
    assert [x["event"] for x in rows if x["disposition"] == "transition"][
        :3
    ] == ["SUBMIT", "LEGAL_APPROVE", "FINANCE_APPROVE"]


# -----------------------------------------------------------------------------
# 3. the OpenAPI schema
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_openapi_schema_has_every_event_and_is_valid(people: Any) -> None:
    schema = (
        _api(people["legal"])
        .get("/api/schema/", HTTP_ACCEPT="application/json")
        .json()
    )
    paths = schema["paths"]
    for route in ("legal-approve", "finance-approve", "reject", "submit"):
        assert f"/api/expenses/{{id}}/{route}/" in paths, route
        op = paths[f"/api/expenses/{{id}}/{route}/"]["post"]
        codes = set(op["responses"])
        assert {"200", "403", "409"} <= codes, (route, codes)
    for extra in ("send", "events", "history"):
        assert f"/api/expenses/{{id}}/{extra}/" in paths, extra
    validator = pytest.importorskip("openapi_spec_validator")
    validator.validate(schema)


# -----------------------------------------------------------------------------
# 4. a hundred WebSocket subscribers on one expense
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_hundred_subscribers_receive_each_transition_once(people: Any):
    [pk] = _submit(1)
    app = URLRouter(websocket_urlpatterns)
    before = live_consumers()

    async def go() -> Dict[str, Any]:
        comms: List[Any] = []
        try:
            for _ in range(100):
                c = WebsocketCommunicator(app, f"/ws/expenses/{pk}/")
                c.scope["user"] = people["legal"]
                ok, _ = await c.connect(timeout=DEADLINE)
                # 🧹 Register it BEFORE the snapshot read: a consumer whose
                #    connect succeeded is already in `_LIVE`, so if the read
                #    below fails the teardown must still disconnect it --
                #    otherwise the next test's baseline cannot see the leak.
                comms.append(c)
                assert ok
                snap = await c.receive_json_from(timeout=DEADLINE)
                assert snap["kind"] == "snapshot"
            assert live_consumers() == before + 100
            # one subscriber disconnects mid-way (a closed laptop)
            await comms[50].disconnect(timeout=DEADLINE)
            del comms[50]
            # a transition sent through ONE socket
            await comms[0].send_json_to({"type": "LEGAL_APPROVE"})
            receipt = await _next_frame(comms[0], "receipt")
            assert receipt["changed"] is True
            got_ws = await _receive_all(comms, "transition")
            for msg in got_ws:
                assert msg["state"]["review"]["legal"] == "approved", msg
            # 🔥 a transition made through the REST API must reach them too
            await asyncio.to_thread(
                lambda: _api(people["finance"]).post(
                    f"/api/expenses/{pk}/finance-approve/", {}, format="json"
                )
            )
            got_api = await _receive_all(comms, "transition")
            for msg in got_api:
                assert msg["state"] == "approved", msg
            # nothing else is queued: exactly once each
            for c in comms[:5]:
                await _no_more_events(c)
            return {"ws": len(got_ws), "api": len(got_api)}
        finally:
            # 🧹 #591: teardown is DETERMINISTIC even when an assertion
            #    above failed. Otherwise every subscriber stays in the
            #    process-global `_LIVE` registry, and the NEXT test's
            #    `live_consumers()` assertion reports THIS test's leak as
            #    its own (main #591: 99 consumers, "assert 99 == 0" in
            #    the anonymous-socket test). `disconnect()` awaits each
            #    consumer's own teardown, so the registry is clean when it
            #    returns.
            await asyncio.gather(
                *(c.disconnect(timeout=DEADLINE) for c in comms),
                return_exceptions=True,
            )

    counts = asyncio.run(go())
    assert counts == {"ws": 99, "api": 99}, counts
    assert live_consumers() == before


# -----------------------------------------------------------------------------
# 5. auth and origin
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_anonymous_unauthorised_and_cross_origin_sockets_are_refused(
    people: Any,
) -> None:
    from django.contrib.auth.models import AnonymousUser

    [pk] = _submit(1)
    app = URLRouter(websocket_urlpatterns)
    before = live_consumers()

    async def go() -> None:
        # 📝 #591: keep every communicator so the teardown below runs even
        #    when an assertion fails -- a refused socket must leave nothing
        #    registered, and neither may a failing test.
        comms: List[Any] = []
        try:
            c = WebsocketCommunicator(app, f"/ws/expenses/{pk}/")
            comms.append(c)
            c.scope["user"] = AnonymousUser()
            ok, code = await c.connect(timeout=DEADLINE)
            assert not ok and code == 1008, (ok, code)
            # a user with no view permission on expenses
            U = get_user_model()
            nobody = await asyncio.to_thread(
                lambda: U.objects.create_user("nobody", password="p")
            )
            c = WebsocketCommunicator(app, f"/ws/expenses/{pk}/")
            comms.append(c)
            c.scope["user"] = nobody
            ok, code = await c.connect(timeout=DEADLINE)
            assert not ok and code == 1008, (ok, code)
            # a missing expense
            c = WebsocketCommunicator(app, "/ws/expenses/999999/")
            comms.append(c)
            c.scope["user"] = people["legal"]
            ok, code = await c.connect(timeout=DEADLINE)
            assert not ok and code == 1008
            # the real ASGI stack refuses a cross-origin handshake
            from config.asgi import application

            c = WebsocketCommunicator(
                application,
                f"/ws/expenses/{pk}/",
                headers=[
                    (b"origin", b"https://evil.example"),
                    (b"host", b"testserver"),
                ],
            )
            comms.append(c)
            ok, code = await c.connect(timeout=DEADLINE)
            assert not ok, (ok, code)
        finally:
            for c in comms:
                try:
                    await c.disconnect(timeout=DEADLINE)
                except Exception:  # noqa: BLE001 - already failing
                    pass

    asyncio.run(go())
    # 📝 #591: compare against THIS test's baseline, not an absolute 0 --
    #    a leak another test left behind (main #591: 99 consumers, because
    #    a timed-out neighbour never disconnected) is not this test's.
    assert live_consumers() == before, "a refused socket was left registered"


# -----------------------------------------------------------------------------
# 6. a real daphne
# -----------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.parametrize("server", ["uvicorn", "daphne"])
def test_asgi_server_end_to_end(tmp_path: Path, server: str) -> None:
    """The example's `config.asgi:application` under a REAL ASGI server.

    📝 daphne on Windows: an authenticated DRF request never returns (the
    twisted/asyncio reactor sits idle; uvicorn serves the same app fine,
    and so does daphne on Linux) -- not this library's doing, so that
    cell is skipped on win32 and documented in the example README.
    """
    if server == "daphne" and sys.platform == "win32":
        pytest.skip("daphne + Windows: authenticated requests stall")
    pytest.importorskip(server)
    httpx = pytest.importorskip("httpx")
    websockets = pytest.importorskip("websockets")
    port = _free_port()
    db = tmp_path / "daphne.sqlite3"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [
                str(EXAMPLE),
                str(EXAMPLE.parents[2] / "src"),
                os.environ.get("PYTHONPATH", ""),
            ]
        ).rstrip(os.pathsep),
        "PYTHONUTF8": "1",
        "APPROVALS_DB": str(db),
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }
    env.pop("DATABASE_URL", None)
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, "manage.py", *a],
        cwd=str(EXAMPLE),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run("migrate", "-v0").returncode == 0
    seed = (
        "from django.contrib.auth import get_user_model;"
        "from django.contrib.auth.models import Group, Permission;"
        "from approvals.models import Expense;"
        "U=get_user_model();"
        "u=U.objects.create_user('lena', password='p', is_staff=True);"
        "u.user_permissions.add(*Permission.objects.filter("
        "codename__in=['view_expense','change_expense']));"
        "u.groups.add(Group.objects.get_or_create(name='legal')[0]);"
        "e=Expense.objects.create(title='Desk', amount='300.00');"
        "e.send('SUBMIT'); print(e.pk)"
    )
    r = run("shell", "-c", seed)
    assert r.returncode == 0, r.stderr[-1500:]
    pk = int(r.stdout.strip().splitlines()[-1])
    argv = (
        ["-m", "daphne", "-b", "127.0.0.1", "-p", str(port)]
        if server == "daphne"
        else ["-m", "uvicorn", "--host", "127.0.0.1", "--port", str(port)]
    )
    log = open(tmp_path / "server.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, *argv, "config.asgi:application"],
        cwd=str(EXAMPLE),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    def server_log() -> str:
        log.flush()
        return (tmp_path / "server.log").read_text("utf-8", "replace")[-3000:]

    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.fail(server_log())
            try:
                if (
                    httpx.get(base + "/admin/login/", timeout=2).status_code
                    == 200
                ):
                    break
            except Exception:  # noqa: BLE001 - not up yet
                time.sleep(0.3)
        else:
            pytest.fail(f"{server} did not come up")
        with httpx.Client(base_url=base, follow_redirects=True) as c:
            page = c.get("/admin/login/").text
            import re

            token = re.search(
                r'name="csrfmiddlewaretoken" value="([^"]+)"', page
            )
            assert token
            r = c.post(
                "/admin/login/",
                data={
                    "username": "lena",
                    "password": "p",
                    "csrfmiddlewaretoken": token.group(1),
                    "next": "/admin/",
                },
                headers={"Referer": base + "/admin/login/"},
            )
            assert r.status_code == 200, r.status_code
            cookies = {k: v for k, v in c.cookies.items()}
            assert "sessionid" in cookies, (sorted(cookies), r.text[:300])

            async def ws_then_api() -> Dict[str, Any]:
                headers = {
                    "Cookie": "; ".join(
                        f"{k}={v}" for k, v in cookies.items()
                    ),
                    "Origin": base,
                }
                async with websockets.connect(
                    f"ws://127.0.0.1:{port}/ws/expenses/{pk}/",
                    additional_headers=headers,
                ) as ws:
                    snap = json.loads(await asyncio.wait_for(ws.recv(), 10))
                    assert snap["kind"] == "snapshot"
                    # approve through the REST API while the socket listens
                    csrf = cookies.get("csrftoken", "")
                    rr = await asyncio.to_thread(
                        lambda: c.post(
                            f"/api/expenses/{pk}/legal-approve/",
                            json={},
                            headers={
                                "X-CSRFToken": csrf,
                                "Referer": base + "/",
                            },
                        )
                    )
                    assert rr.status_code == 200, (
                        rr.status_code,
                        rr.text[:300],
                    )
                    pushed = json.loads(await asyncio.wait_for(ws.recv(), 15))
                    return {"api": rr.status_code, "pushed": pushed}

            try:
                out = asyncio.run(ws_then_api())
            except Exception as exc:  # noqa: BLE001 - show the server side
                pytest.fail(f"{exc!r} -- server log: {server_log()}")
        assert out["api"] == 200, out
        assert out["pushed"]["kind"] == "transition", out
        assert out["pushed"]["state"]["review"]["legal"] == "approved"
    finally:
        proc.kill()
        proc.wait(timeout=10)
        log.close()


# -----------------------------------------------------------------------------
# 7. the scope user AuthMiddlewareStack really hands over is a lazy proxy
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_lazy_scope_user_survives_a_push(people: Any) -> None:
    """🔥 under `AuthMiddlewareStack` `scope["user"]` is a `SimpleLazyObject`;
    the per-push re-authorisation reloaded it via `type(user)._default_
    manager` -- which the proxy class lacks -- and closed EVERY subscriber
    with 1008 on the first transition. The communicator tests set a
    concrete user and never saw it; a real daphne/uvicorn did."""
    from channels.auth import UserLazyObject

    [pk] = _submit(1)
    app = URLRouter(websocket_urlpatterns)
    # what `AuthMiddlewareStack` puts in the scope: a lazy proxy whose
    # `_wrapped` the middleware has populated (so attribute access needs
    # no query), but whose TYPE is the proxy class
    lazy = UserLazyObject()
    lazy._wrapped = get_user_model().objects.get(pk=people["legal"].pk)

    async def go() -> Any:
        c = WebsocketCommunicator(app, f"/ws/expenses/{pk}/")
        c.scope["user"] = lazy
        try:
            ok, _ = await c.connect(timeout=DEADLINE)
            assert ok
            snap = await c.receive_json_from(timeout=DEADLINE)
            assert snap["kind"] == "snapshot"
            await asyncio.to_thread(
                lambda: Expense.objects.get(pk=pk).send(
                    "LEGAL_APPROVE", actor=people["legal"]
                )
            )
            return await _next_frame(c, "transition")
        finally:
            await c.disconnect(timeout=DEADLINE)

    msg = asyncio.run(go())
    assert msg["kind"] == "transition", msg
