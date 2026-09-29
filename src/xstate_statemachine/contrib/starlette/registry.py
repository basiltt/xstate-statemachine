# src/xstate_statemachine/contrib/starlette/registry.py
# -----------------------------------------------------------------------------
# ðŸ—‚ï¸ StatechartRegistry -- create â†’ act â†’ persist â†’ discard, over HTTP
# -----------------------------------------------------------------------------
# ðŸ›ï¸ Under N workers there is no shared memory, so the honest model is:
#    per request, load the snapshot, run ONE async `Interpreter` over it,
#    save with `expected_version`, and throw the interpreter away. That is
#    `persistence.apersisted` (#260) -- `act()` is a thin wrapper that adds
#    the registry's plugins, the idempotency inbox (#261), strict mode and
#    a post-save fan-out to SSE/WebSocket subscribers.
#
# ðŸ  `resident()` is the opt-in exception: a long-lived in-process actor for
#    single-worker deployments and dev. Bounded (`max_residents`, idle TTL,
#    X0.11/12), stopped -- and saved -- on eviction and on shutdown.
#
# â° Timers: a persisted `after` deadline is woken by `DueTimerScanner`
#    (#264), which `lifespan` runs in a daemon thread when `run_timers=True`.
#
# ðŸ” X0.1 closed-by-default: `register(authorize=)` is REQUIRED; `allow_all`
#    is the explicit, logged opt-out.
# -----------------------------------------------------------------------------
"""`StatechartRegistry` and the `allow_all` authorizer."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from ...events import Receipt
from ...interpreter import Interpreter
from ...models import MachineNode
from ...persistence.async_store import as_async
from ...persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    IdempotencyPlugin,
)
from ...persistence.locking import _restore_kwargs, apersisted
from ...persistence.store import validate_key
from ...plugins import PluginBase
from ._fanout import _Subscribers
from ._http import (
    ForbiddenError,
    idempotency_key_from,
    json_body,
    problem,
    problem_for_exception,
    receipt_body,
    receipt_to_status,
    state_body,
)

logger = logging.getLogger(__name__)

__all__ = ["Authorizer", "StatechartRegistry", "allow_all"]

Authorizer = Callable[..., Union[bool, Awaitable[bool]]]
#: Separator between machine name and instance key in the STORE key.
#: Names may not contain it; keys may (the split is on the first one).
KEY_SEP = "."
_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")

_allow_all_warned = threading.Event()


def allow_all(
    conn: HTTPConnection, *, name: str, key: str, event: Optional[str]
) -> bool:
    """Authorizer that admits everything. Logs a WARNING the first time
    it is USED, so an accidental production deployment is visible."""
    if not _allow_all_warned.is_set():
        _allow_all_warned.set()
        logger.warning(
            "âš ï¸ xstate-statemachine: `allow_all` authorizer in use for "
            "machine %r -- every client may read and drive every "
            "instance. Do not ship this to production (X0.1).",
            name,
        )
    return True


@dataclass
class _Registration:
    name: str
    machine: MachineNode[Any]
    authorize: Authorizer
    context_serializer: Optional[Callable[[Any], Any]]
    strict: Optional[bool]


class _Recorder(PluginBase):  # type: ignore[type-arg]
    """Collect the changed USER receipts of one `act()` for fan-out."""

    def __init__(self) -> None:
        self.changed: List[Receipt] = []

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Receipt
    ) -> None:
        etype = str(getattr(event, "type", ""))
        if receipt.changed and not etype.startswith(_INTERNAL_PREFIXES):
            self.changed.append(receipt)


class _SkipSave(Exception):
    """Raised inside `act()` to leave without persisting (duplicates)."""

    def __init__(self, receipt: Receipt, body: Dict[str, Any]) -> None:
        super().__init__("skip save")
        self.receipt = receipt
        self.body = body


class _Resident:
    __slots__ = ("interp", "version", "last_used")

    def __init__(self, interp: Any, version: int, now: float) -> None:
        self.interp = interp
        self.version = version
        self.last_used = now


class StatechartRegistry:
    """Named machines over one store, exposed to an ASGI app.

    Args:
        store: A sync `StateStore` or an `AsyncStateStore`. Sync stores
            are wrapped with `as_async()` for requests; the timer scanner
            needs the sync store itself.
        lock: `OptimisticLock()` (default) / `PessimisticLock()`.
        clock: Forwarded to every interpreter.
        plugins: Attached to every interpreter `act()` / `resident()`
            builds (audit, observability ...).
        migrator: Forwarded to `apersisted` (#263).
        inbox: An `InboxStore`; when given, `act()` attaches an
            `IdempotencyPlugin` scoped to the caller's principal (X0.2).
        principal: ``(conn) -> str`` naming the authenticated caller; used
            by `send_event` / the WebSocket endpoint as the idempotency
            scope. Required together with *inbox* for those helpers.
        max_residents: Cap on resident actors (LRU-evicted beyond it).
        resident_idle_ttl_s: A resident idle this long is evicted.
        max_connections_per_key: Concurrent SSE + WebSocket clients per
            instance; beyond it the connection is refused.
        drain_timeout_s: Upper bound on shutdown work in `lifespan`.
        run_timers: Start a `DueTimerScanner` under `lifespan`.
        scanner_interval_s: Scanner poll interval.
        scanner_now: Inject ``() -> float`` epoch seconds (tests).
        heartbeat_s: SSE comment / WebSocket ping interval.
        allowed_origins: Extra ``Origin`` values accepted on SSE/WS besides
            same-origin (X0.7).
        max_body_bytes: `json_body` cap for `send_event`.
    """

    def __init__(
        self,
        store: Any,
        *,
        lock: Optional[Any] = None,
        clock: Optional[Any] = None,
        plugins: Iterable[Any] = (),
        migrator: Optional[Any] = None,
        inbox: Optional[Any] = None,
        principal: Optional[Callable[[HTTPConnection], str]] = None,
        max_residents: int = 1000,
        resident_idle_ttl_s: float = 300.0,
        max_connections_per_key: int = 16,
        drain_timeout_s: float = 10.0,
        run_timers: bool = False,
        scanner_interval_s: float = 1.0,
        scanner_now: Optional[Callable[[], float]] = None,
        heartbeat_s: float = 15.0,
        allowed_origins: Iterable[str] = (),
        max_body_bytes: Optional[int] = None,
    ) -> None:
        if max_residents < 1:
            raise ValueError("max_residents must be >= 1")
        if max_connections_per_key < 1:
            raise ValueError("max_connections_per_key must be >= 1")
        self.store = store
        is_async = inspect.iscoroutinefunction(getattr(store, "load", None))
        self._sync_store = None if is_async else store
        self._astore = store if is_async else as_async(store)
        self.lock = lock
        self.clock = clock
        self.plugins = list(plugins)
        self.migrator = migrator
        self.inbox = inbox
        self.principal = principal
        self.max_residents = int(max_residents)
        self.resident_idle_ttl_s = float(resident_idle_ttl_s)
        self.max_connections_per_key = int(max_connections_per_key)
        self.drain_timeout_s = float(drain_timeout_s)
        self.run_timers = bool(run_timers)
        self.scanner_interval_s = float(scanner_interval_s)
        self.scanner_now = scanner_now
        self.heartbeat_s = float(heartbeat_s)
        self.allowed_origins = frozenset(allowed_origins)
        from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

        self.max_body_bytes = (
            DEFAULT_MAX_SNAPSHOT_BYTES
            if max_body_bytes is None
            else int(max_body_bytes)
        )
        self._regs: Dict[str, _Registration] = {}
        self._residents: "OrderedDict[Tuple[str, str], _Resident]" = (
            OrderedDict()
        )
        # 📝 Created lazily: on Python 3.9 syncio.Lock() binds to the
        #    current loop at construction and raises with no running loop --
        #    and a registry is built at import time, before the server starts.
        self.__resident_lock: Optional[asyncio.Lock] = None
        self.subscribers = _Subscribers()
        self._connections: Dict[Tuple[str, str], int] = {}
        self.scanner: Optional[Any] = None
        self._scanner_thread: Optional[threading.Thread] = None
        self.started = False
        self.draining = False
        #: Monotonic source for resident idle accounting (tests patch it).
        self.monotonic: Callable[[], float] = time.monotonic

    def _lock(self) -> asyncio.Lock:
        if self.__resident_lock is None:
            self.__resident_lock = asyncio.Lock()
        return self.__resident_lock

    # -- registration -------------------------------------------------------
    def register(
        self,
        name: str,
        machine: MachineNode[Any],
        *,
        authorize: Authorizer,
        context_serializer: Optional[Callable[[Any], Any]] = None,
        strict: Optional[bool] = None,
    ) -> None:
        """Register *machine* as *name*.

        Args:
            authorize: ``(conn, *, name, key, event) -> bool`` (sync or
                async). ``event`` is ``None`` for reads / connects.
                Required: pass `allow_all` to opt out explicitly.
            context_serializer: ``(context) -> JSON`` -- when given,
                responses include ``context``; otherwise state only.
            strict: Override `machine.strict` for requests (undeclared
                events â†’ 422 instead of 200-unchanged).
        """
        if not callable(authorize):
            raise TypeError(
                "register(authorize=) is required and must be callable; "
                "pass `allow_all` to opt out explicitly (X0.1)."
            )
        if not name or KEY_SEP in name:
            raise ValueError(
                f"Machine name {name!r} must be non-empty and must not "
                f"contain {KEY_SEP!r}."
            )
        if name in self._regs:
            raise ValueError(f"Machine name {name!r} is already registered.")
        self._regs[name] = _Registration(
            name, machine, authorize, context_serializer, strict
        )

    @property
    def machines(self) -> Mapping[str, MachineNode[Any]]:
        return {n: r.machine for n, r in self._regs.items()}

    def _reg(self, name: str) -> _Registration:
        try:
            return self._regs[name]
        except KeyError:
            raise KeyError(f"No machine registered as {name!r}.") from None

    def store_key(self, name: str, key: str) -> str:
        """The store key an instance lives under: ``"<name>.<key>"``."""
        self._reg(name)
        return validate_key(f"{name}{KEY_SEP}{key}")

    def machine_for_store_key(self, store_key: str) -> MachineNode[Any]:
        return self._reg(store_key.split(KEY_SEP, 1)[0]).machine

    # -- authorization ------------------------------------------------------
    async def authorize(
        self,
        conn: HTTPConnection,
        name: str,
        key: str,
        event: Optional[str] = None,
    ) -> None:
        """Raise `ForbiddenError` unless the registered authorizer admits."""
        verdict = self._reg(name).authorize(
            conn, name=name, key=key, event=event
        )
        if inspect.isawaitable(verdict):
            verdict = await verdict
        if not verdict:
            raise ForbiddenError()

    # -- create â†’ act â†’ persist â†’ discard ------------------------------------
    @contextlib.asynccontextmanager
    async def act(
        self, name: str, key: str, *, principal: Optional[str] = None
    ) -> AsyncIterator[Interpreter]:
        """Yield a started async `Interpreter` for *key*; save on exit.

        Built by `persistence.apersisted` over `as_async(store)`: one
        interpreter per call, saved with `expected_version`, then stopped.
        A `ConflictError` on save means another writer won -- the caller
        retries (HTTP 409).

        Args:
            principal: The authenticated caller. **Required** when the
                registry has an *inbox* -- it scopes idempotency keys
                (X0.2).
        """
        reg = self._reg(name)
        skey = self.store_key(name, key)
        plugins = list(self.plugins)
        if self.inbox is not None:
            if principal is None:
                raise ValueError(
                    "act(principal=) is required when the registry has an "
                    "idempotency inbox (X0.2)."
                )
            who = str(principal)
            plugins.append(
                IdempotencyPlugin(self.inbox, principal=lambda e: who)
            )
        recorder = _Recorder()
        plugins.append(recorder)
        async with apersisted(
            self._astore,
            skey,
            reg.machine,
            lock=self.lock,
            clock=self.clock,
            plugins=plugins,
            migrator=self.migrator,
        ) as interp:
            if reg.strict is not None:
                interp.strict = reg.strict
            interp._xsm_context_serializer = reg.context_serializer
            yield interp
            bodies = [
                receipt_body(
                    interp, r, context_serializer=reg.context_serializer
                )
                for r in recorder.changed
            ]
        # âœ… Only after the save committed: subscribers never see a
        #    transition that a conflict rolled back.
        if bodies:
            self.subscribers.publish(name, str(key), bodies)

    async def exists(self, name: str, key: str) -> bool:
        """Whether instance *key* of *name* has a stored snapshot."""
        return await self._astore.load(self.store_key(name, key)) is not None

    async def peek(self, name: str, key: str) -> Dict[str, Any]:
        """The current state body WITHOUT saving (SSE/WS connect).

        A missing instance reports the machine's initial state.
        """
        reg = self._reg(name)
        rec = await self._astore.load(self.store_key(name, key))
        interp: Any
        if rec is not None:
            interp = Interpreter.from_snapshot(
                rec.snapshot, reg.machine, clock=self.clock
            )
            body = state_body(interp, reg.context_serializer)
        else:
            interp = Interpreter(reg.machine, clock=self.clock)
            await interp.start()
            try:
                body = state_body(interp, reg.context_serializer)
            finally:
                await interp.stop()
        return body

    # -- one-call HTTP helper -------------------------------------------------
    async def send_event(
        self,
        request: Request,
        name: str,
        key: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        principal: Optional[str] = None,
    ) -> Response:
        """Authorize, read the JSON body (unless *payload*), honour
        ``Idempotency-Key``, `act()`, and answer with `ReceiptResponse` --
        or an RFC 9457 problem. Never raises for request-level failures.

        Args:
            principal: The authenticated caller, when a framework resolved
                it already (FastAPI's ``actor_from_request`` dependency).
                Defaults to the registry's ``principal(conn)`` callable.
        """
        try:
            await self.authorize(request, name, key, event_type)
            if payload is None:
                payload = await json_body(
                    request, max_body_bytes=self.max_body_bytes
                )
            payload = dict(payload)
            idem = idempotency_key_from(request)
            if idem is not None:
                payload["idempotency_key"] = idem
            if principal is None:
                principal = self._principal_of(request)
            reg = self._reg(name)
            try:
                async with self.act(name, key, principal=principal) as interp:
                    receipt = await interp.send(
                        event_type, wait=True, **payload
                    )
                    body = receipt_body(
                        interp,
                        receipt,
                        context_serializer=reg.context_serializer,
                    )
                    if receipt.duplicate:
                        # 🔁 A replay / in-flight refusal changed nothing:
                        #    do NOT save. Saving would bump the version and
                        #    make the ORIGINAL request's save lose with a
                        #    409 -- under a burst of retries with one key,
                        #    nobody would win (#277 load test).
                        raise _SkipSave(receipt, body)
            except _SkipSave as skip:
                receipt, body = skip.receipt, skip.body
            # 🧾 An idempotency REFUSAL (same key, different body → 422;
            #    still in flight → 409) is an error to the caller, so it is
            #    an RFC 9457 problem like every other 4xx -- not a receipt
            #    body with a 4xx status, which is what the wheel shipped
            #    (found by the clean-venv battle test). A plain replay
            #    (duplicate=True, no error) keeps the original receipt.
            if receipt.error is not None and isinstance(
                receipt.error,
                (IdempotencyMismatchError, IdempotencyInFlightError),
            ):
                return problem_for_exception(receipt.error)
            return JSONResponse(body, status_code=receipt_to_status(receipt))
        except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
            if receipt_to_status_is_server_error(exc):
                logger.exception(
                    "ðŸ”¥ %s %r failed on %s/%s",
                    type(exc).__name__,
                    event_type,
                    name,
                    key,
                )
            return problem_for_exception(exc)

    def _principal_of(self, conn: HTTPConnection) -> Optional[str]:
        if self.inbox is None:
            return None
        if self.principal is None:
            raise ValueError(
                "StatechartRegistry(principal=) is required with inbox= "
                "for the HTTP helpers (X0.2)."
            )
        return str(self.principal(conn))

    # -- residents ------------------------------------------------------------
    @property
    def residents(self) -> int:
        return len(self._residents)

    async def resident(self, name: str, key: str) -> Interpreter:
        """A long-lived in-process actor for *key* (opt-in).

        Loaded from the store on first use, LRU/TTL-evicted, and saved
        (with `expected_version`) + stopped when evicted, released or on
        shutdown. Single-process only: two workers holding the same key as
        residents will conflict on save.
        """
        reg = self._reg(name)
        topic = (name, str(key))
        async with self._lock():
            await self._evict_idle_locked()
            now = self.monotonic()
            res = self._residents.get(topic)
            if res is not None:
                res.last_used = now
                self._residents.move_to_end(topic)
                return res.interp
            if self.draining:
                raise RuntimeError("registry is shutting down")
            skey = self.store_key(name, key)
            rec = await self._astore.load(skey)
            if rec is None:
                interp = Interpreter(reg.machine, clock=self.clock)
                for p in self.plugins:
                    interp.use(p)
                version = 0
            else:
                interp = Interpreter.from_snapshot(
                    rec.snapshot,
                    reg.machine,
                    clock=self.clock,
                    plugins=list(self.plugins),
                    **_restore_kwargs(self.migrator, None),
                )
                version = rec.version
            interp.store_key = skey
            if reg.strict is not None:
                interp.strict = reg.strict
            await interp.start()
            self._residents[topic] = _Resident(interp, version, now)
            while len(self._residents) > self.max_residents:
                old_topic, old = self._residents.popitem(last=False)
                await self._retire(old_topic, old)
            return interp

    async def release_resident(self, name: str, key: str) -> None:
        """Save and stop the resident for *key* (no-op if none)."""
        async with self._lock():
            res = self._residents.pop((name, str(key)), None)
            if res is not None:
                await self._retire((name, str(key)), res)

    async def evict_idle(self) -> int:
        """Retire residents idle longer than `resident_idle_ttl_s`."""
        async with self._lock():
            return await self._evict_idle_locked()

    async def _evict_idle_locked(self) -> int:
        cutoff = self.monotonic() - self.resident_idle_ttl_s
        stale = [t for t, r in self._residents.items() if r.last_used < cutoff]
        for topic in stale:
            await self._retire(topic, self._residents.pop(topic))
        return len(stale)

    async def _retire(self, topic: Tuple[str, str], res: _Resident) -> None:
        interp = res.interp
        try:
            if interp.status == "running":
                await self._astore.save(
                    interp.store_key,
                    interp.get_snapshot(),
                    expected_version=res.version,
                    machine_version=interp.machine.version or "",
                    deadlines=tuple(interp._persist_deadlines()),
                )
        except Exception:  # noqa: BLE001 -- eviction must not fail
            logger.exception(
                "ðŸ”¥ resident %s/%s: save on retire failed", *topic
            )
        finally:
            with contextlib.suppress(Exception):
                await interp.stop()

    async def _retire_all(self) -> None:
        async with self._lock():
            while self._residents:
                topic, res = self._residents.popitem(last=False)
                await self._retire(topic, res)

    # -- connection accounting (SSE + WS) --------------------------------------
    def try_open_connection(self, name: str, key: str) -> bool:
        topic = (name, str(key))
        n = self._connections.get(topic, 0)
        if n >= self.max_connections_per_key or self.draining:
            return False
        self._connections[topic] = n + 1
        return True

    def close_connection(self, name: str, key: str) -> None:
        topic = (name, str(key))
        n = self._connections.get(topic, 0) - 1
        if n <= 0:
            self._connections.pop(topic, None)
        else:
            self._connections[topic] = n

    def connections(self, name: Optional[str] = None, key: Any = None) -> int:
        if name is None:
            return sum(self._connections.values())
        return self._connections.get((name, str(key)), 0)

    def origin_allowed(self, conn: HTTPConnection) -> bool:
        """X0.7: no ``Origin`` (non-browser), same-origin, or allow-listed."""
        origin = conn.headers.get("origin")
        if origin is None:
            return True
        if origin in self.allowed_origins:
            return True
        host = conn.headers.get("host")
        if not host:
            return False
        bare = origin.split("://", 1)[-1].rstrip("/")
        return bare == host

    # -- lifespan -------------------------------------------------------------
    def _start_scanner(self) -> None:
        from ...persistence.timers import DueTimerScanner

        if self._sync_store is None:
            raise RuntimeError(
                "run_timers=True needs a sync StateStore (the scanner runs "
                "in a thread); pass the sync store to the registry."
            )
        self.scanner = DueTimerScanner(
            self._sync_store,
            self.machine_for_store_key,
            lock=self.lock,
            plugins=self.plugins,
            now=self.scanner_now,
            migrator=self.migrator,
        )
        scanner = self.scanner
        self._scanner_thread = threading.Thread(
            target=scanner.run_forever,
            args=(self.scanner_interval_s,),
            name="xsm-timer-scanner",
            daemon=True,
        )
        self._scanner_thread.start()

    def _stop_scanner(self, timeout: float) -> None:
        if self.scanner is not None:
            self.scanner.stop()
        if self._scanner_thread is not None:
            self._scanner_thread.join(timeout)
            if self._scanner_thread.is_alive():
                logger.warning(
                    "âš ï¸ timer scanner did not stop in %.1fs", timeout
                )
        self.scanner = None
        self._scanner_thread = None

    @contextlib.asynccontextmanager
    async def lifespan(self, app: Any = None) -> AsyncIterator[None]:
        """``Starlette(lifespan=registry.lifespan)``.

        Startup: optionally start the timer scanner. Shutdown: stop
        accepting streams, close subscribers, save+stop residents and stop
        the scanner -- bounded by `drain_timeout_s` (X0.11).
        """
        self.draining = False
        if self.run_timers:
            self._start_scanner()
        self.started = True
        try:
            yield
        finally:
            self.draining = True
            self.started = False
            self.subscribers.close_all()
            deadline = time.monotonic() + self.drain_timeout_s
            try:
                await asyncio.wait_for(
                    self._retire_all(), timeout=self.drain_timeout_s
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "âš ï¸ resident drain exceeded %.1fs; abandoning %d",
                    self.drain_timeout_s,
                    len(self._residents),
                )
                self._residents.clear()
            left = max(0.0, deadline - time.monotonic())
            await asyncio.get_running_loop().run_in_executor(
                None, self._stop_scanner, left
            )

    # -- probes ----------------------------------------------------------------
    def health_route(self, path: str = "/_xsm/health") -> Route:
        """Liveness: 200 while the process can answer."""

        async def health(request: Request) -> Response:
            return JSONResponse({"status": "ok"})

        return Route(path, health, methods=["GET"])

    def ready_route(self, path: str = "/_xsm/ready") -> Route:
        """Readiness: 200 once `lifespan` started, the store answers and we
        are not draining; else a 503 problem."""

        async def ready(request: Request) -> Response:
            if not self.started or self.draining:
                return problem(503, "Not Ready")
            probe = getattr(self._astore, "health", None)
            if probe is not None:
                try:
                    info = await probe()
                except Exception as exc:  # noqa: BLE001
                    return problem(
                        503, "Store unavailable", error=type(exc).__name__
                    )
                if isinstance(info, dict) and info.get("ok") is False:
                    return problem(503, "Store unavailable")
            return JSONResponse(
                {
                    "status": "ready",
                    "residents": self.residents,
                    "timers": self.scanner is not None,
                }
            )

        return Route(path, ready, methods=["GET"])


def receipt_to_status_is_server_error(exc: BaseException) -> bool:
    from ._http import status_for_exception

    return status_for_exception(exc) >= 500
