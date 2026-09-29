# examples/integrations/sqlalchemy_orders/async_app.py
# -----------------------------------------------------------------------------
# ⚡ Async variant: `AsyncSQLAlchemyStore` + `apersisted()` on aiosqlite
# -----------------------------------------------------------------------------
# 🏛️ The mixin is a sync-ORM feature, so the async variant keeps orders in
#    the key-value `SQLAlchemyStore` layout instead (table
#    ``xsm_snapshots``, created by the same Alembic migration). Each call is
#    create → act → persist → discard over an async `Interpreter`; a racing
#    writer gets `ConflictError`, which `asend` retries.
#
#    Deadlines are written to the same `xsm_deadlines` index, and the
#    scanner is the SYNC `SQLAlchemyStore` + `DueTimerScanner` over the
#    same database -- one scanner process serves both variants.
#
#    Run:  alembic upgrade head
#          python async_app.py
# -----------------------------------------------------------------------------
"""Order lifecycle on SQLAlchemy 2.0 asyncio."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from logic import order_machine
from xstate_statemachine.contrib.sqlalchemy import (
    AsyncSQLAlchemyStore,
    SQLAlchemyStore,
)
from xstate_statemachine.exceptions import ConflictError
from xstate_statemachine.persistence import DueTimerScanner, apersisted

DEFAULT_PATH = "orders.db"
MACHINE = order_machine()


def make_store(path: Optional[str] = None) -> AsyncSQLAlchemyStore:
    path = path or os.environ.get("ORDERS_DB_PATH", DEFAULT_PATH)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    store = AsyncSQLAlchemyStore(async_sessionmaker(engine))
    store.engine = engine  # type: ignore[attr-defined]
    return store


async def asend(
    store: AsyncSQLAlchemyStore,
    key: str,
    event: str,
    retries: int = 10,
    **payload: Any,
) -> str:
    """Apply one event; retry the whole cycle on a version conflict."""
    for attempt in range(retries + 1):
        try:
            async with apersisted(store, key, MACHINE) as i:
                await i.send(event, wait=True, **payload)
                return ",".join(sorted(i.current_state_ids))
        except ConflictError:
            if attempt == retries:
                raise
            await asyncio.sleep(0.005 * (attempt + 1))
    raise AssertionError("unreachable")  # pragma: no cover


async def astate(store: AsyncSQLAlchemyStore, key: str) -> str:
    async with apersisted(store, key, MACHINE, create_if_missing=False) as i:
        return ",".join(sorted(i.current_state_ids))


def scanner(path: str) -> DueTimerScanner:
    """Sync scanner over the same file (it is "another process")."""
    engine = create_engine(f"sqlite:///{path}")
    store = SQLAlchemyStore(sessionmaker(engine))
    return DueTimerScanner(store, lambda key: MACHINE)


async def demo() -> None:
    store = make_store()
    try:
        await asend(store, "order-1", "ADD_ITEM", price_cents=450)
        await asend(store, "order-1", "CHECKOUT")
        print("order-1:", await asend(store, "order-1", "PAY"))
    finally:
        await store.engine.dispose()  # type: ignore[attr-defined]


if __name__ == "__main__":
    asyncio.run(demo())
