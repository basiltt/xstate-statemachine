# examples/integrations/flask_wizard/app.py
# -----------------------------------------------------------------------------
# 🧙 A 4-step onboarding wizard: one statechart per browser session
# -----------------------------------------------------------------------------
# 🏛️ What you are looking at:
#    * The wizard's position is a statechart, not a `step` integer. NEXT /
#      BACK / SUBMIT are events; the chart decides what is legal (you
#      cannot SUBMIT from step 1, and step 1 needs a name and an email).
#    * Each browser gets its own machine: the key comes from the session
#      (`session.setdefault("wizard_id", ...)`), so two clients never see
#      each other's wizard.
#    * Storage is switchable by env: `SessionStore` (default: the snapshot
#      rides in the signed cookie, hard 3 KiB cap) or `SQLiteStore`
#      (`WIZARD_STORE=sqlite`, server-side, no size worry).
#    * Pages are server-rendered Jinja; every write is a POST followed by a
#      redirect (PRG). CSRF is on when Flask-WTF is installed.
#
#    Run:  flask --app app run          (Flask finds `create_app`)
#          flask --app app xsm inspect wizard
# -----------------------------------------------------------------------------
"""Flask onboarding wizard over `xstate_statemachine.contrib.flask`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.flask import (
    SessionStore,
    SessionStoreTooLargeError,
    XState,
    allow_all,
)
from xstate_statemachine.exceptions import ConflictError
from xstate_statemachine.persistence import PessimisticLock, SQLiteStore

HERE = Path(__file__).resolve().parent
MACHINE_JSON = HERE / "machine.json"
CONFIG: Dict[str, Any] = json.loads(MACHINE_JSON.read_text("utf-8"))
PLANS = ("free", "team", "enterprise")
#: Which fields each step's NEXT carries (anything else is dropped).
FIELDS = {
    "account": ("name", "email"),
    "profile": ("company", "bio"),
    "plan": ("plan",),
}


# -----------------------------------------------------------------------------
# 🧠 Logic: actions copy a step's fields into context; guards validate
# -----------------------------------------------------------------------------
def _copy(ctx: Dict[str, Any], e: Any, keys: Any) -> None:
    for k in keys:
        ctx[k] = str(e.payload.get(k, "")).strip()


def save_account(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    _copy(ctx, e, FIELDS["account"])


def save_profile(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    _copy(ctx, e, FIELDS["profile"])


def save_plan(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    _copy(ctx, e, FIELDS["plan"])


def has_account(ctx: Dict[str, Any], e: Any) -> bool:
    name = str(e.payload.get("name", "")).strip()
    return bool(name) and "@" in str(e.payload.get("email", ""))


def valid_plan(ctx: Dict[str, Any], e: Any) -> bool:
    return e.payload.get("plan") in PLANS


LOGIC = MachineLogic(
    actions={
        "saveAccount": save_account,
        "saveProfile": save_profile,
        "savePlan": save_plan,
    },
    guards={"hasAccount": has_account, "validPlan": valid_plan},
)
MACHINE = create_machine(CONFIG, logic=LOGIC, strict_config=True)


def wizard_key() -> str:
    """One wizard per browser session."""
    return str(session.setdefault("wizard_id", uuid4().hex))


# 📝 Module-level extension + registration; `init_app` binds per app, so
#    the application-factory pattern is safe.
xsm = XState()
xsm.register(
    "wizard",
    MACHINE,
    key=wizard_key,
    # 🔒 The key comes from the caller's own signed session, so a browser
    #    can only ever reach its own wizard; there is nothing else to check.
    authorize=allow_all,
    context_serializer=lambda ctx: dict(ctx),
    source=str(MACHINE_JSON),
)


def make_store(settings: Mapping[str, Any]) -> Any:
    """`SessionStore` by default; `SQLiteStore` when WIZARD_STORE=sqlite."""
    if settings.get("WIZARD_STORE", "session") == "sqlite":
        return SQLiteStore(settings.get("WIZARD_DB", "wizard.db"))
    return SessionStore()


def _enable_csrf(app: Flask) -> bool:
    """Flask-WTF CSRF when importable (soft dependency)."""
    try:
        from flask_wtf.csrf import CSRFProtect
    except ImportError:  # pragma: no cover - exercised without flask-wtf
        return False
    CSRFProtect(app)
    return True


def create_app(config: Optional[Mapping[str, Any]] = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("WIZARD_SECRET_KEY", "dev-only-change-me"),
        WIZARD_STORE=os.environ.get("WIZARD_STORE", "session"),
        WIZARD_DB=os.environ.get("WIZARD_DB", str(HERE / "wizard.db")),
    )
    app.config.update(config or {})
    app.config["CSRF_ENABLED"] = _enable_csrf(app)
    store = make_store(app.config)
    # 🔒 #285 battle: a double-click (two POSTs in flight on ONE wizard)
    #    under the default optimistic lock makes the second lose with
    #    ConflictError. The SQLite store can serialise writers per key
    #    instead; the cookie store has one writer by construction.
    lock = PessimisticLock() if isinstance(store, SQLiteStore) else None
    xsm.init_app(app, store=store, lock=lock)
    _routes(app)
    return app


def _routes(app: Flask) -> None:
    @app.get("/")
    def show() -> Any:
        # 💡 A read: `peek` never saves (and `act` refuses GET anyway).
        body = g.xsm.peek("wizard", wizard_key())
        step = body["state"].split(".")[-1]
        return render_template(
            f"{step}.html",
            ctx=body.get("context", {}),
            step=step,
            plans=PLANS,
        )

    @app.post("/<any(next, back, submit):action>")
    def step(action: str) -> Any:
        # 🛡️ #285 battle: every form names the step it was rendered FOR.
        #    A double-click or the browser's Back button re-posts a form
        #    for a step the wizard has already left; applying it would
        #    push the wizard a step further with empty answers (NEXT is
        #    legal from most steps). The check runs INSIDE `act()`, against
        #    the state under the lock -- a `peek` before it would let two
        #    simultaneous clicks both pass and the second apply anyway.
        sent_for = request.form.get("step")
        seen = {"here": "", "receipt": None}
        try:
            with g.xsm.act("wizard") as w:
                here = sorted(w.current_state_ids)[0].split(".")[-1]
                seen["here"] = here
                if sent_for and sent_for != here:
                    g.xsm.skip_save()  # leaves the block; nothing saved
                fields = {
                    k: request.form.get(k, "") for k in FIELDS.get(here, ())
                }
                seen["receipt"] = w.send(action.upper(), wait=True, **fields)
        except SessionStoreTooLargeError:
            # 🔥 Nothing was saved: `act` writes only on a clean exit.
            return (
                render_template("too_large.html", step=seen["here"]),
                413,
            )
        except ConflictError:
            # 🔁 another request on THIS wizard won the race (a
            #    double-click under the cookie store, two tabs). Nothing
            #    was saved; show the page as it is now instead of a 500.
            flash("That step was already submitted; here is where you are.")
            return redirect(url_for("show"))
        receipt = seen["receipt"]
        if receipt is None:  # the stale form was skipped
            flash("That step was already submitted; here is where you are.")
            return redirect(url_for("show"))
        if not receipt.changed:
            flash("Please check the highlighted fields.")
        return redirect(url_for("show"))

    @app.post("/restart")
    def restart() -> Any:
        # 📝 clear() also drops the old snapshot the SessionStore kept in
        #    the cookie, so restarting never grows the cookie.
        session.clear()
        return redirect(url_for("show"))
