# examples/integrations/sqlalchemy_orders/models.py
# -----------------------------------------------------------------------------
# 🗃️ The mapped `Order` row: a statechart column + optimistic locking
# -----------------------------------------------------------------------------
# 🏛️ `Base.metadata` is what Alembic's `env.py` imports as
#    `target_metadata`. `xsm_sqlalchemy_ddl` adds the extra's own tables
#    (deadlines, audit log, inbox, locks, schema, snapshots) to it, so the
#    committed migration creates them and autogenerate sees no diff.
# -----------------------------------------------------------------------------
"""Declarative models for the sqlalchemy_orders example."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from logic import order_machine
from xstate_statemachine.contrib.sqlalchemy import (
    StatechartMixin,
    StatechartType,
    xsm_sqlalchemy_ddl,
)


class Base(DeclarativeBase):
    pass


class Order(StatechartMixin, Base):
    """One customer order; its lifecycle lives in ``statechart``."""

    __tablename__ = "orders"
    __xsm_machine__ = order_machine()
    __xsm_audit__ = True  # one xsm_transitions row per event, same flush
    id: Mapped[int] = mapped_column(primary_key=True)
    customer: Mapped[str] = mapped_column(String(120))
    statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        StatechartType, nullable=True
    )
    # 🔒 version_id_col: a concurrent writer gets ConflictError, never a
    #    lost update.
    __mapper_args__ = StatechartMixin.optimistic()


xsm_sqlalchemy_ddl(Base.metadata)
