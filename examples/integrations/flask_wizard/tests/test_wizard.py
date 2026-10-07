# examples/integrations/flask_wizard/tests/test_wizard.py
"""The flask_wizard example through Flask's test client.

Plain pytest -- no ``[testing]`` fixtures. Two clients advance independent
wizards, BACK/NEXT are events the chart validates, an oversize context is
refused with nothing saved, the `SQLiteStore` variant is selected by
config, CSRF is enforced when Flask-WTF is installed, and ``flask xsm
inspect wizard`` works.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest

import app as wizard

STEP = re.compile(r'data-step="(\w+)"')


def make(tmp_path: Path, **cfg: Any) -> Any:
    base: Dict[str, Any] = {"TESTING": True, "WTF_CSRF_ENABLED": False}
    base.update(cfg)
    if base.get("WIZARD_STORE") in ("sqlite", "sqlalchemy"):
        base.setdefault("WIZARD_DB", str(tmp_path / "wizard.db"))
    return wizard.create_app(base)


def step_of(client: Any) -> str:
    m = STEP.search(client.get("/").get_data(as_text=True))
    assert m, "page has no data-step marker"
    return m.group(1)


def post(client: Any, action: str, **form: str) -> Any:
    r = client.post(f"/{action}", data=form)
    assert r.status_code == 302, r.get_data(as_text=True)[:500]
    return r


ACCOUNT = {"name": "Ada", "email": "ada@example.com"}


@pytest.fixture(params=["session", "sqlite"])
def app(request: Any, tmp_path: Path) -> Any:
    return make(tmp_path, WIZARD_STORE=request.param)


class TestNavigation:
    def test_full_walk_forward_and_back(self, app: Any) -> None:
        c = app.test_client()
        assert step_of(c) == "account"
        post(c, "next", **ACCOUNT)
        assert step_of(c) == "profile"
        post(c, "next", company="Analytical Engines", bio="Numbers")
        assert step_of(c) == "plan"
        post(c, "back")
        assert step_of(c) == "profile"
        # 💡 going back keeps what was typed: the page is pre-filled
        assert "Analytical Engines" in c.get("/").get_data(as_text=True)
        post(c, "next", company="Analytical Engines", bio="Numbers")
        post(c, "next", plan="team")
        assert step_of(c) == "confirm"
        post(c, "submit")
        page = c.get("/").get_data(as_text=True)
        assert 'data-step="done"' in page and "team" in page

    def test_guards_refuse_bad_input_and_illegal_events(self, app):
        c = app.test_client()
        post(c, "next", name="", email="nope")  # guard: hasAccount
        page = c.get("/").get_data(as_text=True)  # flash shows once
        assert "check the highlighted fields" in page
        assert step_of(c) == "account"
        post(c, "submit")  # SUBMIT is not an event of step 1
        assert step_of(c) == "account"
        post(c, "next", **ACCOUNT)
        post(c, "next")
        post(c, "next", plan="platinum")  # guard: validPlan
        assert step_of(c) == "plan"

    def test_two_clients_advance_independent_wizards(self, app: Any):
        a, b = app.test_client(), app.test_client()
        post(a, "next", **ACCOUNT)
        post(a, "next")
        assert step_of(a) == "plan"
        assert step_of(b) == "account"
        post(b, "next", name="Bob", email="bob@example.com")
        assert (step_of(a), step_of(b)) == ("plan", "profile")
        assert "Ada" not in b.get("/").get_data(as_text=True)

    def test_restart_starts_a_new_wizard(self, app: Any) -> None:
        c = app.test_client()
        post(c, "next", **ACCOUNT)
        post(c, "restart")
        assert step_of(c) == "account"

    def test_reads_never_change_state(self, app: Any) -> None:
        c = app.test_client()
        assert c.get("/next").status_code == 405


class TestStores:
    def test_store_switch(self, tmp_path: Path) -> None:
        from xstate_statemachine.contrib.flask import SessionStore
        from xstate_statemachine.persistence import SQLiteStore

        assert isinstance(wizard.make_store({}), SessionStore)
        s = wizard.make_store(
            {"WIZARD_STORE": "sqlite", "WIZARD_DB": str(tmp_path / "w.db")}
        )
        assert isinstance(s, SQLiteStore)
        s.close()

    def test_oversize_context_is_refused_in_the_cookie(self, tmp_path):
        c = make(tmp_path).test_client()
        post(c, "next", **ACCOUNT)
        r = c.post("/next", data={"company": "x", "bio": "y" * 5000})
        assert r.status_code == 413
        assert "Nothing was saved" in r.get_data(as_text=True)
        assert step_of(c) == "profile"  # the old, small snapshot remains

    def test_sqlite_variant_takes_the_same_input(self, tmp_path: Path):
        c = make(tmp_path, WIZARD_STORE="sqlite").test_client()
        post(c, "next", **ACCOUNT)
        post(c, "next", company="x", bio="y" * 5000)
        assert step_of(c) == "plan"

    def test_sqlalchemy_variant_takes_the_same_input(self, tmp_path: Path):
        pytest.importorskip("sqlalchemy")
        from xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

        app = make(tmp_path, WIZARD_STORE="sqlalchemy")
        assert isinstance(app.extensions["xstate"].store, SQLAlchemyStore)
        c = app.test_client()
        post(c, "next", **ACCOUNT)
        post(c, "next", company="x", bio="y" * 5000)
        assert step_of(c) == "plan"

    def test_unknown_store_is_refused(self) -> None:
        with pytest.raises(ValueError, match="WIZARD_STORE"):
            wizard.make_store({"WIZARD_STORE": "postgres"})


class TestCSRF:
    def test_post_without_token_is_rejected(self, tmp_path: Path) -> None:
        pytest.importorskip("flask_wtf")
        c = make(tmp_path, WTF_CSRF_ENABLED=True).test_client()
        assert c.post("/next", data=ACCOUNT).status_code == 400
        page = c.get("/").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page)
        assert token, "form must carry the CSRF token"
        r = c.post("/next", data={**ACCOUNT, "csrf_token": token.group(1)})
        assert r.status_code == 302
        assert step_of(c) == "profile"


class TestCLI:
    def test_flask_xsm_inspect_wizard(self, tmp_path: Path) -> None:
        res = (
            make(tmp_path)
            .test_cli_runner()
            .invoke(args=["xsm", "inspect", "wizard", "--plain"])
        )
        assert res.exit_code == 0, res.output
        for step in ("account", "profile", "plan", "confirm", "done"):
            assert step in res.output
