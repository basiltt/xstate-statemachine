# src/xstate_statemachine/contrib/flask/extension.py
# -----------------------------------------------------------------------------
# 🧪 XState -- the Flask extension: init_app, register, act, receipt_response
# -----------------------------------------------------------------------------
# 🏛️ Application-factory friendly: `XState()` holds only DECLARATIONS
#    (``register`` calls made before / without an app, like blueprint
#    routes); each app's state -- store, lock, plugins, inbox, the SSE
#    fan-out -- lives in ``app.extensions["xstate"]`` (`AppRegistry`). Two
#    apps built from one `XState()` never share a store.
#
#    `act(name, key)` is `persistence.persisted()` with the app's lock /
#    plugins / inbox: load → yield a started `SyncInterpreter` → save on a
#    clean exit (nothing written on an exception) → stop. The optimistic
#    default raises `ConflictError` (HTTP 409) when another writer won; the
#    CALLER retries -- or pass ``lock=PessimisticLock()`` to `init_app`.
#
# 🔐 X0.1 `register(authorize=)` required; X0.2 principal-scoped
#    ``Idempotency-Key``; X0.7 JSON only / 413 / 415 / problems without
#    exception text; a state-changing `act()` inside a GET/HEAD/OPTIONS
#    request is REFUSED (405) -- safe methods must stay safe.
# -----------------------------------------------------------------------------
"""`XState` extension, `receipt_response`, `problem_response`."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional

from flask import Flask, Response, current_app, g, has_request_context
from flask import request as flask_request

from ...events import Receipt
from ...exceptions import StoreUnavailableError
from ...persistence.locking import _restore_kwargs, persisted
from ...persistence.log import TransitionLogPlugin
from ...plugins import PluginBase
from ...receipts import receipt_to_status
from ...sync_interpreter import SyncInterpreter
from ._core import (
    EXTENSION_KEY,
    REQUIRED,
    AppRegistry,
    Registration,
    make_registration,
)
from ._http import (
    PROBLEM_MEDIA_TYPE,
    MethodNotAllowedError,
    is_idempotency_refusal,
    mapped_exceptions,
    problem_for_exception,
    receipt_body,
    state_body,
)

logger = logging.getLogger(__name__)

__all__ = ["XState", "problem_response", "receipt_response"]

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")


def _json(body: Any, status: int, mimetype: str = "application/json") -> Any:
    return Response(
        json.dumps(body, default=str), status=status, mimetype=mimetype
    )


def problem_response(exc: BaseException) -> Any:
    """An RFC 9457 ``application/problem+json`` response for *exc* --
    fixed title and class name, never the exception text (X0.7)."""
    status, body = problem_for_exception(exc)
    if isinstance(exc, StoreUnavailableError):
        # 🔌 #306 battle (agent B): a backend outage is ONE warning line
        #    per request, as in the Starlette registry -- a Redis failover
        #    under load used to write a full traceback per request here.
        logger.warning(
            "🔌 store unavailable; %s %s answered 503: %s",
            flask_request.method if has_request_context() else "-",
            flask_request.path if has_request_context() else "-",
            exc,
        )
    elif status >= 500:
        # 📝 Full traceback in the SERVER log (operators need it); the
        #    client body still carries only the class name (X0.7).
        logger.exception(
            "🔥 %s while handling a statechart request", type(exc).__name__
        )
    return _json(body, status, PROBLEM_MEDIA_TYPE)


def receipt_response(
    interp: Any,
    receipt: Receipt,
    *,
    status: Optional[int] = None,
    context_serializer: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """JSON response for *receipt*; status from the CORE
    `receipts.receipt_to_status` table (200 / 202 deferred / 409 denied /
    422 key mismatch / 500 error). An idempotency refusal (key reused with
    a different body, or still in flight) is an RFC 9457 problem."""
    if receipt.error is not None and is_idempotency_refusal(receipt):
        return problem_response(receipt.error)
    if context_serializer is None:
        context_serializer = getattr(interp, "_xsm_context_serializer", None)
    body = receipt_body(interp, receipt, context_serializer=context_serializer)
    return _json(
        body, receipt_to_status(receipt) if status is None else status
    )


class _Recorder(PluginBase):  # type: ignore[type-arg]
    """Collect changed USER receipts of one `act()` for the SSE fan-out."""

    def __init__(self) -> None:
        self.changed: List[Receipt] = []

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Receipt
    ) -> None:
        etype = str(getattr(event, "type", ""))
        if receipt.changed and not etype.startswith(_INTERNAL_PREFIXES):
            self.changed.append(receipt)


class _SkipSave(Exception):
    """Raised inside `act()` to leave WITHOUT persisting (a duplicate)."""


class _Bound:
    """``g.xsm``: the current app's `XState` operations, bound."""

    def __init__(self, ext: "XState") -> None:
        self._ext = ext

    def act(self, name: str, key: Any = None, **kw: Any) -> Any:
        return self._ext.act(name, key, **kw)

    def peek(self, name: str, key: Any) -> Dict[str, Any]:
        return self._ext.peek(name, key)

    def skip_save(self) -> None:
        # 📝 #285 battle: `g.xsm` is the handle the guide hands out, and it
        #    could `act()` but not leave the block without saving.
        self._ext.skip_save()

    @property
    def registry(self) -> AppRegistry:
        return self._ext.registry()


