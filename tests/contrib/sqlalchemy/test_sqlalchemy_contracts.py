# tests/contrib/sqlalchemy/test_sqlalchemy_contracts.py
"""#284: `SQLAlchemyStore`, `SQLAlchemyInbox` and `SQLAlchemyLog` pass the
SAME suites as the stdlib backends (A2 store contract is parametrised in
`tests/persistence/test_store_contract.py` itself; A3 locking, A4 inbox and
A5 log suites are re-bound here, like the Redis backends)."""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("sqlalchemy")

from tests.persistence import test_idempotency as _inbox_suite  # noqa: E402
from tests.persistence import test_locking as _lock_suite  # noqa: E402
from tests.persistence import test_log as _log_suite  # noqa: E402
from tests.persistence import test_store_contract as _store  # noqa: E402

from .conftest import make_store  # noqa: E402


class TestStoreOptimistic(_store.TestOptimisticRetry):
    pass


class TestLocking(_lock_suite.TestPersistedBlock):
    pass


class TestLockingOptimistic(_lock_suite.TestOptimisticRun):
    pass


class TestLockingPessimistic(_lock_suite.TestPessimistic):
    pass


class TestLockingAsync(_lock_suite.TestAsync):
    pass


@pytest.mark.parametrize("lock_name", ["optimistic", "pessimistic"])
def test_sixteen_threads_no_lost_updates(store: Any, lock_name: str) -> None:
    _lock_suite.test_sixteen_threads_no_lost_updates(store, lock_name)


@pytest.fixture
def inbox(tmp_path: Any) -> Iterator[Any]:
    from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyInbox

    s = make_store(tmp_path)
    yield SQLAlchemyInbox(s)
    s._engine.dispose()


class TestInboxContract(_inbox_suite.TestInboxContract):
    pass


class TestInboxPluginSync(_inbox_suite.TestPluginSync):
    pass


@pytest.fixture
def log(tmp_path: Any) -> Iterator[Any]:
    from src.xstate_statemachine.contrib.sqlalchemy import SQLAlchemyLog

    s = make_store(tmp_path)
    yield SQLAlchemyLog(s)
    s._engine.dispose()


class TestLogContract(_log_suite.TestLogContract):
    pass


class TestLogPluginSync(_log_suite.TestPluginSync):
    pass
