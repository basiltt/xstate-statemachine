# src/xstate_statemachine/eda/asyncapi.py
# -----------------------------------------------------------------------------
# 📜 asyncapi_document -- an AsyncAPI 3.0 description of a machine (#293/#295)
# -----------------------------------------------------------------------------
# 🏛️ A machine already declares everything AsyncAPI asks for: the events it
#    CONSUMES (its `on` keys) and the events it PUBLISHES (`meta.publish`
#    transitions and `publish`-tagged states, see `outbox.publish_specs`).
#    This module renders that as an AsyncAPI 3.0.0 document whose messages
#    are CloudEvents (structured mode), so the docs of an event-driven
#    service are generated from the chart and cannot drift from it.
#
# 📦 The AsyncAPI 3.0.0 JSON Schema is VENDORED in `_asyncapi_schema.json`
#    so documents are validated offline (tests, `xsm asyncapi --validate`):
#      source:  https://github.com/asyncapi/spec-json-schemas
#               schemas/3.0.0.json (bundled, draft-07, $id
#               http://asyncapi.com/definitions/3.0.0/asyncapi.json)
#      version: 3.0.0; re-serialised compactly (sort_keys) -- content
#               unchanged. Regenerate by downloading that file and running
#               it through json.dumps(separators=(",", ":"), sort_keys=True).
#    Validation needs `jsonschema` (a test/CLI convenience, never a runtime
#    dependency of the core).
# -----------------------------------------------------------------------------
"""`asyncapi_document`, `consumed_events`, `load_asyncapi_schema`,
`validate_asyncapi`."""

from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any, Dict, List, Optional

from .outbox import publish_specs

__all__ = [
    "ASYNCAPI_VERSION",
    "asyncapi_document",
    "consumed_events",
    "load_asyncapi_schema",
    "validate_asyncapi",
]

ASYNCAPI_VERSION = "3.0.0"
_SCHEMA_FILE = "_asyncapi_schema.json"
_KEY = re.compile(r"[^A-Za-z0-9_.\-]")
_ENGINE_PREFIXES = ("done.", "error.", "xstate.", "after.")


def load_asyncapi_schema() -> Dict[str, Any]:
    """The vendored AsyncAPI 3.0.0 JSON Schema (offline)."""
    text = (
        resources.files(__package__)
        .joinpath(_SCHEMA_FILE)
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


def validate_asyncapi(document: Dict[str, Any]) -> None:
    """Validate *document* against the vendored schema.

    Raises ``jsonschema.ValidationError`` on an invalid document and
    `MissingExtraError` when ``jsonschema`` is not installed.
    """
    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on env
        from ..exceptions import MissingExtraError

        raise MissingExtraError(
            "asyncapi",
            "jsonschema",
            hint="(validation only): pip install jsonschema",
        ) from exc
    jsonschema.Draft7Validator(load_asyncapi_schema()).validate(document)


def consumed_events(machine: Any) -> List[str]:
    """Every caller-sendable event the chart handles, sorted."""
    from ..validation import walk

    names = set()
    for node in walk(machine):
        for ev in getattr(node, "on", None) or {}:
            if (
                not ev
                or ev == "*"
                or ev.endswith(".*")
                or ev.startswith(_ENGINE_PREFIXES)
            ):
                continue
            names.add(ev)
    return sorted(names)


def _key(text: str) -> str:
    return _KEY.sub("_", text)


def _cloudevent_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["specversion", "id", "source", "type"],
        "properties": {
            "specversion": {"type": "string", "const": "1.0"},
            "id": {"type": "string"},
            "source": {"type": "string"},
            "type": {"type": "string"},
            "subject": {
                "type": "string",
                "description": "Machine instance key (partition key).",
            },
            "time": {"type": "string", "format": "date-time"},
            "datacontenttype": {"type": "string"},
            "data": {},
            "correlationid": {"type": "string"},
            "causationid": {"type": "string"},
            "machineid": {"type": "string"},
            "machineversion": {"type": "string"},
            "traceparent": {"type": "string"},
            "xsmattempt": {"type": "integer", "minimum": 0},
        },
    }


