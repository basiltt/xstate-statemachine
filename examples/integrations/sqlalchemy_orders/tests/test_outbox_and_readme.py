# examples/integrations/sqlalchemy_orders/tests/test_outbox_and_readme.py
"""#284 battle (adversary B): the outbox in the example, and the README's
commands run LITERALLY in a subprocess from a temp copy of the example.

Postgres: the README's ``ORDERS_DB_URL=postgresql+psycopg://...`` path is
exercised on a throwaway testcontainer when ``XSM_CONTAINERS=1`` (or on
``DATABASE_URL``); skipped otherwise.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest
from sqlalchemy.orm import Session

import sync_app
from models import Base, Order
from xstate_statemachine.eda import SyncFakeBrokerAdapter

EXAMPLE = Path(__file__).resolve().parents[1]
SRC = EXAMPLE.parents[2] / "src"
NESTED = "XSM_EXAMPLE_README_RUN"
literal = pytest.mark.skipif(
    os.environ.get(NESTED) == "1", reason="inside the README run already"
)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Any]:
    eng = sync_app.make_engine(f"sqlite:///{(tmp_path / 'o.db').as_posix()}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _checked_out(eng: Any, cents: int = 450) -> int:
    oid = sync_app.create_order(eng, "ann")
    sync_app.send(eng, oid, "ADD_ITEM", price_cents=cents)
    sync_app.send(eng, oid, "CHECKOUT")
    return oid


# -----------------------------------------------------------------------------
# 📤 the transactional outbox
# -----------------------------------------------------------------------------
class TestOutbox:
    def test_pay_writes_order_paid_and_relay_drains_it(self, engine: Any):
        oid = _checked_out(engine)
        assert sync_app.outbox(engine).count() == 0  # only PAY publishes
        sync_app.send(engine, oid, "PAY", charge_id="ch_9")
        [rec] = sync_app.outbox(engine).pending()
        assert rec.topic == "orders" and rec.envelope.type == "order.paid"
        assert rec.envelope.data == {"total_cents": 450, "charge_id": "ch_9"}
        broker = SyncFakeBrokerAdapter()
        assert sync_app.relay(engine, broker) == 1
        assert sync_app.relay(engine, broker) == 0  # marked sent
        [d] = list(broker.subscribe("orders", timeout=0))
        assert d.envelope.id == rec.envelope.id

    def test_rolled_back_pay_leaves_no_event(self, engine: Any) -> None:
        from xstate_statemachine.eda import OutboxPlugin

        oid = _checked_out(engine)
        plugin = OutboxPlugin(sync_app.outbox(engine), topic="orders")
        with Session(engine) as s:
            s.get(Order, oid).send("PAY", session=s, plugins=[plugin])
            s.rollback()
        assert sync_app.state_of(engine, oid) == "order.awaitingPayment"
        assert sync_app.outbox(engine).count() == 0


# -----------------------------------------------------------------------------
# 📖 the README, literally
# -----------------------------------------------------------------------------
def _readme_commands() -> List[str]:
    text = (EXAMPLE / "README.md").read_text("utf-8")
    block = re.search(r"## Run it\s+```bash\n(.*?)```", text, re.S)
    assert block, "README lost its Run it block"
    cmds = []
    for line in block.group(1).splitlines():
        cmd = line.split("#", 1)[0].strip()
        if cmd and not cmd.startswith(("pip ", "cd ")):
            cmds.append(cmd)
    return cmds


def _run(cmd: str, cwd: Path, env: Dict[str, str]) -> str:
    argv = cmd.split()
    if argv[0] == "alembic":
        argv = [sys.executable, "-m", "alembic", *argv[1:]]
    elif argv[0] == "python":
        argv = [sys.executable, *argv[1:]]
    p = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )
    out = p.stdout + p.stderr
    assert p.returncode == 0, f"{cmd!r} failed:\n{out}"
    return out


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "sqlalchemy_orders"
    shutil.copytree(
        EXAMPLE,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.db", ".pytest*"),
    )
    return dst


def _env(**extra: str) -> Dict[str, str]:
    env = dict(os.environ)
    for k in ("ORDERS_DB_URL", "ORDERS_DB_PATH"):
        env.pop(k, None)
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), env.get("PYTHONPATH", "")])
    env["PYTHONUTF8"] = "1"
    env[NESTED] = "1"  # the README's own `pytest tests` must not recurse
    env.update(extra)
    return env


def _check_outputs(outs: Dict[str, str]) -> None:
    assert "order 1: order.paid" in outs["python sync_app.py demo"]
    assert "woke 1 order(s)" in outs["python sync_app.py scan --at-offset 901"]
    relay = outs["python sync_app.py relay"]
    assert "publish orders: order.paid" in relay
    assert "relayed 1 event(s)" in relay
    assert "No new upgrade operations detected" in outs["alembic check"]


@literal
@pytest.mark.timeout(600)
def test_readme_commands_run_literally_on_sqlite(tmp_path: Path) -> None:
    pytest.importorskip("alembic")
    pytest.importorskip("aiosqlite")
    cmds = _readme_commands()
    assert "python sync_app.py relay" in cmds
    work = _copy(tmp_path)
    outs = {c: _run(c, work, _env()) for c in cmds}
    _check_outputs(outs)
    assert (work / "orders.db").exists()


def _pg_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL", "")
    return url if url.startswith("postgresql") else None


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    url = _pg_url()
    if url:
        yield url
        return
    if os.environ.get("XSM_CONTAINERS") != "1":
        pytest.skip("no Postgres: set DATABASE_URL or XSM_CONTAINERS=1")
    tc = pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("psycopg")
    with tc.PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@literal
@pytest.mark.timeout(600)
def test_readme_postgres_instructions(tmp_path: Path, pg_url: str) -> None:
    """``ORDERS_DB_URL=postgresql+psycopg://...`` for the sync app and
    Alembic: upgrade, demo, scan, relay, check, downgrade."""
    pytest.importorskip("alembic")
    work = _copy(tmp_path)
    env = _env(ORDERS_DB_URL=pg_url)
    cmds = [c for c in _readme_commands() if "async_app" not in c]
    cmds = [c for c in cmds if "pytest" not in c]
    _run("alembic downgrade base", work, env)
    try:
        outs = {c: _run(c, work, env) for c in cmds}
        _check_outputs(outs)
    finally:
        _run("alembic downgrade base", work, env)
