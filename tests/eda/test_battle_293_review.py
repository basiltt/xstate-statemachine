# tests/eda/test_battle_293_review.py
"""#293 independent review -- regressions for what it found.

* **C1** a parseable-but-deep envelope could neither be processed nor
  dead-lettered (`redact` recursed out) and was redelivered forever;
* **H1** an `xsm_outbox` table created by 0.11.0 lacked the lease
  columns: `SQLAlchemyOutboxStore` adds them (or names the migration);
* **H2** the SQLAlchemy claim is the guard on every dialect -- two relays
  on one SQLAlchemy/SQLite outbox never publish a row twice;
* **M1** `release()` runs even when `mark_sent` raises;
* **L4** `NaN` / `Infinity` are not JSON.
"""

from __future__ import annotations

import json
import threading
from typing import Any, List

import pytest

from xstate_statemachine import create_machine
from xstate_statemachine.eda import (
    MAX_DATA_DEPTH,
    Envelope,
    EnvelopeCorruptError,
    InboundDispatcher,
    MemoryOutboxStore,
    OutboxRelay,
)
from xstate_statemachine.persistence import MemoryStore

CFG = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


def _deep(n: int) -> Any:
    out: Any = {"x": 1}
    for _ in range(n):
        out = [out]
    return out


# -----------------------------------------------------------------------------
# C1
# -----------------------------------------------------------------------------
def test_deep_but_parseable_envelope_is_corrupt_not_a_loop() -> None:
    """A 700-deep payload parses (the C decoder manages ~950) but every
    later consumer -- `redact`, the dead-letter writer -- recursed out,
    so it was neither processed nor recorded: redelivered forever. It is
    refused at DECODE now, which every adapter maps to `corrupt`."""
    text = json.dumps(
        {
            "specversion": "1.0",
            "id": "deep-1",
            "type": "xsm.m.GO",
            "source": "s",
            "subject": "k",
            "data": _deep(700),
        }
    )
    with pytest.raises(EnvelopeCorruptError, match="nested deeper"):
        Envelope.from_json(text)
    # and the fake broker (a real wire) dead-letters it like one
    from xstate_statemachine.eda import SyncFakeBrokerAdapter

    broker = SyncFakeBrokerAdapter()
    disp = InboundDispatcher(MemoryStore(), {"xsm.m.GO": create_machine(CFG)})
    with pytest.raises(EnvelopeCorruptError):
        broker.deliver("t", Envelope.from_dict(json.loads(text)))
    assert disp.run_once_sync(broker, "t").outcomes == []


def test_depth_limit_is_the_documented_constant() -> None:
    Envelope.new(
        type="t", subject="k", data=_deep(MAX_DATA_DEPTH - 1)
    ).validate()
    with pytest.raises(EnvelopeCorruptError, match="nested deeper"):
        Envelope.new(
            type="t", subject="k", data=_deep(MAX_DATA_DEPTH + 1)
        ).validate()


def test_unknown_type_with_unredactable_payload_still_leaves_a_record() -> (
    None
):
    """Even when the redactor cannot walk the payload, a record with the
    envelope's id / type / source is written -- never a silent requeue."""
    from xstate_statemachine.eda import dispatcher as mod

    env = Envelope.new(type="nobody.Handles", subject="k", data={"a": 1})
    disp = InboundDispatcher(MemoryStore(), {})
    real = mod.redact

    def boom(_value: Any) -> Any:
        raise RecursionError("maximum recursion depth exceeded")

    mod.redact = boom  # type: ignore[assignment]
    try:
        out = disp.handle(env).outcomes[0][1]
    finally:
        mod.redact = real  # type: ignore[assignment]
    assert out == "dead_lettered:unknown_event"
    [rec] = disp.dead_letters.list()
    assert rec.envelope["id"] == env.id
    assert rec.event["payload"] == {"_unrecorded": "RecursionError"}


# -----------------------------------------------------------------------------
# L4
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_nan_and_infinity_are_not_json(literal: str) -> None:
    text = (
        '{"specversion":"1.0","id":"1","type":"t","source":"s",'
        '"data":{"v":' + literal + "}}"
    )
    with pytest.raises(EnvelopeCorruptError, match="not JSON"):
        Envelope.from_json(text)


