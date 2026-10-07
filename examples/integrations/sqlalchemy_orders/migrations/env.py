# examples/integrations/sqlalchemy_orders/migrations/env.py
"""Alembic environment: `models.Base.metadata` (incl. the xsm_* tables)."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 📝 The example directory holds `models.py` / `logic.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base  # noqa: E402

from xstate_statemachine.contrib.sqlalchemy import (  # noqa: E402
    render_statechart_type,
)

config = context.config
if config.config_file_name is not None and config.attributes.get(
    "configure_logger", True
):
    fileConfig(config.config_file_name)

# 💡 ORDERS_DB_URL overrides alembic.ini (tests point it at a temp file).
url = os.environ.get("ORDERS_DB_URL")
if url:
    config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


# 💡 `StatechartType` renders as ``sa.JSON().with_variant(postgresql.JSONB(),
#    "postgresql")`` -- the DDL `create_all` emits -- so a migration made on
#    SQLite creates JSONB on Postgres and autogenerate stays quiet on both.
#    The size cap is a Python-side guard, not a database type.
render_item = render_statechart_type


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        render_item=render_item,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
