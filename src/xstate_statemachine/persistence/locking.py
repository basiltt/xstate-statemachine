# src/xstate_statemachine/persistence/locking.py
# -----------------------------------------------------------------------------
# 🔐 Locking strategies + persisted() -- make the safe pattern the easy one
# -----------------------------------------------------------------------------
# 🏛️ Two requests transition the same entity at once → a lost update or a
#    double side effect (a double charge). django-fsm has a
#    `ConcurrentTransition` exception precisely because this is unsolved
#    there. Three standard mechanisms sit behind ONE interface:
#
#      OptimisticLock  load → act → save(expected_version) → retry on conflict
#      PessimisticLock with store.lock(key): load → act → save
#      NoLock          load → act → save (last writer wins; single-writer only)
#
#    and `persisted()` wraps create → act → persist → discard in a context
#    manager so the caller writes `with persisted(...) as order:
#    order.send("PAY")` and gets the safe behaviour by default.
#
# ⚠️ A context-manager BODY cannot be re-run. So `with persisted(...,
#    lock=OptimisticLock())` raises `ConflictError` on the FIRST conflict
#    and the caller retries the whole block; the retrying form is
#    `lock.run(store, key, machine, fn)`, where `fn` is a callable the
#    strategy may invoke up to `retries + 1` times. That is a real
#    guarantee (X0.3): under optimistic retry, ACTIONS MAY RUN MORE THAN
#    ONCE per logical send -- put side effects in services or an outbox.
#
# 🔒 Fencing: `PessimisticLock` ALSO saves with `expected_version`. On a
#    store whose lock can expire (Redis #306) an expired lock then yields
#    `ConflictError`, never a lost update.
#
# 🧵 Each thread gets its OWN interpreter from `persisted()` / `run()`; the
#    engine is not shareable across threads and nothing here changes that.
# -----------------------------------------------------------------------------
"""`LockStrategy`, `OptimisticLock`, `PessimisticLock`, `NoLock`,
`persisted()`, `apersisted()`, `persisted_retry()`."""

from __future__ import annotations

import contextlib
import inspect
import time
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    TypeVar,
)

try:  # pragma: no cover
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from ..clock import Clock
from ..exceptions import ConflictError, LockTimeoutError
from ..models import MachineNode
from ..patterns.retry import RetryPolicy
from .helpers import _build, save_interpreter
from .store import StateStore

__all__ = [
    "LockStrategy",
    "OptimisticLock",
    "PessimisticLock",
    "NoLock",
    "persisted",
    "apersisted",
    "persisted_retry",
    "DEFAULT_BACKOFF",
]

T = TypeVar("T")

#: Retry backoff for `OptimisticLock`: short, jittered -- a conflict means
#: another writer JUST finished, so a few ms of decorrelated wait is enough
#: to break the herd without adding latency a user notices.
DEFAULT_BACKOFF = RetryPolicy(
    max_attempts=6, base_ms=2.0, factor=2.0, max_ms=100.0, jitter="full"
)


@runtime_checkable
class LockStrategy(Protocol):
    """How a `persisted()` block coordinates with other writers."""

    def run(
        self,
        store: StateStore,
        key: str,
        machine: MachineNode[Any],
        fn: Callable[[Any], T],
        *,
        clock: Optional[Clock] = None,
        plugins: Iterable[Any] = (),
        create_if_missing: bool = True,
    ) -> T:
        """load → ``fn(interp)`` → save → discard, under this strategy.
        May call *fn* more than once (optimistic retry)."""
        ...  # pragma: no cover

    @contextlib.contextmanager
    def acquire(self, store: StateStore, key: str) -> Iterator[None]:
        """Hold whatever this strategy holds for the duration of a
        `persisted()` block (a store lock for pessimistic; nothing for the
        others)."""
        ...  # pragma: no cover

    def fence(self, version: int) -> Optional[int]:
        """The ``expected_version`` to save with, given the loaded
        *version*; ``None`` for an unconditional write."""
        ...  # pragma: no cover


def _cycle(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    fn: Callable[[Any], T],
    expected: Callable[[int], Optional[int]],
    clock: Optional[Clock],
    plugins: Iterable[Any],
    create_if_missing: bool,
) -> T:
    """One create → act → persist → discard pass."""
    from ..sync_interpreter import SyncInterpreter

    interp, version = _build(
        store,
        key,
        machine,
        SyncInterpreter,
        clock,
        plugins,
        create_if_missing,
        True,
        {},
    )
    markers = _mark_plugins(plugins)
    for m in markers:
        m.buffer_marks = True
    interp.store_key = key  # #261: the instance identity for scoped plugins
    interp.start()
    try:
        result = fn(interp)
        _save_with_marks(store, key, interp, expected(version), markers)
        return result
    except BaseException:
        for m in markers:
            m.discard_marks()
        raise
    finally:
        interp.stop()


