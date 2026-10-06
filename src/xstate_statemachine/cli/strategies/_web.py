# src/xstate_statemachine/cli/strategies/_web.py
# -----------------------------------------------------------------------------
# 🌐 Shared input model for the `fastapi-router` / `pydantic-models` companions
# -----------------------------------------------------------------------------
# Both templates need the same facts about a chart: its client-sendable
# events (with a Python-safe class name, identifier and URL segment each),
# the prose attached to them (`description` / `meta`), and any payload
# shape the JSON declares. They are read from the RAW config -- no machine
# is built -- so every export in the corpus generates, including ones the
# engine would refuse to run.
#
# 🛡️ Nothing read here is ever emitted as code: names go through
#    `repr()` (string literals) or the identifier slugger below, prose
#    through `docstring_safe` (no quotes, backslashes or newlines).
# -----------------------------------------------------------------------------
"""Event / payload / prose extraction shared by the web companions."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from ...exceptions import InvalidConfigError
from ..naming import docstring_safe

#: Event prefixes the engine raises itself; a client never sends them.
INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")

#: A URL path segment that needs no rewriting.
_PLAIN_SEGMENT = re.compile(r"[A-Za-z0-9_.-]+")

#: JSON-ish type names → Python annotations (anything else is `Any`).
_TYPES = {
    "string": "str",
    "str": "str",
    "number": "float",
    "float": "float",
    "integer": "int",
    "int": "int",
    "boolean": "bool",
    "bool": "bool",
    "array": "List[Any]",
    "list": "List[Any]",
    "object": "Dict[str, Any]",
    "dict": "Dict[str, Any]",
}

#: Names a pydantic field may not take (shadow `BaseModel` API or the
#: event discriminator). Such fields get a safe name plus an alias.
_RESERVED_FIELDS = frozenset(
    {
        "type",
        "copy",
        "dict",
        "json",
        "schema",
        "schema_json",
        "construct",
        "validate",
        "fields",
        "parse_obj",
        "parse_raw",
        "parse_file",
        "from_orm",
        "update_forward_refs",
        "Config",
    }
)


@dataclass(frozen=True)
class PayloadField:
    """One declared payload field."""

    name: str  # the JSON key, as sent on the wire
    attr: str  # a valid, non-reserved Python attribute name
    annotation: str
    required: bool


@dataclass
class EventSpec:
    """Everything the generators need to know about one event."""

    type: str
    class_name: str = ""
    ident: str = ""
    path: str = ""
    sources: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)
    payload: Optional[List[PayloadField]] = None

    @property
    def doc(self) -> str:
        """Docstring-safe prose: first description + where it is accepted."""
        parts = []
        if self.descriptions:
            parts.append(self.descriptions[0].rstrip(".") + ".")
        if self.sources:
            where = ", ".join(sorted(set(self.sources))[:6])
            more = len(set(self.sources)) - 6
            parts.append(
                f"Accepted in: {where}"
                + (f" (+{more} more)." if more > 0 else ".")
            )
        return docstring_safe(" ".join(parts), limit=200) if parts else ""


# -----------------------------------------------------------------------------
# 🔤 Naming
# -----------------------------------------------------------------------------
def _tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+", text)


def snake_slug(text: str, *, fallback: str = "event") -> str:
    """``"BTN: Abort / Exit"`` → ``"btn_abort_exit"`` (a valid identifier)."""
    slug = "_".join(t.lower() for t in _tokens(text)) or fallback
    if slug[0].isdigit():
        slug = f"{fallback}_{slug}"
    if keyword.iskeyword(slug):
        slug += "_"
    return slug


def pascal_slug(text: str, *, fallback: str = "Event") -> str:
    """``"CAR_SALES_OK"`` → ``"CarSalesOk"``; ``"goNext"`` → ``"GoNext"``."""
    out = "".join(
        t.capitalize() if t.isupper() or t.islower() else t[0].upper() + t[1:]
        for t in _tokens(text)
    )
    if not out or out[0].isdigit():
        out = fallback + out
    return out


def _unique(base: str, taken: Set[str], sep: str = "_") -> str:
    name, n = base, 2
    while name in taken:
        name, n = f"{base}{sep}{n}", n + 1
    taken.add(name)
    return name


def field_attr(key: str, taken: Set[str]) -> str:
    """A safe pydantic attribute for JSON key *key* (alias when it differs)."""
    attr = key
    if (
        not key.isidentifier()
        or keyword.iskeyword(key)
        or key.startswith("_")
        or key.startswith("model_")
        or key in _RESERVED_FIELDS
    ):
        attr = "f_" + snake_slug(key, fallback="field")
    return _unique(attr, taken)


# -----------------------------------------------------------------------------
# 🔎 Reading the chart
# -----------------------------------------------------------------------------
def _transitions(value: Any) -> Iterable[Dict[str, Any]]:
    items = value if isinstance(value, list) else [value]
    return (t for t in items if isinstance(t, dict))


def _walk_on(
    node: Dict[str, Any], path: str, found: Dict[str, EventSpec]
) -> None:
    on = node.get("on")
    pairs: List[Tuple[Any, Any]] = []
    if isinstance(on, dict):
        pairs = list(on.items())
    elif isinstance(on, list):  # legacy array form [{event, target}]
        pairs = [(t.get("event"), t) for t in on if isinstance(t, dict)]
    for etype, value in pairs:
        if (
            not isinstance(etype, str)
            or not etype
            or etype.startswith(INTERNAL_PREFIXES)
            or "*" in etype
        ):
            continue
        spec = found.setdefault(etype, EventSpec(type=etype))
        spec.sources.append(path)
        for t in _transitions(value):
            _note_transition(spec, t)
    states = node.get("states")
    if isinstance(states, dict):
        for key, child in states.items():
            if isinstance(child, dict):
                _walk_on(child, f"{path}.{key}" if path else str(key), found)


def _note_transition(spec: EventSpec, t: Dict[str, Any]) -> None:
    desc = t.get("description")
    raw_meta = t.get("meta")
    meta: Dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
    if not isinstance(desc, str):
        desc = meta.get("description") or meta.get("summary")
    if isinstance(desc, str) and desc.strip():
        spec.descriptions.append(desc.strip())
    if spec.payload is None and "payload" in meta:
        spec.payload = parse_payload(meta["payload"])


def _root_payloads(config: Dict[str, Any]) -> Dict[str, Any]:
    """``meta.events.<E>.payload`` / ``meta.eventSchemas.<E>`` -- also one
    level down (``meta.<anything>.events.<E>.payload``, the shape some
    Stately exports carry)."""
    meta = config.get("meta")
    if not isinstance(meta, dict):
        return {}
    out: Dict[str, Any] = {}
    scopes = [meta] + [v for v in meta.values() if isinstance(v, dict)]
    for scope in scopes:
        for key in ("events", "eventSchemas", "event_schemas"):
            table = scope.get(key)
            if not isinstance(table, dict):
                continue
            for etype, entry in table.items():
                if not isinstance(entry, dict) or etype in out:
                    continue
                if key == "events":
                    if "payload" in entry:
                        out[etype] = entry["payload"]
                else:
                    out[etype] = entry
    return out


def parse_payload(schema: Any) -> Optional[List[PayloadField]]:
    """Declared payload → fields. ``None`` when *schema* is not a mapping.

    Accepts ``{field: "number"}``, ``{field: {"type": ..., "required":
    bool}}`` and JSON-Schema ``{"type": "object", "properties": {...},
    "required": [...]}``.
    """
    if not isinstance(schema, dict):
        return None
    if _is_json_schema_root(schema):
        # 📝 review H1 (#279): a JSON-Schema ROOT (`{"type": "object"}`,
        #    `{"type": ["object", "null"]}`, ...) with no `properties` is
        #    "any object" -- never a field map with a field called `type`.
        #    A non-object root is refused as such, with its type named.
        kinds = schema["type"]
        kinds = kinds if isinstance(kinds, list) else [kinds]
        if "object" not in kinds:
            raise InvalidConfigError(
                f"an event payload schema must describe an object, got "
                f"type {schema['type']!r}"
            )
        return None
    required: Set[str] = set()
    props: Dict[str, Any] = schema
    if isinstance(schema.get("properties"), dict):
        props = schema["properties"]
        req = schema.get("required")
        required = (
            {r for r in req if isinstance(r, str)}
            if isinstance(req, list)
            else set()
        )
    fields: List[PayloadField] = []
    taken: Set[str] = set()
    for key, spec in props.items():
        if not isinstance(key, str):
            continue
        if isinstance(spec, str):
            ann, is_required = _TYPES.get(spec, "Any"), True
        elif isinstance(spec, dict):
            t = spec.get("type")
            ann = _TYPES.get(t, "Any") if isinstance(t, str) else "Any"
            is_required = key in required or spec.get("required") is True
        else:
            ann, is_required = "Any", key in required
        fields.append(
            PayloadField(key, field_attr(key, taken), ann, is_required)
        )
    return fields


def _is_json_schema_root(schema: Dict[str, Any]) -> bool:
    """``{"type": <json type or list of them>, ...}`` with no `properties`
    is a JSON-Schema root, not a flat field map (whose values are field
    specs: strings naming a type or dicts)."""
    if "properties" in schema:
        return False
    kind = schema.get("type")
    names = {
        "object",
        "string",
        "number",
        "integer",
        "boolean",
        "array",
        "null",
    }
    if isinstance(kind, str):
        return kind in names
    if isinstance(kind, list) and kind:
        return all(isinstance(k, str) and k in names for k in kind)
    return False


#: Payload names no client can send: `send()` options (the registry
#: refuses them with 422) and `type`, which IS the event's own type on
#: the wire (an aliased field silently received the event name).
SEND_OPTIONS = ("wait", "priority", "type")


def _refuse_send_options(spec: EventSpec) -> None:
    bad = sorted({f.name for f in spec.payload or []} & set(SEND_OPTIONS))
    if bad:
        # 🔥 #279 battle: the model declared `wait`, the registry then
        #    refused every request carrying it (a reserved `send()` option)
        #    -- a field no client could ever send. Loud, at generation.
        raise InvalidConfigError(
            f"event {spec.type!r} declares payload field(s) {bad}: they "
            "name `send()` options or the event type and cannot be sent; "
            "rename them"
        )


def collect_events(config: Dict[str, Any]) -> List[EventSpec]:
    """Every client-sendable event, sorted, with unique names assigned.

    Raises:
        InvalidConfigError: a declared payload field names a `send()`
            option (``wait`` / ``priority``) or the discriminator
            ``type``; or a payload schema's root type is not an object.
    """
    found: Dict[str, EventSpec] = {}
    _walk_on(config, "", found)
    for etype, schema in _root_payloads(config).items():
        if etype in found and found[etype].payload is None:
            found[etype].payload = parse_payload(schema)
    for spec in found.values():
        _refuse_send_options(spec)
    classes: Set[str] = set()
    idents: Set[str] = set()
    paths: Set[str] = set()
    specs = [found[k] for k in sorted(found)]
    for spec in specs:
        spec.sources = [s or "(root)" for s in spec.sources]
        spec.class_name = _unique(pascal_slug(spec.type) + "Event", classes)
        spec.ident = _unique(snake_slug(spec.type), idents)
        segment = (
            spec.type
            if _PLAIN_SEGMENT.fullmatch(spec.type) and spec.type.strip(".")
            else snake_slug(spec.type)
        )
        spec.path = _unique(segment, paths, sep="-")
    return specs


def machine_prose(config: Dict[str, Any]) -> str:
    """The chart's own ``description`` (or ``meta.description``), safe."""
    desc = config.get("description")
    meta = config.get("meta")
    if not isinstance(desc, str) and isinstance(meta, dict):
        desc = meta.get("description")
    return docstring_safe(desc, limit=200) if isinstance(desc, str) else ""
