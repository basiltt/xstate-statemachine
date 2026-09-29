# src/xstate_statemachine/contrib/flask/blueprint.py
# -----------------------------------------------------------------------------
# 🧭 create_statechart_blueprint -- the C2 route table on Flask
# -----------------------------------------------------------------------------
#    GET  /<id>                  state (context only via context_serializer)
#    POST /<id>/send             {"type": "EVENT", ...payload}
#    POST /<id>/events/<EVENT>   payload body (per_event_routes=True adds
#                                one named endpoint per declared event)
#    GET  /<id>/events           available + declared events
#    GET  /<id>/history          transition log (404 problem without a log)
#    GET  /<id>/stream           SSE: snapshot, then committed transitions
#    GET  /schema/diagram.mmd    Mermaid source of the chart
#
# 🔐 Every route runs `authorize` (event=None for reads). Writes are POST
#    only: a GET to a write path is 405 (Flask's method routing) and
#    `act()` itself refuses to run inside a safe-method request. Bodies:
#    JSON only (415), capped (413), problem+json errors without exception
#    text (X0.7). ``Idempotency-Key`` is honoured and principal-scoped (X0.2).
#
# ⚠️ SSE holds a WORKER for the life of the stream. Flask's dev server and
#    a sync gunicorn worker serve one request per thread/worker: run the
#    stream behind a threaded/gevent server, or on Quart.
# -----------------------------------------------------------------------------
"""`create_statechart_blueprint()`."""

from __future__ import annotations

import json
import logging
import queue
from typing import Any, Dict, Iterator, Optional

from flask import Blueprint, Response
from flask import request as flask_request
from flask import stream_with_context

from ...persistence.helpers import KeyNotFoundError
from ._http import (
    IDEMPOTENCY_HEADER,
    BadRequestError,
    HTTPProblemError,
    MethodNotAllowedError,
    declared_events,
    is_idempotency_refusal,
    parse_json_body,
    problem_body,
    receipt_body,
)
from .extension import XState, problem_response, receipt_response

logger = logging.getLogger(__name__)

__all__ = ["create_statechart_blueprint", "sse"]


def sse(event: str, data: Dict[str, Any], seq: Optional[int] = None) -> str:
    """One Server-Sent-Events frame."""
    lines = []
    if seq is not None:
        lines.append(f"id: {seq}")
    lines.append(f"event: {event}")
    lines.append("data: " + json.dumps(data, separators=(",", ":")))
    return "\n".join(lines) + "\n\n"


def _json_body(max_body_bytes: int) -> Dict[str, Any]:
    stream = flask_request.stream
    return parse_json_body(
        flask_request.content_type,
        flask_request.content_length,
        stream.read,
        max_body_bytes=max_body_bytes,
    )


