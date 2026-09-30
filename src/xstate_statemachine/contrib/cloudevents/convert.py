# src/xstate_statemachine/contrib/cloudevents/convert.py
# -----------------------------------------------------------------------------
# ☁️ Envelope <-> cloudevents SDK objects and HTTP modes
# -----------------------------------------------------------------------------
"""Conversions between `Envelope` and the ``cloudevents`` SDK."""

from __future__ import annotations

import json
import warnings
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from ...eda.envelope import (
    Envelope,
    EnvelopeCorruptError,
    EnvelopeTooLargeError,
)
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

try:  # cloudevents 2.x keeps the 1.x API under `v1`
    from cloudevents.v1 import http as _ce_http  # type: ignore
except ImportError:  # pragma: no cover - cloudevents 1.x
    from cloudevents import http as _ce_http  # type: ignore

__all__ = [
    "from_cloudevent",
    "from_http",
    "to_binary",
    "to_cloudevent",
    "to_structured",
]

Body = Union[bytes, str]


def to_cloudevent(envelope: Envelope) -> Any:
    """An SDK ``CloudEvent`` with the same attributes, extensions and data."""
    attrs = envelope.to_dict()
    data = attrs.pop("data", None)
    return _ce_http.CloudEvent(attrs, data)


def from_cloudevent(event: Any) -> Envelope:
    """An `Envelope` from an SDK ``CloudEvent``; validated.

    Credential-bearing extensions are dropped (X0.8); anything else that
    does not fit the envelope raises `EnvelopeCorruptError`.
    """
    attrs: Dict[str, Any] = dict(event.get_attributes())
    attrs = Envelope.safe_extensions(attrs)
    time_value = attrs.get("time")
    if time_value is not None and not isinstance(time_value, str):
        attrs["time"] = time_value.isoformat()
    data = event.get_data() if hasattr(event, "get_data") else event.data
    if isinstance(data, (bytes, bytearray)):
        try:
            data = json.loads(data)
        except ValueError as exc:
            raise EnvelopeCorruptError("CloudEvent data is not JSON") from exc
    attrs["data"] = data
    return Envelope.from_dict(attrs)


def _quiet(fn: Any, *args: Any) -> Any:
    # 📝 1.x marks the top-level http helpers deprecated in favour of the
    #    conversion module; the behaviour is identical and supported.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*args)


def to_binary(envelope: Envelope) -> Tuple[Dict[str, str], bytes]:
    """HTTP binary mode: ``ce-*`` headers + the JSON data as the body."""
    headers, body = _quiet(_ce_http.to_binary, to_cloudevent(envelope))
    return dict(headers), _bytes(body)


def to_structured(envelope: Envelope) -> Tuple[Dict[str, str], bytes]:
    """HTTP structured mode: ``application/cloudevents+json`` body."""
    headers, body = _quiet(_ce_http.to_structured, to_cloudevent(envelope))
    return dict(headers), _bytes(body)


def from_http(
    headers: Mapping[str, str],
    body: Optional[Body],
    *,
    max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
) -> Envelope:
    """Decode an HTTP request in either mode into an `Envelope`.

    The body size is checked before the SDK parses it (X0.4); request
    headers that are not ``ce-*`` never become extensions, and
    credential-bearing ``ce-*`` names are dropped (X0.8).
    """
    raw = body.encode("utf-8") if isinstance(body, str) else (body or b"")
    if len(raw) > max_bytes:
        raise EnvelopeTooLargeError(
            f"CloudEvent body is {len(raw)} bytes; the limit is {max_bytes}"
        )
    safe = {
        k: v
        for k, v in headers.items()
        if k.lower() == "content-type" or k.lower().startswith("ce-")
    }
    try:
        event = _quiet(_ce_http.from_http, safe, raw)
    except Exception as exc:  # noqa: BLE001 - SDK raises its own family
        raise EnvelopeCorruptError(f"not a CloudEvent: {exc}") from exc
    return from_cloudevent(event)


def _bytes(body: Any) -> bytes:
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    return str(body).encode("utf-8")
