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
    EXTENSION_KEY,
    REQUIRED,
    AppRegistry,
    Registration,
    make_registration,
)
from ._http import (  # noqa: E402
    IDEMPOTENCY_HEADER,
    PROBLEM_MEDIA_TYPE,
    BadRequestError,
    MethodNotAllowedError,
    declared_events,
    is_idempotency_refusal,
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


def problem_response(exc: BaseException) -> Any:
    status, body = problem_for_exception(exc)
    return _json(body, status, PROBLEM_MEDIA_TYPE)


def receipt_response(
    interp: Any, receipt: Receipt, *, status: Optional[int] = None
) -> Any:
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
        max_body_bytes: Optional[int] = None,
        heartbeat_s: float = 15.0,
    ) -> None:
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
            max_body_bytes=max_body_bytes,
            heartbeat_s=heartbeat_s,
        )
        reg.shared = self._declared
        app.extensions[EXTENSION_KEY] = reg

    def registry(self, app: Optional[Quart] = None) -> AppRegistry:
        app = app or current_app._get_current_object()  # type: ignore
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
        plugins = r.plugins_for(principal)
        recorder = _Recorder()
        plugins.append(recorder)
        bodies: List[Dict[str, Any]] = []
        try:
            async with apersisted(
                r.store, skey, reg.machine, lock=r.lock, plugins=plugins
            ) as interp:
                if reg.strict is not None:
                    interp.strict = reg.strict
                interp._xsm_context_serializer = reg.context_serializer
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
        r = self.registry()
        reg = r.reg(name)
        rec = r.store.load(r.store_key(name, key))
        if rec is None:
            interp = Interpreter(reg.machine)
            await interp.start()
            try:
                return state_body(interp, reg.context_serializer)
            finally:
                await interp.stop()
        # 🧬 #263 battle: a read of a stale instance migrates like a write
        #    does (read-only; the next `act()` re-saves at the new label).
        restored: Any = Interpreter.from_snapshot(
            rec.snapshot,
            reg.machine,
            **_restore_kwargs(r.migrator, None),
        )
        return state_body(restored, reg.context_serializer)


async def _json_body(limit: int) -> Dict[str, Any]:
    raw = await quart_request.get_data(as_text=False)
    data: bytes = raw if isinstance(raw, bytes) else raw.encode()
    return parse_json_body(
        quart_request.content_type,
        quart_request.content_length,
        lambda n: data[:n],
        max_body_bytes=limit,
    )


def create_quart_statechart_blueprint(  # noqa: C901 -- one route table
    xsm: QuartXState, name: str, url_prefix: str
) -> Blueprint:
    """The same route table as `create_statechart_blueprint`, on Quart."""
    bp = Blueprint(f"xsm_{name}", __name__, url_prefix=url_prefix)

    async def guard(key: Optional[str], event: Optional[str]) -> None:
        await xsm.registry().aauthorize(quart_request, name, key, event)

    def principal() -> Optional[str]:
        r = xsm.registry()
        if r.inbox is None or r.principal is None:
            return None
        return principal_or_401(r.principal(quart_request))

    async def send(key: str, etype: str, payload: Dict[str, Any]) -> Any:
        await guard(key, etype)
        payload = dict(payload)
        payload.pop("type", None)
        refuse_reserved_send_keys(payload)
        idem = quart_request.headers.get(IDEMPOTENCY_HEADER)
        if idem:
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
        await guard(key, None)
        body = await xsm.peek(name, key)
        body["machine_version"] = xsm.registry().reg(name).machine.version
        return _json(body, 200)

    @bp.post("/<key>/send")
    @mapped
    async def send_event(key: str) -> Any:
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
        r = xsm.registry()
        await guard(key, None)
        if r.log is None:
            return _json(
                problem_body(404, "History not enabled"),
                404,
                PROBLEM_MEDIA_TYPE,
            )
        rows = r.log.read(r.store_key(name, key))
        return _json({"items": [x.to_dict() for x in rows]}, 200)

    @bp.get("/<key>/stream")
    @mapped
    async def stream(key: str) -> Any:
        r = xsm.registry()
        await guard(key, None)
        snapshot = await xsm.peek(name, key)
        q = r.fanout.subscribe(name, str(key))
        if q is None:
            return _json(problem_body(429, "Too many connections"), 429)
        once = quart_request.args.get("once") == "1"

        async def body() -> AsyncIterator[bytes]:
            try:
                yield sse("snapshot", snapshot).encode()
                while not once:
                    item = await asyncio.get_running_loop().run_in_executor(
                        None, _get, q, r.heartbeat_s
                    )
                    if item is None:
                        yield b": heartbeat\n\n"
                        continue
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


def _get(q: Any, timeout: float) -> Any:
    import queue

    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None