class OptimisticLock:
    """load → act → ``save(expected_version)`` → on `ConflictError` reload
    and re-apply *fn*, up to *retries* times, with jittered backoff.

    Stateless and thread-safe: one instance may be shared by every caller
    (the default argument of `persisted()` is one).

    Args:
        retries: Extra attempts after the first (``0`` = fail on the first
            conflict, exactly like the `persisted()` block does).
        backoff: A `RetryPolicy` for the wait between attempts.
        rng: Only for deterministic tests; ``None`` uses the policy's.
    """

    def __init__(
        self,
        *,
        retries: int = 5,
        backoff: Optional[RetryPolicy] = None,
        rng: Optional[Callable[[], float]] = None,
    ) -> None:
        if retries < 0:
            raise ValueError("retries must be >= 0")
        self.retries = int(retries)
        self.backoff = backoff or DEFAULT_BACKOFF
        self._rng = rng

    def fence(self, version: int) -> Optional[int]:
        return version

    @contextlib.contextmanager
    def acquire(self, store: StateStore, key: str) -> Iterator[None]:
        yield  # nothing held; the version is the fence

    def _sleep(self, attempt: int) -> None:
        policy = self.backoff
        if self._rng is not None:
            policy = RetryPolicy(
                max_attempts=policy.max_attempts,
                base_ms=policy.base_ms,
                factor=policy.factor,
                max_ms=policy.max_ms,
                jitter=policy.jitter,
                rng=self._rng,
            )
        time.sleep(policy.delay_ms(attempt) / 1000.0)

    def run(
        self,
        store: StateStore,
        key: str,
        machine: MachineNode[Any],
        fn: Callable[[Any], T],
        *,
        clock: Optional[Clock] = None,
        plugins: Iterable[Any] = (),
        create_if_missing: bool = True,
    ) -> T:
        attempt = 0
        while True:
            attempt += 1
            try:
                return _cycle(
                    store,
                    key,
                    machine,
                    fn,
                    self.fence,
                    clock,
                    plugins,
                    create_if_missing,
                )
            except ConflictError as exc:
                if attempt > self.retries:
                    exc.attempts = attempt  # type: ignore[attr-defined]
                    raise
                self._sleep(attempt)


class PessimisticLock:
    """``with store.lock(key, timeout)``: load → act → save.

    Serialises writers on the store's lock; `LockTimeoutError` if it cannot
    be taken in *timeout* seconds; released on any exception. Saves WITH
    ``expected_version`` as a fence, so on a store whose lock can expire
    (Redis) an expired lock produces `ConflictError` -- never a lost update.
    """

    def __init__(self, *, timeout: float = 10.0) -> None:
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        self.timeout = float(timeout)

    def fence(self, version: int) -> Optional[int]:
        return version

    @contextlib.contextmanager
    def acquire(self, store: StateStore, key: str) -> Iterator[None]:
        with store.lock(key, timeout=self.timeout):
            yield

    def run(
        self,
        store: StateStore,
        key: str,
        machine: MachineNode[Any],
        fn: Callable[[Any], T],
        *,
        clock: Optional[Clock] = None,
        plugins: Iterable[Any] = (),
        create_if_missing: bool = True,
    ) -> T:
        with self.acquire(store, key):
            return _cycle(
                store,
                key,
                machine,
                fn,
                self.fence,
                clock,
                plugins,
                create_if_missing,
            )


class NoLock:
    """load → act → save, unconditionally. Last writer wins.

    Only correct when there is exactly one writer per key (a single
    consumer per partition, a CLI). Exists so the choice is explicit, not
    the accident of forgetting a lock.
    """

    def fence(self, version: int) -> Optional[int]:
        return None

    @contextlib.contextmanager
    def acquire(self, store: StateStore, key: str) -> Iterator[None]:
        yield

    def run(
        self,
        store: StateStore,
        key: str,
        machine: MachineNode[Any],
        fn: Callable[[Any], T],
        *,
        clock: Optional[Clock] = None,
        plugins: Iterable[Any] = (),
        create_if_missing: bool = True,
    ) -> T:
        return _cycle(
            store,
            key,
            machine,
            fn,
            self.fence,
            clock,
            plugins,
            create_if_missing,
        )


_DEFAULT_LOCK = OptimisticLock()


def _mark_plugins(plugins: Iterable[Any]) -> List[Any]:
    """Plugins that buffer inbox marks (`IdempotencyPlugin`, #261)."""
    return [p for p in plugins if callable(getattr(p, "flush_marks", None))]


def _save_with_marks(
    store: StateStore,
    key: str,
    interp: Any,
    expected: Optional[int],
    markers: List[Any],
) -> int:
    """Save the snapshot, then commit buffered inbox marks -- inside the
    same store transaction when the caller holds one (`PessimisticLock`
    on SQLite: the lock IS the transaction), else immediately after
    (save-then-mark; the in-snapshot `processed_ids` ring covers the gap).
    A failed save discards the marks and releases their claims."""
    try:
        version = save_interpreter(
            store, key, interp, expected_version=expected
        )
    except BaseException:
        for m in markers:
            m.discard_marks()
        raise
    for m in markers:
        m.flush_marks()
    return version


