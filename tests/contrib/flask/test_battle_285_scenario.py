# tests/contrib/flask/test_battle_285_scenario.py
"""#285 battle: the onboarding wizard as browsers actually use it.

`examples/integrations/flask_wizard` is the host. Real users double-click
Submit, open the form in two tabs, press Back, resend stale cookies, and
hit the app through a real WSGI server -- not through `test_client()`:

* **a double-click on one wizard** (SQLite store, 50 concurrent POSTs on
  ONE browser's key) -- no request may die with a 500: the losers of the
  optimistic race are answered like a stale form (re-rendered current
  step), the state advances exactly one step, nothing is lost;
* **fifty browsers at once**, each walking all four steps through its
  own cookie -- every wizard ends in `done` with ITS answers; no
  cross-talk (the store is one SQLite file);
* **two apps from one extension** (the application-factory pattern) --
  different stores, same registration, zero cross-talk;
* **back-button replay** -- re-POSTing an earlier step's form after the
  wizard moved on is a no-op the chart refuses, never a corrupted
  context; a replayed STALE session cookie (`SessionStore`) rewinds
  only that browser, as documented (the guide says: use a server-side
  store for anything that matters) -- pinned so the claim stays true;
* **the cookie cap** -- an oversize answer is 413 and the previous
  step is intact; the cookie never grows past the cap;
* **CSRF** -- with Flask-WTF the forms carry a token and a tokenless
  POST is 400 (nothing saved);
* **a real server** -- `flask --app app run` in a subprocess, driven
  with `httpx` end to end through all four steps, PRG redirects and
  all; `flask --app app xsm inspect wizard --plain` from the CLI;
* **Quart** -- the same wizard chart through the `contrib.quart` shim
  under `asyncio`, two concurrent clients.

Runs on every `[flask]` cell (the real-server test skips without
`flask` on PATH / a free port).
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest

from ..conftest import requires_extra

pytestmark = [requires_extra("flask"), pytest.mark.timeout(300)]
pytest.importorskip("flask")

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples" / "integrations" / "flask_wizard"
STEP = re.compile(r'data-step="(\w+)"')
#: What each step's form posts (a browser sends the hidden `step` too).
ACCOUNT = {"step": "account", "name": "Ada", "email": "ada@example.com"}
PROFILE = {"step": "profile", "company": "Analytical Engines", "bio": "pc"}
PLAN = {"step": "plan", "plan": "team"}
SUBMIT = {"step": "confirm"}


@pytest.fixture
def wizard() -> Iterator[Any]:
    """The example's `app` module, imported from ITS directory and kept
    live for the test; same-named modules of other examples set aside
    (CI's Coverage job runs every example suite in one process)."""
    import importlib

    saved = {k: sys.modules.pop(k) for k in ("app",) if k in sys.modules}
    sys.path.insert(0, str(EXAMPLE))
    try:
        yield importlib.import_module("app")
    finally:
        sys.path.remove(str(EXAMPLE))
        sys.modules.pop("app", None)
        sys.modules.update(saved)


def _make(wizard: Any, tmp_path: Path, **cfg: Any) -> Any:
    base: Dict[str, Any] = {"TESTING": True, "WTF_CSRF_ENABLED": False}
    base.update(cfg)
    if base.get("WIZARD_STORE") == "sqlite":
        base.setdefault("WIZARD_DB", str(tmp_path / "wizard.db"))
    return wizard.create_app(base)


def _step(client: Any) -> str:
    m = STEP.search(client.get("/").get_data(as_text=True))
    assert m, "page has no data-step marker"
    return m.group(1)


def _walk(client: Any) -> None:
    for action, form in (
        ("next", ACCOUNT),
        ("next", PROFILE),
        ("next", PLAN),
        ("submit", SUBMIT),
    ):
        r = client.post(f"/{action}", data=form)
        assert r.status_code == 302, (action, r.status_code)


# -----------------------------------------------------------------------------
# 1. a double-click on one wizard
# -----------------------------------------------------------------------------
def test_double_click_on_one_wizard_never_500s(
    wizard: Any, tmp_path: Path
) -> None:
    app = _make(wizard, tmp_path, WIZARD_STORE="sqlite")
    first = app.test_client()
    first.get("/")
    cookie = first.get_cookie("session").value
    statuses: List[int] = []
    errors: List[str] = []
    lock = threading.Lock()

    def click() -> None:
        try:
            c = app.test_client()
            c.set_cookie("session", cookie)
            r = c.post("/next", data=ACCOUNT)  # the SAME form, 50 times
            with lock:
                statuses.append(r.status_code)
        except Exception as exc:  # noqa: BLE001 - reported below
            with lock:
                errors.append(repr(exc)[:200])

    threads = [threading.Thread(target=click) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 🔥 a raw ConflictError escaping as a 500 (or an exception out of the
    #    test client) is a user-facing crash on a double-click
    assert errors == [], errors[:3]
    assert all(s < 500 for s in statuses), sorted(set(statuses))
    assert statuses.count(302) >= 1
    assert _step(first) == "profile"
    # the single logical step landed exactly once (the account answers)
    with app.test_request_context(
        "/", headers={"Cookie": f"session={cookie}"}
    ):
        app.preprocess_request()
        body = wizard.g.xsm.peek("wizard", wizard.wizard_key())
    assert body["context"]["name"] == "Ada"


# -----------------------------------------------------------------------------
# 2. fifty browsers at once
# -----------------------------------------------------------------------------
def test_fifty_browsers_walk_the_wizard_concurrently(
    wizard: Any, tmp_path: Path
) -> None:
    app = _make(wizard, tmp_path, WIZARD_STORE="sqlite")
    results: Dict[int, Dict[str, Any]] = {}
    errors: List[str] = []
    lock = threading.Lock()

    def browser(n: int) -> None:
        try:
            c = app.test_client()
            c.get("/")
            mine = {**ACCOUNT, "name": f"user{n}", "email": f"u{n}@x.io"}
            for action, form in (
                ("next", mine),
                ("next", {**PROFILE, "company": f"co{n}"}),
                ("next", PLAN),
                ("submit", SUBMIT),
            ):
                r = c.post(f"/{action}", data=form)
                assert r.status_code == 302, (n, action, r.status_code)
            html = c.get("/").get_data(as_text=True)
            with lock:
                results[n] = {
                    "step": STEP.search(html).group(1),  # type: ignore[union-attr]
                    "mine": f"user{n}" in html,
                    "others": bool(re.search(r"user(?!%d\b)\d+" % n, html)),
                }
        except Exception as exc:  # noqa: BLE001 - reported below
            with lock:
                errors.append(f"{n}: {exc!r}"[:200])

    t0 = time.perf_counter()
    threads = [threading.Thread(target=browser, args=(n,)) for n in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    took = time.perf_counter() - t0
    assert errors == [], errors[:3]
    assert len(results) == 50
    assert all(r["step"] == "done" for r in results.values()), results
    assert all(r["mine"] and not r["others"] for r in results.values())
    assert took < 120, took


# -----------------------------------------------------------------------------
# 3. two apps from one extension
# -----------------------------------------------------------------------------
def test_application_factory_two_apps_share_nothing(
    wizard: Any, tmp_path: Path
) -> None:
    a = _make(wizard, tmp_path / "a", WIZARD_STORE="sqlite")
    b = _make(wizard, tmp_path / "b", WIZARD_STORE="sqlite")
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "b").mkdir(exist_ok=True)
    assert a.extensions["xstate"] is not b.extensions["xstate"]
    ca, cb = a.test_client(), b.test_client()
    ca.get("/")
    cookie = ca.get_cookie("session").value
    ca.post("/next", data=ACCOUNT)
    assert _step(ca) == "profile"
    # the same signed cookie on app B (same SECRET_KEY) finds NO wizard
    # there: B's store is another file
    cb.set_cookie("session", cookie)
    assert _step(cb) == "account"
    assert _step(ca) == "profile"


# -----------------------------------------------------------------------------
# 4. back-button replay
# -----------------------------------------------------------------------------
def test_replaying_an_earlier_steps_form_is_refused_not_applied(
    wizard: Any, tmp_path: Path
) -> None:
    app = _make(wizard, tmp_path, WIZARD_STORE="sqlite")
    c = app.test_client()
    c.get("/")
    c.post("/next", data=ACCOUNT)
    c.post("/next", data=PROFILE)
    assert _step(c) == "plan"
    # the browser's Back button re-submits step 1's form (it names step 1)
    r = c.post("/next", data={**ACCOUNT, "name": "Mallory"})
    assert r.status_code == 302
    # 🔥 before the fix the stale form was applied to the CURRENT step:
    #    NEXT from `plan` with no plan -- refused here by the guard, but
    #    from `profile` it would have advanced with EMPTY answers
    assert _step(c) == "plan"
    # and a stale step-2 form after the wizard moved to `plan` must not
    # advance it to `confirm` with empty profile answers either
    r = c.post("/next", data={"step": "account", "name": "x", "email": "y@z"})
    assert r.status_code == 302 and _step(c) == "plan"
    cookie = c.get_cookie("session").value
    with app.test_request_context(
        "/", headers={"Cookie": f"session={cookie}"}
    ):
        app.preprocess_request()
        ctx = wizard.g.xsm.peek("wizard", wizard.wizard_key())["context"]
    assert ctx["name"] == "Ada" and ctx["company"] == PROFILE["company"]


def test_stale_cookie_rewinds_only_that_browser_as_documented(
    wizard: Any, tmp_path: Path
) -> None:
    """`SessionStore`: the guide says a client CAN resend an older cookie
    (use a server-side store for anything that matters). Pin the claim
    and its limit: the rewind touches nothing but this browser."""
    app = _make(wizard, tmp_path)  # SessionStore
    c = app.test_client()
    c.get("/")
    c.post("/next", data=ACCOUNT)
    stale = c.get_cookie("session").value
    c.post("/next", data=PROFILE)
    assert _step(c) == "plan"
    c.set_cookie("session", stale)
    assert _step(c) == "profile"  # rewound -- by design, documented
    other = app.test_client()
    other.get("/")
    assert _step(other) == "account"
    guide = (ROOT / "docs" / "_guide" / "integration-flask.md").read_text(
        "utf-8"
    )
    assert "SessionStore" in guide and "older signed cookie" in guide


# -----------------------------------------------------------------------------
# 5. the cookie cap
# -----------------------------------------------------------------------------
def test_cookie_cap_413_and_the_cookie_never_grows_past_it(
    wizard: Any, tmp_path: Path
) -> None:
    app = _make(wizard, tmp_path)
    c = app.test_client()
    c.get("/")
    c.post("/next", data=ACCOUNT)
    before = c.get_cookie("session").value
    r = c.post(
        "/next", data={"step": "profile", "company": "x", "bio": "y" * 4000}
    )
    assert r.status_code == 413
    assert _step(c) == "profile"
    after = c.get_cookie("session").value
    assert len(after) <= len(before) + 64, (len(before), len(after))
    # a normal answer still works afterwards
    c.post("/next", data=PROFILE)
    assert _step(c) == "plan"


# -----------------------------------------------------------------------------
# 6. CSRF
# -----------------------------------------------------------------------------
def test_csrf_tokenless_post_saves_nothing(wizard: Any, tmp_path: Path):
    pytest.importorskip("flask_wtf")
    app = _make(wizard, tmp_path, WIZARD_STORE="sqlite", WTF_CSRF_ENABLED=True)
    c = app.test_client()
    page = c.get("/").get_data(as_text=True)
    assert c.post("/next", data=ACCOUNT).status_code == 400
    assert _step(c) == "account"
    token = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert token
    r = c.post("/next", data={**ACCOUNT, "csrf_token": token.group(1)})
    assert r.status_code == 302 and _step(c) == "profile"


# -----------------------------------------------------------------------------
# 7. a real server
# -----------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_flask_run_subprocess_end_to_end(tmp_path: Path) -> None:
    httpx = pytest.importorskip("httpx")
    port = _free_port()
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep),
        "PYTHONUTF8": "1",
        "WIZARD_STORE": "sqlite",
        "WIZARD_DB": str(tmp_path / "w.db"),
        "WIZARD_SECRET_KEY": "test-secret",
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "flask",
            "--app",
            "app",
            "run",
            "--port",
            str(port),
            "--no-reload",
        ],
        cwd=str(EXAMPLE),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if httpx.get(base + "/", timeout=2).status_code == 200:
                    break
            except Exception:  # noqa: BLE001 - not up yet
                time.sleep(0.2)
        else:
            out = proc.stdout.read() if proc.stdout else ""
            pytest.fail(f"server did not come up:\n{out[-2000:]}")
        token_re = re.compile(r'name="csrf_token" value="([^"]+)"')
        with httpx.Client(base_url=base, follow_redirects=True) as c:
            page = c.get("/").text
            assert STEP.search(page).group(1) == "account"  # type: ignore[union-attr]
            for action, form in (
                ("next", ACCOUNT),
                ("next", PROFILE),
                ("next", PLAN),
                ("submit", SUBMIT),
            ):
                # a browser sends the form's CSRF token (Flask-WTF is on
                # in a real deployment); without flask-wtf there is none
                m = token_re.search(page)
                data = {**form, **({"csrf_token": m.group(1)} if m else {})}
                r = c.post(f"/{action}", data=data)
                assert r.status_code == 200, (
                    action,
                    r.status_code,
                    r.text[:200],
                )
                page = r.text
            html = c.get("/").text
            assert STEP.search(html).group(1) == "done"  # type: ignore[union-attr]
            # a fresh client (no cookie) is a fresh wizard
            assert (
                STEP.search(httpx.get(base + "/").text).group(1)  # type: ignore[union-attr]
                == "account"
            )
    finally:
        proc.kill()
        proc.wait(timeout=10)
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "flask",
            "--app",
            "app",
            "xsm",
            "inspect",
            "wizard",
            "--plain",
        ],
        cwd=str(EXAMPLE),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stdout[-1000:] + r.stderr[-1000:]
    for step in ("account", "profile", "plan", "confirm", "done"):
        assert step in r.stdout


