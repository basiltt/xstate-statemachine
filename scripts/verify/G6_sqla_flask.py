"""Verification for G6: #284 D5 [sqlalchemy] (parts 1-2) + #285 D6 [flask].

`python scripts/verify/G6_sqla_flask.py`.

Windows-safe (no heredocs, no /tmp: every database lives in a
``tempfile.mkdtemp()`` directory). Runs the two contrib test folders and
the store contract suite, then end-to-end checks straight from the issues:

* #284: 8 threads x 50 `send_with_retry` on ONE mapped row -> 400, with
  `ConflictError` observed; `in_state()`; audit row + state in one flush;
  `SQLAlchemyStore` round trip + `forget()` cascade; async store on
  aiosqlite; deadlines fired by `DueTimerScanner` through `ModelStore`.
* #285: the issue's blueprint one-liner; two apps / two stores; a
  session wizard; `SessionStore` refusing oversize; `flask xsm inspect
  --plain` parity; 20 concurrent requests on one `SQLiteStore` key.

Prints ``ALL OK``.
"""

import asyncio
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path.insert(0, str(ROOT / "src"))
TMP = pathlib.Path(tempfile.mkdtemp(prefix="xsm-g6-"))


def step(name: str) -> None:
    print(f"\n== {name}")


def run_tests() -> None:
    step("pytest contrib/sqlalchemy + contrib/flask + store contract")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/sqlalchemy",
            "tests/contrib/flask",
            "tests/persistence/test_store_contract.py",
            "tests/contrib/test_extras_matrix.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, "tests failed"


