# src/xstate_statemachine/contrib/flask/quart.py
# -----------------------------------------------------------------------------
# ⚡ Quart shim -- the same extension on Flask's async twin
# -----------------------------------------------------------------------------
# 🏛️ Quart re-implements Flask's API on asyncio (and depends on Flask), so
#    the shim reuses everything framework-neutral -- `AppRegistry`, the
#    problem/body helpers, the CORE receipt status table -- and swaps only
#    the I/O: `act()` is ``async with`` over `apersisted()` (an async
#    `Interpreter`), bodies are awaited, SSE is an async generator.
#
# 📦 Soft import, NOT a separate extra: ``_registry.py`` has no ``quart``
#    entry, and adding one is a packaging decision for a later issue.
#    ``import xstate_statemachine.contrib.flask.quart`` without Quart raises
#    `MissingExtraError` with ``pip install quart`` as the hint.
# -----------------------------------------------------------------------------
"""`QuartXState` and `create_quart_statechart_blueprint` (best-effort)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import queue
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .._compat import require_extra

require_extra("flask", "quart", hint="Quart shim: pip install quart")

from quart import Blueprint, Quart, Response, current_app  # noqa: E402
from quart import request as quart_request  # noqa: E402

from ...events import Receipt  # noqa: E402
from ...interpreter import Interpreter  # noqa: E402
from ...persistence.locking import (  # noqa: E402
    DEFAULT_SETTLE_TIMEOUT,
    _restore_kwargs,
    apersisted,
)
from ...persistence.log import AuditPlugin, TransitionLogPlugin  # noqa: E402
from ...receipts import receipt_to_status  # noqa: E402
from ._core import (  # noqa: E402
    CLOSED,
    EXTENSION_KEY,
    REQUIRED,
    AppRegistry,
    Registration,
    make_registration,
)
from ._http import (  # noqa: E402
    DEFAULT_BODY_TIMEOUT_S,
    IDEMPOTENCY_HEADER,
    PROBLEM_MEDIA_TYPE,
    BadRequestError,
    MethodNotAllowedError,
    PayloadTooLargeError,
    RequestTimeoutError,
    declared_events,
    history_args,
    history_items,
    idempotency_key_from_header,
    is_idempotency_refusal,
    log_problem,
    register_problem_handlers,
    parse_json_body,
    principal_or_401,
    problem_body,
    problem_for_exception,
    receipt_body,
    refuse_reserved_send_keys,
    state_body,
)
from .blueprint import sse  # noqa: E402
from .extension import _Recorder, _SkipSave  # noqa: E402

logger = logging.getLogger(__name__)

__all__ = [
    "QuartXState",
    "create_quart_statechart_blueprint",
    "problem_response",
    "receipt_response",
]

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _json(body: Any, status: int, mimetype: str = "application/json") -> Any:
    return Response(
        json.dumps(body, default=str), status=status, mimetype=mimetype
    )


def _where() -> str:
    """``"<METHOD> <path>"`` of the current request, for log lines."""
    from quart import has_request_context

    if has_request_context():
        return f"{quart_request.method} {quart_request.path}"
    return "-"


def problem_response(exc: BaseException) -> Any:
    """Build an RFC 9457 problem response for *exc*.

    A 5xx leaves a server-side trace (review CW-09: Quart used to answer
    a bare 500 and log nothing), through the same `log_problem` rule as
    the Flask extension.

    Args:
        exc: The exception to map to a status and problem body.

    Returns:
        A Quart `Response` with the problem media type.
    """
    status, body = problem_for_exception(exc)
    log_problem(exc, _where())
    return _json(body, status, PROBLEM_MEDIA_TYPE)


async def _aproblem(exc: BaseException) -> Any:
    return problem_response(exc)


def receipt_response(
    interp: Any, receipt: Receipt, *, status: Optional[int] = None
) -> Any:
    """Build the JSON response for a send receipt.

    Idempotency refusals become problem responses; otherwise the receipt
    body is returned with the receipt's status unless overridden.

    Args:
        interp: The interpreter that produced the receipt.
        receipt: The receipt of the processed event.
        status: Optional HTTP status overriding the receipt's own.

    Returns:
        A Quart `Response`.
    """
    if receipt.error is not None and is_idempotency_refusal(receipt):
        return problem_response(receipt.error)
    ser = getattr(interp, "_xsm_context_serializer", None)
    body = receipt_body(interp, receipt, context_serializer=ser)
    return _json(
        body, receipt_to_status(receipt) if status is None else status
    )


class QuartXState:
    """`XState` for Quart: identical ``init_app`` / ``register``;
    ``async with xsm.act(name, key) as interp: await interp.send(...)``."""

    def __init__(self, app: Optional[Quart] = None, **kw: Any) -> None:
        self._declared: Dict[str, Registration] = {}
        if app is not None:
            self.init_app(app, **kw)

    def init_app(
        self,
        app: Quart,
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
        error_handlers: bool = True,
    ) -> None:
        """Attach an `AppRegistry` to *app* under `EXTENSION_KEY`.

        Args:
            app: The Quart application.
            store: Persistence store for machine instances.
            lock: Optional lock used around load/save.
            plugins: Interpreter plugins applied to every instance.
            inbox: Optional idempotency inbox.
            principal: Callable identifying the caller from a request.
            log: Optional transition log; adds an `AuditPlugin`.
            clock: Optional clock for the interpreters.
            migrator: Optional snapshot migrator.
            max_body_bytes: Request body size limit.
            heartbeat_s: SSE heartbeat interval in seconds.
            max_connections_per_key: Concurrent streams per instance.
            allowed_origins: Origins allowed on stream endpoints.
            error_handlers: Install problem-shaped error handlers.
        """
        plugins = list(plugins)
        if log is not None:
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
        # 🔐 #285 battle (A): as in Flask -- a lost race / a GET `act()` in
        #    the app's own views is a 409 / 405 problem, not an HTML 500.
        if error_handlers:
            register_problem_handlers(app, _aproblem)

    def registry(self, app: Optional[Quart] = None) -> AppRegistry:
        """Return the `AppRegistry` of *app* (default: the current app).

        Args:
            app: The Quart application; defaults to ``current_app``.

        Returns:
            The registry installed by `init_app`.

        Raises:
            RuntimeError: If `init_app` was not called for the app.
        """
        app = app or current_app._get_current_object()
        try:
            reg: AppRegistry = app.extensions[EXTENSION_KEY]
        except KeyError:
            raise RuntimeError("QuartXState.init_app was not called") from None
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
    ) -> None:
        """Declare a machine under *name* for every app of this extension.

        Args:
            name: Unique machine name.
            machine: A `MachineNode`, JSON path or config dict.
            key: Callable returning the default instance key.
            authorize: Required authorizer (``allow_all`` to opt out).
            context_serializer: Optional serializer for response contexts.
            strict: Optional strict-mode override for the interpreters.
            source: Optional JSON source for the CLI commands.

        Raises:
            ValueError: If *name* is already registered.
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
        if name in self._declared:
            raise ValueError(f"Machine name {name!r} is already registered.")
        self._declared[name] = reg

    @contextlib.asynccontextmanager
    async def act(
        self, name: str, key: Any = None, *, principal: Optional[Any] = None
    ) -> AsyncIterator[Interpreter[Any]]:
        """Yield a started async `Interpreter`; save on clean exit."""
        from quart import has_request_context

        if has_request_context() and quart_request.method in _SAFE_METHODS:
            raise MethodNotAllowedError()
        r = self.registry()
        reg = r.reg(name)
        k = r.key_for(name, key)
        skey = r.store_key(name, k)
        if principal is None and r.inbox is not None and has_request_context():
            # 📝 #285 battle (A): parity with Flask's `act()`.
            # 🔐 Review CW-20: anonymous is a 401, not a ValueError (500).
            if r.principal is not None:
                principal = principal_or_401(r.principal(quart_request))
        plugins = r.plugins_for(principal)
        recorder = _Recorder()
        plugins.append(recorder)
        bodies: List[Dict[str, Any]] = []
        try:
            async with apersisted(
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
                tagged: Any = interp  # 📝 per-request tag, see Flask `act`
                tagged._xsm_context_serializer = reg.context_serializer
                yield interp
                # ⏳ #263 battle: settle a plain-`def` invoke chain before
                #    the bodies are built (and `apersisted` saves).
                await interp.await_settled(DEFAULT_SETTLE_TIMEOUT)
                bodies = [
                    receipt_body(
                        interp, rc, context_serializer=reg.context_serializer
                    )
                    for rc in recorder.changed
                ]
        except _SkipSave:
            return
        if bodies:
            r.fanout.publish(name, k, bodies)

    def skip_save(self) -> None:
        raise _SkipSave()

    async def peek(self, name: str, key: Any) -> Dict[str, Any]:
        """Read the state of an instance without persisting anything.

        A missing instance reports the machine's initial state from a
        pure-transition probe (nothing runs); a stored one is restored
        (migrating if needed).

        Args:
            name: Registered machine name.
            key: Instance key.

        Returns:
            The state body (state, context, available events).
        """
        r = self.registry()
        reg = r.reg(name)
        rec = r.store.load(r.store_key(name, key))
        if rec is None:
            # 🔥 Review CW-05: a started `Interpreter` ran the initial
            #    state's entry actions on a safe GET. The pure-transition
            #    probe records them without running anything.
            from ...helpers import _build_probe

            probe, _ = _build_probe(reg.machine, None)
            probe.start()
            return state_body(probe, reg.context_serializer)
        # 🧬 #263 battle: a read of a stale instance migrates like a write
        #    does (read-only; the next `act()` re-saves at the new label).
        restored: Any = Interpreter.from_snapshot(
            rec.snapshot,
            reg.machine,
            **_restore_kwargs(r.migrator, None),
        )
        return state_body(restored, reg.context_serializer)


async def _read_body(limit: int, timeout_s: float) -> bytes:
    """Read the request body, at most *limit* bytes, within *timeout_s*.

    🔥 Review CW-11: ``get_data()`` buffered the WHOLE body before any size
    check (a chunked request with no Content-Length was bounded only by
    Quart's own config) and nothing timed a stalled client out. The
    stream is cut once it passes the cap, and a body that does not
    arrive in time is a 408.

    Raises:
        PayloadTooLargeError: The body exceeds *limit* (413).
        RequestTimeoutError: The body did not arrive in time (408).
    """

    async def _read() -> bytes:
        chunks: List[bytes] = []
        size = 0
        async for chunk in quart_request.body:
            size += len(chunk)
            if size > limit:
                raise PayloadTooLargeError()
            chunks.append(chunk)
        return b"".join(chunks)

    try:
        return await asyncio.wait_for(_read(), timeout_s)
    except asyncio.TimeoutError:
        raise RequestTimeoutError() from None


async def _json_body(limit: int) -> Dict[str, Any]:
    declared = quart_request.content_length
    if declared is not None and declared > limit:
        raise PayloadTooLargeError()  # refuse before reading anything
    data = await _read_body(limit, DEFAULT_BODY_TIMEOUT_S)
    return parse_json_body(
        quart_request.content_type,
        quart_request.content_length,
        lambda n: data[:n],
        max_body_bytes=limit,
    )


def create_quart_statechart_blueprint(  # noqa: C901 -- one route table
    xsm: QuartXState, name: str, url_prefix: str
) -> Blueprint:
    """The route table of `create_statechart_blueprint`, reduced, on Quart.

    📝 Review CW-26: NOT a full twin. Missing versus Flask: the
    ``per_event_routes`` / ``blueprint_name`` / ``create_if_missing``
    options (an unknown key always starts a fresh instance on first
    write), the ``context_serializer=`` kwarg of ``receipt_response``, the
    ``Cache-Control`` / ``X-Accel-Buffering`` headers on the SSE response
    (set them in a proxy) and the ``seq`` on the snapshot frame.

    Args:
        xsm: The `QuartXState` extension; *name* must be registered on it.
        name: Registered machine name.
        url_prefix: Where to mount (``"/orders"``).

    Returns:
        The blueprint.
    """
    bp = Blueprint(f"xsm_{name}", __name__, url_prefix=url_prefix)

    async def guard(key: Optional[str], event: Optional[str]) -> None:
        """Authorize the request for this machine, key and event.

        Raises:
            ForbiddenError: If the authorizer refuses.
        """
        await xsm.registry().aauthorize(quart_request, name, key, event)

    def principal() -> Optional[str]:
        """Return the validated caller identity, or ``None`` without an inbox.

        Raises:
            UnauthenticatedError: If the principal callable gives no caller.
        """
        r = xsm.registry()
        if r.inbox is None or r.principal is None:
            return None
        return principal_or_401(r.principal(quart_request))

    async def send(key: str, etype: str, payload: Dict[str, Any]) -> Any:
        """Send *etype* to instance *key* and build the receipt response.

        Args:
            key: Instance key.
            etype: Event type.
            payload: Event payload (``type`` is dropped; reserved keys
                refused).

        Returns:
            The JSON receipt response, or a problem for an idempotency
            refusal.
        """
        await guard(key, etype)
        payload = dict(payload)
        payload.pop("type", None)
        refuse_reserved_send_keys(payload)
        # 🔑 Review CW-03: validated like the Starlette stack (400 / 501).
        idem = idempotency_key_from_header(
            quart_request.headers.get(IDEMPOTENCY_HEADER),
            has_inbox=xsm.registry().inbox is not None,
        )
        if idem is not None:
            payload["idempotency_key"] = idem
        out: Dict[str, Any] = {}
        ser = xsm.registry().reg(name).context_serializer
        async with xsm.act(name, key, principal=principal()) as interp:
            receipt = await interp.send(etype, wait=True, **payload)
            out["r"] = receipt
            if not receipt.duplicate:  # ⏳ #263 battle, see `act`
                await interp.await_settled(DEFAULT_SETTLE_TIMEOUT)
            out["b"] = receipt_body(interp, receipt, context_serializer=ser)
            if receipt.duplicate:
                xsm.skip_save()
        if out["r"].error is not None and is_idempotency_refusal(out["r"]):
            return problem_response(out["r"].error)
        return _json(out["b"], receipt_to_status(out["r"]))

    def mapped(fn: Any) -> Any:
        """Wrap async view *fn* so any exception becomes a problem response.

        Args:
            fn: The async view function.

        Returns:
            The wrapped view, keeping *fn*'s name.
        """

        async def view(*a: Any, **kw: Any) -> Any:
            try:
                return await fn(*a, **kw)
            except Exception as exc:  # noqa: BLE001 -- mapped, never leaked
                return problem_response(exc)

        view.__name__ = fn.__name__
        return view

    @bp.get("/<key>")
    @mapped
    async def get_state(key: str) -> Any:
        """``GET /<key>`` -- the instance's state as JSON."""
        await guard(key, None)
        body = await xsm.peek(name, key)
        body["machine_version"] = xsm.registry().reg(name).machine.version
        return _json(body, 200)

    @bp.post("/<key>/send")
    @mapped
    async def send_event(key: str) -> Any:
        """``POST /<key>/send`` -- send the event named by the body's type."""
        body = await _json_body(xsm.registry().max_body_bytes)
        etype = body.get("type")
        if not isinstance(etype, str) or not etype:
            raise BadRequestError('Body must carry a string "type"')
        return await send(key, etype, body)

    @bp.post("/<key>/events/<event>")
    @mapped
    async def send_named(key: str, event: str) -> Any:
        return await send(
            key, event, await _json_body(xsm.registry().max_body_bytes)
        )

    async def refuse_get(**_: Any) -> Any:
        """Answer ``GET`` on a write path with a 405 problem (Allow: POST)."""
        resp = problem_response(MethodNotAllowedError())
        resp.headers["Allow"] = "POST"
        return resp

    bp.add_url_rule("/<key>/send", "refuse_get_send", refuse_get)
    bp.add_url_rule("/<key>/events/<event>", "refuse_get_event", refuse_get)

    @bp.get("/<key>/events")
    @mapped
    async def list_events(key: str) -> Any:
        await guard(key, None)
        return _json(
            {
                "available": (await xsm.peek(name, key))["available_events"],
                "declared": declared_events(xsm.registry().reg(name).machine),
            },
            200,
        )

    @bp.get("/<key>/history")
    @mapped
    async def history(key: str) -> Any:
        """``GET /<key>/history`` -- the transition log (404 if disabled)."""
        r = xsm.registry()
        await guard(key, None)
        if r.log is None:
            return _json(
                problem_body(404, "History not enabled"),
                404,
                PROBLEM_MEDIA_TYPE,
            )
        # 🔐 Review CW-06: same bounds and the same payload-free rows as
        #    Flask (the raw `event_payload` used to be disclosed here).
        after, limit = history_args(quart_request.args)
        skey = r.store_key(name, key)
        # ⚡ The log store is synchronous: keep it off the event loop.
        log = r.log
        rows = await asyncio.get_running_loop().run_in_executor(
            None, lambda: log.read(skey, after_seq=after, limit=limit)
        )
        return _json({"items": history_items(rows)}, 200)

    @bp.get("/<key>/stream")
    @mapped
    async def stream(key: str) -> Any:
        """``GET /<key>/stream`` -- SSE: snapshot, then each transition."""
        r = xsm.registry()
        # 🔐 #285 battle (A): the Quart stream skipped the Origin check
        #    (X0.7) the Flask one makes; any page could read it.
        origin = quart_request.headers.get("Origin")
        if not r.origin_allowed(origin, quart_request.host):
            return _json(
                problem_body(403, "Origin not allowed"),
                403,
                PROBLEM_MEDIA_TYPE,
            )
        await guard(key, None)
        loop = asyncio.get_running_loop()
        wake = asyncio.Event()
        # 🔥 Review CW-16: subscribe BEFORE reading the snapshot, so a
        #    transition committed in between is queued, not lost.

        def poke() -> None:
            loop.call_soon_threadsafe(wake.set)

        q = r.fanout.subscribe(name, str(key), poke)
        if q is None:
            return _json(problem_body(429, "Too many connections"), 429)
        try:
            snapshot = await xsm.peek(name, key)
        except BaseException:
            r.fanout.unsubscribe(name, str(key), q)
            raise
        once = quart_request.args.get("once") == "1"

        async def body() -> AsyncIterator[bytes]:
            try:
                yield sse("snapshot", snapshot).encode()
                while not once:
                    item = await _next_item(q, wake, r.heartbeat_s)
                    if item is None:
                        yield b": heartbeat\n\n"
                        continue
                    if item is CLOSED:
                        return  # cut off for lagging: reconnect
                    yield sse("transition", item[1], item[0]).encode()
            finally:
                r.fanout.unsubscribe(name, str(key), q)

        return Response(body(), mimetype="text/event-stream")

    @bp.get("/schema/diagram.mmd")
    @mapped
    async def diagram() -> Any:
        await guard(None, None)
        return Response(
            xsm.registry().reg(name).machine.to_mermaid(),
            mimetype="text/plain",
        )

    return bp


async def _next_item(q: Any, wake: "asyncio.Event", timeout: float) -> Any:
    """The next queued item, or ``None`` after *timeout* seconds.

    📝 Review CW-10: waits on an `asyncio.Event` the fan-out sets through
    ``call_soon_threadsafe``; no thread is parked per connected client.
    The queue is re-read after clearing the event so a put that lands
    between the two is never missed.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        try:
            return q.get_nowait()
        except queue.Empty:
            pass
        wake.clear()
        try:
            return q.get_nowait()
        except queue.Empty:
            pass
        remaining = deadline - loop.time()
        if remaining <= 0:
            return None
        try:
            await asyncio.wait_for(wake.wait(), remaining)
        except asyncio.TimeoutError:
            return None
