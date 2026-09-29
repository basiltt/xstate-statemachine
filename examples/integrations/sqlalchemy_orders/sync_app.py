# examples/integrations/sqlalchemy_orders/sync_app.py
# -----------------------------------------------------------------------------
# 🛒 Sync variant: the statechart lives ON the `orders` row
# -----------------------------------------------------------------------------
# 🏛️ What you are looking at:
#    * `order.send(...)` restores a `SyncInterpreter` from the row, applies
#      the event and FLUSHES snapshot + state columns + deadline index +
#      audit row together. The caller commits.
#    * `send_with_retry` rolls back and re-applies on `ConflictError`
#      (the `version_id_col` from `StatechartMixin.optimistic()`).
#    * `Order.statechart_store(...)` + `DueTimerScanner` fire the 15-minute
#      payment timeout for orders nobody touches -- run exactly ONE
#      scanner process (`python sync_app.py scan`).
#
#    Run:  alembic upgrade head          (creates orders.db)
#          python sync_app.py demo
#          python sync_app.py scan --at-offset 901
# -----------------------------------------------------------------------------
"""Order lifecycle on SQLAlchemy 2.0, synchronous ORM."""

from __future__ import annotations

import argparse
import os
import time
from typing import Any, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from logic import order_machine
from models import Base, Order
from xstate_statemachine.contrib.sqlalchemy import send_with_retry
from xstate_statemachine.persistence import DueTimerScanner

DEFAULT_URL = "sqlite:///orders.db"


def make_engine(url: Optional[str] = None) -> Any:
    """An engine for *url* (default ``$ORDERS_DB_URL`` or ``orders.db``)."""
    url = url or os.environ.get("ORDERS_DB_URL", DEFAULT_URL)
    kw = {"connect_args": {"timeout": 30}} if url.startswith("sqlite") else {}
    return create_engine(url, **kw)


def create_order(engine: Any, customer: str) -> int:
    with Session(engine) as s:
        order = Order(customer=customer)
        s.add(order)
        s.commit()
        return order.id


def send(engine: Any, order_id: int, event: str, **payload: Any) -> Any:
    """Apply one event with optimistic retry; returns the `Receipt`."""
    with Session(engine) as s:
        order = s.get(Order, order_id)
        if order is None:
            raise KeyError(order_id)
        receipt = send_with_retry(order, event, session=s, **payload)
        s.commit()
        return receipt


def state_of(engine: Any, order_id: int) -> str:
    with Session(engine) as s:
        order = s.get(Order, order_id)
        return (order.state or "") if order is not None else ""


def orders_in(engine: Any, *state_ids: str) -> List[int]:
    """SQL query on the denormalised state column (no snapshot parsing)."""
    with Session(engine) as s:
        q = select(Order.id).where(Order.in_state(*state_ids))
        return list(s.scalars(q.order_by(Order.id)))


def scanner(engine: Any) -> DueTimerScanner:
    """The ONE timer process: wakes rows whose `after` deadline passed."""
    store = Order.statechart_store(sessionmaker(engine))
    machine = order_machine()
    return DueTimerScanner(store, lambda key: machine)


def demo(engine: Any) -> None:
    a = create_order(engine, "alice")
    send(engine, a, "ADD_ITEM", price_cents=450)
    send(engine, a, "CHECKOUT")
    send(engine, a, "PAY", charge_id="ch_1")
    b = create_order(engine, "bob")
    send(engine, b, "ADD_ITEM", price_cents=1200)
    send(engine, b, "CHECKOUT")
    for oid in (a, b):
        print(f"order {oid}: {state_of(engine, oid)}")
    print("awaiting payment:", orders_in(engine, "order.awaitingPayment"))


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["init", "demo", "scan"])
    p.add_argument("--url", default=None)
    p.add_argument(
        "--at-offset",
        type=float,
        default=0.0,
        help="scan as if this many seconds had passed (demo only)",
    )
    args = p.parse_args(argv)
    engine = make_engine(args.url)
    if args.command == "init":  # 💡 without Alembic: create_all
        Base.metadata.create_all(engine)
    elif args.command == "demo":
        demo(engine)
    else:
        woken = scanner(engine).run_once(now=time.time() + args.at_offset)
        print(f"woke {woken} order(s)")
    engine.dispose()


if __name__ == "__main__":
    main()
