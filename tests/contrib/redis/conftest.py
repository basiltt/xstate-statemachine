# tests/contrib/redis/conftest.py
"""Redis fixtures: fakeredis by default; a live server when
``XSM_REDIS_URL`` is set (e.g. ``redis://localhost:6379/15``). Every test
gets a fresh, unique prefix and the namespace is wiped afterwards."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Iterator

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("redis")


_SERVERS: dict = {}


def _client() -> Any:
    url = os.environ.get("XSM_REDIS_URL")
    if url:
        import redis

        return redis.Redis.from_url(url)
    fakeredis = pytest.importorskip("fakeredis")
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server)
    _SERVERS[id(client)] = server
    return client


def _aclient(sync_client: Any) -> Any:
    # 📝 3.9: an asyncio client built with no running loop calls
    #    `get_event_loop()`, which raises once an earlier test closed /
    #    unset the thread's loop. Provide one; the client binds lazily.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
    url = os.environ.get("XSM_REDIS_URL")
    if url:
        import redis.asyncio as aredis

        return aredis.Redis.from_url(url)
    fakeredis = pytest.importorskip("fakeredis")
    # One FakeServer behind both clients so sync and async views agree.
    return fakeredis.FakeAsyncRedis(server=_SERVERS[id(sync_client)])


@pytest.fixture
def r() -> Iterator[Any]:
    client = _client()
    yield client
    _SERVERS.pop(id(client), None)


@pytest.fixture
def prefix(r: Any) -> Iterator[str]:
    p = f"t-{uuid.uuid4().hex[:8]}"
    yield p
    for k in r.scan_iter(match=f"{p}:*"):
        r.delete(k)