# -----------------------------------------------------------------------------
# M1
# -----------------------------------------------------------------------------
def test_release_runs_even_when_mark_sent_raises() -> None:
    class Store(MemoryOutboxStore):
        def mark_sent(self, seqs: List[int]) -> int:
            raise RuntimeError("database is locked")

    class Broker:
        def __init__(self) -> None:
            self.n = 0

        def publish(self, topic: str, env: Envelope) -> None:
            self.n += 1
            if self.n == 2:
                raise ConnectionError("gone")

    store = Store()
    for i in range(3):
        store.add("t", Envelope.new(type="t", subject=str(i), data={}))
    relay = OutboxRelay(store, Broker(), owner="r1", lease_s=600)
    with pytest.raises(ConnectionError):  # the ORIGINAL error, not the mark's
        relay.relay_once_sync()
    # rows 2 and 3 were handed back: another relay takes them NOW
    other = OutboxRelay(store, Broker(), owner="r2", lease_s=600)
    taken = other._take()
    assert sorted(r.seq for r in taken) == [2, 3], taken


# -----------------------------------------------------------------------------
# H1 / H2 (SQLAlchemy)
# -----------------------------------------------------------------------------
sa = pytest.importorskip("sqlalchemy")


def _sa_store(url: str, metadata: Any = None) -> Any:
    from sqlalchemy.orm import sessionmaker

    from xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

    eng = sa.create_engine(url)
    kw = {"metadata": metadata} if metadata is not None else {}
    return eng, SQLAlchemyStore(sessionmaker(eng), **kw)


def test_old_outbox_table_gains_the_lease_columns(tmp_path: Any) -> None:
    from xstate_statemachine.contrib.sqlalchemy import SQLAlchemyOutboxStore
    from xstate_statemachine.persistence.store import StoreError

    url = f"sqlite:///{tmp_path / 'o.db'}"
    eng = sa.create_engine(url)
    with eng.begin() as conn:  # a 0.11.0 table: no claimed_* columns
        conn.execute(
            sa.text(
                "CREATE TABLE xsm_outbox (seq INTEGER PRIMARY KEY, id TEXT,"
                " topic TEXT, subject TEXT, envelope TEXT, created_at REAL,"
                " sent_at REAL)"
            )
        )
    eng.dispose()
    # migrations are the team's: refuse and name the migration
    eng, store = _sa_store(url)
    with pytest.raises(StoreError, match="claimed_by"):
        SQLAlchemyOutboxStore(store, create_table=False)
    # create_table=True adds them, and the relay works
    outbox = SQLAlchemyOutboxStore(store)
    cols = {c["name"] for c in sa.inspect(eng).get_columns("xsm_outbox")}
    assert {"claimed_by", "claimed_until"} <= cols
    outbox.add("t", Envelope.new(type="t", subject="s", data={}))
    sent: List[Envelope] = []

    class B:
        def publish(self, topic: str, env: Envelope) -> None:
            sent.append(env)

    assert OutboxRelay(outbox, B()).relay_once_sync() == 1
    eng.dispose()


def test_two_relays_on_one_sqlalchemy_sqlite_outbox_publish_once(
    tmp_path: Any,
) -> None:
    from xstate_statemachine.contrib.sqlalchemy import SQLAlchemyOutboxStore

    url = f"sqlite:///{tmp_path / 'o.db'}"
    eng, store = _sa_store(url)
    outbox = SQLAlchemyOutboxStore(store)
    for i in range(200):
        outbox.add("t", Envelope.new(type="t", subject=str(i), data={}))
    published: List[str] = []
    lock = threading.Lock()

    class B:
        def publish(self, topic: str, env: Envelope) -> None:
            with lock:
                published.append(env.id)

    errors: List[str] = []

    def run(owner: str) -> None:
        relay = OutboxRelay(outbox, B(), batch=7, owner=owner, lease_s=600)
        try:
            for _ in range(60):
                if relay.relay_once_sync() == 0 and not outbox.pending(
                    limit=1
                ):
                    return
        except Exception as exc:  # noqa: BLE001 - reported
            errors.append(repr(exc)[:200])

    ts = [threading.Thread(target=run, args=(f"r{i}",)) for i in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    assert errors == [], errors
    assert outbox.count(pending_only=True) == 0
    assert len(published) == 200
    assert len(set(published)) == 200, "a row was published twice"
    eng.dispose()
