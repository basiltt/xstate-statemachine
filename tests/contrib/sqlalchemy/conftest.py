# tests/contrib/sqlalchemy/conftest.py
"""SQLAlchemy fixtures: a file-backed SQLite engine per test by default; a
real server when ``DATABASE_URL`` is set (e.g.
``postgresql+psycopg://u:p@localhost/xsm``). No testcontainers here --
the Postgres cell is opt-in and gated on that variable."""

from __future__ import annotations

import os
import uuid
from typing import Any, Iterator

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("sqlalchemy")


def sqlite_engine(path: Any) -> Any:
    from sqlalchemy import create_engine

    # 📝 A generous busy timeout: the concurrency tests put 16 writers on
    #    one SQLite file.
    return create_engine(
        f"sqlite:///{path}", connect_args={"timeout": 30}, future=True
    )


def make_store(tmp_path: Any, **kw: Any) -> Any:
    from sqlalchemy.orm import sessionmaker

    from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore

    url = os.environ.get("DATABASE_URL")
    if url:
        from sqlalchemy import create_engine

        eng = create_engine(url)
        # A unique snapshot table per test keeps runs isolated.
        kw.setdefault("table", f"xsm_t_{uuid.uuid4().hex[:10]}")
    else:
        eng = sqlite_engine(tmp_path / f"{uuid.uuid4().hex[:6]}.db")
    s = SQLAlchemyStore(sessionmaker(eng), **kw)
    s._engine = eng  # type: ignore[attr-defined]
    return s


@pytest.fixture
def store(tmp_path: Any) -> Iterator[Any]:
    s = make_store(tmp_path)
    yield s
    s._engine.dispose()
