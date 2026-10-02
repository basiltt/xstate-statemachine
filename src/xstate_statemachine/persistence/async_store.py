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
import contextvars
import functools
import weakref
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

from ..exceptions import LockTimeoutError, StoreError
from .deadline import Deadline
from .store import StateStore, StoredSnapshot

__all__ = ["AsyncStateStore", "AsyncStoreAdapter", "as_async"]

#: 🔑 The lock-holder token for the current context. Set by `_alock`,
#: inherited by every task the holder spawns (asyncio copies the context
#: into child tasks), so work fanned out from inside the lock is still
#: "the holder" and never queues behind its own parent (review H1, #259).
_HOLDING: "contextvars.ContextVar[Optional[object]]" = contextvars.ContextVar(
    "xsm_async_store_holder", default=None
)


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
        self._gates: "weakref.WeakKeyDictionary[Any, asyncio.Lock]" = (
            weakref.WeakKeyDictionary()
        )
        #: Set while some task is inside `lock()`; the value is a token the
        #: holder's context (and every child task it spawns) carries.
        self._holder_token: Optional[object] = None
        #: How long a non-holder call waits for the lock to be released
        #: before giving up. Mirrors the sync stores' bounded waits.
        self.gate_timeout: float = 10.0
        self._closed = False

    def _is_holder(self) -> bool:
        """Is the CURRENT context (task or any task it spawned) the holder?

        🏛️ Review H1 (#259): identity was `holder is current_task()`, so
        work the holder fanned out with `gather` / `create_task` / a
        `TaskGroup` counted as a stranger, queued behind the gate the
        parent holds while awaiting that very child -- an unbounded
        deadlock. A `ContextVar` is copied into child tasks, so the
        holder's token travels with its whole subtree.
        """
        token = self._holder_token
        return token is not None and _HOLDING.get() is token

    async def _run(self, fn: Any, *a: Any, **kw: Any) -> Any:
        loop = asyncio.get_running_loop()
        if self._holder_token is not None and not self._is_holder():
            # 🛡️ #259 battle: the worker thread is "inside" another task's
            #    lock. A call from here would run on that thread and join
            #    the holder's state -- on SQLite its open transaction (a
            #    `save` that returned a version and was then rolled back
            #    with the holder), on FileStore its held-key set (a `save`
            #    that skipped the lock). Wait until the holder is done --
            #    BOUNDED (review H1): a wait that can never end is worse
            #    than a loud refusal.
            gate = self._gate()
            try:
                await asyncio.wait_for(gate.acquire(), self.gate_timeout)
            except asyncio.TimeoutError:
                raise LockTimeoutError(
                    "<adapter>", self.gate_timeout
                ) from None
            gate.release()
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
        # 🛡️ #259 battle: every call runs on ONE worker thread, so two
        #    coroutines both inside `lock()` were the SAME thread to the
        #    sync store. Memory/File: the second acquire blocked the only
        #    worker, so the holder's own save queued behind it (waiters
        #    timed out, the holder stalled for their whole timeout).
        #    SQLite: the second "re-entered" the first's transaction -- no
        #    exclusion at all. Holders now queue here, on the loop, first.
        if self._is_holder():
            # ⚠️ Review M1: ONE lock per adapter at a time, because the one
            #    worker thread can only be "inside" one transaction / one
            #    held key. Nesting used to wait out the full timeout and
            #    then raise; refuse at once with the reason instead.
            raise LockTimeoutError(
                key,
                0.0,
                holder=(
                    "this adapter's own lock -- nested adapter.lock() on one "
                    "AsyncStoreAdapter is refused: the single worker thread "
                    "holds one lock at a time. Use a second as_async(store) "
                    "for the inner key, or release the outer lock first"
                ),
            )
        gate = self._gate()
        try:
            await asyncio.wait_for(gate.acquire(), timeout)
        except asyncio.TimeoutError:
            raise LockTimeoutError(key, timeout) from None
        token = object()
        self._holder_token = token
        reset = _HOLDING.set(token)
        try:
            cm = self.sync_store.lock(key, timeout=timeout)
            await self._run(cm.__enter__)
            try:
                yield
            except BaseException as exc:
                await self._run(cm.__exit__, type(exc), exc, exc.__traceback__)
                raise
            else:
                await self._run(cm.__exit__, None, None, None)
        finally:
            _HOLDING.reset(reset)
            self._holder_token = None
            gate.release()

    def _gate(self) -> asyncio.Lock:
        # Created lazily, per loop: an `asyncio.Lock` made outside a running
        # loop binds the wrong loop on 3.9.
        loop = asyncio.get_running_loop()
        gate = self._gates.get(loop)
        if gate is None:
            gate = self._gates[loop] = asyncio.Lock()
        return gate

    async def health(self) -> Dict[str, Any]:
        return await self._run(self.sync_store.health)

    def close(self) -> None:
        """Shut the worker thread down (idempotent).

        Waits for in-flight calls. A call that arrives AFTER close raises
        `StoreError` (review M2: it used to surface as a bare
        `RuntimeError` from the shut-down executor).
        """
        if self._pool is not None:
            self._pool.shutdown(wait=True)
            self._pool = None
        self._closed = True

    def _executor(self) -> concurrent.futures.ThreadPoolExecutor:
        if self._closed:
            raise StoreError("AsyncStoreAdapter is closed.")
        if self._pool is None:
            self._pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="xsm-store"
            )
        return self._pool


def as_async(store: StateStore) -> AsyncStateStore:
    """Return an `AsyncStateStore` view of a synchronous store."""
    return AsyncStoreAdapter(store)