@contextlib.contextmanager
def persisted(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    *,
    lock: Optional[Any] = None,
    clock: Optional[Clock] = None,
    plugins: Iterable[Any] = (),
    create_if_missing: bool = True,
) -> Iterator[Any]:
    """create → act → persist → discard as a ``with`` block (sync engine).

    ::

        with persisted(store, f"order:{order_id}", machine) as order:
            receipt = order.send("PAY", wait=True)

    Persists on clean exit; **on an exception inside the block nothing is
    written** (the caller's transaction semantics). The interpreter is
    stopped either way. Under the default `OptimisticLock` a concurrent
    writer makes the exit raise `ConflictError` -- a block cannot be
    re-run, so the CALLER retries (or uses `persisted_retry` /
    `lock.run`, which can). Under `PessimisticLock` the store lock is held
    for the whole block.
    """
    from ..sync_interpreter import SyncInterpreter

    strategy = lock if lock is not None else _DEFAULT_LOCK
    with strategy.acquire(store, key):
        interp, version = _build(
            store,
            key,
            machine,
            SyncInterpreter,
            clock,
            plugins,
            create_if_missing,
            True,
            {},
        )
        markers = _mark_plugins(plugins)
        for m in markers:
            m.buffer_marks = True
        interp.store_key = key  # #261
        interp.start()
        try:
            yield interp
        except BaseException:
            for m in markers:
                m.discard_marks()
            interp.stop()
            raise
        try:
            _save_with_marks(
                store, key, interp, strategy.fence(version), markers
            )
        finally:
            interp.stop()


@contextlib.asynccontextmanager
async def apersisted(
    store: Any,
    key: str,
    machine: MachineNode[Any],
    *,
    lock: Optional[Any] = None,
    clock: Optional[Clock] = None,
    plugins: Iterable[Any] = (),
    create_if_missing: bool = True,
) -> AsyncIterator[Any]:
    """Async twin of `persisted()`: yields a started `Interpreter`.

    *store* may be a sync `StateStore` or an `AsyncStateStore` (from
    `as_async()`); sync stores are called via the executor so the loop is
    never blocked. `PessimisticLock` holds the store's lock via the async
    adapter's ``async with``.
    """
    from ..interpreter import Interpreter
    from .async_store import as_async

    strategy = lock if lock is not None else _DEFAULT_LOCK
    astore = store if _is_async_store(store) else as_async(store)

    async def _hold() -> Any:
        if isinstance(strategy, PessimisticLock):
            return astore.lock(key, timeout=strategy.timeout)
        return contextlib.nullcontext()

    lock_cm = await _hold()
    async with _maybe_async(lock_cm):
        record = await astore.load(key)
        if record is None:
            if not create_if_missing:
                from .helpers import KeyNotFoundError

                raise KeyNotFoundError(key)
            interp = Interpreter(machine, clock=clock)
            for p in plugins:
                interp.use(p)
            version = 0
        else:
            interp = Interpreter.from_snapshot(
                record.snapshot,
                machine,
                clock=clock,
                plugins=list(plugins),
            )
            version = record.version
        markers = _mark_plugins(plugins)
        for m in markers:
            m.buffer_marks = True
        interp.store_key = key  # #261
        await interp.start()
        try:
            yield interp
        except BaseException:
            for m in markers:
                m.discard_marks()
            await interp.stop()
            raise
        try:
            snapshot = interp.get_snapshot()
            deadlines = tuple(interp._persist_deadlines())
            try:
                await astore.save(
                    key,
                    snapshot,
                    expected_version=strategy.fence(version),
                    machine_version=machine.version or "",
                    deadlines=deadlines,
                )
            except BaseException:
                for m in markers:
                    m.discard_marks()
                raise
            for m in markers:
                m.flush_marks()
        finally:
            await interp.stop()


def _is_async_store(store: Any) -> bool:
    return inspect.iscoroutinefunction(getattr(store, "load", None))


@contextlib.asynccontextmanager
async def _maybe_async(cm: Any) -> AsyncIterator[None]:
    if hasattr(cm, "__aenter__"):
        async with cm:
            yield
    else:
        with cm:
            yield


def persisted_retry(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    fn: Callable[[Any], T],
    *,
    lock: Optional[Any] = None,
    **kw: Any,
) -> T:
    """`lock.run(...)` with the same defaults as `persisted()`.

    The retrying form: *fn* receives a started interpreter and may be
    invoked up to ``retries + 1`` times under `OptimisticLock`.
    """
    strategy = lock if lock is not None else _DEFAULT_LOCK
    return strategy.run(store, key, machine, fn, **kw)
