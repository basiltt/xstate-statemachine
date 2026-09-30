# src/xstate_statemachine/inspect/plugin.py
# -----------------------------------------------------------------------------
# 🔎 InspectorPlugin -- engine hooks → Stately Inspector messages (#274)
# -----------------------------------------------------------------------------
# 🏛️ Hook mapping (both engines):
#      on_interpreter_start → @xstate.actor
#      init transition      → @xstate.event {xstate.init} + @xstate.snapshot
#      on_event_received    → @xstate.event (sourceId from on_event_sent)
#      on_event_processed   → @xstate.snapshot
#    `on_event_sent` (new core hook, #274) fires on the SENDER of a
#    sendTo / sendParent / forwardTo; we remember "who sent this" and stamp
#    it as ``sourceId`` when the receiver's `on_event_received` fires.
#
# 🔒 X0.7 data exposure: context is DENY-BY-DEFAULT -- only keys listed in
#    ``context_allowlist`` are sent, and those still go through `redact()`.
#    Event payloads are dropped unless ``include_payloads=True`` (then
#    redacted). The chart definition is sent with its initial ``context``
#    filtered by the same allow-list (initial values are data too).
#
# 📝 Spawned/invoked children are separate interpreters. They are seen
#    only if the plugin is attached to them too -- use `install()` (the
#    global registry, #305) rather than `interp.use()` to follow actors.
# -----------------------------------------------------------------------------
"""The live-inspector plugin."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Deque, Dict, Iterable, Optional, Tuple

from .. import plugins as _plugins
from ..plugins import DEFAULT_REDACT_KEYS, PluginBase, redact
from .protocol import (
    actor_message,
    event_message,
    snapshot_body,
    snapshot_message,
    status_of,
)

__all__ = ["InspectorPlugin"]

_INIT = "___xstate_statemachine_init___"


def _root(interp: Any) -> Any:
    node = interp
    while getattr(node, "parent", None) is not None:
        node = node.parent
    return node


class InspectorPlugin(PluginBase[Any]):
    """Translate interpreter activity into Stately Inspector messages.

    Args:
        sink: Anything with ``send(message: dict)`` -- `JsonLinesSink`,
            `SseSink`, `MemorySink`, `contrib.starlette.WebSocketSink`, or
            a plain callable.
        context_allowlist: Context keys that may leave the process. Empty
            (default) → every snapshot carries ``context: {}``.
        include_payloads: Send event payload fields (redacted). Default
            ``False``: events carry only ``type``.
        redact_keys: Key substrings redacted inside allowed values.
        clock: ``() -> float`` epoch seconds for ``createdAt``.
    """

    def __init__(
        self,
        sink: Any,
        *,
        context_allowlist: Iterable[str] = (),
        include_payloads: bool = False,
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._send: Callable[[Dict[str, Any]], None] = (
            sink.send if hasattr(sink, "send") else sink
        )
        self.sink = sink
        self.context_allowlist = frozenset(context_allowlist)
        self.include_payloads = include_payloads
        self.redact_keys = redact_keys
        self.clock = clock
        self._lock = threading.Lock()
        #: target session id -> FIFO of (event type, event id, source id)
        self._sent: Dict[str, Deque[Tuple[str, int, str]]] = {}

    # -- attach helpers ---------------------------------------------------
    def install(self) -> "InspectorPlugin":
        """Attach to every interpreter built from now on (children too)."""
        _plugins.register_global(self)
        return self

    def uninstall(self) -> None:
        _plugins.unregister_global(self)

    # -- shaping ----------------------------------------------------------
    def _definition(self, machine: Any) -> Optional[Dict[str, Any]]:
        """The chart config, with its initial ``context`` put through the
        SAME allow-list as snapshots -- the config's context holds initial
        VALUES (a seeded API token is still a token)."""
        config = getattr(machine, "source_config", None)
        if not isinstance(config, dict):
            return None
        out = dict(config)
        ctx = out.get("context")
        if isinstance(ctx, dict):
            out["context"] = redact(
                {k: v for k, v in ctx.items() if k in self.context_allowlist},
                self.redact_keys,
            )
        elif "context" in out:
            out["context"] = {}
        return out

    def _context(self, interp: Any) -> Dict[str, Any]:
        if not self.context_allowlist:
            return {}
        ctx = getattr(interp, "context", None) or {}
        picked = {k: v for k, v in ctx.items() if k in self.context_allowlist}
        return redact(picked, self.redact_keys)

    def _event(self, event: Any) -> Dict[str, Any]:
        etype = getattr(event, "type", None) or ""
        if etype == _INIT:
            return {"type": "xstate.init"}
        out: Dict[str, Any] = {"type": etype}
        payload = getattr(event, "payload", None)
        if self.include_payloads and isinstance(payload, dict):
            for k, v in redact(payload, self.redact_keys).items():
                if k != "type":
                    out[k] = v
        return out

    def _snapshot(self, interp: Any) -> Dict[str, Any]:
        actors = getattr(interp, "_actors", None) or {}
        prefix = f"{interp.id}:"
        children = [
            a[len(prefix) :] if a.startswith(prefix) else a for a in actors
        ]
        try:
            tags = interp.tags
        except Exception:  # noqa: BLE001 -- a snapshot never raises
            tags = ()
        return snapshot_body(
            status=status_of(interp.status),
            value=interp.value,
            context=self._context(interp),
            children=children,
            tags=tags,
        )

    def _emit(self, msg: Dict[str, Any]) -> None:
        self._send(msg)

    @staticmethod
    def _ids(interp: Any) -> Tuple[str, str]:
        return str(interp.id), str(_root(interp).id)

    # -- hooks ------------------------------------------------------------
    def on_interpreter_start(self, interpreter: Any) -> None:
        sid, root = self._ids(interpreter)
        parent = getattr(interpreter, "parent", None)
        machine = interpreter.machine
        name = getattr(interpreter, "_invoked_as", None) or str(machine.id)
        self._emit(
            actor_message(
                session_id=sid,
                name=name,
                root_id=root,
                parent_id=None if parent is None else str(parent.id),
                definition=self._definition(machine),
                snapshot=self._snapshot(interpreter),
                clock=self.clock,
            )
        )

    def on_event_sent(
        self, interpreter: Any, target_id: str, event: Any
    ) -> None:
        with self._lock:
            q = self._sent.setdefault(str(target_id), deque(maxlen=256))
            q.append(
                (getattr(event, "type", ""), id(event), str(interpreter.id))
            )

    def _source_for(self, target: str, event: Any) -> Optional[str]:
        with self._lock:
            q = self._sent.get(target)
            if not q:
                return None
            etype = getattr(event, "type", "")
            for match in (
                lambda item: item[1] == id(event),
                lambda item: item[0] == etype,
            ):
                for item in list(q):
                    if match(item):
                        q.remove(item)
                        return item[2]
        return None

    def _event_msg(self, interp: Any, event: Any, source: Optional[str]):
        sid, root = self._ids(interp)
        self._emit(
            event_message(
                session_id=sid,
                event=self._event(event),
                root_id=root,
                source_id=source,
                clock=self.clock,
            )
        )

    def _snapshot_msg(self, interp: Any, event: Any) -> None:
        sid, root = self._ids(interp)
        self._emit(
            snapshot_message(
                session_id=sid,
                event=self._event(event),
                snapshot=self._snapshot(interp),
                root_id=root,
                clock=self.clock,
            )
        )

    def on_transition(
        self, interpreter: Any, from_states: Any, to_states: Any, transition
    ) -> None:
        # 🚀 The init step has no received/processed pair; report it the
        #    way XState does: an `xstate.init` event, then a snapshot.
        if getattr(transition, "event", None) != _INIT:
            return
        parent = getattr(interpreter, "parent", None)
        init = type("Init", (), {"type": _INIT, "payload": {}})()
        self._event_msg(
            interpreter, init, None if parent is None else str(parent.id)
        )
        self._snapshot_msg(interpreter, init)

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        self._event_msg(
            interpreter, event, self._source_for(str(interpreter.id), event)
        )

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        self._snapshot_msg(interpreter, event)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        with self._lock:
            self._sent.pop(str(interpreter.id), None)
