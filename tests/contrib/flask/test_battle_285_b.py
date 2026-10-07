# tests/contrib/flask/test_battle_285_b.py
"""#285 battle, adversary B: the docs and the newcomer path.

Pins what the Flask guide, the API reference and the `xsm new --template
flask` scaffold claim against what the code does:

* the Guarantees box: under the default optimistic lock 50 concurrent
  writers on one key lose with 409 (blueprint) / ``ConflictError`` (plain
  view), never a lost update; with ``PessimisticLock`` all 50 commit;
* ``act()`` in a GET view raises the 405 problem error (a 500 unless the
  app renders it -- the guide says so);
* the CSRF recipe for the JSON blueprint: cookie session + ``X-CSRFToken``;
* ``g.xsm.skip_save`` exists and saves nothing;
* every ``__all__`` name of ``contrib.flask`` / ``contrib.quart`` is in
  ``docs/api/index.md``;
* the scaffold: README / requirements render, file set equals the
  example's both directions (templates/ and tests/ included), and
  ``flask --app app run`` serves from it.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any, List

import pytest

pytest.importorskip("flask")

from flask import Flask, g  # noqa: E402

from xstate_statemachine import MachineLogic, create_machine  # noqa: E402
from xstate_statemachine.contrib.flask import (  # noqa: E402
    HTTPProblemError,
    XState,
    allow_all,
    create_statechart_blueprint,
    problem_response,
    receipt_response,
)
from xstate_statemachine.exceptions import ConflictError  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    MemoryStore,
    PessimisticLock,
    SQLiteStore,
)

ROOT = Path(__file__).resolve().parents[3]
GUIDE = ROOT / "docs" / "_guide" / "integration-flask.md"
API = ROOT / "docs" / "api" / "index.md"
EXAMPLE = ROOT / "examples" / "integrations" / "flask_wizard"
N = 50


def _inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["n"] += 1


COUNTER = create_machine(
    {
        "id": "counter",
        "initial": "on",
        "context": {"n": 0},
        "states": {"on": {"on": {"INC": {"actions": "inc"}}}},
    },
    logic=MachineLogic(actions={"inc": _inc}),
)


def _app(tmp_path: Path, lock: Any = None) -> Any:
    xsm = XState()
    xsm.register("c", COUNTER, authorize=allow_all, context_serializer=dict)
    app = Flask(__name__)
    xsm.init_app(app, store=SQLiteStore(str(tmp_path / "c.db")), lock=lock)
    app.register_blueprint(create_statechart_blueprint(xsm, "c", "/c"))
    conflicts: List[str] = []

    @app.post("/plain/<k>")
    def plain(k: str) -> Any:
        try:
            with xsm.act("c", k) as i:
                return receipt_response(i, i.send("INC", wait=True))
        except ConflictError as exc:
            conflicts.append(type(exc).__name__)
            return problem_response(exc)

    app.conflicts = conflicts  # type: ignore[attr-defined]
    return app, xsm


def _hammer(app: Any, url: str, **kw: Any) -> Counter:
    codes: List[int] = []
    lock = threading.Lock()

    def go() -> None:
        r = app.test_client().post(url, **kw)
        with lock:
            codes.append(r.status_code)

    ts = [threading.Thread(target=go) for _ in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return Counter(codes)


def _n(app: Any, xsm: Any, key: str) -> int:
    with app.test_request_context(method="POST"):
        return int(xsm.peek("c", key)["context"]["n"])


class TestGuarantees:
    @pytest.mark.parametrize("url", ["/c/k/send", "/plain/k"])
    def test_optimistic_losers_get_409_and_nothing_is_lost(
        self, tmp_path: Path, url: str
    ) -> None:
        app, xsm = _app(tmp_path)
        codes = _hammer(app, url, json={"type": "INC"})
        assert set(codes) <= {200, 409}, codes
        assert _n(app, xsm, "k") == codes[200]  # no lost update

    @pytest.mark.parametrize("url", ["/c/k/send", "/plain/k"])
    def test_pessimistic_lock_commits_all_fifty(
        self, tmp_path: Path, url: str
    ) -> None:
        app, xsm = _app(tmp_path, lock=PessimisticLock())
        codes = _hammer(app, url, json={"type": "INC"})
        assert codes == Counter({200: N})
        assert _n(app, xsm, "k") == N

    def test_plain_view_conflict_propagates_as_conflict_error(
        self, tmp_path: Path
    ) -> None:
        """The guide: in your own view `ConflictError` propagates."""
        app, _ = _app(tmp_path)
        _hammer(app, "/plain/k")
        assert app.conflicts and set(app.conflicts) == {"ConflictError"}


class TestActInGet:
    @staticmethod
    def _get_app(handled: bool) -> Any:
        xsm = XState()
        xsm.register("c", COUNTER, authorize=allow_all)
        app = Flask(__name__)
        app.config["PROPAGATE_EXCEPTIONS"] = False
        xsm.init_app(app, store=MemoryStore())
        if handled:
            app.register_error_handler(HTTPProblemError, problem_response)

        @app.get("/v")
        def v() -> Any:
            with xsm.act("c", "1"):
                return "unreachable"

        return app

    def test_act_in_get_is_500_without_a_handler(self) -> None:
        assert self._get_app(False).test_client().get("/v").status_code == 500

    def test_act_in_get_is_405_problem_with_the_handler(self) -> None:
        r = self._get_app(True).test_client().get("/v")
        assert r.status_code == 405
        assert r.mimetype == "application/problem+json"
        assert "Traceback" not in r.get_data(as_text=True)


class TestSkipSave:
    def test_g_xsm_skip_save_saves_nothing(self) -> None:
        xsm = XState()
        xsm.register("c", COUNTER, authorize=allow_all)
        app = Flask(__name__)
        store = MemoryStore()
        xsm.init_app(app, store=store)

        @app.post("/x")
        def x() -> Any:
            with g.xsm.act("c", "1") as i:
                i.send("INC")
                g.xsm.skip_save()
            return "ok"

        assert app.test_client().post("/x").status_code == 200
        assert store.load("c.1") is None


class TestCSRFRecipe:
    def test_header_needs_its_cookie_session(self) -> None:
        pytest.importorskip("flask_wtf")
        from flask_wtf.csrf import CSRFProtect, generate_csrf

        xsm = XState()
        xsm.register("c", COUNTER, authorize=allow_all)
        app = Flask(__name__)
        app.secret_key = "t"
        CSRFProtect(app)
        xsm.init_app(app, store=MemoryStore())
        app.register_blueprint(create_statechart_blueprint(xsm, "c", "/c"))
        app.add_url_rule("/token", "token", generate_csrf)
        b = app.test_client()
        assert b.post("/c/1/send", json={"type": "INC"}).status_code == 400
        tok = b.get("/token").get_data(as_text=True)
        for header in ("X-CSRFToken", "X-CSRF-Token"):
            r = b.post(
                "/c/1/send", json={"type": "INC"}, headers={header: tok}
            )
            assert r.status_code == 200, header
        other = app.test_client()
        r = other.post(
            "/c/1/send", json={"type": "INC"}, headers={"X-CSRFToken": tok}
        )
        assert r.status_code == 400


class TestDocsTruth:
    def test_no_stale_release_phrases(self) -> None:
        text = GUIDE.read_text("utf-8")
        for phrase in ("Not in this release", "arrives with", "planned"):
            assert phrase not in text, phrase

    def test_guide_documents_both_409_patterns(self) -> None:
        text = GUIDE.read_text("utf-8")
        assert "lock=PessimisticLock()" in text
        assert "persisted_retry(" in text
        assert "skip_save" in text

    @pytest.mark.parametrize(
        "mod",
        [
            "xstate_statemachine.contrib.flask",
            "xstate_statemachine.contrib.quart",
        ],
    )
    def test_every_public_name_is_in_the_api_reference(self, mod: str):
        if mod.endswith("quart"):
            pytest.importorskip("quart")
        import importlib

        names = importlib.import_module(mod).__all__
        api = API.read_text("utf-8")
        missing = [n for n in names if f"`{n}" not in api]
        assert not missing, missing
        assert "skip_save" in api


def _scaffold(tmp_path: Path, name: str = "onboard") -> Path:
    from xstate_statemachine.cli.commands import new as N_

    out = tmp_path / "proj"
    N_.scaffold("flask", out, name=name)
    return out


def _files(root: Path) -> set:
    return {
        f.relative_to(root).as_posix()
        for f in root.rglob("*")
        if f.is_file()
        and "__pycache__" not in f.parts
        and not f.name.endswith((".pyc", ".db"))
    }


class TestScaffold:
    def test_file_set_equals_the_example_both_ways(self, tmp_path: Path):
        out = _scaffold(tmp_path)
        got = _files(out) - {"requirements.txt"}
        assert got == _files(EXAMPLE), got ^ _files(EXAMPLE)
        assert any(f.startswith("templates/") for f in got)
        assert any(f.startswith("tests/") for f in got)

    def test_readme_and_requirements_render(self, tmp_path: Path) -> None:
        from xstate_statemachine import __version__

        out = _scaffold(tmp_path)
        readme = (out / "README.md").read_text("utf-8")
        req = (out / "requirements.txt").read_text("utf-8")
        assert readme.startswith("# onboard -- ")
        assert "${" not in readme + req
        assert f"xstate-statemachine[flask]>={__version__}" in req

    def test_flask_run_from_the_scaffold(self, tmp_path: Path) -> None:
        httpx = pytest.importorskip("httpx")
        out = _scaffold(tmp_path)
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
        except OSError as exc:  # pragma: no cover
            pytest.skip(f"cannot bind: {exc}")
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        env.pop("WIZARD_STORE", None)
        proc = subprocess.Popen(
            [sys.executable, "-m", "flask", "--app", "app", "run"]
            + ["--port", str(port)],
            cwd=out,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    r = httpx.get(f"http://127.0.0.1:{port}/", timeout=2)
                    break
                except httpx.TransportError:
                    if proc.poll() is not None or time.monotonic() > deadline:
                        pytest.fail("scaffold never served")
                    time.sleep(0.2)
            assert r.status_code == 200
            assert re.search(r'data-step="account"', r.text)
        finally:
            proc.kill()
            proc.wait(timeout=10)


class TestCliTranscript:
    def test_cli_md_flask_xsm_transcript_is_real(self) -> None:
        import importlib
        import sys as _sys

        text = (ROOT / "docs" / "_guide" / "cli.md").read_text("utf-8")
        m = re.search(
            r"<!-- flask-xsm-transcript -->\s*```text\n(.*?)```", text, re.S
        )
        assert m, "cli.md lost its flask xsm transcript"
        _sys.path.insert(0, str(EXAMPLE))
        try:
            wizard = importlib.import_module("app")
            app = wizard.create_app({"TESTING": True})
            res = app.test_cli_runner().invoke(
                args=["xsm", "inspect", "wizard", "--plain"]
            )
        finally:
            _sys.path.remove(str(EXAMPLE))
            _sys.modules.pop("app", None)
        assert res.exit_code == 0, res.output
        lines = [ln.rstrip() for ln in res.output.splitlines()]
        for want in m.group(1).splitlines():
            assert want.rstrip() in lines, want
