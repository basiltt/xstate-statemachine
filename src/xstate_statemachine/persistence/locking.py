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
import contextvars
import inspect
import time
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
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
    "DEFAULT_RESTART_TIMERS",
]

T = TypeVar("T")

#: ⏰ #264: `persisted()` re-arms persisted `after` deadlines with their
#: REMAINING wall time by default -- the whole point of durable timers.
DEFAULT_RESTART_TIMERS: Any = "resume"

#: Retry backoff for `OptimisticLock`: short, jittered -- a conflict means
#: another writer JUST finished, so a few ms of decorrelated wait is enough
#: to break the herd without adding latency a user notices.
DEFAULT_BACKOFF = RetryPolicy(
    max_attempts=6, base_ms=2.0, factor=2.0, max_ms=100.0, jitter="full"
)

#: 🔑 #293: the persisted() block the current thread / task is inside.
#:    A `contextvars.ContextVar` is per-thread AND per-asyncio-task, so a
#:    plugin shared by concurrent blocks (the dispatcher runs subjects on
#:    worker threads; `apersisted` blocks interleave on one loop) can key
#:    its post-save buffer by the block that produced it. ``None`` outside
#:    any block.
current_session: "contextvars.ContextVar[Optional[object]]" = (
    contextvars.ContextVar("xsm_persisted_session", default=None)
)
#: Callbacks to run once the OUTERMOST persisted() scope -- including the
#: `PessimisticLock` transaction -- has exited cleanly (see `after_commit`).
_post_commit: "contextvars.ContextVar[Optional[List[Callable[[], Any]]]]" = (
    contextvars.ContextVar("xsm_post_commit", default=None)
)


def after_commit(fn: Callable[[], Any]) -> None:
    """Run *fn* after the enclosing persisted() block has committed.

    For non-transactional side effects (a direct broker publish) that must
    not happen for a state a rollback discards. Outside any block, *fn*
    runs immediately. Dropped if the block raises.

    Callbacks run in registration order once the OUTERMOST block (a nested
    `persisted()` on another key included) has saved and released its
    lock. Every callback runs even if an earlier one raises; the first
    error is then re-raised -- the save is already durable, so do NOT
    retry the block on it. Inside `apersisted` a callback may return an
    awaitable (an ``async def``); it is awaited. Under the sync
    `persisted()` an awaitable result is a `TypeError` (never silently
    dropped).
    """
    pending = _post_commit.get()
    if pending is None:
        _run_callbacks([fn], allow_async=False)
    else:
        pending.append(fn)


def _run_callbacks(
    pending: List[Callable[[], Any]], *, allow_async: bool
) -> List[Any]:
    """Run every callback; collect awaitables (async scope) or refuse them
    (sync scope); re-raise the first error after all have run."""
    first: Optional[BaseException] = None
    awaitables: List[Any] = []
    for fn in pending:
        try:
            result = fn()
            if inspect.isawaitable(result):
                if allow_async:
                    awaitables.append(result)
                else:
                    close = getattr(result, "close", None)
                    if callable(close):
                        close()
                    raise TypeError(
                        "after_commit callback returned an awaitable; "
                        "async callbacks are only awaited inside "
                        "apersisted() -- use a sync callback here"
                    )
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            if first is None:
                first = exc
    if first is not None:
        for aw in awaitables:
            close = getattr(aw, "close", None)
            if callable(close):
                close()
        raise first
    return awaitables


@contextlib.contextmanager
def _commit_scope(allow_async: bool = False) -> Iterator[List[Any]]:
    """Collect `after_commit` callbacks; run them on clean exit only.
    Nested scopes defer to the outermost. Yields a list that receives the
    awaitables the async twin must await."""
    out: List[Any] = []
    if _post_commit.get() is not None:
        yield out
        return
    pending: List[Callable[[], Any]] = []
    token = _post_commit.set(pending)
    try:
        yield out
    except BaseException:
        _post_commit.reset(token)
        raise
    _post_commit.reset(token)
    out.extend(_run_callbacks(pending, allow_async=allow_async))


@contextlib.asynccontextmanager
async def _commit_scope_async() -> AsyncIterator[None]:
    """`_commit_scope` for ``async with``; awaits coroutine callbacks."""
    with _commit_scope(allow_async=True) as awaitables:
        yield
    first: Optional[BaseException] = None
    for aw in awaitables:
        try:
            await aw
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            if first is None:
                first = exc
    if first is not None:
        raise first


@contextlib.contextmanager
def _session(markers: List[Any]) -> Iterator[object]:
    """Enter a persisted() block: a fresh session token, and
    ``buffer_marks`` on for its markers -- restored on exit so a plugin
    also used OUTSIDE persisted() goes back to writing immediately."""
    token_obj = object()
    token = current_session.set(token_obj)
    previous = [(m, getattr(m, "buffer_marks", False)) for m in markers]
    for m in markers:
        m.buffer_marks = True
    try:
        yield token_obj
    finally:
        for m, was in previous:
            m.buffer_marks = was
        current_session.reset(token)


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
        migrator: Optional[Any] = None,
        on_version_mismatch: Optional[str] = None,
        restart_timers: Any = DEFAULT_RESTART_TIMERS,
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


def _restore_kwargs(
    migrator: Optional[Any],
    on_version_mismatch: Optional[str],
    restart_timers: Any = DEFAULT_RESTART_TIMERS,
) -> Dict[str, Any]:
    """The `from_snapshot` kwargs `persisted()` forwards (#263, #264)."""
    kw: Dict[str, Any] = {"restart_timers": restart_timers}
    if migrator is not None:
        kw["migrator"] = migrator
    if on_version_mismatch is not None:
        kw["on_version_mismatch"] = on_version_mismatch
    return kw


