# src/xstate_statemachine/eda/envelope.py
# -----------------------------------------------------------------------------
# ✉️ Envelope -- the CloudEvents-shaped wire format (#272 defines, #293 extends)
# -----------------------------------------------------------------------------
# 🏛️ One envelope for every broker. It is CloudEvents 1.0 from day one --
#    `specversion, id, type, source, subject, time, datacontenttype, data`
#    plus the extensions `correlationid`, `causationid`, `machineid`,
#    `machineversion` -- so a non-Python consumer can read it and the
#    `[cloudevents]` extra only adds SDK interop, never a second format.
#    `subject` is the machine instance key AND the partition key: every
#    adapter must preserve order per subject.
#
# 🔐 X0.4: `from_json` checks the byte size BEFORE `json.loads` (same cap
#    and semantics as snapshots, `DEFAULT_MAX_SNAPSHOT_BYTES`), then the
#    shape; a wrong shape is `EnvelopeCorruptError`, never a `KeyError`
#    from inside a consumer loop.
# 🔐 X0.8: extension names that would carry credentials (`authorization`,
#    `cookie`, ...) are refused on construction and DROPPED by the header
#    decoders, so a broker header can never smuggle a secret into a
#    persisted snapshot, a dead letter or a log. `traceparent` must match
#    the W3C Trace Context grammar.
# -----------------------------------------------------------------------------
"""`Envelope`, sortable ids and envelope validation."""

from __future__ import annotations

import json
import os
import re
import threading
import time as _time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from ..events import Event
from ..exceptions import XStateMachineError
from ..persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

__all__ = [
    "ATTEMPT_EXTENSION",
    "EXTENSION_NAME",
    "FORBIDDEN_EXTENSIONS",
    "SPECVERSION",
    "TRACEPARENT",
    "Envelope",
    "EnvelopeCorruptError",
    "EnvelopeTooLargeError",
    "default_event_name",
    "new_id",
]

SPECVERSION = "1.0"
#: The per-envelope delivery-attempt counter (X0.8).
ATTEMPT_EXTENSION = "xsmattempt"
#: CloudEvents 1.0: extension names are lower-case ASCII letters or digits.
EXTENSION_NAME = re.compile(r"^[a-z0-9]{1,20}$")
#: W3C Trace Context `traceparent` (version 00; `ff` is invalid).
TRACEPARENT = re.compile(
    r"^(?!ff)[0-9a-f]{2}-(?!0{32})[0-9a-f]{32}-(?!0{16})[0-9a-f]{16}"
    r"-[0-9a-f]{2}$"
)
#: Substrings that mark an extension as credential-bearing (X0.8).
FORBIDDEN_EXTENSIONS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "apikey",
)
_CORE = (
    "specversion",
    "id",
    "type",
    "source",
    "subject",
    "time",
    "datacontenttype",
    "data",
)
_KNOWN_EXT = ("correlationid", "causationid", "machineid", "machineversion")
_MAX_ATTR = 1024


class EnvelopeCorruptError(XStateMachineError, ValueError):
    """An envelope's shape is invalid (missing / mistyped attribute, a
    forbidden or malformed extension, a bad ``traceparent``, non-object
    ``data`` where an event payload is required)."""


class EnvelopeTooLargeError(EnvelopeCorruptError):
    """The encoded envelope exceeds ``max_bytes`` (checked before parsing)."""


# -----------------------------------------------------------------------------
# 🔢 Sortable ids: 48-bit ms timestamp + 74 random bits, UUIDv7 layout
# -----------------------------------------------------------------------------
_id_lock = threading.Lock()
_last = [0, 0]  # [ms, random tail] -- monotonic within one millisecond


