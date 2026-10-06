# src/xstate_statemachine/contrib/redis/_errors.py
"""Map raw ``redis.RedisError`` onto the documented store exceptions.

🛡️ #306 battle: a Redis failover surfaced as a bare
``redis.exceptions.ConnectionError`` past ``except StoreError`` -- every
web route answered **500** "ConnectionError" (an application fault in the
dashboards) for a dependency outage, and the inbox plugin's
``on_inbox_error`` never saw a `StoreError` to refuse on. `SQLiteStore`
has had this mapping since #259 (`_sqlite_errors_typed`); the Redis
backend now has the same shape, for the sync and the asyncio client.
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, TypeVar

import redis

from ...exceptions import StoreError, StoreUnavailableError

__all__ = ["redis_errors_typed", "aredis_errors_typed", "typed"]

_F = TypeVar("_F", bound=Callable[..., Any])

#: Backend-unreachable errors: retryable, nothing was written.
_UNAVAILABLE = (
    redis.ConnectionError,
    redis.TimeoutError,
    redis.BusyLoadingError,
)

#: "unknown command 'evalsha'" -- the server has no Lua scripting.
_NO_LUA = re.compile(r"unknown command '?(evalsha|eval|script)(?![a-z])", re.I)


def typed(exc: redis.RedisError, backend: str = "RedisStore") -> StoreError:
    """The `StoreError` for a raw *exc* (connection-class →
    `StoreUnavailableError`, anything else → `StoreError`)."""
    if isinstance(exc, _UNAVAILABLE):
        return StoreUnavailableError(
            f"{backend}: backend unavailable ({type(exc).__name__}: {exc})"
        )
    text = str(exc)
    if _NO_LUA.search(text):
        # 🔥 battle #309: a newcomer following the journey page installed
        #    plain `fakeredis` and got a raw "unknown command 'evalsha'".
        #    The store needs Lua scripting: name the cure.
        return StoreError(
            f"{backend}: the Redis server has no Lua scripting (EVALSHA "
            f"unknown). The store needs Redis >= 7 or, for tests, "
            f'`pip install "fakeredis[lua]"` -- plain `fakeredis` does not '
            f"ship a Lua engine. ({type(exc).__name__}: {text})"
        )
    return StoreError(f"{backend}: {type(exc).__name__}: {text}")


def redis_errors_typed(fn: _F) -> _F:
    @functools.wraps(fn)
    def wrapper(self: Any, *a: Any, **kw: Any) -> Any:
        try:
            return fn(self, *a, **kw)
        except redis.RedisError as exc:
            raise typed(exc, type(self).__name__) from exc

    return wrapper  # type: ignore[return-value]


def aredis_errors_typed(fn: _F) -> _F:
    @functools.wraps(fn)
    async def wrapper(self: Any, *a: Any, **kw: Any) -> Any:
        try:
            return await fn(self, *a, **kw)
        except redis.RedisError as exc:
            raise typed(exc, type(self).__name__) from exc

    return wrapper  # type: ignore[return-value]
