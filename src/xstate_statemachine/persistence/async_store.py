# src/xstate_statemachine/persistence/async_store.py
# -----------------------------------------------------------------------------
# ⚡ AsyncStateStore + as_async() -- the same contract for asyncio (#259)
# -----------------------------------------------------------------------------
# 🏛️ Every stdlib store is synchronous (file and SQLite I/O are blocking
#    calls). An asyncio caller must not block the loop on them, so
#    `as_async(store)` runs each call in the default executor -- the same
#    thing `loop.run_in_executor` does for any blocking library -- and
#    exposes the identical surface with `await`. Native async backends
#    (Redis #306, SQLAlchemy async #276) implement `AsyncStateStore`
#    directly; `as_async` is for wrapping, not a base class.
# -----------------------------------------------------------------------------
"""`AsyncStateStore` protocol and `as_async()` executor wrapper."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import functools
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Sequence,
)

try:  # pragma: no cover
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from .deadline import Deadline
from .store import StateStore, StoredSnapshot

__all__ = ["AsyncStateStore", "AsyncStoreAdapter", "as_async"]


@runtime_checkable
class AsyncStateStore(Protocol):
    """`StateStore` with every method awaitable and `lock` an async CM."""

    async def load(self, key: str) -> Optional[StoredSnapshot]:
        pass  # pragma: no cover

    async def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        pass  # pragma: no cover

    async def delete(self, key: str) -> bool:
        pass  # pragma: no cover

    async def forget(self, key: str) -> Dict[str, int]:
        pass  # pragma: no cover

    async def list_keys(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[str]:
        pass  # pragma: no cover

    def lock(
        self, key: str, *, timeout: float = 10.0
    ) -> AsyncContextManager[None]:
        pass  # pragma: no cover

    async def health(self) -> Dict[str, Any]:
        pass  # pragma: no cover


class AsyncStoreAdapter:
    """Wraps a synchronous `StateStore`; every call runs on ONE worker thread.

    🧵 One dedicated single-thread executor per adapter, not the default
    pool: file and SQLite locks (and SQLite connections) are thread-affine,
    so a `lock()` acquired on worker A and a `save()` that lands on worker
    B would deadlock or bypass the lock. Funnelling every call through the
    same thread makes `async with adapter.lock(key): await adapter.save()`
    correct by construction. Calls are serialised per adapter -- the right
    trade for local stores; a native async backend (Redis #306) does not
    go through this class.
    """

    def __init__(self, store: StateStore) -> None:
        self.sync_store = store
        self._pool: Optional[concurrent.futures.ThreadPoolExecutor] = None

    def _executor(self) -> concurrent.futures.ThreadPoolExecutor:
        if self._pool is None:
            self._pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="xsm-store"
            )
        return self._pool

    async def _run(self, fn: Any, *a: Any, **kw: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor(), functools.partial(fn, *a, **kw)
        )

    async def load(self, key: str) -> Optional[StoredSnapshot]:
        return await self._run(self.sync_store.load, key)

    async def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        return await self._run(
            self.sync_store.save,
            key,
            snapshot,
            expected_version=expected_version,
            machine_version=machine_version,
            deadlines=deadlines,
        )

    async def delete(self, key: str) -> bool:
        return await self._run(self.sync_store.delete, key)

    async def forget(self, key: str) -> Dict[str, int]:
        return await self._run(self.sync_store.forget, key)

    async def list_keys(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[str]:
        return await self._run(
            self.sync_store.list_keys, prefix=prefix, limit=limit
        )

    def lock(
        self, key: str, *, timeout: float = 10.0
    ) -> AsyncContextManager[None]:
        return self._alock(key, timeout)

    @contextlib.asynccontextmanager
    async def _alock(self, key: str, timeout: float) -> AsyncIterator[None]:
        cm = self.sync_store.lock(key, timeout=timeout)
        await self._run(cm.__enter__)
        try:
            yield
        except BaseException as exc:
            await self._run(cm.__exit__, type(exc), exc, exc.__traceback__)
            raise
        else:
            await self._run(cm.__exit__, None, None, None)

    async def health(self) -> Dict[str, Any]:
        return await self._run(self.sync_store.health)

    def close(self) -> None:
        """Shut the worker thread down (idempotent)."""
        if self._pool is not None:
            self._pool.shutdown(wait=True)
            self._pool = None


def as_async(store: StateStore) -> AsyncStateStore:
    """Return an `AsyncStateStore` view of a synchronous store."""
    return AsyncStoreAdapter(store)
