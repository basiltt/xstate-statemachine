# tests/contrib/redis/test_redis_contracts.py
"""#306: the Redis backends pass the SAME contract suites as the stdlib
stores -- `tests/persistence/test_store_contract.py` (A2),
`test_idempotency.py` (A4) and `test_log.py` (A5) -- by re-binding each
suite's backend fixture to a Redis factory. Runs on fakeredis by default,
on a live server with ``XSM_REDIS_URL``."""

from __future__ import annotations

import uuid
from typing import Any, Iterator

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("redis")

# ---------------------------------------------------------------------------
# A2 store contract
# ---------------------------------------------------------------------------
from tests.persistence import test_store_contract as _store_suite  # noqa: E402
from tests.persistence import test_idempotency as _inbox_suite  # noqa: E402
from tests.persistence import test_log as _log_suite  # noqa: E402
from tests.persistence import test_locking as _lock_suite  # noqa: E402
from tests.persistence import test_durable_timers as _timer_suite  # noqa: E402


def _redis_store(r: Any) -> Any:
    from src.xstate_statemachine.contrib.redis import RedisStore

    return RedisStore(r, prefix=f"t-{uuid.uuid4().hex[:8]}")


@pytest.fixture
def store(r: Any) -> Iterator[Any]:
    s = _redis_store(r)
    yield s
    for k in r.scan_iter(match=f"{s.k.p}:*"):
        r.delete(k)


class TestStoreContract(_store_suite.TestContract):
    """Every A2 contract test, against RedisStore."""

    # The codec test builds sibling stores from STORE_FACTORIES by backend
    # name; give it a Redis-aware version.
    def test_codec_seam(self, store: Any, tmp_path: Any) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        class Rot:
            def encode(self, s: str) -> str:
                return s[::-1]

            def decode(self, s: str) -> str:
                return s[::-1]

        enc = RedisStore(store.r, prefix=store.k.p + "-enc", codec=Rot())
        raw = RedisStore(store.r, prefix=store.k.p + "-enc")
        blob = _store_suite.snapshot_of(1)
        enc.save("k", blob)
        assert enc.load("k").snapshot == blob
        assert raw.load("k").snapshot == blob[::-1]

    def test_size_cap_on_save_and_load(
        self, store: Any, tmp_path: Any
    ) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore
        from src.xstate_statemachine.persistence import SnapshotTooLargeError

        small = RedisStore(
            store.r, prefix=store.k.p + "-small", max_snapshot_bytes=64
        )
        with pytest.raises(SnapshotTooLargeError):
            small.save("k", _store_suite.snapshot_of())
        store.save("k", _store_suite.snapshot_of())
        store.max_snapshot_bytes = 64
        with pytest.raises(SnapshotTooLargeError):
            store.load("k")


class TestStoreOptimistic(_store_suite.TestOptimisticRetry):
    pass


# ---------------------------------------------------------------------------
# A3 locking suite (persisted / strategies) against RedisStore
# ---------------------------------------------------------------------------
class TestLocking(_lock_suite.TestPersistedBlock):
    pass


class TestLockingOptimistic(_lock_suite.TestOptimisticRun):
    pass


class TestLockingPessimistic(_lock_suite.TestPessimistic):
    pass


class TestLockingAsync(_lock_suite.TestAsync):
    pass


# ---------------------------------------------------------------------------
# A4 inbox contract
# ---------------------------------------------------------------------------
@pytest.fixture
def inbox(r: Any) -> Iterator[Any]:
    from src.xstate_statemachine.contrib.redis import RedisInbox

    ib = RedisInbox(r, prefix=f"t-{uuid.uuid4().hex[:8]}")
    yield ib
    for k in r.scan_iter(match=f"{ib.k.p}:*"):
        r.delete(k)


class TestInboxContract(_inbox_suite.TestInboxContract):
    pass


class TestInboxPluginSync(_inbox_suite.TestPluginSync):
    pass


class TestInboxPluginAsync(_inbox_suite.TestPluginAsync):
    pass


# ---------------------------------------------------------------------------
# A5 log contract
# ---------------------------------------------------------------------------
@pytest.fixture
def log(r: Any) -> Iterator[Any]:
    from src.xstate_statemachine.contrib.redis import RedisLog

    lg = RedisLog(r, prefix=f"t-{uuid.uuid4().hex[:8]}")
    yield lg
    for k in r.scan_iter(match=f"{lg.k.p}:*"):
        r.delete(k)


class TestLogContract(_log_suite.TestLogContract):
    pass


class TestLogPluginSync(_log_suite.TestPluginSync):
    pass


class TestLogPluginAsync(_log_suite.TestPluginAsync):
    pass


class TestLogReplay(_log_suite.TestReplay):
    pass


# ---------------------------------------------------------------------------
# A7 scanner end-to-end against RedisStore (uses the zset index)
# ---------------------------------------------------------------------------
class TestScannerOnRedis:
    def test_end_to_end(self, r: Any) -> None:
        import time

        from src.xstate_statemachine.persistence import (
            DueTimerScanner,
            persisted,
        )

        prefix = f"t-{uuid.uuid4().hex[:8]}"
        m = _timer_suite.machine(
            {
                **_timer_suite.CFG,
                "states": {
                    **_timer_suite.CFG["states"],
                    "waiting": {
                        "after": {
                            "3600000": {
                                "target": "reminded",
                                "actions": "note",
                            }
                        }
                    },
                },
            }
        )

        from src.xstate_statemachine.contrib.redis import RedisStore

        def make() -> Any:  # a new handle each call = "another process"
            return RedisStore(r, prefix=prefix)

        with persisted(make(), "u1", m):
            pass
        now = time.time()
        sc = DueTimerScanner(make(), lambda k: m)
        assert sc.run_once(now=now + 1800) == 0
        assert sc.run_once(now=now + 3601) == 1
        assert sc.run_once(now=now + 3601) == 0
        with persisted(make(), "u1", m) as i:
            assert i.current_state_ids == {"r.reminded"}
        assert make().due_keys(now + 99999) == []