def new_id(now_ms: Optional[int] = None) -> str:
    """A UUIDv7-style id: lexicographically sortable by creation time.

    Within one millisecond the random tail is incremented, so ids minted by
    one process are strictly increasing. Stdlib only.
    """
    ms = int(_time.time() * 1000) if now_ms is None else int(now_ms)
    with _id_lock:
        if ms <= _last[0]:
            ms = _last[0]
            tail = _last[1] + 1
        else:
            tail = int.from_bytes(os.urandom(10), "big") >> 6  # 74 bits
        tail &= (1 << 74) - 1
        _last[0], _last[1] = ms, tail
    rand_a = tail >> 62  # 12 bits
    rand_b = tail & ((1 << 62) - 1)  # 62 bits
    value = (
        ((ms & ((1 << 48) - 1)) << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    h = f"{value:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_forbidden(name: str) -> bool:
    low = name.lower().replace("-", "").replace("_", "")
    return any(bad in low for bad in FORBIDDEN_EXTENSIONS)


def _check_str(name: str, value: Any, *, required: bool) -> None:
    if value is None:
        if required:
            raise EnvelopeCorruptError(f"envelope attribute {name!r} missing")
        return
    if not isinstance(value, str) or (required and not value):
        raise EnvelopeCorruptError(
            f"envelope attribute {name!r} must be a non-empty string"
        )
    if len(value) > _MAX_ATTR:
        raise EnvelopeCorruptError(
            f"envelope attribute {name!r} exceeds {_MAX_ATTR} characters"
        )


def _check_extensions(ext: Mapping[str, Any]) -> None:
    for name, value in ext.items():
        if not isinstance(name, str) or not EXTENSION_NAME.match(name):
            raise EnvelopeCorruptError(
                f"invalid CloudEvents extension name {name!r} "
                f"(lower-case letters/digits, at most 20)"
            )
        if name in _CORE or name in _KNOWN_EXT:
            raise EnvelopeCorruptError(
                f"{name!r} is an envelope attribute, not an extension"
            )
        if _is_forbidden(name):
            raise EnvelopeCorruptError(
                f"extension {name!r} looks credential-bearing; secrets "
                f"never travel in envelope extensions (X0.8)"
            )
        if not isinstance(value, (str, int, bool)):
            raise EnvelopeCorruptError(
                f"extension {name!r} must be a string, integer or boolean"
            )
        if name == "traceparent" and not TRACEPARENT.match(str(value)):
            raise EnvelopeCorruptError("invalid W3C traceparent extension")
        if name == ATTEMPT_EXTENSION and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise EnvelopeCorruptError(
                f"{ATTEMPT_EXTENSION} must be a non-negative integer"
            )


def default_event_name(envelope_type: str) -> str:
    """``xsm.<machine>.<EVENT>`` → ``EVENT``; anything else unchanged."""
    if envelope_type.startswith("xsm."):
        parts = envelope_type.split(".", 2)
        if len(parts) == 3 and parts[2]:
            return parts[2]
    return envelope_type


@dataclass(frozen=True)
class Envelope:
    """A CloudEvents 1.0 event as the library moves it between machines.

    Build one with `Envelope.new` (fills ``id`` / ``time``) or
    `Envelope.from_transition`; decode with `from_json` / `from_dict`.
    Instances are immutable; `with_attempt` / `replace` return copies.

    Attributes:
        type: Event type, e.g. ``xsm.order.PAY`` (inbound command) or
            ``order.paid`` (integration event).
        source: URI-reference of the producer (``xsm/order``).
        subject: Machine instance key -- also the partition key.
        id: Sortable unique id (`new_id`); the idempotency key.
        time: RFC 3339 timestamp.
        data: JSON payload; must be an object to become an `Event`.
        correlationid / causationid: Correlation-chain extensions.
        machineid / machineversion: The producing machine.
        extensions: Any further CloudEvents extensions (validated).
    """

    type: str
    source: str
    subject: Optional[str] = None
    id: str = ""
    time: Optional[str] = None
    data: Any = None
    specversion: str = SPECVERSION
    datacontenttype: Optional[str] = "application/json"
    correlationid: Optional[str] = None
    causationid: Optional[str] = None
    machineid: Optional[str] = None
    machineversion: Optional[str] = None
    extensions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", new_id())
        self.validate()

    # -- construction -------------------------------------------------------
    @classmethod
    def new(
        cls,
        *,
        type: str,
        subject: Optional[str] = None,
        data: Any = None,
        source: str = "xsm",
        **attrs: Any,
    ) -> "Envelope":
        """A fresh envelope with a new sortable ``id`` and ``time`` now."""
        attrs.setdefault("time", _now_iso())
        return cls(
            type=type, source=source, subject=subject, data=data, **attrs
        )

    @classmethod
    def from_transition(
        cls,
        interpreter: Any,
        *,
        type: str,
        data: Any = None,
        cause: Optional["Envelope"] = None,
        subject: Optional[str] = None,
        source: Optional[str] = None,
    ) -> "Envelope":
        """An outbound envelope describing what *interpreter* just did.

        ``causationid`` is the id of the inbound *cause* (if any) and the
        correlation id is inherited from it, so a chain of machines shares
        one ``correlationid``. ``subject`` defaults to the cause's subject
        (the business key), then the instance's store key.
        """
        machine = interpreter.machine
        subj = subject or (cause.subject if cause else None)
        if not subj:
            subj = str(
                getattr(interpreter, "store_key", None) or interpreter.id
            )
        eid = new_id()
        corr = (cause.correlationid or cause.id) if cause else eid
        ext: Dict[str, Any] = {}
        if cause is not None and "traceparent" in cause.extensions:
            ext["traceparent"] = cause.extensions["traceparent"]
        return cls(
            type=type,
            source=source or f"xsm/{machine.id}",
            subject=subj,
            id=eid,
            time=_now_iso(),
            data=data,
            correlationid=corr,
            causationid=cause.id if cause else None,
            machineid=str(machine.id),
            machineversion=machine.version or None,
            extensions=ext,
        )

    # -- validation ---------------------------------------------------------
    def validate(self) -> "Envelope":
        """Raise `EnvelopeCorruptError` unless the shape is valid."""
        if self.specversion != SPECVERSION:
            raise EnvelopeCorruptError(
                f"unsupported specversion {self.specversion!r}"
            )
        for name in ("id", "type", "source"):
            _check_str(name, getattr(self, name), required=True)
        for name in ("subject", "time", "datacontenttype") + _KNOWN_EXT:
            _check_str(name, getattr(self, name), required=False)
        if not isinstance(self.extensions, dict):
            raise EnvelopeCorruptError("extensions must be a mapping")
        _check_extensions(self.extensions)
        return self

    # -- attempts (X0.8) ----------------------------------------------------
    @property
    def attempt(self) -> int:
        """Delivery attempts recorded so far (0 for a first delivery)."""
        return int(self.extensions.get(ATTEMPT_EXTENSION, 0))

    def with_attempt(self, n: int) -> "Envelope":
        ext = dict(self.extensions)
        ext[ATTEMPT_EXTENSION] = int(n)
        return replace(self, extensions=ext)

    def replace(self, **changes: Any) -> "Envelope":
        return replace(self, **changes)

    # -- conversion ---------------------------------------------------------
    def to_event(self, event_type: Optional[str] = None) -> Event:
        """The `Event` this envelope delivers to a machine.

        The event name is *event_type* or `default_event_name(type)`; the
        payload is ``data`` (which must be a JSON object or ``None``).
        """
        self.validate()
        if self.data is not None and not isinstance(self.data, dict):
            raise EnvelopeCorruptError(
                "envelope data must be a JSON object to become an event "
                f"payload, got {type(self.data).__name__}"
            )
        return Event(
            type=event_type or default_event_name(self.type),
            payload=dict(self.data or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """The CloudEvents structured-mode JSON object (``None`` omitted)."""
        out: Dict[str, Any] = {}
        for name in _CORE + _KNOWN_EXT:
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        out.update(self.extensions)
        return out

    def to_json(self, *, max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES) -> str:
        text = json.dumps(self.to_dict(), separators=(",", ":"), default=str)
        if len(text.encode("utf-8")) > max_bytes:
            raise EnvelopeTooLargeError(
                f"envelope {self.id} is larger than {max_bytes} bytes"
            )
        return text

    @classmethod
    def from_dict(cls, raw: Any) -> "Envelope":
        if not isinstance(raw, dict):
            raise EnvelopeCorruptError("an envelope must be a JSON object")
        attrs = {k: raw[k] for k in _CORE + _KNOWN_EXT if k in raw}
        ext = {k: v for k, v in raw.items() if k not in attrs}
        for required in ("id", "type", "source", "specversion"):
            if required not in attrs:
                raise EnvelopeCorruptError(
                    f"envelope attribute {required!r} missing"
                )
        try:
            return cls(extensions=ext, **attrs)
        except TypeError as exc:  # pragma: no cover - guarded above
            raise EnvelopeCorruptError(str(exc)) from exc

    @classmethod
    def from_json(
        cls,
        text: Any,
        *,
        max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> "Envelope":
        """Decode a structured-mode envelope; size-capped before parsing."""
        size = len(text) if isinstance(text, (bytes, bytearray)) else None
        if size is None:
            if not isinstance(text, str):
                raise EnvelopeCorruptError("envelope must be str or bytes")
            size = len(text.encode("utf-8"))
        if size > max_bytes:
            raise EnvelopeTooLargeError(
                f"envelope is {size} bytes; the limit is {max_bytes}"
            )
        try:
            raw = json.loads(text)
        except ValueError as exc:
            raise EnvelopeCorruptError(f"envelope is not JSON: {exc}") from exc
        return cls.from_dict(raw)

    @staticmethod
    def safe_extensions(raw: Mapping[str, Any]) -> Dict[str, Any]:
        """*raw* minus credential-bearing names (X0.8) -- for decoders that
        copy transport headers into extensions."""
        return {k: v for k, v in raw.items() if not _is_forbidden(str(k))}
