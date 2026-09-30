# src/xstate_statemachine/inspect/protocol.py
# -----------------------------------------------------------------------------
# 📡 Stately Inspector wire protocol (`@statelyai/inspect`) -- message builders
# -----------------------------------------------------------------------------
# 🏛️ The protocol is not formally documented. Shapes here are pinned against
#    fixtures RECORDED from the real npm package (`@statelyai/inspect@0.7.2`,
#    `xstate@5.33.2`) -- see tests/inspect/fixtures/ (provenance + the
#    `record.mjs` that regenerates them). Three message kinds:
#
#      @xstate.actor     name, sessionId, parentId?, rootId, definition (JSON
#                        string of the machine config), snapshot
#      @xstate.event     event {type, ...}, sessionId (receiver), sourceId?
#      @xstate.snapshot  event (the one that caused it), snapshot {status,
#                        value, context, children, historyValue, tags}
#
#    Every message also carries ``_version`` (the package version the
#    receiving UI checks is a string), ``createdAt`` (epoch ms as a string)
#    and ``id: null``. Keys whose JS value is ``undefined`` are OMITTED, as
#    `JSON.stringify` does -- the fixtures show e.g. no ``sourceId`` on a
#    root actor's init event.
# -----------------------------------------------------------------------------
"""Builders for Stately Inspector protocol messages."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Iterable, Optional

__all__ = [
    "PROTOCOL_VERSION",
    "MESSAGE_TYPES",
    "actor_message",
    "event_message",
    "snapshot_message",
    "status_of",
]

#: The `@statelyai/inspect` version the fixtures were recorded from.
PROTOCOL_VERSION = "0.7.2"
MESSAGE_TYPES = ("@xstate.actor", "@xstate.event", "@xstate.snapshot")

_STATUS = {
    "running": "active",
    "done": "done",
    "error": "error",
    "stopped": "stopped",
    "not_started": "active",
}


def status_of(interp_status: str) -> str:
    """Engine status → XState snapshot status."""
    return _STATUS.get(str(interp_status), "active")


def _now_ms(clock: Optional[Callable[[], float]]) -> str:
    return str(int((clock or time.time)() * 1000))


def _base(
    kind: str,
    session_id: str,
    root_id: Optional[str],
    clock: Optional[Callable[[], float]],
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "type": kind,
        "sessionId": session_id,
        "_version": PROTOCOL_VERSION,
        "createdAt": _now_ms(clock),
        "id": None,
    }
    if root_id is not None:
        msg["rootId"] = root_id
    return msg


def snapshot_body(
    *,
    status: str,
    value: Any,
    context: Dict[str, Any],
    children: Iterable[str] = (),
    tags: Iterable[str] = (),
) -> Dict[str, Any]:
    """The ``snapshot`` object shared by actor and snapshot messages."""
    return {
        "status": status,
        "value": value,
        "context": context,
        "children": {c: {"id": c} for c in sorted(children)},
        "historyValue": {},
        "tags": sorted(tags),
    }


def actor_message(
    *,
    session_id: str,
    name: str,
    root_id: Optional[str],
    parent_id: Optional[str],
    definition: Optional[Dict[str, Any]],
    snapshot: Dict[str, Any],
    clock: Optional[Callable[[], float]] = None,
) -> Dict[str, Any]:
    """``@xstate.actor`` -- an actor was created."""
    msg = _base("@xstate.actor", session_id, root_id, clock)
    msg["name"] = name
    if parent_id is not None:
        msg["parentId"] = parent_id
    msg["definition"] = json.dumps(
        definition if definition is not None else {"id": name},
        default=lambda o: f"[{type(o).__name__}]",
        sort_keys=True,
    )
    msg["snapshot"] = snapshot
    return msg


def event_message(
    *,
    session_id: str,
    event: Dict[str, Any],
    root_id: Optional[str],
    source_id: Optional[str] = None,
    clock: Optional[Callable[[], float]] = None,
) -> Dict[str, Any]:
    """``@xstate.event`` -- *event* was delivered to *session_id*."""
    msg = _base("@xstate.event", session_id, root_id, clock)
    msg["event"] = event
    if source_id is not None:
        msg["sourceId"] = source_id
    return msg


def snapshot_message(
    *,
    session_id: str,
    event: Dict[str, Any],
    snapshot: Dict[str, Any],
    root_id: Optional[str],
    clock: Optional[Callable[[], float]] = None,
) -> Dict[str, Any]:
    """``@xstate.snapshot`` -- the actor's state after processing *event*."""
    msg = _base("@xstate.snapshot", session_id, root_id, clock)
    msg["event"] = event
    msg["snapshot"] = snapshot
    return msg