def _cycle(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    fn: Callable[[Any], T],
    expected: Callable[[int], Optional[int]],
    clock: Optional[Clock],
    plugins: Iterable[Any],
    create_if_missing: bool,
    restore_kwargs: Optional[Dict[str, Any]] = None,
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
        restore_kwargs or {},
    )
    markers = _mark_plugins(plugins)
    interp.store_key = key  # #261: the instance identity for scoped plugins
    with _session(markers):
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
        migrator: Optional[Any] = None,
        on_version_mismatch: Optional[str] = None,
        restart_timers: Any = DEFAULT_RESTART_TIMERS,
    ) -> T:
        attempt = 0
        while True:
            attempt += 1
            try:
                with _commit_scope():
                    return _cycle(
                        store,
                        key,
                        machine,
                        fn,
                        self.fence,
                        clock,
                        plugins,
                        create_if_missing,
                        _restore_kwargs(
                            migrator, on_version_mismatch, restart_timers
                        ),
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
        migrator: Optional[Any] = None,
        on_version_mismatch: Optional[str] = None,
        restart_timers: Any = DEFAULT_RESTART_TIMERS,
    ) -> T:
        with _commit_scope(), self.acquire(store, key):
            return _cycle(
                store,
                key,
                machine,
                fn,
                self.fence,
                clock,
                plugins,
                create_if_missing,
                _restore_kwargs(migrator, on_version_mismatch, restart_timers),
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
        migrator: Optional[Any] = None,
        on_version_mismatch: Optional[str] = None,
        restart_timers: Any = DEFAULT_RESTART_TIMERS,
    ) -> T:
        with _commit_scope():
            return _cycle(
                store,
                key,
                machine,
                fn,
                self.fence,
                clock,
                plugins,
                create_if_missing,
                _restore_kwargs(migrator, on_version_mismatch, restart_timers),
            )


_DEFAULT_LOCK = OptimisticLock()


def _strategy(lock: Any) -> Any:
    """Resolve *lock*; anything that is not a strategy fails loudly here
    instead of as an ``AttributeError`` deep inside the block."""
    if lock is None:
        return _DEFAULT_LOCK
    if all(
        callable(getattr(lock, n, None)) for n in ("run", "acquire", "fence")
    ):
        return lock
    raise ValueError(
        f"lock must be a LockStrategy instance -- OptimisticLock(), "
        f"PessimisticLock() or NoLock() -- not {lock!r}"
    )


def _mark_plugins(plugins: Iterable[Any]) -> List[Any]:
    """Plugins that buffer post-save writes (`IdempotencyPlugin` #261,
    `OutboxPlugin` #293), ordered by ``flush_priority`` (lower first) so
    the inbox mark -- which stops a committed event being redelivered --
    is written before anything that may still fail."""
    found = [p for p in plugins if callable(getattr(p, "flush_marks", None))]
    return sorted(found, key=lambda p: getattr(p, "flush_priority", 0))


def _flush_all(markers: List[Any]) -> None:
    """Flush every marker even if one raises; re-raise the first error.

    📝 A failing outbox flush must not stop the inbox mark: the snapshot
    is already saved, so skipping the mark would make the dispatcher
    retry a committed event."""
    first: Optional[BaseException] = None
    for m in markers:
        try:
            m.flush_marks()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            if first is None:
                first = exc
    if first is not None:
        raise first


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
    _flush_all(markers)
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
    migrator: Optional[Any] = None,
    on_version_mismatch: Optional[str] = None,
    restart_timers: Any = DEFAULT_RESTART_TIMERS,
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

    strategy = _strategy(lock)
    with _commit_scope(), strategy.acquire(store, key):
        interp, version = _build(
            store,
            key,
            machine,
            SyncInterpreter,
            clock,
            plugins,
            create_if_missing,
            True,
            _restore_kwargs(migrator, on_version_mismatch, restart_timers),
        )
        markers = _mark_plugins(plugins)
        interp.store_key = key  # #261
        with _session(markers):
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
    migrator: Optional[Any] = None,
    on_version_mismatch: Optional[str] = None,
    restart_timers: Any = DEFAULT_RESTART_TIMERS,
) -> AsyncIterator[Any]:
    """Async twin of `persisted()`: yields a started `Interpreter`.

    *store* may be a sync `StateStore` or an `AsyncStateStore` (from
    `as_async()`); sync stores are called via the executor so the loop is
    never blocked. `PessimisticLock` holds the store's lock via the async
    adapter's ``async with``.
    """
    from ..interpreter import Interpreter
    from .async_store import as_async

    strategy = _strategy(lock)
    astore = store if _is_async_store(store) else as_async(store)

    async def _hold() -> Any:
        if isinstance(strategy, PessimisticLock):
            return astore.lock(key, timeout=strategy.timeout)
        return contextlib.nullcontext()

    lock_cm = await _hold()
    async with _commit_scope_async(), _maybe_async(lock_cm):
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
                **_restore_kwargs(
                    migrator, on_version_mismatch, restart_timers
                ),
            )
            version = record.version
        markers = _mark_plugins(plugins)
        interp.store_key = key  # #261
        with _session(markers):
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
                _flush_all(markers)
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
    strategy = _strategy(lock)
    return strategy.run(store, key, machine, fn, **kw)