def create_statechart_blueprint(
    xsm: XState,
    name: str,
    url_prefix: str,
    *,
    per_event_routes: bool = False,
    blueprint_name: Optional[str] = None,
    create_if_missing: bool = True,
) -> Blueprint:
    """A `Blueprint` exposing machine *name* (see the route table above).

    Args:
        xsm: The `XState` extension; *name* must be registered on it.
        url_prefix: Where to mount (``"/orders"``).
        per_event_routes: Also add one endpoint per declared event
            (``xsm_<name>.event_<EVENT>``) for ``url_for`` / OpenAPI tools.
        create_if_missing: ``False`` → an unknown id is 404 on every route
            instead of starting a fresh instance on first write.
    """
    bp = Blueprint(
        blueprint_name or f"xsm_{name}", __name__, url_prefix=url_prefix
    )

    def reg() -> Any:
        return xsm.registry()

    def guard(key: Optional[str], event: Optional[str]) -> None:
        r = reg()
        r.authorize(flask_request, name, key, event)
        if key is not None and not create_if_missing:
            if r.store.load(r.store_key(name, key)) is None:
                raise KeyNotFoundError(key)

    def principal() -> Optional[str]:
        r = reg()
        if r.inbox is None:
            return None
        return str(r.principal(flask_request))

    def send(key: str, etype: str, payload: Dict[str, Any]) -> Any:
        r = reg()
        guard(key, etype)
        payload = dict(payload)
        payload.pop("type", None)
        idem = flask_request.headers.get(IDEMPOTENCY_HEADER)
        if idem:
            payload["idempotency_key"] = idem
        result: Dict[str, Any] = {}
        with xsm.act(name, key, principal=principal()) as interp:
            receipt = interp.send(etype, wait=True, **payload)
            result["receipt"] = receipt
            result["body"] = receipt_body(
                interp,
                receipt,
                context_serializer=r.reg(name).context_serializer,
            )
            result["interp"] = interp
            if receipt.duplicate:
                # 🔁 A replay changed nothing: do NOT save (a save would
                #    bump the version and make the original lose a 409).
                xsm.skip_save()
        receipt = result["receipt"]
        if receipt.error is not None and is_idempotency_refusal(receipt):
            return problem_response(receipt.error)
        from ...receipts import receipt_to_status

        return Response(
            json.dumps(result["body"], default=str),
            status=receipt_to_status(receipt),
            mimetype="application/json",
        )

    def mapped(fn: Any) -> Any:
        def view(*a: Any, **kw: Any) -> Any:
            try:
                return fn(*a, **kw)
            except (HTTPProblemError, Exception) as exc:  # noqa: BLE001
                return problem_response(exc)

        view.__name__ = fn.__name__
        return view

    @bp.get("/<key>")
    @mapped
    def get_state(key: str) -> Any:
        guard(key, None)
        body = xsm.peek(name, key)
        body["machine_version"] = reg().reg(name).machine.version or None
        return body

    @bp.post("/<key>/send")
    @mapped
    def send_event(key: str) -> Any:
        body = _json_body(reg().max_body_bytes)
        etype = body.get("type")
        if not isinstance(etype, str) or not etype:
            raise BadRequestError('Body must carry a string "type"')
        return send(key, etype, body)

    @bp.post("/<key>/events/<event>")
    @mapped
    def send_named(key: str, event: str) -> Any:
        return send(key, event, _json_body(reg().max_body_bytes))

    # 🔐 A GET to a write path is an explicit 405 problem (with ``Allow``),
    #    never a silent read and never Flask's HTML error page.
    def refuse_get(**_: Any) -> Any:
        resp = problem_response(MethodNotAllowedError())
        resp.headers["Allow"] = "POST"
        return resp

    bp.add_url_rule("/<key>/send", "refuse_get_send", refuse_get)
    bp.add_url_rule("/<key>/events/<event>", "refuse_get_event", refuse_get)

    @bp.get("/<key>/events")
    @mapped
    def list_events(key: str) -> Any:
        guard(key, None)
        machine = reg().reg(name).machine
        return {
            "available": xsm.peek(name, key)["available_events"],
            "declared": declared_events(machine),
        }

    @bp.get("/<key>/history")
    @mapped
    def history(key: str) -> Any:
        guard(key, None)
        return _history(reg(), name, key)

    @bp.get("/<key>/stream")
    @mapped
    def stream(key: str) -> Any:
        r = reg()
        origin = flask_request.headers.get("Origin")
        if not r.origin_allowed(origin, flask_request.host):
            return problem_response(_OriginRefused())
        guard(key, None)
        return _stream(r, name, key, xsm.peek(name, key))

    @bp.get("/schema/diagram.mmd")
    @mapped
    def diagram() -> Any:
        guard(None, None)
        return Response(
            reg().reg(name).machine.to_mermaid(), mimetype="text/plain"
        )

    if per_event_routes:
        _add_event_routes(bp, xsm, name, send, mapped)
    return bp


def _problem(status: int, title: str, **kw: Any) -> Any:
    return Response(
        json.dumps(problem_body(status, title, **kw)),
        status=status,
        mimetype="application/problem+json",
    )


def _history(r: Any, name: str, key: str) -> Any:
    """``GET /<id>/history`` -- the transition log (payloads omitted)."""
    if r.log is None:
        return _problem(
            404,
            "History not enabled",
            detail="init_app(log=...) enables transition history",
        )
    try:
        after = int(flask_request.args.get("after", 0))
        limit = min(int(flask_request.args.get("limit", 100)), 1000)
    except ValueError:
        raise BadRequestError("after/limit must be integers")
    rows = r.log.read(r.store_key(name, key), after_seq=after, limit=limit)
    return {
        "items": [
            {k: v for k, v in rec.to_dict().items() if k != "event_payload"}
            for rec in rows
        ]
    }


def _stream(r: Any, name: str, key: str, snapshot: Dict[str, Any]) -> Any:
    """``GET /<id>/stream`` -- SSE: a snapshot, then committed transitions
    published by `act()` in THIS process; ``?once=1`` ends after the
    snapshot (health checks, tests)."""
    q = r.fanout.subscribe(name, str(key))
    if q is None:
        return _problem(429, "Too many connections for this instance")
    seq0 = r.fanout.seq(name, str(key))
    once = flask_request.args.get("once") == "1"

    def body() -> Iterator[str]:
        try:
            yield sse("snapshot", snapshot, seq0)
            if once:
                return
            while True:
                try:
                    seq, data = q.get(timeout=r.heartbeat_s)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue
                yield sse("transition", data, seq)
        finally:
            r.fanout.unsubscribe(name, str(key), q)

    return Response(
        stream_with_context(body()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


class _OriginRefused(HTTPProblemError):
    status = 403
    title = "Origin not allowed"


def _add_event_routes(
    bp: Blueprint, xsm: XState, name: str, send: Any, mapped: Any
) -> None:
    """One named endpoint per declared event, registered lazily at the
    first request (the machine lives in the app's registry, not here)."""
    declared = xsm._declared.get(name)
    if declared is None:
        raise KeyError(
            f"per_event_routes needs {name!r} registered on the extension "
            f"(xsm.register(...)) before the blueprint is created"
        )
    for etype in declared_events(declared.machine):

        def make(e: str) -> Any:
            def handler(key: str) -> Any:
                return send(key, e, _json_body(xsm.registry().max_body_bytes))

            handler.__name__ = f"event_{e}"
            return mapped(handler)

        bp.add_url_rule(
            f"/<key>/events/{etype}",
            endpoint=f"event_{etype}",
            view_func=make(etype),
            methods=["POST"],
        )