def _message(
    ce_type: str, summary: str, fields: Optional[List[str]]
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"type": "object"}
    if fields:
        data["properties"] = {f: {} for f in fields}
    return {
        "name": ce_type,
        "title": ce_type,
        "summary": summary,
        "contentType": "application/cloudevents+json",
        "payload": {
            "allOf": [
                {"$ref": "#/components/schemas/CloudEvent"},
                {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "const": ce_type},
                        "data": data,
                    },
                },
            ]
        },
    }


def asyncapi_document(
    machine: Any,
    *,
    server: Optional[Dict[str, Any]] = None,
    inbound_topic: Optional[str] = None,
    outbound_topic: str = "events",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """An AsyncAPI 3.0.0 document for *machine*.

    Args:
        machine: A built `MachineNode`.
        server: Optional ``{"host": ..., "protocol": ..., ...}`` (an
            AsyncAPI Server Object); registered as ``default``.
        inbound_topic: Channel address of consumed events (default: the
            machine id).
        outbound_topic: Channel address of published events (the
            `OutboxPlugin` topic).
        title: ``info.title`` (default ``"<machine id> events"``).

    Consumed messages have CloudEvents type ``xsm.<machine>.<EVENT>``
    (what `InboundDispatcher` maps back to ``EVENT``); published messages
    carry the type the chart declares.
    """
    mid = str(machine.id)
    inbound = inbound_topic or mid
    messages: Dict[str, Any] = {}
    in_msgs: Dict[str, Any] = {}
    out_msgs: Dict[str, Any] = {}
    for ev in consumed_events(machine):
        ce_type = f"xsm.{mid}.{ev}"
        key = _key(f"consume.{ev}")
        messages[key] = _message(ce_type, f"Command: send {ev!r}.", None)
        in_msgs[key] = {"$ref": f"#/components/messages/{key}"}
    for spec in publish_specs(machine):
        key = _key(f"publish.{spec['type']}")
        if key in messages:
            continue
        origin = (
            f"on {spec['event']!r} from {spec['from']}"
            if spec["source"] == "transition"
            else f"on entering {spec['from']}"
        )
        messages[key] = _message(
            spec["type"], f"Published {origin}.", spec["fields"]
        )
        out_msgs[key] = {"$ref": f"#/components/messages/{key}"}

    channels: Dict[str, Any] = {}
    operations: Dict[str, Any] = {}
    if in_msgs:
        channels["inbound"] = {
            "address": inbound,
            "description": f"Commands consumed by {mid}.",
            "messages": in_msgs,
        }
        operations[f"consume_{_key(mid)}"] = {
            "action": "receive",
            "channel": {"$ref": "#/channels/inbound"},
            "messages": [
                {"$ref": f"#/channels/inbound/messages/{k}"} for k in in_msgs
            ],
        }
    if out_msgs:
        channels["outbound"] = {
            "address": outbound_topic,
            "description": f"Integration events published by {mid}.",
            "messages": out_msgs,
        }
        operations[f"publish_{_key(mid)}"] = {
            "action": "send",
            "channel": {"$ref": "#/channels/outbound"},
            "messages": [
                {"$ref": f"#/channels/outbound/messages/{k}"} for k in out_msgs
            ],
        }
    doc: Dict[str, Any] = {
        "asyncapi": ASYNCAPI_VERSION,
        "info": {
            "title": title or f"{mid} events",
            "version": str(getattr(machine, "version", None) or "0.0.0"),
            "description": (
                f"Generated by xstate-statemachine from machine {mid!r}."
            ),
        },
        "defaultContentType": "application/cloudevents+json",
        "channels": channels,
        "operations": operations,
        "components": {
            "schemas": {"CloudEvent": _cloudevent_schema()},
            "messages": messages,
        },
    }
    if server:
        doc["servers"] = {"default": dict(server)}
    return doc
