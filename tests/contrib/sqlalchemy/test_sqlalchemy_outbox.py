# tests/contrib/sqlalchemy/test_sqlalchemy_outbox.py
"""#284 part 3 / #293: `SQLAlchemyOutboxStore` implements the core
`OutboxStore` protocol and shares the `SQLAlchemyStore` transaction: the
outbox row commits with the snapshot, and a FORCED ROLLBACK leaves no row
(and no snapshot)."""

from __future__ import annotations

from typing import Any

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("sqlalchemy")
pytest.importorskip("sqlalchemy")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.sqlalchemy import (  # noqa: E402
    SQLAlchemyOutboxStore,
)
from src.xstate_statemachine.eda import (  # noqa: E402
    Envelope,
    OutboxPlugin,
    OutboxRelay,
    OutboxStore,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.persistence import (  # noqa: E402
    PessimisticLock,
    persisted,
)

CFG = {
    "id": "order",
    "initial": "open",
    "context": {"total": 3},
    "states": {
        "open": {
            "on": {
                "PAY": {
                    "target": "paid",
                    "meta": {
                        "publish": {"type": "order.paid", "data": ["total"]}
                    },
                }
            }
        },
        "paid": {},
    },
}


class TestSQLAlchemyOutbox:
    def test_protocol_and_row_commits_with_the_snapshot(
        self, store: Any
    ) -> None:
        outbox = SQLAlchemyOutboxStore(store)
        assert isinstance(outbox, OutboxStore)
        assert outbox.shares_connection_with is store
        with persisted(
            store,
            "o-1",
            create_machine(CFG),
            lock=PessimisticLock(),
            plugins=[OutboxPlugin(outbox, topic="orders")],
        ) as i:
            i.send("PAY")
        [rec] = outbox.pending()
        assert (rec.topic, rec.envelope.type) == ("orders", "order.paid")
        assert rec.envelope.data == {"total": 3}
        assert store.load("o-1") is not None

    def test_forced_rollback_leaves_no_row(self, store: Any) -> None:
        outbox = SQLAlchemyOutboxStore(store)
        real = outbox.add

        def add_then_fail(topic: str, env: Envelope) -> None:
            real(topic, env)
            raise RuntimeError("forced rollback after the outbox write")

        outbox.add = add_then_fail  # type: ignore[method-assign]
        with pytest.raises(RuntimeError):
            with persisted(
                store,
                "o-1",
                create_machine(CFG),
                lock=PessimisticLock(),
                plugins=[OutboxPlugin(outbox)],
            ) as i:
                i.send("PAY")
        assert outbox.count() == 0
        assert store.load("o-1") is None

    def test_explicit_transaction_rollback(self, store: Any) -> None:
        outbox = SQLAlchemyOutboxStore(store)
        with pytest.raises(ValueError):
            with store.transaction():
                outbox.add("t", Envelope.new(type="x"))
                raise ValueError("rollback")
        assert outbox.count() == 0

    def test_relay(self, store: Any) -> None:
        outbox = SQLAlchemyOutboxStore(store)
        outbox.add("t", Envelope.new(type="a"))
        outbox.add("t", Envelope.new(type="b"))
        broker = SyncFakeBrokerAdapter()
        assert OutboxRelay(outbox, broker).relay_once_sync() == 2
        assert [e.type for e in broker.published] == ["a", "b"]
        assert outbox.count(pending_only=True) == 0
        assert outbox.count() == 2
        assert outbox.mark_sent([]) == 0
        # idempotent construction on an existing table
        SQLAlchemyOutboxStore(store)

    def test_requires_a_sqlalchemy_store(self) -> None:
        with pytest.raises(TypeError):
            SQLAlchemyOutboxStore(object())  # type: ignore[arg-type]


def test_a_new_snapshot_rolls_back_with_its_lease(store: Any) -> None:
    """🐛 Regression (#293): on pysqlite the create-only INSERT ran in a
    SAVEPOINT that opened SQLite's transaction itself, so its RELEASE
    committed -- a NEW snapshot survived a failure later in the same
    `PessimisticLock` block. No outbox involved."""
    with pytest.raises(RuntimeError):
        with store.lock("fresh"):
            store.save("fresh", '{"x": 1}', expected_version=0)
            raise RuntimeError("fail after the save")
    assert store.load("fresh") is None
