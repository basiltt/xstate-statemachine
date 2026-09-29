# src/xstate_statemachine/contrib/sqlalchemy/__init__.py
# -----------------------------------------------------------------------------
# 🗄️ [sqlalchemy] -- statecharts on mapped rows, and stores on any RDBMS
# -----------------------------------------------------------------------------
# 🏛️ SQLAlchemy sits under Flask, FastAPI and most Python services, so one
#    adapter reaches most relational deployments. Two independent halves:
#
#      * ROW-BACKED -- `StatechartType` + `StatechartMixin`: the snapshot is
#        a column of your business row, four denormalised columns make it
#        queryable (`in_state()`), `version_id_col` gives optimistic locking
#        (`StaleDataError` → `ConflictError`, `send_with_retry`), a mapper
#        listener keeps the columns true, deadlines go to `xsm_deadlines`
#        so `DueTimerScanner` fires them, and `__xsm_audit__` writes the
#        audit row in the SAME flush.
#      * KEY-VALUE -- `SQLAlchemyStore` / `AsyncSQLAlchemyStore` implement
#        the A2 `StateStore` contract (they pass the same contract suite as
#        the stdlib stores); `SQLAlchemyInbox` / `SQLAlchemyLog` share its
#        transaction so inbox marks and audit rows commit with the save
#        (X0.3) and `forget(key)` erases every table (X0.5).
#
# 📦 The transactional OUTBOX (#284 part 3) arrives with the EDA core
#    (#293) -- it needs that group's `BrokerAdapter` / `OutboxStore`
#    protocols and is deliberately not invented here.
# -----------------------------------------------------------------------------
"""SQLAlchemy 2.x integration.

Install with ``pip install "xstate-statemachine[sqlalchemy]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("sqlalchemy", "sqlalchemy")

from ._schema import SCHEMA_VERSION, xsm_sqlalchemy_ddl  # noqa: E402
from .inbox_log import SQLAlchemyInbox, SQLAlchemyLog  # noqa: E402
from .mixin import StatechartMixin, send_with_retry  # noqa: E402
from .model_store import ModelStore  # noqa: E402
from .store import AsyncSQLAlchemyStore, SQLAlchemyStore  # noqa: E402
from .types import StatechartType  # noqa: E402

__all__ = [
    "AsyncSQLAlchemyStore",
    "ModelStore",
    "SCHEMA_VERSION",
    "SQLAlchemyInbox",
    "SQLAlchemyLog",
    "SQLAlchemyStore",
    "StatechartMixin",
    "StatechartType",
    "send_with_retry",
    "xsm_sqlalchemy_ddl",
]
