# src/xstate_statemachine/contrib/redis/__init__.py
# -----------------------------------------------------------------------------
# 🟥 [redis] -- RedisStore / RedisInbox / RedisLog with fencing locks (#306)
# -----------------------------------------------------------------------------
# 🏛️ `SQLiteStore` is single-host. The first real deployment question every
#    web user asks is "I have 4 uvicorn workers on 2 machines -- where does
#    the snapshot live?" Redis is the lowest-friction shared answer. This
#    package ships the STORE / INBOX / LOG / LOCK only; Redis Streams as a
#    broker is #294.
#
# 🔐 X0 items (#303):
#    * `prefix` is mandatory and non-empty (X0.15) -- two apps on one Redis
#      must not share a namespace by accident; a `{prefix}:schema` key
#      records the layout version.
#    * Optimistic save is a Lua script that compares the stored version and
#      writes atomically -- no WATCH window, no lost update.
#    * Pessimistic `lock()` is `SET NX PX` with a random token released
#      only by its owner (Lua compare-and-delete); and because a Redis lock
#      can EXPIRE under a slow holder, `persisted()` still saves with
#      `expected_version` (fencing, #260) so an expired lock yields
#      `ConflictError`, never a lost update.
#    * `forget(key)` deletes snapshot + deadlines + inbox rows + log stream
#      atomically (Lua). `list_keys(prefix)` escapes SCAN glob
#      metacharacters so a user prefix containing `*?[` matches literally.
#    * Snapshot size cap and key validation come from `BaseStore`.
# -----------------------------------------------------------------------------
"""Redis-backed `StateStore`, `InboxStore` and `TransitionLogStore`.

Install with ``pip install "xstate-statemachine[redis]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("redis", "redis")

from .inbox import RedisInbox  # noqa: E402
from .log import RedisLog  # noqa: E402
from .store import (  # noqa: E402
    DEFAULT_SOCKET_CONNECT_TIMEOUT_S,
    DEFAULT_SOCKET_TIMEOUT_S,
    AsyncRedisStore,
    RedisStore,
    escape_glob,
)

__all__ = [
    "AsyncRedisStore",
    "DEFAULT_SOCKET_CONNECT_TIMEOUT_S",
    "DEFAULT_SOCKET_TIMEOUT_S",
    "RedisInbox",
    "RedisLog",
    "RedisStore",
    "escape_glob",
]