class XState:
    """The Flask extension.

    ::

        xsm = XState()
        xsm.register("order", order_machine, authorize=can_touch_order)

        def create_app():
            app = Flask(__name__)
            xsm.init_app(app, store=SQLiteStore("app.db"))
            app.register_blueprint(
                create_statechart_blueprint(xsm, "order", "/orders")
            )
            return app
    """

    def __init__(self, app: Optional[Flask] = None, **kw: Any) -> None:
        #: Declarations shared by every app (config, not app state).
        self._declared: Dict[str, Registration] = {}
        if app is not None:
            self.init_app(app, **kw)

    # -- setup ---------------------------------------------------------------------
    def init_app(
        self,
        app: Flask,
        store: Any = None,
        *,
        lock: Optional[Any] = None,
        plugins: Any = (),
        inbox: Optional[Any] = None,
        principal: Optional[Callable[[Any], Any]] = None,
        log: Optional[Any] = None,
        clock: Optional[Any] = None,
        migrator: Optional[Any] = None,
        max_body_bytes: Optional[int] = None,
        heartbeat_s: float = 15.0,
        max_connections_per_key: int = 16,
        allowed_origins: Any = (),
        cli: bool = True,
        error_handlers: bool = True,
    ) -> None:
        """Bind a store (and policies) to *app*.

        Args:
            store: A `StateStore` (`SQLiteStore`, `SQLAlchemyStore`,
                `SessionStore` ...). Required.
            lock: `OptimisticLock()` (default) / `PessimisticLock()`.
            plugins: Attached to every interpreter `act()` builds.
            inbox: An `InboxStore`; enables ``Idempotency-Key`` dedup,
                scoped by *principal* (X0.2).
            principal: ``(request) -> str`` naming the authenticated
                caller. Required with *inbox*.
            log: A `TransitionLogStore`; an `AuditPlugin` is attached and
                ``GET /<id>/history`` reads it.
            max_body_bytes: JSON body cap (413); default 1 MiB.
            cli: Register the ``flask xsm`` command group.
            error_handlers: Register app-level handlers so the library's
                exceptions raised in YOUR views (a lost race, an `act()`
                in a GET, an oversized session) answer RFC 9457 problems
                (409 / 405 / 413) instead of a 500. ``False`` opts out.
        """
        plugins = list(plugins)
        if log is not None:
            from ...persistence.log import AuditPlugin

            plugins.append(AuditPlugin(log))
        else:
            for p in plugins:
                if isinstance(p, TransitionLogPlugin):
                    log = p.log
        reg = AppRegistry(
            store,
            lock=lock,
            plugins=plugins,
            inbox=inbox,
            principal=principal,
            log=log,
            clock=clock,
            migrator=migrator,
            max_body_bytes=max_body_bytes,
            heartbeat_s=heartbeat_s,
            max_connections_per_key=max_connections_per_key,
            allowed_origins=allowed_origins,
        )
        reg.shared = self._declared
        app.extensions[EXTENSION_KEY] = reg
        ext = self

        @app.before_request
        def _bind_g() -> None:
            g.xsm = _Bound(ext)

        # 🔐 #285 battle (A): `act()` in the APP'S OWN views raised a bare
        #    `MethodNotAllowedError` (GET) / `ConflictError` (lost race)
        #    that Flask answered as an HTML 500 -- the documented 405 / 409
        #    only held inside the blueprint. App-level handlers for the
        #    library's mapped exceptions only; an app's own handler for one
        #    of them, registered after `init_app`, still wins.
        if error_handlers:
            for exc_cls in mapped_exceptions():
                app.register_error_handler(exc_cls, problem_response)

        if cli:
            from .cli import xsm_cli

            app.cli.add_command(xsm_cli)

    def registry(self, app: Optional[Flask] = None) -> AppRegistry:
        """The `AppRegistry` of *app* (default: `current_app`)."""
        app = app or current_app._get_current_object()  # type: ignore
        try:
            reg: AppRegistry = app.extensions[EXTENSION_KEY]
        except KeyError:
            raise RuntimeError(
                "XState.init_app(app, store=...) was not called for this app"
            ) from None
        return reg

    def register(
        self,
        name: str,
        machine: Any,
        *,
        key: Optional[Callable[[], Any]] = None,
        authorize: Any = REQUIRED,
        context_serializer: Optional[Callable[[Any], Any]] = None,
        strict: Optional[bool] = None,
        source: Any = None,
        app: Optional[Flask] = None,
    ) -> None:
        """Register *machine* as *name*.

        Args:
            machine: A `MachineNode`, a JSON path, or a config dict.
            key: ``() -> str`` giving the instance key when a view calls
                ``act(name)`` without one (e.g. from the session).
            authorize: ``(request, *, name, key, event) -> bool``.
                **Required** (X0.1); pass `allow_all` to opt out
                explicitly. ``event`` is ``None`` for reads.
            context_serializer: ``(context) -> JSON``; without it responses
                carry state only (X0.1).
            strict: Override ``machine.strict`` for requests.
            source: The machine's JSON (path or dict) for ``flask xsm``
                when *machine* is a `MachineNode`.
            app: Register on this app only; default: every app this
                extension initialises (and the current app, if any).
        """
        reg = make_registration(
            name,
            machine,
            key=key,
            authorize=authorize,
            context_serializer=context_serializer,
            strict=strict,
            source=source,
        )
        if app is not None:
            self.registry(app).add(reg)
            return
        if name in self._declared:
            raise ValueError(f"Machine name {name!r} is already registered.")
        self._declared[name] = reg

    # -- act -----------------------------------------------------------------------
    def _reg(self, name: str) -> Registration:
        return self.registry().reg(name)

    @contextlib.contextmanager
    def act(
        self,
        name: str,
        key: Any = None,
        *,
        principal: Optional[Any] = None,
    ) -> Iterator[SyncInterpreter[Any]]:
        """Yield a started `SyncInterpreter` for *key*; save on clean exit.

        Refused with `MethodNotAllowedError` (405) inside a GET / HEAD /
        OPTIONS request: safe methods must not change state (X0.7).
        """
        if has_request_context() and flask_request.method in _SAFE_METHODS:
            raise MethodNotAllowedError()
        r = self.registry()
        reg = r.reg(name)
        k = r.key_for(name, key)
        skey = r.store_key(name, k)
        if principal is None and r.inbox is not None and has_request_context():
            principal = r.principal(flask_request)  # type: ignore[misc]
        plugins = r.plugins_for(principal)
        recorder = _Recorder()
        plugins.append(recorder)
        skipped = False
        bodies: List[Dict[str, Any]] = []
        try:
            with persisted(
                r.store,
                skey,
                reg.machine,
                lock=r.lock,
                clock=r.clock,
                plugins=plugins,
                migrator=r.migrator,
            ) as interp:
                if reg.strict is not None:
                    interp.strict = reg.strict
                interp._xsm_context_serializer = reg.context_serializer
                interp._xsm_key = k
                yield interp
                bodies = [
                    receipt_body(
                        interp, rc, context_serializer=reg.context_serializer
                    )
                    for rc in recorder.changed
                ]
        except _SkipSave:
            skipped = True
        if not skipped and bodies:
            # ✅ Only after the save committed.
            r.fanout.publish(name, k, bodies)

    def skip_save(self) -> None:
        """Leave the enclosing `act()` block WITHOUT saving (used for
        idempotent replays, which must not bump the version)."""
        raise _SkipSave()

    def peek(self, name: str, key: Any) -> Dict[str, Any]:
        """The current state body WITHOUT saving; a missing instance
        reports the machine's initial state."""
        r = self.registry()
        reg = self._reg(name)
        rec = r.store.load(r.store_key(name, key))
        if rec is None:
            interp = SyncInterpreter(reg.machine, clock=r.clock).start()
            try:
                return state_body(interp, reg.context_serializer)
            finally:
                interp.stop()
        # 🧬 #263 battle: a read of a stale instance migrates like a write
        #    does (read-only; the next `act()` re-saves at the new label).
        interp = SyncInterpreter.from_snapshot(
            rec.snapshot,
            reg.machine,
            clock=r.clock,
            **_restore_kwargs(r.migrator, None),
        )
        return state_body(interp, reg.context_serializer)