# -----------------------------------------------------------------------------
# 8. Quart
# -----------------------------------------------------------------------------
def test_quart_shim_two_concurrent_clients(wizard: Any) -> None:
    quart = pytest.importorskip("quart")
    import asyncio

    # 📝 the example imports the INSTALLED package name; the chart it
    #    built must be the same MachineNode class the shim checks against
    from xstate_statemachine.contrib.flask import allow_all
    from xstate_statemachine.contrib.quart import QuartXState as QXState
    from xstate_statemachine.persistence import MemoryStore

    app = quart.Quart(__name__)
    xsm = QXState()
    xsm.init_app(app, store=MemoryStore())
    xsm.register("wizard", wizard.MACHINE, authorize=allow_all)

    @app.post("/<key>/<event>")
    async def send(key: str, event: str) -> Any:
        form = await quart.request.form
        async with xsm.act("wizard", key) as w:
            r = await w.send(event, wait=True, **dict(form))
        return {"state": sorted(w.current_state_ids), "changed": r.changed}

    async def walk(client: Any, key: str, n: int) -> List[str]:
        out = []
        for ev, form in (
            ("NEXT", {"name": f"u{n}", "email": f"u{n}@x.io"}),
            ("NEXT", {"company": "c", "bio": "b"}),
            ("NEXT", PLAN),
            ("SUBMIT", {}),
        ):
            r = await client.post(f"/{key}/{ev}", form=form)
            assert r.status_code == 200
            out.append((await r.get_json())["state"][0])
        return out

    async def main() -> None:
        c = app.test_client()
        a, b = await asyncio.gather(walk(c, "k1", 1), walk(c, "k2", 2))
        assert (
            a
            == b
            == [
                "wizard.profile",
                "wizard.plan",
                "wizard.confirm",
                "wizard.done",
            ]
        )

    asyncio.run(main())