# -----------------------------------------------------------------------------
# #284
# -----------------------------------------------------------------------------
def sqlalchemy_mixin() -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import (
        DeclarativeBase,
        Mapped,
        Session,
        mapped_column,
        sessionmaker,
    )

    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.sqlalchemy import (
        StatechartMixin,
        StatechartType,
        send_with_retry,
        xsm_sqlalchemy_ddl,
    )
    from xstate_statemachine.exceptions import ConflictError
    from xstate_statemachine.persistence import DueTimerScanner

    def inc(i: Any, c: Any, e: Any, a: Any) -> None:
        c["n"] = c["n"] + 1

    m = create_machine(
        {
            "id": "c",
            "initial": "s",
            "context": {"n": 0},
            "states": {
                "s": {"on": {"T": {"actions": "inc"}, "WAIT": "w"}},
                "w": {"after": {"60000": "late"}},
                "late": {"type": "final"},
            },
        },
        logic=MachineLogic(actions={"inc": inc}),
    )

    class Base(DeclarativeBase):
        pass

    class Counter(StatechartMixin, Base):
        __tablename__ = "counters"
        __xsm_machine__ = m
        __xsm_audit__ = True
        id: Mapped[int] = mapped_column(primary_key=True)
        statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
            StatechartType, nullable=True
        )
        __mapper_args__ = StatechartMixin.optimistic()

    eng = create_engine(
        f"sqlite:///{TMP / 'counters.db'}", connect_args={"timeout": 30}
    )
    xsm_sqlalchemy_ddl(Base.metadata).create_all(eng)
    with Session(eng) as s:
        c = Counter()
        s.add(c)
        s.commit()
        cid = c.id

    step("#284: 8 threads x 50 send_with_retry on one row")
    conflicts: List[int] = []
    real = Counter.send

    def counting(self: Any, *a: Any, **k: Any) -> Any:
        try:
            return real(self, *a, **k)
        except ConflictError:
            conflicts.append(1)
            raise

    Counter.send = counting  # type: ignore[method-assign]

    def w() -> None:
        for _ in range(50):
            with Session(eng) as s:
                send_with_retry(
                    s.get(Counter, cid), "T", session=s, retries=10_000
                )
                s.commit()

    ts = [threading.Thread(target=w) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    Counter.send = real  # type: ignore[method-assign]
    with Session(eng) as s:
        row = s.get(Counter, cid)
        assert row.machine.context["n"] == 400, row.machine.context
        assert row.statechart_version == 401
    assert conflicts, "no ConflictError observed"
    print(f"   400 increments, {len(conflicts)} conflicts retried")

    step("#284: in_state(), audit rows, deadlines -> DueTimerScanner")
    with Session(eng) as s:
        s.get(Counter, cid).send("WAIT", session=s, actor="ops")
        s.commit()
        q = select(Counter.id).where(Counter.in_state("c.w"))
        assert s.scalars(q).all() == [cid]
    t = Base.metadata.tables["xsm_transitions"]
    with Session(eng) as s:
        n_audit = len(s.execute(select(t.c.seq)).all())
    assert n_audit == 401, n_audit
    store = Counter.statechart_store(sessionmaker(eng))
    sc = DueTimerScanner(store, lambda k: m)
    assert sc.run_once(now=time.time() + 61) == 1
    with Session(eng) as s:
        assert s.get(Counter, cid).state == "c.late"
    eng.dispose()


def sqlalchemy_stores() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.sqlalchemy import (
        AsyncSQLAlchemyStore,
        SQLAlchemyLog,
        SQLAlchemyStore,
    )
    from xstate_statemachine.persistence import (
        AuditPlugin,
        apersisted,
        persisted,
    )

    def inc(i: Any, c: Any, e: Any, a: Any) -> None:
        c["n"] = c["n"] + 1

    m = create_machine(
        {
            "id": "o",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"GO": {"actions": "inc"}}}},
        },
        logic=MachineLogic(actions={"inc": inc}),
    )

    step("#284: SQLAlchemyStore + SQLAlchemyLog, forget() cascades")
    eng = create_engine(f"sqlite:///{TMP / 'store.db'}")
    store = SQLAlchemyStore(sessionmaker(eng))
    log = SQLAlchemyLog(store)
    for _ in range(3):
        with persisted(store, "k", m, plugins=[AuditPlugin(log)]) as i:
            i.send("GO")
    assert store.load("k").version == 3 and len(log.read("k")) == 3
    counts = store.forget("k")
    assert counts["snapshots"] == 1 and counts["log_entries"] == 3, counts
    assert store.health()["ok"]
    eng.dispose()

    step("#284: AsyncSQLAlchemyStore on aiosqlite")
    try:
        import aiosqlite  # noqa: F401
    except ImportError:
        print("   (aiosqlite not installed: skipped)")
        return
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def go() -> int:
        aeng = create_async_engine(f"sqlite+aiosqlite:///{TMP / 'a.db'}")
        astore = AsyncSQLAlchemyStore(async_sessionmaker(aeng))
        try:
            for _ in range(2):
                async with apersisted(astore, "k", m) as i:
                    await i.send("GO", wait=True)
            rec = await astore.load("k")
            return int(json.loads(rec.snapshot)["context"]["n"])
        finally:
            await aeng.dispose()

    assert asyncio.run(go()) == 2


# -----------------------------------------------------------------------------
# #285
# -----------------------------------------------------------------------------
ORDER = {
    "id": "order",
    "initial": "cart",
    "context": {"items": 0},
    "states": {
        "cart": {"on": {"ADD": {"actions": "add"}, "CHECKOUT": "paying"}},
        "paying": {"on": {"PAY": "paid"}},
        "paid": {"type": "final"},
    },
}


def _order() -> Any:
    from xstate_statemachine import MachineLogic, create_machine

    def add(i: Any, c: Any, e: Any, a: Any) -> None:
        c["items"] = c["items"] + 1

    return create_machine(ORDER, logic=MachineLogic(actions={"add": add}))


