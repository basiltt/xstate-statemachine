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
            f"{backend}: backend unavailable ({type(exc).__name__})"
        )
    text = str(exc)
    no_lua = _NO_LUA.search(text)
    if no_lua:
        # 🔥 battle #309: a newcomer following the journey page installed
        #    plain `fakeredis` and got a raw "unknown command 'evalsha'".
        #    The store needs Lua scripting: name the cure -- and the
        #    command the server rejected (a command name, never the
        #    host or credentials that `str(exc)` may carry, CM-10).
        return StoreError(
            f"{backend}: the Redis server has no Lua scripting ("
            f"'{no_lua.group(1).lower()}' unknown). The store needs Redis "
            f'>= 7 or, for tests, `pip install "fakeredis[lua]"` -- plain '
            f"`fakeredis` does not ship a Lua engine. ({type(exc).__name__})"
        )
    # 🔥 review CM-10: never echo connection details. A server REPLY
    #    (`ResponseError`: WRONGTYPE, unknown command, ...) is the cause an
    #    operator needs (battle #309), so its text is kept -- minus any URL
    #    (credentials) and any echoed command arguments (payload data).
    #    Every other class (connection, timeout, data errors raised client
    #    side) carries `host:port` in `str(exc)` and is named by class only.
    if isinstance(exc, redis.ResponseError):
        return StoreError(
            f"{backend}: {type(exc).__name__}: {_safe_reply(text)}"
        )
    return StoreError(f"{backend}: {type(exc).__name__}")


#: ``scheme://...`` anywhere in a reply (a URL may carry ``user:pw@``).
_URL = re.compile(r"\b\w+://\S+")
#: redis' "unknown command 'X', with args beginning with: ..." tail echoes
#: the command's arguments -- payload data that does not belong in a log.
_ECHOED_ARGS = re.compile(r",?\s*with args beginning with:.*$", re.S)


def _safe_reply(text: str) -> str:
    """A server reply with URLs and echoed arguments stripped (CM-10)."""
    text = _ECHOED_ARGS.sub("", text)
    return _URL.sub("<url redacted>", text).strip()


def redis_errors_typed(fn: _F) -> _F:
    """Wrap a method so `redis.RedisError` becomes the typed xsm error.

    Args:
        fn: The method to wrap.

    Returns:
        The wrapped method.
    """

    @functools.wraps(fn)
    def wrapper(self: Any, *a: Any, **kw: Any) -> Any:
        try:
            return fn(self, *a, **kw)
        except redis.RedisError as exc:
            raise typed(exc, type(self).__name__) from exc

    return wrapper  # type: ignore[return-value]


def aredis_errors_typed(fn: _F) -> _F:
    """Wrap a coroutine method so `redis.RedisError` becomes the typed error.

    Args:
        fn: The coroutine method to wrap.

    Returns:
        The wrapped coroutine method.
    """

    @functools.wraps(fn)
    async def wrapper(self: Any, *a: Any, **kw: Any) -> Any:
        try:
            return await fn(self, *a, **kw)
        except redis.RedisError as exc:
            raise typed(exc, type(self).__name__) from exc

    return wrapper  # type: ignore[return-value]