def flask_checks() -> None:
    from flask import Flask, request, session

    from xstate_statemachine.contrib.flask import (
        SessionStore,
        SessionStoreTooLargeError,
        XState,
        allow_all,
        create_statechart_blueprint,
        receipt_response,
    )
    from xstate_statemachine.persistence import MemoryStore, SQLiteStore

    step("#285: blueprint one-liner (issue verification script)")
    xsm = XState()
    xsm.register("order", _order(), authorize=allow_all, source=ORDER)
    app = Flask(__name__)
    xsm.init_app(app, store=MemoryStore())
    app.register_blueprint(
        create_statechart_blueprint(xsm, "order", url_prefix="/orders")
    )
    c = app.test_client()
    r = c.post("/orders/1/send", json={"type": "CHECKOUT"})
    print("  ", r.status_code, r.get_json()["state"])
    assert r.status_code == 200 and r.get_json()["state"] == "paying"
    assert c.get("/orders/1/events").get_json()["available"] == ["PAY"]
    assert c.get("/orders/1/send").status_code == 405

    step("#285: two apps, two stores, one extension")
    other = Flask(__name__)
    s2 = MemoryStore()
    xsm.init_app(other, store=s2)
    other.register_blueprint(
        create_statechart_blueprint(xsm, "order", url_prefix="/orders")
    )
    assert other.test_client().get("/orders/1").get_json()["state"] == "cart"
    assert s2.list_keys() == []

    step("#285: flask xsm inspect order --plain == xsm inspect --plain")
    path = TMP / "order.json"
    path.write_text(json.dumps(ORDER), encoding="utf-8")
    app.extensions["xstate"].reg("order").source = path
    via_flask = app.test_cli_runner().invoke(
        args=["xsm", "inspect", "order", "--plain"]
    )
    assert via_flask.exit_code == 0, via_flask.output
    direct = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "--plain",
            "inspect",
            str(path),
        ],
        cwd=str(ROOT / "src"),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert direct.returncode == 0, direct.stderr
    assert via_flask.output.strip() == direct.stdout.strip()

    step("#285: session wizard + SessionStore size limit")
    from xstate_statemachine import MachineLogic, create_machine

    def keep(i: Any, c: Any, e: Any, a: Any) -> None:
        c["answers"] = dict(e.payload)

    wiz = XState()
    wiz.register(
        "wizard",
        create_machine(
            {
                "id": "wizard",
                "initial": "a",
                "context": {"answers": {}},
                "states": {
                    "a": {"on": {"NEXT": {"target": "b", "actions": "keep"}}},
                    "b": {"type": "final"},
                },
            },
            logic=MachineLogic(actions={"keep": keep}),
        ),
        key=lambda: session.setdefault("wid", "w-" + str(id(session))),
        authorize=allow_all,
    )
    wapp = Flask(__name__)
    wapp.config["SECRET_KEY"] = "verify"
    wiz.init_app(wapp, store=SessionStore(max_snapshot_bytes=2048))

    @wapp.post("/next")
    def nxt() -> Any:
        with wiz.act("wizard") as w:
            return receipt_response(
                w, w.send("NEXT", wait=True, **request.get_json())
            )

    a, b = wapp.test_client(), wapp.test_client()
    assert a.post("/next", json={}).get_json()["state"] == "b"
    wapp.testing = True
    try:
        b.post("/next", json={"blob": "x" * 5000})
    except SessionStoreTooLargeError as exc:
        print("   refused:", str(exc)[:60], "...")
    else:
        raise AssertionError("oversize snapshot was accepted")

    step("#285: 20 concurrent requests on one SQLiteStore key")
    store = SQLiteStore(TMP / "flask.db")
    capp = Flask(__name__)
    cx = XState()
    cx.register("order", _order(), authorize=allow_all)
    cx.init_app(capp, store=store)
    capp.register_blueprint(create_statechart_blueprint(cx, "order", "/o"))

    def worker() -> None:
        cl = capp.test_client()
        for _ in range(500):
            if cl.post("/o/1/send", json={"type": "ADD"}).status_code == 200:
                return
        raise AssertionError("never won")

    ts = [threading.Thread(target=worker) for _ in range(20)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    snap = json.loads(store.load("order.1").snapshot)
    assert snap["context"]["items"] == 20, snap["context"]
    store.close()


def main() -> None:
    run_tests()
    sqlalchemy_mixin()
    sqlalchemy_stores()
    flask_checks()
    print("\nALL OK")


if __name__ == "__main__":
    main()
